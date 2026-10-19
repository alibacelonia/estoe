import io
import json
import os
import random
import subprocess

import pytest
from dotenv import dotenv_values

from estoe.application import export_secret
from estoe.encoding import encode_env, parse_secret
from estoe.errors import EstoeError
from estoe.files import destination


def test_many_deterministic_encoding_combinations():
    generator = random.Random(42)
    alphabet = "aA1'\"\\\n\r\t${}#= ☃\v\f"
    for _ in range(200):
        value = "".join(generator.choice(alphabet) for _ in range(50))
        expected = {"KEY": value}
        output = encode_env(parse_secret(json.dumps(expected)))
        assert dotenv_values(stream=io.StringIO(output.decode()), interpolate=False) == expected


def test_final_create_cannot_clobber_racing_file(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    real_link = os.link

    def racing_link(source, target, **kwargs):
        path.write_text("racing-content")
        return real_link(source, target, **kwargs)

    monkeypatch.setattr("estoe.files.os.link", racing_link)
    with destination(str(path)) as target, pytest.raises(EstoeError):
        target.publish(b"synthetic")
    assert path.read_text() == "racing-content"
    assert not list(tmp_path.glob(".estoe-*"))


def test_preview_preserves_existing_output(tmp_path):
    path = tmp_path / ".env"
    path.write_text("original")

    class Fake:
        def fetch(self, secret):
            return '{"KEY":"synthetic"}'

    result = export_secret(Fake(), "example", str(path), preview=True)
    assert result.keys == ("KEY",)
    assert path.read_text() == "original"


def test_parent_permissions_changed_during_fetch(tmp_path):
    class Fake:
        def fetch(self, secret):
            tmp_path.chmod(0o777)
            return '{"KEY":"synthetic"}'

    try:
        with pytest.raises(EstoeError):
            export_secret(Fake(), "example", str(tmp_path / ".env"))
        assert not (tmp_path / ".env").exists()
    finally:
        tmp_path.chmod(0o700)


def test_git_tracking_change_during_fetch(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    path = tmp_path / ".env"

    class Fake:
        def fetch(self, secret):
            # Simulate another program making the path tracked while the read was in flight.
            path.write_text("other-program")
            subprocess.run(["git", "-C", str(tmp_path), "add", ".env"], check=True)
            return '{"KEY":"synthetic"}'

    with pytest.raises(EstoeError):
        export_secret(Fake(), "example", str(path), allow_unignored=True)
    assert path.read_text() == "other-program"


def test_private_temp_file_at_creation(tmp_path, monkeypatch):
    real_open = os.open
    seen = []

    def checked_open(path, flags, mode=0o777, **kwargs):
        descriptor = real_open(path, flags, mode, **kwargs)
        if flags & os.O_CREAT:
            seen.append(os.fstat(descriptor).st_mode & 0o777)
            assert mode == 0o600
        return descriptor

    monkeypatch.setattr("estoe.files.os.open", checked_open)
    with destination(str(tmp_path / ".env")) as target:
        target.publish(b"synthetic")
    assert seen == [0o600]


def test_git_missing_is_a_safe_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("estoe.files.check_filesystem", lambda path: None)

    def fail(*args, **kwargs):
        raise FileNotFoundError("synthetic-sensitive-canary")

    monkeypatch.setattr("estoe.files.subprocess.run", fail)
    with pytest.raises(EstoeError) as error, destination(str(tmp_path / ".env")):
        pytest.fail("git failure ignored")
    assert error.value.code == "git"
    assert "synthetic-sensitive-canary" not in str(error.value)


def test_noninteractive_existing_file_never_constructs_sdk(tmp_path, monkeypatch, capsys):
    from estoe.cli import main

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    path = tmp_path / ".env"
    path.write_text("original")
    monkeypatch.setattr(
        "estoe.providers.AWSProvider.fetch", lambda *args: pytest.fail("AWS called")
    )
    assert main(["pull", "--provider", "aws", "--secret", "example", "--output", str(path)]) == 1
    assert "exists" in capsys.readouterr().err
    assert path.read_text() == "original"


def test_interactive_confirmation_happens_before_fetch(tmp_path, monkeypatch):
    from estoe.cli import main

    path = tmp_path / ".env"
    path.write_text("original")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda message: "no")
    monkeypatch.setattr(
        "estoe.providers.AWSProvider.fetch", lambda *args: pytest.fail("AWS called")
    )
    assert main(["pull", "--provider", "aws", "--secret", "example", "--output", str(path)]) == 1
    assert path.read_text() == "original"


def test_path_parent_traversal_rejected(tmp_path):
    with pytest.raises(EstoeError), destination(str(tmp_path / ".." / ".env")):
        pytest.fail("traversal accepted")


def test_platform_rejected(tmp_path, monkeypatch):
    import estoe.files as files

    # Patch the module's os reference without changing pathlib's global platform detection.
    class Unsupported:
        name = "nt"

    monkeypatch.setattr(files, "os", Unsupported())
    with pytest.raises(EstoeError) as error, files.destination(str(tmp_path / ".env")):
        pytest.fail("platform accepted")
    assert error.value.code == "platform"


def test_symlink_ancestors_rejected(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    (tmp_path / "alias").symlink_to(actual, target_is_directory=True)
    with pytest.raises(EstoeError), destination(str(tmp_path / "alias" / ".env")):
        pytest.fail("symlink accepted")
    assert not (actual / ".env").exists()


@pytest.mark.parametrize("enabled", [False, True])
def test_macos_ownership_enforcement_is_required(tmp_path, monkeypatch, enabled):
    import plistlib

    from estoe.files import check_filesystem

    monkeypatch.setattr("estoe.files.sys.platform", "darwin")

    def result(*args, **kwargs):
        assert args[0][:3] == ["/usr/sbin/diskutil", "info", "-plist"]
        return subprocess.CompletedProcess(
            args[0], 0, plistlib.dumps({"GlobalPermissionsEnabled": enabled})
        )

    monkeypatch.setattr("estoe.files.subprocess.run", result)
    if enabled:
        check_filesystem(tmp_path)
    else:
        with pytest.raises(EstoeError) as error:
            check_filesystem(tmp_path)
        assert error.value.code == "filesystem"
