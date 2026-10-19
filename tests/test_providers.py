import time
import warnings

import boto3
import pytest
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
from botocore.stub import Stubber

from estoe.errors import EstoeError
from estoe.providers import AWSProvider, _worker, read_aws, send_result


class Client:
    def __init__(self, response=None, error=None):
        self.response = response if response is not None else {"SecretString": '{"A":"synthetic"}'}
        self.error = error
        self.closed = False

    def get_secret_value(self, **kwargs):
        assert kwargs == {"SecretId": "example/dev/app", "VersionStage": "AWSCURRENT"}
        if self.error:
            raise self.error
        return self.response

    def close(self):
        self.closed = True


class Session:
    region_name = "us-east-1"

    def __init__(self, client):
        self.backend = client

    def client(self, service, config):
        assert service == "secretsmanager"
        assert config.retries["total_max_attempts"] == 2
        assert config.connect_timeout == 2
        assert config.read_timeout == 3
        return self.backend


def test_exact_api_and_profile_region():
    client = Client()

    def factory(**kwargs):
        assert kwargs == {"profile_name": "sandbox", "region_name": "us-east-1"}
        return Session(client)

    assert read_aws("example/dev/app", "sandbox", "us-east-1", factory) == '{"A":"synthetic"}'
    assert client.closed


def test_inherited_profile_region_defaults():
    def factory(**kwargs):
        assert kwargs == {"profile_name": None, "region_name": None}
        return Session(Client())

    read_aws("example/dev/app", None, None, factory)


def test_real_sdk_stubber_without_network():
    session = boto3.Session(
        aws_access_key_id="synthetic", aws_secret_access_key="synthetic", region_name="us-east-1"
    )
    client = session.client("secretsmanager")
    with Stubber(client) as stub:
        stub.add_response(
            "get_secret_value",
            {"SecretString": '{"A":"synthetic"}'},
            {"SecretId": "example/dev/app", "VersionStage": "AWSCURRENT"},
        )
        assert (
            read_aws("example/dev/app", None, None, lambda **kwargs: Session(client))
            == '{"A":"synthetic"}'
        )
        stub.assert_no_pending_responses()


@pytest.mark.parametrize(
    ("aws_code", "expected"),
    [
        ("AccessDeniedException", "access_denied"),
        ("DecryptionFailure", "access_denied"),
        ("ResourceNotFoundException", "not_found"),
        ("ThrottlingException", "throttled"),
        ("ExpiredTokenException", "credentials"),
        ("UnrecognizedClientException", "credentials"),
        ("InvalidSignatureException", "credentials"),
        ("UnknownException", "provider"),
    ],
)
def test_safe_sdk_errors(aws_code, expected):
    client = Client(
        error=ClientError(
            {"Error": {"Code": aws_code, "Message": "synthetic-sensitive-canary"}}, "GetSecretValue"
        )
    )
    with pytest.raises(EstoeError) as error:
        read_aws("example/dev/app", None, None, lambda **kwargs: Session(client))
    assert error.value.code == expected
    assert "synthetic-sensitive-canary" not in str(error.value)
    assert client.closed


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (NoCredentialsError(), "credentials"),
        (ProfileNotFound(profile="synthetic"), "configuration"),
    ],
)
def test_session_construction_errors(failure, expected):
    def factory(**kwargs):
        raise failure

    with pytest.raises(EstoeError) as error:
        read_aws("example/dev/app", None, None, factory)
    assert error.value.code == expected


def test_missing_region_before_client():
    session = Session(Client())
    session.region_name = None
    with pytest.raises(EstoeError) as error:
        read_aws("example/dev/app", None, None, lambda **kwargs: session)
    assert error.value.code == "configuration"


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"SecretBinary": b"synthetic"}, "binary_secret"),
        ({}, "invalid_content"),
        ({"SecretString": 5}, "invalid_content"),
        ({"SecretString": "x" * 65537}, "content_limit"),
    ],
)
def test_response_validation(response, expected):
    with pytest.raises(EstoeError) as error:
        read_aws("example/dev/app", None, None, lambda **kwargs: Session(Client(response)))
    assert error.value.code == expected


# Spawned test workers use no SDK and do not connect to any network.
def successful_worker(connection, secret, profile, region):
    connection.send_bytes(b'+{"A":"synthetic"}')
    connection.close()


def timed_out_worker(connection, secret, profile, region):
    time.sleep(2)


def crashed_worker(connection, secret, profile, region):
    connection.close()


def failed_worker(connection, secret, profile, region):
    connection.send_bytes(b"-access_denied")
    connection.close()


def oversized_worker(connection, secret, profile, region):
    connection.send_bytes(b"+" + b"x" * 65537)
    connection.close()


def test_isolated_fetch():
    assert AWSProvider(worker=successful_worker).fetch("example") == '{"A":"synthetic"}'


@pytest.mark.parametrize(
    ("worker", "deadline", "expected"),
    [
        (timed_out_worker, 0.2, "timeout"),
        (crashed_worker, 5, "provider"),
        (failed_worker, 5, "access_denied"),
        (oversized_worker, 5, "provider"),
    ],
)
def test_worker_failures_are_bounded(worker, deadline, expected):
    started = time.monotonic()
    with pytest.raises(EstoeError) as error:
        AWSProvider(worker=worker, deadline=deadline).fetch("example")
    assert error.value.code == expected
    assert time.monotonic() - started < 6


def test_worker_suppresses_arbitrary_exception(monkeypatch):
    monkeypatch.setattr("estoe.providers.logging.disable", lambda level: None)

    class Pipe:
        messages = []

        def send_bytes(self, message):
            self.messages.append(message)

        def close(self):
            pass

    def fail(*args):
        raise ValueError("synthetic-sensitive-canary")

    monkeypatch.setattr("estoe.providers.read_aws", fail)
    pipe = Pipe()
    _worker(pipe, "example", None, None)
    assert pipe.messages == [b"-provider"]


@pytest.mark.parametrize("fails", [False, True])
def test_worker_suppresses_sdk_warnings_and_restores_filters(monkeypatch, capsys, fails):
    monkeypatch.setattr("estoe.providers.logging.disable", lambda level: None)

    class Pipe:
        def __init__(self):
            self.messages = []
            self.closed = False

        def send_bytes(self, message):
            self.messages.append(message)

        def close(self):
            self.closed = True

    def reader():
        warnings.warn("synthetic-sensitive-canary", UserWarning, stacklevel=1)
        if fails:
            raise EstoeError("credentials")
        return '{"A":"synthetic"}'

    # Also exercise environments using PYTHONWARNINGS=error. Suppressing an advisory
    # warning must not turn an otherwise valid read into a provider failure.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        original_filters = warnings.filters[:]
        pipe = Pipe()
        send_result(pipe, reader)
        assert warnings.filters == original_filters
    assert pipe.messages == ([b"-credentials"] if fails else [b'+{"A":"synthetic"}'])
    assert pipe.closed
    output = capsys.readouterr()
    assert output.out == output.err == ""
