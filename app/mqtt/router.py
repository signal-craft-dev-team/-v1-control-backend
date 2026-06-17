"""MQTT 토픽 라우터 — 토픽 필터 → 핸들러 등록·매칭·디스패치.

핸들러 시그니처:
    async def handler(client: aiomqtt.Client, message: aiomqtt.Message) -> None

사용:
    router = Router()
    router.on("sc/v1/e2c/+/upload_request", upload.handle)
    ...
    await router.dispatch(client, message)   # service 루프에서 호출
"""
import logging
from collections.abc import Awaitable, Callable

import aiomqtt

log = logging.getLogger("control_backend.mqtt.router")

Handler = Callable[[aiomqtt.Client, aiomqtt.Message], Awaitable[None]]


class Router:
    def __init__(self) -> None:
        self._routes: list[tuple[str, Handler]] = []

    def on(self, topic_filter: str, handler: Handler) -> Handler:
        """토픽 필터(와일드카드 가능)에 핸들러를 등록."""
        self._routes.append((topic_filter, handler))
        return handler

    def subscriptions(self) -> list[str]:
        """구독해야 할 토픽 필터 목록(중복 제거)."""
        seen: set[str] = set()
        out: list[str] = []
        for f, _ in self._routes:
            if f not in seen:
                seen.add(f)
                out.append(f)
        return out

    async def dispatch(self, client: aiomqtt.Client, message: aiomqtt.Message) -> None:
        """수신 메시지를 첫 매칭 핸들러로 라우팅. 매칭 없으면 경고만."""
        for topic_filter, handler in self._routes:
            if message.topic.matches(topic_filter):   # aiomqtt 와일드카드 매칭(+/#)
                await handler(client, message)
                return
        log.warning("no route for topic=%s", message.topic)
