"""Aşama 0 — Ön İşleme: büyük sayfa bölme.

Karar (CLAUDE.md §2, Aşama 0): Büyük sayfalar DOM/section sınırlarına göre
bölünmeli (DCGen'in "divide and conquer" mantığı), rastgele piksel
aralıklarına göre DEĞİL.

Bölme, canlı Playwright sayfasından üst düzey (body'nin doğrudan çocukları)
semantik section sınırları okunarak yapılır; bu sınırlar orijinal ekran
görüntüsü üzerinde dikey kırpma için kullanılır.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page

SECTION_TAGS = ("header", "nav", "main", "section", "footer", "div", "article", "aside")

_BOUNDARY_JS = """
(tags) => {
  const body = document.body;
  const results = [];
  for (const child of Array.from(body.children)) {
    const tag = child.tagName.toLowerCase();
    if (!tags.includes(tag)) continue;
    const rect = child.getBoundingClientRect();
    if (rect.height <= 0) continue;
    results.push({
      tag,
      top: Math.round(rect.top + window.scrollY),
      bottom: Math.round(rect.bottom + window.scrollY),
    });
  }
  return results;
}
"""


@dataclass(frozen=True)
class SectionBoundary:
    tag: str
    top: int
    bottom: int


def get_section_boundaries(page: Page) -> list[SectionBoundary]:
    """body'nin doğrudan çocuklarının dikey (top/bottom) sınırlarını okur."""
    raw = page.evaluate(_BOUNDARY_JS, list(SECTION_TAGS))
    return [SectionBoundary(**item) for item in raw]


def split_by_sections(
    image_path: str | Path,
    boundaries: list[SectionBoundary],
    output_dir: str | Path,
    *,
    stem: str = "section",
) -> list[Path]:
    """Tam sayfa görselini section sınırlarına göre dikey olarak kırpar."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    with Image.open(image_path) as img:
        width, height = img.size
        for idx, b in enumerate(boundaries):
            top = max(0, min(b.top, height))
            bottom = max(0, min(b.bottom, height))
            if bottom <= top:
                continue
            crop = img.crop((0, top, width, bottom))
            out_path = output_dir / f"{stem}_{idx:03d}_{b.tag}.png"
            crop.save(out_path, format="PNG")
            outputs.append(out_path)
    return outputs


def split_if_needed(
    page: Page,
    image_path: str | Path,
    output_dir: str | Path,
    *,
    height_threshold: int = 4000,
) -> list[Path]:
    """Sayfa yüksekliği eşiği aşıyorsa DOM sınırlarına göre böler.

    Aşmıyorsa boş liste döner — çağıran taraf tam sayfayı olduğu gibi kullanır.
    """
    with Image.open(image_path) as img:
        height = img.height
    if height <= height_threshold:
        return []

    boundaries = get_section_boundaries(page)
    if not boundaries:
        return []
    return split_by_sections(image_path, boundaries, output_dir)
