"""ScreenCoder-tarzı basit mimari — kaba bölge çözümleme.

Girdi: Aşama 1'in (src/grounding, artık sadece sidebar/header/navigation/
main_content arayan kaba prompt — bkz. src/grounding/prompts.py) ürettiği
`{bbox_2d, label}` tespit listesi (0-1000 normalize).

Karar (ScreenCoderClone'un `block_parsor.py::resolve_containment`'ından
adapte): büyük düzen bileşenleri birbirini İÇERMEMELİ — bir bbox diğerini
tamamen kapsıyorsa, küçük olanı (muhtemelen aynı bölgenin yanlışlıkla ikinci
kez, daha dar tespit edilmiş hali) atılır. Model çağrısı YOK — tamamen
kural-tabanlı, model.py/inference.py'ye bağımlı değil.
"""

from __future__ import annotations

from src.grounding.coords import denormalize_bbox

BBox = tuple[float, float, float, float]


def _contains(box_a: BBox, box_b: BBox) -> bool:
    """box_a, box_b'yi tamamen kapsıyor mu?"""
    xa1, ya1, xa2, ya2 = box_a
    xb1, yb1, xb2, yb2 = box_b
    return xa1 <= xb1 and ya1 <= yb1 and xa2 >= xb2 and ya2 >= yb2


def resolve_containment(detections: list[dict]) -> list[dict]:
    """Bir bbox diğerini tamamen kapsıyorsa, kapsananı listeden çıkarır."""
    removed: set[int] = set()
    for i in range(len(detections)):
        for j in range(len(detections)):
            if i == j or i in removed or j in removed:
                continue
            box_i = tuple(detections[i]["bbox_2d"])
            box_j = tuple(detections[j]["bbox_2d"])
            if _contains(box_i, box_j) or _contains(box_j, box_i):
                removed.add(j)
    return [d for idx, d in enumerate(detections) if idx not in removed]


def build_regions(detections: list[dict], image_width: int, image_height: int) -> list[dict]:
    """Normalize tespitleri, containment-resolve uygulanmış piksel bbox'lı
    region listesine çevirir: [{"id": "region_0", "label": "...", "bbox": [x1,y1,x2,y2]}]"""
    resolved = resolve_containment(detections)
    regions: list[dict] = []
    for i, det in enumerate(resolved):
        bbox_px = [round(v) for v in denormalize_bbox(det["bbox_2d"], image_width, image_height)]
        regions.append({"id": f"region_{i}", "label": det["label"], "bbox": bbox_px})
    return regions
