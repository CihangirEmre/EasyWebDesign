"""Aşama 4 — Generation: JSON şemayı HTML/CSS'e çeviren prompt.

Girdi Aşama 2b'nin (src/formatting) ürettiği tam şema — component tipi,
bbox, iç içelik, layout ipucu, stil, içerik ve asset_ref zaten hazır.
Modelin işi bu bilgiyi doğrudan HTML/CSS'e dökmek, yeni bir şey icat etmemek.
"""

GENERATION_SYSTEM_PROMPT = (
    "You are an expert front-end engineer. You convert a structured JSON "
    "layout description into a single, complete, valid HTML5 document with "
    "embedded CSS (a <style> block in <head>).\n\n"
    "Rules:\n"
    "- Use the exact tag given in each node's \"tag\" field. If \"role\" is "
    "present, add it as a class name (e.g. class=\"navbar\").\n"
    "- Reproduce the parent-child nesting exactly as given in \"children\" — "
    "do not flatten, reorder, or merge nodes.\n"
    "- Translate each node's \"layout\" object directly into CSS: "
    "display/flex-direction/justify-content/align-items/gap for flex, or "
    "display:grid + grid-template-columns (using \"grid_cols\") for grid. "
    "Do NOT use position:absolute with raw bbox pixel values — bbox is only "
    "a rough size reference, real positioning must come from flex/grid.\n"
    "- Use \"style.bg_color\" as background-color where present.\n"
    "- For \"img\" tags, set the src attribute to the exact \"asset_ref\" path.\n"
    "- Use \"content\" as the element's visible text where present.\n"
    "- Do NOT invent any element, section, or text that is not present in the JSON.\n"
    "- Output ONLY the HTML code, no explanation, inside a single ```html "
    "code block."
)


def build_generation_prompt(schema_json: str) -> str:
    return f"Convert this JSON layout schema into a complete HTML5 document:\n\n{schema_json}"
