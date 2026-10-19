# estoe

**Secret to Env.** Turn one cloud secret into a local `.env` file without copying
secret values by hand. The multi-cloud version supports AWS Secrets Manager,
Azure Key Vault, and Google Secret Manager.

**Release status:** published GitHub release `v0.1.0` supports AWS only. This
checkout prepares `0.2.0` (not yet published), with Azure/GCP added. The owner reported successful AWS
pull and GCP pull/preview on macOS. Azure has offline tests, but no live test;
the owner waived that release gate. This is not verification of live Azure
authentication, permissions, or networking. Linux CI passed the initial multi-cloud
PR revision on Python 3.12–3.14; subsequent changes must pass again before merging.

## Before you start

You need Python 3.12+, uv, Git, and macOS or Linux. Windows is not supported yet.
macOS also needs the built-in `diskutil` command for file-safety checks.
Your cloud identity must already have read access to the secret you select.

The secret must contain a **JSON object whose values are all strings**:

```json
{"APP_MODE":"development","API_URL":"https://example.com","API_TOKEN":"synthetic-test-value"}
```

For that fictional example, estoe writes:

```dotenv
API_TOKEN="synthetic-test-value"
API_URL="https://example.com"
APP_MODE="development"
```

Never put real values in command arguments, Git, screenshots, or issue reports.
estoe reads secrets; it does not create them or log you in.

## 1. Install the version you want

### Released version: AWS only

```bash
uv tool install "git+https://github.com/alibacelonia/estoe.git@v0.1.0"
estoe --help
estoe pull --help
```

This installs the tagged GitHub release. No PyPI publication is claimed; do not
assume `pip install estoe` installs this project.

### Multi-cloud development version: AWS, Azure, GCP

Use the multi-cloud branch or its PR checkout:

```bash
git clone --branch feature/azure-gcp-providers https://github.com/alibacelonia/estoe.git
cd estoe
uv sync --locked
uv run estoe --version
uv run estoe pull --help
```

Run the examples below from that directory using `uv run estoe`. This selects the
checkout, not an older globally installed `estoe`. The branch is development code,
not a published stable release.

## 2. Choose a provider and authenticate

Replace the example resource names with your own authorized test resources.
Never pass passwords or access tokens as flags.

| Provider | Which login does estoe use? | Which resource options do I need? |
| --- | --- | --- |
| AWS | Existing credentials; optional `--profile sandbox` selects a named profile | `--secret` name/ARN; optional `--region` |
| Azure | Existing Azure CLI (`az login`) session; optional `--tenant-id` selects a tenant | `--vault-url` and `--secret` name |
| GCP | Application Default Credentials (ADC), not just a regular gcloud login | `--project` and `--secret` ID |

For AWS SSO, refresh your existing session yourself with
`aws sso login --profile sandbox` when needed. Without `--profile`, AWS uses its
default credential chain. Without `--region`, the SDK/profile must supply one.
GCP `--project` selects the secret's project, not the login identity or quota project.

New to Azure or GCP? Start with the complete setup guides:

- [Azure: create a synthetic secret, configure permissions, and test](docs/TESTING_AZURE.md)
- [GCP: create a synthetic secret, configure ADC, and test](docs/TESTING_GCP.md)

Those guides include resource creation and IAM changes for you to review and run.
Cloud resources and reads may cost money. estoe never performs setup automatically.

## 3. Check output safety, then preview

Use an existing directory owned by you and not writable by other users. Inside a
Git repository, add your destination to your own `.gitignore` first, for example
`.env.local`. This repository already ignores `.env` and `.env.*`.
Never use a tracked file for output.

Choose **one** command for your provider:

```bash
# AWS
uv run estoe pull --provider aws --secret example/dev/app \
  --profile sandbox --region us-east-1 --output .env.local --preview

# Azure
uv run estoe pull --provider azure --secret estoe-test-app \
  --vault-url https://example-vault.vault.azure.net/ --output .env.local --preview

# GCP
uv run estoe pull --provider gcp --secret estoe-test-app \
  --project example-project --output .env.local --preview
```

For the fictional JSON above, preview prints only:

```text
Preview: 3 variable(s)
API_TOKEN
API_URL
APP_MODE
```

Preview writes no file, but **does read the cloud secret** and may incur charges.
It checks the selected output path too. Secret values are never printed by estoe.

## 4. Write the file

Run your chosen command again **without `--preview`**. For example:

```bash
uv run estoe pull --provider aws --secret example/dev/app \
  --profile sandbox --region us-east-1 --output .env.local
```

Expected success for three variables:

```text
Wrote 3 variable(s) to the selected output (mode 0600).
```

Mode `0600` means only the owning user has POSIX read/write permissions. The file
still contains plaintext secrets: keep it out of shared folders, backups, and sync
tools where possible. Do not paste its contents into terminals or support tickets.

If the file exists, estoe asks before replacing it in an interactive terminal.
In scripts, deliberately pass `--overwrite` only when replacement is intended.
`--preview` and `--overwrite` cannot be combined.

## 5. Load the file in your application

The supported consumer is **python-dotenv 1.x with interpolation disabled**.
Install python-dotenv in your application's environment separately, then use:

```python
from dotenv import load_dotenv

load_dotenv(".env.local", interpolate=False)
```

