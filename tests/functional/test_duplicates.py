"""Tests fonctionnels du DuplicateManager : détection + exclusion corbeille."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.config.duplicate_config import DuplicateManagerConfig, ExecutionMode  # noqa: E402
from src.core.operations.duplicate_manager import DuplicateManager  # noqa: E402


@pytest.fixture
def cfg():
    c = DuplicateManagerConfig()
    c.execution_mode = ExecutionMode.DRY_RUN
    return c


def test_is_system_folder_recyclebin(cfg):
    mgr = DuplicateManager(cfg)
    # Composant final : sensitive case
    assert mgr._is_system_folder(r"C:\$RECYCLE.BIN")
    assert mgr._is_system_folder(r"C:\$Recycle.Bin\S-1-5-21-12345")
    assert mgr._is_system_folder(r"D:\Photos\System Volume Information\foo")


def test_is_system_folder_macos_linux(cfg):
    mgr = DuplicateManager(cfg)
    assert mgr._is_system_folder("/home/user/.Trash")
    assert mgr._is_system_folder("/home/user/.Trash-1000/files")
    assert mgr._is_system_folder("/Volumes/photo/.Trashes/501")


def test_normal_folder_not_system(cfg):
    mgr = DuplicateManager(cfg)
    assert not mgr._is_system_folder(r"C:\Users\me\Photos\2024")
    assert not mgr._is_system_folder("/home/me/photos/sub")


def test_should_include_folder_excludes_system(cfg):
    mgr = DuplicateManager(cfg)
    assert not mgr._should_include_folder(r"C:\$Recycle.Bin")
    assert mgr._should_include_folder(r"C:\Users\me\Photos")


def test_should_include_file_excludes_system_path(cfg, tmp_path):
    # Crée un fichier dans un faux $Recycle.Bin
    bad = tmp_path / "$Recycle.Bin" / "victim.jpg"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"x")
    mgr = DuplicateManager(cfg)
    cfg.extensions.include = [".jpg"]
    assert not mgr._should_include_file(str(bad))


def test_file_manager_injection(cfg):
    """Lot D (audit 2026-06-11) : le FileManager partagé est injectable.

    Avant, _execute_action historisait dans un singleton module-level que
    l'UI n'affichait jamais — les opérations doublons étaient invisibles
    dans l'onglet Historique. L'UI injecte désormais son FileManager ;
    par défaut (CLI/tests), chaque manager a une instance privée.
    """
    from src.core.operations.file_manager import FileManager

    shared = FileManager()
    mgr = DuplicateManager(cfg, file_manager=shared)
    assert mgr.file_manager is shared

    mgr_a = DuplicateManager(cfg)
    mgr_b = DuplicateManager(cfg)
    assert mgr_a.file_manager is not mgr_b.file_manager  # pas de singleton caché


def test_collect_files_skips_recyclebin(cfg, tmp_path):
    """End-to-end : un re-scan ne renvoie pas les fichiers de la corbeille."""
    photo = tmp_path / "real.jpg"
    photo.write_bytes(b"REAL")
    deleted = tmp_path / "$Recycle.Bin" / "old.jpg"
    deleted.parent.mkdir(parents=True)
    deleted.write_bytes(b"REAL")  # même contenu

    cfg.source_directories = [str(tmp_path)]
    cfg.extensions.include = [".jpg"]
    cfg.recursive = True

    mgr = DuplicateManager(cfg)
    files = mgr._collect_files(progress_callback=None)
    # Seul le fichier "real.jpg" doit remonter
    assert any("real.jpg" in f for f in files)
    assert not any("Recycle.Bin" in f for f in files)
