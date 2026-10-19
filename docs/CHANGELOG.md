# Changelog

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
