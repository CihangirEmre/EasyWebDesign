"""Aşama 4 — Generation: model çalıştırma (bölge bazlı, görsel + JSON girdili)."""

from __future__ import annotations

from PIL import Image

from .prompts import GENERATION_SYSTEM_PROMPT, build_region_prompt


def run_region_generation(
    model, processor, image: Image.Image, region_json: str, *, max_new_tokens: int = 2048
) -> str:
    """Tek bir bölge (root'un bir çocuğu) için, kırpılmış görüntü + JSON
    alt-ağacı birlikte verip HTML fragment'ı üretir."""
    messages = [
        {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": build_region_prompt(region_json)},
            ],
        },
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
