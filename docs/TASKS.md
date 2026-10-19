# Tasks

Statuses: todo, in-progress, blocked, done, waived. Done means the stated checks were
executed; waived is an explicit owner risk acceptance, not a passing check.

| ID | Priority | Status | Task | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| T-01 | P0 | done | Local requirements and CLI scaffold | owner request | SSD directory, project docs, installed help/version, offline scaffold tests, local commit |
| T-02 | P0 | done | Record implementation choices | owner proceed instruction | Python/argparse, python-dotenv with interpolate=False, macOS/Linux, caps and overwrite policy documented; license remains a publication gate |
| T-03 | P0 | done | JSON validator and dotenv encoder | T-02 | R-04–R-06 round-trip/rejection cases pass without exposing input values |
| T-04 | P0 | done | Git/destination safety and atomic writer | T-02 | R-08–R-10 tests cover permissions, failure, symlinks, observed changes, cooperative lock, atomic create non-clobber, Git tracking/ignores and disabled macOS ownership |
| T-05 | P0 | done | AWS read adapter and export use case | T-03, T-04 | R-01–R-03, R-07, R-11–R-14 pass with stub clients and no live reads |
| T-06 | P1 | done | Local install/package and security review | T-05 | macOS tests/build/installed-wheel smoke/audit pass; review and residual limits recorded below |
| T-06L | P1 | done | Linux verification before public release | T-06; Linux environment | GitHub CI passed all 92 tests, Ruff, build and installed CLI help/version under Python 3.12–3.14 |
| T-07 | P1 | done | Record owner-run AWS smoke verification | owner report | Owner stated estoe is working after their AWS pull; no values or identifying account/profile/selector information recorded; agent did not retrieve secrets |
| T-08 | P1 | done | Publish GitHub AWS release | owner request; MIT selected | PR #1 merged as a6a2f3e; merged-main CI/audit passed; annotated v0.1.0 tag and wheel/source GitHub release published |
| MC-01 | P0 | done | Azure/GCP adapters and provider-specific CLI validation | owner request | MC-01–MC-05 offline tests pass; AWS commands unchanged |
| MC-02 | P0 | done | End-to-end manual setup/testing guides | MC-01 | Separate guides match actual flags/auth contracts; shell blocks syntax-checked only |
| MC-03 | P1 | done | Local package/audit/security verification | MC-01, MC-02 | 171 offline macOS tests, Ruff, wheel/source build, installed help, dependency audit and sensitive-diff review passed; new Linux CI execution pending |
| MC-04 | P1 | waived | Owner-run Azure/GCP sandbox testing | owner report/waiver | GCP pull/preview owner-reported successful; Azure live testing waived, not passed; no identifiers/values recorded |
| RC-01 | P1 | done | Suppress SDK warnings as well as logging | owner release-readiness request | 81 provider tests passed; warning canaries stay off stdout/stderr on success/failure, including warnings-as-errors; filters restored; Ruff passed |
| RC-02 | P1 | waived | Complete Azure live smoke test | explicit owner waiver | Owner chose to skip; no live Azure result claimed; GCP pull/preview owner-reported successful |
| RC-03 | P1 | done | Refresh beginner-friendly release documentation | RC-02 | 37 documentation/CLI tests passed; shell syntax, local links, example options and sample output checked offline; Ruff passed |
| RC-04 | P1 | todo | Run multi-cloud Linux PR CI | branch push/PR approved | Python 3.12–3.14 CI and dependency audit pass before merge; no merge/tag/upload authorized |
| RC-05 | P1 | todo | Prepare stable 0.2.0 metadata/changelog | preceding release gates | Version, lockfile, package smoke and changelog agree; no tag/upload without approval |
| RC-06 | P1 | todo | Improve safe validation feedback | owner UX request | Fixed actionable validation categories, no payload/key disclosure, preservation and CLI tests |

Historical AWS release preparation: owner selected MIT. Version was 0.1.0; Linux CI verifies built-wheel
help, pull help, and version. Local macOS tests remain 92 passed. Dependency audit passed;
tracked-file secret scan findings were reviewed as fixed error text and synthetic fixtures.
The owner-run AWS result is a smoke report, not exhaustive live-provider validation.

