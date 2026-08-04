"""Aşama 1 — Grounding: prompt tasarımı.

KARAR GÜNCELLEMESİ (bkz. CLAUDE.md §2, Aşama 1 — ScreenCoder-tarzı basit mimari
pivotu): Artık her tekil UI elemanı (buton/başlık/li...) tek tek tespit
EDİLMİYOR. Qwen3-VL sadece 4 kaba düzen bölgesini (sidebar/header/navigation/
main_content) buluyor — ScreenCoderClone'un `block_parsor.py`'sindeki
PROMPT_MERGE ile aynı fikir, bizim mevcut {bbox_2d,label} JSON formatımızda.
Neden: tekil-eleman tespiti + kural-tabanlı hiyerarşi + zengin JSON şema
katmanları (eski Aşama 2a/2b) projedeki hataların asıl kaynağıydı; kod üretimi
artık bu kaba bölge crop'unu doğrudan görüp kendi yorumuyla HTML/CSS yazan
Claude'a bırakılıyor (bkz. src/generation/prompts.py).
"""

GROUNDING_PROMPT = (
    "Analyze this UI screenshot and locate ONLY these 4 coarse layout regions, "
    "if present: sidebar, header, navigation, main_content.\n\n"
    "Rules:\n"
    "- Return AT MOST one bounding box per region — do not detect individual "
    "elements (buttons, headings, list items...) inside them.\n"
    "- Regions must not overlap.\n"
    "- All visible text/content on the page must be framed inside one of the "
    "regions — keep boxes compact, do not leave large empty margins inside them.\n"
    "- If a region is not present on the page (e.g. no sidebar), omit it entirely "
    "— do not invent it.\n"
    "- \"header\" is a top banner/navbar-like strip; \"navigation\" is a distinct "
    "menu/tab bar (only label it separately if it is visually separate from "
    "header/sidebar); \"main_content\" is everything else (the primary content "
    "area).\n\n"
    "Output ONLY a JSON list, no explanation text, in this exact format:\n"
    '[{"bbox_2d": [x1, y1, x2, y2], "label": "sidebar" | "header" | "navigation" | "main_content"}]\n\n'
    "Coordinates must be normalized to a 0-1000 scale."
)
