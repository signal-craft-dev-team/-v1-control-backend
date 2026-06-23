import json
import logging
import aiomqtt
from signalcraft_models.mqtt import edge_cloud_models as M
from signalcraft_models.mqtt import edge_cloud_topics as T
from app.database.db import get_pool
from app.database.queries import edge_server

log = logging.getLogger("control_backend.handler.param_request")

async def param_request_handler(client: aiomqtt.Client, message: aiomqtt.Message) -> None:
    req = M.ParamRequest.model_validate_json(message.payload)
    server_id = str(req.server_id)

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await edge_server.find(conn, server_id)

    if row is None:
        log.warning("server not found server_id=%s", server_id)
        return

    result = M.ParamResult(
        server_id=server_id,
        is_active=row.is_active,
        capture_duration_ms=row.capture_duration_ms,
        upload_interval_ms=row.upload_interval_ms,
        active_hours_start=str(row.active_hours_start) if row.active_hours_start else None,
        active_hours_end=str(row.active_hours_end) if row.active_hours_end else None,
        sensor_captured_gap_ms=row.sensor_captured_gap_ms,
    )
    await client.publish(
        T.c2e(server_id, T.PARAM_RESULT),
        json.dumps(result.model_dump(mode='json')),
        qos=1,
    )
    log.info("param_result sent server_id=%s is_active=%s", server_id, row.is_active)