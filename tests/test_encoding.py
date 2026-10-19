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
