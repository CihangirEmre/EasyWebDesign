"""Aşama 3 — Asset Extraction: gerçek görselleri kırpıp yerleştirme.

Karar (CLAUDE.md §2, Aşama 3): PIL/OpenCV ile crop — placeholder'lar orijinal
screenshot'tan kırpılan gerçek görsellerle değiştirilir (ScreenCoder'ın
`image_replacer.py` mantığı). Model gerektirmez.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def find_image_nodes(node: dict) -> list[dict]:
    """Şema ağacında tag=='img' olan tüm node'ları (derinlik farketmeksizin) toplar."""
    nodes: list[dict] = []
    if node.get("tag") == "img":
        nodes.append(node)
    for child in node.get("children", []):
        nodes.extend(find_image_nodes(child))
    return nodes


def crop_and_save(image: Image.Image, bbox_px: list[float], save_path: str | Path) -> Path:
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    x1, y1 = max(0, int(bbox_px[0])), max(0, int(bbox_px[1]))
    x2 = min(image.width, max(x1 + 1, int(bbox_px[2])))
    y2 = min(image.height, max(y1 + 1, int(bbox_px[3])))

    crop = image.crop((x1, y1, x2, y2))
    crop.save(save_path, format="PNG")
    return save_path


def extract_assets(schema: dict, image: Image.Image, output_dir: str | Path) -> list[Path]:
    """Şemadaki her img node'u için `asset_ref` yolunda gerçek kırpılmış PNG üretir.

    `asset_ref` (ör. "assets/n2_logo.png") output_dir'e göre relatif kabul edilir.
    """
    output_dir = Path(output_dir)
    saved: list[Path] = []
    for node in find_image_nodes(schema["root"]):
        asset_ref = node.get("asset_ref")
        if not asset_ref:
            continue
        save_path = crop_and_save(image, node["bbox"], output_dir / asset_ref)
        saved.append(save_path)
    return saved
