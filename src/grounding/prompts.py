"""Aşama 1 — Grounding: prompt tasarımı.

Karar (CLAUDE.md §2, Aşama 1, adım 2): "Locate each/every UI component..."
şeklinde açık çoğul ifade + kategori listesi + halüsinasyon/gruplama karşıtı
kurallar.
"""

GROUNDING_PROMPT = (
    "Analyze this UI screenshot and locate EVERY visible interface component.\n\n"
    "Common categories include (but are not limited to): navigation bar, sidebar, "
    "button, link, input field, dropdown, checkbox, radio button, card, icon, image, "
    "logo, heading, paragraph text, badge, tab, tooltip, modal, avatar, progress bar, "
    "table, list item.\n\n"
    "Rules:\n"
    "- Locate ALL instances of each component type.\n"
    "- Do not group multiple distinct elements into a single bounding box.\n"
    "- Do not invent elements that are not visibly present in the image.\n"
    "- Distinguish carefully between \"link\" and plain \"text\": label as \"link\" ONLY "
    "if it appears interactive/clickable (underlined, differently colored, part of a menu); "
    "otherwise label as \"text\" or \"paragraph\".\n"
    "- If a component doesn't match the categories above, still detect it and give it "
    "the most descriptive short label you can.\n\n"
    "Output ONLY a JSON list, no explanation text, in this exact format:\n"
    '[{"bbox_2d": [x1, y1, x2, y2], "label": "..."}]\n\n'
    "Coordinates must be normalized to a 0-1000 scale."
)
