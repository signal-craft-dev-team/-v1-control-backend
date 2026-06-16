"""MQTT 클라이언트 헬퍼 (aiomqtt, TLS).

연결 정보는 환경변수로 받는다 (특수문자 비밀번호 안전 — URL 아님):
  MQTT_HOST / MQTT_PORT(기본 8883) / MQTT_USER / MQTT_PASSWORD

브로커는 public Let's Encrypt 인증서를 쓰므로 시스템 CA로 검증한다(커스텀 CA 불필요).
"""
import os
import ssl

import aiomqtt


def make_client() -> aiomqtt.Client:
    return aiomqtt.Client(
        hostname=os.environ["MQTT_HOST"],
        port=int(os.environ.get("MQTT_PORT", "8883")),
        username=os.environ["MQTT_USER"],
        password=os.environ["MQTT_PASSWORD"],
        tls_context=ssl.create_default_context(),
    )
