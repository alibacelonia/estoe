# Security posture

Automated verification uses offline synthetic tests. The owner reported a successful
AWS pull on macOS. The agent did not retrieve live secrets; the owner-run result is not a
claim of exhaustive live validation. GitHub distributes this release; PyPI is not configured.
Azure/GCP implementation is on the development branch with no owner-run live verification yet.

Use existing credentials/SSO. No command-line credential flags, telemetry, raw errors, secret
logging, caches, clipboard output, or automatic shell sourcing are implemented. Output `.env`
files are plaintext with mode 0600; tracked files are rejected and unignored files require
explicit acknowledgment. SDK errors are translated to fixed messages, including during
session construction. Worker SDK logging is disabled. stdout never contains values.

Do not put real values, account IDs, internal URLs, resource names, credentials, or private
customer/employer code in this public project. Tests use synthetic data; live tests require
explicit approval and authorized synthetic sandbox resources. No AWS/IAM changes are implied.

Tests cover encoding with interpolation disabled, permissions, symlinks, observed file/parent
changes, atomic create-only non-clobber, Git checks, diagnostics canaries, and failure cleanup.
Review evidence in TASKS; tests are not a formal proof of confidentiality.

On macOS, diskutil must confirm ownership enforcement on the destination mount. Volumes
with ownership disabled are rejected for secret output. The CLI does not enable ownership
or change system settings. Use an ownership-enforcing output directory.

The parent must be owned by the caller, with no group/world write bits. A pinned directory
descriptor prevents symlink redirection; file identity/content metadata is checked before
publication. Directory flock serializes cooperating estoe processes. POSIX replacement lacks
a portable compare-and-swap primitive, so an uncooperative same-user process can race the final
check. Inherited ACLs, privileged users, hostile filesystems, backups/sync tools, core dumps,
memory erasure, and downstream applications remain outside the confidentiality boundary.
Avoid directories with permissive ACLs. Crashes after publication may leave the completed
output, and storage failures can prevent temporary-file cleanup; inspect private temp files
after such failures. Windows requires separate ACL design and tests.

The provider uses a spawned process and a private bounded pipe. Its 15-second deadline covers
credential resolution and SDK calls, with startup/cleanup overhead. SDK credential helpers
are trusted user configuration and may spawn subprocesses of their own. Killing the worker
does not cancel already received AWS requests or guarantee termination of independent helpers.

AWS permissions: GetSecretValue for exactly the selected secret, plus KMS Decrypt for a
customer-managed key if needed. See placeholder policies in `docs/iam/`. No cloud write
operation exists. Logs/CloudTrail may include secret selector metadata on AWS's side;
avoid sensitive information in resource names and command history.

## Azure/GCP development adapters

- Azure: an existing Azure CLI login, optionally scoped by tenant UUID. Only HTTPS public
  Key Vault vault URLs are accepted; custom endpoints, ports, userinfo and non-root paths
  are refused. The SDK's challenge-resource validation is left enabled. estoe calls only
  get_secret; the testing principal should have Key Vault Secrets User at the dedicated
  vault scope. Setup uses different privileges and is never performed by estoe.
- GCP: existing ADC, not gcloud's active CLI login alone. --project identifies the secret's
  project. One global latest version is read; CRC32C/UTF-8 are verified before parsing. Use
  Secret Manager Secret Accessor on the individual secret, with quota-project service-usage
  permission when required. No credential files or service-account keys are created.
- Both use the same isolated 15-second worker and fixed error codes. SDK HTTP logging is
  disabled; GCP uses REST to avoid native gRPC diagnostic output outside Python logging.
  Azure SDK may invoke the installed Azure CLI; trusted credential helper behavior remains
  outside the payload-logging boundary. No login flow or fallback account is chosen by estoe.
- Local tests strip AWS/Azure/GCP credential-selection environment variables and deny socket
  connections. Cloud SDKs are faked, except for offline construction/protobuf checks.
  Manual setup commands in the guides require cloud write/IAM permissions but are not part
  of the CLI. Test using only examples/synthetic-secret.json; never replace that fixture
  with real credentials.

## Reporting vulnerabilities

Do not include secret values, generated dotenv files, or credentials in public issues.
Use GitHub private vulnerability reporting when enabled in the repository's Security tab.
If it is unavailable, contact the maintainer privately rather than posting sensitive details.
