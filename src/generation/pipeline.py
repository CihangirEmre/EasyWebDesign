"""Aşama 4 — Generation: uçtan uca CLI.

Girdi: Aşama 2b'nin (src/formatting) ürettiği `<stem>_formatted.json`.
Aşama 3'ün (src/assets) ürettiği gerçek asset dosyaları `asset_ref`
yollarıyla eşleşecek şekilde çıktı klasörüne kopyalanmalı (bu script
kopyalamaz, sadece HTML üretir — asset'ler ayrı pipeline'dan geliyor).

Kullanım:
    python -m src.generation.pipeline --formatted-dir formatting_results \
        --output-dir generation_results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inference import run_generation
from .model import DEFAULT_MODEL_ID, load_generation_model
from .postprocess import extract_html


def run(
    formatted_dir: str | Path,
    output_dir: str | Path,
    model,
    tokenizer,
    *,
    max_new_tokens: int = 4096,
) -> None:
    formatted_dir = Path(formatted_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for schema_path in sorted(formatted_dir.glob("*_formatted.json")):
        stem = schema_path.stem.removesuffix("_formatted")
        schema_json = schema_path.read_text(encoding="utf-8")

        print(f"→ İşleniyor: {stem}")
        raw_text = run_generation(model, tokenizer, schema_json, max_new_tokens=max_new_tokens)
        html = extract_html(raw_text)

        (output_dir / f"{stem}_raw.txt").write_text(raw_text, encoding="utf-8")
        (output_dir / f"{stem}.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 4 — Generation (Qwen2.5-Coder-7B)")
    parser.add_argument("--formatted-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="generation_results")
    parser.add_argument("--model-id", type=str, default=DEFAULT_MODEL_ID)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    parser.add_argument("--load-in-4bit", action="store_true")
    args = parser.parse_args()

    model, tokenizer = load_generation_model(args.model_id, load_in_4bit=args.load_in_4bit)
    run(
        args.formatted_dir, args.output_dir, model, tokenizer,
        max_new_tokens=args.max_new_tokens,
    )


if __name__ == "__main__":
    main()
