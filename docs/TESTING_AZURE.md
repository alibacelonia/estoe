# Azure Key Vault: setup and manual estoe test

Release status: Azure is tested offline. The owner waived live Azure validation for
release preparation; no real-vault success is claimed. This optional guide remains
available if you want to verify your own account, permissions and networking.

These are instructions for you to review and run. They create resources and assign roles;
estoe itself only reads. No Azure setup or live read was performed by the implementation
agent. Use an authorized sandbox subscription. Azure resource and operation charges may apply.

This guide targets Azure public cloud and an existing interactive Azure CLI user login.
Managed identity/service-principal chains and sovereign vault endpoints are not implemented.

## 1. Prepare the local CLI and synthetic input

From your estoe checkout on branch `feature/azure-gcp-providers` (or a later merged checkout):

```bash
uv sync --locked
uv run estoe --version
uv run estoe pull --help
```

Expect version `0.2.0.dev0` and `azure` among provider choices. The published AWS v0.1.0
does not have this feature. Use `uv run estoe` throughout to select the checkout version.

Install the Azure CLI using Microsoft's [installation instructions](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli),
then check `az version`. `examples/synthetic-secret.json` already contains ONLY fictional
test values, including three keys: `APP_MODE`, `API_URL`, `API_TOKEN`. Do not replace that
tracked fixture with real credentials. All its values are strings, as estoe requires.

## 2. Log in and explicitly select your sandbox subscription

Replace the placeholders locally. Do not commit tenant, subscription, principal or vault details.

```bash
az login --tenant "<TENANT_ID>"
az account set --subscription "<SUBSCRIPTION_ID>"
az account show --query '{name:name,tenant:tenantId}' --output table
```

Check that the displayed subscription/tenant is the intended sandbox. This login is what
estoe's AzureCliCredential will use; AWS profiles do not apply. Keep Azure CLI credentials
outside the repository. If you use multiple tenants, pass the same tenant UUID to estoe's
`--tenant-id` later. estoe does not launch login or choose another identity automatically.

## 3. Create a dedicated resource group and vault

The selected account needs permission to create these resources. Assigning roles separately
requires role-assignment permission; being a vault Contributor alone is insufficient for
reading secret values. If you lack permission, have the sandbox administrator run setup.

Choose a globally unique, lowercase vault name: 3–24 letters/digits/hyphens, starting with
a letter, ending with a letter/digit, with no consecutive hyphens. Choose a new name, not a
production vault. The placeholders below must be replaced before running:

```bash
ESTOE_AZ_GROUP="estoe-test-rg"
ESTOE_AZ_LOCATION="eastus"
ESTOE_AZ_VAULT="<YOUR_UNIQUE_VAULT_NAME>"

az group create --name "$ESTOE_AZ_GROUP" --location "$ESTOE_AZ_LOCATION" --output none
az keyvault create --name "$ESTOE_AZ_VAULT" --resource-group "$ESTOE_AZ_GROUP" \
  --location "$ESTOE_AZ_LOCATION" --enable-rbac-authorization true \
  --enable-purge-protection true --output none
```

This uses Azure RBAC. Purge protection prevents immediate permanent deletion of the vault
after soft deletion; the retention policy also reserves its name. Review that behavior
before creating it. If the subscription requires resource-provider registration, an
administrator may need to register `Microsoft.KeyVault` first.

Alternative in the Azure portal: create a Resource Group, then a Key Vault using Azure
RBAC under Access configuration. Ensure vault networking permits your development machine;
do not disable an existing production firewall to make a test pass.

## 4. Grant setup permission, then create one JSON secret

These commands resolve your signed-in user's object ID and the new vault ID without printing
values. If directory lookup is unavailable, ask the administrator for the correct principal.

```bash
ESTOE_AZ_USER_ID=$(az ad signed-in-user show --query id --output tsv)
ESTOE_AZ_VAULT_ID=$(az keyvault show --name "$ESTOE_AZ_VAULT" \
  --resource-group "$ESTOE_AZ_GROUP" --query id --output tsv)

az role assignment create --assignee-object-id "$ESTOE_AZ_USER_ID" \
  --assignee-principal-type User --role "Key Vault Secrets Officer" \
  --scope "$ESTOE_AZ_VAULT_ID" --output none
```

Allow time for RBAC propagation before attempting the next command; a new assignment may
not be effective immediately. With the new empty test vault, create the secret:

