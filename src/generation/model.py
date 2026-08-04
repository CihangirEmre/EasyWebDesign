"""Aşama 4 — Generation: Gemini API istemcisi.

Karar güncellemesi (bkz. CLAUDE.md §2, Aşama 4): Qwen2.5-VL-7B (yerel, Colab
GPU'sunda çalışan açık model) yerine Gemini API'ye geçildi. Gerekçe: bu
oturumda tekrarlayan generation bug'larının (geçersiz CSS property adı,
content'in attribute'a gömülmesi, iç içe <html> sarmalayıcı vb.) hepsi aynı
kök soruna işaret ediyordu — 7B'lik açık modelin talimatlara güvenilir
uymaması. Kapalı, daha güçlü bir model (Gemini) bu güvenilirlik sorununu
azaltıp azaltmadığını test etmek için değiştirildi.

API key GEMINI_API_KEY ortam değişkeninden okunur — google-genai SDK'sı
bunu otomatik yapar, key kodun hiçbir yerinde metin olarak geçmez.
"""

from __future__ import annotations

from google import genai

DEFAULT_MODEL_ID = "gemini-2.5-flash"


def load_generation_model(model_id: str = DEFAULT_MODEL_ID):
    """Gemini istemcisini döner.

    Diğer aşamalardaki (model, processor) çiftiyle arayüz tutarlılığı için
    (client, model_id) döner — ikinci eleman burada bir processor değil,
    her çağrıda hangi Gemini modelinin kullanılacağını taşıyan string'dir.
    """
    client = genai.Client()
    return client, model_id
