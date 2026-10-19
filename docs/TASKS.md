# Tasks

Statuses: todo, in-progress, blocked, done. Done means the stated checks were executed.

| ID | Priority | Status | Task | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| T-01 | P0 | done | Local requirements and CLI scaffold | owner request | SSD directory, project docs, installed help/version, offline scaffold tests, local commit |
| T-02 | P0 | blocked | Confirm pending product/encoding/platform choices | owner decisions | Resolve five questions in PROJECT before application implementation |
| T-03 | P0 | todo | JSON validator and dotenv encoder | T-02 | R-04–R-06 round-trip/rejection cases pass without exposing input values |
| T-04 | P0 | todo | Git/destination safety and atomic writer | T-02 | R-08–R-10 tests cover permissions, failure, symlinks, race protection, and Git tracking/ignores |
| T-05 | P0 | todo | AWS read adapter and export use case | T-03, T-04 | R-01–R-03, R-07, R-11–R-14 pass with stub clients and no live reads |
| T-06 | P1 | todo | Install/package and security review | T-05 | R-15, macOS/Linux checks, complete docs, reviewed staged changes, passing CI |
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
