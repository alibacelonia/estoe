"""Strict JSON and deterministic python-dotenv encoding; no interpolation."""

from __future__ import annotations

import json
import re

from estoe.errors import EstoeError

MAX_SECRET_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 256 * 1024
KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", re.ASCII)


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise EstoeError("invalid_content", reason="duplicate_keys")
        result[key] = value
    return result


def parse_secret(content: str) -> dict[str, str]:
    try:
        if len(content.encode("utf-8")) > MAX_SECRET_BYTES:
            raise EstoeError("content_limit")
        values = json.loads(content, object_pairs_hook=_object)
        if not isinstance(values, dict) or not values:
            raise EstoeError("invalid_content", reason="object_required")
        for key, value in values.items():
            if not KEY.fullmatch(key):
                raise EstoeError("invalid_content", reason="invalid_keys")
            if not isinstance(value, str):
                raise EstoeError("invalid_content", reason="string_values")
            if "\0" in value:
                raise EstoeError("invalid_content", reason="nul")
            value.encode("utf-8")  # Reject unpaired Unicode surrogates.
        return dict(sorted(values.items()))
    except json.JSONDecodeError:
        raise EstoeError("invalid_content", reason="json_syntax") from None
    except UnicodeError:
        raise EstoeError("invalid_content", reason="unicode") from None
    except (ValueError, TypeError, RecursionError):
        raise EstoeError("invalid_content") from None


def encode_env(values: dict[str, str]) -> bytes:
    # Double quotes with documented python-dotenv escapes; dollars are literal ONLY when
    # the consumer uses interpolate=False. Never shell-source the result.
    lines = []
    for key, value in sorted(values.items()):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        escaped = escaped.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
        lines.append(f'{key}="{escaped}"\n')
    result = "".join(lines).encode("utf-8")
    if len(result) > MAX_OUTPUT_BYTES:
        raise EstoeError("content_limit")
    return result
