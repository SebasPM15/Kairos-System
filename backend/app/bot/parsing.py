"""Pure functions that parse the free-text arguments of bot commands."""

import re
from collections.abc import Collection

_ID_PATTERN = re.compile(r"#?([0-9]+)")


def split_slug(args: str) -> tuple[str, str] | None:
    """Split "slug: text" on the first colon; None if either side is empty."""
    slug, separator, text = args.partition(":")
    slug, text = slug.strip().lower(), text.strip()
    if not separator or not slug or not text:
        return None
    return slug, text


def parse_idea(args: str, known_slugs: Collection[str]) -> tuple[str | None, str]:
    """Return (slug, content). The prefix counts as a slug only if it names an existing project."""
    parsed = split_slug(args)
    if parsed is not None and parsed[0] in known_slugs:
        return parsed
    return None, args.strip()


def split_title_rationale(text: str) -> tuple[str, str] | None:
    """Split "title | rationale" on the first pipe; None if either side is empty."""
    title, separator, rationale = text.partition("|")
    title, rationale = title.strip(), rationale.strip()
    if not separator or not title or not rationale:
        return None
    return title, rationale


def parse_id(arg: str) -> int | None:
    """Accept "12" or "#12"; zero and anything non-numeric give None."""
    match = _ID_PATTERN.fullmatch(arg.strip())
    value = int(match.group(1)) if match else 0
    return value or None
