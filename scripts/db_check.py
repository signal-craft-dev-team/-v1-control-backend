"""독립 실행 DB 연결 점검 스크립트.

배포 없이 빠르게 연결을 확인할 때 사용한다.

권장 — 특수문자 비밀번호는 URL 인코딩 없이 분리 파라미터로 전달:
  # .env (같은 폴더)
  PGHOST=localhost          # 노트북에서 IAP 터널 사용 시. VM 안이면 10.178.0.3
  PGPORT=5432
  PGUSER=signalcraft_control_backend
  PGPASSWORD=<원본 비밀번호 그대로, 인코딩 불필요>
  PGDATABASE=signalcraft

  python scripts/db_check.py

대안 — DATABASE_URL 하나로 줄 때는 비밀번호를 반드시 URL 인코딩(quote_plus)할 것.

노트북에서 실행 시 IAP 터널을 먼저 띄워야 한다(Beekeeper가 쓰는 그 터널):
  gcloud compute start-iap-tunnel main-db-server-01 5432 \
    --local-host-port=localhost:5432 --zone=asia-northeast3-a
"""
import asyncio
import os

import asyncpg

try:
    from dotenv import load_dotenv

    load_dotenv()  # 같은 경로의 .env 자동 로드
except ImportError:
    pass


async def main() -> None:
    if os.environ.get("PGUSER"):
        # 분리 파라미터 (특수문자 비밀번호 안전)
        host = os.environ.get("PGHOST", "localhost")
        port = int(os.environ.get("PGPORT", "5432"))
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=os.environ["PGUSER"],
            password=os.environ["PGPASSWORD"],
            database=os.environ.get("PGDATABASE", "signalcraft"),
            timeout=10,
        )
        target = f"{host}:{port}"
    elif os.environ.get("DATABASE_URL"):
        conn = await asyncpg.connect(os.environ["DATABASE_URL"], timeout=10)
        target = "DATABASE_URL"
    else:
        raise SystemExit("PGUSER+PGPASSWORD 또는 DATABASE_URL 을 설정하세요.")

    try:
        rows = await conn.fetch("SELECT * FROM edge_server")
        print(f"연결 성공 ({target}) — edge_server {len(rows)}행")
        for r in rows:
            print(dict(r))
    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (asyncio.TimeoutError, OSError) as e:
        raise SystemExit(
            f"연결 실패: {e!r}\n"
            "→ host가 맞는지 확인(노트북=localhost+IAP터널 / VM=10.178.0.3), "
            "터널이 떠 있는지 확인하세요."
        )
