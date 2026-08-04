"""Aşama 4 — Generation: model çalıştırma (bölge bazlı, görsel + JSON girdili).

Ana sağlayıcı: Claude API (anthropic SDK) — bkz. src/generation/model.py'deki
karar (Gemini 503 hatası verdiği için değiştirildi). Gemini implementasyonu
(run_region_generation_gemini) SİLİNMEDİ, kodda duruyor ama çağrılmıyor.
"""

from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image

from .prompts import GENERATION_SYSTEM_PROMPT, build_region_prompt


def _image_to_base64_png(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def run_region_generation_claude(
    client, model_id: str, image: Image.Image, region_json: str, *, max_new_tokens: int = 4096
) -> str:
    """Tek bir bölge (root'un bir çocuğu) için, kırpılmış görüntü + JSON
    alt-ağacı birlikte verip HTML fragment'ı üretir (Claude Messages API)."""
    image_b64 = _image_to_base64_png(image)

    response = client.messages.create(
        model=model_id,
        max_tokens=max_new_tokens,
        system=GENERATION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": image_b64},
                    },
                    {"type": "text", "text": build_region_prompt(region_json)},
                ],
            }
        ],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def run_region_generation_gemini(
    client, model_id: str, image: Image.Image, region_json: str, *, max_new_tokens: int = 4096
) -> str:
    """Aynı görev, Gemini API ile — ŞU AN KULLANILMIYOR (bkz. modül docstring'i)."""
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


# Aktif sağlayıcı: Claude. Gemini'ye geri dönmek için:
#   run_region_generation = run_region_generation_gemini
run_region_generation = run_region_generation_claude
