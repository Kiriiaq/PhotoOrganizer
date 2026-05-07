"""Tests de performance via pytest-benchmark."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from core.operations.file_manager import FileManager  # noqa: E402


@pytest.fixture
def listing_tree(tmp_path):
    for i in range(1_000):
        (tmp_path / f"f_{i:04d}.jpg").write_bytes(b"")
    return tmp_path


def test_bench_list_files_1k(benchmark, listing_tree):
    """Liste 1 000 fichiers — < 200 ms attendu."""
    fm = FileManager()
    result = benchmark(fm.list_files, str(listing_tree), recursive=False)
    assert len(result) == 1_000


def test_bench_get_unique_name(benchmark, tmp_path):
    """Génération de noms uniques — < 1 ms en cas idéal."""
    target = tmp_path / "x.jpg"
    target.write_bytes(b"")
    fm = FileManager()
    result = benchmark(fm._get_unique_name, str(target))
    assert result.endswith(".jpg") and result != str(target)
