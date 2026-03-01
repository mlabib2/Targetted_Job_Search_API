"""Shared utilities used across scrapers and matcher."""

import re
import html as _html
from typing import Optional


def strip_html(text: str) -> Optional[str]:
    """Strip HTML tags and decode entities. Returns None if result is empty."""
    if not text:
        return None
    text = _html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None
