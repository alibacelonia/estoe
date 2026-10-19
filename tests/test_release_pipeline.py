"""Offline release guard and workflow contract tests; no uploads or token requests."""

import json
import re
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
GUARD = runpy.run_path(str(ROOT / "scripts/check_release.py"))
SMOKE = runpy.run_path(str(ROOT / "scripts/smoke_wheel.py"))


def git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def release_repo(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Synthetic Test")
    git(tmp_path, "config", "user.email", "synthetic@example.invalid")
    (tmp_path / "pyproject.toml").write_text('[project]\nname="estoe"\nversion="0.2.0"\n')
    git(tmp_path, "add", "pyproject.toml")
    git(tmp_path, "commit", "-m", "synthetic fixture")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(tmp_path, "tag", "v0.2.0")
    return tmp_path


def test_release_guard_accepts_tag_on_main_without_mutation(release_repo):
    before = git(release_repo, "show-ref")
    GUARD["validate_release"](release_repo, "v0.2.0")
    assert git(release_repo, "show-ref") == before
    assert git(release_repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("tag", ["v0.2.1", "v0.2.0rc1", "0.2.0", "v00.2.0", "--help", "v0.2.0;id"])
def test_release_guard_rejects_invalid_or_mismatched_tag(release_repo, tag):
    with pytest.raises(ValueError):
        GUARD["validate_release"](release_repo, tag)


def test_release_guard_rejects_commit_outside_main(release_repo):
    git(release_repo, "switch", "-c", "synthetic-branch")
    git(release_repo, "commit", "--allow-empty", "-m", "not merged")
    git(release_repo, "tag", "-f", "v0.2.0")
    with pytest.raises(ValueError, match="origin/main"):
        GUARD["validate_release"](release_repo, "v0.2.0")


def test_release_guard_rejects_checkout_different_from_tag(release_repo):
    git(release_repo, "commit", "--allow-empty", "-m", "different checkout")
    git(release_repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    with pytest.raises(ValueError, match="checked-out"):
        GUARD["validate_release"](release_repo, "v0.2.0")


@pytest.mark.parametrize("ref", ["refs/tags/v0.2.0", "refs/remotes/origin/main"])
def test_release_guard_fails_closed_on_missing_ref(release_repo, ref):
    git(release_repo, "update-ref", "-d", ref)
    with pytest.raises(ValueError, match="origin/main"):
        GUARD["validate_release"](release_repo, "v0.2.0")


def test_release_guard_cli_never_echoes_untrusted_tag(release_repo):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_release.py"),
            "--tag",
            "synthetic-sensitive-canary",
        ],
        cwd=release_repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "synthetic-sensitive-canary" not in result.stdout + result.stderr


@pytest.mark.parametrize("failure", [None, "missing", "extra", "wrong_version", "cli_version"])
def test_smoke_wheel_checks_exact_artifact_and_runs_outside_source(tmp_path, monkeypatch, failure):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="0.2.0"\n')
    dist = tmp_path / "dist"
    dist.mkdir()
    if failure != "missing":
        (dist / "estoe-0.2.0-py3-none-any.whl").touch()
    if failure == "extra":
        (dist / "other.whl").touch()
    if failure == "wrong_version":
        (dist / "estoe-0.2.0-py3-none-any.whl").rename(dist / "estoe-0.1.0-py3-none-any.whl")
    calls = []

    def fake_run(arguments, **kwargs):
        assert Path(kwargs["cwd"]).resolve() != tmp_path.resolve()
        assert arguments[:2] == ["uvx", "--from"]
        assert Path(arguments[2]).is_absolute()
        calls.append(arguments)
        return SimpleNamespace(stdout="estoe 0.1.0" if failure == "cli_version" else "estoe 0.2.0")

    monkeypatch.setattr(SMOKE["subprocess"], "run", fake_run)
    if failure:
        with pytest.raises(ValueError):
            SMOKE["smoke_wheel"](tmp_path)
    else:
        SMOKE["smoke_wheel"](tmp_path)
        assert [call[4:] for call in calls] == [["--help"], ["pull", "--help"], ["--version"]]


def test_publishing_workflow_is_release_only_tokenless_and_gated():
    workflow = yaml.load(
        (ROOT / ".github/workflows/publish-pypi.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert set(workflow["on"]) == {"pull_request", "workflow_dispatch", "release"}
    assert workflow["on"]["release"]["types"] == ["published"]
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert jobs["verify"]["uses"] == "./.github/workflows/ci.yml"
    assert jobs["audit"]["uses"] == "./.github/workflows/dependency-audit.yml"
    assert jobs["build"]["needs"] == ["verify", "audit"]
    assert jobs["publish"]["needs"] == "build"
    publish = jobs["publish"]
    for gate in (
        "github.event_name == 'release'",
        "alibacelonia/estoe",
        "!github.event.release.draft",
        "!github.event.release.prerelease",
        "vars.PYPI_PUBLISH_ENABLED == 'true'",
    ):
        assert gate in publish["if"]
    assert publish["environment"]["name"] == "pypi"
    assert publish["permissions"] == {"id-token": "write"}
    assert all("run" not in step for step in publish["steps"])
    assert (
        len(publish["steps"]) == 2
    )  # Download this run's artifacts, then publish; no checkout/build.
    assert "actions/download-artifact@" in publish["steps"][0]["uses"]
    assert "pypa/gh-action-pypi-publish@" in publish["steps"][1]["uses"]
    assert "with" not in publish["steps"][1]  # No passwords or skip-existing behavior.
    for job in (jobs["build"], publish):
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", step["uses"])
    build = jobs["build"]
    assert build["steps"][0]["with"] == {"fetch-depth": "0", "persist-credentials": "false"}
    guard = next(
        step for step in build["steps"] if step.get("name", "").startswith("Validate stable")
    )
    assert guard["env"]["RELEASE_TAG"] == "${{ github.event.release.tag_name }}"
    assert guard["run"] == 'python scripts/check_release.py --tag "$RELEASE_TAG"'
    assert "${{" not in guard["run"]
    assert any(
        step.get("run") == "uvx --from twine==7.0.0 twine check --strict dist/*"
        for step in build["steps"]
    )
    assert "secrets." not in json.dumps(workflow)
    for filename in ("ci.yml", "dependency-audit.yml"):
        reusable = yaml.load(
            (ROOT / ".github/workflows" / filename).read_text(), Loader=yaml.BaseLoader
        )
        assert "workflow_call" in reusable["on"]


def test_workflow_shell_steps_parse_without_execution():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if "run" in step:
                    result = subprocess.run(
                        ["bash", "-n"], input=step["run"], capture_output=True, text=True
                    )
                    assert result.returncode == 0, (path.name, result.stderr)
