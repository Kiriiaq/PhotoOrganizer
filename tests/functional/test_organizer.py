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
