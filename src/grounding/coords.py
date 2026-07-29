"""Aşama 1 — Grounding: koordinat dönüşümleri.

Karar (CLAUDE.md §2, Aşama 1, adım 3): Model çıktısı 0-1000 normalize
skalada gelir → x_piksel = (bbox_değeri/1000) × görsel_genişliği.
"""

from __future__ import annotations

BBox = tuple[float, float, float, float]


def denormalize_bbox(bbox_2d: list[float], width: int, height: int) -> list[float]:
    """0-1000 normalize bbox'ı piksel koordinatına çevirir."""
    x1, y1, x2, y2 = bbox_2d
    return [
        x1 / 1000 * width,
        y1 / 1000 * height,
        x2 / 1000 * width,
        y2 / 1000 * height,
    ]


def normalize_bbox(bbox_px: list[float], width: int, height: int) -> list[float]:
    """Piksel bbox'ı 0-1000 normalize skalaya çevirir (round edilmez)."""
    x1, y1, x2, y2 = bbox_px
    return [
        x1 / width * 1000,
        y1 / height * 1000,
        x2 / width * 1000,
        y2 / height * 1000,
    ]


def compute_iou(box1: BBox, box2: BBox) -> float:
    """İki bbox arasındaki kesişim/birleşim (IoU) oranı."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = area1 + area2 - inter_area

    return inter_area / union_area if union_area > 0 else 0.0
