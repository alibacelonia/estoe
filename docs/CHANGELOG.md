# Changelog

## Unreleased — 0.1.0.dev0

- Implemented AWS pull using existing named profiles/credential chain, explicit region,
  bounded isolated SDK execution, and safe error codes.
- Added strict JSON expansion, deterministic literal dotenv encoding, key-only preview,
  confirmation/overwrite control, Git safeguards, private atomic file publication, and
  macOS ownership-enforcement checks. No live AWS verification or public release yet.

- Independent SSD project with requirements, architecture, decisions, task plan, and security
  posture.
- Installable argparse CLI scaffold with help/version and documented pull flags, including
  --profile. Pull explicitly reports unimplemented behavior without AWS access or writes.
- Offline CLI tests, packaging configuration, and CI/audit workflow definitions.
