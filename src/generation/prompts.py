"""Aşama 4 — Generation: ScreenCoder-tarzı basit mimari, region-tipine-özel prompt.

KARAR GÜNCELLEMESİ (bkz. CLAUDE.md §2, Aşama 4 — ScreenCoder-tarzı pivot):
Modele artık JSON alt-ağacı VERİLMİYOR — sadece o region'ın kırpılmış görseli
ve region tipine (sidebar/header/navigation/main_content) özel bir doğal dil
talimatı veriliyor. Yapı/renk/metin tamamen modelin kendi görsel yorumundan
geliyor (ScreenCoderClone'un `html_generator.py::PROMPT_DICT`'i ile aynı
felsefe). Gerçek fotoğraf/thumbnail'ları modelin üretim ANINDA, bilerek boş
bir placeholder olarak işaretlemesi isteniyor — bu placeholder daha sonra
src/assets/placeholders.py tarafından orijinal screenshot'tan gerçek bir
crop ile değiştiriliyor.

BUG DÜZELTMESİ (gerçek Colab çıktısı, upload_0000/YouTube sidebar): placeholder
kuralı ilk sürümde SADECE main_content prompt'una eklenmişti (ScreenCoder'ın
kendi kuralı da sadece "main content" için idi). Ama gerçek testte sidebar'daki
kullanıcı avatarları için model bunun yerine UYDURMA bir dış URL üretti
(`https://i.pravatar.cc/40?img=1` gibi) — hem sahte/yanlış görsel hem de
render'ın internet erişimine bağımlı hale gelmesi anlamına geliyor. Artık
placeholder kuralı TÜM region tiplerine uygulanıyor — herhangi bir bölge
gerçek bir fotoğraf/avatar içerebilir, sadece main_content değil.

Tailwind/CDN KULLANILMIYOR (offline/self-contained render gerekiyor — CLIP
score değerlendirmesi internet erişimi olmadan da çalışmalı) — düz inline CSS.

BUG DÜZELTMESİ (gerçek Colab çıktısı, upload_0001/Claude.ai — orijinal
screenshot ile karşılaştırılarak doğrulandı): model, gerçek sayfadaki düz
monokrom SVG ikonları (Chats/Projects/Artifacts/Customize/Design...) renkli
Unicode EMOJİ karakterleriyle (💬🗂️🔗💼🎨🧪⚙️🎓☕💡🎙) değiştirdi — bunlar
CSS `color`'dan bağımsız, OS'a göre değişen, sabit çok-renkli glyph'ler
olarak render ediliyor, orijinal tek-renkli ikon setiyle hiç uyuşmuyor;
metrikleri de düz metinden farklı olduğu için yan yazıda hafif kaymaya yol
açıyor. Ayrıca her region bağımsız üretildiği için (aralarında paylaşılan
durum yok) sidebar ve main_content birbirinden habersiz iki farklı
font-family seçmişti (biri var olmayan bir marka fontu — "Söhne" — uydurmuş).
Bu iki hata için _SHARED_RULES'a ikon ve font kuralları eklendi (girdi
sadece görsel olduğu için gerçek font adı bilinemez — bkz. ilgili kural).

BUG DÜZELTMESİ (gerçek Colab çıktısı, upload_0000/YouTube main_content —
kaynak koddan doğrulandı): gerçek video thumbnail'larının ÜZERİNE üreticinin
bastığı büyük başlık tasarımı (ör. "Upgrade Your AI Skills") görselin kendi
piksellerinin bir parçası. Model bunu fark edip aynı metni AYRICA, placeholder
kutusunun üstüne `position:absolute` div'lerle yeniden çizdi. Ama placeholder
zaten src/assets/placeholders.py tarafından orijinal screenshot'tan gerçek bir
crop ile değiştiriliyor — o crop'ta bu metin ZATEN var (piksel olarak). Sonuç:
gerçek fotoğraf + modelin ayrıca çizdiği metin üst üste binip render'da
çakışan/tekrarlı metin oluşturuyor. Süre rozeti gibi GERÇEKTEN ayrı bir UI
katmanı olan küçük overlay'ler bu kuralın dışında (bkz. _IMAGE_PLACEHOLDER_RULE).
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
    "- For icons (search, chat, folder, link, gear, pencil, and similar "
    "glyphs): NEVER use full-color Unicode emoji characters (e.g. "
    "\U0001F4AC\U0001F3A8☕\U0001F393\U0001F4A1\U0001F517\U0001F4BC"
    "\U0001F9EA⚙️) as a substitute. These render as fixed, "
    "multi-colored glyphs that ignore CSS \"color\" and never match a flat "
    "monochrome icon set, and their inconsistent size/baseline can shift "
    "neighboring text. Instead draw a small inline <svg> (simple shapes/"
    "paths, fill=\"currentColor\" or the exact color you observe) that "
    "reproduces the icon's actual silhouette and color. Plain monochrome "
    "symbol characters that DO respect CSS \"color\" (e.g. →, ✕, "
    "▸, ‹, ›) are fine to use directly where they match what "
    "is visible.\n"
    "- For font-family: you cannot know the page's real font name from a "
    "screenshot alone, so do NOT invent or guess a specific named font "
    "(e.g. \"Söhne\", \"Circular\", \"SF Pro\") — it will not be installed "
    "and silently falls back anyway. Pick ONE generic stack for this ENTIRE "
    "fragment based only on what the visible letterforms actually look "
    "like: a serif stack (\"Georgia, 'Times New Roman', serif\") only if "
    "the text clearly has serifs, otherwise a plain sans-serif stack "
    "(\"-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif\"). Do not "
    "mix serif and sans-serif within this fragment unless the screenshot "
    "clearly shows two visibly different typefaces.\n"
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
    "This placeholder will later be replaced with the ACTUAL real photo "
    "cropped from the original screenshot — so ANY text, logo, or graphic "
    "that appears BAKED INTO the photo itself (e.g. a stylized thumbnail "
    "title, a watermark, a channel bug drawn on the image) is part of that "
    "photo's own pixels and will automatically appear once the real crop is "
    "substituted in. Do NOT reproduce that baked-in text as separate HTML "
    "elements positioned over the placeholder — doing so duplicates it, "
    "since the real photo already contains it. The ONLY elements allowed to "
    "sit visually on top of a placeholder are small pieces of UI chrome "
    "that are clearly a SEPARATE layer added by the site over any photo "
    "(e.g. a small semi-transparent video-duration badge in a corner) — "
    "never large stylized text mimicking the photo's own design.\n"
    "- Caption/title/text that sits OUTSIDE the photo's own boundaries "
    "(e.g. a video title below the thumbnail, next to an avatar) is real "
    "page text, not baked into any image — transcribe that normally as its "
    "own visible text element."
)

REGION_PROMPTS: dict[str, str] = {
    "sidebar": (
        _SHARED_RULES
        + _IMAGE_PLACEHOLDER_RULE
        + "\n\nThis section is a SIDEBAR (a vertical panel, usually with menu "
        "items, icons, or navigation links stacked vertically). Reproduce its "
        "vertical arrangement, icons, and labels exactly."
    ),
    "header": (
        _SHARED_RULES
        + _IMAGE_PLACEHOLDER_RULE
        + "\n\nThis section is a HEADER (a top banner, usually containing a "
        "logo, title, and/or a row of controls). Reproduce the relative "
        "positions of its elements and their text/colors exactly."
    ),
    "navigation": (
        _SHARED_RULES
        + _IMAGE_PLACEHOLDER_RULE
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
