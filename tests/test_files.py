import os
import stat
import subprocess

import pytest

from estoe.application import export_secret
from estoe.errors import EstoeError
from estoe.files import destination


class Fake:
    calls = 0

    def fetch(self, secret):
        self.calls += 1
        return '{"TOKEN":"synthetic-canary"}'


def test_private_create_and_explicit_replace(tmp_path):
    path = tmp_path / ".env"
    fake = Fake()
    export_secret(fake, "example", str(path))
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    before = path.read_bytes()
    with pytest.raises(EstoeError) as error:
        export_secret(fake, "example", str(path))
    assert error.value.code == "exists"
    assert fake.calls == 1
    assert path.read_bytes() == before
    export_secret(fake, "example", str(path), overwrite=True)
    assert fake.calls == 2
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".estoe-*"))


def test_confirmation_declined_without_fetch(tmp_path):
    path = tmp_path / ".env"
    path.write_text("original")
    fake = Fake()
    with pytest.raises(EstoeError) as error:
        export_secret(fake, "example", str(path), confirm=lambda: False)
    assert error.value.code == "cancelled"
    assert fake.calls == 0
    assert path.read_text() == "original"


@pytest.mark.parametrize("kind", ["symlink", "parent_symlink", "directory", "fifo", "hardlink"])
def test_unsafe_destinations_never_fetch(tmp_path, kind):
    path = tmp_path / "output"
    if kind == "directory":
        path.mkdir()
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        original = tmp_path / "original"
        if kind == "parent_symlink":
            original.mkdir()
            path.symlink_to(original, target_is_directory=True)
            path = path / ".env"
        else:
            original.write_text("untouched")
            if kind == "hardlink":
                os.link(original, path)
            else:
                path.symlink_to(original)
    fake = Fake()
    with pytest.raises(EstoeError):
        export_secret(fake, "example", str(path), overwrite=True)
    assert fake.calls == 0


def test_missing_parent_and_world_writable_parent(tmp_path):
    with pytest.raises(EstoeError):
        export_secret(Fake(), "example", str(tmp_path / "missing" / ".env"))
    tmp_path.chmod(0o777)
    try:
        with pytest.raises(EstoeError):
            export_secret(Fake(), "example", str(tmp_path / ".env"))
    finally:
        tmp_path.chmod(0o700)


@pytest.mark.parametrize("existing", [False, True])
def test_racing_file_change_is_detected(tmp_path, existing):
    path = tmp_path / ".env"
    if existing:
        path.write_text("old")
    with destination(str(path)) as target:
        path.write_text("racing writer")
        with pytest.raises(EstoeError) as error:
            target.publish(b'NEW="value"\n')
        assert error.value.code == "changed"
    assert path.read_text() == "racing writer"


def test_parent_swap_is_detected(tmp_path):
    parent = tmp_path / "folder"
    parent.mkdir()
    with destination(str(parent / ".env")) as target:
        parent.rename(tmp_path / "moved")
        parent.mkdir()
        with pytest.raises(EstoeError):
            target.publish(b"synthetic")
    assert not (parent / ".env").exists()


def test_cooperating_writers_are_locked(tmp_path):
    with (
        destination(str(tmp_path / ".env")),
        pytest.raises(EstoeError),
        destination(str(tmp_path / ".env")),
    ):
        pytest.fail("lock not enforced")


@pytest.mark.parametrize("failure", ["provider", "invalid", "fsync", "replace"])
def test_failure_preserves_original_and_cleans_temp(tmp_path, monkeypatch, failure):
    path = tmp_path / ".env"
    path.write_text("original")

    class Provider:
        def fetch(self, secret):
            if failure == "provider":
                raise EstoeError("provider")
            return "not json" if failure == "invalid" else '{"A":"synthetic"}'

    def fail(*args, **kwargs):
        raise OSError("synthetic-canary")

    if failure in {"fsync", "replace"}:
        monkeypatch.setattr(f"estoe.files.os.{failure}", fail)
    with pytest.raises(EstoeError):
        export_secret(Provider(), "example", str(path), overwrite=True)
    assert path.read_text() == "original"
    assert not list(tmp_path.glob(".estoe-*"))


def git(tmp_path, *args):
    return subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)


def test_git_tracked_unignored_and_ignored(tmp_path):
    git(tmp_path, "init")
    path = tmp_path / ".env"
    fake = Fake()
    with pytest.raises(EstoeError) as error:
        export_secret(fake, "example", str(path))
    assert error.value.code == "unignored"
    assert fake.calls == 0
    export_secret(fake, "example", str(path), allow_unignored=True)
    git(tmp_path, "add", ".env")
    with pytest.raises(EstoeError) as error:
        export_secret(fake, "example", str(path), allow_unignored=True, overwrite=True)
    assert error.value.code == "tracked"
    ignored = tmp_path / ".env.local"
    (tmp_path / ".gitignore").write_text(".env.local\n")
    export_secret(fake, "example", str(ignored))
    assert ignored.exists()


def test_git_environment_does_not_redirect_checks(tmp_path, monkeypatch):
    git(tmp_path, "init")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "nonexistent"))
    with pytest.raises(EstoeError) as error:
        export_secret(Fake(), "example", str(tmp_path / ".env"))
    assert error.value.code == "unignored"
