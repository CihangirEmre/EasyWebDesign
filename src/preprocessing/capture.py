"""Aşama 0 — Ön İşleme: ekran görüntüsü yakalama.

Karar (CLAUDE.md §2, Aşama 0): Playwright headless browser, DPR sabit (1.0,
Retina simülasyonu kapalı), browser chrome yok, sabit viewport genişliği,
çıktı her zaman PNG (JPEG yasak).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_VIEWPORT_WIDTH = 1280
DEFAULT_VIEWPORT_HEIGHT = 800
DEFAULT_DEVICE_SCALE_FACTOR = 1.0  # Retina simülasyonu KAPALI


@dataclass(frozen=True)
class CaptureResult:
    output_path: Path
    viewport_width: int
    viewport_height: int
    full_page: bool


def capture_screenshot(
    url: str,
    output_path: str | Path,
    *,
    full_page: bool = True,
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
    wait_until: str = "networkidle",
) -> CaptureResult:
    """Bir URL'nin ekran görüntüsünü yakalar.

    full_page=True: tüm sayfa yüksekliği yakalanır (uzun sayfalar için).
    full_page=False: sadece viewport (viewport_width x viewport_height) yakalanır.
    Her iki modda da DPR=1.0 sabit, browser chrome dahil edilmez (Playwright
    screenshot API'si zaten chrome içermez), çıktı PNG'dir.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".png":
        raise ValueError("Çıktı formatı PNG olmalı — JPEG kesinlikle kullanılmamalı.")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=DEFAULT_DEVICE_SCALE_FACTOR,
        )
        page.goto(url, wait_until=wait_until)
        page.screenshot(path=str(output_path), full_page=full_page, type="png")
        browser.close()

    return CaptureResult(
        output_path=output_path,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        full_page=full_page,
    )
