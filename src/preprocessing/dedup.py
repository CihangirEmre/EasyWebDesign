"""Aşama 0 — Ön İşleme: pHash tabanlı deduplication ve sızıntı kontrolü.

Karar (CLAUDE.md §2, Aşama 0 ve §4 kural 8): pHash ile deduplication
yapılmalı; eğitim/dış-test seti arasında görsel örtüşme kontrol edilmeli
(dış test setleri asla eğitimde kullanılmamalı).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import imagehash
from PIL import Image

DEFAULT_HAMMING_THRESHOLD = 5  # bu mesafenin altı "neredeyse aynı görsel" sayılır


def compute_phash(image_path: str | Path) -> imagehash.ImageHash:
    with Image.open(image_path) as img:
        return imagehash.phash(img)


def _hash_all(image_paths: list[Path]) -> dict[Path, imagehash.ImageHash]:
    return {p: compute_phash(p) for p in image_paths}


@dataclass(frozen=True)
class DuplicatePair:
    a: Path
    b: Path
    distance: int


def find_duplicates(
    image_paths: list[str | Path],
    *,
    threshold: int = DEFAULT_HAMMING_THRESHOLD,
) -> list[DuplicatePair]:
    """Bir görsel kümesi içindeki neredeyse-aynı çiftleri bulur (O(n^2))."""
    paths = [Path(p) for p in image_paths]
    hashes = _hash_all(paths)
    pairs: list[DuplicatePair] = []
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            dist = hashes[paths[i]] - hashes[paths[j]]
            if dist <= threshold:
                pairs.append(DuplicatePair(a=paths[i], b=paths[j], distance=dist))
    return pairs


def dedupe_directory(
    image_dir: str | Path,
    *,
    pattern: str = "*.png",
    threshold: int = DEFAULT_HAMMING_THRESHOLD,
) -> tuple[list[Path], list[DuplicatePair]]:
    """Bir klasördeki PNG'leri tarar, tekrarlanan çiftleri raporlar.

    Döner: (benzersiz_kalan_dosyalar, bulunan_tekrar_çiftleri).
    Silme yapmaz — karar çağıran tarafa bırakılır (hangi kopyanın tutulacağı
    içerik kalitesine göre değişebilir).
    """
    paths = sorted(Path(image_dir).glob(pattern))
    pairs = find_duplicates(paths, threshold=threshold)
    duplicate_set = {pair.b for pair in pairs}
    unique = [p for p in paths if p not in duplicate_set]
    return unique, pairs

# önemsiz 
# def check_train_external_overlap(
#     train_dir: str | Path,
#     external_dir: str | Path,
#     *,
#     pattern: str = "*.png",
#     threshold: int = DEFAULT_HAMMING_THRESHOLD,
# ) -> list[DuplicatePair]:
#     """Eğitim seti ile dış (izole) değerlendirme seti arasında görsel
#     örtüşme olup olmadığını kontrol eder.

#     Boş olmayan bir sonuç veri sızıntısı riski demektir — dış test setinden
#     görüntülerin eğitim verisiyle örtüştüğü anlamına gelir ve bu görüntüler
#     eğitim setinden çıkarılmalıdır.
#     """
#     train_paths = sorted(Path(train_dir).glob(pattern))
#     external_paths = sorted(Path(external_dir).glob(pattern))
#     train_hashes = _hash_all(train_paths)
#     external_hashes = _hash_all(external_paths)

#     overlaps: list[DuplicatePair] = []
#     for t_path, t_hash in train_hashes.items():
#         for e_path, e_hash in external_hashes.items():
#             dist = t_hash - e_hash
#             if dist <= threshold:
#                 overlaps.append(DuplicatePair(a=t_path, b=e_path, distance=dist))
#     return overlaps
