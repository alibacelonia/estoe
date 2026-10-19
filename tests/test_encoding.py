import io
import json

import pytest
from dotenv import dotenv_values

from estoe.encoding import encode_env, parse_secret
from estoe.errors import EstoeError


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "quotes ' and \"",
        "\\n\\r\\t\\'\\\"",
        "line\nnext\r\nend\t",
        "snowman ☃",
        "#hash=equals",
        "${HOME} $HOME $(touch sentinel) `id`",
        "\a\b\f\v",
        "ends\\",
        "\\\\'double'",
    ],
)
def test_round_trip(value):
    parsed = parse_secret(json.dumps({"VALUE": value, "A": ""}))
    encoded = encode_env(parsed)
    assert encoded.startswith(b'A=""\n')
    assert dotenv_values(stream=io.StringIO(encoded.decode()), interpolate=False) == parsed
    assert encode_env(parsed) == encoded


@pytest.mark.parametrize(
    "content",
    [
        "{}",
        "[]",
        "null",
        '"text"',
        '{"A":1}',
        '{"A":false}',
        '{"A":null}',
        '{"A":[]}',
        '{"A":{}}',
        '{"1A":"x"}',
        '{"A-B":"x"}',
        '{"A":"x","A":"y"}',
        '{"A":"\\u0000"}',
        '{"A":"\\ud800"}',
        "broken",
    ],
)
def test_reject_unsafe_content_without_echoing(content):
    with pytest.raises(EstoeError) as error:
        parse_secret(content)
    assert error.value.code == "invalid_content"
    assert content not in str(error.value)


def test_size_bounds():
    with pytest.raises(EstoeError, match="size limit"):
        parse_secret(json.dumps({"A": "x" * 65536}))
    with pytest.raises(EstoeError, match="size limit"):
        encode_env({"A": "x" * 262144})


@pytest.mark.parametrize(
    ("content", "reason", "advice"),
    [
        ("synthetic-sensitive-canary", "json_syntax", "not valid JSON"),
        ('{"PRIVATE_KEY":"synthetic-sensitive-canary",}', "json_syntax", "trailing commas"),
        ('["synthetic-sensitive-canary"]', "object_required", "nonempty JSON object"),
        ("{}", "object_required", "empty object"),
        (
            '{"PRIVATE_KEY":"synthetic-sensitive-canary","PRIVATE_KEY":"x"}',
            "duplicate_keys",
            "only once",
        ),
        ('{"PRIVATE-KEY":"synthetic-sensitive-canary"}', "invalid_keys", "leading digit"),
        ('{"PRIVATE_KEY":123}', "string_values", "Quote numbers/booleans"),
        (
            '{"PRIVATE_KEY":{"INNER":"synthetic-sensitive-canary"}}',
            "string_values",
            "nested objects",
        ),
        ('{"PRIVATE_KEY":"synthetic-sensitive-canary\\u0000"}', "nul", "NUL"),
        ('{"PRIVATE_KEY":"synthetic-sensitive-canary\\ud800"}', "unicode", "Unicode"),
    ],
)
def test_actionable_content_errors_are_fixed_and_value_free(content, reason, advice):
    from estoe.errors import CONTENT_HINTS

    with pytest.raises(EstoeError) as error:
        parse_secret(content)
    assert error.value.code == "invalid_content"
    assert str(error.value) == CONTENT_HINTS[reason]
    assert advice in str(error.value)
    for sensitive in ("synthetic-sensitive-canary", "PRIVATE_KEY", "PRIVATE-KEY", "INNER"):
        assert sensitive not in str(error.value)


def test_untrusted_content_reason_cannot_become_a_diagnostic():
    from estoe.errors import MESSAGES

    assert (
        str(EstoeError("invalid_content", reason="synthetic-sensitive-canary"))
        == MESSAGES["invalid_content"]
    )
    assert str(EstoeError("credentials", reason="json_syntax")) == MESSAGES["credentials"]
