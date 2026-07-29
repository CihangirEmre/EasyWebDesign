"""Aşama 4 — Generation: model çalıştırma."""

from __future__ import annotations

from .prompts import GENERATION_SYSTEM_PROMPT, build_generation_prompt


def run_generation(model, tokenizer, schema_json: str, *, max_new_tokens: int = 4096) -> str:
    messages = [
        {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": build_generation_prompt(schema_json)},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    output = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
    )
    return tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
