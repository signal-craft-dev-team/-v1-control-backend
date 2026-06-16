import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.db import close_pool, get_pool
from app.mqtt_client import make_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok!"}


@app.get("/test/edge-servers")
async def list_edge_servers():
    """DB 연결 테스트 — edge_server 테이블 전체 행 반환."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM edge_server")
        payload = {"count": len(rows), "rows": [dict(r) for r in rows]}
        # UUID / IPv4Address / datetime / time 등을 일괄 안전 직렬화
        return JSONResponse(json.loads(json.dumps(payload, default=str)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e!s}")

@app.get("/test/mqtt-broker")
async def pub_sub_mqtt():
    """MQTT 연결 테스트 - 목업 메시지 전송"""
    TOPIC = "sc/v1/_healthcheck/ping"
    try:
        client = make_client()
        print(client)
        async with client:
            msg = json.dumps({"msg": "hello"})
            print(f"연결 성공 ({client._hostname}:{client._port})")
            await client.subscribe(TOPIC)
            await client.publish(TOPIC, msg)
            async with asyncio.timeout(10):
                async for msg in client.messages:
                    print(f"수신: {msg.topic} → {msg.payload.decode()}")
                    break
        return JSONResponse(json.loads(json.dumps("구독/발행 왕복 확인 완료 ✅", default=str)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MQTT error: {e!s}")