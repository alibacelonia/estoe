"""Install and smoke-test the one built wheel outside the checkout; never read secrets."""

from __future__ import annotations

import subprocess
import tempfile
import tomllib
from pathlib import Path


def smoke_wheel(root: Path) -> None:
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    wheels = list((root / "dist").glob("*.whl"))
    if len(wheels) != 1 or wheels[0].name != f"estoe-{version}-py3-none-any.whl":
        raise ValueError(
            "Build exactly one estoe wheel matching pyproject.toml in a clean dist directory."
        )
    with tempfile.TemporaryDirectory(prefix="estoe-wheel-smoke-") as directory:
        for arguments in (["--help"], ["pull", "--help"], ["--version"]):
            result = subprocess.run(
                ["uvx", "--from", str(wheels[0].resolve()), "estoe", *arguments],
                cwd=directory,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if "--version" in arguments and result.stdout.strip() != f"estoe {version}":
                raise ValueError("Installed CLI version does not match package metadata.")
    print("PASS: installed wheel help, pull help and version outside source tree")


if __name__ == "__main__":
    smoke_wheel(Path.cwd())
