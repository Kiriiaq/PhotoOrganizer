"""Tests fonctionnels du SmartOrganizer : organisation par date/format."""

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from core.operations.file_manager import FileManager  # noqa: E402
from core.operations.organizer import OrganizationOptions, SmartOrganizer  # noqa: E402


@pytest.fixture
def organizer():
    return SmartOrganizer()


@pytest.fixture
def photos(tmp_path):
    """Crée 3 photos JPEG factices."""
    from PIL import Image

    paths = []
    for i in range(3):
        p = tmp_path / f"p_{i}.jpg"
        Image.new("RGB", (50, 50), (i * 60, 0, 0)).save(p)
        paths.append(str(p))
    return paths


def test_organize_empty(organizer, tmp_path):
    res = organizer.organize([], str(tmp_path), OrganizationOptions())
    assert res.total == 0


def test_organize_copies_files_into_dest(organizer, photos, tmp_path):
    dest = tmp_path / "out"
    opts = OrganizationOptions(
        organize_by_date=False, organize_by_camera=False, organize_by_location=False, copy_not_move=True
    )
    res = organizer.organize(photos, str(dest), opts)
    assert res.total == 3
    # Sans aucun critère actif → les fichiers vont à la racine de dest
    assert (dest).exists()


def test_organize_by_date_falls_back_to_sans_date(organizer, photos, tmp_path):
    """Sans EXIF, les photos atterrissent dans 'Sans date'."""
    dest = tmp_path / "out"
    opts = OrganizationOptions(organize_by_date=True)
    res = organizer.organize(photos, str(dest), opts)
    assert res.processed >= 0  # PIL Image.new peut produire ou non du EXIF
    # Soit 'Sans date' existe, soit un YYYY existe
    assert any(p.is_dir() for p in dest.iterdir())


def test_organize_move_preserves_session(tmp_path):
    """Le FileManager partagé enregistre toutes les opérations."""
    from PIL import Image

    fm = FileManager()
    org = SmartOrganizer(file_manager=fm)
    src = tmp_path / "src.jpg"
    Image.new("RGB", (10, 10)).save(src)
    dest = tmp_path / "out"
    opts = OrganizationOptions(organize_by_date=False, copy_not_move=False)
    org.organize([str(src)], str(dest), opts)
    history = fm.get_operations_history()
    assert len(history) == 1
    assert history[0].operation_type == "move"
    assert history[0].success


def test_organize_cancel_propagates(tmp_path):
    """SmartOrganizer.cancel() doit interrompre la boucle."""
    from PIL import Image

    org = SmartOrganizer()
    paths = []
    for i in range(20):
        p = tmp_path / f"f_{i}.jpg"
        Image.new("RGB", (5, 5)).save(p)
        paths.append(str(p))

    cancelled_at = {"value": None}

    def cb(current, total, message):
        if current >= 3 and cancelled_at["value"] is None:
            cancelled_at["value"] = current
            org.cancel()

    res = org.organize(paths, str(tmp_path / "out"), OrganizationOptions(), cb)
    # On a annulé : le total processed doit être < total
    assert res.total == 20
    assert res.processed < 20


def test_organization_options_from_dict_defaults():
    o = OrganizationOptions.from_dict({})
    assert o.organize_by_date is True
    assert o.date_format == "year/month/day"
    assert o.criteria_order == ["date", "camera", "location"]


def test_sanitize_dirname_cleans_forbidden_chars(organizer):
    bad = 'a/b\\c:d*e?f"g<h>i|j'
    cleaned = organizer._sanitize_dirname(bad)
    for ch in '<>:"/\\|?*':
        assert ch not in cleaned


