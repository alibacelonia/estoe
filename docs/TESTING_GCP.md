# Google Secret Manager: setup and manual estoe test

Verification status: the owner reported a successful GCP pull and key-only preview on
macOS. No account/project identifiers or secret values are recorded here. Agent checks
remain offline; this report is not exhaustive live-provider validation.

These are instructions for you to review and run, not actions performed by the agent.
Use an authorized sandbox project with billing configured. API enablement, secret creation,
and IAM bindings modify cloud state. Secret storage/access can incur charges. estoe itself
only reads one explicitly named secret version and never creates resources.

This adapter supports global secrets and uses Application Default Credentials (ADC) with
the official Python SDK. Regional Secret Manager resources are not supported in this version.

## 1. Prepare estoe and the synthetic JSON

From branch `feature/azure-gcp-providers` or a later merged checkout:

```bash
uv sync --locked
uv run estoe --version
uv run estoe pull --help
```

Expect `0.2.0` (prepared, not published) and `gcp` among provider choices. The AWS-only v0.1.0 does not support
GCP. Keep using `uv run estoe` to run this checkout, rather than an older installed command.

Install the [Google Cloud CLI](https://docs.cloud.google.com/sdk/docs/install), then check
`gcloud version`. The tracked file `examples/synthetic-secret.json` contains only three
fictional string values. Do not replace it with real secrets or commit downloaded credentials.

## 2. Select a sandbox project and authenticate the setup CLI

Create a dedicated sandbox project in the console if needed, attach billing, and record
its project ID locally. Project creation/billing setup requires your organization's normal
authorization; estoe will not perform it. An existing sandbox project is also suitable.

```bash
ESTOE_GCP_PROJECT="<YOUR_SANDBOX_PROJECT_ID>"
gcloud auth login
gcloud config set project "$ESTOE_GCP_PROJECT"
gcloud config get-value project
```

Verify the selected project. Use explicit `--project` in subsequent commands to avoid
modifying the wrong project. `gcloud auth login` authenticates setup commands, not necessarily
the Python SDK. SDK ADC is configured separately in step 5.

## 3. Enable Secret Manager and obtain setup permissions

```bash
gcloud services enable secretmanager.googleapis.com --project "$ESTOE_GCP_PROJECT"
```

Enabling APIs requires `serviceusage.services.enable`, commonly through Service Usage
Admin. An administrator can perform this once. Creating the test secret/version needs
appropriate Secret Manager creation/version permissions; Secret Manager Admin is the
documented setup role, but is broader than estoe needs. Ask the sandbox administrator for
appropriate temporary setup access or have them create the secret. Do not give estoe's
read identity project Owner or Secret Manager Admin just to fetch a value.

## 4. Create the global test secret and first version

With a NEW secret name in the intended project:

```bash
gcloud secrets create estoe-test-app --project "$ESTOE_GCP_PROJECT" \
  --replication-policy=automatic --data-file=examples/synthetic-secret.json --quiet
```

This creates the secret resource AND its first version. The command uses a file so the
JSON payload is not in command arguments or shell history. CLI output contains metadata,
not the value. Do not run `versions access` or enable HTTP debug logging for this guide.
If the name already exists, choose a different synthetic test name and consistently use it
below rather than changing an existing application's secret.

Console alternative: Secret Manager → Create secret; name `estoe-test-app`; paste the exact
synthetic JSON as its value; choose automatic replication; create. This adapter uses global
secret paths, so do not choose regional secrets. Review replication policy before creation
if your organization has data-residency requirements.

## 5. Configure SDK credentials and read-only access

For local development using your user account:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "$ESTOE_GCP_PROJECT"
```

Sign in as the identity you intend estoe to use. ADC and `gcloud auth login` can represent
different users; a CLI operation succeeding does not prove the SDK has the same permissions.
If the quota-project command fails, ask the administrator for `serviceusage.services.use`
on the chosen quota project (Service Usage Consumer is the standard role). ADC files stay
in the SDK's local configuration directory, never in this repository.

If `GOOGLE_APPLICATION_CREDENTIALS` is already set, it takes precedence over the local ADC
file. Check locally whether you intended that identity; do not print or commit its contents.
Do not create/download service-account keys for this test. Existing service-account
impersonation ADC may also be used when configured and authorized by your administrator.

An administrator or identity with IAM-management permission grants **Secret Manager Secret
Accessor on this one secret** to the ADC identity. For a user-account ADC identity:

```bash
ESTOE_GCP_READER="user:<YOUR_ADC_USER_EMAIL>"
gcloud secrets add-iam-policy-binding estoe-test-app --project "$ESTOE_GCP_PROJECT" \
  --member="$ESTOE_GCP_READER" --role=roles/secretmanager.secretAccessor --quiet
```

For existing service-account ADC, the member format is `serviceAccount:<EMAIL>` instead.
Do not use `allUsers`/`allAuthenticatedUsers`. After creation, remove only temporary broad
setup permissions if you are using the same identity for reading; granting Accessor does not
subtract existing Admin privileges. Do not remove unrelated organizational grants. Allow
time for permission propagation.

## 6. Preview, then generate .env.gcp

From the estoe checkout, whose ignore rules include `.env.*`:

```bash
uv run estoe pull --provider gcp --project "$ESTOE_GCP_PROJECT" \
  --secret estoe-test-app --output .env.gcp --preview
```

Expected: `Preview: 3 variable(s)` and sorted names `API_TOKEN`, `API_URL`, `APP_MODE`.
No values appear and preview creates no file. It IS a billable-capable live read of:

```text
projects/PROJECT_ID/secrets/estoe-test-app/versions/latest
```

Then create the dotenv file:

```bash
uv run estoe pull --provider gcp --project "$ESTOE_GCP_PROJECT" \
  --secret estoe-test-app --output .env.gcp
```

Expect three variables written, mode 0600. The CLI verifies CRC32C and UTF-8 before JSON
parsing. Use a private ownership-enforcing output directory; on an ownership-disabled SSD,
select a different existing output parent using `--output`. estoe changes no mount settings.

Verify without printing secret values:

```bash
uv run python -c 'import json,stat; from pathlib import Path; from dotenv import dotenv_values; p=Path(".env.gcp"); assert dict(dotenv_values(p,interpolate=False)) == json.loads(Path("examples/synthetic-secret.json").read_text()); assert stat.S_IMODE(p.stat().st_mode)==0o600; print("PASS: synthetic values and private file mode")'
git check-ignore --quiet .env.gcp && echo "PASS: output is Git-ignored"
```

Adjust the verification path if you chose a different destination. Do not share generated
files, ADC files, tokens, actual identifiers, or raw SDK response dumps in public issues.

## 7. Negative tests and troubleshooting

- Repeat pull: existing output needs explicit confirmation or `--overwrite` noninteractively.
- Select `estoe-missing-secret`: expect `not_found`, no new output.
- Add `--profile sandbox`: usage error 2 before cloud access; AWS profiles do not select ADC.
- `credentials`: run the ADC login step; check whether an environment override selected a
  different identity. Ordinary `gcloud auth login` alone is insufficient for Python SDK ADC.
- Quota-project setup: even when a read succeeds, configure the ADC quota project in
  step 5. estoe suppresses raw SDK warnings; their absence does not prove quota/billing
  configuration is complete. Ask your administrator about Service Usage Consumer access
  if `set-quota-project` fails. Do not change projects or permissions just to silence a warning.
- `access_denied`: check ADC principal, secret-level Accessor binding, IAM propagation,
  enabled API, and quota-project service-usage permission. Viewer alone cannot read values.
- `configuration`: check project/secret IDs and that the latest version is enabled. `latest`
  does not guarantee fallback to an older enabled version if the newest is disabled/destroyed.
- `timeout` / `throttled`: verify network/quota; the provider worker is capped at 15 seconds
  plus process startup/cleanup. No automatic multi-secret retry loop is run.
- `integrity`: payload checksum did not match; no output is written. Retry once manually
  and investigate persistent corruption rather than disabling verification.
- `invalid_content`: verify flat JSON string values and UTF-8. Regional paths/full resource
  paths supplied as `--secret` are unsupported; supply the secret ID and `--project` separately.

## 8. Cleanup (manual and optional)

When testing is complete, inspect the exact sandbox secret in the console and delete only
that test secret if no longer needed. Secret deletion affects its versions and dependent
users; review any configured delayed-destruction policy first. Do not delete a shared
project or shared credentials. Remove only IAM assignments created for this test when
appropriate. Retain synthetic resources if needed for the next test; estoe never cleans up.

## Sources

- [Create secrets and versions](https://docs.cloud.google.com/secret-manager/docs/creating-and-accessing-secrets)
- [CLI file-based creation](https://docs.cloud.google.com/sdk/gcloud/reference/secrets/create)
- [Per-secret access](https://docs.cloud.google.com/secret-manager/docs/manage-access-to-secrets)
- [Local ADC setup](https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment)
- [Payload integrity verification](https://docs.cloud.google.com/secret-manager/docs/samples/secretmanager-access-secret-version)
