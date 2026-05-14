"""Tests de volume : gros fichiers et grandes listes."""
import sys
import tracemalloc
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from core.operations.file_manager import FileManager  # noqa: E402


@pytest.mark.slow
def test_list_files_large_directory(tmp_path):
    """list_files doit traiter 10k entrées sans dégradation excessive."""
    # Créer 10k fichiers vides .jpg
    for i in range(10_000):
        (tmp_path / f"f_{i:05d}.jpg").write_bytes(b"")
    fm = FileManager()
    files = fm.list_files(str(tmp_path), recursive=False)
    assert len(files) == 10_000


@pytest.mark.slow
def test_no_memory_leak_repeated_scan(tmp_path):
    """Plusieurs scans ne doivent pas faire exploser la mémoire."""
    for i in range(500):
        (tmp_path / f"f_{i:04d}.jpg").write_bytes(b"")
    fm = FileManager()

    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    for _ in range(20):
        _ = fm.list_files(str(tmp_path), recursive=False)

    snapshot2 = tracemalloc.take_snapshot()
    diff = snapshot2.compare_to(snapshot1, "lineno")
    total_growth = sum(stat.size_diff for stat in diff)
    tracemalloc.stop()

    # On accepte jusqu'à 2 Mo de croissance résiduelle
    assert total_growth < 2 * 1024 * 1024, f"Memory growth: {total_growth}"


@pytest.mark.slow
def test_copy_large_file(tmp_path):
    """Copier un fichier 10 Mo doit fonctionner sans problème."""
    src = tmp_path / "big.jpg"
    src.write_bytes(b"X" * (10 * 1024 * 1024))
    dest = tmp_path / "out" / "big.jpg"
    fm = FileManager()
    op = fm.copy_file(str(src), str(dest))
    assert op.success
    assert dest.stat().st_size == 10 * 1024 * 1024
