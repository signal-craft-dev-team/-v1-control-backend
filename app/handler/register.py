"""서버 등록 HTTP 엔드포인트 — POST /register.

엣지가 활성화(customer_id/place_id 확보) 후 hostname/mac으로 등록 → server_id 발급.
register_initialized_edge(find-or-create, ON CONFLICT(hostname))로 처리.
"""
import logging

from fastapi import APIRouter, HTTPException
from signalcraft_models.registration import RegisterRequest, RegisterResult

from app.database.db import get_pool
from app.database.queries import edge_server

log = logging.getLogger("control_backend.handler.register")

router = APIRouter()


@router.post("/register", response_model=RegisterResult)
async def register(req: RegisterRequest) -> RegisterResult:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                edge = await edge_server.register_initialized_edge(
                    conn,
                    customer_id=req.customer_id,
                    place_id=req.place_id,
                    hostname=req.hostname,
                    mac_address=req.mac_address,
                    installed_at=req.installed_at,
                )
    except Exception as e:
        # FK 위반(미존재 customer/place 등) 포함 — 검증 보강은 추후 TODO
        log.exception("register failed hostname=%s", req.hostname)
        raise HTTPException(status_code=500, detail=f"register error: {e!s}")

    log.info("registered server=%s hostname=%s", edge.id, req.hostname)
    return RegisterResult(server_id=edge.id, is_active=edge.is_active)
