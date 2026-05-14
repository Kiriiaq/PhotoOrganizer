"""Tests unitaires de base pour les modules de PhotoOrganizer.

Les anciens tests référençaient des modules inexistants
(`src.core.scanner.PhotoScanner`, `src.core.organizer.Organizer`,
`src.core.metadata.MetadataExtractor`). Ils ont été remplacés par
des smoke tests qui exercent l'API réellement publiée par le projet.
"""
import sys
from pathlib import Path

# Permettre les imports depuis src/ comme fait main.py
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


class TestFileManager:
    """Tests pour le FileManager."""

    def test_filemanager_init(self):
        from core.operations.file_manager import FileManager
        fm = FileManager()
        assert fm.rollback_enabled is True
        assert fm.get_operations_history() == []

    def test_extensions_constant(self):
        from core.operations.file_manager import FileManager
        assert ".jpg" in FileManager.EXTENSIONS["image"]
        assert ".cr2" in FileManager.EXTENSIONS["raw"]
        assert ".mp4" in FileManager.EXTENSIONS["video"]

    def test_list_files_filters_extensions(self, source_folder):
        from core.operations.file_manager import FileManager
        fm = FileManager()
        files = fm.list_files(str(source_folder), include_videos=False)
        assert all(f.lower().endswith((".jpg", ".jpeg")) for f in files)
        assert len(files) == 5


class TestSmartOrganizer:
    """Tests pour le SmartOrganizer."""

    def test_organizer_init(self):
        from core.operations.organizer import SmartOrganizer
        org = SmartOrganizer()
        assert org.file_manager is not None

    def test_organize_empty_list(self, tmp_path):
        from core.operations.organizer import OrganizationOptions, SmartOrganizer
        org = SmartOrganizer()
        result = org.organize([], str(tmp_path), OrganizationOptions())
        assert result.total == 0
        assert result.processed == 0
        assert result.errors == 0

    def test_options_dataclass_defaults(self):
        from core.operations.organizer import OrganizationOptions
        o = OrganizationOptions()
        assert o.organize_by_date is True
        assert o.copy_not_move is True
        assert o.date_format == "year/month/day"


class TestMetadataExtractors:
    """Tests pour les extracteurs de métadonnées (API fonction)."""

    def test_get_exif_data_callable(self, source_folder):
        from core.metadata import get_exif_data
        photo = next(source_folder.glob("*.jpg"))
        data = get_exif_data(str(photo))
        assert isinstance(data, dict)

    def test_camera_info_returns_tuple(self, source_folder):
        from core.metadata import get_camera_info, get_exif_data
        photo = next(source_folder.glob("*.jpg"))
        info = get_camera_info(get_exif_data(str(photo)), str(photo))
        assert isinstance(info, tuple) and len(info) == 2
