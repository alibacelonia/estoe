"""GCP global Secret Manager adapter using Application Default Credentials."""

from __future__ import annotations

import re

from estoe.encoding import MAX_SECRET_BYTES
from estoe.errors import EstoeError
from estoe.providers import run_isolated, send_result


def valid_project(value: str) -> bool:
    return bool(re.fullmatch(r"(?:[a-z][a-z0-9-]{4,28}[a-z0-9]|[0-9]{6,30})", value))


def read_gcp(secret: str, project: str, client_factory=None) -> str:
    import google_crc32c
    from google.api_core import exceptions as errors
    from google.auth.exceptions import DefaultCredentialsError, RefreshError
    from google.cloud import secretmanager

    if not valid_project(project) or not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", secret):
        raise EstoeError("configuration")
    client_factory = client_factory or secretmanager.SecretManagerServiceClient
    try:
        # REST avoids native gRPC diagnostics writing to stderr outside Python logging.
        with client_factory(transport="rest") as client:
            response = client.access_secret_version(
                request={"name": f"projects/{project}/secrets/{secret}/versions/latest"},
                retry=None,
                timeout=5,
            )
        data = response.payload.data
        if not isinstance(data, bytes):
            raise EstoeError("invalid_content")
        if len(data) > MAX_SECRET_BYTES:
            raise EstoeError("content_limit")
        if google_crc32c.value(data) != response.payload.data_crc32c:
            raise EstoeError("integrity")
        return data.decode("utf-8")
    except (DefaultCredentialsError, RefreshError, errors.Unauthenticated):
        raise EstoeError("credentials") from None
    except errors.PermissionDenied:
        raise EstoeError("access_denied") from None
    except errors.NotFound:
        raise EstoeError("not_found") from None
    except errors.ResourceExhausted:
        raise EstoeError("throttled") from None
    except errors.DeadlineExceeded:
        raise EstoeError("timeout") from None
    except (errors.FailedPrecondition, errors.InvalidArgument):
        raise EstoeError("configuration") from None
    except errors.GoogleAPICallError:
        raise EstoeError("provider") from None
    except (UnicodeDecodeError, AttributeError):
        raise EstoeError("invalid_content") from None


def _gcp_worker(connection, secret: str, project: str) -> None:
    send_result(connection, read_gcp, secret, project)


class GCPProvider:
    def __init__(self, project: str) -> None:
        self.project = project

    def fetch(self, secret: str) -> str:
        return run_isolated(_gcp_worker, secret, self.project)
