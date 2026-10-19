# Publish estoe to PyPI

This guide is for the repository owner. Creating a workflow is not the same as
publishing a package. The first upload and account/environment setup are separate,
explicit owner actions. No upload, API-token creation or cloud login was performed
while implementing this workflow.

## What happens automatically?

`.github/workflows/publish-pypi.yml` runs on PRs, manual requests and published GitHub
releases. It reuses the existing Linux Python 3.12–3.14 tests and dependency audit,
builds a wheel and source archive, runs strict Twine metadata checks, and smoke-tests
the installed CLI outside the checkout. The workflow's build artifact is named
`pypi-distributions` and is retained for seven days.

Only a stable **published GitHub release** can reach the upload job. Drafts,
prereleases, ordinary pushes, PRs and manual workflow runs cannot publish. The
release tag must match `pyproject.toml`, point to the checked-out commit, and that
commit must be reachable from `origin/main`. Only the upload job has OIDC token
permission; it downloads this run's built artifacts and does not check out or run
project source. External actions in this workflow are pinned to commit SHAs.

Uploads also require the repository variable `PYPI_PUBLISH_ENABLED` to be exactly
`true`. It is intentionally unset/disabled initially. Configure the approval
environment before enabling it; a name in YAML alone does not require human approval.

## 1. Prepare your PyPI account

1. Sign up/sign in at [PyPI](https://pypi.org/) and complete its account security
   requirements, including two-factor authentication.
2. Confirm you control the project name. A missing package page does **not** reserve
   `estoe` or guarantee the name will be accepted at upload time.
3. For this first package, use [pending Trusted Publisher registration](https://pypi.org/manage/account/publishing/).
   If you already own the PyPI project, use that project's **Manage → Publishing**.
4. Choose GitHub and enter these exact values:

| Field | Value |
| --- | --- |
| PyPI project name (pending publisher only) | `estoe` |
| GitHub owner | `alibacelonia` |
| Repository | `estoe` |
| Workflow filename | `publish-pypi.yml` (not the full path) |
| Environment | `pypi` |

If the name belongs to someone else, stop: do not publish under an unrelated name
or advertise their package. Agree on a new name first and update metadata/docs/tests.
A pending publisher creates the project only after its first successful upload.
Do not paste PyPI passwords, recovery codes, API tokens or OIDC tokens into this repo.

## 2. Configure the GitHub approval environment

In **alibacelonia/estoe → Settings → Environments**:

1. Create an environment named exactly `pypi`.
2. Add yourself (or a trusted maintainer) as a **required reviewer**. For a solo
   owner who initiates releases, leave “Prevent self-review” off so you can approve
   your own release job. Confirm the protection actually saved.
3. Restrict deployment refs to selected **tags**, pattern `v*`. The workflow checks
   stable version syntax and main ancestry too; it will not upload a prerelease.
4. Where available, disable administrator bypass of environment protection.

Do this before registering/enabling a working upload path. If your GitHub plan or
repository configuration does not support the required protection, stop and agree
on an alternative approval gate before enabling uploads. Repository administrators
can change policy; workflow checks do not defend against a trusted admin rewriting
the workflow or approval settings.

## 3. Merge the PR and do a validation-only run

Review and merge the publishing PR after required checks pass. In **Actions →
Package and publish → Run workflow**, select `main` and run it.

Expected: tests, audit, package checks and wheel smoke pass; **publish is skipped**.
Download the `pypi-distributions` artifact to inspect the wheel/source inventory and
metadata before approving a real release. This manual run cannot upload, even if
the enable variable is set.

For local validation from the checkout:

```bash
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Use a clean checkout/output directory for packaging. `uv build` followed by
`uvx --from twine==7.0.0 twine check --strict dist/*` validates distributions.
`uv run python scripts/smoke_wheel.py` expects exactly one current-version wheel in
`dist/` and tests help/version outside the source tree. If old builds are present,
move the exact old artifacts aside after reviewing them; do not blindly delete files.

## 4. Explicitly enable publishing

Only after the publisher, tag restrictions and reviewer gate are configured:

1. Open **Settings → Secrets and variables → Actions → Variables**.
2. Add a **repository variable**, not a secret: `PYPI_PUBLISH_ENABLED` = `true`.
3. Do not create `PYPI_API_TOKEN`; this workflow uses short-lived OIDC credentials.

Changing this variable enables future eligible release uploads, subject to the
environment approval. Setting it to `false` prevents future jobs from entering the
publish step; cancel an already running/waiting job separately if necessary.

## 5. Publish one version deliberately

1. Verify main's CI/audit pass and your source changes are merged. For the first
   multi-cloud release the prepared version is `0.2.0`, so its tag is `v0.2.0`.
2. Review the changelog and known limitations (Azure live testing was waived).
   For later releases, update `pyproject.toml`, `uv.lock`, changelog and versioned
   docs through a PR first; package smoke tests discover the version dynamically.
3. In GitHub **Releases → Draft a new release**, select/create the matching tag
   on the intended main commit. Review its target and release notes. Publishing
   that GitHub release starts the workflow; merely creating a draft does not.
4. After validations pass, inspect the waiting `pypi` environment job, target tag,
   commit and build artifact. Approve it only when you intend a public upload.
5. Verify the upload job succeeds and [PyPI's estoe page](https://pypi.org/project/estoe/)
   shows the expected version and links back to
   [alibacelonia/estoe](https://github.com/alibacelonia/estoe).

Once the package is confirmed available, test installation from PyPI in an isolated
environment with `uv tool install estoe==0.2.0` and check `estoe --version` and help.
Do not test by retrieving real secrets. Update README release status to published
only after verification. PyPI is public distribution, not a place to store secrets.

## Troubleshooting and recovery

- **Publish skipped:** PRs/manual runs always skip it. For a stable release, check
  the repository enable variable, repository identity and release type.
- **Tag/version or ancestry error:** fix the release selection or prepare a new
  version normally. Never move a published tag or bypass the guard to make it pass.
- **Multiple wheels:** start from a clean checkout/output; do not upload stale artifacts.
- **Waiting for approval:** a configured environment reviewer must approve the job.
- **OIDC / invalid publisher:** check owner/repo/workflow filename/environment exactly
  match PyPI. Do not work around this by committing a long-lived token.
- **Filename/version already exists:** PyPI files cannot be overwritten. Review a
  partial upload before retrying; there is no automatic `skip-existing` behavior.
  Use a new version for a corrected release rather than deleting/reusing a filename.
- **Bad published release:** a Git revert does not remove a PyPI package. Consider
  yanking the affected release and publishing a corrected new version after review.
  Deletion, yanking and credential/publisher changes require explicit owner decisions.

TestPyPI is a separate service/account/publisher. No TestPyPI upload path is included
in this initial workflow. Local tests and PR CI validate without publishing; an
end-to-end registry upload remains untested until explicitly approved and performed.

## Official references

- [PyPI: create a project using Trusted Publishing](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [PyPI: publisher configuration and approval environments](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [PyPI: tokenless upload permissions](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [Python packaging: GitHub Actions publishing](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
