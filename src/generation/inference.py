"""Aşama 4 — Generation: model çalıştırma (bölge bazlı, görsel + JSON girdili).

Gemini API (google-genai SDK) kullanıyor — bkz. src/generation/model.py'deki
karar güncellemesi (Qwen2.5-VL-7B yerine).
"""

from __future__ import annotations

from PIL import Image

from .prompts import GENERATION_SYSTEM_PROMPT, build_region_prompt


def run_region_generation(
    client, model_id: str, image: Image.Image, region_json: str, *, max_new_tokens: int = 2048
) -> str:
    """Tek bir bölge (root'un bir çocuğu) için, kırpılmış görüntü + JSON
    alt-ağacı birlikte verip HTML fragment'ı üretir."""
    from google.genai import types

    response = client.models.generate_content(
        model=model_id,
        contents=[image, build_region_prompt(region_json)],
        config=types.GenerateContentConfig(
            system_instruction=GENERATION_SYSTEM_PROMPT,
            max_output_tokens=max_new_tokens,
        ),
    )
    return response.text or ""
