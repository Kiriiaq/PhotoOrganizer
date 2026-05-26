"""Tests fonctionnels du batch CLI Pro.

On teste :
  - le parsing argparse + dispatch des sous-commandes ;
  - le rejet quand la licence est absente (code 2) ;
  - le comportement dry-run (n'écrit rien, retourne 0) ;
  - la sous-commande ``info`` sans licence ;
  - la sous-commande ``dedup`` sur un mini-fixture.

On ne teste PAS le vrai ``organize`` (déjà couvert par
``tests/functional/test_organizer.py``).
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

# -----------------------------------------------------------------------
# DEFERRED v3.0+ — pivot économique 2026-05-26
# Le module testé est gelé : entry point CLI commenté dans pyproject.toml,
# pas d'usage dans l'app v2.x. On garde le fichier intact pour réactivation
# conditionnelle. Cf. AUDIT.md §15 et docs/MONETIZATION.md §8.
# -----------------------------------------------------------------------
pytestmark = pytest.mark.skip(reason="Deferred to v3.0+ (see AUDIT.md §15)")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.photoorganizer_pro.cli import batch_organize  # noqa: E402
from src.photoorganizer_pro.license import EDITION_PERSONAL  # noqa: E402
from src.photoorganizer_pro.license.keygen import generate_key  # noqa: E402
from src.photoorganizer_pro.license.validator import (  # noqa: E402
    _license_storage_path,
    save_license_key,
)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------
@pytest.fixture
def clean_license():
    """Garantit aucune licence avant le test, restaure après."""
    p = _license_storage_path()
    backup = p.read_text(encoding="ascii") if p.exists() else None
    if p.exists():
        p.unlink()
    yield
    if p.exists():
        p.unlink()
    if backup:
        p.write_text(backup, encoding="ascii")


@pytest.fixture
def with_valid_license(clean_license):
    future = date.today() + timedelta(days=365)
    key = generate_key("test@example.com", EDITION_PERSONAL, future)
    save_license_key(key)
    yield


@pytest.fixture
def mini_photos(tmp_path: Path) -> Path:
    """Crée 3 fichiers JPEG minuscules (entêtes JPEG suffisent pour list_files)."""
    src = tmp_path / "src"
    src.mkdir()
    jpeg_magic = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    for i in range(3):
        (src / f"img_{i}.jpg").write_bytes(jpeg_magic + b"\x00" * 100)
    return src


# ---------------------------------------------------------------------
# Parsing / help
# ---------------------------------------------------------------------
class TestArgparse:
    def test_no_command_errors(self, capsys):
        with pytest.raises(SystemExit):
            batch_organize.main([])

    def test_help_does_not_crash(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            batch_organize.main(["--help"])
        # --help sort en code 0
        assert excinfo.value.code == 0

    def test_unknown_command_errors(self, capsys):
        with pytest.raises(SystemExit):
            batch_organize.main(["nonexistent-cmd"])


# ---------------------------------------------------------------------
# info — ne nécessite PAS de licence
# ---------------------------------------------------------------------
class TestInfoCommand:
    def test_info_without_license(self, clean_license, capsys):
        code = batch_organize.main(["info"])
        captured = capsys.readouterr()
        assert code == 2
        assert "Aucune licence Pro active" in captured.out

    def test_info_with_valid_license(self, with_valid_license, capsys):
        code = batch_organize.main(["info"])
        captured = capsys.readouterr()
        assert code == 0
        assert "active" in captured.out.lower()
        assert "test@example.com" in captured.out


# ---------------------------------------------------------------------
# Rejet sans licence
# ---------------------------------------------------------------------
class TestLicenseGate:
    def test_organize_without_license_exits_2(self, clean_license, mini_photos, tmp_path, capsys):
        dest = tmp_path / "dest"
        with pytest.raises(SystemExit) as excinfo:
            batch_organize.main([
                "organize",
                "--source", str(mini_photos),
                "--dest", str(dest),
                "--create-dest",
                "--dry-run",
            ])
        assert excinfo.value.code == 2
        err = capsys.readouterr().err
        assert "licence" in err.lower()

    def test_dedup_without_license_exits_2(self, clean_license, mini_photos):
        with pytest.raises(SystemExit) as excinfo:
            batch_organize.main([
                "dedup",
                "--source", str(mini_photos),
            ])
        assert excinfo.value.code == 2


# ---------------------------------------------------------------------
# organize --dry-run
# ---------------------------------------------------------------------
class TestOrganizeDryRun:
    def test_dry_run_with_valid_license(self, with_valid_license, mini_photos, tmp_path, capsys):
        dest = tmp_path / "dest"
        code = batch_organize.main([
            "organize",
            "--source", str(mini_photos),
            "--dest", str(dest),
            "--create-dest",
            "--dry-run",
        ])
        captured = capsys.readouterr().out
        assert code == 0
        assert "DRY-RUN" in captured
        assert "Aucun fichier ne sera modifié" in captured
        # Le dossier dest a été créé (--create-dest) mais reste vide.
        assert dest.exists()
        assert list(dest.iterdir()) == []

    def test_dry_run_missing_source_returns_1(self, with_valid_license, tmp_path, capsys):
        nonexistent = tmp_path / "does-not-exist"
        dest = tmp_path / "dest"
        with pytest.raises(SystemExit) as excinfo:
            batch_organize.main([
                "organize",
                "--source", str(nonexistent),
                "--dest", str(dest),
                "--create-dest",
                "--dry-run",
            ])
        assert excinfo.value.code == 1


# ---------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------
class TestDedupCommand:
    def test_dedup_runs_on_unique_files(self, with_valid_license, mini_photos, capsys):
        """3 fichiers différents → 0 doublon, code 0."""
        code = batch_organize.main([
            "dedup",
            "--source", str(mini_photos),
        ])
        captured = capsys.readouterr().out
        assert code == 0
        assert "Total fichiers" in captured
        assert "Doublons" in captured
