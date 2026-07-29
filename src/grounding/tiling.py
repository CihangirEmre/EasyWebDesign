"""Aşama 1 — Grounding: uzun sayfaları parçalara bölme (tiling).

Not (CLAUDE.md §2, Aşama 1 "Bilinen risk"): Genel VLM'ler piksel-hassas
koordinat tahmininde zayıf olabiliyor; çok uzun (dikey) sayfalarda tek
geçişte tüm componentleri doğru yakalamak zorlaşıyor. Tiling, sayfayı
genişliğe orantılı, üst üste binen (overlap) parçalara bölerek modelin her
parçayı ayrı ayrı analiz etmesini sağlar; overlap bölgesindeki tekrarlar
`parsing.merge_tile_detections` ile temizlenir.
"""

from __future__ import annotations

from PIL import Image

from .coords import denormalize_bbox, normalize_bbox

DEFAULT_MAX_TILE_HEIGHT_RATIO = 1.3
DEFAULT_OVERLAP_PX = 150


def tile_long_page(
    image: Image.Image,
    max_tile_height_ratio: float = DEFAULT_MAX_TILE_HEIGHT_RATIO,
    overlap_px: int = DEFAULT_OVERLAP_PX,
) -> list[tuple[Image.Image, int]]:
    """Uzun bir sayfayı, genişliğe orantılı yükseklikte, overlap'li parçalara böler.

    Kısa sayfalarda (zaten kare-yakını oranda) hiç bölme yapmaz.
    Döner: [(tile_image, y_offset), ...] — y_offset, tile'ın orijinal
    görseldeki başlangıç y koordinatı (piksel).
    """
    w, h = image.size
    tile_height = int(w * max_tile_height_ratio)

    if h <= tile_height:
        return [(image, 0)]

    tiles: list[tuple[Image.Image, int]] = []
    y = 0
    while y < h:
        y_end = min(y + tile_height, h)
        tiles.append((image.crop((0, y, w, y_end)), y))
        if y_end == h:
            break
        y += tile_height - overlap_px
    return tiles


def rescale_tile_detections(
    detections: list[dict],
    *,
    tile_size: tuple[int, int],
    y_offset: int,
    orig_size: tuple[int, int],
) -> list[dict]:
    """Tile-lokal 0-1000 normalize bbox'ları orijinal görsele göre 0-1000
    normalize koordinata dönüştürür (tile piksel → orijinal piksel → normalize)."""
    tile_w, tile_h = tile_size
    orig_w, orig_h = orig_size

    rescaled: list[dict] = []
    for det in detections:
        x1_px, y1_px, x2_px, y2_px = denormalize_bbox(det["bbox_2d"], tile_w, tile_h)
        y1_orig, y2_orig = y1_px + y_offset, y2_px + y_offset
        det = {**det, "bbox_2d": [
            round(v)
            for v in normalize_bbox([x1_px, y1_orig, x2_px, y2_orig], orig_w, orig_h)
        ]}
        rescaled.append(det)
    return rescaled