```bash
az keyvault secret set --vault-name "$ESTOE_AZ_VAULT" --name estoe-test-app \
  --file examples/synthetic-secret.json --encoding utf-8 \
  --content-type application/json --output none
```

`--output none` matters: the default secret-set response can contain the value. Do not add
`--debug`, print the SDK response, or run a value-retrieval command for troubleshooting.
Secret `set` creates a new version if the name already exists; this guide assumes a NEW
dedicated test vault and name. In the portal, the equivalent is Secrets → Generate/Import,
name `estoe-test-app`, and the exact synthetic JSON as the value.

## 5. Use read-only permissions for the estoe test

For a dedicated single-app test vault, give the testing principal **Key Vault Secrets User**
at that vault's scope:

```bash
az role assignment create --assignee-object-id "$ESTOE_AZ_USER_ID" \
  --assignee-principal-type User --role "Key Vault Secrets User" \
  --scope "$ESTOE_AZ_VAULT_ID" --output none
```

After creating the secret, remove only the temporary Secrets Officer assignment made in
step 4 using the vault's Access control (IAM) → Role assignments screen. If Officer remains,
your test identity still has write privileges; adding User does not subtract Officer.
Do not remove unrelated assignments. An administrator may do setup and grant a different
user the read-only role instead. Allow propagation after permission changes.

## 6. Preview, then generate .env.azure

From the estoe repository, whose `.gitignore` includes `.env.*`:

```bash
uv run estoe pull --provider azure --secret estoe-test-app \
  --vault-url "https://${ESTOE_AZ_VAULT}.vault.azure.net/" --preview --output .env.azure
```

Expected: `Preview: 3 variable(s)` and the sorted key names `API_TOKEN`, `API_URL`, `APP_MODE`.
No values appear and no file is created by preview. Preview IS a live read.

```bash
uv run estoe pull --provider azure --secret estoe-test-app \
  --vault-url "https://${ESTOE_AZ_VAULT}.vault.azure.net/" --output .env.azure
```

If a specific tenant is needed, add `--tenant-id "<TENANT_ID>"` to either command.
Expected: three variables written, mode 0600. The output parent must enforce ownership and
be private. On macOS an ownership-disabled external volume is rejected; use `--output` with
an existing private directory on an ownership-enforcing volume. No system setting is changed.

Check contents WITHOUT printing values:

```bash
uv run python -c 'import json,stat; from pathlib import Path; from dotenv import dotenv_values; p=Path(".env.azure"); assert dict(dotenv_values(p,interpolate=False)) == json.loads(Path("examples/synthetic-secret.json").read_text()); assert stat.S_IMODE(p.stat().st_mode)==0o600; print("PASS: synthetic values and private file mode")'
git check-ignore --quiet .env.azure && echo "PASS: output is Git-ignored"
```

Adjust the verification path if you selected another output. Do not paste output files,
credentials, actual account identifiers, or raw cloud exceptions into issues.

## 7. Negative tests and troubleshooting

- Repeat pull: existing file needs confirmation, or `--overwrite` in noninteractive use.
  Without approval it stays unchanged. With synthetic data you may explicitly test overwrite.
- Use secret name `estoe-missing-secret`: expect `not_found`, no new output file.
- Add `--profile sandbox`: expect usage error 2 before any cloud call (AWS option).
- `credentials`: check Azure CLI installation/session/tenant; run `az login` yourself.
- `access_denied`: confirm the identity, RBAC propagation, vault data-plane role, networking,
  and that the secret is enabled. Subscription Reader/Contributor is not Secrets User.
- `timeout`: check CLI/network availability; the SDK worker has a 15-second deadline.
- `invalid_content`: check that the secret value is a flat JSON object of strings.
- `filesystem`, `tracked`, or `unignored`: follow the file-safety message; prefer a private
  Git-ignored file rather than overriding protection.

## 8. Cleanup (manual and optional)

Retain the sandbox until testing is complete. In the portal, identify the exact test secret
and delete it if no longer needed. If the vault is exclusively for this test, review its
contents and delete only that vault/resource group when appropriate. Resource-group deletion
removes ALL resources inside it. Do not purge protected resources or delete shared resources.
Purge protection/soft-delete retention can prevent immediate name reuse. estoe performs no cleanup.

## Sources

- [Azure setup and RBAC](https://learn.microsoft.com/en-us/azure/key-vault/secrets/quick-create-cli)
- [Read-only versus management roles](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide)
- [Secret import from a file](https://learn.microsoft.com/en-us/cli/azure/keyvault/secret)
- [AzureCliCredential](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.azureclicredential)
