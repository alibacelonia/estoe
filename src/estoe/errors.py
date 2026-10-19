"""Value-free errors suitable for command-line diagnostics."""

MESSAGES = {
    "invalid_content": "Expected a nonempty flat JSON object with valid keys and string values.",
    "content_limit": "Secret or encoded output exceeds the supported size limit.",
    "binary_secret": "Binary secrets are unsupported; use a JSON SecretString.",
    "credentials": "Cloud credentials are missing or expired; refresh your provider login.",
    "configuration": "Check the selected provider's identity and resource configuration.",
    "access_denied": "Access denied; check secret permissions and the encryption-key policy.",
    "not_found": "The selected secret was not found.",
    "throttled": "The provider throttled the request; retry later.",
    "timeout": "Secret retrieval exceeded its time limit.",
    "provider": "Secret retrieval failed; check provider configuration and connectivity.",
    "integrity": "Secret payload checksum verification failed; no output was written.",
    "unsafe_path": "Use a regular destination in an existing private directory without symlinks.",
    "filesystem": "Destination volume must enforce ownership and private POSIX permissions.",
    "exists": "Destination exists; confirm replacement or pass --overwrite.",
    "changed": "Destination changed during the operation; retry and review replacement.",
    "tracked": "Destination is tracked by Git; choose an untracked output file.",
    "unignored": "Destination is not Git-ignored; add an ignore rule or pass --allow-unignored.",
    "git": "Git safety checks failed; check Git installation and repository health.",
    "write": "File publication failed; check permissions and storage availability.",
    "platform": "This release supports macOS/Linux POSIX filesystems only.",
    "cancelled": "Operation cancelled.",
    "internal": "Operation failed safely; no diagnostic payload is available.",
}


# Only these fixed messages may add detail to content failures. Never include a JSON
# decoder exception, offending key, value, selector, or caller-supplied reason text.
CONTENT_HINTS = {
    "json_syntax": 'Secret is not valid JSON. Store an object such as {"APP_MODE":"development"}, '
    "not KEY=value text; use double quotes and remove trailing commas.",
    "object_required": "Secret must be a nonempty JSON object, "
    "not an array, scalar, or empty object.",
    "duplicate_keys": "Secret contains duplicate JSON keys. Keep each key only once.",
    "invalid_keys": "Variable names must match [A-Za-z_][A-Za-z0-9_]*; "
    "do not use spaces, hyphens, or a leading digit.",
    "string_values": "Every value must be a string. Quote numbers/booleans "
    '(for example "PORT":"8000") '
    "and replace nested objects, arrays, or null with string values.",
    "nul": "String values cannot contain NUL characters. Remove NUL before retrying.",
    "unicode": "Secret must contain valid UTF-8 text without unpaired Unicode surrogates.",
}


class EstoeError(Exception):
    def __init__(self, code: str, *, reason: str | None = None) -> None:
        self.code = code if code in MESSAGES else "internal"
        message = MESSAGES[self.code]
        if self.code == "invalid_content":
            message = CONTENT_HINTS.get(reason, message)
        super().__init__(message)
