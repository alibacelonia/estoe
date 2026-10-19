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

## ADR-008: Separate cloud readers behind the existing isolated export boundary

- Status: accepted for the owner-requested Azure/GCP implementation.
- Decision: retain the AWS import/interface and factor its worker into a shared runner.
  Add Azure/GCP modules with lazy official-SDK imports and the same fetch(secret)->str
  contract. Keep --provider explicit; validate provider-specific options before SDK access.
- Consequences: existing AWS syntax remains valid. Common JSON/encoding/preview/filesystem
  behavior stays in one path. All SDK dependencies are included in the installation; no
  extra install flags or runtime downloading is needed. The next version is 0.2.0.dev0;
  the released AWS tag and its artifacts remain unchanged.

## ADR-009: Explicit Azure CLI identity and constrained Key Vault URLs

- Status: accepted.
- Decision: use AzureCliCredential with a 5-second process timeout and optional --tenant-id.
  Require --vault-url on the public azure.net vault suffix, without userinfo/ports/query
  or non-root path. Read the latest secret via SecretClient, keep challenge-resource checks
  enabled, cap one retry, and map SDK errors to fixed messages.
- Consequences: local developers can use az login without creating client secrets. No
  environment/managed-identity fallback is implied, and sovereign clouds are deferred.
  The credential may launch the installed Azure CLI; that trusted helper is outside
  Python log suppression. The worker deadline and SDK process timeout bound normal use.

## ADR-010: GCP ADC, global resource names, and payload integrity

- Status: accepted.
- Decision: require a project ID/number and a simple secret ID; read the global latest
  version via Secret Manager's REST transport using ADC. Disable automatic API retries,
  use a 5-second request timeout plus the shared worker deadline, and verify CRC32C/UTF-8.
- Consequences: --project selects the resource, not the identity or quota project. ADC
  setup/quota configuration is managed by the user; no service-account keys are created.
  REST avoids native gRPC diagnostics bypassing Python logging. Regional endpoints and
  explicit version selection require future scope. A checksum mismatch fails closed.
