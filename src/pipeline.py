"""Master orkestratör — ScreenCoder-tarzı basit mimari (bkz. CLAUDE.md §2).

KARAR GÜNCELLEMESİ: Eski Aşama 2a (Planning/kural-tabanlı hiyerarşi) ve Aşama 2b
(Formatting/zengin JSON şema) tamamen kaldırıldı. Yeni akış 4 aşamalı:

    0. Preprocessing   (değişmedi — Playwright + normalize)
    1. Grounding       (Qwen3-VL, artık SADECE kaba sidebar/header/navigation/
                        main_content bbox'larını tespit ediyor)
    2. Regions         (containment-resolve — model yok, kural-tabanlı)
    3. Generation      (Claude, her region kendi kırpılmış görseli + doğal dil
                        talimatıyla; main_content'teki gerçek fotoğraflar
                        `.img-placeholder` olarak işaretleniyor)
    4. Görsel Yerleştirme (Playwright render + placeholder bbox'ını orijinal
                        screenshot'a ölçekleyip crop — UIED/eşleme YOK)

Girdi olarak URL listesi VE/VEYA doğrudan görsel dosyası/klasörü kabul eder.
URL verilirse Aşama 0 (Playwright screenshot) çalışır; doğrudan görsel
verilirse yakalama adımı atlanır ama normalize adımı YİNE uygulanır.

Ağır bağımlılıklar (playwright/transformers/torch) yalnızca ihtiyaç duyulan
alt-fonksiyon içinde import edilir.

Colab kullanımı:
    !bash scripts/setup_colab.sh
    import os; os.environ["ANTHROPIC_API_KEY"] = "..."
    !python -m src.pipeline --urls-file urls.txt --images photo1.png photo2.png \
        --output-dir /content/drive/MyDrive/pipeline_output
"""

from __future__ import annotations

import argparse
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
    """Kaba sidebar/header/navigation/main_content bbox tespiti (bkz.
    src/grounding/prompts.py'deki güncellenmiş GROUNDING_PROMPT). Tiling
    kapalı — tek bir kaba bölge seti için tile'lara bölmenin getirisi yok."""
    from src.grounding.model import load_grounding_model
    from src.grounding.pipeline import process_images

    model, processor = load_grounding_model(model_id, load_in_4bit=load_in_4bit)
    try:
        process_images(model, processor, normalized_dir, stage1_dir, use_tiling=False)
    finally:
        del model, processor
        _empty_cuda_cache()


def _run_regions(stage1_dir: Path, normalized_dir: Path, stage2_dir: Path) -> None:
    from src.regions.pipeline import run as run_regions

    run_regions(stage1_dir, normalized_dir, stage2_dir)


def _run_generation(stage2_dir: Path, normalized_dir: Path, stage3_dir: Path, *, model_id: str) -> None:
    from src.generation.model import load_generation_model
    from src.generation.pipeline import run as run_generation

    client, model_id = load_generation_model(model_id)
    run_generation(stage2_dir, normalized_dir, stage3_dir, client, model_id)


def _run_placeholder_replace(stage3_dir: Path, normalized_dir: Path, final_dir: Path) -> None:
    from src.assets.pipeline import run as run_assets

    run_assets(stage3_dir, normalized_dir, final_dir)


def run_full_pipeline(
    *,
    urls: list[str] | None = None,
    images: list[str] | None = None,
    output_dir: str | Path = "pipeline_output",
    grounding_model_id: str = "Qwen/Qwen3-VL-8B-Instruct",
    generation_model_id: str = "claude-sonnet-5",
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

    print("== Aşama 1: Grounding (Qwen3-VL, kaba bölge tespiti) ==")
    _run_grounding(
        normalized_dir, output_dir / "stage1",
        model_id=grounding_model_id, load_in_4bit=load_in_4bit,
    )

    print("== Aşama 2: Regions (containment-resolve) ==")
    _run_regions(output_dir / "stage1", normalized_dir, output_dir / "stage2")

    print("== Aşama 3: Generation (Claude, region bazlı, JSON şema yok) ==")
    _run_generation(
        output_dir / "stage2", normalized_dir, output_dir / "stage3",
        model_id=generation_model_id,
    )

    print("== Aşama 4: Görsel Yerleştirme (üretim sonrası, UIED yok) ==")
    final_dir = output_dir / "final"
    _run_placeholder_replace(output_dir / "stage3", normalized_dir, final_dir)

    print(f"Bitti. Çıktılar: {final_dir}")
    return final_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Uçtan uca web2code pipeline'ı")
    parser.add_argument("--urls-file", type=str, default=None, help="Her satırda bir URL")
    parser.add_argument("--images", type=str, nargs="+", default=None, help="Görsel dosyası/dosyaları veya klasör")
    parser.add_argument("--output-dir", type=str, default="pipeline_output")
    parser.add_argument("--grounding-model-id", type=str, default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument("--generation-model-id", type=str, default="claude-sonnet-5")
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
