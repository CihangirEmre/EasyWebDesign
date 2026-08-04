"""Aşama 3 — Görsel Yerleştirme: uçtan uca CLI (üretim SONRASI, ScreenCoder-tarzı).

Girdi: src/generation'ın ürettiği `<stem>.html` (gri `.img-placeholder`'lı) +
Aşama 0'da normalize edilmiş orijinal görsel. Çıktı: her stem için kendi
klasöründe `index.html` + `assets/phN.png`.

Kullanım:
    python -m src.assets.pipeline --generation-dir generation_results \
        --images-dir data/train/normalized --output-dir final_results
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .placeholders import replace_placeholders


def run(generation_dir: str | Path, images_dir: str | Path, output_dir: str | Path) -> None:
    generation_dir = Path(generation_dir)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for html_path in sorted(generation_dir.glob("*.html")):
        stem = html_path.stem
        image_path = next(
            (p for ext in ("png", "jpg", "jpeg") if (p := images_dir / f"{stem}.{ext}").exists()),
            None,
        )
        if image_path is None:
            print(f"⚠ {stem}: orijinal görsel bulunamadı, atlanıyor")
            continue

        target_dir = output_dir / stem
        replace_placeholders(
            html_path, image_path,
            target_dir / "index.html",
            target_dir / "assets",
        )
        print(f"→ {stem}: final HTML yazıldı")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 3 — Görsel Yerleştirme (üretim sonrası)")
    parser.add_argument("--generation-dir", type=str, required=True)
    parser.add_argument("--images-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="final_results")
    args = parser.parse_args()
    run(args.generation_dir, args.images_dir, args.output_dir)


if __name__ == "__main__":
    main()
