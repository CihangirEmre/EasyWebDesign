"""Aşama 4 — Generation: ScreenCoder tarzı bölge seçimi.

Karar: sayfa tek seferde büyük bir VLM çağrısına verilmek yerine, root'un
doğrudan çocukları (header/nav/main/footer gibi Aşama 2a'nın zaten ayırdığı
üst seviye gruplar) ayrı ayrı kırpılıp ayrı VLM çağrılarına gönderilir.
Gerekçe: ScreenCoder'ın (arXiv:2507.22827) modüler mimarisinin asıl kazancı
budur — bir VLM'e dar/sınırlı bir görsel kapsam verildiğinde "gördüğünü
kopyala" görevinde çok daha güvenilir; tüm sayfa tek seferde verildiğinde
eleman atlama/karıştırma riski artıyor (CLAUDE.md §1'deki motivasyon).

DEFAULT_MAX_REGION_NODES: gerçek Colab çıktısında (bkz. layout.py'nin
sidebar|ana-içerik seam-split düzeltmesi) "ana içerik" gibi bir kök çocuğu
tek başına ~38 node'luk devasa bir alt-ağaç olabiliyor — bu da tek bir VLM
çağrısının hem çok büyük bir görsel kapsam almasına (ScreenCoder'ın küçük-
kapsam avantajını kaybettiriyor) hem de üretimin `max_new_tokens` sınırında
yarıda kesilmesine yol açtı (gerçek pilot testte gözlemlendi). Bu yüzden bir
bölgenin kendi alt-ağacı bu eşiği aşarsa, o bölge kendi ÇOCUKLARINA
bölünerek (recursive) daha küçük, bağımsız VLM çağrılarına dönüştürülüyor.
"""

from __future__ import annotations

DEFAULT_MAX_REGION_NODES = 15


def _count_nodes(node: dict) -> int:
    return 1 + sum(_count_nodes(c) for c in node.get("children", []))


def _expand_if_too_large(node: dict, *, max_nodes: int) -> list[dict]:
    if not node.get("children") or _count_nodes(node) <= max_nodes:
        return [node]
    expanded: list[dict] = []
    for child in node["children"]:
        expanded.extend(_expand_if_too_large(child, max_nodes=max_nodes))
    return expanded


def select_regions(root: dict, *, max_nodes: int = DEFAULT_MAX_REGION_NODES) -> list[dict]:
    """root'un doğrudan çocuklarını bölge olarak döner; bir çocuğun kendi
    alt-ağacı `max_nodes`'u aşıyorsa, o çocuğun KENDİ çocuklarına inilerek
    daha küçük bölgelere bölünür (recursive).

    root'un çocuğu yoksa (ör. tüm sayfa tek bir kart/komponentse) root'un
    kendisi tek bölge olarak döner.
    """
    children = root.get("children")
    if not children:
        return [root]

    regions: list[dict] = []
    for child in children:
        regions.extend(_expand_if_too_large(child, max_nodes=max_nodes))
    return regions
