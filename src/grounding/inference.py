"""Aşama 1 — Grounding: model çalıştırma (tekli görsel ve tiling'li tam sayfa).
"""

from __future__ import annotations

from PIL import Image

from .parsing import merge_tile_detections, parse_grounding_output
from .prompts import GROUNDING_PROMPT
from .tiling import (
    DEFAULT_MAX_TILE_HEIGHT_RATIO,
    DEFAULT_OVERLAP_PX,
    rescale_tile_detections,
    tile_long_page,
)


def run_grounding(model, processor, image: Image.Image, *, prompt: str = GROUNDING_PROMPT, max_new_tokens: int = 4096) -> str:
    """Modeli tek bir görsel/tile üzerinde çalıştırır, ham metin çıktısını döner."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    return processor.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


def run_grounding_with_tiling(
    model,
    processor,
    image: Image.Image,
    *,
    max_new_tokens: int = 4096,
    max_tile_height_ratio: float = DEFAULT_MAX_TILE_HEIGHT_RATIO,
    overlap_px: int = DEFAULT_OVERLAP_PX,
) -> tuple[list[dict], str]:
    """Uzun sayfalarda otomatik tiling uygulayarak grounding çalıştırır.

    Sayfa tile_long_page eşiğini aşmıyorsa tek geçişte, aşıyorsa parça parça
    çalıştırıp koordinatları orijinal görsele göre yeniden ölçekler ve
    IoU-tabanlı dedupe ile birleştirir.
    """
    tiles = tile_long_page(image, max_tile_height_ratio, overlap_px)

    if len(tiles) == 1:
        raw_text = run_grounding(model, processor, image, max_new_tokens=max_new_tokens)
        return parse_grounding_output(raw_text), raw_text

    all_detections: list[dict] = []
    combined_raw: list[str] = []

    for i, (tile_img, y_offset) in enumerate(tiles):
        raw_text = run_grounding(model, processor, tile_img, max_new_tokens=max_new_tokens)
        tile_detections = parse_grounding_output(raw_text)
        rescaled = rescale_tile_detections(
            tile_detections,
            tile_size=tile_img.size,
            y_offset=y_offset,
            orig_size=image.size,
        )
        all_detections.extend(rescaled)
        combined_raw.append(f"--- Tile {i + 1} (y_offset={y_offset}) ---\n{raw_text}")

    merged_detections = merge_tile_detections(all_detections)
    return merged_detections, "\n\n".join(combined_raw)
