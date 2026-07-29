"""Aşama 1 — Grounding: tespitleri kutulu görsel olarak kaydetme (pilot değerlendirme için)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from PIL import Image

from .coords import denormalize_bbox


def save_annotated_image(image: Image.Image, detections: list[dict], save_path: str | Path, title: str = "") -> None:
    fig, ax = plt.subplots(1, figsize=(14, 10))
    ax.imshow(image)
    w, h = image.size

    for det in detections:
        x1, y1, x2, y2 = denormalize_bbox(det["bbox_2d"], w, h)
        rect = patches.Rectangle(
            (x1, y1), x2 - x1, y2 - y1, linewidth=1.5, edgecolor="red", facecolor="none"
        )
        ax.add_patch(rect)
        ax.text(
            x1, max(y1 - 4, 0), det["label"], color="red", fontsize=7,
            bbox=dict(facecolor="white", alpha=0.6, pad=0.5),
        )

    ax.set_title(title or f"{len(detections)} component tespit edildi")
    ax.axis("off")
    plt.savefig(save_path, bbox_inches="tight", dpi=120)
    plt.close(fig)
