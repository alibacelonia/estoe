"""Minimal provider contract and bounded AWS adapter."""

from __future__ import annotations

import logging
import multiprocessing
from collections.abc import Callable
from multiprocessing.connection import Connection
from typing import Protocol

from estoe.encoding import MAX_SECRET_BYTES
from estoe.errors import EstoeError

PROVIDER_DEADLINE = 15.0


class SecretProvider(Protocol):
    def fetch(self, secret: str) -> str: ...


def read_aws(secret: str, profile: str | None, region: str | None, session_factory=None) -> str:
    """Runs inside the isolated worker; session_factory is an offline test seam."""
    from botocore.config import Config
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        ConnectTimeoutError,
        CredentialRetrievalError,
        NoCredentialsError,
        NoRegionError,
        PartialCredentialsError,
        ProfileNotFound,
        ReadTimeoutError,
        SSOTokenLoadError,
        TokenRetrievalError,
        UnauthorizedSSOTokenError,
    )

    try:
        if session_factory is None:
            import boto3

            session_factory = boto3.session.Session
        session = session_factory(profile_name=profile, region_name=region)
        if not session.region_name:
            raise EstoeError("configuration")
        client = session.client(
            "secretsmanager",
            config=Config(
                connect_timeout=2,
                read_timeout=3,
                retries={"total_max_attempts": 2, "mode": "standard"},
            ),
        )
        try:
            response = client.get_secret_value(SecretId=secret, VersionStage="AWSCURRENT")
        finally:
            client.close()
        if "SecretBinary" in response:
            raise EstoeError("binary_secret")
        value = response.get("SecretString")
        if not isinstance(value, str):
            raise EstoeError("invalid_content")
        if len(value.encode("utf-8")) > MAX_SECRET_BYTES:
            raise EstoeError("content_limit")
        return value
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        mapped = {
            "AccessDeniedException": "access_denied",
            "DecryptionFailure": "access_denied",
            "ResourceNotFoundException": "not_found",
            "ThrottlingException": "throttled",
            "ExpiredTokenException": "credentials",
            "UnrecognizedClientException": "credentials",
            "InvalidSignatureException": "credentials",
        }.get(code, "provider")
        raise EstoeError(mapped) from None
    except (
        NoCredentialsError,
        PartialCredentialsError,
        CredentialRetrievalError,
        TokenRetrievalError,
        SSOTokenLoadError,
        UnauthorizedSSOTokenError,
    ):
        raise EstoeError("credentials") from None
    except (ProfileNotFound, NoRegionError):
        raise EstoeError("configuration") from None
    except (ConnectTimeoutError, ReadTimeoutError):
        raise EstoeError("timeout") from None
    except BotoCoreError:
        raise EstoeError("provider") from None


def _worker(connection: Connection, secret: str, profile: str | None, region: str | None) -> None:
    # SDK debug logging can include payloads. This process never emits SDK diagnostics.
    logging.disable(logging.CRITICAL)
    try:
        value = read_aws(secret, profile, region)
        connection.send_bytes(b"+" + value.encode("utf-8"))
    except EstoeError as exc:
        connection.send_bytes(b"-" + exc.code.encode("ascii"))
    except Exception:
        connection.send_bytes(b"-provider")
    finally:
        connection.close()


class AWSProvider:
    def __init__(
        self,
        profile: str | None = None,
        region: str | None = None,
        *,
        deadline: float = PROVIDER_DEADLINE,
        worker: Callable = _worker,
    ) -> None:
        self.profile = profile
        self.region = region
        self.deadline = deadline
        self.worker = worker

    def fetch(self, secret: str) -> str:
        # A process boundary bounds SDK client construction, credential resolution, retries,
        # and the read itself. A timed-out thread would keep running after the CLI returns.
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(
            target=self.worker, args=(sender, secret, self.profile, self.region), daemon=True
        )
        started = False
        try:
            process.start()
            started = True
            sender.close()
            if not receiver.poll(self.deadline):
                raise EstoeError("timeout")
            message = receiver.recv_bytes(MAX_SECRET_BYTES + 1)
            if message.startswith(b"+"):
                return message[1:].decode("utf-8")
            code = message[1:].decode("ascii") if message.startswith(b"-") else "provider"
            raise EstoeError(code)
        except (OSError, EOFError, UnicodeError):
            raise EstoeError("provider") from None
        finally:
            receiver.close()
            sender.close()
            if started:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join()
                process.close()
