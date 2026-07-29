"""Aşama 2a — Planning: geometrik temel işlemler.

Aşama 1'in çıktısındaki bbox'lar 0-1000 normalize skalada. Kapsanma/örtüşme
oranları eksen-bazlı orantılardan çıkarıldığı için normalize skalada
çalışmak, piksel skalasında çalışmakla aynı sonucu verir (anisotropik
ölçekleme kapsanma ilişkisini bozmaz) — bu yüzden bu modül gerçek piksel
boyutuna ihtiyaç duymaz.
"""

from __future__ import annotations

BBox = list[float]


def area(box: BBox) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def intersection_area(a: BBox, b: BBox) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def containment_ratio(outer: BBox, inner: BBox) -> float:
    """inner'ın ne kadarının outer içinde kaldığı (0-1). inner alanı 0 ise 0 döner."""
    inner_area = area(inner)
    if inner_area <= 0:
        return 0.0
    return intersection_area(outer, inner) / inner_area


def axis_overlap_ratio(a_range: tuple[float, float], b_range: tuple[float, float]) -> float:
    """İki 1D aralığın örtüşme oranı — kesişim/birleşim (Jaccard, 0-1).

    Kısa aralığa göre normalize etmek YANLIŞ: küçük bir eleman (ör. 24px'lik
    bir sidebar metni), çok daha uzun bir elemanın (ör. 285px'lik bir video
    thumbnail'ı) aralığına tamamen düşerse oran hep 1.0 çıkar ve ikisi
    görsel olarak aynı "satırda" olmasa da aynı banda düşer — bu gerçek bir
    pilot testte (sidebar'ın video ızgarasıyla birleşmesi) tespit edildi.
    Jaccard, boy farkı büyük elemanları artık aynı satır saymıyor.
    """
    a1, a2 = a_range
    b1, b2 = b_range
    inter = max(0.0, min(a2, b2) - max(a1, b1))
    union = max(a2, b2) - min(a1, b1)
    if union <= 0:
        return 0.0
    return inter / union


def y_range(box: BBox) -> tuple[float, float]:
    return box[1], box[3]


def x_range(box: BBox) -> tuple[float, float]:
    return box[0], box[2]


def union_bbox(boxes: list[BBox]) -> BBox:
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]
