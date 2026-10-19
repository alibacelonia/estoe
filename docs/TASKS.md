# Tasks

Statuses: todo, in-progress, blocked, done. Done means the stated checks were executed.

| ID | Priority | Status | Task | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| T-01 | P0 | done | Local requirements and CLI scaffold | owner request | SSD directory, project docs, installed help/version, offline scaffold tests, local commit |
| T-02 | P0 | done | Record implementation choices | owner proceed instruction | Python/argparse, python-dotenv with interpolate=False, macOS/Linux, caps and overwrite policy documented; license remains a publication gate |
| T-03 | P0 | done | JSON validator and dotenv encoder | T-02 | R-04–R-06 round-trip/rejection cases pass without exposing input values |
| T-04 | P0 | done | Git/destination safety and atomic writer | T-02 | R-08–R-10 tests cover permissions, failure, symlinks, observed changes, cooperative lock, atomic create non-clobber, Git tracking/ignores and disabled macOS ownership |
| T-05 | P0 | done | AWS read adapter and export use case | T-03, T-04 | R-01–R-03, R-07, R-11–R-14 pass with stub clients and no live reads |
| T-06 | P1 | done | Local install/package and security review | T-05 | macOS tests/build/installed-wheel smoke/audit pass; review and residual limits recorded below |
| T-06L | P1 | todo | Linux verification before public release | T-06; Linux environment | Run full tests, packaging and installed help under Linux; CI definitions prepared but no remote configured |
| T-07 | P1 | blocked | Synthetic sandbox live test | T-06; run approval | Owner authorizes exact secret/account/run bounds; safe result, no values committed/logged |
| T-08 | P1 | blocked | Create public repository/package and release | owner approval; license | Reviewed commits, green remote checks, ruleset, version tag, release |

Azure/GCP adapters, raw mode, Windows ACL support, and multi-secret mapping are post-MVP
candidates requiring separate requirements. No cloud or remote actions are authorized now.

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
