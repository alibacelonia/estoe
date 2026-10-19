from __future__ import annotations

import socket

import pytest

from estoe.cli import main


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network access is forbidden in offline tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


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


def test_missing_required_arguments_are_usage_errors(capsys):
    with pytest.raises(SystemExit) as error:
        main(["pull"])
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_scaffold_pull_never_creates_output(tmp_path, capsys):
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
        == 1
    )
    assert not output.exists()
    assert "not implemented" in capsys.readouterr().err
