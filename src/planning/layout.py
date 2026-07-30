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
# Sütun (yan yana bölge, ör. sidebar | ana içerik) tespiti için: bandlar
# arasındaki genişlik oranı bu eşiği aşarsa "homojen bir grid'in sütunları"
# değil, "birbirinden bağımsız iki bölge" olduğu varsayılır (bir grid'in
# sütunları genelde birbirine yakın genişliktedir; bir sidebar ise ana
# içerikten çok daha dardır).
DEFAULT_COLUMN_WIDTH_RATIO_THRESHOLD = 2.0
# İki komşu eleman arasındaki X boşluğu, kendi ortalama genişliklerinin bu
# katından fazlaysa artık "aynı satır" değil, alakasız iki grup sayılır.
# Bulundu: aynı y-bandında olan ama aralarında büyük X mesafesi olan iki
# öğe (ör. sidebar'daki bir liste öğesi ile ana içerikteki bir buton grubu,
# sırf y-aralıkları örtüştüğü için) yanlışlıkla tek satır sayılıyordu.
DEFAULT_MAX_GAP_RATIO = 2.5
# En geniş bant ile diğerlerinin birleşiminin (containment-tarzı, kısa
# aralığa göre normalize) örtüşme oranı bu eşiği aşmalı — gerçek yan yana
# sütunlarda (sidebar | ana içerik) biri diğerinin kapsama alanına düşer;
# ardışık bölümler (header sonra footer) hiç örtüşmez (oran ~0).
DEFAULT_MIN_COLUMN_Y_OVERLAP = 0.5


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


def _split_by_gap(
    nodes_sorted: list[Node], *, start_idx: int, end_idx: int, max_gap_ratio: float = DEFAULT_MAX_GAP_RATIO
) -> list[list[Node]]:
    """Ana eksende sıralı node'ları, komşu elemanların kendi boyutlarına göre
    aşırı büyük bir X/Y boşluğu olan noktalardan alt gruplara böler.

    Neden gerekli: bir y-bandındaki tüm elemanlar y-ekseninde örtüşse bile,
    aralarında (kendi boyutlarına oranla) devasa bir boşluk varsa bunlar
    aslında alakasız iki grup olabilir (ör. solda dar bir sidebar öğesi,
    sağda çok uzakta bir buton grubu — ikisi de benzer y-aralığında ama
    hiç ilişkili değiller). Pilot testte tam bu senaryo yakalandı.
    """
    if len(nodes_sorted) <= 1:
        return [nodes_sorted]

    groups: list[list[Node]] = [[nodes_sorted[0]]]
    for prev, cur in zip(nodes_sorted, nodes_sorted[1:]):
        gap = cur.bbox[start_idx] - prev.bbox[end_idx]
        avg_size = ((prev.bbox[end_idx] - prev.bbox[start_idx]) + (cur.bbox[end_idx] - cur.bbox[start_idx])) / 2
        if avg_size > 0 and gap > avg_size * max_gap_ratio:
            groups.append([])
        groups[-1].append(cur)
    return groups


def _split_row_into_entries(
    nodes_sorted_x: list[Node], *, next_id: Callable[[], str]
) -> tuple[list[Node], bool]:
    """Bir "satır" adayını gap'e göre alt gruplara böler; her çok-elemanlı
    alt grup kendi flex-row wrapper'ına sarılır, tekil elemanlar olduğu gibi
    kalır. İkinci dönen değer: hiç bölünme olmadıysa True (çağıran taraf
    orijinal düz listeyi tek bir row olarak işleyebilir)."""
    groups = _split_by_gap(nodes_sorted_x, start_idx=0, end_idx=2)
    if len(groups) == 1:
        return nodes_sorted_x, True

    entries: list[Node] = []
    for g in groups:
        if len(g) == 1:
            entries.append(g[0])
        else:
            wrapper = Node(id=next_id(), label=None, bbox=union_bbox([n.bbox for n in g]), children=g, synthetic=True)
            wrapper.layout = _build_axis_layout(g, wrapper.bbox, direction="row")
            entries.append(wrapper)
    return entries, False


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


