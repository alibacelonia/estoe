from contextlib import nullcontext
from types import SimpleNamespace

import google_crc32c
import pytest
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.identity import CredentialUnavailableError
from google.api_core import exceptions as gcp_errors
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.cloud.secretmanager_v1.types import AccessSecretVersionResponse

from estoe.azure_provider import AzureProvider, _azure_worker, read_azure, valid_vault_url
from estoe.errors import EstoeError
from estoe.gcp_provider import GCPProvider, _gcp_worker, read_gcp
from estoe.providers import send_result

CANARY = "synthetic-sensitive-canary"
CONTENT = '{"APP_MODE":"development","TOKEN":"synthetic-sensitive-canary"}'
VAULT = "https://example-vault.vault.azure.net/"


class AzureClient:
    def __init__(self, value=CONTENT, error=None):
        self.value = value
        self.error = error
        self.calls = []

    def get_secret(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error
        return SimpleNamespace(value=self.value)


def azure_factories(client):
    def credential_factory(**kwargs):
        assert kwargs == {"tenant_id": "", "process_timeout": 5}
        return nullcontext("synthetic-credential")

    def client_factory(**kwargs):
        assert kwargs == {
            "vault_url": VAULT,
            "credential": "synthetic-credential",
            "retry_total": 1,
            "connection_timeout": 2,
            "read_timeout": 3,
            "logging_enable": False,
        }
        return nullcontext(client)

    return credential_factory, client_factory


def test_azure_exact_read():
    client = AzureClient()
    assert read_azure("estoe-dev-app", VAULT, None, *azure_factories(client)) == CONTENT
    assert client.calls == [(("estoe-dev-app",), {"logging_enable": False})]


def test_azure_tenant_forwarding_and_real_credential():
    from azure.identity import AzureCliCredential

    tenant = "00000000-0000-0000-0000-000000000000"
    with AzureCliCredential(tenant_id=tenant, process_timeout=5) as credential:
        assert credential is not None  # Construction is offline; no get_token invocation.

    def factory(**kwargs):
        assert kwargs["tenant_id"] == tenant
        return nullcontext("synthetic-credential")

    _, clients = azure_factories(AzureClient())
    assert read_azure("estoe-dev-app", VAULT, tenant, factory, clients) == CONTENT


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ClientAuthenticationError(CANARY), "credentials"),
        (CredentialUnavailableError(CANARY), "credentials"),
        (ResourceNotFoundError(CANARY), "not_found"),
        (ServiceRequestError(CANARY), "provider"),
    ],
)
def test_azure_error_mapping(error, expected):
    with pytest.raises(EstoeError) as result:
        read_azure("estoe-dev-app", VAULT, None, *azure_factories(AzureClient(error=error)))
    assert result.value.code == expected
    assert CANARY not in str(result.value)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "credentials"),
        (403, "access_denied"),
        (404, "not_found"),
        (408, "timeout"),
        (429, "throttled"),
        (500, "provider"),
        (504, "timeout"),
    ],
)
def test_azure_http_errors(status, expected):
    failure = HttpResponseError(CANARY)
    failure.status_code = status
    with pytest.raises(EstoeError) as result:
        read_azure("estoe-dev-app", VAULT, None, *azure_factories(AzureClient(error=failure)))
    assert result.value.code == expected
    assert CANARY not in str(result.value)


def test_azure_constructor_failure_is_safe():
    def fail(**kwargs):
        raise CredentialUnavailableError(CANARY)

    with pytest.raises(EstoeError) as result:
        read_azure("estoe-dev-app", VAULT, None, fail)
    assert result.value.code == "credentials"
    assert CANARY not in str(result.value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "invalid_content"),
        (5, "invalid_content"),
        ("x" * 65537, "content_limit"),
        ("\ud800", "invalid_content"),
    ],
)
def test_azure_payload_bounds(value, expected):
    with pytest.raises(EstoeError) as result:
        read_azure("estoe-dev-app", VAULT, None, *azure_factories(AzureClient(value)))
    assert result.value.code == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://example-vault.vault.azure.net",
        "https://example.com",
        "https://example-vault.vault.azure.net.evil.example",
        "https://user:pass@example-vault.vault.azure.net",
        "https://localhost",
        "https://example-vault.vault.azure.net:443",
        "https://example-vault.vault.azure.net/path",
        "https://example-vault.vault.azure.net?x=y",
        "https://example-vault.vault.azure.net#fragment",
        "https://example--vault.vault.azure.net",
        "https://example-vault.vault.azure.net\n",
    ],
)
def test_azure_unsafe_endpoints_rejected_before_client(url):
    assert not valid_vault_url(url)

    def forbidden(**kwargs):
        pytest.fail("credential/client invoked")

    with pytest.raises(EstoeError):
        read_azure("estoe-dev-app", url, None, forbidden, forbidden)


def response(data=None, checksum=None):
    data = CONTENT.encode() if data is None else data
    return AccessSecretVersionResponse(
        payload={
            "data": data,
            "data_crc32c": google_crc32c.value(data) if checksum is None else checksum,
        }
    )


