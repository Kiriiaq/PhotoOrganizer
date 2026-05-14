"""Tests de stress : opérations répétées et concurrence."""
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from core.operations.file_manager import FileManager  # noqa: E402
from core.operations.organizer import OrganizationOptions, SmartOrganizer  # noqa: E402


@pytest.mark.slow
def test_repeated_copy_rollback_cycle(tmp_path):
    """1000 cycles copy+rollback ne doivent pas fuir / corrompre l'historique."""
    fm = FileManager()
    src = tmp_path / "src.jpg"
    src.write_bytes(b"X")
    dest = tmp_path / "out" / "x.jpg"

    for _ in range(1_000):
        fm.copy_file(str(src), str(dest))
        fm.rollback_last()

    assert fm.get_operations_history() == []
    assert not dest.exists()
    assert src.exists()


@pytest.mark.slow
def test_concurrent_list_files(tmp_path):
    """Plusieurs threads listent en parallèle — pas de corruption."""
    for i in range(200):
        (tmp_path / f"f_{i}.jpg").write_bytes(b"")
    fm = FileManager()
    results = [None] * 8
    errors = []

    def worker(idx):
        try:
            results[idx] = len(fm.list_files(str(tmp_path), recursive=False))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors
    assert all(r == 200 for r in results)


@pytest.mark.slow
def test_organizer_cancellable_under_stress(tmp_path):
    from PIL import Image
    paths = []
    for i in range(50):
        p = tmp_path / f"p_{i}.jpg"
        Image.new("RGB", (5, 5)).save(p)
        paths.append(str(p))

    org = SmartOrganizer()
    cancelled = {"called": False}

    def cb(current, total, message):
        if current >= 5 and not cancelled["called"]:
            cancelled["called"] = True
            org.cancel()

    res = org.organize(paths, str(tmp_path / "out"), OrganizationOptions(), cb)
    assert res.processed < 50
    assert cancelled["called"]
