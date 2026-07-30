"""Aşama 4 — Generation: model çıktısından HTML kodunu ayıklama."""

from __future__ import annotations

import re

_CODE_FENCE_PATTERN = re.compile(r"```(?:html)?\s*\n(.*?)```", re.DOTALL)
_BODY_PATTERN = re.compile(r"<body\b[^>]*>(.*)</body>", re.DOTALL | re.IGNORECASE)
_DOC_WRAPPER_PATTERN = re.compile(r"<!DOCTYPE[^>]*>|</?html[^>]*>|<head\b.*?</head>|</?body[^>]*>", re.DOTALL | re.IGNORECASE)


def extract_html(raw_text: str) -> str:
    """```html ... ``` bloğunu ayıklar; blok yoksa ham metni olduğu gibi döner.

    Bölge prompt'u modelden yalnızca bir fragment istiyor (bkz. prompts.py),
    ama model buna güvenilir uymayabiliyor — bazen tam bir <!DOCTYPE>/<html>/
    <head>/<body> sarmalı üretebiliyor. Bu, root'un kendi <body>'sinin İÇİNE
    bir bölge fragment'ı olarak yerleştirildiğinde iç içe <body>/<html>
    etiketlerine (tarayıcının nasıl normalleştireceği belirsiz) yol açar; bu
    yüzden modele güvenmek yerine sarmalayıcı etiketleri deterministik olarak
    ayıklıyoruz.
    """
    match = _CODE_FENCE_PATTERN.search(raw_text)
    html = match.group(1).strip() if match else raw_text.strip()

    body_match = _BODY_PATTERN.search(html)
    if body_match:
        html = body_match.group(1).strip()
    else:
        html = _DOC_WRAPPER_PATTERN.sub("", html).strip()

    return html
