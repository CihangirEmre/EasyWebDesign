"""Aşama 2a — Planning: kardeş gruplama ve layout (flex/grid) çıkarımı.

Kapsayan bir bbox tespit edilmemiş olsa bile (görünmez wrapper div gibi),
kardeşler arasındaki y-ekseni örtüşmesine bakarak "bunlar aynı satırda mı"
sorusu geometrik olarak cevaplanır. Aynı satırda birden fazla eleman varsa
ve bu satır için tespit edilmiş bir kapsayıcı yoksa, o grup için sentetik
(synthetic=True) bir wrapper node üretilir — bu node görselde karşılığı
olmayan ama layout kurmak için gereken örtük flex-row/column'u temsil eder.
"""

from __future__ import annotations

import statistics
from typing import Callable

from .geometry import area, axis_overlap_ratio, union_bbox, x_range, y_range
from .hierarchy import Node

DEFAULT_BAND_OVERLAP_THRESHOLD = 0.5


def _cluster_by_axis(nodes: list[Node], range_fn, overlap_threshold: float) -> list[dict]:
    """1D interval sweep: aynı eksende örtüşen node'ları aynı banda toplar."""
    ordered = sorted(nodes, key=lambda n: range_fn(n.bbox)[0])
    bands: list[dict] = []
    for n in ordered:
        rng = range_fn(n.bbox)
        for band in bands:
            if axis_overlap_ratio(band["range"], rng) >= overlap_threshold:
                band["nodes"].append(n)
                band["range"] = (min(band["range"][0], rng[0]), max(band["range"][1], rng[1]))
                break
        else:
            bands.append({"range": rng, "nodes": [n]})
    return bands


def _columns_align(
    band_a_sorted: list[Node], band_b_sorted: list[Node], *, tolerance_ratio: float = 0.15
) -> bool:
    """İki bandın (aynı eleman sayılı) x-merkezlerinin sütun sütun hizalı olup
    olmadığını kontrol eder — sadece eleman sayısı eşitliği bir grid'in devamı
    olduğu anlamına gelmez, sütunlar da hizalı olmalı (ör. bir kart satırının
    altındaki bağımsız buton grubuyla karıştırılmaması için)."""
    for a, b in zip(band_a_sorted, band_b_sorted):
        center_a = (a.bbox[0] + a.bbox[2]) / 2
        center_b = (b.bbox[0] + b.bbox[2]) / 2
        width = max(a.bbox[2] - a.bbox[0], b.bbox[2] - b.bbox[0], 1.0)
        if abs(center_a - center_b) > width * tolerance_ratio:
            return False
    return True


def _estimate_gap(ordered_nodes: list[Node], *, main_start_idx: int, main_end_idx: int) -> float:
    gaps = []
    for a, b in zip(ordered_nodes, ordered_nodes[1:]):
        gap = b.bbox[main_start_idx] - a.bbox[main_end_idx]
        if gap > 0:
            gaps.append(gap)
    return round(statistics.median(gaps), 1) if gaps else 0.0


def _build_axis_layout(ordered_nodes: list[Node], parent_bbox: list[float], *, direction: str) -> dict:
    """direction='row' -> ana eksen x, çapraz eksen y. direction='column' -> tersi."""
    if direction == "row":
        main_start_idx, main_end_idx = 0, 2
        cross_start_idx, cross_end_idx = 1, 3
    else:
        main_start_idx, main_end_idx = 1, 3
        cross_start_idx, cross_end_idx = 0, 2

    gap = _estimate_gap(ordered_nodes, main_start_idx=main_start_idx, main_end_idx=main_end_idx)

    parent_main_len = parent_bbox[main_end_idx] - parent_bbox[main_start_idx]
    margin_start = ordered_nodes[0].bbox[main_start_idx] - parent_bbox[main_start_idx]
    margin_end = parent_bbox[main_end_idx] - ordered_nodes[-1].bbox[main_end_idx]

    tolerance = max(parent_main_len * 0.05, 4.0)
    if margin_start < tolerance and margin_end < tolerance and len(ordered_nodes) > 1:
        justify = "space-between"
    elif abs(margin_start - margin_end) < tolerance:
        justify = "center"
    else:
        justify = "flex-start"

    cross_spans = [n.bbox[cross_end_idx] - n.bbox[cross_start_idx] for n in ordered_nodes]
    parent_cross_len = parent_bbox[cross_end_idx] - parent_bbox[cross_start_idx]
    avg_cross_span = statistics.mean(cross_spans) if cross_spans else 0

    if parent_cross_len > 0 and avg_cross_span / parent_cross_len > 0.8:
        align = "stretch"
    else:
        centers = [(n.bbox[cross_start_idx] + n.bbox[cross_end_idx]) / 2 for n in ordered_nodes]
        center_spread = statistics.pstdev(centers) if len(centers) > 1 else 0
        align = "center" if parent_cross_len > 0 and center_spread / parent_cross_len < 0.1 else "flex-start"

    return {
        "display": "flex",
        "direction": direction,
        "justify": justify,
        "align": align,
        "gap": gap,
    }


