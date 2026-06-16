"""GCS presigned(V4) URL 발급 — keyless signBlob.

VM에 부착된 SA(control-backend@)를 ADC로 사용하며, 개인키 없이 IAM signBlob으로 서명한다.
필요 조건:
  - VM 스코프: cloud-platform
  - SA 권한: 자기 자신에 roles/iam.serviceAccountTokenCreator + 대상 버킷 objectCreator
  - iamcredentials.googleapis.com 활성화
"""
import datetime
import os
import urllib.request

from google.auth import default
from google.auth.transport.requests import Request
from google.cloud import storage

RAW_BUCKET = os.environ.get("RAW_BUCKET", "signalcraft-raw-audio")


def _vm_sa_email() -> str:
    """VM 메타데이터에서 부착된 SA 이메일을 읽는다(서명 주체)."""
    req = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
        headers={"Metadata-Flavor": "Google"},
    )
    return urllib.request.urlopen(req, timeout=5).read().decode()


def generate_upload_url(
    object_name: str,
    content_type: str = "application/octet-stream",
    expires_minutes: int = 15,
) -> str:
    """raw 버킷에 대한 V4 PUT presigned URL을 발급한다(keyless)."""
    creds, project = default()
    creds.refresh(Request())  # access_token 확보 (signBlob 서명에 사용)
    client = storage.Client(project=project, credentials=creds)
    blob = client.bucket(RAW_BUCKET).blob(object_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expires_minutes),
        method="PUT",
        content_type=content_type,
        service_account_email=_vm_sa_email(),
        access_token=creds.token,
    )
