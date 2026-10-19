import json
from pathlib import Path

import pytest

from estoe.cli import main
from estoe.errors import EstoeError


@pytest.mark.parametrize(
    "arguments",
    [
        ["--provider", "azure", "--secret", "estoe-test-app"],
        ["--provider", "gcp", "--secret", "estoe-test-app"],
        ["--provider", "azure", "--secret", "estoe-test-app", "--vault-url", "http://localhost"],
        [
            "--provider",
            "azure",
            "--secret",
            "bad/name",
            "--vault-url",
            "https://example-vault.vault.azure.net",
        ],
        [
            "--provider",
            "azure",
            "--secret",
            "safe",
            "--vault-url",
            "https://example-vault.vault.azure.net",
            "--tenant-id",
            "bad",
        ],
        [
            "--provider",
            "gcp",
            "--secret",
            "safe",
            "--project",
            "example-project",
            "--profile",
            "sandbox",
        ],
        [
            "--provider",
            "gcp",
            "--secret",
            "safe",
            "--project",
            "example-project",
            "--region",
            "us-east-1",
        ],
        [
            "--provider",
            "gcp",
            "--secret",
            "safe",
            "--project",
            "example-project",
            "--tenant-id",
            "bad",
        ],
        ["--provider", "gcp", "--secret", "bad/name", "--project", "example-project"],
        ["--provider", "gcp", "--secret", "safe", "--project", "../other"],
        ["--provider", "aws", "--secret", "safe", "--project", "example-project"],
        [
            "--provider",
            "aws",
            "--secret",
            "safe",
            "--vault-url",
            "https://example-vault.vault.azure.net",
        ],
        ["--provider", "azure", "--secret", "safe", "--profile", "sandbox"],
    ],
)
def test_invalid_provider_options_never_construct_adapters(arguments, monkeypatch):
    def forbidden(*args):
        pytest.fail("provider was constructed")

    for name in ("AWSProvider", "AzureProvider", "GCPProvider"):
        monkeypatch.setattr(f"estoe.cli.{name}", forbidden)
    with pytest.raises(SystemExit) as error:
        main(["pull", *arguments])
    assert error.value.code == 2


@pytest.mark.parametrize(
    "provider,options",
    [
        ("azure", ["--vault-url", "https://example-vault.vault.azure.net/"]),
        ("gcp", ["--project", "example-project"]),
    ],
)
@pytest.mark.parametrize("preview", [False, True])
def test_cloud_provider_uses_common_export(
    provider, options, preview, tmp_path, monkeypatch, capsys
):
    content = json.dumps({"APP_MODE": "development", "TOKEN": "synthetic-sensitive-canary"})
    calls = []

    class Fake:
        def __init__(self, *args):
            calls.append(args)

        def fetch(self, secret):
            assert secret == "estoe-test-app"
            return content

    name = "AzureProvider" if provider == "azure" else "GCPProvider"
    monkeypatch.setattr(f"estoe.cli.{name}", Fake)
    output = tmp_path / ".env"
    args = [
        "pull",
        "--provider",
        provider,
        "--secret",
        "estoe-test-app",
        *options,
        "--output",
        str(output),
    ]
    if preview:
        args.append("--preview")
    assert main(args) == 0
    assert calls == (
        [("https://example-vault.vault.azure.net/", None)]
        if provider == "azure"
        else [("example-project",)]
    )
    captured = capsys.readouterr()
    assert "synthetic-sensitive-canary" not in captured.out + captured.err
    assert output.exists() is not preview
    if not preview:
        assert output.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "provider,options",
    [
        ("azure", ["--vault-url", "https://example-vault.vault.azure.net/"]),
        ("gcp", ["--project", "example-project"]),
    ],
)
@pytest.mark.parametrize("failure", ["credentials", "invalid_content", "integrity"])
def test_cloud_failures_preserve_output(provider, options, failure, tmp_path, monkeypatch, capsys):
    path = tmp_path / ".env"
    path.write_text("original")

    class Fake:
        def __init__(self, *args):
            pass

        def fetch(self, secret):
            raise EstoeError(failure)

    monkeypatch.setattr(
        f"estoe.cli.{'AzureProvider' if provider == 'azure' else 'GCPProvider'}", Fake
    )
    assert (
        main(
            [
                "pull",
                "--provider",
                provider,
                "--secret",
                "estoe-test-app",
                *options,
                "--output",
                str(path),
                "--overwrite",
            ]
        )
        == 1
    )
    assert path.read_text() == "original"
    assert failure in capsys.readouterr().err


def test_manual_fixture_is_flat_synthetic_json():
    from estoe.encoding import parse_secret

    root = Path(__file__).resolve().parents[1]
    values = parse_secret((root / "examples" / "synthetic-secret.json").read_text())
    assert values == {
        "APP_MODE": "development",
        "API_URL": "https://example.com",
        "API_TOKEN": "synthetic-test-value",
    }
