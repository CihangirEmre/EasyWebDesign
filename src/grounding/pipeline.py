"""Aşama 1 — Grounding: uçtan uca zero-shot pilot CLI.

Colab'da kullanım:
    !python -m src.grounding.pipeline --source /content/drive/MyDrive/Design2Code-HARD \
        --output-dir /content/drive/MyDrive/grounding_pilot_results

Not: Design2Code-HARD/ScreenBench gibi dış test setleri (CLAUDE.md §5) bu
komutla yalnızca zero-shot DEĞERLENDİRME için kullanılabilir — hiçbir
koşulda eğitim/fine-tune veri kümesine dahil edilmemeli.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image

from .inference import run_grounding, run_grounding_with_tiling
from .model import DEFAULT_MODEL_ID, load_grounding_model
from .parsing import parse_grounding_output
from .tiling import DEFAULT_MAX_TILE_HEIGHT_RATIO, DEFAULT_OVERLAP_PX
from .visualize import save_annotated_image

IMAGE_EXTENSIONS = ("*.png", "*.jpg", "*.jpeg")


def _resolve_image_paths(source: str | Path | list[str]) -> list[Path]:
    if isinstance(source, (list, tuple)):
        return [Path(p) for p in source]
    source = Path(source)
    if source.is_dir():
        paths: list[Path] = []
        for pattern in IMAGE_EXTENSIONS:
            paths.extend(sorted(source.glob(pattern)))
        return paths
    if source.is_file():
        return [source]
    raise ValueError(f"Geçersiz kaynak: {source}")


def process_images(
    model,
    processor,
    source: str | Path | list[str],
    output_dir: str | Path = "grounding_results",
    *,
    max_new_tokens: int = 2048,
    use_tiling: bool = False,
    max_tile_height_ratio: float = DEFAULT_MAX_TILE_HEIGHT_RATIO,
    overlap_px: int = DEFAULT_OVERLAP_PX,
) -> list[dict]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_paths = _resolve_image_paths(source)
    print(f"İşlenecek görsel sayısı: {len(image_paths)}")

    results_log: list[dict] = []
    for img_path in image_paths:
        print(f"→ İşleniyor: {img_path.name}")
        image = Image.open(img_path).convert("RGB")

        if use_tiling:
            detections, raw_text = run_grounding_with_tiling(
                model, processor, image,
                max_new_tokens=max_new_tokens,
                max_tile_height_ratio=max_tile_height_ratio,
                overlap_px=overlap_px,
            )
        else:
            raw_text = run_grounding(model, processor, image, max_new_tokens=max_new_tokens)
            detections = parse_grounding_output(raw_text)

        (output_dir / f"{img_path.stem}_raw.txt").write_text(raw_text, encoding="utf-8")
        (output_dir / f"{img_path.stem}_detections.json").write_text(
            json.dumps(detections, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        save_annotated_image(
            image, detections,
            save_path=output_dir / f"{img_path.stem}_annotated.png",
            title=f"{img_path.name} — {len(detections)} component",
        )

        results_log.append({"image": img_path.name, "detection_count": len(detections)})

    return results_log


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 1 — Grounding zero-shot pilot")
    parser.add_argument("--source", type=str, required=True, help="Görsel dosyası veya klasörü")
    parser.add_argument("--output-dir", type=str, default="grounding_results")
    parser.add_argument("--model-id", type=str, default=DEFAULT_MODEL_ID)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument(
        "--use-tiling", action="store_true",
        help="Tiling'i aç (varsayılan kapalı — artık tek bir kaba bölge seti tespit "
             "edildiği için tile'lara bölmek riskli: her tile kendi 'main_content'ını "
             "üretebilir).",
    )
    parser.add_argument("--max-tile-height-ratio", type=float, default=DEFAULT_MAX_TILE_HEIGHT_RATIO)
    parser.add_argument("--overlap-px", type=int, default=DEFAULT_OVERLAP_PX)
    parser.add_argument("--load-in-4bit", action="store_true")
    args = parser.parse_args()

    model, processor = load_grounding_model(args.model_id, load_in_4bit=args.load_in_4bit)

    results = process_images(
        model, processor, args.source, args.output_dir,
        max_new_tokens=args.max_new_tokens,
        use_tiling=args.use_tiling,
        max_tile_height_ratio=args.max_tile_height_ratio,
        overlap_px=args.overlap_px,
    )

    summary_path = Path(args.output_dir) / "summary.json"
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Özet kaydedildi: {summary_path}")


if __name__ == "__main__":
    main()
