"""ScreenCoder-tarzı basit mimari — stilsiz iskelet üretimi.

ScreenCoderClone'un `html_generator.py::generate_html()` eşdeğeri: region
bbox'larından, hiçbir stil/renk içermeyen, sadece yüzde-bazlı `position:absolute`
boş <div>'lerden oluşan bir iskelet üretir. Her region'ın gerçek HTML/CSS'i
sonradan src/generation/pipeline.py tarafından bu id'li div'lerin İÇİNE
enjekte edilir (bkz. inject_region_html).

Not: Aşama 2a/2b'nin (eski) recursive hiyerarşi/JSON şema katmanları burada
yok — regionlar zaten düz (en fazla 4), iç içe konteyner gerekmiyor.
"""

from __future__ import annotations

import bs4

_HTML_START = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>skeleton</title>
<style>
  html, body { margin: 0; padding: 0; width: 100%; height: 100%; }
  .canvas { position: relative; width: 100%; height: 100%; box-sizing: border-box; }
  .region { position: absolute; box-sizing: border-box; overflow: hidden; }
</style>
</head>
<body>
<div class="canvas">
"""

_HTML_END = """</div>
</body>
</html>
"""


def build_skeleton(regions: list[dict], canvas_width: int, canvas_height: int) -> str:
    """regions: [{"id": "region_0", "bbox": [x1, y1, x2, y2], ...}] (piksel)."""
    html = _HTML_START
    for region in regions:
        x1, y1, x2, y2 = region["bbox"]
        left = x1 / canvas_width * 100
        top = y1 / canvas_height * 100
        width = (x2 - x1) / canvas_width * 100
        height = (y2 - y1) / canvas_height * 100
        html += (
            f'<div id="{region["id"]}" class="region" '
            f'style="left:{left:.4f}%;top:{top:.4f}%;width:{width:.4f}%;height:{height:.4f}%;">'
            f"</div>\n"
        )
    html += _HTML_END

    soup = bs4.BeautifulSoup(html, "html.parser")
    return soup.prettify()


def inject_region_html(skeleton_html: str, region_id: str, inner_html: str) -> str:
    """skeleton_html'deki `id=region_id` olan div'in İÇİNE inner_html'i ekler."""
    soup = bs4.BeautifulSoup(skeleton_html, "html.parser")
    target = soup.find(id=region_id)
    if target is not None:
        target.append(bs4.BeautifulSoup(inner_html, "html.parser"))
    return str(soup)
