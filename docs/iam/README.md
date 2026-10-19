# Read-only policy examples

These files are templates, not deployable policies until the placeholders are replaced
locally. Do not commit account identifiers or real resource names. No IAM policy is attached
or modified by estoe. Account owners must authorize IAM changes separately.

- `read-secret-policy.json`: allow only GetSecretValue for one full secret ARN including its
  AWS-generated suffix. Do not replace it with account-wide `*`.
- `customer-key-policy.json`: optional identity permission when a customer-managed key is
  used. Its key policy must also authorize the principal. Do not add it unnecessarily.

References:
- https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
- https://bbc2.github.io/python-dotenv/ (supported encoding/consumer)
- https://docs.aws.amazon.com/botocore/latest/reference/config.html (SDK retry/socket bounds)
