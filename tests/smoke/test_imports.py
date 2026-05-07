"""Smoke tests : tout le projet doit s'importer sans erreur."""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

MODULES = [
    "core.metadata.exif_extractor",
    "core.metadata.gps_processor",
    "core.metadata.date_extractor",
    "core.metadata.camera_detector",
    "core.operations.file_manager",
    "core.operations.organizer",
    "core.operations.duplicate_finder",
    "core.operations.duplicate_manager",
    "utils.cache",
    "utils.config",
    "utils.logger",
    "utils.hash_cache",
    "src.config.duplicate_config",
    "src.reports.duplicate_reporter",
]


def test_all_modules_importable():
    """Tous les modules de logique doivent s'importer sans crash."""
    for module_name in MODULES:
        importlib.import_module(module_name)


def test_app_class_importable():
    """La classe principale doit être importable même sans instancier Tk."""
    from ui.app import PhotoOrganizerApp
    # On vérifie juste les attributs de classe — pas d'instanciation
    assert PhotoOrganizerApp.APP_NAME == "PhotoOrganizer"
    assert PhotoOrganizerApp.APP_VERSION
    assert "📁 Organisation" in PhotoOrganizerApp.TAB_NAMES


def test_main_module_callable():
    """Le point d'entrée doit être importable et exposer `main`."""
    import src.main as m
    assert callable(m.main)
    assert callable(m.check_dependencies)
