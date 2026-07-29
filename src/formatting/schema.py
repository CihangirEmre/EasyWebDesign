"""Aşama 2b — Formatting: planning ağacını KESİN KARAR şemaya (CLAUDE.md §2,
Aşama 2b) çevirme.

Girdi: src/planning'in ürettiği ağaç (node_to_dict çıktısı) — bbox 0-1000
normalize, label/synthetic/layout/children alanları var.
Çıktı: CLAUDE.md'de sabitlenmiş `ui-to-code-formatting-schema-v1` JSON'u.
"""

from __future__ import annotations

import itertools

from PIL import Image

from src.grounding.coords import denormalize_bbox

from .content import extract_content
from .style import extract_style
from .tags import IMAGE_TAGS, resolve_tag

SCHEMA_VERSION = "ui-to-code-formatting-schema-v1"


def _build_node(plan_node: dict, image: Image.Image, next_id) -> dict:
    label = plan_node.get("label")
    synthetic = plan_node.get("synthetic", False)
    tag, role = resolve_tag(label)

    bbox_px = [round(v) for v in denormalize_bbox(plan_node["bbox_2d"], image.width, image.height)]

    node: dict = {"id": next_id(), "tag": tag}
    if role:
        node["role"] = role

    layout = plan_node.get("layout")
    if layout:
        node["layout"] = layout

    node["bbox"] = bbox_px

    style = extract_style(image, bbox_px, synthetic=synthetic)
    if style:
        node["style"] = style

    if tag in IMAGE_TAGS:
        node["content"] = None
        node["asset_ref"] = f"assets/{node['id']}_{role or tag}.png"
    else:
        content = extract_content(image, bbox_px, tag)
        if content is not None:
            node["content"] = content

    children = plan_node.get("children")
    if children:
        node["children"] = [_build_node(c, image, next_id) for c in children]

    return node


def build_formatted_schema(
    plan_root: dict,
    image: Image.Image,
    *,
    source_image: str,
    viewport_type: str = "full_page",
) -> dict:
    """plan_root: src/planning'in kök node'u (node_to_dict çıktısı, tag="body")."""
    counter = itertools.count()
    next_id = lambda: f"n{next(counter)}"

    return {
        "$schema": SCHEMA_VERSION,
        "meta": {
            "source_image": source_image,
            "canvas": {"width": image.width, "height": image.height},
            "viewport_type": viewport_type,
        },
        "root": _build_node(plan_root, image, next_id),
    }
