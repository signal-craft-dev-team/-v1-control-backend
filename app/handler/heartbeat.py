import logging
import aiomqtt
from signalcraft_models.mqtt import edge_cloud_models as M
from app.database.db import get_pool

log = logging.getLogger("control_backend.handler.heartbeat")

async def server_heartbeat_handler(client: aiomqtt.Client, message: aiomqtt.Message) -> None:
    hb = M.ServerHeartbeat.model_validate_json(message.payload)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO server_heartbeats (id, server_id, recorded_at)
                VALUES (gen_random_uuid(), $1::uuid, $2::timestamptz)""",
            str(hb.server_id), hb.sent_at,
        )
    log.debug("server heartbeat recorded server_id=%s", hb.server_id)


async def sensor_heartbeat_handler(client: aiomqtt.Client, message: aiomqtt.Message) -> None:
    hb = M.SensorHeartbeat.model_validate_json(message.payload)
    pool = await get_pool()
    async with pool.acquire() as conn:
        # hardware_id로 edge_sensor UUID 조회
        row = await conn.fetchrow(
            """SELECT id FROM edge_sensor
                WHERE hardware_id = $1 AND server_id = $2::uuid""",
            hb.sensor_id, str(hb.server_id),
        )
        if row is None:
            log.warning("sensor not found hardware_id=%s server_id=%s", hb.sensor_id, hb.server_id)
            return
        await conn.execute(
            """INSERT INTO sensor_heartbeats (id, sensor_id, recorded_at)
                VALUES (gen_random_uuid(), $1::uuid, $2::timestamptz)""",
            str(row["id"]), hb.sent_at,
        )
    log.debug("sensor heartbeat recorded hardware_id=%s", hb.sensor_id)