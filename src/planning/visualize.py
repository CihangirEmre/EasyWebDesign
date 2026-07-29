"""Aşama 2a — Planning: hiyerarşi ağacını derinlik-renkli kutularla görselleştirme.

CLAUDE.md §2 Aşama 2a "Not" bölümündeki fallback tespiti için: üretilen
hiyerarşi ağacı gözle orijinal görselle karşılaştırılabilsin diye.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from PIL import Image

from .hierarchy import Node

_DEPTH_COLORS = ["red", "blue", "green", "orange", "purple", "brown"]


def _denormalize(bbox: list[float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = bbox
    return [x1 / 1000 * width, y1 / 1000 * height, x2 / 1000 * width, y2 / 1000 * height]


def _draw(ax, node: Node, width: int, height: int, depth: int) -> None:
    if depth > 0:
        x1, y1, x2, y2 = _denormalize(node.bbox, width, height)
        color = _DEPTH_COLORS[(depth - 1) % len(_DEPTH_COLORS)]
        rect = patches.Rectangle(
            (x1, y1), x2 - x1, y2 - y1,
            linewidth=max(2.5 - depth * 0.4, 0.8), edgecolor=color, facecolor="none",
        )
        ax.add_patch(rect)
        label = node.label or ("wrapper" if node.synthetic else "")
        layout_tag = ""
        if node.layout:
            layout_tag = f" [{node.layout['display']}:{node.layout.get('direction', node.layout.get('grid_cols'))}]"
        ax.text(
            x1, max(y1 - 3, 0), f"{label}{layout_tag}", color=color, fontsize=6,
            bbox=dict(facecolor="white", alpha=0.5, pad=0.3),
        )
    for child in node.children:
        _draw(ax, child, width, height, depth + 1)


def save_hierarchy_image(image: Image.Image, root: Node, save_path: str | Path, title: str = "") -> None:
    fig, ax = plt.subplots(1, figsize=(14, 10))
    ax.imshow(image)
    _draw(ax, root, image.width, image.height, depth=0)
    ax.set_title(title or "Aşama 2a — hiyerarşi + layout çıkarımı")
    ax.axis("off")
    plt.savefig(save_path, bbox_inches="tight", dpi=120)
    plt.close(fig)
