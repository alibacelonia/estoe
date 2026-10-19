"""Export sequencing; no SDK, shell syntax, or transport dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from estoe.encoding import encode_env, parse_secret
from estoe.errors import EstoeError
from estoe.files import destination
from estoe.providers import SecretProvider


@dataclass(frozen=True)
class ExportResult:
    keys: tuple[str, ...]
    preview: bool
    in_git: bool


def export_secret(
    provider: SecretProvider,
    secret: str,
    output: str = ".env",
    *,
    preview: bool = False,
    overwrite: bool = False,
    allow_unignored: bool = False,
    confirm: Callable[[], bool] | None = None,
) -> ExportResult:
    with destination(output, allow_unignored) as target:
        if target.before is not None and not preview and not overwrite:
            if confirm is None:
                raise EstoeError("exists")
            if not confirm():
                raise EstoeError("cancelled")
        target.verify()
        values = parse_secret(provider.fetch(secret))
        encoded = encode_env(values)
        if not preview:
            target.publish(encoded)
        return ExportResult(tuple(values), preview, target.in_git)
