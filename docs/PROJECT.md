# estoe requirements

## Status and purpose

Local scaffold and proposed MVP requirements, 2026-10-19. Owner confirmed the name `estoe`,
JSON-key expansion as default, `--profile`, useful `--help`, and SSD project location.
Python/uv/argparse and macOS/Linux support are working scaffold choices. Remaining product
decisions are listed below; no live reads or publication are authorized.

Developers should be able to retrieve one explicitly selected cloud secret and generate
local configuration without manually copying values. Public examples must be fictional.

## Command contract

`estoe pull --provider aws --secret example/dev/app --profile sandbox --region us-east-1`

- Required: `--provider aws`, `--secret` (exact name/full ARN).
- Optional: `--profile` (SDK credential chain by default), `--region` (profile/SDK default),
  `--output` (`.env` by default), `--preview`, and `--overwrite`.
- `estoe --help`, `estoe pull --help`, and `estoe --version` exit 0.
- Invalid/missing arguments return usage help and exit 2; operational failures exit 1.
- Help explains defaults, AWS credentials/SSO, fictional examples, plaintext output,
  preview read charges, and keeping generated files out of Git.

## Requirements and acceptance criteria

| ID | Requirement | Observable acceptance criterion |
| --- | --- | --- |
| R-01 | Validate arguments and destination before cloud access. | Invalid provider, arguments, missing required flags, or unsafe path invoke zero SDK operations and change no files. |
| R-02 | Fetch one current SecretString using GetSecretValue. | Stub verifies exact selector and AWSCURRENT behavior; no ListSecrets, discovery, cloud writes, or shell commands. SecretBinary fails explicitly. |
| R-03 | Use existing AWS credential chain/profile and region. | Explicit flags override SDK defaults; missing/expired credentials and absent region produce safe errors; no automatic login or credential edits. |
| R-04 | Expand a nonempty flat JSON object of strings. | Duplicate JSON keys, nested objects, arrays, nonstrings, invalid variable names, and NUL are rejected before writing. Empty string values work. |
| R-05 | Preserve keys and deterministic output. | Keys match `[A-Za-z_][A-Za-z0-9_]*`, remain unchanged, and sort consistently. Repeated inputs produce identical bytes. |
| R-06 | Use a documented dotenv encoding contract. | A selected parser round-trips empty strings, spaces, quotes, backslashes, Unicode, hashes, equals, dollars, and multiline values; unsupported values fail without touching output. No execution or shell sourcing. |
| R-07 | Preview shows key names/counts only. | Fetches/validates but writes nothing; no values, lengths, hashes, raw SDK payloads, or credentials appear in output. |
| R-08 | Refuse overwrite unless explicitly authorized. | Existing file preserved; prompt before retrieval in a terminal, or require --overwrite noninteractively. Concurrent destination changes invalidate approval. |
| R-09 | Enforce destination and Git safety. | Reject symlinks (including parent traversal), special files, directories, tracked files, and missing parents. Unignored Git destinations require a dedicated explicit acknowledgment; never modify .gitignore. No shell used for Git checks. |
| R-10 | Publish private files atomically. | POSIX temp/final files are 0600 from creation; create-only publication cannot clobber a concurrent file. Authorized replacement is atomic. Failure leaves existing output intact and cleans temp files; no secret backup. |
| R-11 | Protect values on all diagnostics paths. | Canary tests prove stdout/stderr/debug/errors contain no values or credentials. Stable categories replace raw SDK/JSON exceptions. No telemetry, persistent secret cache, or logging of payload objects. |
| R-12 | Bound requests and content. | Proposed 15-second overall provider deadline, 2 total attempts, 64 KiB fetched content, and 256 KiB rendered output; tests cover limit enforcement. |
| R-13 | Keep tests offline. | Socket-denial guard, fake SDK, synthetic secrets, and temporary destinations cover all above failures; no AWS account/model required. |
| R-14 | Document least privilege. | IAM examples use placeholder exact secret ARN with GetSecretValue; optional KMS Decrypt scoped to a customer-managed key. No credentials or real identifiers in examples. |
| R-15 | Ship an installable CLI. | Built wheel installs in a fresh environment; help/version work outside the source tree; package checks, formatting, lint, offline tests, and dependency audit pass. |

The scaffold only satisfies help/version and explicit unimplemented behavior; the remaining
criteria must not be represented as delivered functionality.

## Out of scope

Azure/GCP implementations in v0.1; whole-secret/raw mode; multi-secret discovery/merging;
automatic refresh; cloud writes/IAM provisioning; deployment; shell execution; stdout or
clipboard secret export; automatic login; Windows confidentiality guarantees; real data in
fixtures; private reference-code redistribution.

## Decisions requiring confirmation before implementation

1. Python/uv/argparse as the chosen stack (currently working scaffold choice).
2. Supported dotenv loader and exact multiline/dollar/interpolation behavior. `.env` syntax
   differs across consumers; universal compatibility is not promised.
3. Accept macOS/Linux first, with Windows deferred pending secure ACL behavior.
4. Accept proposed deadline/content caps and overwrite/Git acknowledgment policy.
5. Choose a license before public publication (MIT is a candidate, not yet selected).

## Authorization boundary

Requirements, scaffold, tests, and local commits are authorized. Owner approval of a concrete
scope is required for application implementation; separate approval is required for live
secret retrieval, cloud changes, remote/package creation/publication, and destructive actions.
Generated dotenv files are plaintext; the CLI cannot prevent OS users, backups, sync software,
or downstream applications with access from exposing them. Managed-runtime memory erasure
is not guaranteed.
