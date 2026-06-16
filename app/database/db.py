"""DB 연결 헬퍼 (asyncpg 풀).

연결 정보는 두 방식 중 하나로 받는다 (분리 파라미터 우선):
  1) 분리 파라미터(권장, 특수문자 비밀번호 안전):
     PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE
  2) DATABASE_URL (이 경우 비밀번호는 URL 인코딩 필요)
"""
import os

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """지연 생성 싱글톤 풀. 첫 요청 때 연결을 연다(앱 기동은 DB와 무관하게 성공)."""
    global _pool
    if _pool is None:
        if os.environ.get("PGUSER"):
            _pool = await asyncpg.create_pool(
                host=os.environ.get("PGHOST", "localhost"),
                port=int(os.environ.get("PGPORT", "5432")),
                user=os.environ["PGUSER"],
                password=os.environ["PGPASSWORD"],
                database=os.environ.get("PGDATABASE", "signalcraft"),
                min_size=1,
                max_size=5,
            )
        else:
            dsn = os.environ.get("DATABASE_URL")
            if not dsn:
                raise RuntimeError("PGUSER+PGPASSWORD 또는 DATABASE_URL 이 필요합니다.")
            _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None



{
  "server_id": "test-server",
  "round_ts": "2026-06-16T06:30:00Z",
  "object_key": "test-server/20260616/20260616_153000_merged.wav",
  "presigned_url": "",
  "expires_at": "2026-06-16T07:41:51.484905+00:00"
}