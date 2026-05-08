"""Pytest configuration and fixtures for PhotoOrganizer."""
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

# Ajout des chemins src/ comme le fait main.py — assure que les tests qui
# importent `core.*` ou `utils.*` fonctionnent peu importe l'ordre de collection.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def pytest_configure(config):
    """Marqueurs personnalisés."""
    config.addinivalue_line("markers", "slow: tests longs (volume / stress)")


@pytest.fixture
def temp_dir():
    """Crée un dossier temporaire pour les tests."""
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_photos(temp_dir):
    """Crée 5 photos JPEG factices."""
    from PIL import Image

    photos = []
    for i in range(5):
        photo_path = temp_dir / f"photo_{i}.jpg"
        Image.new("RGB", (200, 150), color=(i * 40, 100, 200 - i * 30)).save(str(photo_path))
        photos.append(photo_path)
    return photos


@pytest.fixture
def source_folder(temp_dir, sample_photos):
    """Dossier source pré-rempli de photos pour les tests d'organisation."""
    source = temp_dir / "source"
    source.mkdir()
    for photo in sample_photos:
        shutil.copy(photo, source / photo.name)
    return source


# ---------------------------------------------------------------------------
# Fixture partagée pour tous les tests UI smoke (test_ui_v3, test_ux_v4, …).
#
# Une seule instance Tk est créée pour toute la session pytest. Recréer
# un second Tk dans le même processus déclenche une TclError sur Python
# 3.11+ ("invalid command name tcl_findLibrary"), donc tous les modules
# UI doivent réutiliser cette fixture au lieu d'instancier leur propre Tk.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def app():
    """Instance unique de PhotoOrganizerApp partagée pour les tests UI."""
    try:
        from ui.app import PhotoOrganizerApp
        a = PhotoOrganizerApp()
    except Exception as exc:
        pytest.skip(f"Pas d'environnement graphique : {exc}")
    a.geometry("1400x900")
    for _ in range(3):
        a.update_idletasks()
        a.update()
    yield a
    try:
        a.destroy()
    except Exception:
        pass
