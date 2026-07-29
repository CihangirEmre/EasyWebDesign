"""Aşama 3 — Asset Extraction: uçtan uca CLI.

Girdi: Aşama 2b'nin (src/formatting) ürettiği `<stem>_formatted.json` +
karşılık gelen görsel. Model kullanılmaz — yalnızca crop.

Kullanım:
    python -m src.assets.pipeline --formatted-dir formatting_results \
        --images-dir data/train/normalized --output-dir assets_results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .extractor import extract_assets


def run(formatted_dir: str | Path, images_dir: str | Path, output_dir: str | Path) -> None:
    formatted_dir = Path(formatted_dir)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for schema_path in sorted(formatted_dir.glob("*_formatted.json")):
        stem = schema_path.stem.removesuffix("_formatted")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        image_path = next(
            (p for ext in ("png", "jpg", "jpeg") if (p := images_dir / f"{stem}.{ext}").exists()),
            None,
        )
        if image_path is None:
            print(f"⚠ {stem}: görsel bulunamadı, atlanıyor")
            continue

        image = Image.open(image_path).convert("RGB")
        saved = extract_assets(schema, image, output_dir / stem)
        print(f"→ {stem}: {len(saved)} asset kırpıldı")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 3 — Asset Extraction")
    parser.add_argument("--formatted-dir", type=str, required=True)
    parser.add_argument("--images-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="assets_results")
    args = parser.parse_args()
    run(args.formatted_dir, args.images_dir, args.output_dir)


if __name__ == "__main__":
    main()