def infer_layout_for_children(
    children: list[Node],
    parent_bbox: list[float],
    *,
    next_id: Callable[[], str],
    overlap_threshold: float = DEFAULT_BAND_OVERLAP_THRESHOLD,
) -> tuple[list[Node], dict | None]:
    """Bir node'un çocukları için layout çıkarır; gerekirse sentetik wrapper üretir.

    Döner: (yeni_children_sırası, layout_dict_veya_None)
    """
    if len(children) <= 1:
        return children, None

    y_bands = _cluster_by_axis(children, y_range, overlap_threshold)

    if len(y_bands) == 1:
        row_nodes = sorted(children, key=lambda n: n.bbox[0])
        return row_nodes, _build_axis_layout(row_nodes, parent_bbox, direction="row")

    if len(y_bands) == len(children):
        col_nodes = sorted(children, key=lambda n: n.bbox[1])
        return col_nodes, _build_axis_layout(col_nodes, parent_bbox, direction="column")

    bands_sorted = sorted(y_bands, key=lambda b: b["range"][0])

    # Bandları sırayla gez: aynı eleman sayısına sahip ARDIŞIK çok-elemanlı
    # bandlar bir "grid run"u oluşturur (ör. 2 satır x 3 kart). Aradaki tekil
    # bandlar (header, paragraph, footer gibi) grid'e karışmadan olduğu gibi
    # geçer; tek başına kalan çok-elemanlı bir band ise satır (flex-row)
    # wrapper'ına dönüşür — tam olarak "kapsayıcısı tespit edilmemiş buton
    # grubu" senaryosu.
    new_children: list[Node] = []
    i = 0
    while i < len(bands_sorted):
        band = bands_sorted[i]
        band_nodes = sorted(band["nodes"], key=lambda n: n.bbox[0])

        if len(band_nodes) == 1:
            new_children.append(band_nodes[0])
            i += 1
            continue

        run = [band]
        j = i + 1
        while j < len(bands_sorted) and len(bands_sorted[j]["nodes"]) == len(band_nodes):
            next_band_sorted = sorted(bands_sorted[j]["nodes"], key=lambda n: n.bbox[0])
            if not _columns_align(band_nodes, next_band_sorted):
                break
            run.append(bands_sorted[j])
            j += 1

        if len(run) >= 2:
            run_nodes_ordered: list[Node] = []
            for b in run:
                run_nodes_ordered.extend(sorted(b["nodes"], key=lambda n: n.bbox[0]))
            row_gap = _estimate_gap(band_nodes, main_start_idx=0, main_end_idx=2)
            col_gap = _estimate_gap(
                [run[0]["nodes"][0], run[1]["nodes"][0]], main_start_idx=1, main_end_idx=3
            )
            wrapper = Node(
                id=next_id(),
                label=None,
                bbox=union_bbox([n.bbox for n in run_nodes_ordered]),
                children=run_nodes_ordered,
                synthetic=True,
            )
            wrapper.layout = {
                "display": "grid",
                "grid_cols": len(band_nodes),
                "gap": max(row_gap, col_gap),
            }
            new_children.append(wrapper)
            i = j
        else:
            wrapper = Node(
                id=next_id(),
                label=None,
                bbox=union_bbox([n.bbox for n in band_nodes]),
                children=band_nodes,
                synthetic=True,
            )
            wrapper.layout = _build_axis_layout(band_nodes, wrapper.bbox, direction="row")
            new_children.append(wrapper)
            i += 1

    layout = _build_axis_layout(new_children, parent_bbox, direction="column")
    return new_children, layout
