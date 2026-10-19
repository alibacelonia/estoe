# Architecture

## Implemented scaffold

Python 3.12+, uv, standard-library argparse, pytest, Ruff, and Hatchling packaging.
`src/estoe/cli.py` parses documented flags and provides help/version. Pull exits 1 with an
explicit unimplemented message. There is no provider, encoder, writer, or AWS SDK dependency.

## Planned boundaries

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

Encoding depends on approval of a supported dotenv parser. Atomic create and replacement
need distinct implementations so a create-only invocation cannot overwrite a racing file.
Filesystem and Git preflight happen before fetching; destination identity is checked again
at publication. Secret values travel only in process memory and private output files.

Tests use a fake provider and temporary paths, with network denied by default. CI covers
Python 3.12–3.14 on Linux; macOS filesystem behavior must be verified before release.
