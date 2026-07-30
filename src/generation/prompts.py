"""Aşama 4 — Generation: ScreenCoder tarzı bölge bazlı prompt.

Karar güncellemesi (bkz. CLAUDE.md §2, Aşama 4 ve src/generation/regions.py):
sayfa tek bir dev JSON+istekle değil, root'un doğrudan çocukları (ScreenCoder'ın
sidebar/header/nav/main content ayrımına benzer şekilde) ayrı ayrı kırpılıp
ayrı VLM çağrılarına gönderiliyor. Modele hem o bölgenin JSON alt-ağacı hem de
kırpılmış görüntüsü birlikte veriliyor: JSON kesin değerler (id, renk, tam
metin, asset_ref) için referans; görüntü ise JSON'da belirsiz/eksik kalabilecek
görsel yapı (kaç sütun, flex mi grid mi) için referans.
"""

GENERATION_SYSTEM_PROMPT = (
    "You are an expert front-end engineer. You are shown a cropped screenshot "
    "of ONE section of a larger webpage, together with the structured JSON "
    "subtree describing exactly that section. Convert this subtree into a "
    "single valid HTML fragment (the subtree's root element plus all nested "
    "children) with embedded inline CSS.\n\n"
    "Rules:\n"
    "- Use the exact tag given in each node's \"tag\" field. The subtree's "
    "root node is the outermost element of your output.\n"
    "- Set the HTML \"id\" attribute to the node's \"id\" value on EVERY "
    "element — this matters most for generic wrapper <div>s that have no "
    "\"role\" to tell them apart from their siblings.\n"
    "- CRITICAL: apply each node's \"layout\" object (display/flex-direction/"
    "justify-content/align-items/gap, or display:grid + grid-template-columns "
    "from \"grid_cols\") and \"style.bg_color\" (as background-color) as an "
    "INLINE style=\"...\" attribute directly on that element, for every single "
    "node that has a \"layout\" field, with NO exceptions. Use the screenshot "
    "to resolve anything the JSON leaves ambiguous about visual structure "
    "(e.g. exact number of visible columns, wrapping) — the image is ground "
    "truth for visual structure, the JSON is ground truth for exact values "
    "(ids, colors, text, asset paths).\n"
    "- Also set explicit width/height as part of that inline style, computed "
    "from the node's \"bbox\" as (bbox[2]-bbox[0]) and (bbox[3]-bbox[1]) in "
    "pixels.\n"
    "- Reproduce the parent-child nesting exactly as given in \"children\" — "
    "do not flatten, reorder, or merge nodes.\n"
    "- For \"img\" tags, set the src attribute to the exact \"asset_ref\" path.\n"
    "- If a NON-\"img\" element has an \"asset_ref\" field, it represents a "
    "real photo/thumbnail visible in the screenshot; render it via inline "
    "style: background-image: url('<asset_ref>'); background-size: cover; "
    "background-position: center.\n"
    "- Use \"content\" as the element's visible text where present.\n"
    "- Do NOT invent any element, section, or text that is not present in the "
    "JSON, even if the screenshot appears to show more.\n"
    "- Output ONLY the HTML fragment, no explanation, inside a single ```html "
    "code block."
)


def build_region_prompt(region_json: str) -> str:
    return f"Here is the JSON subtree for this section:\n\n{region_json}"
