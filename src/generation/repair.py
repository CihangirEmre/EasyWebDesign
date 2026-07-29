"""Aşama 4 — Generation: deterministik post-process onarımı.

Gözlem (ilk pilot): Qwen2.5-Coder, logo görseli için `src` HTML attribute'u
yazmak yerine geçersiz bir CSS satırı üretti (`img.logo { src: assets/n3_logo.png; }`)
— prompt açıkça "img tag'lerine asset_ref'i src olarak yaz" dese de model
bunu güvenilir uygulamadı. Bu tür tekil hatalar için modele güvenmek yerine,
şemadaki asset_ref'leri üretilen HTML'deki <img> tag'lerine DOĞRUDAN,
programatik olarak enjekte ediyoruz — <img> sayısı şemayla eşleşmiyorsa
(model bir görseli atladı/eklediyse) güvenli tarafta kalıp dokunmuyoruz.
"""

from __future__ import annotations

import re

_IMG_TAG_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ATTR_PATTERN_TEMPLATE = r'{attr}\s*=\s*"[^"]*"'


def _collect_asset_refs(node: dict) -> list[str]:
    refs: list[str] = []
    if node.get("tag") == "img" and node.get("asset_ref"):
        refs.append(node["asset_ref"])
    for child in node.get("children", []):
        refs.extend(_collect_asset_refs(child))
    return refs


def _set_attr(tag: str, attr: str, value: str) -> str:
    pattern = re.compile(_ATTR_PATTERN_TEMPLATE.format(attr=attr), re.IGNORECASE)
    if pattern.search(tag):
        return pattern.sub(f'{attr}="{value}"', tag, count=1)
    return tag[:-1].rstrip() + f' {attr}="{value}">'


def repair_image_srcs(html: str, schema_root: dict) -> str:
    """Şemadaki img node'larının asset_ref'lerini, üretilen HTML'deki <img>
    tag'lerine döküman sırasına göre eşleştirip `src` attribute'unu zorla
    doğru değere ayarlar. <img> sayısı uyuşmuyorsa dokunmadan döner."""
    asset_refs = _collect_asset_refs(schema_root)
    tags = _IMG_TAG_PATTERN.findall(html)

    if len(tags) != len(asset_refs):
        return html

    result = html
    for tag, ref in zip(tags, asset_refs):
        fixed_tag = _set_attr(tag, "src", ref)
        result = result.replace(tag, fixed_tag, 1)
    return result
