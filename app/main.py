import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.database.db import close_pool, get_pool


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
