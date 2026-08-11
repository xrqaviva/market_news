"""Shared source-URL policy for report parsing and rendering."""

import html
from urllib.parse import urlsplit


def renderable_source_url(value: str) -> str:
    """Return a normalized HTTP(S) URL with a network location, else empty."""
    candidate = html.unescape(value).strip()
    if not candidate:
        return ""
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return candidate