Linux release verification: [PR CI run](https://github.com/alibacelonia/estoe/actions/runs/39220646870)
passed all three Python versions; [dependency audit](https://github.com/alibacelonia/estoe/actions/runs/39220646924)
passed. Public source is delivered through PR #1, preserving the local implementation commits.

AWS release complete: [v0.1.0](https://github.com/alibacelonia/estoe/releases/tag/v0.1.0).
[Merged-main CI](https://github.com/alibacelonia/estoe/actions/runs/39220829200) and
[audit](https://github.com/alibacelonia/estoe/actions/runs/39220829168) passed before tagging.
The release wheel/source archives were checked for dotenv/credential paths; none were
included. PyPI publication, remote rulesets/settings, and any additional live reads were
not performed as part of this release.

Azure/GCP implementation is now owner-authorized development scope. Raw mode, Windows ACL
support and multi-secret mapping remain future candidates. GitHub push/release was authorized for AWS v0.1;
new live reads, cloud changes, and package-registry publication still need separate approval.
The owner subsequently approved pushing the reviewed multi-cloud branch and opening a PR
for Linux CI only. Merge, tag/release, PyPI upload and remote settings remain unauthorized.

## Scaffold verification (2026-10-19)

Executed locally on macOS / Python 3.14.3: `uv sync`, Ruff formatting/lint, pytest
(6 passed), source/wheel build, and installed-wheel `pull --help` from outside the source
directory. The locked development dependency export passed pip-audit with no known
vulnerabilities. Workflow files are prepared; remote CI has not run because no remote exists.
No live AWS requests or secret writes were performed.

## AWS feature verification (2026-10-19)

- macOS / Python 3.14.3: 92 offline tests passed; Ruff format/lint, source/wheel build,
  installed-wheel `pull --help` outside the source directory, and locked dependency audit passed.
- Generated only synthetic output in temporary test directories. Verified the actual SSD
  reports ownership disabled and the final preflight rejects it with `filesystem`.
- Code review covered input boundaries, fixed error messages, SDK isolation/bounds, Git
  checks, file permissions, create-only non-clobber, and cleanup. Residual same-user overwrite
  races, ACLs, interrupted publication/cleanup, SDK credential helpers, and storage semantics
  are documented in SECURITY and ADR-004–006.
- Linux was not executed: Docker is installed but its daemon is unavailable. Remote CI,
  live AWS tests, cloud changes, and publication have not been run. No live secret was fetched.

## Azure/GCP development verification (2026-10-19)

- Python 3.14.3/macOS: 171 offline tests passed, including all prior AWS tests; no live
  Azure/GCP/AWS reads or credential login commands were executed.
- Ruff format/lint, 0.2.0.dev0 source/wheel build, installed-wheel provider help, and locked
  dependency audit passed. SDK client construction and GCP protobuf/checksum are checked
  offline. Error canaries, provider routing, invalid flag/scope/endpoint rejection, preview,
  private export and destination preservation have regression tests.
- Both detailed guides' nine shell blocks passed bash syntax validation only. Cloud
  account permissions, propagation, network access, costs and cleanup require owner-run
  verification. The synthetic JSON fixture is checked by tests.
- Review covered shared worker extraction, SDK logging/error suppression, explicit Azure
  identity/URL constraints, GCP ADC resource scoping and CRC32C, plus unchanged filesystem
  safeguards. Secret scan findings were synthetic selectors, fixed error text, and an
  intentionally rejected fake userinfo URL; no live values are included.
- This branch is prepared for local manual testing. New Linux CI, remote publication,
  release tagging and PyPI upload were not performed in this implementation pass.

## Multi-cloud release readiness

- Owner-reported GCP pull and preview succeeded on macOS. No values or real identifiers
  are recorded. The owner waived live Azure testing; offline coverage is not a live pass.
- README now separates the published AWS-only version from the multi-cloud checkout and
  explains installation, login differences, JSON input, Git safety, preview, export and
  consuming the file step by step. Related requirements, architecture and guides agree.
- Documentation tests check shell syntax without executing cloud commands, local links,
  literal CLI examples and the sample JSON-to-dotenv result. The focused documentation
  and CLI suite passed 37 tests; Ruff lint/format and diff whitespace checks passed.
