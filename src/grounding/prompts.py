"""Aşama 1 — Grounding: prompt tasarımı.

Karar (CLAUDE.md §2, Aşama 1, adım 2): "Locate each/every UI component..."
şeklinde açık çoğul ifade + kategori listesi + halüsinasyon/gruplama karşıtı
kurallar.

Not: "text" alanı sonradan eklendi (CLAUDE.md'nin Qwen3-VL seçim gerekçesi
"konum + içerik/OCR + bağlam" idi — bu OCR yeteneği başlangıçta kullanılmamıştı).
İlk pilotta Aşama 2b'de content çıkarımı için pytesseract denendi, küçük/stilize
UI fontlarında güvenilmez çıktı (anlamsız string) ürettiği görüldü. Qwen3-VL
zaten aynı görseli işlediği için metni de tek geçişte okutmak, ayrı bir OCR
adımından çok daha güvenilir.
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
    "the most descriptive short label you can.\n"
    "- If the component visibly displays text (button label, link text, heading, "
    "paragraph, menu item...), transcribe it VERBATIM and exactly as shown in the "
    "\"text\" field. If it has no visible text (icon, image, plain container), set "
    "\"text\" to null. Never guess or invent text that isn't actually visible.\n\n"
    "Output ONLY a JSON list, no explanation text, in this exact format:\n"
    '[{"bbox_2d": [x1, y1, x2, y2], "label": "...", "text": "..." or null}]\n\n'
    "Coordinates must be normalized to a 0-1000 scale."
)
