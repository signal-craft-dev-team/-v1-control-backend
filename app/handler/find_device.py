"""서버 검색 HTTP 엔드 포인트

edge_server / edge_sensor를 검색해서 등록이 검증되었는지를 확인하는 엔드포인트
"""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from signalcraft_models.edge import EdgeServerRequest

from app.database.db import get_pool
from app.database.queries import edge_server

log = logging.getLogger("control_backend.handler.find_device")

router = APIRouter()

@router.post("/find_server")
async def find_server(req: EdgeServerRequest):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                edge = await edge_server.find(conn, server_id=req.id)
        if edge is None:
            raise ValueError()
        return Response(status_code=200, content=str(edge.id))
    except ValueError:
        log.warning("not find server id=%s", req.id)
        raise HTTPException(status_code=404, detail="server not found")
    except Exception as e:
        # FK 위반(미존재 customer/place 등) 포함 — 검증 보강은 추후 TODO
        log.exception("server error=%s", str(e))
        raise HTTPException(status_code=500, detail=f"register error: {e!s}")
    
