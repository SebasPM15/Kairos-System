import pytest

from app.bot.parsing import parse_id, parse_idea, split_slug, split_title_rationale

KNOWN = {"kairos", "web"}


@pytest.mark.parametrize(
    "args, expected",
    [
        ("kairos: do it", ("kairos", "do it")),
        ("  Kairos :  do it  ", ("kairos", "do it")),
        ("kairos: a: b", ("kairos", "a: b")),
        ("kairos:", None),
        (": text", None),
        ("no colon", None),
        ("", None),
    ],
)
def test_split_slug(args, expected):
    assert split_slug(args) == expected


@pytest.mark.parametrize(
    "args, expected",
    [
        ("kairos: nueva idea", ("kairos", "nueva idea")),
        ("KAIROS: nueva idea", ("kairos", "nueva idea")),
        ("desconocido: nueva idea", (None, "desconocido: nueva idea")),
        ("Nota importante: comprar leche", (None, "Nota importante: comprar leche")),
        ("  solo texto  ", (None, "solo texto")),
        ("kairos:", (None, "kairos:")),
    ],
)
def test_parse_idea_only_trusts_known_slugs(args, expected):
    assert parse_idea(args, KNOWN) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Usar SQLite | es local", ("Usar SQLite", "es local")),
        ("A | b | c", ("A", "b | c")),
        ("sin barra", None),
        ("título |", None),
        ("| porqué", None),
    ],
)
def test_split_title_rationale(text, expected):
    assert split_title_rationale(text) == expected


@pytest.mark.parametrize(
    "arg, expected",
    [("12", 12), (" 7 ", 7), ("#3", 3), ("0", None), ("-1", None), ("abc", None), ("", None), ("1 2", None)],
)
def test_parse_id(arg, expected):
    assert parse_id(arg) == expected
