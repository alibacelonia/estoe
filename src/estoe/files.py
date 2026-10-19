"""POSIX directory-pinned destination checks and private publication."""

from __future__ import annotations

import contextlib
import os
import plistlib
import secrets
import stat
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from estoe.errors import EstoeError


def check_filesystem(path: Path) -> None:
    # On macOS external volumes can ignore ownership despite reporting chmod(0600).
    if sys.platform != "darwin":
        return
    mount = path
    while not os.path.ismount(mount) and mount.parent != mount:
        mount = mount.parent
    try:
        result = subprocess.run(
            ["/usr/sbin/diskutil", "info", "-plist", str(mount)],
            capture_output=True,
            timeout=5,
            check=False,
        )
        if (
            result.returncode
            or plistlib.loads(result.stdout).get("GlobalPermissionsEnabled") is not True
        ):
            raise EstoeError("filesystem")
    except (OSError, ValueError, plistlib.InvalidFileException, subprocess.TimeoutExpired):
        raise EstoeError("filesystem") from None


def open_directory(path: Path) -> int:
    """Walk every component without following symlinks; caller owns returned fd."""
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def fingerprint(info: os.stat_result | None) -> tuple | None:
    if info is None:
        return None
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_mode,
    )


def git_check(path: Path, allow_unignored: bool) -> bool:
    """Returns True if inside Git. Fail closed on errors for a detected repository."""
    # No arbitrary GIT_* overrides or fsmonitor hooks may redirect the safety check.
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment["GIT_TERMINAL_PROMPT"] = "0"

    def run(*args: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "-C", str(path.parent), *args],
                capture_output=True,
                env=environment,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise EstoeError("git") from None

    # Presence of .git includes linked worktrees. A bare repository is also unsafe output.
    known_repository = any((parent / ".git").exists() for parent in (path.parent, *path.parents))
    result = run("rev-parse", "--is-inside-work-tree")
    if result.returncode:
        if known_repository:
            raise EstoeError("git")
        return False
    if result.stdout.strip() != b"true":
        raise EstoeError("git")
    target = f":(literal){path.name}"
    tracked = run("ls-files", "--error-unmatch", "--", target)
    if tracked.returncode == 0:
        raise EstoeError("tracked")
    if tracked.returncode != 1:
        raise EstoeError("git")
    ignored = run("check-ignore", "--quiet", "--", path.name)
    if ignored.returncode not in (0, 1):
        raise EstoeError("git")
    if ignored.returncode == 1 and not allow_unignored:
        raise EstoeError("unignored")
    return True


@dataclass(repr=False)
class Destination:
    path: Path
    directory: int
    before: os.stat_result | None
    allow_unignored: bool
    in_git: bool

    def current(self) -> os.stat_result | None:
        try:
            info = os.stat(self.path.name, dir_fd=self.directory, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid():
            raise EstoeError("unsafe_path")
        return info

    def verify(self) -> None:
        check_filesystem(self.path.parent)
        # Detect renamed/replaced parents as well as changed file identity/content metadata.
        check = open_directory(self.path.parent)
        try:
            original = os.fstat(self.directory)
            latest = os.fstat(check)
            if latest.st_uid != os.geteuid() or latest.st_mode & 0o022:
                raise EstoeError("unsafe_path")
            if (original.st_dev, original.st_ino) != (latest.st_dev, latest.st_ino):
                raise EstoeError("changed")
        finally:
            os.close(check)
        if fingerprint(self.current()) != fingerprint(self.before):
            raise EstoeError("changed")

    def publish(self, content: bytes) -> None:
        temporary = f".estoe-{secrets.token_hex(16)}.tmp"
        created = False
        try:
            self.verify()
            git_check(self.path, self.allow_unignored)
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.directory,
            )
            created = True
            with os.fdopen(descriptor, "wb") as stream:
                os.fchmod(stream.fileno(), 0o600)
                if stat.S_IMODE(os.fstat(stream.fileno()).st_mode) != 0o600:
                    raise EstoeError("filesystem")
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            self.verify()
            if self.before is None:
                # link is atomic create-if-absent; replace/rename would clobber a racing file.
                os.link(
                    temporary,
                    self.path.name,
                    src_dir_fd=self.directory,
                    dst_dir_fd=self.directory,
                    follow_symlinks=False,
                )
            else:
                os.replace(
                    temporary, self.path.name, src_dir_fd=self.directory, dst_dir_fd=self.directory
                )
        except FileExistsError:
            raise EstoeError("changed") from None
        except OSError:
            raise EstoeError("write") from None
        finally:
            if created:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(temporary, dir_fd=self.directory)


@contextlib.contextmanager
def destination(output: str, allow_unignored: bool = False) -> Iterator[Destination]:
    if os.name != "posix":
        raise EstoeError("platform")
    import fcntl

    if not output or "\0" in output or ".." in Path(output).parts:
        raise EstoeError("unsafe_path")
    path = Path(os.path.abspath(output))
    descriptor = None
    try:
        descriptor = open_directory(path.parent)
        info = os.fstat(descriptor)
        # The writer assumes the containing directory is controlled by the current user.
        if info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise EstoeError("unsafe_path")
        check_filesystem(path.parent)
        # Cooperating estoe processes serialize without creating a persistent lock file.
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise EstoeError("changed") from None
        target = Destination(path, descriptor, None, allow_unignored, False)
        target.before = target.current()
        target.in_git = git_check(path, allow_unignored)
        yield target
    except OSError:
        raise EstoeError("unsafe_path") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
