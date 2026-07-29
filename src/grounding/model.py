"""Aşama 1 — Grounding: Qwen3-VL model/processor yükleme.

Karar (CLAUDE.md §2, Aşama 1): Qwen3-VL, zero-shot pilot olarak kullanılır
(hiç fine-tune edilmeden). Bu modül yalnızca model/processor yüklemeyi
sarmalar — GPU gerektirir, Colab A100 üzerinde çalıştırılmak üzere
tasarlanmıştır.
"""

from __future__ import annotations

from transformers import AutoModelForImageTextToText, AutoProcessor

DEFAULT_MODEL_ID = "Qwen/Qwen3-VL-8B-Instruct"


def load_grounding_model(
    model_id: str = DEFAULT_MODEL_ID,
    *,
    load_in_4bit: bool = False,
):
    """Qwen3-VL modelini ve processor'ını yükler.

    load_in_4bit=True: VRAM kısıtlı ortamlar için bitsandbytes 4-bit
    quantization uygular (A100 40GB'de genelde gerekmez, daha küçük GPU'lar
    için opsiyonel).
    """
    quantization_config = None
    if load_in_4bit:
        from transformers import BitsAndBytesConfig

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype="bfloat16",
        )

    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        dtype="auto",
        device_map="auto",
        quantization_config=quantization_config,
    )
    processor = AutoProcessor.from_pretrained(model_id)
    return model, processor
