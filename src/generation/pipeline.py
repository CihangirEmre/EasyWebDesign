"""Aşama 4 — Generation: uçtan uca CLI (ScreenCoder-tarzı basit mimari).

Girdi: src/regions'ın ürettiği `<stem>_regions.json` (en fazla 4 kaba bölge:
sidebar/header/navigation/main_content) + Aşama 0'da normalize edilmiş görsel.
JSON alt-ağacı YOK — her bölge sadece kendi kırpılmış görüntüsü + region
tipine özel doğal dil talimatıyla modele veriliyor (bkz. src/generation/prompts.py).

Üretilen HTML fragment'ları, src/skeleton.py'nin ürettiği stilsiz iskeletteki
ilgili id'li div'in içine enjekte edilir. Bu adımın çıktısı (`<stem>.html`),
main_content içindeki gerçek fotoğraflar için hâlâ boş `img-placeholder`
elemanları içerir — bunlar src/assets/placeholders.py tarafından üretim
SONRASI gerçek crop'larla değiştirilir.

Kullanım:
    python -m src.generation.pipeline --regions-dir regions_results \
        --images-dir data/train/normalized --output-dir generation_results

Claude API kullanır (bkz. src/generation/model.py) — ANTHROPIC_API_KEY ortam
değişkeninin ayarlı olması gerekir.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from src.skeleton import build_skeleton, inject_region_html

from .inference import run_region_generation
from .model import DEFAULT_MODEL_ID, load_generation_model
from .postprocess import extract_html


def run(
    regions_dir: str | Path,
    images_dir: str | Path,
    output_dir: str | Path,
    client,
    model_id: str,
    *,
    max_new_tokens: int = 4096,
) -> None:
    regions_dir = Path(regions_dir)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for regions_path in sorted(regions_dir.glob("*_regions.json")):
        stem = regions_path.stem.removesuffix("_regions")
        regions = json.loads(regions_path.read_text(encoding="utf-8"))

        image_path = next(
            (p for ext in ("png", "jpg", "jpeg") if (p := images_dir / f"{stem}.{ext}").exists()),
            None,
        )
        if image_path is None:
            print(f"⚠ {stem}: görsel bulunamadı, atlanıyor")
            continue
        image = Image.open(image_path).convert("RGB")

        print(f"→ İşleniyor: {stem} ({len(regions)} region)")
        skeleton_html = build_skeleton(regions, image.width, image.height)

        raw_texts: list[str] = []
        for region in regions:
            x1, y1, x2, y2 = (int(v) for v in region["bbox"])
            crop = image.crop((x1, y1, x2, y2))

            raw_text = run_region_generation(
                client, model_id, crop, region["label"], max_new_tokens=max_new_tokens
            )
            raw_texts.append(raw_text)
            region_html = extract_html(raw_text)
            skeleton_html = inject_region_html(skeleton_html, region["id"], region_html)

        (output_dir / f"{stem}_raw.txt").write_text("\n\n---\n\n".join(raw_texts), encoding="utf-8")
        (output_dir / f"{stem}.html").write_text(skeleton_html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 4 — Generation (Claude, ScreenCoder-tarzı bölge bazlı)")
    parser.add_argument("--regions-dir", type=str, required=True)
    parser.add_argument("--images-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="generation_results")
    parser.add_argument("--model-id", type=str, default=DEFAULT_MODEL_ID)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    args = parser.parse_args()

    client, model_id = load_generation_model(args.model_id)
    run(
        args.regions_dir, args.images_dir, args.output_dir, client, model_id,
        max_new_tokens=args.max_new_tokens,
    )


if __name__ == "__main__":
    main()