This keeps dollar expressions such as `${TOKEN}` literal. Other dotenv loaders
may parse escapes differently. **Never execute or shell-source the file.**

## Options and limits

Run `uv run estoe pull --help` for all options. With the released installation,
use `estoe pull --help` instead.

- `--provider` is always required; there is no default provider.
- `--output` defaults to `.env`. Provider-specific flags cannot be mixed.
- `--allow-unignored` bypasses only the Git-ignore requirement. Prefer fixing your
  ignore rule. Tracked files are always refused, even with this flag.
- Outside a Git worktree, estoe warns that Git-ignore protection cannot be checked.
- Keys match `[A-Za-z_][A-Za-z0-9_]*`; output is sorted and keys stay unchanged.
  Empty strings work. Numbers must be quoted, for example `"PORT":"8000"`.
- Duplicate keys, nesting, arrays, non-string values, binary secrets, NUL, and
  invalid Unicode fail before writing. Content is capped at 64 KiB; encoded output
  at 256 KiB. One secret is read per command; existing files are not merged.
- Azure supports public-cloud vaults and the latest version only. GCP supports
  global secrets and `versions/latest`, not regional secrets or custom endpoints.
- Retrieval has a 15-second worker deadline plus startup/cleanup. AWS/Azure allow
  at most two SDK attempts; GCP automatic API retries are disabled. Authentication
  may make additional requests. Git/filesystem checks have separate short timeouts.

## Troubleshooting

Exit codes: `0` success, `2` invalid arguments, `1` operational failure. Errors are
deliberately value-free; raw SDK warnings and exceptions are not shown.

| Error | What to check |
| --- | --- |
| `invalid_content` | Read the explanation after the code: JSON validation distinguishes syntax, shape, duplicate keys, names, string types, NUL and Unicode. No offending key/value is displayed. |
| `credentials` | Refresh the correct login. GCP needs ADC; Azure needs Azure CLI. |
| `access_denied` | Check this secret's read permission, identity, and IAM propagation; do not grant broad admin just to read. |
| `not_found` | Check the secret name and selected vault/project/region. |
| `filesystem` | On macOS, use an ownership-enforcing volume. estoe does not change volume settings. |
| `unsafe_path` | Use an existing private directory without symlink components or hard-linked destination files. |
| `tracked` / `unignored` | Choose an untracked destination and add your own ignore rule. |
| `exists` | Review the existing file, then confirm replacement or deliberately use `--overwrite`. |
| `timeout` / `throttled` | Check connectivity/quota and retry manually when appropriate. |

### Common secret-format mistakes

The cloud secret's **entire value** must be JSON, not the resulting dotenv file.
For example, store `{"PORT":"8000"}`, not `PORT=8000` or `{"PORT":8000}`.

| Mistake | How to fix it |
| --- | --- |
| `KEY=value`, single quotes, or a trailing comma | Use valid JSON with double quotes, as shown above. |
| Empty object, array, or plain string | Use a nonempty object with one or more named variables. |
| Numbers, booleans, null, nested objects or arrays | Represent each variable as a string; for example `"ENABLED":"true"`. estoe does not flatten nested data. |
| Repeated keys | Keep each key only once; estoe will not silently pick a value. |
| Names with spaces/hyphens or a leading digit | Use letters/underscores first, then letters/digits/underscores. |
| NUL characters or invalid Unicode | Correct the source text before retrying; estoe will not silently alter it. |

Correct the intended secret through your normal authorized workflow, then run preview
again. An invalid secret does not create a new output or replace an existing one.
Do not paste real secret content into a JSON-validation website or public issue.

On an external macOS drive with “Ignore ownership on this volume” enabled, choose
`--output /absolute/path/on/a/private/volume/.env.local` instead. estoe never changes
system settings. GCP quota-project setup is explained in the
[GCP guide](docs/TESTING_GCP.md#7-negative-tests-and-troubleshooting).
After an interrupt or error, check whether the destination already exists before
retrying: a completed atomic write can survive an interruption immediately afterward.
See [security boundaries](docs/SECURITY.md) for the full limitations.

## Development and permissions

From the checkout:

```bash
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv build
```

Automated tests use synthetic data and deny network access. Azure's live-test gate
was waived, not passed. Its guide remains available for voluntary sandbox testing.
AWS needs `secretsmanager:GetSecretValue` on the intended secret; a customer-managed
KMS key may also need `kms:Decrypt` on that key. See the [IAM examples](docs/iam/).
Azure/GCP least-privilege roles are in their setup guides. No telemetry, secret cache,
automatic login, or secret discovery is used.

The protected `main` branch requires PRs, passing CI/audit, an up-to-date branch and
resolved review conversations. Force pushes/deletion are blocked; no bypass actors are
configured. Reviewer approvals are optional for solo maintenance. See the
[ruleset reference](.github/rulesets/README.md). These rules do not publish releases.

## Project documents

- [Requirements](docs/PROJECT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decisions](docs/DECISIONS.md)
- [Task plan](docs/TASKS.md)
- [Security](docs/SECURITY.md)
- [Changelog](docs/CHANGELOG.md)

Source, issues, and release artifacts: [alibacelonia/estoe](https://github.com/alibacelonia/estoe).
A PyPI link will be added only after publication.

## License

[MIT](LICENSE).
