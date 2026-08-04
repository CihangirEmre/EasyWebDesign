"""Aşama 4 — Generation: LLM istemcisi.

Karar güncellemesi (bkz. CLAUDE.md §2, Aşama 4): Gemini API 503 (servis
kullanılamıyor) hatası verdiği için Claude API'ye geçildi — ANA SAĞLAYICI
şu an Claude. Gemini entegrasyonu (load_gemini_model) SİLİNMEDİ, kodda
duruyor; gerekirse `load_generation_model = load_gemini_model` satırına
geri dönülerek tekrar aktif edilebilir.

API key'ler ortam değişkenlerinden okunur (ANTHROPIC_API_KEY / GEMINI_API_KEY),
kodun hiçbir yerinde metin olarak geçmez — ilgili SDK'lar bunu otomatik yapar.
"""

from __future__ import annotations

import anthropic
from google import genai

DEFAULT_CLAUDE_MODEL_ID = "claude-sonnet-5"
DEFAULT_GEMINI_MODEL_ID = "gemini-2.5-flash"


def load_claude_model(model_id: str = DEFAULT_CLAUDE_MODEL_ID):
    """Claude istemcisini döner. API key ANTHROPIC_API_KEY ortam
    değişkeninden okunur (anthropic SDK'sı otomatik yapar)."""
    client = anthropic.Anthropic()
    return client, model_id


def load_gemini_model(model_id: str = DEFAULT_GEMINI_MODEL_ID):
    """Gemini istemcisini döner — ŞU AN KULLANILMIYOR (bkz. modül docstring'i).
    API key GEMINI_API_KEY ortam değişkeninden okunur."""
    client = genai.Client()
    return client, model_id


# Aktif sağlayıcı: Claude. Gemini'ye geri dönmek için bu iki satırı değiştir:
#   DEFAULT_MODEL_ID = DEFAULT_GEMINI_MODEL_ID
#   load_generation_model = load_gemini_model
DEFAULT_MODEL_ID = DEFAULT_CLAUDE_MODEL_ID
load_generation_model = load_claude_model
