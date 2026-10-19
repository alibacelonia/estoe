# estoe requirements

## Status and purpose

Local MVP implementation, 2026-10-19. Owner confirmed the name `estoe`,
JSON-key expansion as default, `--profile`, useful `--help`, and SSD project location.
Owner authorized feature implementation. Python/uv/argparse and macOS/Linux are used with
the concrete encoding and filesystem decisions below; no live reads or publication are authorized.

Developers should be able to retrieve one explicitly selected cloud secret and generate
local configuration without manually copying values. Public examples must be fictional.

## Command contract

`estoe pull --provider aws --secret example/dev/app --profile sandbox --region us-east-1`

- Required: `--provider aws`, `--secret` (exact name/full ARN).
- Optional: `--profile` (SDK credential chain by default), `--region` (profile/SDK default),
  `--output` (`.env` by default), `--preview`, and `--overwrite`.
- `--allow-unignored` explicitly acknowledges writing an unignored destination; Git-tracked
  destinations are always rejected. Preview and overwrite are mutually exclusive.
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
| R-08 | Refuse overwrite unless explicitly authorized. | Existing file preserved; prompt before retrieval in a terminal, or require --overwrite noninteractively. Detect changes to destination identity/content metadata before publication; serialize cooperating estoe writers. See the same-user race boundary below. |
| R-09 | Enforce destination and Git safety. | Reject symlinks (including parent traversal), special files, directories, tracked files, and missing parents. Unignored Git destinations require a dedicated explicit acknowledgment; never modify .gitignore. No shell used for Git checks. |
| R-10 | Publish private files atomically. | POSIX temp/final files are 0600 from creation; create-only publication cannot clobber a concurrent file. Authorized replacement is atomic. Failures before publication leave existing output intact and clean temp files; no secret backup. Reject macOS volumes with ownership disabled. |
| R-11 | Protect values on all diagnostics paths. | Canary tests prove stdout/stderr/debug/errors contain no values or credentials. Stable categories replace raw SDK/JSON exceptions. No telemetry, persistent secret cache, or logging of payload objects. |
| R-12 | Bound requests and content. | A worker bounds provider execution to 15 seconds plus process startup/cleanup, with 2 total SDK attempts, 64 KiB fetched content, and 256 KiB rendered output; tests cover limit enforcement. Git/filesystem preflight time is separate. |
| R-13 | Keep tests offline. | Socket-denial guard, fake SDK, synthetic secrets, and temporary destinations cover all above failures; no AWS account/model required. |
| R-14 | Document least privilege. | IAM examples use placeholder exact secret ARN with GetSecretValue; optional KMS Decrypt scoped to a customer-managed key. No credentials or real identifiers in examples. |
| R-15 | Ship an installable CLI. | Built wheel installs in a fresh environment; help/version work outside the source tree; package checks, formatting, lint, offline tests, and dependency audit pass. |

Implementation is verified through offline tests and local packaging. The owner reported
a successful AWS pull on macOS; agent verification did not retrieve live secrets. Linux
execution is a remote CI gate for this release.

## Out of scope

Azure/GCP implementations in v0.1; whole-secret/raw mode; multi-secret discovery/merging;
automatic refresh; cloud writes/IAM provisioning; deployment; shell execution; stdout or
clipboard secret export; automatic login; Windows confidentiality guarantees; real data in
fixtures; private reference-code redistribution.

## Implementation decisions and remaining approval

Python/uv/argparse, macOS/Linux first, 15-second provider limit, explicit overwrite and Git
acknowledgment are used. The supported consumer is python-dotenv 1.x with
`interpolate=False`; double-quoted values use its documented escapes, including multiline
values, while dollar expressions remain literal. Universal dotenv/shell compatibility is
not promised. python-dotenv is a development/test dependency; consumers install it separately.

The output parent must be owned by the caller and not group/world writable. On macOS,
diskutil must confirm ownership enforcement. The SSD may store the project even when
ownership is disabled, but secret output must use another ownership-enforcing volume.
Git and diskutil (macOS) are required for preflight. No system setting is changed automatically.

MIT license was explicitly selected by the owner for the public release.

## Authorization boundary

Requirements, implementation, tests, and local commits are authorized. Separate approval is required for live
secret retrieval, cloud changes, remote/package creation/publication, and destructive actions.
Generated dotenv files are plaintext; the CLI cannot prevent OS users, backups, sync software,
or downstream applications with access from exposing them. Managed-runtime memory erasure
is not guaranteed. POSIX replacement has no portable compare-and-swap primitive: the lock
coordinates estoe writers and checks catch observed changes, but another same-user program
can race the final check. Such programs, privileged users, permissive inherited ACLs, and
hostile shared/synchronized filesystems are outside this confidentiality boundary. A
post-publication interrupt/cleanup error may leave the fully written file in place.