def _column_split_indicated(x_bands: list[dict], num_children: int, parent_bbox: list[float]) -> bool:
    """x-bandları gerçek bir sütun (yan yana bölge) ayrımına mı işaret
    ediyor, yoksa homojen bir grid'in sütunlarına ya da art arda dizilmiş
    (sıralı) sayfa bölümlerine mi?

    İki ayrı yanlış-pozitif riski var:
    1. Homojen grid'lerde sütun genişlikleri birbirine yakındır — genişlik
       oranı büyükse gerçek bir sütun ayrımı (dar sidebar vs geniş içerik).
    2. Header/footer gibi aralarında hiçbir y-örtüşmesi olmayan, sırf ikisi
       de tam genişlikte olduğu için X-kümelemesinde "aynı bant"a düşen
       elemanlar — bunlar sütun değil, art arda dizilmiş bölümlerdir. Bunu
       elemek için: çocukların toplam kapladığı dikey alan, ebeveynin
       yüksekliğinin büyük kısmını (>%70) kaplıyorsa bu sıralı bölümlerdir,
       yan yana sütunlar değil (gerçek sütunlar yerelde/dar bir dikey
       aralıkta bir arada bulunur).
    """
    if not (2 <= len(x_bands) < num_children):
        return False
    if not any(len(b["nodes"]) > 1 for b in x_bands):
        return False
    widths = [b["range"][1] - b["range"][0] for b in x_bands]
    if min(widths) <= 0:
        return False
    if max(widths) / min(widths) <= DEFAULT_COLUMN_WIDTH_RATIO_THRESHOLD:
        return False

    # Hiçbir bant ebeveynin genişliğinin neredeyse tamamını kaplamamalı —
    # kaplıyorsa bu bir sütun değil, tam genişlikte ayrı bir bölümdür (ör.
    # bir header/footer, altındaki kart grid'inden bağımsız olarak "sütun"
    # sayılmamalı, sırf bant genişlik oranı testini geçti diye).
    parent_width = parent_bbox[2] - parent_bbox[0]
    if parent_width > 0 and max(widths) / parent_width > 0.85:
        return False

    # Gerçek sütunlar YAN YANA var olur ve birbirleriyle YEREL olarak
    # örtüşür (sidebar | ana içerik ikisi de sayfanın aynı dikey bölümünde).
    # Bunu HER bant ÇİFTİ için ikili olarak test ediyoruz — "en geniş bandı,
    # diğer TÜM bantların BİRLEŞİMİYLE" karşılaştırmak (önceki versiyon)
    # >2 primary band olduğunda yanlış-pozitif üretiyordu: gerçek bir tam
    # sayfa örneğinde (bkz. pilot: YouTube ana sayfası) 8 ayrı bant tesadüfen
    # X ekseninde hizalanmıştı (bir buton + 500px aşağıdaki bir avatar + yine
    # 900px aşağıdaki bir ikon gibi, aralarında hiçbir ilişki yok) — bu
    # bantların birleşimi zaten neredeyse tüm sayfa yüksekliğini kapladığı
    # için "en geniş bant vs birleşim" testi neredeyse her zaman geçiyordu
    # (ölçülen oran: 1.0), oysa gerçekte alakasız bant ÇİFTLERİ arasında
    # örtüşme çok düşüktü (ör. 0.30). İkili test bunu doğru reddediyor: her
    # iki bant GERÇEKTEN aynı yerel dikey bölümde olmalı, sadece "birileri
    # her yerde" olması yetmez. Ayrıca oranı KISA aralığa göre normalize
    # ediyoruz (containment-tarzı, Jaccard değil): ana içerik genelde
    # sidebar'dan çok daha KISA bir dikey aralıkta (sayfanın ortasında) kalır.
    # NOT: Önceki versiyonda "toplam dikey kaplama alanı ebeveyn yüksekliğinin
    # >%70'ini geçmemeli" kuralı vardı; bu, tam-yükseklik gerçek bir sidebar'ı
    # yanlışlıkla engelliyordu — gerçek pilot testte yakalandı.
    # NOT: kontrol SADECE "primary" (>1 node'lu) bantlar arasında değil, TÜM
    # bantlar arasında (tekil bantlar dahil) yapılmalı — aksi halde tek bir
    # yalnız eleman (ör. sayfanın çok uzağında, alakasız bir köşe ikonu),
    # kendi başına "primary" sayılmadığı için bu kontrolden tamamen muaf
    # kalıyor ve alakasız olsa bile geçerli bir sütun sanılıyordu (gerçek
    # pilot testte yakalandı: Claude.ai'de sağ üstteki yalnız bir ikon, asıl
    # içerikten 500px+ uzakta olmasına rağmen sahte bir "sütun" oluşturdu).
    if len(x_bands) >= 2:
        band_y_ranges = [
            (min(n.bbox[1] for n in b["nodes"]), max(n.bbox[3] for n in b["nodes"]))
            for b in x_bands
        ]
        for i in range(len(band_y_ranges)):
            y1_a, y2_a = band_y_ranges[i]
            for y1_b, y2_b in band_y_ranges[i + 1 :]:
                inter = max(0.0, min(y2_a, y2_b) - max(y1_a, y1_b))
                shorter = min(y2_a - y1_a, y2_b - y1_b)
                containment_ratio = inter / shorter if shorter > 0 else 0.0
                if containment_ratio < DEFAULT_MIN_COLUMN_Y_OVERLAP:
                    return False

    return True


