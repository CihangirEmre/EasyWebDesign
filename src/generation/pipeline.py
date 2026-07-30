"""Aşama 4 — Generation: uçtan uca CLI.

Girdi: Aşama 2b'nin (src/formatting) ürettiği `<stem>_formatted.json` + Aşama
0/1'de kullanılan normalize edilmiş görsel. Sayfa tek seferde değil, ScreenCoder
tarzı bölge bölge (root'un doğrudan çocukları, bkz. src/generation/regions.py)
işlenir: her bölge kırpılıp kendi JSON alt-ağacıyla birlikte VLM'e verilir,
üretilen HTML fragment'ları deterministik olarak root'un içine yerleştirilir
(bkz. src/generation/assembly.py).

Aşama 3'ün (src/assets) ürettiği gerçek asset dosyaları `asset_ref`
yollarıyla eşleşecek şekilde çıktı klasörüne kopyalanmalı (bu script
kopyalamaz, sadece HTML üretir — asset'ler ayrı pipeline'dan geliyor).

Kullanım:
    python -m src.generation.pipeline --formatted-dir formatting_results \
        --images-dir data/train/normalized --output-dir generation_results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .assembly import assemble_document
from .inference import run_region_generation
from .model import DEFAULT_MODEL_ID, load_generation_model
from .postprocess import extract_html
from .regions import select_regions
from .repair import repair_flex_properties, repair_image_srcs


def run(
    formatted_dir: str | Path,
    images_dir: str | Path,
    output_dir: str | Path,
    model,
    processor,
    *,
    max_new_tokens: int = 2048,
) -> None:
    formatted_dir = Path(formatted_dir)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for schema_path in sorted(formatted_dir.glob("*_formatted.json")):
        stem = schema_path.stem.removesuffix("_formatted")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        root = schema["root"]

        image_path = next(
            (p for ext in ("png", "jpg", "jpeg") if (p := images_dir / f"{stem}.{ext}").exists()),
            None,
        )
        if image_path is None:
            print(f"⚠ {stem}: görsel bulunamadı, atlanıyor")
            continue
        image = Image.open(image_path).convert("RGB")

        print(f"→ İşleniyor: {stem}")
        raw_texts: list[str] = []
        region_htmls: list[str] = []
        for region in select_regions(root):
            x1, y1, x2, y2 = (int(v) for v in region["bbox"])
            crop = image.crop((x1, y1, x2, y2))
            region_json = json.dumps(region, ensure_ascii=False)

            raw_text = run_region_generation(model, processor, crop, region_json, max_new_tokens=max_new_tokens)
            raw_texts.append(raw_text)
            region_htmls.append(extract_html(raw_text))

        html = assemble_document(root, region_htmls)
        html = repair_flex_properties(html)
        html = repair_image_srcs(html, root)

        (output_dir / f"{stem}_raw.txt").write_text("\n\n---\n\n".join(raw_texts), encoding="utf-8")
        (output_dir / f"{stem}.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 4 — Generation (Qwen2.5-VL-7B, bölge bazlı)")
    parser.add_argument("--formatted-dir", type=str, required=True)
    parser.add_argument("--images-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="generation_results")
    parser.add_argument("--model-id", type=str, default=DEFAULT_MODEL_ID)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--load-in-4bit", action="store_true")
    args = parser.parse_args()

    model, processor = load_generation_model(args.model_id, load_in_4bit=args.load_in_4bit)
    run(
        args.formatted_dir, args.images_dir, args.output_dir, model, processor,
        max_new_tokens=args.max_new_tokens,
    )


if __name__ == "__main__":
    main()