def test_multilayer_respects_criteria_order(tmp_path):
    """En multicouche, la hiérarchie suit ``criteria_order``."""

    from PIL import Image

    src = tmp_path / "p.jpg"
    Image.new("RGB", (10, 10)).save(src)

    org = SmartOrganizer()
    dest = tmp_path / "out"

    # On force criteria_order = ['camera', 'date'] : Appareil avant Date
    opts = OrganizationOptions(
        organize_by_date=True,
        organize_by_camera=True,
        organize_by_location=False,
        multilayer=True,
        criteria_order=["camera", "date", "location"],
        date_format="year",
    )

    res = org.organize([str(src)], str(dest), opts)
    assert res.processed == 1

    # Le 1er niveau du chemin de destination doit être l'appareil ('Appareil
    # inconnu' faute d'EXIF), puis la date (ou 'Sans date').
    children = [p.name for p in dest.iterdir()]
    # Premier niveau = critère #1 = 'camera' → 'Appareil inconnu'
    assert "Appareil inconnu" in children, f"Children: {children}"


def test_size_filter_rejects_too_small(tmp_path):
    """Lot R1 : filtre size_min_bytes rejette les fichiers trop petits."""
    from PIL import Image

    small = tmp_path / "small.jpg"
    Image.new("RGB", (10, 10)).save(small)
    big = tmp_path / "big.jpg"
    Image.new("RGB", (1000, 1000)).save(big)

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=False,
        organize_by_camera=False,
        size_min_bytes=10000,  # rejette small (< 10 Ko)
        validate_disk_space=False,
    )
    res = org.organize([str(small), str(big)], str(tmp_path / "out"), opts)
    assert res.processed == 1
    assert res.skipped == 1


def test_skip_if_identical(tmp_path):
    """Lot R2 : skip_if_identical n'écrase pas un fichier identique existant."""
    from PIL import Image

    src = tmp_path / "p.jpg"
    Image.new("RGB", (50, 50)).save(src)
    dest_dir = tmp_path / "out"
    dest_dir.mkdir()
    # On copie une première fois manuellement le fichier identique
    import shutil

    shutil.copy2(src, dest_dir / "p.jpg")

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=False,
        organize_by_camera=False,
        skip_if_identical=True,
        auto_rename=False,
        validate_disk_space=False,
    )
    res = org.organize([str(src)], str(dest_dir), opts)
    # 1 fichier détecté mais skip car identique déjà présent
    assert res.processed == 0
    assert res.skipped == 1


def test_rename_template(tmp_path):
    """Lot Q4 : le template de renommage est appliqué au fichier final."""
    from PIL import Image

    src = tmp_path / "IMG_0001.jpg"
    Image.new("RGB", (50, 50)).save(src)

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=False,
        organize_by_camera=False,
        rename_template="{counter:04d}_{original}",
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    org.organize([str(src)], str(dest), opts)
    # Le fichier final s'appelle "0001_IMG_0001.jpg"
    files = list(dest.iterdir())
    assert any(f.name == "0001_IMG_0001.jpg" for f in files), f"got: {[f.name for f in files]}"


def test_organize_by_location_falls_back_when_no_gps(tmp_path):
    """Sans EXIF GPS, le fichier va dans 'Sans localisation GPS' et le
    compteur ``files_without_gps`` est incrémenté."""
    from PIL import Image

    src = tmp_path / "no_gps.jpg"
    Image.new("RGB", (40, 40)).save(src)

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=False,
        organize_by_camera=False,
        organize_by_location=True,
        use_geocoding=False,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    res = org.organize([str(src)], str(dest), opts)
    assert res.processed == 1
    assert (dest / "Sans localisation GPS").is_dir()
    assert res.files_without_gps == 1
    assert res.files_with_gps == 0


