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

- Status: accepted for implementation following the owner's proceed instruction.
- Decision: Python 3.12+, uv, argparse, Hatchling, pytest, and Ruff. Argparse needs no runtime
  CLI dependency. The AWS SDK is added only when the fetch adapter is implemented.

## ADR-004: Private atomic publication and explicit encoding

- Status: accepted for implementation following the owner's proceed instruction.
- Decision: validate before retrieval, keep values out of diagnostics, create private temp
  files, and publish atomically. Use python-dotenv 1.x with interpolation disabled; emit
  double-quoted escaped strings. Use a directory flock for cooperating writers, pinned
  directory descriptors and metadata checks, and atomic hard-link creation to prevent
  create-only clobber. Atomic overwrite follows a final metadata check; it cannot prevent
  a hostile same-user program from racing that check. No universal race-free claim is made.
- Consequences: safe behavior requires filesystem tests and platform limits; Windows is
  deferred until ACL confidentiality is proved.

## ADR-005: Bound the SDK with an isolated process

- Status: accepted.
- Decision: construct the boto3 session/client inside a spawned worker, suppress SDK logging,
  and return only bounded SecretString bytes or a fixed error code over a private pipe.
  Stop the worker after 15 seconds and reap it; configure 2 total SDK attempts, 2-second
  connect timeout, and 3-second read timeout. No secret is passed via command-line arguments.
- Consequences: profile/SSO credential resolution is also bounded; startup and cleanup add
  small overhead. Configured SDK credential helpers are trusted user configuration and may
  themselves launch external processes; terminating the worker does not revoke remote calls
  or guarantee termination of independently launched credential helpers.

## ADR-006: Verify ownership enforcement on macOS

- Status: accepted as a security requirement.
- Context: the development SSD is APFS with ownership disabled. chmod reports 0600 but the
  mount ignores ownership, so mode checks alone cannot support the confidentiality claim.
- Decision: query diskutil's GlobalPermissionsEnabled on the destination mount and fail
  closed if false/unknown. Check parent ownership/writability and actual temp-file mode.
- Consequences: source code can stay on the SSD while output goes to an ownership-enforcing
  filesystem. Enabling volume ownership is a separate owner-approved system operation.

## ADR-007: Publish AWS v0.1 through GitHub under MIT

- Status: accepted; owner requested the release/push and explicitly selected MIT.
- Decision: publish source and built wheel/source archives on GitHub, using a feature PR
  with Linux Python 3.12–3.14 checks before the v0.1.0 tag. Package-registry publication is
  separate; no PyPI upload credentials or trusted publisher are configured.
- Consequences: installation is available from the tagged GitHub URL or wheel, while
  `pip install estoe` from PyPI is not advertised. Account/profile/selector details and
  generated dotenv content are excluded from commits and release notes.