class GCPClient:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else response()
        self.error = error
        self.calls = []

    def access_secret_version(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def gcp_factory(client):
    def factory(**kwargs):
        assert kwargs == {"transport": "rest"}
        return nullcontext(client)

    return factory


def test_gcp_exact_read_and_checksum():
    client = GCPClient()
    assert read_gcp("estoe-dev-app", "example-project", gcp_factory(client)) == CONTENT
    assert client.calls == [
        {
            "request": {"name": "projects/example-project/secrets/estoe-dev-app/versions/latest"},
            "retry": None,
            "timeout": 5,
        }
    ]


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (DefaultCredentialsError(CANARY), "credentials"),
        (RefreshError(CANARY), "credentials"),
        (gcp_errors.Unauthenticated(CANARY), "credentials"),
        (gcp_errors.PermissionDenied(CANARY), "access_denied"),
        (gcp_errors.NotFound(CANARY), "not_found"),
        (gcp_errors.ResourceExhausted(CANARY), "throttled"),
        (gcp_errors.DeadlineExceeded(CANARY), "timeout"),
        (gcp_errors.FailedPrecondition(CANARY), "configuration"),
        (gcp_errors.InvalidArgument(CANARY), "configuration"),
        (gcp_errors.ServiceUnavailable(CANARY), "provider"),
    ],
)
def test_gcp_safe_errors(failure, expected):
    with pytest.raises(EstoeError) as result:
        read_gcp("estoe-dev-app", "example-project", gcp_factory(GCPClient(error=failure)))
    assert result.value.code == expected
    assert CANARY not in str(result.value)


def test_gcp_adc_failure_during_construction():
    def fail(**kwargs):
        raise DefaultCredentialsError(CANARY)

    with pytest.raises(EstoeError) as result:
        read_gcp("estoe-dev-app", "example-project", fail)
    assert result.value.code == "credentials"


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (response(checksum=1), "integrity"),
        (response(b"\xff"), "invalid_content"),
        (response(b"x" * 65537), "content_limit"),
        (SimpleNamespace(), "invalid_content"),
        (SimpleNamespace(payload=SimpleNamespace(data="not-bytes")), "invalid_content"),
    ],
)
def test_gcp_bad_payload(result, expected):
    with pytest.raises(EstoeError) as error:
        read_gcp("estoe-dev-app", "example-project", gcp_factory(GCPClient(result)))
    assert error.value.code == expected


@pytest.mark.parametrize(
    ("project", "secret"),
    [
        ("../other", "safe"),
        ("example-project", "../secret"),
        ("https://example.com", "safe"),
        ("example-project", "secret/versions/1"),
    ],
)
def test_gcp_scope_validation_before_client(project, secret):
    def forbidden(**kwargs):
        pytest.fail("client invoked")

    with pytest.raises(EstoeError):
        read_gcp(secret, project, forbidden)


def test_new_adapters_use_shared_isolation(monkeypatch):
    calls = []

    def run(*args):
        calls.append(args)
        return CONTENT

    monkeypatch.setattr("estoe.azure_provider.run_isolated", run)
    monkeypatch.setattr("estoe.gcp_provider.run_isolated", run)
    assert AzureProvider(VAULT).fetch("estoe-dev-app") == CONTENT
    assert GCPProvider("example-project").fetch("estoe-dev-app") == CONTENT
    assert calls == [
        (_azure_worker, "estoe-dev-app", VAULT, None),
        (_gcp_worker, "estoe-dev-app", "example-project"),
    ]


@pytest.mark.parametrize(
    "worker,reader_path,options",
    [
        (_azure_worker, "estoe.azure_provider.read_azure", (VAULT, None)),
        (_gcp_worker, "estoe.gcp_provider.read_gcp", ("example-project",)),
    ],
)
def test_cloud_worker_diagnostics_are_value_free(monkeypatch, worker, reader_path, options):
    monkeypatch.setattr("estoe.providers.logging.disable", lambda level: None)

    class Pipe:
        messages = []

        def send_bytes(self, message):
            self.messages.append(message)

        def close(self):
            pass

    def fail(*args):
        raise RuntimeError(CANARY)

    monkeypatch.setattr(reader_path, fail)
    pipe = Pipe()
    worker(pipe, "estoe-dev-app", *options)
    assert pipe.messages == [b"-provider"]


def test_shared_worker_rejects_oversized_reader_result(monkeypatch):
    monkeypatch.setattr("estoe.providers.logging.disable", lambda level: None)
    messages = []
    pipe = SimpleNamespace(send_bytes=messages.append, close=lambda: None)
    send_result(pipe, lambda: "x" * 65537)
    assert messages == [b"-content_limit"]


def test_installed_sdk_client_construction_is_offline():
    from azure.identity import AzureCliCredential
    from azure.keyvault.secrets import SecretClient
    from google.auth.credentials import AnonymousCredentials
    from google.cloud.secretmanager import SecretManagerServiceClient

    with (
        AzureCliCredential(tenant_id="", process_timeout=5) as credential,
        SecretClient(
            vault_url=VAULT,
            credential=credential,
            retry_total=1,
            connection_timeout=2,
            read_timeout=3,
            logging_enable=False,
        ) as client,
    ):
        assert callable(client.get_secret)  # No request or get_token is made.
    with SecretManagerServiceClient(transport="rest", credentials=AnonymousCredentials()) as client:
        assert callable(client.access_secret_version)
