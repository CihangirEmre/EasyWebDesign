"""ScreenCoder-tarzı basit mimari — Aşama 1 çıktısından region listesi üretme, CLI.

Girdi: src/grounding/pipeline.py'nin ürettiği `<stem>_detections.json` dosyaları
(artık her biri en fazla 4 kaydı içeriyor — sidebar/header/navigation/main_content).

Kullanım:
    python -m src.regions.pipeline --detections-dir grounding_results \
        --images-dir data/train/normalized --output-dir regions_results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .resolve import build_regions


def run(detections_dir: str | Path, images_dir: str | Path, output_dir: str | Path) -> None:
    detections_dir = Path(detections_dir)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for det_path in sorted(detections_dir.glob("*_detections.json")):
        stem = det_path.stem.removesuffix("_detections")
        detections = json.loads(det_path.read_text(encoding="utf-8"))

        image_path = next(
            (p for ext in ("png", "jpg", "jpeg") if (p := images_dir / f"{stem}.{ext}").exists()),
            None,
        )
        if image_path is None:
            print(f"⚠ {stem}: görsel bulunamadı, atlanıyor")
            continue

        with Image.open(image_path) as image:
            width, height = image.size

        regions = build_regions(detections, width, height)
        (output_dir / f"{stem}_regions.json").write_text(
            json.dumps(regions, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"→ {stem}: {len(regions)} region")


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaba bölge çözümleme (containment-resolve)")
    parser.add_argument("--detections-dir", type=str, required=True)
    parser.add_argument("--images-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="regions_results")
    args = parser.parse_args()
    run(args.detections_dir, args.images_dir, args.output_dir)


if __name__ == "__main__":
    main()
