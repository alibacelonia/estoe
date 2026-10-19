# estoe engineering instructions

Read `project.yaml`, `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, and `docs/TASKS.md`
before implementation. Stop and report conflicting requirements.

- Keep changes within this repository. Never copy private employer code or configuration.
- Never print, log, commit, or include secret values in errors. Use synthetic fixtures only.
- Never retrieve live secrets, provision resources, modify IAM, publish a remote/package,
  or change remote settings without explicit owner approval for the concrete action.
- Never overwrite user changes or run destructive Git operations without approval.
- Use small commits after reviewing staged changes for sensitive content. Use the owner's
  verified GitHub noreply identity, not personal email addresses.
- After remote setup, use branches and PRs; do not push directly to protected main.
- Keep tests offline and deterministic. Report only checks actually executed.
- Update tasks as work progresses; record significant decisions and their status.
- Keep CLI, use case, providers, encoding, Git checks, and filesystem operations separate.
- No arbitrary shell execution, telemetry, secret cache, or unsolicited AWS discovery.

Current authorization includes application implementation and local commits (owner request).
Live secrets, cloud changes, and publication still require separate approval.
