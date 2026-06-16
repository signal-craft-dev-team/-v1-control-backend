"""MQTT 서비스 루프 — 연결/재연결 + 전체 구독 + 디스패치.

- 단일 aiomqtt 연결을 들고 router에 등록된 모든 토픽을 구독.
- 재연결 시 세션이 초기화되므로 연결할 때마다 다시 subscribe.
- 메시지별 try/except로 한 메시지 실패가 루프를 죽이지 않게 격리.

단독 실행(동작 점검):
    # 환경: MQTT_HOST / MQTT_PORT / MQTT_USER / MQTT_PASSWORD
    python -m app.mqtt_service
    # MQTTX: sc/v1/e2c/test1/_ping 발행 → sc/v1/c2e/test1/_pong 수신 확인
"""
import asyncio
import logging

import aiomqtt

from .client import make_client
from .router import Router

log = logging.getLogger("control_backend.mqtt.service")

_RECONNECT_DELAY = 5

async def serve(router: Router) -> None:
    while True:
        try:
            async with make_client() as client:
                subs = router.subscriptions()
                for topic_filter in subs:
                    await client.subscribe(topic_filter, qos=1)
                log.info("MQTT connected — subscribed: %s", subs)
                async for message in client.messages:
                    try:
                        await router.dispatch(client, message)
                    except Exception:
                        log.exception("dispatch failed topic=%s", message.topic)
        except aiomqtt.MqttError as e:
            log.warning("MQTT error: %s — reconnect in %ss", e, _RECONNECT_DELAY)
            await asyncio.sleep(_RECONNECT_DELAY)


# ──────────────────────────────────────────────────────────────────────────────
# 통합(integration) 사용법
# ──────────────────────────────────────────────────────────────────────────────
# 이 모듈은 pub/sub 프레임워크(연결·구독·디스패치)만 제공한다.
# 핸들러 조합은 mqtt 범위 밖 — integration 단계에서 main.py가 담당한다:
#
#   import asyncio
#   from contextlib import asynccontextmanager
#   from fastapi import FastAPI
#   from app.mqtt.router import Router
#   from app.mqtt.service import serve
#   from app.mqtt.handlers import upload                       # presigned 등 핸들러(integration에서 추가)
#   from signalcraft_models.mqtt import edge_cloud_topics as T
#
#   router = Router()
#   router.on(T.e2c("+", T.UPLOAD_REQUEST), upload.handle)
#
#   @asynccontextmanager
#   async def lifespan(app: FastAPI):
#       task = asyncio.create_task(serve(router))
#       try:
#           yield
#       finally:
#           task.cancel()
#
#   app = FastAPI(lifespan=lifespan)
#
# ──────────────────────────────────────────────────────────────────────────────
# 로컬 pub/sub 점검용 데모 (ping/pong) — 필요 시 주석 해제 후 `python -m app.mqtt.service`
# ──────────────────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     import json
#     import dotenv
#     dotenv.load_dotenv()
#
#     logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
#
#     router = Router()
#
#     async def _ping(client: aiomqtt.Client, message: aiomqtt.Message) -> None:
#         server_id = message.topic.value.split("/")[3]   # sc/v1/e2c/{server_id}/_ping
#         log.info("ping from %s payload=%s", server_id, message.payload.decode(errors="replace"))
#         await client.publish(f"sc/v1/c2e/{server_id}/_pong", json.dumps({"ok": True}), qos=1)
#
#     router.on("sc/v1/e2c/+/_ping", _ping)
#     asyncio.run(serve(router))
