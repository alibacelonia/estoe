from __future__ import annotations

import pytest

from estoe.cli import main


@pytest.mark.parametrize("arguments", [["--help"], ["pull", "--help"], ["--version"]])
def test_help_and_version_exit_successfully(arguments, capsys):
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 0
    assert "estoe" in capsys.readouterr().out


def test_pull_help_explains_profile_and_safety(capsys):
    with pytest.raises(SystemExit):
        main(["pull", "--help"])
    output = capsys.readouterr().out
    for phrase in ("--profile", "--region", "--preview", "plaintext", "SSO", "charges"):
        assert phrase in output
    assert "JSON object with string values" in output
    assert "KEY=value" in output


def test_missing_required_arguments_are_usage_errors(capsys):
    with pytest.raises(SystemExit) as error:
        main(["pull"])
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_pull_writes_with_profile(tmp_path, capsys, monkeypatch):
    class FakeProvider:
        def __init__(self, profile, region):
            assert profile == "sandbox"
            assert region is None

        def fetch(self, secret):
            assert secret == "example/dev/app"
            return '{"APP_MODE":"synthetic-value"}'

    monkeypatch.setattr("estoe.cli.AWSProvider", FakeProvider)
    output = tmp_path / ".env"
    assert (
        main(
            [
                "pull",
                "--provider",
                "aws",
                "--secret",
                "example/dev/app",
                "--profile",
                "sandbox",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert output.read_text() == 'APP_MODE="synthetic-value"\n'
    captured = capsys.readouterr()
    assert "synthetic-value" not in captured.out + captured.err


def test_preview_only_shows_keys(tmp_path, monkeypatch, capsys):
    class Fake:
        def fetch(self, secret):
            return '{"TOKEN":"synthetic-canary"}'

    monkeypatch.setattr("estoe.cli.AWSProvider", lambda *args: Fake())
    output = tmp_path / ".env"
    assert (
        main(
            [
                "pull",
                "--provider",
                "aws",
                "--secret",
                "example/dev/app",
                "--output",
                str(output),
                "--preview",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "TOKEN" in captured.out
    assert "synthetic-canary" not in captured.out + captured.err
    assert not output.exists()


def test_unexpected_exception_is_value_free(tmp_path, monkeypatch, capsys):
    def fail(*args):
        raise ValueError("synthetic-sensitive-canary")

    monkeypatch.setattr("estoe.cli.AWSProvider", fail)
    assert (
        main(
            [
                "pull",
                "--provider",
                "aws",
                "--secret",
                "example/dev/app",
                "--output",
                str(tmp_path / ".env"),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "synthetic-sensitive-canary" not in captured.out + captured.err


def test_empty_selector_is_usage_error(monkeypatch):
    monkeypatch.setattr("estoe.cli.AWSProvider", lambda *args: pytest.fail("provider invoked"))
    with pytest.raises(SystemExit) as error:
        main(["pull", "--provider", "aws", "--secret", " "])
    assert error.value.code == 2