DEFAULT_GAP_SPLIT_MIN_RATIO = 0.03
# Ebeveyn genişliğine oranla, dikey "seam" (boş şerit) en az bu kadar geniş
# olmalı — küçük satır-içi boşluklar (ör. buton aralıkları) yanlışlıkla
# sütun ayrımı sayılmasın.
DEFAULT_GAP_SPLIT_MIN_HEIGHT_RATIO = 0.3
# Seam'in HER İKİ tarafındaki grup da ebeveyn yüksekliğinin en az bu kadarını
# kaplamalı — bu, "tek bir satırdaki elemanlar arasında tesadüfen büyük bir
# boşluk var" durumunu (ki bunlar sütun değil, aynı satırın parçalarıdır)
# gerçek dikey sütun ayrımından ayırt eder.
DEFAULT_GAP_SPLIT_MIN_CONTENT_HEIGHT_RATIO = 0.5
# Tüm çocukların BİRLEŞİK dikey kapsamı, ebeveyn yüksekliğinin en az bu
# kadarını doldurmalı — aksi halde içerik zaten tek bir satır/bant demektir,
# X'teki boşluklar satır-içi boşluklardır, sütun seam'i değil.


def _find_vertical_seam_split(
    children: list[Node], parent_bbox: list[float]
) -> tuple[list[Node], list[Node]] | None:
    """Çocukları sol kenara göre sıralayıp aralarındaki EN BÜYÜK boş X
    şeridini ("seam") bulur — hiçbir elemanın bu şeridi kesmediği garantisiyle
    (running-max-right / skyline taraması). Bulunursa, seam'in solundaki ve
    sağındaki gruplar (her biri kendi iç yapısına bakılmaksızın) döner.

    Neden gerekli: X-ekseni interval kümeleme (_cluster_by_axis), gerçek bir
    sidebar'ı (kendi içinde farklı alt-X-aralıklarına sahip elemanlardan
    oluşabilir — başlık, liste, alt ikon satırı gibi, bunlar birbiriyle
    yeterince X-örtüşmediği için TEK bir banda düşmüyor) yakalayamıyor; aynı
    şekilde "ana içerik" tarafındaki dağınık küçük elemanları (buton, kart —
    farklı X aralıklarında) da tek bir bant halinde birleştiremiyor, bunun
    yerine hepsini N ayrı (çoğu sahte) banda bölüyor. Gerçek pilot testte
    (YouTube ana sayfası) bu N-parçalı yapı N ayrı sahte "sütuna"
    dönüşüyordu — bkz. _column_split_indicated'ın pairwise Y-örtüşme
    kontrolü bunu artık reddediyor, ama bu da sidebar'ın kendisinin bir sütun
    olarak tanınmasını engelliyordu (ya hep ya hiç). Boşluk-tabanlı tek-seam
    tespiti bunun yerine "insan gözünün gördüğü" TEK boşluğu arar — sidebar'ın
    bittiği, ana içeriğin başladığı YER; elemanların kendi aralarında nasıl
    kümelendiği önemli değil, sadece o TEK boşluğun solunda mı sağında mı
    oldukları önemli.
    """
    if len(children) < 2:
        return None

    parent_width = parent_bbox[2] - parent_bbox[0]
    parent_height = parent_bbox[3] - parent_bbox[1]
    if parent_width <= 0 or parent_height <= 0:
        return None

    content_y1 = min(n.bbox[1] for n in children)
    content_y2 = max(n.bbox[3] for n in children)
    if (content_y2 - content_y1) / parent_height < DEFAULT_GAP_SPLIT_MIN_CONTENT_HEIGHT_RATIO:
        return None

    ordered = sorted(children, key=lambda n: n.bbox[0])
    running_max_right = ordered[0].bbox[2]
    best_gap = 0.0
    best_idx = None
    for i in range(1, len(ordered)):
        gap = ordered[i].bbox[0] - running_max_right
        if gap > best_gap:
            best_gap = gap
            best_idx = i
        running_max_right = max(running_max_right, ordered[i].bbox[2])

    if best_idx is None or best_gap < parent_width * DEFAULT_GAP_SPLIT_MIN_RATIO:
        return None

    left, right = ordered[:best_idx], ordered[best_idx:]

    left_height = max(n.bbox[3] for n in left) - min(n.bbox[1] for n in left)
    right_height = max(n.bbox[3] for n in right) - min(n.bbox[1] for n in right)
    if left_height / parent_height < DEFAULT_GAP_SPLIT_MIN_HEIGHT_RATIO:
        return None
    if right_height / parent_height < DEFAULT_GAP_SPLIT_MIN_HEIGHT_RATIO:
        return None

    return left, right


