"""Aşama 4 — Generation: ScreenCoder-tarzı basit mimari, region-tipine-özel prompt.

KARAR GÜNCELLEMESİ (bkz. CLAUDE.md §2, Aşama 4 — ScreenCoder-tarzı pivot):
Modele artık JSON alt-ağacı VERİLMİYOR — sadece o region'ın kırpılmış görseli
ve region tipine (sidebar/header/navigation/main_content) özel bir doğal dil
talimatı veriliyor. Yapı/renk/metin tamamen modelin kendi görsel yorumundan
geliyor (ScreenCoderClone'un `html_generator.py::PROMPT_DICT`'i ile aynı
felsefe). Gerçek fotoğraf/thumbnail'ları modelin üretim ANINDA, bilerek boş
bir placeholder olarak işaretlemesi isteniyor (sadece main_content'te, tıpkı
ScreenCoder'ın "images = gray block" talimatında olduğu gibi) — bu placeholder
daha sonra src/assets/placeholders.py tarafından orijinal screenshot'tan
gerçek bir crop ile değiştiriliyor.

Tailwind/CDN KULLANILMIYOR (offline/self-contained render gerekiyor — CLIP
score değerlendirmesi internet erişimi olmadan da çalışmalı) — düz inline CSS.
"""

_SHARED_RULES = (
    "You are an expert front-end engineer. You are shown a cropped screenshot of "
    "ONE section of a larger webpage. Write a complete HTML fragment with inline "
    "CSS that visually reproduces this section as closely as possible: layout, "
    "spacing, colors, fonts, and all visible text (transcribed verbatim from the "
    "image).\n\n"
    "Rules:\n"
    "- Output a BARE fragment only: do NOT include \"<!DOCTYPE>\", \"<html>\", "
    "\"<head>\", or \"<body>\" tags, and do NOT add a <style> block or any "
    "external stylesheet/CDN link (e.g. no Tailwind CDN) — every style must be "
    "inline via the style=\"...\" attribute, so the fragment renders correctly "
    "with no network access.\n"
    "- Do NOT use \"position: absolute\" or \"position: fixed\" for this "
    "section's own top-level layout — use normal document flow plus flexbox/"
    "grid so the section adapts to the width/height it is placed into.\n"
    "- Non-void elements (<div>, <span>, <p>, <li>, <button>, <a>, <section>...) "
    "must always have an explicit closing tag; never self-close them with "
    "\"/>\" (only true void elements like <img> may self-close).\n"
    "- Do not invent text, icons, or elements that are not visible in the "
    "screenshot.\n"
    "- Output ONLY the HTML fragment, no explanation, inside a single ```html "
    "code block."
)

_IMAGE_PLACEHOLDER_RULE = (
    "\n\n- IMPORTANT — for real photos, thumbnails, illustrations, or avatar "
    "images visible in this section (NOT small icon glyphs, NOT logos, NOT "
    "decorative shapes): do not try to draw or describe them. Instead output an "
    "empty placeholder element in their exact place with "
    "class=\"img-placeholder\" and inline style width/height matching that "
    "image's own size and background-color:#cccccc — with NO text or child "
    "content inside it whatsoever (e.g. <div class=\"img-placeholder\" "
    "style=\"width:120px;height:80px;background-color:#cccccc;\"></div>). "
    "Any caption/title/text that happens to overlap or sit near the image "
    "still belongs in its own separate visible text element, not inside the "
    "placeholder."
)

REGION_PROMPTS: dict[str, str] = {
    "sidebar": (
        _SHARED_RULES
        + "\n\nThis section is a SIDEBAR (a vertical panel, usually with menu "
        "items, icons, or navigation links stacked vertically). Reproduce its "
        "vertical arrangement, icons, and labels exactly."
    ),
    "header": (
        _SHARED_RULES
        + "\n\nThis section is a HEADER (a top banner, usually containing a "
        "logo, title, and/or a row of controls). Reproduce the relative "
        "positions of its elements and their text/colors exactly."
    ),
    "navigation": (
        _SHARED_RULES
        + "\n\nThis section is a NAVIGATION bar (a menu/tab bar, usually a "
        "horizontal row of links or tabs). Reproduce the exact text of each "
        "link/tab and their order."
    ),
    "main_content": (
        _SHARED_RULES
        + _IMAGE_PLACEHOLDER_RULE
        + "\n\nThis section is the MAIN CONTENT area of the page — the primary "
        "body, which may contain cards, lists, articles, forms, or other "
        "content blocks. Reproduce its structure and all visible text exactly."
    ),
}


def build_region_prompt(region_label: str) -> str:
    """region_label: src/grounding'in döndürdüğü "sidebar"/"header"/"navigation"/
    "main_content" etiketlerinden biri. Tanınmayan bir etiket main_content
    kuralına (placeholder talimatı dahil, en güvenli varsayılan) düşer."""
    return REGION_PROMPTS.get(region_label, REGION_PROMPTS["main_content"])
