"""Aşama 6 — Değerlendirme: uçtan uca CLIP score raporu.

Girdi: orijinal (normalize edilmiş) screenshot'lar + Aşama 4'ün ürettiği HTML
çıktıları. İki klasör düzenini de destekler:
  - final montaj çıktısı: <generated-dir>/<stem>/index.html  (bkz. src/pipeline.py _assemble_final)
  - ham generation çıktısı: <generated-dir>/<stem>.html      (bkz. src/generation/pipeline.py)

Her sayfa için: (1) HTML Playwright ile render edilir, (2) orijinal görüntü
ile render arasındaki CLIP score hesaplanır.

Kullanım:
    python -m src.evaluation.pipeline --originals-dir data/train/normalized \
        --generated-dir pipeline_output/final --output-dir eval_results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .clip_score import clip_score, load_clip_model
from .render import render_html


def _find_html_files(generated_dir: Path) -> dict[str, Path]:
    """stem -> html dosya yolu eşlemesi (alt klasör veya düz dosya, her iki düzen)."""
    found: dict[str, Path] = {}
    for index_html in sorted(generated_dir.glob("*/index.html")):
        found[index_html.parent.name] = index_html
    for html_path in sorted(generated_dir.glob("*.html")):
        found.setdefault(html_path.stem, html_path)
    return found


def run(originals_dir: str | Path, generated_dir: str | Path, output_dir: str | Path) -> dict[str, float]:
    originals_dir = Path(originals_dir)
    generated_dir = Path(generated_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model, processor = load_clip_model()
    scores: dict[str, float] = {}

    for stem, html_path in _find_html_files(generated_dir).items():
        original_path = next(
            (p for ext in ("png", "jpg", "jpeg") if (p := originals_dir / f"{stem}.{ext}").exists()),
            None,
        )
        if original_path is None:
            print(f"⚠ {stem}: orijinal görsel bulunamadı, atlanıyor")
            continue

        render_path = output_dir / f"{stem}_render.png"
        render_html(html_path, render_path)

        original_img = Image.open(original_path).convert("RGB")
        render_img = Image.open(render_path).convert("RGB")
        score = clip_score(original_img, render_img, model, processor)
        scores[stem] = score
        print(f"→ {stem}: CLIP score = {score:.4f}")

    (output_dir / "clip_scores.json").write_text(
        json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if scores:
        print(f"\nOrtalama CLIP score: {sum(scores.values()) / len(scores):.4f}")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 6 — Değerlendirme (CLIP score)")
    parser.add_argument("--originals-dir", type=str, required=True)
    parser.add_argument("--generated-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="eval_results")
    args = parser.parse_args()
    run(args.originals_dir, args.generated_dir, args.output_dir)


if __name__ == "__main__":
    main()