def _build_gap_split(
    left: list[Node],
    right: list[Node],
    parent_bbox: list[float],
    *,
    next_id: Callable[[], str],
    overlap_threshold: float,
) -> tuple[list[Node], dict]:
    """Boşluk-tabanlı tek-seam split'in iki tarafını, her biri KENDİ iç
    düzenini bulmak üzere recursive olarak infer_layout_for_children'a geri
    göndererek bir flex-row'a sarar."""
    new_children: list[Node] = []
    for group in (left, right):
        if len(group) == 1:
            new_children.append(group[0])
            continue
        group_bbox = union_bbox([n.bbox for n in group])
        sub_children, sub_layout = infer_layout_for_children(
            group, group_bbox, next_id=next_id, overlap_threshold=overlap_threshold
        )
        wrapper = Node(id=next_id(), label=None, bbox=group_bbox, children=sub_children, synthetic=True)
        wrapper.layout = sub_layout
        new_children.append(wrapper)

    layout = _build_axis_layout(new_children, parent_bbox, direction="row")
    return new_children, layout


def _build_column_split(
    x_bands: list[dict],
    parent_bbox: list[float],
    *,
    next_id: Callable[[], str],
    overlap_threshold: float,
) -> tuple[list[Node], dict]:
    """Yan yana duran bağımsız bölgeleri (sidebar | ana içerik gibi) bir
    flex-row'a, her bölgeyi ise KENDİ iç düzenini bulmak üzere recursive
    olarak infer_layout_for_children'a geri gönderir."""
    bands_sorted = sorted(x_bands, key=lambda b: b["range"][0])
    new_children: list[Node] = []

    for b in bands_sorted:
        nodes = b["nodes"]
        if len(nodes) == 1:
            new_children.append(nodes[0])
            continue

        band_bbox = union_bbox([n.bbox for n in nodes])
        sub_children, sub_layout = infer_layout_for_children(
            nodes, band_bbox, next_id=next_id, overlap_threshold=overlap_threshold
        )
        wrapper = Node(id=next_id(), label=None, bbox=band_bbox, children=sub_children, synthetic=True)
        wrapper.layout = sub_layout
        new_children.append(wrapper)

    layout = _build_axis_layout(new_children, parent_bbox, direction="row")
    return new_children, layout


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

    seam_split = _find_vertical_seam_split(children, parent_bbox)
    if seam_split is not None:
        return _build_gap_split(*seam_split, parent_bbox, next_id=next_id, overlap_threshold=overlap_threshold)

    x_bands = _cluster_by_axis(children, x_range, overlap_threshold)
    if _column_split_indicated(x_bands, len(children), parent_bbox):
        return _build_column_split(x_bands, parent_bbox, next_id=next_id, overlap_threshold=overlap_threshold)

    y_bands = _cluster_by_axis(children, y_range, overlap_threshold)

    if len(y_bands) == 1:
        # NOT: burada gap-split UYGULANMAZ — bu dal, tüm children kümesinin
        # zaten tek bir y-bandında olduğu (genelde gerçek/kapsanmış bir
        # container'ın tüm çocukları, ör. bir header'ın logo+link+buton'u)
        # güçlü bir sinyal. justify:space-between gibi kasıtlı geniş
        # boşluklu satırlar burada yanlışlıkla bölünmemeli — gap-split'i
        # sadece aşağıdaki "karışık bantlar içinde tekil kalan bant" dalında
        # (containment'a değil, salt y-örtüşmesine dayanan daha zayıf bir
        # sinyal) uyguluyoruz.
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
            row_children, _ = _split_row_into_entries(band_nodes, next_id=next_id)
            wrapper = Node(
                id=next_id(),
                label=None,
                bbox=union_bbox([n.bbox for n in band_nodes]),
                children=row_children,
                synthetic=True,
            )
            wrapper.layout = _build_axis_layout(row_children, wrapper.bbox, direction="row")
            new_children.append(wrapper)
            i += 1

    layout = _build_axis_layout(new_children, parent_bbox, direction="column")
    return new_children, layout
