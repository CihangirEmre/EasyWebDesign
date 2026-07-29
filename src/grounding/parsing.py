"""Aşama 1 — Grounding: model çıktısını parse etme ve dedupe.

Karar (CLAUDE.md §2, Aşama 1): Model çıktısı konum (bbox) + serbest metin
etiket verir; tam tutarlılık (deduplication/çakışma temizleme) pipeline'da
ayrıca yapılmalı.
"""

from __future__ import annotations

import json
import re

from .coords import compute_iou

_BBOX_PATTERN = r'\{\s*"bbox_2d"\s*:\s*\[[\d,\s]+\]\s*,\s*"label"\s*:\s*"[^"]*"\s*\}'


def parse_grounding_output(raw_text: str) -> list[dict]:
    """Model çıktısındaki JSON tespitlerini ayıklar; bozuk/tekrar eden kayıtları atlar."""
    matches = re.findall(_BBOX_PATTERN, raw_text)

    detections: list[dict] = []
    seen: set[tuple] = set()
    for m in matches:
        try:
            obj = json.loads(m)
        except json.JSONDecodeError:
            continue
        key = (tuple(obj["bbox_2d"]), obj["label"])
        if key in seen:
            continue
        seen.add(key)
        detections.append(obj)
    return detections


def merge_tile_detections(all_detections: list[dict], *, iou_threshold: float = 0.5) -> list[dict]:
    """Tile overlap bölgesinde aynı component'in iki tile'da yakalanmasından
    doğan near-duplicate kutuları IoU eşiğine göre eler."""
    merged: list[dict] = []
    for det in all_detections:
        is_duplicate = any(
            det["label"] == existing["label"]
            and compute_iou(det["bbox_2d"], existing["bbox_2d"]) > iou_threshold
            for existing in merged
        )
        if not is_duplicate:
            merged.append(det)
    return merged
