# Security posture

This version is a local CLI scaffold; it performs no cloud reads or dotenv writes.
Planned controls are requirements, not implemented security claims.

Use existing credentials/SSO. No command-line credential flags, telemetry, raw errors, secret
logging, caches, clipboard output, or automatic shell sourcing are planned. Output `.env`
files are plaintext, ignored by Git, and intended to have POSIX mode 0600.

Do not put real values, account IDs, internal URLs, resource names, credentials, or private
customer/employer code in this public project. Tests use synthetic data; live tests require
explicit approval and authorized synthetic sandbox resources. No AWS/IAM changes are implied.

Before release, verify encoding, permissions, symlink/race protection, diagnostics canaries,
Git checks, and failure cleanup. No guarantee is made for backups, sync tools, memory erasure,
or downstream applications. Windows needs ACL design and tests before equivalent support.

License and a private vulnerability-reporting channel must be selected before publication.
