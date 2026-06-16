"""edge_server 테이블 조회 쿼리.

순수 데이터 액세스 계층 — conn(asyncpg.Connection)을 인자로 받고,
반환은 signalcraft_models의 EdgeServer(pydantic)로 구조화한다.
(signalcraft_models는 외부 공유 스키마 패키지 — app 내부 의존 아님)
"""
import asyncpg
from signalcraft_models.edge import EdgeServer


async def find(conn: asyncpg.Connection, server_id: str) -> EdgeServer | None:
    """server_id(uuid)로 edge_server 행을 조회. 없으면 None.

    반환은 EdgeServer 모델 — 호출 측은 `row.customer_id` 처럼 타입 안전하게 사용.
    """
    row = await conn.fetchrow(
        "SELECT * FROM edge_server WHERE id = $1::uuid",
        server_id,
    )
    return EdgeServer.model_validate(dict(row)) if row else None
