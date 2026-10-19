# Main branch protection

The owner authorized the active [Protect main ruleset](https://github.com/alibacelonia/estoe/rules/25403554).
`main.json` records the requested configuration; GitHub adds some default fields to its
stored representation. This file is a reference, not an automatic settings synchronizer.
Committing or reverting it does not change GitHub settings by itself.

The rules apply only to `refs/heads/main`:

- Require a pull request; direct pushes are not allowed.
- Require GitHub Actions checks `test (3.12)`, `test (3.13)`, `test (3.14)` and `audit`.
- Require the PR branch to be up to date with main and resolve review conversations.
- Block force pushes and deletion. No bypass actors are configured, including administrators.
- Require zero reviewer approvals so a solo maintainer can merge their own PR after CI.
  No code-owner review or approval of the last push is required.

Repository administrators can still edit the ruleset. Do not weaken or disable it without
owner approval. If independent reviewers join, the owner can choose to require approvals.
Feature branches remain writable; the ruleset does not merge, release or publish anything.

Read-only verification with an appropriately authenticated GitHub CLI:

```bash
gh api repos/alibacelonia/estoe/rules/branches/main
gh api repos/alibacelonia/estoe/rulesets/25403554
```

The active rules were verified through these read APIs and `main` reports protected.
No destructive push or deletion was attempted as a test. Changes and recovery of remote
policy require a deliberate settings update; a Git revert alone is not a rollback.
