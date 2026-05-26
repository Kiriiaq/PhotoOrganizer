# -*- coding: utf-8 -*-
"""Tests fonctionnels de la quarantaine interne (refonte 2026-05-19).

Vérifie que :
  - QuarantineManager déplace bien le fichier dans le dossier session
  - Le manifest JSON est écrit à chaque opération
  - restore_entry restaure le fichier à sa source d'origine
  - empty_to_system_trash vide la quarantaine
  - FileManager.record_operation + rollback_last sur type 'trash' fonctionne
  - Intégration duplicate_manager → quarantine → file_manager
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Permet d'importer src/ sans installer le package
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.operations.file_manager import FileManager  # noqa: E402
from core.operations.quarantine import (  # noqa: E402
    QuarantineEntry,
    QuarantineManager,
    MANIFEST_FILENAME,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tmp_workspace(tmp_path):
    """Crée 3 fichiers source + un dossier racine pour la quarantaine."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    files = []
    for i in range(3):
        f = src_dir / f"photo{i}.jpg"
        f.write_bytes(f"JPGDATA-{i}".encode() * 200)
        files.append(f)
    qroot = tmp_path / "quarantine"
    return src_dir, files, qroot


# =============================================================================
# QuarantineManager — opérations de base
# =============================================================================

class TestQuarantineManagerBasic:

    def test_quarantine_file_moves_to_session_dir(self, tmp_workspace):
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="20260519")
        entry = qm.quarantine_file(str(files[0]), reason="duplicate")
        assert not files[0].exists()
        assert Path(entry.destination).exists()
        # Le fichier est dans <qroot>/<session_id>/
        assert Path(entry.destination).parent == qroot / "20260519"

    def test_manifest_is_written_after_each_op(self, tmp_workspace):
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="20260519")
        qm.quarantine_file(str(files[0]))
        manifest = qroot / "20260519" / MANIFEST_FILENAME
        assert manifest.exists()
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["session_id"] == "20260519"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["source"] == str(files[0])

    def test_quarantine_multiple_files(self, tmp_workspace):
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        for f in files:
            qm.quarantine_file(str(f))
        assert len(qm.list_entries()) == 3
        assert qm.total_size_bytes() > 0

    def test_quarantine_handles_name_collision(self, tmp_workspace, tmp_path):
        """Deux fichiers de même nom dans dossiers différents → préfixes uniques."""
        src_dir, files, qroot = tmp_workspace
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        f_collide = other_dir / "photo0.jpg"  # même nom que files[0]
        f_collide.write_bytes(b"DIFFERENT" * 100)
        qm = QuarantineManager(root=qroot, session_id="s1")
        e1 = qm.quarantine_file(str(files[0]))
        e2 = qm.quarantine_file(str(f_collide))
        # Les deux ont des destinations différentes (préfixes de hash)
        assert e1.destination != e2.destination
        assert Path(e1.destination).exists()
        assert Path(e2.destination).exists()

    def test_quarantine_raises_on_missing_source(self, tmp_path):
        qm = QuarantineManager(root=tmp_path / "qr", session_id="s1")
        with pytest.raises(FileNotFoundError):
            qm.quarantine_file(str(tmp_path / "ghost.jpg"))


# =============================================================================
# QuarantineManager — restauration
# =============================================================================

class TestQuarantineRestore:

    def test_restore_brings_file_back_to_source(self, tmp_workspace):
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        e = qm.quarantine_file(str(files[0]))
        assert not files[0].exists()
        ok = qm.restore_entry(e)
        assert ok is True
        assert files[0].exists()
        # L'entrée doit avoir disparu du manifest
        assert e not in qm.list_entries()

    def test_restore_recreates_missing_source_dir(self, tmp_workspace):
        """Si l'utilisateur a supprimé le dossier source entre temps,
        on doit le recréer avant de restaurer le fichier."""
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        e = qm.quarantine_file(str(files[0]))
        # Supprime le dossier source vide
        for f in files:
            if f.exists():
                f.unlink()
        src_dir.rmdir()
        assert not src_dir.exists()
        ok = qm.restore_entry(e)
        assert ok is True
        assert files[0].exists()

    def test_restore_renames_if_source_taken(self, tmp_workspace):
        """Si un fichier du même nom existe à la source, on suffixe '_restored'."""
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        e = qm.quarantine_file(str(files[0]))
        # Recrée un fichier au même nom à la source
        files[0].write_bytes(b"NEW_CONTENT")
        ok = qm.restore_entry(e)
        assert ok is True
        # Le restauré doit être suffixé
        restored = files[0].parent / f"{files[0].stem}_restored1{files[0].suffix}"
        assert restored.exists()
        assert files[0].exists()  # l'original récent n'est pas écrasé

    def test_restore_missing_quarantined_returns_false(self, tmp_workspace):
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        e = qm.quarantine_file(str(files[0]))
        Path(e.destination).unlink()  # quelqu'un a effacé le fichier en QT
        ok = qm.restore_entry(e)
        assert ok is False


