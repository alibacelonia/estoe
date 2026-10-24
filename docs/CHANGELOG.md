# Changelog

## 0.2.1 — 2026-10-24

- eMudhra TLS remediation: require certifi>=2026.10.19, lock 2026.10.23, require
  patched uv, pin CI uv 0.13.5, and update the publisher action's pip/certifi/sigstore.
  Offline trust-store regression checks and environment/container update guidance added.
- Correct package installation documentation now that estoe is available on PyPI.

## 0.2.0 — 2026-10-19

- Prepared release-gated PyPI Trusted Publishing workflow with reusable CI/audit, stable
  tag/version/main ancestry guard, strict metadata checks and isolated wheel smoke.
  Upload is disabled until owner setup/enablement and release approval. No upload performed.
- Added a beginner-friendly publishing guide, pending PyPI link in README, and package
  project URLs for GitHub repository, issues, documentation, changelog and PyPI.

- Azure Key Vault reader using the existing Azure CLI identity, required vault URL,
  optional tenant UUID, latest-version reads, endpoint validation and safe errors.
- GCP Secret Manager reader using ADC, explicit project/secret ID, latest-version reads
  over REST, CRC32C verification, UTF-8 validation and safe errors.
- Shared worker isolation and existing output safeguards for all providers; cross-provider
  CLI options are rejected. AWS commands remain compatible and provider remains required.
- Detailed Azure/GCP synthetic-secret provisioning, IAM/authentication and manual testing
  guides, plus a fictional JSON fixture. No cloud setup or live reads performed by the agent.
- Suppress Python SDK warnings as well as logging during isolated reads, including when
  the environment treats warnings as errors.
- Beginner-friendly README covering provider login differences, JSON input, safe preview,
  private output, application loading and troubleshooting; offline documentation checks.
- Owner reported successful GCP pull/preview on macOS. Azure live validation was explicitly
  waived, not passed; actual Azure credentials, permissions and networking remain unverified.
- Published multi-cloud version 0.2.0 on GitHub and PyPI.
- Actionable, fixed JSON validation explanations for syntax, root shape, duplicate keys,
  variable names, non-string values, NUL and Unicode; retain `invalid_content` and exit 1.
  No offending key/value or raw parser exception is disclosed. Help and guides explain
  common mistakes; regression tests cover output preservation for all three providers.

## 0.1.0 — 2026-10-19

First AWS release: one JSON secret to a private dotenv file, explicit profiles/regions,
key-only preview, and guarded overwrite. The owner reported a successful macOS AWS pull;
no secret values, account IDs, profile names, or real selectors are recorded here.

- Implemented AWS pull using existing named profiles/credential chain, explicit region,
  bounded isolated SDK execution, and safe error codes.
- Added strict JSON expansion, deterministic literal dotenv encoding, key-only preview,
  confirmation/overwrite control, Git safeguards, private atomic file publication, and
  macOS ownership-enforcement checks. Automated verification remains offline.

- Independent SSD project with requirements, architecture, decisions, task plan, and security
  posture.
- Installable argparse CLI scaffold with help/version and documented pull flags, including
  --profile. Pull explicitly reports unimplemented behavior without AWS access or writes.
- Offline CLI tests, packaging configuration, and CI/audit workflow definitions.
