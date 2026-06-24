"""audio_recordings 테이블 R/W 쿼리.

control_backend 단독 writer. 2단계:
  - insert: upload_request 시 pending 레코드 생성
  - update: upload_result 시 status 갱신 (done / error), gcs_uri로 매칭

입출력은 signalcraft_models.pipeline 의 AudioRecording / DataStatus 로 구조화.
(signalcraft_models는 외부 공유 스키마 패키지 — app 내부 의존 아님)
"""
import json

import asyncpg
from signalcraft_models.pipeline import AudioRecording, DataStatus


async def insert(conn: asyncpg.Connection, rec: AudioRecording) -> None:
    """AudioRecording 모델로 레코드 삽입.

    - id: 모델 값(호출 측 uuid4 생성)을 그대로 사용
    - created_at: INSERT에 미포함 → DB 기본값 now() 사용 (모델의 created_at은 무시)
    - status: 보통 DataStatus.pending (발급 시점)
    """
    await conn.execute(
        """
        INSERT INTO audio_recordings (
            id, customer_id, server_id, gcs_uri, format,
            sample_rate, bit_depth, duration_ms, channel_count,
            status, file_size_bytes, query_params, captured_at, sensor_id
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9,
            $10::data_status, $11, $12::jsonb, $13, $14
        )
        """,
        rec.id,
        rec.customer_id,
        rec.server_id,
        rec.gcs_uri,
        rec.format,
        rec.sample_rate,
        rec.bit_depth,
        rec.duration_ms,
        rec.channel_count,
        rec.status.value,
        rec.file_size_bytes,
        json.dumps(rec.query_params),
        rec.captured_at,
        rec.sensor_id,
    )


async def update(conn: asyncpg.Connection, gcs_uri: str, status: DataStatus) -> str:
    """업로드 결과 시 status 갱신. gcs_uri로 매칭.

    반환: asyncpg 명령 태그(예: 'UPDATE 1') — 0건이면 'UPDATE 0'.
    """
    return await conn.execute(
        "UPDATE audio_recordings SET status = $2::data_status WHERE gcs_uri = $1",
        gcs_uri,
        status.value,
    )
