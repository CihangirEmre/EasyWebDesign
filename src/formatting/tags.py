"""Aşama 2b — Formatting: Aşama 1'in serbest-metin etiketini semantik HTML5
tag/role çiftine çevirme.

Karar (CLAUDE.md §2, Aşama 2b): Şema, front-end mühendisinin doğal olarak
düşüneceği kavramlara (header, nav, main, section...) sadık kalmalı — "özel/
keyfi bir format" değil.
"""

from __future__ import annotations

# label (küçük harf, normalize edilmiş) -> (tag, role|None)
LABEL_TAG_MAP: dict[str, tuple[str, str | None]] = {
    "navigation bar": ("header", "navbar"),
    "navbar": ("header", "navbar"),
    "nav": ("nav", None),
    "sidebar": ("aside", "sidebar"),
    "button": ("button", None),
    "link": ("a", None),
    "input field": ("input", None),
    "input": ("input", None),
    "dropdown": ("select", None),
    "checkbox": ("input", "checkbox"),
    "radio button": ("input", "radio"),
    "card": ("section", "card"),
    "icon": ("span", "icon"),
    "image": ("img", None),
    "logo": ("img", "logo"),
    "heading": ("h3", None),
    "paragraph": ("p", None),
    "paragraph text": ("p", None),
    "text": ("p", None),
    "badge": ("span", "badge"),
    "tab": ("button", "tab"),
    "tooltip": ("div", "tooltip"),
    "modal": ("div", "modal"),
    "avatar": ("img", "avatar"),
    "progress bar": ("div", "progressbar"),
    "table": ("table", None),
    "list item": ("li", None),
    "footer": ("footer", None),
    "body": ("body", None),
}

TEXT_BEARING_TAGS = {"p", "a", "span", "h1", "h2", "h3", "h4", "h5", "h6", "button", "li", "td"}
IMAGE_TAGS = {"img"}


def resolve_tag(label: str | None) -> tuple[str, str | None]:
    """Bilinmeyen/None etiket için güvenli varsayılan: <div>, role=orijinal etiket."""
    if label is None:
        return "div", None
    key = label.strip().lower()
    if key in LABEL_TAG_MAP:
        return LABEL_TAG_MAP[key]
    return "div", key
