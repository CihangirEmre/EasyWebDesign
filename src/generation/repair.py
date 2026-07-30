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

import bs4

_IMG_TAG_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ATTR_PATTERN_TEMPLATE = r'{attr}\s*=\s*"[^"]*"'

_FLEX_PROPERTY_FIXES = [
    (re.compile(r"(?<!flex-)\bdirection\s*:"), "flex-direction:"),
    (re.compile(r"\bjustify\s*:"), "justify-content:"),
    (re.compile(r"\balign\s*:"), "align-items:"),
]


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


def repair_flex_properties(html: str) -> str:
    """Gözlem (gerçek Colab çıktısı): model, JSON'un "layout" alanındaki
    "direction"/"justify"/"align" anahtarlarını CSS PROPERTY ismi sanıp
    birebir kopyalıyor — doğrusu flex-direction/justify-content/align-items.
    "direction" ayrıca GERÇEK ama alakasız bir CSS özelliği (metin yönü,
    yalnızca ltr/rtl kabul eder), bu yüzden tarayıcı geçersiz "column"/"row"
    değerini sessizce yok sayıp varsayılan satır akışına düşüyor — dikey
    olması gereken listeler yatay sıkışıp sayfa genişliğini taşırıyor
    (gözlemlenen: 1280px yerine 4379px full-page render). Prompt'u
    sıkılaştırmak (bkz. prompts.py) tek başına güvenilir değil, bu yüzden
    üretilen HTML'deki bu üç hatalı property adı deterministik olarak
    doğrularıyla değiştiriliyor. "flex-direction:" zaten doğruysa
    (?<!flex-) lookbehind'i "flex-flex-direction:" çift-önekini engeller."""
    for pattern, replacement in _FLEX_PROPERTY_FIXES:
        html = pattern.sub(replacement, html)
    return html


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


def _repair_visible_text(soup: bs4.BeautifulSoup, node: dict) -> None:
    content = node.get("content")
    if content and node.get("tag") != "img":
        el = soup.find(id=node["id"])
        if el is not None and not el.get_text(strip=True):
            # el.string = content DEĞİL: node'un gerçek çocukları varsa (ör.
            # metin + yanında bir ikon) bunları silip yerine tek bir metin
            # koymak ikonu yok eder. insert(0, ...) mevcut çocukları koruyarak
            # metni en başa ekler.
            el.insert(0, content)
    for child in node.get("children", []):
        _repair_visible_text(soup, child)


def repair_visible_text(html: str, schema_root: dict) -> str:
    """Gözlem (gerçek Colab çıktısı, Claude.ai): model bazı node'larda görünür
    metni ("New chat", "Chats" vb.) gerçek bir metin düğümü yerine, boş bir
    elemanın `content="..."` attribute'una gömdü — bu metin tarayıcıda HİÇ
    görünmüyor (render'da sidebar'ın tamamı boş çıktı, CLIP score bu yüzden
    düştü). Prompt'ta "content'i görünür metin yap, attribute yapma" kuralı
    zaten var ama model buna güvenilir uymadı (bkz. repair.py'nin genel
    felsefesi) — bu yüzden şemadaki id eşleşmesiyle, o node'un HTML'de hâlâ
    görünür metni yoksa (get_text boşsa) metni doğrudan enjekte ediyoruz."""
    soup = bs4.BeautifulSoup(html, "html.parser")
    for region in schema_root.get("children", [schema_root]):
        _repair_visible_text(soup, region)
    return str(soup)
