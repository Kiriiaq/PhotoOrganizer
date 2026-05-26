"""Tests fonctionnels du FileManager : copy/move/rollback."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from core.operations.file_manager import FileManager  # noqa: E402


@pytest.fixture
def fm():
    return FileManager()


@pytest.fixture
def src_file(tmp_path):
    p = tmp_path / "src.jpg"
    p.write_bytes(b"PHOTO_BYTES")
    return p


def test_copy_creates_destination(fm, src_file, tmp_path):
    dest = tmp_path / "dest" / "src.jpg"
    op = fm.copy_file(str(src_file), str(dest))
    assert op.success
    assert dest.exists()
    assert dest.read_bytes() == b"PHOTO_BYTES"


def test_copy_auto_rename_on_conflict(fm, src_file, tmp_path):
    dest = tmp_path / "dest.jpg"
    dest.write_bytes(b"OTHER")
    op = fm.copy_file(str(src_file), str(dest), auto_rename=True)
    assert op.success
    assert op.destination != str(dest)  # un nouveau nom est généré
    assert Path(op.destination).read_bytes() == b"PHOTO_BYTES"
    assert dest.read_bytes() == b"OTHER"  # original préservé


def test_move_then_rollback_restores_source(fm, src_file, tmp_path):
    dest = tmp_path / "subdir" / "src.jpg"
    op = fm.move_file(str(src_file), str(dest))
    assert op.success
    assert dest.exists() and not src_file.exists()

    assert fm.rollback_last() is True
    assert src_file.exists() and not dest.exists()


def test_rollback_all_returns_dict(fm, tmp_path):
    """rollback_all renvoie maintenant un dict, total = success+failed+skipped."""
    a = tmp_path / "a.jpg"
    a.write_bytes(b"A")
    b = tmp_path / "b.jpg"
    b.write_bytes(b"B")
    fm.copy_file(str(a), str(tmp_path / "dst" / "a.jpg"))
    fm.copy_file(str(b), str(tmp_path / "dst" / "b.jpg"))
    res = fm.rollback_all()
    assert isinstance(res, dict)
    assert set(res.keys()) == {"success", "failed", "skipped", "total"}
    assert res["total"] == 2
    assert res["success"] + res["failed"] + res["skipped"] == res["total"]
    assert res["success"] == 2


def test_clear_history_does_not_undo(fm, src_file, tmp_path):
    dest = tmp_path / "dest.jpg"
    fm.copy_file(str(src_file), str(dest))
    assert dest.exists()
    fm.clear_history()
    assert dest.exists()  # le fichier reste
    assert fm.get_operations_history() == []


def test_list_files_excludes_videos_by_default(fm, tmp_path):
    (tmp_path / "p.jpg").write_bytes(b"")
    (tmp_path / "v.mp4").write_bytes(b"")
    files = fm.list_files(str(tmp_path))
    assert any(f.endswith(".jpg") for f in files)
    assert not any(f.endswith(".mp4") for f in files)


def test_list_files_recursive(fm, tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.jpg").write_bytes(b"")
    (sub / "deep.jpg").write_bytes(b"")
    files = fm.list_files(str(tmp_path), recursive=True)
    assert len(files) == 2
    files_flat = fm.list_files(str(tmp_path), recursive=False)
    assert len(files_flat) == 1


def test_rollback_last_skips_failed_ops(fm, tmp_path):
    """Une opération en erreur initiale est ignorée par rollback_last."""
    bad = tmp_path / "missing.jpg"
    op = fm.copy_file(str(bad), str(tmp_path / "out.jpg"))
    assert not op.success  # source absente
    # rollback_last doit retourner False car aucune op réussie
    assert fm.rollback_last() is False
