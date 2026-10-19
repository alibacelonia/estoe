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


class EstoeError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code if code in MESSAGES else "internal"
        super().__init__(MESSAGES[self.code])
