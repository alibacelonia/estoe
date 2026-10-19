# Architecture decisions

## ADR-001: Independent CLI repository

- Status: accepted (owner instruction).
- Decision: estoe lives on the SSD as a separate project. No cloud-incident-service code or
  private reference implementation is imported/copied.

## ADR-002: JSON expansion and explicit AWS profile

- Status: accepted (owner instruction).
- Decision: one JSON secret expands into separate environment variables, with `--profile`
  and comprehensive `--help`. Preserve variable names. AWS is first; Azure/GCP follow later.

## ADR-003: Python scaffold using argparse

- Status: proposed; used for the reversible scaffold.
- Decision: Python 3.12+, uv, argparse, Hatchling, pytest, and Ruff. Argparse needs no runtime
  CLI dependency. The AWS SDK is added only when the fetch adapter is implemented.

## ADR-004: Private atomic publication and explicit encoding

- Status: proposed.
- Decision: validate before retrieval, keep values out of diagnostics, create private temp
  files, and publish atomically with race protection. Define a supported dotenv parser and
  encoding contract before implementation; do not assume shell syntax is dotenv syntax.
- Consequences: safe behavior requires filesystem tests and platform limits; Windows is
  deferred until ACL confidentiality is proved.
