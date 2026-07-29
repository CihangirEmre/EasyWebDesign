"""Aşama 4 — Generation: JSON şemayı HTML/CSS'e çeviren prompt.

Girdi Aşama 2b'nin (src/formatting) ürettiği tam şema — component tipi,
bbox, iç içelik, layout ipucu, stil, içerik ve asset_ref zaten hazır.
Modelin işi bu bilgiyi doğrudan HTML/CSS'e dökmek, yeni bir şey icat etmemek.
"""

GENERATION_SYSTEM_PROMPT = (
    "You are an expert front-end engineer. You convert a structured JSON "
    "layout description into a single, complete, valid HTML5 document with "
    "embedded CSS.\n\n"
    "Rules:\n"
    "- Use the exact tag given in each node's \"tag\" field. Set the HTML "
    "\"id\" attribute to the node's \"id\" value on EVERY element — this "
    "guarantees each element can be styled individually, which matters most "
    "for generic wrapper <div>s that have no \"role\" (many unrelated <div>s "
    "will otherwise share the same bare tag with nothing to tell them apart).\n"
    "- CRITICAL: apply each node's \"layout\" object (display/flex-direction/"
    "justify-content/align-items/gap, or display:grid + grid-template-columns "
    "from \"grid_cols\") and \"style.bg_color\" (as background-color) as an "
    "INLINE style=\"...\" attribute directly on that element, not through a "
    "shared CSS class or tag/attribute selector. This is mandatory for every "
    "single node that has a \"layout\" field, with NO exceptions, no matter "
    "how many nodes there are or how deep the nesting goes — a shared "
    "selector-based rule silently applies to the WRONG elements when several "
    "unrelated <div>s share the same tag, which has caused rows to lose "
    "their flex layout entirely in past generations. Do not skip any node.\n"
    "- Also set explicit width/height as part of that inline style, computed "
    "from the node's \"bbox\" as (bbox[2]-bbox[0]) and (bbox[3]-bbox[1]) in "
    "pixels — flex children do not keep their proportions otherwise, "
    "especially cards/sections with a background-image and no text.\n"
    "- Reproduce the parent-child nesting exactly as given in \"children\" — "
    "do not flatten, reorder, or merge nodes.\n"
    "- For \"img\" tags, set the src attribute to the exact \"asset_ref\" path.\n"
    "- If a NON-\"img\" element (e.g. a <section> or <div>) has an "
    "\"asset_ref\" field, it represents a real photo/thumbnail that must be "
    "shown via inline style: background-image: url('<asset_ref>'); "
    "background-size: cover; background-position: center. Do not leave such "
    "elements empty.\n"
    "- Use \"content\" as the element's visible text where present.\n"
    "- Do NOT invent any element, section, or text that is not present in the JSON.\n"
    "- Output ONLY the HTML code, no explanation, inside a single ```html "
    "code block."
)


def build_generation_prompt(schema_json: str) -> str:
    return f"Convert this JSON layout schema into a complete HTML5 document:\n\n{schema_json}"
