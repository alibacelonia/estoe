# Architecture

## Implemented components

Python 3.12+, uv, standard-library argparse, pytest, Ruff, and Hatchling packaging.
`cli.py` owns help/options, confirmation, and value-free diagnostics. `application.py`
sequences preflight, fetching, validation, encoding, and publication. `providers.py` contains
the fetch protocol and boto3 AWS adapter; `encoding.py` validates and encodes; `files.py`
owns Git checks, directory-pinned POSIX operations, and macOS mount checks. `errors.py`
defines fixed diagnostic codes/messages. No provider payload is logged.

## Data flow

```text
CLI -> export use case
         -> destination/Git preflight and overwrite approval
         -> SecretProvider.fetch(selector) -> in-memory content
         -> JSON validation and dotenv encoding
         -> private atomic file publisher
    -> safe status / classified error
```

The first adapter uses the official AWS SDK and only GetSecretValue. Profile/region select
the SDK session; credentials are managed by the user's existing credential chain. Later
Azure/GCP adapters implement the same small fetch boundary after their semantics are scoped.
No provider framework or unused adapters are added speculatively.

Encoding targets python-dotenv 1.x with `interpolate=False`, verified by round-trip tests.
Atomic hard-link create and replacement are distinct so create-only cannot overwrite a racing file.
Filesystem and Git preflight happen before fetching; destination identity is checked again
at publication. Secret values travel only in process memory, a private worker pipe, and private
output files. A directory flock serializes estoe; metadata rechecks detect observed changes.
The final overwrite check is not a portable compare-and-swap against malicious same-user writers.

The SDK worker covers credentials, session construction, request, and retries with a 15-second
deadline plus process startup/cleanup. Worker errors are fixed codes. Preview fetches and
validates without publishing. The filesystem is preflighted even in preview mode.

On macOS diskutil confirms ownership enforcement; unsupported volumes fail closed. No
volume settings are changed. Inherited ACLs and hostile same-user programs are not covered.

Tests use a fake provider and temporary paths, with network denied by default. CI covers
Python 3.12–3.14 on Linux; macOS filesystem behavior must be verified before release.
