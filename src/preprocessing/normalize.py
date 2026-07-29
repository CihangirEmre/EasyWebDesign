"""Aşama 0 — Ön İşleme: çözünürlük normalizasyonu.

Karar (CLAUDE.md §2, Aşama 0):
- Qwen3-VL'in resmi min_pixels/max_pixels aralığı kullanılır (mimari tavan değil).
- Resize sonrası boyutlar Qwen3-VL patch boyutunun (32px) katına yuvarlanır.
- Renk augmentasyonu (jitter/hue/brightness) KESİNLİKLE yapılmaz.
- Çıktı formatı PNG (JPEG yasak).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

PATCH_SIZE = 32  # Qwen3-VL patch boyutu

# Qwen3-VL resmi önerilen min/max_pixels aralığı (görsel token bütçesi).
DEFAULT_MIN_PIXELS = 256 * PATCH_SIZE * PATCH_SIZE
DEFAULT_MAX_PIXELS = 1280 * PATCH_SIZE * PATCH_SIZE


@dataclass(frozen=True)
class NormalizedSize:
    width: int
    height: int


def smart_resize(
    width: int,
    height: int,
    *,
    factor: int = PATCH_SIZE,
    min_pixels: int = DEFAULT_MIN_PIXELS,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> NormalizedSize:
    """Qwen3-VL için boyutları patch katına yuvarlar, min/max_pixels aralığına sıkıştırır."""
    if max(width, height) / min(width, height) > 200:
        raise ValueError("En-boy oranı aşırı — tekil boyutlardan biri diğerinin 200 katından fazla.")

    h_bar = max(factor, round(height / factor) * factor)
    w_bar = max(factor, round(width / factor) * factor)

    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = max(factor, math.floor(height / beta / factor) * factor)
        w_bar = max(factor, math.floor(width / beta / factor) * factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = math.ceil(height * beta / factor) * factor
        w_bar = math.ceil(width * beta / factor) * factor

    return NormalizedSize(width=w_bar, height=h_bar)


def normalize_image(
    input_path: str | Path,
    output_path: str | Path,
    *,
    min_pixels: int = DEFAULT_MIN_PIXELS,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> NormalizedSize:
    """PNG görseli Qwen3-VL boyut kısıtlarına göre yeniden boyutlandırır.

    Yalnızca geometrik resize uygulanır — renk augmentasyonu yapılmaz, CSS
    renk kodlarının piksel-hassas doğruluğu korunur.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".png":
        raise ValueError("Çıktı formatı PNG olmalı — JPEG kesinlikle kullanılmamalı.")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as img:
        img = img.convert("RGB")
        target = smart_resize(
            img.width, img.height, min_pixels=min_pixels, max_pixels=max_pixels
        )
        resized = img.resize((target.width, target.height), Image.LANCZOS)
        resized.save(output_path, format="PNG")

    return target
