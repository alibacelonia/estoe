"""Offline checks only: never execute the cloud commands shown in documentation."""

import ast
import json
import re
import shlex
import subprocess
import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

from estoe.cli import build_parser, validate_options
from estoe.encoding import encode_env, parse_secret

ROOT = Path(__file__).resolve().parents[1]
GUIDES = [ROOT / "README.md", ROOT / "docs/TESTING_AZURE.md", ROOT / "docs/TESTING_GCP.md"]


@pytest.mark.parametrize("path", GUIDES, ids=lambda path: path.name)
def test_documentation_code_and_local_links(path):
    content = path.read_text()
    for language, code in re.findall(r"```(\w+)\n(.*?)```", content, re.DOTALL):
        if language == "bash":
            result = subprocess.run(["bash", "-n"], input=code, text=True, capture_output=True)
            assert result.returncode == 0, result.stderr
            # Validate literal estoe example options without constructing any adapters.
            for line in code.replace("\\\n", " ").splitlines():
                if line.startswith("uv run estoe pull ") and "$" not in line:
                    parser = build_parser()
                    arguments = shlex.split(line)[3:]
                    if "--help" in arguments:
                        with pytest.raises(SystemExit) as error:
                            parser.parse_args(arguments)
                        assert error.value.code == 0
                    else:
                        args = parser.parse_args(arguments)
                        validate_options(parser, args)
        elif language == "python":
            ast.parse(code)
        elif language == "json":
            json.loads(code)
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if "://" not in target and not target.startswith("#"):
            assert (path.parent / target.split("#", 1)[0]).exists(), target


def test_readme_json_example_matches_shown_dotenv():
    content = (ROOT / "README.md").read_text()
    example = re.search(r"```json\n(.*?)```", content, re.DOTALL).group(1)
    expected = re.search(r"```dotenv\n(.*?)```", content, re.DOTALL).group(1)
    assert encode_env(parse_secret(example)).decode() == expected


def test_prepared_version_matches_installation_lock_ci_and_guides():
    expected = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert version("estoe") == expected
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    assert (
        next(package["version"] for package in lock["package"] if package["name"] == "estoe")
        == expected
    )
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert workflow.count(f"estoe-{expected}-py3-none-any.whl") == 3
    for path in GUIDES:
        assert f"`{expected}`" in path.read_text()
    assert f"Unreleased — {expected}" in (ROOT / "docs/CHANGELOG.md").read_text()
