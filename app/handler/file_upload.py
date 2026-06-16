import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import aiomqtt
from app.presigned.storage import generate_upload_url
from signalcraft_models.mqtt import edge_cloud_topics as T, edge_cloud_models as M

KST = ZoneInfo("Asia/Seoul")
TTL = 15

def _object_key(server_id, round_ts):
    dt = datetime.fromisoformat(round_ts.replace("Z","+00:00")).astimezone(KST)
    return f"{server_id}/{dt:%Y%m%d}/{dt:%Y%m%d_%H%M%S}_merged.wav"

async def file_upload_handler(client: aiomqtt.Client, message: aiomqtt.Message):
    req = M.UploadRequest.model_validate_json(message.payload)
    key = _object_key(req.server_id, req.round_ts)
    url = await asyncio.to_thread(generate_upload_url, key, "audio/wav", TTL)   # ★ 블로킹 → to_thread
    expires = (datetime.now(timezone.utc) + timedelta(minutes=TTL)).isoformat()
    # TODO(meta): meta 테이블 INSERT (key, server_id, round_ts, sensor_map, recorded_at)
    
    resp = M.UploadUrl(server_id=req.server_id, round_ts=req.round_ts,
                        object_key=key, presigned_url=url, expires_at=expires)
    await client.publish(T.c2e(req.server_id, T.UPLOAD_URL), resp.model_dump_json(), qos=1)