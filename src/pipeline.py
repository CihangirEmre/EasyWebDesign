"""Master orkestratör — Aşama 0'dan Aşama 4'e kadar tüm pipeline'ı zincirler.

Girdi olarak URL listesi VE/VEYA doğrudan görsel dosyası/klasörü kabul eder
(hedef: projenin sonunda ikisinin de desteklenmesi). URL verilirse Aşama 0
(Playwright screenshot) çalışır; doğrudan görsel verilirse yakalama adımı
atlanır ama Qwen3-VL boyut kısıtı için normalize adımı YİNE uygulanır — Aşama
0'ın normalize kararı girdi kaynağından bağımsız geçerlidir.

Ağır bağımlılıklar (playwright/transformers/torch) yalnızca ihtiyaç duyulan
alt-fonksiyon içinde import edilir; bu sayede bu dosya, o bağımlılıklar kurulu
olmasa bile (ör. yerel geliştirme ortamında) import edilip CLI argümanları
test edilebilir.

Colab kullanımı:
    !bash scripts/setup_colab.sh
    !python -m src.pipeline --urls-file urls.txt --images photo1.png photo2.png \
        --output-dir /content/drive/MyDrive/pipeline_output
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


def _empty_cuda_cache() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def _resolve_image_inputs(images: list[str]) -> list[Path]:
    """--images argümanı hem dosya yollarını hem de bir klasörü kabul eder."""
    resolved: list[Path] = []
    for item in images:
        p = Path(item)
        if p.is_dir():
            for ext in IMAGE_EXTENSIONS:
                resolved.extend(sorted(p.glob(f"*{ext}")))
        elif p.is_file():
            resolved.append(p)
        else:
            raise ValueError(f"Geçersiz görsel yolu: {item}")
    return resolved


def _prepare_stage0(
    urls: list[str] | None,
    images: list[str] | None,
    stage0_dir: Path,
    *,
    viewport_width: int,
    viewport_height: int,
    split_height_threshold: int,
) -> Path:
    """URL'lerden screenshot + doğrudan görsellerden normalize edilmiş çıktıyı
    aynı `normalized/` klasöründe birleştirir."""
    from PIL import Image

    from src.preprocessing.normalize import normalize_image

    normalized_dir = stage0_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    if urls:
        from src.preprocessing.pipeline import run as run_preprocessing

        run_preprocessing(
            urls, stage0_dir,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            split_height_threshold=split_height_threshold,
        )

    if images:
        raw_dir = stage0_dir / "raw_uploads"
        raw_dir.mkdir(parents=True, exist_ok=True)
        for i, img_path in enumerate(_resolve_image_inputs(images)):
            stem = f"upload_{i:04d}"
            raw_copy = raw_dir / f"{stem}.png"
            Image.open(img_path).convert("RGB").save(raw_copy, format="PNG")
            normalize_image(raw_copy, normalized_dir / f"{stem}.png")

    return normalized_dir


def _run_grounding(normalized_dir: Path, stage1_dir: Path, *, model_id: str, load_in_4bit: bool) -> None:
    from src.grounding.model import load_grounding_model
    from src.grounding.pipeline import process_images

    model, processor = load_grounding_model(model_id, load_in_4bit=load_in_4bit)
    try:
        process_images(model, processor, normalized_dir, stage1_dir)
    finally:
        del model, processor
        _empty_cuda_cache()


def _run_generation(stage2b_dir: Path, stage4_dir: Path, *, model_id: str, load_in_4bit: bool) -> None:
    from src.generation.model import load_generation_model
    from src.generation.pipeline import run as run_generation

    model, tokenizer = load_generation_model(model_id, load_in_4bit=load_in_4bit)
    try:
        run_generation(stage2b_dir, stage4_dir, model, tokenizer)
    finally:
        del model, tokenizer
        _empty_cuda_cache()


def _assemble_final(stage3_dir: Path, stage4_dir: Path, final_dir: Path) -> None:
    """Her görsel için üretilen HTML'i, kırpılmış asset'leriyle birlikte
    doğrudan açılabilir tek bir klasörde toplar."""
    final_dir.mkdir(parents=True, exist_ok=True)
    for html_path in sorted(stage4_dir.glob("*.html")):
        stem = html_path.stem
        target_dir = final_dir / stem
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(html_path, target_dir / "index.html")

        assets_src = stage3_dir / stem / "assets"
        if assets_src.exists():
            shutil.copytree(assets_src, target_dir / "assets", dirs_exist_ok=True)


def run_full_pipeline(
    *,
    urls: list[str] | None = None,
    images: list[str] | None = None,
    output_dir: str | Path = "pipeline_output",
    grounding_model_id: str = "Qwen/Qwen3-VL-8B-Instruct",
    generation_model_id: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    load_in_4bit: bool = False,
    viewport_width: int = 1280,
    viewport_height: int = 800,
    split_height_threshold: int = 4000,
) -> Path:
    if not urls and not images:
        raise ValueError("En az bir --urls-file veya --images girdisi verilmeli.")

    output_dir = Path(output_dir)

    print("== Aşama 0: Ön İşleme ==")
    normalized_dir = _prepare_stage0(
        urls, images, output_dir / "stage0",
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        split_height_threshold=split_height_threshold,
    )

    print("== Aşama 1: Grounding (Qwen3-VL) ==")
    _run_grounding(
        normalized_dir, output_dir / "stage1",
        model_id=grounding_model_id, load_in_4bit=load_in_4bit,
    )

    print("== Aşama 2a: Planning (kural-tabanlı) ==")
    from src.planning.pipeline import run as run_planning

    run_planning(output_dir / "stage1", normalized_dir, output_dir / "stage2a")

    print("== Aşama 2b: Formatting ==")
    from src.formatting.pipeline import run as run_formatting

    run_formatting(output_dir / "stage2a", normalized_dir, output_dir / "stage2b")

    print("== Aşama 3: Asset Extraction ==")
    from src.assets.pipeline import run as run_assets

    run_assets(output_dir / "stage2b", normalized_dir, output_dir / "stage3")

    print("== Aşama 4: Generation (Qwen2.5-Coder-7B) ==")
    _run_generation(
        output_dir / "stage2b", output_dir / "stage4",
        model_id=generation_model_id, load_in_4bit=load_in_4bit,
    )

    print("== Son montaj ==")
    final_dir = output_dir / "final"
    _assemble_final(output_dir / "stage3", output_dir / "stage4", final_dir)
    print(f"Bitti. Çıktılar: {final_dir}")
    return final_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Uçtan uca web2code pipeline'ı")
    parser.add_argument("--urls-file", type=str, default=None, help="Her satırda bir URL")
    parser.add_argument("--images", type=str, nargs="+", default=None, help="Görsel dosyası/dosyaları veya klasör")
    parser.add_argument("--output-dir", type=str, default="pipeline_output")
    parser.add_argument("--grounding-model-id", type=str, default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument("--generation-model-id", type=str, default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--viewport-width", type=int, default=1280)
    parser.add_argument("--viewport-height", type=int, default=800)
    parser.add_argument("--split-height-threshold", type=int, default=4000)
    args = parser.parse_args()

    urls = None
    if args.urls_file:
        urls = [
            line.strip()
            for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    run_full_pipeline(
        urls=urls,
        images=args.images,
        output_dir=args.output_dir,
        grounding_model_id=args.grounding_model_id,
        generation_model_id=args.generation_model_id,
        load_in_4bit=args.load_in_4bit,
        viewport_width=args.viewport_width,
        viewport_height=args.viewport_height,
        split_height_threshold=args.split_height_threshold,
    )


if __name__ == "__main__":
    main()
