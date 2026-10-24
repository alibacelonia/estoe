# Architecture

## Implemented components

Python 3.12+, uv, standard-library argparse, pytest, Ruff, and Hatchling packaging.
`cli.py` owns help/options, confirmation, and value-free diagnostics. `application.py`
sequences preflight, fetching, validation, encoding, and publication. `providers.py` contains
the fetch protocol, shared isolated worker/pipe, and boto3 AWS adapter. `azure_provider.py`
uses AzureCliCredential and SecretClient; `gcp_provider.py` uses ADC and the REST Secret
Manager client, with CRC32C validation. SDK imports occur only inside reader functions.
`encoding.py` validates and encodes; `files.py`
owns Git checks, directory-pinned POSIX operations, and macOS mount checks. `errors.py`
defines fixed diagnostic codes/messages. No provider payload is logged.
JSON validation chooses a fixed, allowlisted explanation for `invalid_content`;
neither offending keys/values nor decoder exception text enters a diagnostic. The
error code and exit status remain stable. Unknown explanations fall back to the generic
message. JSON validation occurs in the parent after the bounded provider pipe returns.

## Data flow

```text
CLI -> export use case
         -> destination/Git preflight and overwrite approval
         -> SecretProvider.fetch(selector) -> in-memory content
         -> JSON validation and dotenv encoding
         -> private atomic file publisher
    -> safe status / classified error
```

The AWS adapter calls only GetSecretValue. Profile/region select the SDK session. Azure
reads exactly one latest secret through an existing CLI login; the optional tenant UUID
selects that CLI tenant. Vault URL validation accepts only HTTPS public Key Vault hosts,
without userinfo/ports/query/additional path. Azure challenge resource verification remains
enabled. GCP reads one global latest version with ADC over REST; resource selection is
explicit, UTF-8 and payload CRC32C must validate, and automatic API retries are disabled.
The CLI rejects cross-provider options before constructing adapters. There is no model,
resource discovery, cloud write port, automatic login, or user-defined provider plugin.

Encoding targets python-dotenv 1.x with `interpolate=False`, verified by round-trip tests.
Atomic hard-link create and replacement are distinct so create-only cannot overwrite a racing file.
Filesystem and Git preflight happen before fetching; destination identity is checked again
at publication. Secret values travel only in process memory, a private worker pipe, and private
output files. A directory flock serializes estoe; metadata rechecks detect observed changes.
The final overwrite check is not a portable compare-and-swap against malicious same-user writers.

The shared SDK worker covers credentials, session construction, request, and retries with a 15-second
deadline plus process startup/cleanup. Python SDK logging and warnings are suppressed in
the worker reader; actionable authentication advice is provided through fixed errors and
the testing guides rather than raw SDK diagnostics. Worker errors are fixed codes. Preview fetches and
validates without publishing. The filesystem is preflighted even in preview mode.

On macOS diskutil confirms ownership enforcement; unsupported volumes fail closed. No
volume settings are changed. Inherited ACLs and hostile same-user programs are not covered.

Tests use a fake provider and temporary paths, with network denied by default. CI covers
Python 3.12–3.14 on Linux. macOS filesystem tests and installed-package checks were executed
locally; the owner also reported a successful AWS pull. Remote Linux CI is a release gate.
The multi-cloud PR was merged and its post-merge Linux CI/audit passed. The owner
reported a successful GCP pull/preview and waived Azure live testing. Azure credentials,
permissions and network access remain unverified against a real vault. The testing guides
remain available for voluntary verification. No agent live reads were performed.

## Package delivery boundary

`ci.yml` and `dependency-audit.yml` are reusable by `publish-pypi.yml` while keeping their
existing triggers/check names for main protection. PR/manual publishing-workflow runs are
validation-only. A stable release validates its tag/version, checkout and origin/main
ancestry with a read-only standard-library script. The build job checks Twine metadata,
smokes the exact current wheel outside source, and uploads immutable per-run artifacts.
The upload job downloads only those artifacts, has OIDC permission only, runs no project
source, and uses PyPA Trusted Publishing. It requires a stable published release in this
repository plus an explicit enable variable and the owner-configured pypi environment.
The YAML does not configure environment reviewers or the PyPI account; those remain manual
prerequisites. The owner authorized the 0.2.1 release; its gated OIDC upload and fresh public PyPI
installation were verified on 2026-10-24. See TASKS for run and artifact evidence.