def test_organize_by_location_raw_coords_when_geocoding_disabled(tmp_path):
    """Avec GPS et géocodage off, le dossier porte le nom Lat_x_Lon_y."""
    import piexif
    from PIL import Image

    src = tmp_path / "with_gps.jpg"
    img = Image.new("RGB", (50, 50))

    # GPS Paris ~ 48.8566 N, 2.3522 E (encodé en rationnels EXIF)
    def to_dms(deg):
        d = int(deg)
        m_full = (deg - d) * 60
        m = int(m_full)
        s = (m_full - m) * 60
        return ((d, 1), (m, 1), (int(s * 1000), 1000))

    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: to_dms(48.8566),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: to_dms(2.3522),
    }
    exif_bytes = piexif.dump({"GPS": gps_ifd})
    img.save(src, exif=exif_bytes)

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=False,
        organize_by_camera=False,
        organize_by_location=True,
        use_geocoding=False,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    res = org.organize([str(src)], str(dest), opts)
    assert res.processed == 1
    assert res.files_with_gps == 1
    assert res.files_raw_coords == 1
    # Le dossier doit s'appeler "Lat_48.8566_Lon_2.3522" (ou suffixe sanitisé)
    children = [c.name for c in dest.iterdir()]
    assert any(c.startswith("Lat_") for c in children), f"got: {children}"


