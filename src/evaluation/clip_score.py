"""Aşama 6 — Değerlendirme: CLIP score ile görsel benzerlik (CLAUDE.md §6).

İki görüntünün (orijinal screenshot vs üretilen HTML'in render'ı) CLIP görsel
embedding'leri arasındaki kosinüs benzerliği hesaplanır — 1.0'a ne kadar
yakınsa üretilen sayfa orijinaline o kadar benziyor demektir. Dış test seti
karşılaştırması değil, tek bir çift (orijinal, render) arası benzerlik.
"""

from __future__ import annotations

from PIL import Image
from transformers import CLIPModel, CLIPProcessor

DEFAULT_MODEL_ID = "openai/clip-vit-base-patch32"


def load_clip_model(model_id: str = DEFAULT_MODEL_ID):
    # use_safetensors=True: torch.load pickle güvenlik kısıtı (CVE-2025-32434)
    # eski torch sürümlerinde .bin ağırlık yüklemesini engelliyor; safetensors
    # bu sınıra tabi değil ve zaten CLIP repo'sunda mevcut.
    model = CLIPModel.from_pretrained(model_id, use_safetensors=True)
    model.eval()
    processor = CLIPProcessor.from_pretrained(model_id)
    return model, processor


def clip_score(image_a: Image.Image, image_b: Image.Image, model, processor) -> float:
    """İki görüntü arasındaki CLIP kosinüs benzerliğini [-1, 1] aralığında döner."""
    import torch

    inputs = processor(images=[image_a, image_b], return_tensors="pt")
    with torch.no_grad():
        # model.get_image_features(...) yerine vision_model + visual_projection
        # elle çağrılıyor: bazı transformers sürümlerinde get_image_features
        # projekte edilmemiş pooler_output'u (768-d) döndürüyor, projekte
        # edilmiş CLIP embedding'i (512-d) değil — bu da kosinüs benzerliğini
        # anlamsızlaştırır. Elle çağrı, sürümden bağımsız doğru embedding'i garantiler.
        pooled = model.vision_model(pixel_values=inputs["pixel_values"]).pooler_output
        features = model.visual_projection(pooled)
    features = features / features.norm(p=2, dim=-1, keepdim=True)
    return (features[0] @ features[1]).item()