# =============================================================================
# QuarantineManager — vidage vers corbeille système
# =============================================================================

class TestQuarantineEmpty:

    def test_empty_returns_counts(self, tmp_workspace):
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        for f in files:
            qm.quarantine_file(str(f))
        result = qm.empty_to_system_trash()
        total = result["trashed"] + result["deleted"]
        # send2trash peut être absent → on accepte les deux modes
        assert total + result["failed"] == result["total"] == 3
        # Plus aucune entrée
        assert qm.list_entries() == []

    def test_empty_on_empty_quarantine_returns_zeros(self, tmp_path):
        qm = QuarantineManager(root=tmp_path / "qr", session_id="s1")
        result = qm.empty_to_system_trash()
        assert result == {"trashed": 0, "deleted": 0, "failed": 0, "total": 0}


# =============================================================================
# Persistance — reload d'une session
# =============================================================================

class TestQuarantineLoadSession:

    def test_load_session_restores_entries(self, tmp_workspace):
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        for f in files[:2]:
            qm.quarantine_file(str(f))
        # Simule un redémarrage : on recharge depuis le manifest
        qm2 = QuarantineManager.load_session(qroot / "s1")
        assert len(qm2.list_entries()) == 2
        # Restauration depuis l'instance rechargée fonctionne
        ok = qm2.restore_entry(qm2.list_entries()[0])
        assert ok is True

    def test_load_session_raises_on_missing_manifest(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            QuarantineManager.load_session(tmp_path / "nonexistent")


# =============================================================================
# Intégration FileManager.record_operation + rollback type 'trash'
# =============================================================================

class TestFileManagerTrashRollback:

    def test_record_trash_appears_in_history(self, tmp_workspace):
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        e = qm.quarantine_file(str(files[0]))
        fm = FileManager(rollback_enabled=True)
        op = fm.record_operation(
            operation_type="trash",
            source=e.source, destination=e.destination,
            success=True,
        )
        assert op.operation_type == "trash"
        assert len(fm.get_operations_history()) == 1

    def test_rollback_last_trash_restores_file(self, tmp_workspace):
        """Le rollback d'un type 'trash' déplace destination → source.

        C'est exactement ce qui rend la quarantaine réversible : pour
        l'historique le fichier est passé de source à destination
        (la quarantaine), donc l'annulation fait le chemin inverse.
        """
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        e = qm.quarantine_file(str(files[0]))
        fm = FileManager(rollback_enabled=True)
        fm.record_operation(
            operation_type="trash",
            source=e.source, destination=e.destination,
            success=True,
        )
        ok = fm.rollback_last()
        assert ok is True
        assert files[0].exists()
        # L'entrée a disparu du historique (succès)
        assert len(fm.get_operations_history()) == 0

    def test_rollback_all_with_mixed_ops(self, tmp_workspace, tmp_path):
        """rollback_all sur trash + delete : trash récupéré, delete skipped."""
        src_dir, files, qroot = tmp_workspace
        qm = QuarantineManager(root=qroot, session_id="s1")
        fm = FileManager(rollback_enabled=True)

        # trash : récupérable
        e0 = qm.quarantine_file(str(files[0]))
        fm.record_operation(operation_type="trash",
                            source=e0.source, destination=e0.destination,
                            success=True)
        # delete : définitif
        files[1].unlink()  # supprime "pour de vrai"
        fm.record_operation(operation_type="delete",
                            source=str(files[1]), destination="",
                            success=True)

        result = fm.rollback_all()
        assert result["total"] == 2
        assert result["success"] == 1  # trash restauré
        assert result["skipped"] == 1  # delete intentionnellement ignoré
        assert result["failed"] == 0
        assert files[0].exists()
        assert not files[1].exists()

    def test_rollback_delete_returns_false_with_clear_error(self, tmp_path):
        """rollback d'une suppression définitive doit échouer proprement."""
        fm = FileManager(rollback_enabled=True)
        fm.record_operation(operation_type="delete",
                            source=str(tmp_path / "ghost.jpg"),
                            destination="", success=True)
        ok = fm.rollback_last()
        assert ok is False
        # L'opération est remise en pile avec un message clair
        hist = fm.get_operations_history()
        assert len(hist) == 1
        assert "irreversible" in (hist[0].error or "").lower()


# =============================================================================
# Intégration end-to-end : DuplicateManager.empty_quarantine
# =============================================================================

class TestDuplicateManagerQuarantine:

    def test_duplicate_manager_exposes_quarantine_api(self):
        """duplicate_manager expose les méthodes attendues par l'IHM."""
        from src.config.duplicate_config import DuplicateManagerConfig
        from src.core.operations.duplicate_manager import DuplicateManager
        cfg = DuplicateManagerConfig()
        dm = DuplicateManager(cfg)
        assert hasattr(dm, "quarantine")
        assert callable(dm.empty_quarantine)
        assert callable(dm.quarantine_size_bytes)
        assert callable(dm.quarantine_count)
        # Quarantaine vide par défaut
        assert dm.quarantine_count() == 0
        assert dm.quarantine_size_bytes() == 0
