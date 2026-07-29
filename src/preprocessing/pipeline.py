"""Aşama 0 — Ön İşleme: uçtan uca CLI.

URL listesi alır → screenshot yakalar (capture) → gerekirse DOM sınırlarına
göre böler (splitter) → Qwen3-VL boyutuna normalize eder (normalize) →
pHash ile deduplication uygular (dedup).

Kullanım:
    python -m src.preprocessing.pipeline --urls-file urls.txt --output-dir data/train/raw
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from .capture import DEFAULT_VIEWPORT_HEIGHT, DEFAULT_VIEWPORT_WIDTH
from .dedup import dedupe_directory
from .normalize import normalize_image
from .splitter import split_if_needed


def run(
    urls: list[str],
    output_dir: str | Path,
    *,
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
    split_height_threshold: int = 4000,
) -> None:
    output_dir = Path(output_dir)
    raw_dir = output_dir / "raw"
    sections_dir = output_dir / "sections"
    normalized_dir = output_dir / "normalized"
    for d in (raw_dir, sections_dir, normalized_dir):
        d.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=1.0,
        )

        for idx, url in enumerate(urls):
            stem = f"screenshot_{idx:04d}"
            raw_path = raw_dir / f"{stem}.png"

            page.goto(url, wait_until="networkidle")
            page.screenshot(path=str(raw_path), full_page=True, type="png")

            sections = split_if_needed(
                page, raw_path, sections_dir / stem, height_threshold=split_height_threshold
            )
            sources = sections if sections else [raw_path]

            for src_path in sources:
                out_path = normalized_dir / src_path.name
                normalize_image(src_path, out_path)

        browser.close()

    unique, duplicates = dedupe_directory(normalized_dir)
    print(f"Yakalanan URL sayısı: {len(urls)}")
    print(f"Normalize edilmiş görsel sayısı: {len(list(normalized_dir.glob('*.png')))}")
    print(f"Benzersiz görsel sayısı: {len(unique)}")
    print(f"Bulunan tekrar (pHash) çifti: {len(duplicates)}")
    for pair in duplicates:
        print(f"  DUPLICATE: {pair.a.name} ~ {pair.b.name} (distance={pair.distance})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aşama 0 — Ön İşleme pipeline'ı")
    parser.add_argument("--urls-file", type=str, required=True, help="Her satırda bir URL içeren dosya")
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--viewport-width", type=int, default=DEFAULT_VIEWPORT_WIDTH)
    parser.add_argument("--viewport-height", type=int, default=DEFAULT_VIEWPORT_HEIGHT)
    parser.add_argument("--split-height-threshold", type=int, default=4000)
    args = parser.parse_args()

    urls = [
        line.strip()
        for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    run(
        urls,
        args.output_dir,
        viewport_width=args.viewport_width,
        viewport_height=args.viewport_height,
        split_height_threshold=args.split_height_threshold,
    )


if __name__ == "__main__":
    main()
