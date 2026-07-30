"""Aşama 6 — Değerlendirme: üretilen HTML'i render edip screenshot alma.

Aşama 0'ın (src/preprocessing/capture.py) aynı Playwright ayarlarını (DPR=1.0,
browser chrome yok, PNG, sabit viewport) kullanır — orijinal screenshot ile
render arasındaki karşılaştırmanın adil olması için tek fark render
KAYNAĞIdır (URL yerine yerel dosya), diğer tüm ayarlar birebir aynı kalmalı.
"""

from __future__ import annotations

from pathlib import Path

from src.preprocessing.capture import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
    CaptureResult,
    capture_screenshot,
)


def render_html(
    html_path: str | Path,
    output_path: str | Path,
    *,
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
) -> CaptureResult:
    """Yerel bir HTML dosyasını Playwright ile render edip PNG olarak kaydeder."""
    html_path = Path(html_path).resolve()
    return capture_screenshot(
        html_path.as_uri(),
        output_path,
        full_page=True,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        wait_until="load",
    )
