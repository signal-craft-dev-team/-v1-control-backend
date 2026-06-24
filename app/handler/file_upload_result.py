"""UPLOAD_RESULT 핸들러 — 업로드 결과로 audio_recordings status 마감.

흐름:
  1) UploadResult 파싱
  2) object_key → gcs_uri, status(SUCCESS→done / 그 외→error)
  3) audio_recordings.update (gcs_uri로 매칭). 매칭 0건이면 경고(요청 기록 없이 결과 도착)

발행 없음(종착점). control_backend 단독 writer.
"""
import logging

import aiomqtt
from signalcraft_models.mqtt import edge_cloud_models as M
from signalcraft_models.pipeline import DataStatus

from app.database.db import get_pool
from app.database.queries import audio_recordings
from app.presigned.storage import RAW_BUCKET

log = logging.getLogger("control_backend.handler.upload_result")


async def file_upload_result_handler(client: aiomqtt.Client, message: aiomqtt.Message) -> None:
    res = M.UploadResult.model_validate_json(message.payload)
    gcs_uri = f"gs://{RAW_BUCKET}/{res.object_key}"
    status = DataStatus.done if res.status == "SUCCESS" else DataStatus.error

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            tag = await audio_recordings.update(conn, gcs_uri, status)
            if res.status == "SUCCESS":
                await conn.execute(
                    """UPDATE edge_sensor SET last_processed_file=$1
                        WHERE hardware_id=$2 AND server_id=$3::uuid""",
                    res.object_key, res.sensor_hw_id, res.server_id,
                )

    if tag.rsplit(" ", 1)[-1] == "0":  # 'UPDATE 0' → 매칭 행 없음
        log.warning("no audio_recordings row for gcs_uri=%s (result without request?)", gcs_uri)
    else:
        log.info("upload result server=%s key=%s status=%s",
                 res.server_id, res.object_key, status.value)
