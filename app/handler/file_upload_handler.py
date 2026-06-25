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
from signalcraft_models.timeutil import now_kst

from app.database.db import get_pool
from app.database.queries import audio_recordings, edge_server
from app.presigned.storage import RAW_BUCKET, generate_upload_url

log = logging.getLogger("control_backend.handler.upload")

KST = ZoneInfo("Asia/Seoul")
TTL = 15

async def file_upload_handler(client: aiomqtt.Client, message: aiomqtt.Message) -> None:
    req = M.UploadRequest.model_validate_json(message.payload)
    gcs_uri = f"gs://{RAW_BUCKET}/{req.object_key}"
    pool = await get_pool()

    async with pool.acquire() as conn:
        edge = await edge_server.find(conn, req.server_id)
        if edge is None:
            # 미등록 서버 → 기록 불가(customer_id NOT NULL). URL 발급하지 않고 종료.
            log.error("unknown edge server: data=%s", req.model_dump_json())
            return
        
        sensor = await conn.fetchrow(                                # hardware_id → sensor_id
            "SELECT id FROM edge_sensor WHERE hardware_id=$1 AND server_id=$2::uuid",
            req.sensor_hw_id, req.server_id,
        )
        if sensor is None:
            log.error("unknown sensor: hw_id=%s server=%s", req.sensor_hw_id, req.server_id)
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
            channel_count=1,
            status=DataStatus.pending,
            file_size_bytes=req.file_size_bytes,
            query_params={"round_ts": req.recorded_at},   # ← 추가
            captured_at=datetime.fromisoformat(req.recorded_at),
            created_at=now_kst(),
            sensor_id=sensor["id"]
        )
        async with conn.transaction():
            await audio_recordings.insert(conn, rec)

    # 서명은 동기 네트워크 I/O → 이벤트 루프 보호 (DB 트랜잭션 밖)
    url = await asyncio.to_thread(generate_upload_url, req.object_key, "audio/wav", TTL)
    expires_at=(now_kst() + timedelta(minutes=TTL)).isoformat(),

    resp = M.UploadUrl(
        server_id=req.server_id,                    # 라우팅 id 그대로 echo
        round_ts=req.recorded_at,
        object_key=req.object_key,
        presigned_url=url,
        expires_at=expires_at,
    )
    await client.publish(T.c2e(req.server_id, T.UPLOAD_URL), resp.model_dump_json(), qos=1)
    log.info("issued presigned url server=%s key=%s", req.server_id, req.object_key)
