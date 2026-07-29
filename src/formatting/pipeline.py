"""Aşama 2b — Formatting: uçtan uca CLI.

Girdi: Aşama 2a'nın (src/planning) ürettiği `<stem>_hierarchy.json` +
karşılık gelen görsel (Aşama 0/1'de kullanılan normalize edilmiş görsel).
Model kullanılmaz — yalnızca şema dönüşümü + renk örnekleme + opsiyonel OCR.

Kullanım:
    python -m src.formatting.pipeline --hierarchy-dir planning_results \
        --images-dir data/train/normalized --output-dir formatting_results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .schema import build_formatted_schema


def run(hierarchy_dir: str | Path, images_dir: str | Path, output_dir: str | Path) -> None:
    hierarchy_dir = Path(hierarchy_dir)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for hierarchy_path in sorted(hierarchy_dir.glob("*_hierarchy.json")):
        stem = hierarchy_path.stem.removesuffix("_hierarchy")
        plan_root = json.loads(hierarchy_path.read_text(encoding="utf-8"))

        image_path = next(
            (p for ext in ("png", "jpg", "jpeg") if (p := images_dir / f"{stem}.{ext}").exists()),
            None,
        )
        if image_path is None:
            print(f"⚠ {stem}: görsel bulunamadı, atlanıyor")
            continue

        image = Image.open(image_path).convert("RGB")
        schema = build_formatted_schema(plan_root, image, source_image=image_path.name)

        (output_dir / f"{stem}_formatted.json").write_text(
            json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"→ {stem}: formatted schema kaydedildi")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 2b — Formatting")
    parser.add_argument("--hierarchy-dir", type=str, required=True)
    parser.add_argument("--images-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="formatting_results")
    args = parser.parse_args()
    run(args.hierarchy_dir, args.images_dir, args.output_dir)


if __name__ == "__main__":
    main()
