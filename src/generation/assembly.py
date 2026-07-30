"""Aşama 4 — Generation: bölge bazlı üretilen HTML parçalarını tam sayfaya birleştirme.

Karar: root node'un kendisi hiçbir bölge kırpımına dahil edilmiyor (kırpılan
şey her zaman root'un ÇOCUKLARI, bkz. src/generation/regions.py) — bu yüzden
root'un kendi etiketi ve layout/style'ı modele hiç sorulmadan, doğrudan
şemadan deterministik olarak üretilir; yalnızca çocuklarının içeriği (bölge
bölge) modelden gelir ve olduğu gibi root'un içine yerleştirilir.
"""

from __future__ import annotations


def _style_string(node: dict) -> str:
    parts: list[str] = []
    layout = node.get("layout") or {}
    display = layout.get("display")

    if display == "flex":
        parts.append("display:flex")
        parts.append(f"flex-direction:{layout.get('direction', 'row')}")
        if "justify" in layout:
            parts.append(f"justify-content:{layout['justify']}")
        if "align" in layout:
            parts.append(f"align-items:{layout['align']}")
    elif display == "grid":
        parts.append("display:grid")
        if "grid_cols" in layout:
            parts.append(f"grid-template-columns:repeat({layout['grid_cols']}, 1fr)")

    if "gap" in layout:
        parts.append(f"gap:{layout['gap']}px")

    bg_color = (node.get("style") or {}).get("bg_color")
    if bg_color:
        parts.append(f"background-color:{bg_color}")

    bbox = node.get("bbox")
    if bbox:
        parts.append(f"width:{bbox[2] - bbox[0]}px")
        parts.append(f"height:{bbox[3] - bbox[1]}px")

    return ";".join(parts)


def assemble_document(schema_root: dict, region_htmls: list[str]) -> str:
    """root node'u + üretilen bölge HTML parçalarını tam bir HTML5 belgesine sarar."""
    tag = schema_root.get("tag", "body")
    node_id = schema_root.get("id", "root")
    style = _style_string(schema_root)
    style_attr = f' style="{style}"' if style else ""
    children_html = "\n".join(region_htmls)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        "  <title>Generated Page</title>\n"
        "</head>\n"
        f'<{tag} id="{node_id}"{style_attr}>\n'
        f"{children_html}\n"
        f"</{tag}>\n"
        "</html>\n"
    )
