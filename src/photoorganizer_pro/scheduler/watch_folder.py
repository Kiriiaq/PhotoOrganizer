"""Watch-folder — feature Pro.

Surveille un dossier et déclenche l'organisation automatique des
nouveaux fichiers vers une destination triée.

Dépendance optionnelle : ``watchdog`` (extras ``pro`` de pyproject.toml).
Sans watchdog, on retombe sur un polling simple (intervalle configurable).

Usage typique
-------------

::

    photo-organizer-pro-watch \\
        --source "D:/Camera Imports" \\
        --dest "D:/Photos/library" \\
        --by-date --by-camera \\
        --copy

    # Ctrl+C pour arrêter.

Sous Windows : peut être enregistré comme service via
`nssm <https://nssm.cc/>`_ pour tourner en arrière-plan au démarrage.

Le délai par défaut entre la détection et l'organisation est de
**5 secondes** : laisse le temps à un transfert depuis SD card de se
terminer avant de tenter d'organiser un fichier encore en écriture.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Extensions surveillées (alignées avec core/operations/file_manager.py)
WATCHED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".jfif", ".jp2", ".heic", ".heif",
    ".raw", ".arw", ".cr2", ".cr3", ".nef", ".orf", ".rw2", ".dng",
    ".mp4", ".mov", ".avi", ".mkv",
}

DEFAULT_DEBOUNCE_SECONDS = 5


class WatchFolder:
    """Surveille un dossier source et organise les nouveaux fichiers."""

    def __init__(
        self,
        source: Path,
        dest: Path,
        *,
        by_date: bool = True,
        by_camera: bool = False,
        by_gps: bool = False,
        date_format: str = "year/month",
        copy: bool = True,
        debounce_seconds: int = DEFAULT_DEBOUNCE_SECONDS,
    ):
        self.source = source
        self.dest = dest
        self.by_date = by_date
        self.by_camera = by_camera
        self.by_gps = by_gps
        self.date_format = date_format
        self.copy = copy
        self.debounce_seconds = debounce_seconds
        self._processed: set[str] = set()

    def _organize_one(self, file_path: Path) -> bool:
        """Organise un seul fichier. Retourne True si réussi."""
        # Import différé pour rester léger au démarrage.
        from src.core.operations import FileManager, OrganizationOptions, SmartOrganizer

        fm = FileManager()
        opts = OrganizationOptions(
            organize_by_date=self.by_date,
            organize_by_camera=self.by_camera,
            organize_by_location=self.by_gps,
            date_format=self.date_format,
            copy_instead_of_move=self.copy,
        )
        organizer = SmartOrganizer(file_manager=fm)
        result = organizer.organize(
            files=[str(file_path)],
            source_dir=str(self.source),
            dest_dir=str(self.dest),
            options=opts,
        )
        return result.success == 1

    def _handle_new_file(self, file_path: Path) -> None:
        if file_path.suffix.lower() not in WATCHED_EXTENSIONS:
            return
        # Anti-doublon : ne pas retraiter le même chemin (peut arriver
        # avec certains FS qui émettent plusieurs events pour 1 fichier).
        key = str(file_path.resolve())
        if key in self._processed:
            return
        # Debounce : attendre que l'écriture soit terminée.
        time.sleep(self.debounce_seconds)
        if not file_path.exists():
            return  # supprimé pendant le debounce
        try:
            if self._organize_one(file_path):
                logger.info("Organisé : %s", file_path.name)
                self._processed.add(key)
            else:
                logger.warning("Échec organisation : %s", file_path.name)
        except Exception as exc:  # noqa: BLE001  — boucle de surveillance, on log et continue
            logger.error("Erreur sur %s : %s", file_path.name, exc)

    def run(self) -> int:
        """Lance la surveillance. Retourne quand l'utilisateur Ctrl+C."""
        if not self.source.exists():
            print(f"ERREUR : source introuvable : {self.source}", file=sys.stderr)
            return 1
        self.dest.mkdir(parents=True, exist_ok=True)

        print(f"Surveillance : {self.source}")
        print(f"Destination  : {self.dest}")
        print(f"Debounce     : {self.debounce_seconds}s")
        print("Ctrl+C pour arrêter.")

        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            print(
                "watchdog non installé — fallback en polling toutes les 10s. "
                "Pour de meilleures performances : pip install watchdog",
                file=sys.stderr,
            )
            return self._run_polling()

        class _Handler(FileSystemEventHandler):
            def __init__(self, watcher: "WatchFolder"):
                self.watcher = watcher

            def on_created(self, event):
                if not event.is_directory:
                    self.watcher._handle_new_file(Path(event.src_path))

            def on_moved(self, event):
                # Un déplacement IN du dossier surveillé compte comme création.
                if not event.is_directory and Path(event.dest_path).is_relative_to(self.watcher.source):
                    self.watcher._handle_new_file(Path(event.dest_path))

        observer = Observer()
        observer.schedule(_Handler(self), str(self.source), recursive=True)
        observer.start()
        try:
            while observer.is_alive():
                observer.join(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        return 0

    def _run_polling(self) -> int:
        """Fallback sans watchdog : poll toutes les 10 secondes."""
        seen = {str(p.resolve()) for p in self.source.rglob("*") if p.is_file()}
        try:
            while True:
                time.sleep(10)
                current = {str(p.resolve()): p for p in self.source.rglob("*") if p.is_file()}
                new = set(current) - seen
                for key in new:
                    self._handle_new_file(current[key])
                seen = set(current)
        except KeyboardInterrupt:
            return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="photo-organizer-pro-watch",
        description="Surveille un dossier et organise les nouveaux fichiers (édition Pro).",
    )
    parser.add_argument("--source", "-s", required=True, help="Dossier source à surveiller")
    parser.add_argument("--dest", "-d", required=True, help="Dossier destination organisé")
    parser.add_argument("--by-date", action="store_true", default=True)
    parser.add_argument("--no-by-date", dest="by_date", action="store_false")
    parser.add_argument("--by-camera", action="store_true")
    parser.add_argument("--by-gps", action="store_true")
    parser.add_argument("--date-format", default="year/month")
    parser.add_argument("--copy", action="store_true", default=True)
    parser.add_argument("--move", dest="copy", action="store_false")
    parser.add_argument(
        "--debounce",
        type=int,
        default=DEFAULT_DEBOUNCE_SECONDS,
        help=f"Délai (s) avant traitement après détection. Défaut : {DEFAULT_DEBOUNCE_SECONDS}",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    # Licence Pro requise.
    from src.photoorganizer_pro.license import load_active_license

    if load_active_license() is None:
        print(
            "ERREUR : aucune licence Pro valide trouvée.\n"
            "  Achetez ou activez votre licence : https://photoorganizer.lemonsqueezy.com",
            file=sys.stderr,
        )
        return 2

    watcher = WatchFolder(
        source=Path(args.source).resolve(),
        dest=Path(args.dest).resolve(),
        by_date=args.by_date,
        by_camera=args.by_camera,
        by_gps=args.by_gps,
        date_format=args.date_format,
        copy=args.copy,
        debounce_seconds=args.debounce,
    )
    return watcher.run()


if __name__ == "__main__":
    sys.exit(main())
