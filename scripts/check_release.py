"""Read-only stable-release guard. Does not create tags, commits, or packages."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

STABLE_TAG = re.compile(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()


def validate_release(root: Path, tag: str) -> None:
    if not STABLE_TAG.fullmatch(tag):
        raise ValueError("Use a stable vMAJOR.MINOR.PATCH tag; prereleases are not published.")
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    if project["name"] != "estoe" or tag != f"v{project['version']}":
        raise ValueError("Release tag must match the estoe version in pyproject.toml.")
    try:
        head = git(root, "rev-parse", "--verify", "HEAD^{commit}")
        if git(root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}") != head:
            raise ValueError("The checked-out commit must match the release tag.")
        git(root, "merge-base", "--is-ancestor", head, "refs/remotes/origin/main")
    except (subprocess.SubprocessError, OSError):
        raise ValueError(
            "Release must be tagged and reachable from origin/main; fetch full history."
        ) from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args(argv)
    try:
        validate_release(Path.cwd(), args.tag)
    except (ValueError, KeyError, OSError):
        print(
            "Release validation failed: check stable tag, project version, "
            "checkout and main ancestry.",
            file=sys.stderr,
        )
        return 1
    print("PASS: release tag, version and main ancestry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
