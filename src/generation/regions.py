"""Aşama 4 — Generation: ScreenCoder tarzı bölge seçimi.

Karar: sayfa tek seferde büyük bir VLM çağrısına verilmek yerine, root'un
doğrudan çocukları (header/nav/main/footer gibi Aşama 2a'nın zaten ayırdığı
üst seviye gruplar) ayrı ayrı kırpılıp ayrı VLM çağrılarına gönderilir.
Gerekçe: ScreenCoder'ın (arXiv:2507.22827) modüler mimarisinin asıl kazancı
budur — bir VLM'e dar/sınırlı bir görsel kapsam verildiğinde "gördüğünü
kopyala" görevinde çok daha güvenilir; tüm sayfa tek seferde verildiğinde
eleman atlama/karıştırma riski artıyor (CLAUDE.md §1'deki motivasyon).
"""

from __future__ import annotations


def select_regions(root: dict) -> list[dict]:
    """root'un doğrudan çocuklarını bölge olarak döner.

    root'un çocuğu yoksa (ör. tüm sayfa tek bir kart/komponentse) root'un
    kendisi tek bölge olarak döner.
    """
    children = root.get("children")
    return list(children) if children else [root]
