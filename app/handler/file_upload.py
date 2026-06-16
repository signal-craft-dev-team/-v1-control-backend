"""UPLOAD_REQUEST 핸들러 — presigned 발급 + audio_recordings pending 기록.

흐름:
  1) hostname(+mac)으로 edge_server 식별 (find_by_info) → 없으면 에러 처리(발행 안 함)
  2) audio_recordings pending INSERT (control_backend 단독 writer)
  3) presigned URL 발급(to_thread) → UPLOAD_URL 발행

필요 계약(UploadRequest 필드): server_id(라우팅), hostname, mac_address,
  round_ts, sensor_order, sample_rate, bit_depth, channel_count, duration_ms,
  file_size_bytes, recorded_at
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import aiomqtt
from signalcraft_models.mqtt import edge_cloud_models as M
from signalcraft_models.mqtt import edge_cloud_topics as T
from signalcraft_models.pipeline import AudioRecording, DataStatus

from app.database.db import get_pool
from app.database.queries import audio_recordings, edge_server
from app.presigned.storage import RAW_BUCKET, generate_upload_url

log = logging.getLogger("control_backend.handler.upload")

KST = ZoneInfo("Asia/Seoul")
TTL = 15


def _object_key(server_id: str, round_ts: str) -> str:
    dt = datetime.fromisoformat(round_ts.replace("Z", "+00:00")).astimezone(KST)
    return f"{server_id}/{dt:%Y%m%d}/{dt:%Y%m%d_%H%M%S}_merged.wav"


async def file_upload_handler(client: aiomqtt.Client, message: aiomqtt.Message) -> None:
    req = M.UploadRequest.model_validate_json(message.payload)
    object_key = _object_key(req.server_id, req.round_ts)
    gcs_uri = f"gs://{RAW_BUCKET}/{object_key}"

    pool = await get_pool()
    async with pool.acquire() as conn:
        edge = await edge_server.find_by_info(conn, req.hostname, req.mac_address)
        if edge is None:
            # 미등록 서버 → 기록 불가(customer_id NOT NULL). URL 발급하지 않고 종료.
            log.error("unknown edge server: hostname=%s mac=%s", req.hostname, req.mac_address)
            return

        rec = AudioRecording(
            id=uuid4(),
            customer_id=edge.customer_id,
            server_id=edge.id,                      # DB 정본 UUID
            gcs_uri=gcs_uri,
            format="wav",
            sample_rate=req.sample_rate,
            bit_depth=req.bit_depth,
            duration_ms=req.duration_ms,
            channel_count=req.channel_count,
            status=DataStatus.pending,
            file_size_bytes=req.file_size_bytes,
            query_params={"sensor_order": req.sensor_order},
            captured_at=req.recorded_at,
            created_at=datetime.now(timezone.utc),  # 모델 필수(INSERT선 무시, DB now())
        )
        async with conn.transaction():
            await audio_recordings.insert(conn, rec)

    # 서명은 동기 네트워크 I/O → 이벤트 루프 보호 (DB 트랜잭션 밖)
    url = await asyncio.to_thread(generate_upload_url, object_key, "audio/wav", TTL)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=TTL)).isoformat()

    resp = M.UploadUrl(
        server_id=req.server_id,                    # 라우팅 id 그대로 echo
        round_ts=req.round_ts,
        object_key=object_key,
        presigned_url=url,
        expires_at=expires_at,
    )
    await client.publish(T.c2e(req.server_id, T.UPLOAD_URL), resp.model_dump_json(), qos=1)
    log.info("issued presigned url server=%s key=%s", req.server_id, object_key)
