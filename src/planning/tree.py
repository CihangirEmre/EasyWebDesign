"""Aşama 2a — Planning: containment ağacına recursive layout atama + serileştirme."""

from __future__ import annotations

import itertools

from .hierarchy import Node, build_containment_tree
from .layout import infer_layout_for_children


def build_plan_tree(detections: list[dict], *, containment_threshold: float = 0.9) -> Node:
    """Aşama 1 tespit listesinden, layout bilgisiyle zenginleştirilmiş ağacı kurar."""
    root = build_containment_tree(detections, threshold=containment_threshold)
    wrapper_counter = itertools.count()
    _assign_layout(root, next_id=lambda: f"wrap{next(wrapper_counter)}")
    return root


def _assign_layout(node: Node, *, next_id) -> None:
    for child in node.children:
        _assign_layout(child, next_id=next_id)

    if node.synthetic:
        return

    new_children, layout = infer_layout_for_children(node.children, node.bbox, next_id=next_id)
    node.children = new_children
    node.layout = layout


def node_to_dict(node: Node) -> dict:
    d: dict = {"id": node.id, "bbox_2d": node.bbox}
    if node.label is not None:
        d["label"] = node.label
    if node.text is not None:
        d["text"] = node.text
    if node.synthetic:
        d["synthetic"] = True
    if node.layout is not None:
        d["layout"] = node.layout
    if node.children:
        d["children"] = [node_to_dict(c) for c in node.children]
    return d
