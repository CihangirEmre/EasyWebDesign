"""Aşama 2a — Planning: uçtan uca CLI.

Girdi: Aşama 1'in (src/grounding/pipeline.py) ürettiği `<stem>_detections.json`
dosyaları. Model kullanılmaz — tamamen kural-tabanlı geometrik çıkarım.

Kullanım:
    python -m src.planning.pipeline --detections-dir grounding_results \
        --images-dir data/train/normalized --output-dir planning_results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .tree import build_plan_tree, node_to_dict
from .visualize import save_hierarchy_image


def run(detections_dir: str | Path, images_dir: str | Path, output_dir: str | Path) -> None:
    detections_dir = Path(detections_dir)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for det_path in sorted(detections_dir.glob("*_detections.json")):
        stem = det_path.stem.removesuffix("_detections")
        detections = json.loads(det_path.read_text(encoding="utf-8"))

        root = build_plan_tree(detections)
        tree_dict = node_to_dict(root)
        (output_dir / f"{stem}_hierarchy.json").write_text(
            json.dumps(tree_dict, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        image_path = next(
            (p for ext in ("png", "jpg", "jpeg") if (p := images_dir / f"{stem}.{ext}").exists()),
            None,
        )
        if image_path is not None:
            image = Image.open(image_path).convert("RGB")
            save_hierarchy_image(image, root, output_dir / f"{stem}_hierarchy.png", title=stem)

        print(f"→ {stem}: hiyerarşi kaydedildi")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 2a — Planning (kural-tabanlı)")
    parser.add_argument("--detections-dir", type=str, required=True)
    parser.add_argument("--images-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="planning_results")
    args = parser.parse_args()
    run(args.detections_dir, args.images_dir, args.output_dir)


if __name__ == "__main__":
    main()
