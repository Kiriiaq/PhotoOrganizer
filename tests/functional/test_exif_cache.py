# -*- coding: utf-8 -*-
"""Tests de non-régression pour le cache des métadonnées EXIF (T-114).

Vérifie que ``get_exif_data()`` alimente bien le cache global persistant
(``utils.cache``) et le consulte sur les appels suivants.

Bug historique : le cache mémoire interne d'``ExifExtractor`` était
indépendant du cache global. Résultat : ``cache.get_stats()['hit_rate']``
restait à 0 % même après des dizaines de re-scans (cf. retour qualif
2026-05-13, T-114).
"""

import pytest
from pathlib import Path


@pytest.fixture
def sample_photo(tmp_path):
    """Génère une photo JPG avec EXIF basique pour les tests."""
    from PIL import Image
    p = tmp_path / "sample.jpg"
    img = Image.new("RGB", (100, 75), (120, 150, 180))
    img.save(p, "jpeg")
    return p


def test_global_cache_records_hits_after_repeated_reads(sample_photo):
    """T-114 : 2 lectures successives doivent produire 1 hit cache global."""
    from core.metadata.exif_extractor import get_exif_data, get_extractor
    from utils.cache import get_cache, init_cache

    init_cache()
    cache = get_cache()
    cache.clear()
    extractor = get_extractor()
    extractor.clear_cache()

    # 1er appel → miss (extraction réelle + cache.set)
    get_exif_data(str(sample_photo))

    # Vider le cache mémoire interne pour forcer le passage par le cache global
    extractor.clear_cache()

    # 2e appel → doit hit le cache global
    get_exif_data(str(sample_photo))

    stats = cache.get_stats()
    hit_rate_str = stats.get('hit_rate', '0%')
    hit_rate = float(hit_rate_str.rstrip('%'))

    assert hit_rate > 0, (
        f"T-114 régression : hit rate à {hit_rate}% — le cache global "
        f"n'est pas consulté par get_exif_data(). Stats : {stats}"
    )


def test_global_cache_persists_between_extractor_instances(sample_photo, tmp_path):
    """Vérifie que le cache global persiste même si on recrée ExifExtractor."""
    from core.metadata.exif_extractor import ExifExtractor, get_exif_data
    from utils.cache import get_cache, init_cache

    init_cache()
    cache = get_cache()
    cache.clear()

    # 1ère extraction
    e1 = ExifExtractor()
    e1.extract(str(sample_photo))

    # Nouvelle instance — le cache mémoire local est vide mais le global pas
    e2 = ExifExtractor()
    data = e2.extract(str(sample_photo))

    assert data, "Métadonnées vides"
    stats = cache.get_stats()
    hit_rate = float(stats.get('hit_rate', '0%').rstrip('%'))
    assert hit_rate > 0, "Cache global ne persiste pas entre instances"


def test_use_cache_false_bypasses_global_cache(sample_photo):
    """``use_cache=False`` doit bypasser TOUTES les couches de cache."""
    from core.metadata.exif_extractor import get_extractor
    from utils.cache import get_cache, init_cache

    init_cache()
    cache = get_cache()
    cache.clear()
    extractor = get_extractor()
    extractor.clear_cache()

    # Pré-remplir le cache global
    extractor.extract(str(sample_photo), use_cache=True)
    initial_stats = cache.get_stats()
    initial_hits = initial_stats.get('hits', 0) if 'hits' in initial_stats else 0

    # Lecture avec use_cache=False ne doit pas hitter
    extractor.extract(str(sample_photo), use_cache=False)
    new_stats = cache.get_stats()
    new_hits = new_stats.get('hits', 0) if 'hits' in new_stats else 0

    assert new_hits == initial_hits, (
        "use_cache=False ne doit pas consulter le cache global"
    )
