"""Aşama 4 — Generation: Qwen2.5-Coder-7B yükleme.

Karar (CLAUDE.md §2, Aşama 4): Qwen2.5-Coder-7B, önce fine-tune'suz
(prompt engineering + few-shot) zero-shot pilot olarak kullanılır. Girdi
artık görsel değil, Aşama 2b'nin ürettiği JSON şema — bu yüzden VLM değil,
düz bir metin-tabanlı kod-LLM (AutoModelForCausalLM) yeterli.
"""

from __future__ import annotations

from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"


def load_generation_model(model_id: str = DEFAULT_MODEL_ID, *, load_in_4bit: bool = False):
    """Qwen2.5-Coder modelini ve tokenizer'ını yükler.

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

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype="auto",
        device_map="auto",
        quantization_config=quantization_config,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    return model, tokenizer
