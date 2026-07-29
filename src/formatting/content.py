"""Aşama 2b — Formatting: metin içeriği çıkarımı (opsiyonel OCR).

Not: Aşama 1'in kararlaştırılmış model çıktı formatı (CLAUDE.md §2, Aşama 1)
yalnızca bbox+label içeriyor, OCR metni içermiyor. Metin tag'leri (p, a,
button, h1-h6, li, td) için gerçek içerik gerekiyorsa pytesseract opsiyonel
bağımlılığı kullanılır; kurulu değilse content alanı sessizce None kalır —
bu pilotta zorunlu bir bağımlılık DEĞİL, best-effort bir zenginleştirme.
"""

from __future__ import annotations

from PIL import Image

from .tags import TEXT_BEARING_TAGS

try:
    import pytesseract

    _HAS_TESSERACT = True
except ImportError:
    _HAS_TESSERACT = False


def extract_content(image: Image.Image, bbox_px: list[float], tag: str) -> str | None:
    if tag not in TEXT_BEARING_TAGS or not _HAS_TESSERACT:
        return None
    x1, y1, x2, y2 = (max(0, int(v)) for v in bbox_px)
    x2, y2 = max(x2, x1 + 1), max(y2, y1 + 1)
    crop = image.crop((x1, y1, x2, y2))
    text = pytesseract.image_to_string(crop).strip()
    return text or None
