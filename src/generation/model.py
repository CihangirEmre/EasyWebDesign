"""Aşama 4 — Generation: Qwen2.5-VL-7B yükleme.

Karar güncellemesi (bkz. CLAUDE.md §2, Aşama 4): ScreenCoder (arXiv:2507.22827)
karşılaştırması sonrası saf metin-tabanlı Qwen2.5-Coder-7B yerine Qwen2.5-VL-7B'ye
geçildi. Gerekçe: metin-only model, JSON şemasındaki kuralları (id, inline
layout, vb.) harfiyen uygulamayı tamamen prompt talimatına güveniyordu — bu bir
garanti değil, ve gerçek üretimlerde model bu kuralları sessizce atlayabildi
(bkz. src/generation/repair.py). VLM, JSON'un yanında bölgenin kırpılmış
görüntüsünü de görerek JSON'da belirsiz/eksik kalan noktaları görsel olarak
doğrulayabiliyor — ScreenCoder'ın modüler mimarisinin asıl kazancı bu.
"""

from __future__ import annotations

from transformers import AutoModelForImageTextToText, AutoProcessor

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"


def load_generation_model(model_id: str = DEFAULT_MODEL_ID, *, load_in_4bit: bool = False):
    """Qwen2.5-VL modelini ve processor'ını yükler.

    load_in_4bit=True: VRAM kısıtlı ortamlar için bitsandbytes 4-bit
    quantization (A100 40GB'de 7B model için genelde gerekmez).
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
