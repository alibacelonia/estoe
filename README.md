# estoe

**Secret to Env.** Generate local `.env` files from cloud secret stores.

Status: requirements and CLI scaffold. Help/version work; `pull` reports that it is not
implemented and exits 1. No secrets are fetched and no dotenv files are generated yet.

## Local development

Python 3.12+ and uv are required. Run from this directory:

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

## Planned usage

```bash
estoe pull --provider aws --secret example/dev/app --profile sandbox --region us-east-1
estoe pull --provider aws --secret example/dev/app --profile sandbox --output .env.local
estoe pull --provider aws --secret example/dev/app --preview
```

The AWS MVP will expand one flat JSON secret's string values into separate dotenv variables,
preserving key names. `--profile` selects existing named AWS credentials; when omitted the
SDK default chain applies. `--region` overrides profile/SDK region configuration.
Users manage credentials and SSO login themselves. No access keys are accepted as flags.

Preview will still fetch a secret and may incur AWS charges; it displays only key names and
counts. The generated file contains plaintext secrets. Keep it out of Git and do not execute
or shell-source it. Overwrite, encoding, and file safety behavior are specified in the
requirements; they have not been implemented in this scaffold.

## Project documents

- [Requirements](docs/PROJECT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decisions](docs/DECISIONS.md)
- [Task plan](docs/TASKS.md)
- [Security](docs/SECURITY.md)
- [Changelog](docs/CHANGELOG.md)

AWS is first; Azure Key Vault and Google Secret Manager are future adapters. There is no
remote repository or public package created by this scaffold. License is pending owner
confirmation; choose one before publication.
