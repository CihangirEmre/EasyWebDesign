"""ScreenCoder-tarzı basit mimari — kaba bölge çözümleme.

Girdi: Aşama 1'in (src/grounding, artık sadece sidebar/header/navigation/
main_content arayan kaba prompt — bkz. src/grounding/prompts.py) ürettiği
`{bbox_2d, label}` tespit listesi (0-1000 normalize).

Karar (ScreenCoderClone'un `block_parsor.py::resolve_containment`'ından
adapte): büyük düzen bileşenleri birbirini İÇERMEMELİ — bir bbox diğerini
tamamen kapsıyorsa, küçük olanı (muhtemelen aynı bölgenin yanlışlıkla ikinci
kez, daha dar tespit edilmiş hali) atılır. Model çağrısı YOK — tamamen
kural-tabanlı, model.py/inference.py'ye bağımlı değil.
"""

from __future__ import annotations

from src.grounding.coords import denormalize_bbox

BBox = tuple[float, float, float, float]


def _contains(box_a: BBox, box_b: BBox) -> bool:
    """box_a, box_b'yi tamamen kapsıyor mu?"""
    xa1, ya1, xa2, ya2 = box_a
    xb1, yb1, xb2, yb2 = box_b
    return xa1 <= xb1 and ya1 <= yb1 and xa2 >= xb2 and ya2 >= yb2


def resolve_containment(detections: list[dict]) -> list[dict]:
    """Bir bbox diğerini tamamen kapsıyorsa, kapsananı listeden çıkarır."""
    removed: set[int] = set()
    for i in range(len(detections)):
        for j in range(len(detections)):
            if i == j or i in removed or j in removed:
                continue
            box_i = tuple(detections[i]["bbox_2d"])
            box_j = tuple(detections[j]["bbox_2d"])
            if _contains(box_i, box_j) or _contains(box_j, box_i):
                removed.add(j)
    return [d for idx, d in enumerate(detections) if idx not in removed]


def _expand_main_content(regions: list[dict], canvas_width: int, canvas_height: int) -> list[dict]:
    """Qwen3-VL sadece 4 kaba etiket (sidebar/header/navigation/main_content)
    döndürüyor ve GROUNDING_PROMPT "main_content = geri kalan her şey" dese de
    model bunu genelde sadece en belirgin içerik bloğuna SIKI bir kutu olarak
    tespit ediyor — gerçek Colab çıktısında (upload_0001) main_content
    [604,228,1322,501] gibi kanvasın küçük bir parçasıydı, geri kalan tüm
    kanvas (sol/sağ/üst/alt kenarlar) hiçbir region'a girmediği için üretim
    hiç çağrılmıyor ve render'da dümdüz beyaz kalıyordu.

    Bu yüzden main_content'i modele güvenmeden DETERMİNİSTİK olarak diğer 3
    bölgenin dışında kalan tüm kanvası kapsayacak şekilde genişletiyoruz
    (küçültmüyoruz — sadece BÜYÜTÜYORUZ, modelin doğru tespit ettiği kısmı
    korumak için union alıyoruz). Klasik uygulama kabuğu varsayımı: sidebar
    tam yükseklikte bir kenar sütunu, header tam genişlikte bir üst şerit,
    navigation ana sütunun İÇİNDE (header'ın altında) bir çubuk — main_content
    geri kalan her şeyi doldurur.
    """
    by_label = {r["label"]: r for r in regions if r["label"] != "main_content"}
    main_regions = [r for r in regions if r["label"] == "main_content"]

    left, top, right, bottom = 0, 0, canvas_width, canvas_height

    sidebar = by_label.get("sidebar")
    if sidebar:
        sx1, _, sx2, _ = sidebar["bbox"]
        if (sx1 + sx2) / 2 < canvas_width / 2:
            left = max(left, sx2)  # sol sidebar -> main ondan sonra başlar
        else:
            right = min(right, sx1)  # sağ sidebar -> main ondan önce biter

    header = by_label.get("header")
    if header:
        _, _, _, hy2 = header["bbox"]
        top = max(top, hy2)

    navigation = by_label.get("navigation")
    if navigation:
        nx1, _, nx2, ny2 = navigation["bbox"]
        # navigation'ın x-aralığı ana sütunla örtüşüyorsa (sidebar'ın kendi
        # içinde değil, üstte ayrı bir çubuksa) main_content ondan sonra başlar
        if nx2 > left and nx1 < right:
            top = max(top, ny2)

    if main_regions:
        target = main_regions[0]
        mx1, my1, mx2, my2 = target["bbox"]
        target["bbox"] = [min(mx1, left), min(my1, top), max(mx2, right), max(my2, bottom)]
        return [r for r in regions if r["label"] != "main_content"] + [target]

    new_region = {"id": f"region_{len(regions)}", "label": "main_content", "bbox": [left, top, right, bottom]}
    return regions + [new_region]


def build_regions(detections: list[dict], image_width: int, image_height: int) -> list[dict]:
    """Normalize tespitleri, containment-resolve + main_content genişletme
    uygulanmış piksel bbox'lı region listesine çevirir:
    [{"id": "region_0", "label": "...", "bbox": [x1,y1,x2,y2]}]"""
    resolved = resolve_containment(detections)
    regions: list[dict] = []
    for i, det in enumerate(resolved):
        bbox_px = [round(v) for v in denormalize_bbox(det["bbox_2d"], image_width, image_height)]
        regions.append({"id": f"region_{i}", "label": det["label"], "bbox": bbox_px})
    return _expand_main_content(regions, image_width, image_height)
