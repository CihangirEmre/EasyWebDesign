"""Aşama 2a — Planning: containment (iç içelik) ağacı kurma.

Karar (CLAUDE.md §2, Aşama 2a): Uzamsal hiyerarşi tamamen kural-tabanlı
geometrik algoritma ile çözülür — LLM/VLM kullanılmaz. Her elemanın
ebeveyni, onu kapsayan (kapsanma oranı eşiğin üstünde) tespitler arasından
en küçük alanlıdır ("tightest fit"). Kapsayan bulunamazsa eleman kök (body)
seviyesinde kalır.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import area, containment_ratio

ROOT_BBOX = [0.0, 0.0, 1000.0, 1000.0]
DEFAULT_CONTAINMENT_THRESHOLD = 0.9
# outer alanı inner'dan en az bu kat büyük olmalı — neredeyse eş boyutlu
# (muhtemelen dedupe kaçırılmış) kutuların yanlışlıkla parent-child sayılmasını önler
MIN_AREA_RATIO = 1.02


@dataclass
class Node:
    id: str
    label: str | None
    bbox: list[float]
    children: list["Node"] = field(default_factory=list)
    layout: dict | None = None
    synthetic: bool = False


def build_containment_tree(
    detections: list[dict],
    *,
    threshold: float = DEFAULT_CONTAINMENT_THRESHOLD,
) -> Node:
    """Düz tespit listesinden containment ağacı kurar; kök her zaman [0,0,1000,1000]."""
    nodes = [
        Node(id=f"g{i}", label=d.get("label"), bbox=list(d["bbox_2d"]))
        for i, d in enumerate(detections)
    ]

    root = Node(id="root", label="body", bbox=list(ROOT_BBOX))

    for node in nodes:
        candidates = [
            other
            for other in nodes
            if other is not node
            and area(other.bbox) >= area(node.bbox) * MIN_AREA_RATIO
            and containment_ratio(other.bbox, node.bbox) >= threshold
        ]
        parent = min(candidates, key=lambda o: area(o.bbox)) if candidates else root
        parent.children.append(node)

    return root
