# estoe

**Secret to Env.** Generate local `.env` files from cloud secret stores.

Released: AWS v0.1.0. Development: v0.2.0.dev0 adds Azure Key Vault and Google Secret Manager.
The owner reported a successful AWS pull on macOS; Azure/GCP live tests are pending.
Automated tests use synthetic data.

## Installation

With Python 3.12+ and uv, install the tagged GitHub release:

```bash
uv tool install "git+https://github.com/alibacelonia/estoe.git@v0.1.0"
estoe --help
estoe pull --help
```

This release is distributed through GitHub; no PyPI publication is claimed.

For Azure/GCP, use the development checkout and `uv sync --locked`, then `uv run estoe`.
The v0.1.0 install command above remains AWS-only until the next release is published.

## Local development

Python 3.12+, uv, Git, and macOS/Linux are required. macOS also needs diskutil (built in).
Run from this directory:

```bash
uv sync --locked
uv run estoe --help
uv run estoe --version
uv run estoe pull --help
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv build
```

To install the CLI locally from this checkout:

```bash
uv tool install .
estoe --help
estoe pull --help
```

## Usage

```bash
estoe pull --provider aws --secret example/dev/app --profile sandbox --region us-east-1
estoe pull --provider aws --secret example/dev/app --profile sandbox --output .env.local
estoe pull --provider aws --secret example/dev/app --preview
```

Development Azure/GCP examples (run from this checkout):

```bash
uv run estoe pull --provider azure --secret estoe-test-app \
  --vault-url https://example-vault.vault.azure.net/ --output .env.azure
uv run estoe pull --provider gcp --secret estoe-test-app \
  --project example-project --output .env.gcp
```

| Provider | Authentication | Required resource options |
| --- | --- | --- |
| AWS | Default credential chain or `--profile` | `--secret`; optional `--region` |
| Azure | Existing Azure CLI login; optional `--tenant-id` | `--vault-url`, `--secret` name |
| GCP | Application Default Credentials (ADC) | `--project`, `--secret` ID |

`--provider` is always required. AWS flags are rejected with Azure/GCP; vault/tenant flags
are Azure-only, project is GCP-only. Azure uses the latest version in a public-cloud vault;
GCP reads `projects/PROJECT/secrets/SECRET/versions/latest` and verifies CRC32C. Regional GCP
secrets and Azure sovereign/custom endpoints are not supported. All use the same JSON
contract and file safeguards. Shared flags: `--output`, `--preview`, `--overwrite`,
`--allow-unignored`. No automatic login or secret discovery is performed.

Follow the detailed guides to create synthetic secrets, set up read access, and test:

- [Azure: vault creation through preview/export verification](docs/TESTING_AZURE.md)
- [GCP: project/API setup through ADC and export verification](docs/TESTING_GCP.md)

The commands in those guides create cloud resources and change IAM if you choose to run
them. Review the targets/costs first; the implementation agent has not performed those steps.

Each adapter expands one flat JSON secret's string values into separate dotenv variables,
preserving key names. `--profile` selects existing named AWS credentials; when omitted the
SDK default chain applies. `--region` overrides profile/SDK region configuration.
Users manage credentials and SSO login themselves. No access keys are accepted as flags.

Preview still fetches a secret and may incur cloud charges; it displays only key names and
counts. It performs the same output-path checks as a normal pull. Values are never printed.

The output defaults to `.env`; use `--output .env.local` to change it. An existing file requires
interactive confirmation or `--overwrite`. Tracked files are always refused. Unignored files
inside Git are refused unless you pass `--allow-unignored`; prefer adding your own ignore rule.
Outside a Git worktree, a warning explains that ignore protection cannot be checked.

The output directory must already exist, be owned by you, and not be group/world writable.
Symlink components, special files, and hard-linked destinations are rejected. Files are
created with POSIX mode 0600. macOS volumes must enforce ownership: the CLI refuses volumes
with "Ignore ownership on this volume" enabled. You can keep this project on the SSD and
use `--output /absolute/path/on/a/private/volume/.env` for generated secrets. The CLI never
changes mount settings. See [security boundaries](docs/SECURITY.md).

## Credentials and IAM

Configure credentials yourself using the AWS credential chain, for example a named profile
and an existing SSO session (`aws sso login --profile sandbox`, if applicable). estoe does
not log in, modify credentials, list secrets, or create resources. Explicit `--profile` and
`--region` select the boto3 session; omitted values follow SDK configuration.

Grant `secretsmanager:GetSecretValue` on only the intended secret ARN. For a customer-managed
KMS key, also authorize `kms:Decrypt` on that key as required by its policy. Placeholder-only
examples live in [docs/iam](docs/iam/). Use an authorized account; each pull, including preview,
can incur Secrets Manager/KMS charges and leaves a normal AWS audit event.

## Secret content and dotenv format

The selected SecretString must be a nonempty flat JSON object of strings:

```json
{"APP_MODE":"development","SERVICE_URL":"https://example.com","EMPTY":""}
```

Keys match `[A-Za-z_][A-Za-z0-9_]*` and remain unchanged. Output keys are sorted. Duplicate
keys, nesting, arrays, non-string values, binary secrets, NUL, and invalid Unicode fail
without replacing output. Secret content is capped at 64 KiB; output at 256 KiB.

The format is tested with **python-dotenv 1.x, with interpolation disabled**. In the consuming
Python application, install python-dotenv and load explicitly:

```python
from dotenv import load_dotenv

load_dotenv(".env", interpolate=False)
```

This preserves literal `${...}` expressions and escaped multiline content. Other dotenv
loaders may behave differently. Never execute or shell-source the file; keep plaintext
secrets out of Git, shared directories, backups, and synchronization tools where possible.

SDK retrieval is bounded by a 15-second worker deadline plus process startup/cleanup, with
at most 2 SDK attempts for AWS/Azure; GCP automatic API retries are disabled (one explicit
access call). Authentication may perform additional requests. Git and filesystem checks
have separate short timeouts. Operational
failures exit 1 with a fixed error code/message, argument errors exit 2, and success exits 0.
After interruption or an error, inspect the selected destination before retrying: a completed
atomic publication can survive an interruption immediately afterward.

## Project documents

- [Requirements](docs/PROJECT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decisions](docs/DECISIONS.md)
- [Task plan](docs/TASKS.md)
- [Security](docs/SECURITY.md)
- [Changelog](docs/CHANGELOG.md)

Source and release artifacts: [alibacelonia/estoe](https://github.com/alibacelonia/estoe).

## License

[MIT](LICENSE).
