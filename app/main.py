import asyncio
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
# DB
from app.database.db import close_pool
# MQTT
from app.mqtt.service import serve
# STORAGE
from app.presigned.storage import generate_upload_url, RAW_BUCKET
# HANDLER
from app.handler import mqtt_router
from app.handler.register import router as register_router
from app.handler.find_device import router as find_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(serve(mqtt_router))
    try:
        yield
    finally:
        task.cancel()
        await close_pool()

app = FastAPI(lifespan=lifespan)
app.include_router(register_router)
app.include_router(find_router)

@app.get("/health")
def health():
    return {"status": "ok!"}


# @app.get("/test/edge-servers", tags=['test'])
# async def list_edge_servers():
#     """DB 연결 테스트 — edge_server 테이블 전체 행 반환."""
#     try:
#         pool = await get_pool()
#         async with pool.acquire() as conn:
#             rows = await conn.fetch("SELECT * FROM edge_server")
#         payload = {"count": len(rows), "rows": [dict(r) for r in rows]}
#         # UUID / IPv4Address / datetime / time 등을 일괄 안전 직렬화
#         return JSONResponse(json.loads(json.dumps(payload, default=str)))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"DB error: {e!s}")

# @app.get("/test/mqtt-broker", tags=['test'])
# async def pub_sub_mqtt():
#     """MQTT 연결 테스트 - 목업 메시지 전송"""
#     TOPIC = "sc/v1/_healthcheck/ping"
#     try:
#         client = make_client()
#         print(client)
#         async with client:
#             msg = json.dumps({"msg": "hello"})
#             print(f"연결 성공 ({client._hostname}:{client._port})")
#             await client.subscribe(TOPIC)
#             await client.publish(TOPIC, msg)
#             async with asyncio.timeout(10):
#                 async for msg in client.messages:
#                     print(f"수신: {msg.topic} → {msg.payload.decode()}")
#                     break
#         return JSONResponse(json.loads(json.dumps("구독/발행 왕복 확인 완료 ✅", default=str)))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"MQTT error: {e!s}")

# @app.get("/test/get-presigned-url", tags=['test'])
# async def get_presigned():
#     """Presigned 발급 테스트"""
#     obj = "_healthcheck/presigned-test.txt"
#     try:
#         url = generate_upload_url(obj, content_type="text/plain")
#         req = urllib.request.Request(
#             url, data=b"hello", method="PUT",
#             headers={"Content-Type": "text/plain"},
#         )
#         with urllib.request.urlopen(req, timeout=10) as resp:
#             put_status = resp.status
#         return {"signed": True, "bucket": RAW_BUCKET, "object": obj, "put_status": put_status}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"presigned error: {e!s}")