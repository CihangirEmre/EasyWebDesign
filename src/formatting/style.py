"""Aşama 2b — Formatting: stil bilgisi çıkarımı (renk — "varsa", CLAUDE.md §2).

Font boyutu/ağırlığı gibi bilgiler piksel analizinden güvenilir çıkarılamadığı
için bu pilot sürümde atlanıyor (açık/yetersiz kalan konu — ileride OCR/font
tespiti ile genişletilebilir).
"""

from __future__ import annotations

import statistics
from collections import Counter

from PIL import Image

DEFAULT_PHOTO_STDDEV_THRESHOLD = 15.0


def dominant_color(image: Image.Image, bbox_px: list[float]) -> str:
    """Bölgenin baskın rengini (çoğunlukla arka plan) hex olarak döner."""
    x1, y1, x2, y2 = (max(0, int(v)) for v in bbox_px)
    x2, y2 = max(x2, x1 + 1), max(y2, y1 + 1)
    crop = image.crop((x1, y1, x2, y2)).convert("RGB")
    crop = crop.resize((32, 32))
    most_common = Counter(crop.getdata()).most_common(1)[0][0]
    return "#{:02x}{:02x}{:02x}".format(*most_common)


def looks_photographic(
    image: Image.Image, bbox_px: list[float], *, std_threshold: float = DEFAULT_PHOTO_STDDEV_THRESHOLD
) -> bool:
    """Bölge düz renkli bir UI dolgusu mu, yoksa fotoğraf/thumbnail gibi mi
    görünüyor? Piksel varyansına (gri ton std sapması) bakar — düz renk
    dolgularda varyans neredeyse sıfırdır, fotoğraflarda yüksektir.

    Neden gerekli: Aşama 1 (grounding) bazen bir video thumbnail'ını "image"
    yerine "card" etiketleyebiliyor (model çıktısı deterministik değil); bu
    durumda etikete dayalı tag eşlemesi (tags.py) onu <section> yapıyor ve
    asset_ref hiç atanmıyordu — gerçek fotoğraf tamamen kayboluyordu. Bu
    kontrol, etiketten bağımsız olarak "burada gerçekten bir fotoğraf var mı"
    sorusunu doğrudan piksellerden cevaplar.
    """
    x1, y1, x2, y2 = (max(0, int(v)) for v in bbox_px)
    x2, y2 = max(x2, x1 + 1), max(y2, y1 + 1)
    crop = image.crop((x1, y1, x2, y2)).convert("L")
    # NEAREST kullanılıyor: BICUBIC/BILINEAR gibi yumuşatıcı filtreler gürültüyü
    # ortalamaya çekip varyansı yapay olarak düşürür, fotoğraf tespitini bozar.
    pixels = list(crop.resize((32, 32), Image.NEAREST).getdata())
    if len(pixels) < 2:
        return False
    return statistics.pstdev(pixels) >= std_threshold


def extract_style(
    image: Image.Image, bbox_px: list[float], *, synthetic: bool = False
) -> dict | None:
    """Sentetik (görselde karşılığı olmayan) wrapper node'lar için stil üretilmez."""
    if synthetic:
        return None
    return {"bg_color": dominant_color(image, bbox_px)}
