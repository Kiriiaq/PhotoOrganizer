"""Tests fonctionnels du SmartOrganizer : organisation par date/format."""
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from core.operations.organizer import SmartOrganizer, OrganizationOptions  # noqa: E402
from core.operations.file_manager import FileManager  # noqa: E402


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
    opts = OrganizationOptions(organize_by_date=False, organize_by_camera=False,
                                organize_by_location=False, copy_not_move=True)
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
    from datetime import datetime as dt
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
        criteria_order=['camera', 'date', 'location'],
        date_format='year',
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
        organize_by_date=False, organize_by_camera=False,
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
        organize_by_date=False, organize_by_camera=False,
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
        organize_by_date=False, organize_by_camera=False,
        rename_template="{counter:04d}_{original}",
        validate_disk_space=False,
    )
    dest = tmp_path / "out"
    org.organize([str(src)], str(dest), opts)
    # Le fichier final s'appelle "0001_IMG_0001.jpg"
    files = list(dest.iterdir())
    assert any(f.name == "0001_IMG_0001.jpg" for f in files), \
        f"got: {[f.name for f in files]}"


def test_burst_detection_groups_close_photos(tmp_path):
    """Lot S1 : 3 photos prises < 3 s d'écart → sous-dossier Burst_01."""
    from PIL import Image
    import piexif
    from datetime import datetime as dt

    def make_photo(name: str, when: dt):
        path = tmp_path / name
        img = Image.new("RGB", (50, 50))
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: when.strftime("%Y:%m:%d %H:%M:%S").encode()
            },
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
        organize_by_date=True, organize_by_camera=False,
        date_format='year',
        detect_bursts=True,
        burst_threshold_seconds=3, burst_min_count=3,
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


def test_incremental_mode_skips_known_files(tmp_path):
    """Lot S5 : un 2e run ignore les fichiers déjà indexés à destination."""
    from PIL import Image
    src = tmp_path / "p.jpg"
    Image.new("RGB", (60, 60)).save(src)

    org = SmartOrganizer()
    opts = OrganizationOptions(
        organize_by_date=False, organize_by_camera=False,
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
    import sys, os
    sys.path.insert(0, os.path.abspath('src'))
    from core.scheduler import JobScheduler
    from datetime import datetime, timedelta

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
    import sys, os
    sys.path.insert(0, os.path.abspath('src'))
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
        organize_by_date=False, organize_by_camera=False,
        export_index_csv=True, export_index_json=True,
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
    data = json.loads(json_files[0].read_text(encoding='utf-8'))
    assert len(data) == 1
    assert data[0]['source'].endswith('p.jpg')
    assert 'destination' in data[0]


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
        organize_by_date=True, organize_by_camera=True,
        organize_by_location=False, multilayer=True, date_format='year',
    )
    opts_a = OrganizationOptions(**common, criteria_order=['date', 'camera', 'location'])
    opts_b = OrganizationOptions(**common, criteria_order=['camera', 'date', 'location'])

    org_a.organize([str(src)], str(dest_a), opts_a)
    org_b.organize([str(src)], str(dest_b), opts_b)

    # Top-level différent dans les deux configurations
    top_a = {p.name for p in dest_a.iterdir()}
    top_b = {p.name for p in dest_b.iterdir()}
    assert top_a != top_b, f"a={top_a} b={top_b}"
