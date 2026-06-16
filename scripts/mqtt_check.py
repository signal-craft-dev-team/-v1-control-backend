"""독립 실행 MQTT 연결 점검 — TLS 접속 + 구독/발행 왕복 확인.

배포 없이 브로커 연결을 빠르게 확인할 때 사용한다 (db_check.py 의 MQTT 버전).

  # .env (같은 폴더) 또는 export
  MQTT_HOST=mqtt.kr001.signalcraft.kr
  MQTT_PORT=8883
  MQTT_USER=<user>
  MQTT_PASSWORD=<원본 비밀번호 그대로, 인코딩 불필요>

  python scripts/mqtt_check.py
"""
import asyncio
import os
import ssl
import json

import aiomqtt

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

TOPIC = "sc/v1/_healthcheck/ping"


async def main() -> None:
    host = os.environ["MQTT_HOST"]
    port = int(os.environ.get("MQTT_PORT", "8883"))
    client = aiomqtt.Client(
        hostname=host,
        port=port,
        username=os.environ["MQTT_USER"],
        password=os.environ["MQTT_PASSWORD"],
        tls_context=ssl.create_default_context(),
    )
    async with client:
        msg = json.dumps({"msg": "hello"})
        print(f"연결 성공 ({host}:{port})")
        await client.subscribe(TOPIC)
        await client.publish(TOPIC, msg)
        async with asyncio.timeout(10):
            async for msg in client.messages:
                print(f"수신: {msg.topic} → {msg.payload.decode()}")
                break
    print("구독/발행 왕복 확인 완료 ✅")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        raise SystemExit(f"MQTT 점검 실패: {e!r}")
