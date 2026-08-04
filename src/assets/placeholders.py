"""ScreenCoder-tarzı basit mimari — üretim SONRASI gerçek görsel yerleştirme.

ScreenCoderClone'un `image_box_detection.py` + `image_replacer.py` mantığının
BASİTLEŞTİRİLMİŞ hali: UIED (klasik CV component tespiti) + CIoU/Hungarian
eşleme YOK (ağır/kırılgan bir bağımlılık, bkz. proje planı). Onun yerine:
render edilen `.img-placeholder` elemanının KENDİ bbox'ı orijinal screenshot
boyutuna ölçeklenip doğrudan o bölge crop'lanır — modele zaten "bu görselin
kendi boyutunu koru" dendiği için (bkz. src/generation/prompts.py) bu genelde
yeterince hizalı çıkar, ayrı bir tespit/eşleme adımına gerek kalmaz.
"""

from __future__ import annotations

from pathlib import Path

import bs4
from PIL import Image
from playwright.sync_api import sync_playwright

from src.preprocessing.capture import DEFAULT_DEVICE_SCALE_FACTOR, DEFAULT_VIEWPORT_WIDTH

PLACEHOLDER_CLASS = "img-placeholder"


def find_placeholder_boxes(html_path: str | Path, *, viewport_width: int = DEFAULT_VIEWPORT_WIDTH) -> tuple[list[dict], float, float]:
    """Filled HTML'i render edip her `.img-placeholder` elemanının render
    bbox'ını (döküman sırasına göre) ve toplam layout boyutunu döner."""
    html_path = Path(html_path).resolve()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": viewport_width, "height": 800},
            device_scale_factor=DEFAULT_DEVICE_SCALE_FACTOR,
        )
        page.goto(html_path.as_uri(), wait_until="load")
        data = page.evaluate(
            """() => {
                const els = Array.from(document.querySelectorAll('.img-placeholder'));
                const boxes = els.map(el => {
                    const r = el.getBoundingClientRect();
                    return { x: r.x, y: r.y, w: r.width, h: r.height };
                });
                const layout = document.documentElement.getBoundingClientRect();
                return { boxes, layout_width: layout.width, layout_height: layout.height };
            }"""
        )
        browser.close()

    return data["boxes"], data["layout_width"], data["layout_height"]


def replace_placeholders(
    filled_html_path: str | Path,
    original_image_path: str | Path,
    output_html_path: str | Path,
    assets_dir: str | Path,
) -> str:
    """Filled HTML'deki her `.img-placeholder`'ı, orijinal screenshot'tan
    kendi (ölçeklenmiş) bbox'ından alınan gerçek crop ile değiştirir.

    Placeholder yoksa (sayfa hiç gerçek görsel içermiyorsa) HTML'i olduğu gibi
    kopyalar. Sonucu döner (ayrıca output_html_path'e de yazar)."""
    filled_html_path = Path(filled_html_path)
    assets_dir = Path(assets_dir)
    output_html_path = Path(output_html_path)
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    html_text = filled_html_path.read_text(encoding="utf-8")

    boxes, layout_width, layout_height = find_placeholder_boxes(filled_html_path)

    if not boxes:
        output_html_path.write_text(html_text, encoding="utf-8")
        return html_text

    with Image.open(original_image_path) as original:
        original = original.convert("RGB")
        scale_x = original.width / layout_width if layout_width > 0 else 1.0
        scale_y = original.height / layout_height if layout_height > 0 else 1.0

        soup = bs4.BeautifulSoup(html_text, "html.parser")
        elements = soup.find_all(class_=PLACEHOLDER_CLASS)

        assets_dir.mkdir(parents=True, exist_ok=True)
        for i, el in enumerate(elements):
            if i >= len(boxes):
                break
            b = boxes[i]
            x1 = max(0, int(b["x"] * scale_x))
            y1 = max(0, int(b["y"] * scale_y))
            x2 = min(original.width, int((b["x"] + b["w"]) * scale_x))
            y2 = min(original.height, int((b["y"] + b["h"]) * scale_y))
            if x2 <= x1 or y2 <= y1:
                continue

            asset_name = f"ph{i}.png"
            original.crop((x1, y1, x2, y2)).save(assets_dir / asset_name)

            img_tag = soup.new_tag("img", src=f"assets/{asset_name}")
            style = el.get("style", "")
            img_tag["style"] = f"{style};display:block;object-fit:cover;"
            el.replace_with(img_tag)

    result = str(soup)
    output_html_path.write_text(result, encoding="utf-8")
    return result
