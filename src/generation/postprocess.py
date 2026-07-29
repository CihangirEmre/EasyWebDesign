"""Aşama 4 — Generation: model çıktısından HTML kodunu ayıklama."""

from __future__ import annotations

import re

_CODE_FENCE_PATTERN = re.compile(r"```(?:html)?\s*\n(.*?)```", re.DOTALL)


def extract_html(raw_text: str) -> str:
    """```html ... ``` bloğunu ayıklar; blok yoksa ham metni olduğu gibi döner."""
    match = _CODE_FENCE_PATTERN.search(raw_text)
    if match:
        return match.group(1).strip()
    return raw_text.strip()
