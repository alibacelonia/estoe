"""Azure public-cloud Key Vault adapter using an existing Azure CLI login."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from estoe.encoding import MAX_SECRET_BYTES
from estoe.errors import EstoeError
from estoe.providers import run_isolated, send_result


def valid_vault_url(value: str) -> bool:
    if any(ord(char) <= 32 or ord(char) == 127 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        return bool(
            parsed.scheme == "https"
            and re.fullmatch(r"[a-z][a-z0-9-]{1,22}[a-z0-9]\.vault\.azure\.net", parsed.netloc)
            and "--" not in parsed.netloc
            and parsed.path in {"", "/"}
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def read_azure(
    secret: str, vault_url: str, tenant_id: str | None, credential_factory=None, client_factory=None
) -> str:
    from azure.core.exceptions import (
        ClientAuthenticationError,
        HttpResponseError,
        ResourceNotFoundError,
        ServiceRequestError,
        ServiceResponseError,
    )
    from azure.identity import AzureCliCredential, CredentialUnavailableError
    from azure.keyvault.secrets import SecretClient

    if not valid_vault_url(vault_url) or not re.fullmatch(r"[A-Za-z0-9-]{1,127}", secret):
        raise EstoeError("configuration")
    credential_factory = credential_factory or AzureCliCredential
    client_factory = client_factory or SecretClient
    try:
        with (
            credential_factory(tenant_id=tenant_id or "", process_timeout=5) as credential,
            client_factory(
                vault_url=vault_url,
                credential=credential,
                retry_total=1,
                connection_timeout=2,
                read_timeout=3,
                logging_enable=False,
            ) as client,
        ):
            result = client.get_secret(secret, logging_enable=False)
            value = result.value
        if not isinstance(value, str):
            raise EstoeError("invalid_content")
        if len(value.encode("utf-8")) > MAX_SECRET_BYTES:
            raise EstoeError("content_limit")
        return value
    except (ClientAuthenticationError, CredentialUnavailableError):
        raise EstoeError("credentials") from None
    except ResourceNotFoundError:
        raise EstoeError("not_found") from None
    except HttpResponseError as exc:
        code = {
            401: "credentials",
            403: "access_denied",
            404: "not_found",
            408: "timeout",
            429: "throttled",
            504: "timeout",
        }.get(exc.status_code, "provider")
        raise EstoeError(code) from None
    except (ServiceRequestError, ServiceResponseError):
        raise EstoeError("provider") from None
    except (AttributeError, UnicodeError):
        raise EstoeError("invalid_content") from None


def _azure_worker(connection, secret: str, vault_url: str, tenant_id: str | None) -> None:
    send_result(connection, read_azure, secret, vault_url, tenant_id)


class AzureProvider:
    def __init__(self, vault_url: str, tenant_id: str | None = None) -> None:
        self.vault_url = vault_url
        self.tenant_id = tenant_id

    def fetch(self, secret: str) -> str:
        return run_isolated(_azure_worker, secret, self.vault_url, self.tenant_id)