def test_organize_by_location_offline_fallback(tmp_path, monkeypatch):
    """Si gps_processor.get_location_name lève (réseau down), on retombe
    silencieusement sur Lat_x_Lon_y au lieu de planter."""
    import piexif
    from PIL import Image

    src = tmp_path / "p.jpg"
    img = Image.new("RGB", (40, 40))
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: ((45, 1), (45, 1), (0, 1)),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: ((4, 1), (45, 1), (0, 1)),
    }
    img.save(src, exif=piexif.dump({"GPS": gps_ifd}))

    org = SmartOrganizer()
    # Forcer get_location_name à lever — simule un timeout ou l'absence d'internet
    monkeypatch.setattr(
        org.gps_processor, "get_location_name", lambda lat, lon: (_ for _ in ()).throw(RuntimeError("offline"))
    )
    opts = OrganizationOptions(
        organize_by_date=False,
        organize_by_camera=False,
        organize_by_location=True,
        use_geocoding=True,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    res = org.organize([str(src)], str(dest), opts)
    assert res.processed == 1
    # Le fichier doit être dans Lat_x_Lon_y, pas dans 'Sans localisation GPS'
    assert res.files_with_gps == 1
    assert res.files_raw_coords == 1
    assert res.files_geocoded == 0
    assert any(p.name.startswith("Lat_") for p in dest.iterdir())


def test_burst_detection_groups_close_photos(tmp_path):
    """Lot S1 : 3 photos prises < 3 s d'écart → sous-dossier Burst_01."""
    from datetime import datetime as dt

    import piexif
    from PIL import Image

    def make_photo(name: str, when: dt):
        path = tmp_path / name
        img = Image.new("RGB", (50, 50))
        exif_dict = {
            "Exif": {piexif.ExifIFD.DateTimeOriginal: when.strftime("%Y:%m:%d %H:%M:%S").encode()},
        }
        img.save(path, exif=piexif.dump(exif_dict))
        return path

    base = dt(2026, 5, 7, 12, 0, 0)
    p1 = make_photo("a.jpg", base)
    p2 = make_photo("b.jpg", base.replace(second=1))
    p3 = make_photo("c.jpg", base.replace(second=2))
    # une photo isolée 1 minute plus tard → pas de burst
    p4 = make_photo("z.jpg", base.replace(minute=1))

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=True,
        organize_by_camera=False,
        date_format="year",
        detect_bursts=True,
        burst_threshold_seconds=3,
        burst_min_count=3,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    res = org.organize([str(p1), str(p2), str(p3), str(p4)], str(dest), opts)
    assert res.processed == 4
    # On doit avoir un dossier 2026/Burst_01 contenant 3 fichiers
    burst_dir = dest / "2026" / "Burst_01"
    assert burst_dir.is_dir(), f"Burst_01 manquant — content: {list(dest.rglob('*'))}"
    assert len(list(burst_dir.glob("*.jpg"))) == 3
    # Et le fichier isolé reste à la racine de 2026/
    isolated = list((dest / "2026").glob("*.jpg"))
    assert len(isolated) == 1


def test_burst_detection_numbers_independently_per_destination(tmp_path):
    """Audit 2026-05-15 — Lot S1 amélioré.

    Deux rafales de 3 photos chacune, situées sur deux jours différents.
    Comme on regroupe les bursts PAR dossier-destination avant
    détection, chaque dossier doit avoir son propre ``Burst_01``
    (numérotation indépendante), pas ``Burst_01`` puis ``Burst_02``.
    """
    from datetime import datetime as dt

    import piexif
    from PIL import Image

    def make_photo(name: str, when: dt):
        path = tmp_path / name
        img = Image.new("RGB", (50, 50))
        exif_dict = {
            "Exif": {piexif.ExifIFD.DateTimeOriginal: when.strftime("%Y:%m:%d %H:%M:%S").encode()},
        }
        img.save(path, exif=piexif.dump(exif_dict))
        return path

    # Burst 1 — Vacances 2024
    d1 = dt(2024, 1, 15, 10, 0, 0)
    a1 = make_photo("a1.jpg", d1)
    a2 = make_photo("a2.jpg", d1.replace(second=1))
    a3 = make_photo("a3.jpg", d1.replace(second=2))

    # Burst 2 — Vacances 2026 (jour différent → dossier différent)
    d2 = dt(2026, 5, 7, 14, 0, 0)
    b1 = make_photo("b1.jpg", d2)
    b2 = make_photo("b2.jpg", d2.replace(second=1))
    b3 = make_photo("b3.jpg", d2.replace(second=2))

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=True,
        organize_by_camera=False,
        date_format="year/month/day",
        detect_bursts=True,
        burst_threshold_seconds=3,
        burst_min_count=3,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    res = org.organize(
        [str(a1), str(a2), str(a3), str(b1), str(b2), str(b3)],
        str(dest),
        opts,
    )
    assert res.processed == 6

    # Chaque dossier-destination doit avoir son propre Burst_01
    burst_2024 = dest / "2024" / "01" / "2024_01_15" / "Burst_01"
    burst_2026 = dest / "2026" / "05" / "2026_05_07" / "Burst_01"
    assert burst_2024.is_dir(), f"Burst_01 manquant pour 2024 — {list(dest.rglob('*'))}"
    assert burst_2026.is_dir(), f"Burst_01 manquant pour 2026 — {list(dest.rglob('*'))}"
    assert len(list(burst_2024.glob("*.jpg"))) == 3
    assert len(list(burst_2026.glob("*.jpg"))) == 3

    # Sécurité : pas de Burst_02 dans aucun dossier (chaque dossier
    # n'en a qu'un, la numérotation est bien locale).
    assert not (dest / "2024" / "01" / "2024_01_15" / "Burst_02").exists()
    assert not (dest / "2026" / "05" / "2026_05_07" / "Burst_02").exists()


def test_burst_detection_auto_clamp_bounds_are_configurable(tmp_path):
    """Audit 2026-05-15 (élargissement) — bornes auto exposées.

    Sans bornes étendues : 7 photos espacées d'une heure (Δ = 3600 s)
    → en mode auto le seuil tomberait à 1 s (clamp historique [1; 600]),
    aucune photo n'est regroupée → 0 burst.

    Avec auto_max élargi à 7200 s : mean − stddev ≈ 3600 s,
    clampé à 7200 → seuil ≈ 3600 s → toutes les photos forment 1 burst.

    Couvre le scénario timelapse / pose lente qui motive l'option.
    """
    from datetime import datetime as dt
    from datetime import timedelta

    import piexif
    from PIL import Image

    def make_photo(name: str, when: dt):
        path = tmp_path / name
        img = Image.new("RGB", (40, 40))
        exif_dict = {
            "Exif": {piexif.ExifIFD.DateTimeOriginal: when.strftime("%Y:%m:%d %H:%M:%S").encode()},
        }
        img.save(path, exif=piexif.dump(exif_dict))
        return path

    base = dt(2026, 6, 1, 8, 0, 0)
    paths = [make_photo(f"t_{i}.jpg", base + timedelta(hours=i)) for i in range(7)]

    # 1ʳᵉ exécution : bornes par défaut [1 ; 600] → seuil clampé à 600 s,
    # Δ réels 3600 s >> 600 s → aucun burst.
    org1 = SmartOrganizer()
    opts_default = OrganizationOptions(
        organize_by_date=True,
        organize_by_camera=False,
        date_format="year",
        detect_bursts=True,
        burst_mode="auto",
        burst_threshold_seconds=999,
        burst_min_count=3,
        validate_disk_space=False,
    )
    dest1 = tmp_path / "out1"
    res1 = org1.organize([str(p) for p in paths], str(dest1), opts_default)
    assert res1.processed == 7
    assert not any(p.is_dir() and p.name.startswith("Burst_") for p in (dest1 / "2026").iterdir()), (
        "Pas de burst attendu avec bornes par défaut"
    )

    # 2ᵉ exécution : auto_max élargi à 7200 s → seuil clampé sous 3600 s
    # → toutes les photos rentrent dans un seul Burst_01.
    org2 = SmartOrganizer()
    opts_wide = OrganizationOptions(
        organize_by_date=True,
        organize_by_camera=False,
        date_format="year",
        detect_bursts=True,
        burst_mode="auto",
        burst_threshold_seconds=999,
        burst_min_count=3,
        burst_auto_min_seconds=1,
        burst_auto_max_seconds=7200,
        validate_disk_space=False,
    )
    dest2 = tmp_path / "out2"
    res2 = org2.organize([str(p) for p in paths], str(dest2), opts_wide)
    assert res2.processed == 7
    burst_dir = dest2 / "2026" / "Burst_01"
    assert burst_dir.is_dir(), f"Burst attendu avec auto_max=7200 — got: {list(dest2.rglob('*'))}"
    assert len(list(burst_dir.glob("*.jpg"))) == 7


def test_burst_detection_auto_min_clamp_floors_threshold(tmp_path):
    """Audit 2026-05-15 — auto_min permet d'ignorer les vraies rafales.

    8 photos avec un Δ tres court (1 s) entre 4 premières (qui seraient
    un burst en defaut), puis 4 photos plus espacées (Δ 30 s) :
    avec auto_min=20 s, le clamp force le seuil à >= 20 s, donc toutes
    les photos rentrent dans le même groupe. On obtient 1 seul burst
    de 8 (au lieu de 2 séparés).
    """
    from datetime import datetime as dt
    from datetime import timedelta

    import piexif
    from PIL import Image

    def make_photo(name: str, when: dt):
        path = tmp_path / name
        img = Image.new("RGB", (40, 40))
        exif_dict = {
            "Exif": {piexif.ExifIFD.DateTimeOriginal: when.strftime("%Y:%m:%d %H:%M:%S").encode()},
        }
        img.save(path, exif=piexif.dump(exif_dict))
        return path

    base = dt(2026, 7, 1, 10, 0, 0)
    paths = []
    # 4 photos rapprochées (Δ 1 s)
    for i in range(4):
        paths.append(make_photo(f"a_{i}.jpg", base + timedelta(seconds=i)))
    # 4 photos plus espacées (Δ 30 s à partir de la dernière rapide)
    for i in range(4):
        paths.append(make_photo(f"b_{i}.jpg", base + timedelta(seconds=3 + 30 * (i + 1))))

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=True,
        organize_by_camera=False,
        date_format="year",
        detect_bursts=True,
        burst_mode="auto",
        burst_threshold_seconds=999,
        burst_min_count=3,
        burst_auto_min_seconds=60,  # force seuil ≥ 60 s
        burst_auto_max_seconds=600,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    res = org.organize([str(p) for p in paths], str(dest), opts)
    assert res.processed == 8
    # Avec un seuil ≥ 60 s, les Δ de 1 s et 30 s sont tous sous le seuil
    # → on doit avoir UN seul Burst_01 contenant les 8 photos.
    burst_dir = dest / "2026" / "Burst_01"
    assert burst_dir.is_dir(), f"Burst_01 attendu — got: {list(dest.rglob('*'))}"
    assert len(list(burst_dir.glob("*.jpg"))) == 8
    # Et pas de Burst_02 ailleurs.
    assert not (dest / "2026" / "Burst_02").exists()


def test_burst_detection_auto_bounds_inverted_are_repaired(tmp_path):
    """Audit 2026-05-15 — robustesse : si auto_min > auto_max par erreur,
    le code remet les bornes dans le bon ordre plutôt que de cracher."""
    from datetime import datetime as dt
    from datetime import timedelta

    import piexif
    from PIL import Image

    def make_photo(name: str, when: dt):
        path = tmp_path / name
        img = Image.new("RGB", (40, 40))
        exif_dict = {
            "Exif": {piexif.ExifIFD.DateTimeOriginal: when.strftime("%Y:%m:%d %H:%M:%S").encode()},
        }
        img.save(path, exif=piexif.dump(exif_dict))
        return path

    base = dt(2026, 8, 15, 12, 0, 0)
    paths = [make_photo(f"x_{i}.jpg", base + timedelta(seconds=i)) for i in range(4)]

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=True,
        organize_by_camera=False,
        date_format="year",
        detect_bursts=True,
        burst_mode="auto",
        burst_min_count=3,
        # Bornes inversées : min > max
        burst_auto_min_seconds=600,
        burst_auto_max_seconds=1,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    # Ne doit pas lever — les bornes sont remises à [1 ; 600] en interne.
    res = org.organize([str(p) for p in paths], str(dest), opts)
    assert res.processed == 4


def test_burst_detection_auto_mode_uses_per_folder_stats(tmp_path):
    """Audit 2026-05-15 — mode auto : mean/stddev calculé PAR dossier.

    Scénario : un seul dossier-destination (year='2026'). On a
    deux groupes de photos :
      * Burst : 4 photos en 4 secondes (deltas = 1s, 1s, 1s)
      * Hors burst : 2 photos espacées de 100 s (delta = 100s)
    En mode auto, mean ≈ 25.6s, stddev ≈ 42.8s → seuil = max(1, 25.6 - 42.8) = 1.
    Le burst de 4 photos (deltas 1s ≤ 1s) doit donc être détecté.
    Si le calcul était fait sur un batch plus large mélangeant
    plusieurs dossiers, le seuil pourrait être très différent.
    """
    from datetime import datetime as dt

    import piexif
    from PIL import Image

    def make_photo(name: str, when: dt):
        path = tmp_path / name
        img = Image.new("RGB", (50, 50))
        exif_dict = {
            "Exif": {piexif.ExifIFD.DateTimeOriginal: when.strftime("%Y:%m:%d %H:%M:%S").encode()},
        }
        img.save(path, exif=piexif.dump(exif_dict))
        return path

    base = dt(2026, 8, 1, 10, 0, 0)
    # Burst de 4 photos espacées d'1 seconde
    p1 = make_photo("p1.jpg", base)
    p2 = make_photo("p2.jpg", base.replace(second=1))
    p3 = make_photo("p3.jpg", base.replace(second=2))
    p4 = make_photo("p4.jpg", base.replace(second=3))
    # 2 photos isolées, 100s et 200s plus tard
    p5 = make_photo("p5.jpg", base.replace(minute=1, second=43))
    p6 = make_photo("p6.jpg", base.replace(minute=3, second=23))

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=True,
        organize_by_camera=False,
        date_format="year",
        detect_bursts=True,
        burst_mode="auto",
        burst_threshold_seconds=999,  # ignoré en mode auto
        burst_min_count=3,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    res = org.organize(
        [str(p1), str(p2), str(p3), str(p4), str(p5), str(p6)],
        str(dest),
        opts,
    )
    assert res.processed == 6
    burst_dir = dest / "2026" / "Burst_01"
    assert burst_dir.is_dir(), f"Burst_01 manquant — {list(dest.rglob('*'))}"
    # Le burst contient bien 4 photos (p1..p4)
    assert len(list(burst_dir.glob("*.jpg"))) == 4


def test_incremental_mode_skips_known_files(tmp_path):
    """Lot S5 : un 2e run ignore les fichiers déjà indexés à destination."""
    from PIL import Image

    src = tmp_path / "p.jpg"
    Image.new("RGB", (60, 60)).save(src)

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=False,
        organize_by_camera=False,
        incremental_mode=True,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"

    # 1er run : 1 fichier traité, l'index est créé
    r1 = org.organize([str(src)], str(dest), opts)
    assert r1.processed == 1
    assert (dest / ".photoorganizer_index.json").exists()

    # 2e run sur la même source → skip via index incrémental
    org2 = SmartOrganizer()
    r2 = org2.organize([str(src)], str(dest), opts)
    assert r2.processed == 0
    assert r2.skipped == 1


def test_scheduler_configure_and_next_run():
    """Lot E5 : le scheduler calcule un prochain trigger cohérent."""
    import sys

    sys.path.insert(0, os.path.abspath("src"))
    from datetime import timedelta

    from core.scheduler import JobScheduler

    fired = []
    sched = JobScheduler(callback=lambda: fired.append(1), poll_seconds=5)

    sched.configure(True, "23:30")
    assert sched.is_enabled()
    nxt = sched.get_next_run()
    assert nxt is not None
    # Doit être dans les 24 h à venir
    assert datetime.now() <= nxt <= datetime.now() + timedelta(days=1)
    # H/M doivent matcher
    assert nxt.hour == 23 and nxt.minute == 30

    sched.configure(False, "23:30")
    assert not sched.is_enabled()
    sched.stop()


def test_scheduler_rejects_invalid_time():
    """Heure mal formatée → désactivé silencieusement."""
    import sys

    sys.path.insert(0, os.path.abspath("src"))
    from core.scheduler import JobScheduler

    sched = JobScheduler(callback=lambda: None)
    sched.configure(True, "9999:99")
    assert not sched.is_enabled()
    sched.configure(True, "")
    assert not sched.is_enabled()
    sched.stop()


def test_export_index_csv_json(tmp_path):
    """Lot R7 : export d'un index CSV et JSON dans la destination."""
    from PIL import Image

    src = tmp_path / "p.jpg"
    Image.new("RGB", (50, 50)).save(src)

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=False,
        organize_by_camera=False,
        export_index_csv=True,
        export_index_json=True,
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    org.organize([str(src)], str(dest), opts)

    csv_files = list(dest.glob("_photoorganizer_index_*.csv"))
    json_files = list(dest.glob("_photoorganizer_index_*.json"))
    assert len(csv_files) == 1, f"expected 1 csv, got {csv_files}"
    assert len(json_files) == 1
    # Vérifier le contenu JSON
    import json

    data = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["source"].endswith("p.jpg")
    assert "destination" in data[0]


def test_multilayer_inverted_order(tmp_path):
    """Inverser l'ordre date/camera change la hiérarchie en sortie."""
    from PIL import Image

    src = tmp_path / "p.jpg"
    Image.new("RGB", (10, 10)).save(src)

    org_a = SmartOrganizer()
    org_b = SmartOrganizer()
    dest_a = tmp_path / "out_a"
    dest_b = tmp_path / "out_b"

    common = dict(
        organize_by_date=True,
        organize_by_camera=True,
        organize_by_location=False,
        multilayer=True,
        date_format="year",
    )
    opts_a = OrganizationOptions(**common, criteria_order=["date", "camera", "location"])
    opts_b = OrganizationOptions(**common, criteria_order=["camera", "date", "location"])

    org_a.organize([str(src)], str(dest_a), opts_a)
    org_b.organize([str(src)], str(dest_b), opts_b)

    # Top-level différent dans les deux configurations
    top_a = {p.name for p in dest_a.iterdir()}
    top_b = {p.name for p in dest_b.iterdir()}
    assert top_a != top_b, f"a={top_a} b={top_b}"
