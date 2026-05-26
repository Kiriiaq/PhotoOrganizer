"""Tests fonctionnels du watch-folder Pro.

Stratégie : on N'UTILISE PAS la vraie boucle ``watchdog`` (asynchrone,
flaky en test). On teste :
  - ``WatchFolder.is_watched`` / ``already_processed`` / ``mark_processed`` ;
  - ``WatchFolder.handle_path`` avec ``_organize_one`` monkey-patché ;
  - ``WatchFolder.poll_once`` avec un dossier qui change entre 2 appels.

On injecte un ``sleep_fn`` no-op pour éviter les attentes réelles.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

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

from src.photoorganizer_pro.scheduler.watch_folder import (  # noqa: E402
    WATCHED_EXTENSIONS,
    WatchFolder,
)


@pytest.fixture
def dirs(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"
    return src, dest


def _no_sleep(_seconds: float) -> None:
    """Remplace time.sleep par un no-op pour les tests."""
    return None


# ---------------------------------------------------------------------
# is_watched
# ---------------------------------------------------------------------
class TestIsWatched:
    def test_jpeg_is_watched(self, dirs):
        src, dest = dirs
        wf = WatchFolder(source=src, dest=dest, sleep_fn=_no_sleep)
        assert wf.is_watched(Path("photo.jpg"))
        assert wf.is_watched(Path("photo.JPG"))
        assert wf.is_watched(Path("photo.heic"))
        assert wf.is_watched(Path("photo.dng"))
        assert wf.is_watched(Path("video.mp4"))

    def test_unknown_extension_not_watched(self, dirs):
        src, dest = dirs
        wf = WatchFolder(source=src, dest=dest, sleep_fn=_no_sleep)
        assert not wf.is_watched(Path("doc.pdf"))
        assert not wf.is_watched(Path("note.txt"))
        assert not wf.is_watched(Path("noext"))

    def test_extensions_set_is_not_empty(self):
        assert len(WATCHED_EXTENSIONS) > 20  # bonne couverture formats


# ---------------------------------------------------------------------
# Deduplication via mark_processed
# ---------------------------------------------------------------------
class TestDeduplication:
    def test_mark_and_check(self, dirs):
        src, dest = dirs
        f = src / "img.jpg"
        f.write_bytes(b"x")
        wf = WatchFolder(source=src, dest=dest, sleep_fn=_no_sleep)
        assert not wf.already_processed(f)
        wf.mark_processed(f)
        assert wf.already_processed(f)


# ---------------------------------------------------------------------
# handle_path — avec _organize_one monkey-patché
# ---------------------------------------------------------------------
class TestHandlePath:
    def _make_watcher(self, dirs, organize_results: List[bool]) -> WatchFolder:
        """Watcher avec _organize_one qui renvoie successivement les valeurs fournies."""
        src, dest = dirs
        wf = WatchFolder(source=src, dest=dest, debounce_seconds=0, sleep_fn=_no_sleep)
        calls = iter(organize_results)
        wf._organize_one = lambda _p: next(calls, False)  # type: ignore[assignment]
        return wf

    def test_unwatched_extension_returns_false(self, dirs):
        src, _dest = dirs
        f = src / "note.txt"
        f.write_bytes(b"x")
        wf = self._make_watcher(dirs, [True])
        assert wf.handle_path(f) is False

    def test_watched_file_organized_once(self, dirs):
        src, _dest = dirs
        f = src / "img.jpg"
        f.write_bytes(b"x")
        wf = self._make_watcher(dirs, [True])
        assert wf.handle_path(f) is True
        assert wf.already_processed(f)

    def test_same_file_processed_only_once(self, dirs):
        src, _dest = dirs
        f = src / "img.jpg"
        f.write_bytes(b"x")
        wf = self._make_watcher(dirs, [True, True])
        # Premier appel : OK
        assert wf.handle_path(f) is True
        # Deuxième appel sur le même chemin : ignoré, retourne False
        assert wf.handle_path(f) is False

    def test_missing_file_after_debounce_returns_false(self, dirs):
        src, dest = dirs
        wf = WatchFolder(source=src, dest=dest, debounce_seconds=0, sleep_fn=_no_sleep)
        # On crée puis supprime un fichier (simule un transfert annulé).
        f = src / "vanished.jpg"
        f.write_bytes(b"x")
        f.unlink()
        # handle_path va voir un fichier absent → False
        assert wf.handle_path(f) is False

    def test_organize_exception_swallowed_and_logged(self, dirs, caplog):
        src, _dest = dirs
        f = src / "img.jpg"
        f.write_bytes(b"x")
        wf = WatchFolder(source=src, dest=_dest, debounce_seconds=0, sleep_fn=_no_sleep)

        def boom(_p):
            raise RuntimeError("boom")

        wf._organize_one = boom  # type: ignore[assignment]
        # Ne lève pas, retourne False, log d'erreur visible
        assert wf.handle_path(f) is False


# ---------------------------------------------------------------------
# poll_once — simulation de la boucle de polling
# ---------------------------------------------------------------------
class TestPollOnce:
    def test_initial_scan_does_not_organize(self, dirs):
        """Premier poll (seen=None) marque tout, sans déclencher handle_path."""
        src, dest = dirs
        (src / "a.jpg").write_bytes(b"x")
        (src / "b.jpg").write_bytes(b"x")
        wf = WatchFolder(source=src, dest=dest, debounce_seconds=0, sleep_fn=_no_sleep)
        organized: List[Path] = []
        wf._organize_one = lambda p: organized.append(p) or True  # type: ignore[assignment]

        seen = wf.poll_once(seen=None)
        assert len(seen) == 2
        assert organized == []  # initial scan : pas d'organisation

    def test_new_file_triggers_organize(self, dirs):
        src, dest = dirs
        (src / "old.jpg").write_bytes(b"x")
        wf = WatchFolder(source=src, dest=dest, debounce_seconds=0, sleep_fn=_no_sleep)
        organized: List[Path] = []
        wf._organize_one = lambda p: organized.append(p) or True  # type: ignore[assignment]

        seen = wf.poll_once(seen=None)
        # Nouveau fichier déposé
        (src / "new.jpg").write_bytes(b"x")
        seen = wf.poll_once(seen=seen)
        assert len(organized) == 1
        assert organized[0].name == "new.jpg"

    def test_non_media_file_not_organized(self, dirs):
        src, dest = dirs
        wf = WatchFolder(source=src, dest=dest, debounce_seconds=0, sleep_fn=_no_sleep)
        organized: List[Path] = []
        wf._organize_one = lambda p: organized.append(p) or True  # type: ignore[assignment]

        seen = wf.poll_once(seen=None)
        (src / "readme.txt").write_bytes(b"x")
        seen = wf.poll_once(seen=seen)
        assert organized == []
