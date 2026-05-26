"""Watch-folder — feature Pro.

Surveille un dossier source et organise automatiquement chaque nouveau
fichier vers une destination triée.

Backend : ``watchdog`` si disponible (extras ``pro`` de pyproject.toml),
fallback polling toutes les 10 s sinon.

Sécurité de l'écriture en cours : un *debounce* (par défaut 5 s) est
appliqué entre la détection et le traitement, pour laisser le temps à
un transfert depuis carte SD de se terminer avant d'invoquer
l'organiseur sur un fichier encore en cours d'écriture.

Service Windows : voir ``docs/PRO.md`` (section NSSM).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Callable, List, Optional, Set

logger = logging.getLogger(__name__)


# Extensions surveillées (alignées avec ``core/operations/file_manager.py``)
WATCHED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".jfif", ".jp2", ".heic", ".heif", ".avif",
    ".raw", ".arw", ".cr2", ".cr3", ".nef", ".orf", ".rw2", ".dng",
    ".3fr", ".raf", ".pef", ".srw", ".sr2", ".x3f", ".mef", ".iiq", ".rwl",
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm",
    ".3gp", ".m4v", ".mpg", ".mpeg", ".mts", ".ts", ".vob",
}

DEFAULT_DEBOUNCE_SECONDS = 5


class WatchFolder:
    """Surveille un dossier source et organise les nouveaux fichiers.

    Conçu pour être instanciable et testable indépendamment de la couche
    CLI : on peut piloter à la main les méthodes ``handle_path`` /
    ``poll_once`` sans démarrer la vraie boucle de surveillance.
    """

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
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.source = source
        self.dest = dest
        self.by_date = by_date
        self.by_camera = by_camera
        self.by_gps = by_gps
        self.date_format = date_format
        self.copy = copy
        self.debounce_seconds = debounce_seconds
        # Injection pour permettre aux tests de neutraliser sleep().
        self._sleep = sleep_fn
        # Anti-doublon : ne pas retraiter le même chemin.
        self._processed: Set[str] = set()

    # -----------------------------------------------------------------
    # API publique (testable)
    # -----------------------------------------------------------------
    def is_watched(self, path: Path) -> bool:
        """True si ``path`` est un fichier média qu'on doit traiter."""
        return path.suffix.lower() in WATCHED_EXTENSIONS

    def already_processed(self, path: Path) -> bool:
        return str(path.resolve()) in self._processed

    def mark_processed(self, path: Path) -> None:
        self._processed.add(str(path.resolve()))

    def handle_path(self, file_path: Path) -> bool:
        """Traite UN fichier (debounce + organize). Retourne True si organisé.

        N'attrape pas KeyboardInterrupt — la boucle parent s'en charge.
        """
        if not self.is_watched(file_path):
            return False
        if self.already_processed(file_path):
            return False
        # Debounce : laisser le temps à l'écriture de finir
        if self.debounce_seconds > 0:
            self._sleep(self.debounce_seconds)
        if not file_path.exists():
            return False  # supprimé entretemps
        try:
            ok = self._organize_one(file_path)
        except Exception as exc:  # noqa: BLE001 — surveillance long-running, on log et continue
            logger.error("Erreur sur %s : %s", file_path.name, exc)
            return False
        if ok:
            logger.info("Organisé : %s", file_path.name)
            self.mark_processed(file_path)
        else:
            logger.warning("Échec organisation : %s", file_path.name)
        return ok

    # -----------------------------------------------------------------
    # Backend organisation (peut être patché en test)
    # -----------------------------------------------------------------
    def _organize_one(self, file_path: Path) -> bool:
        from src.core.operations import FileManager, OrganizationOptions, SmartOrganizer

        fm = FileManager()
        opts = OrganizationOptions(
            organize_by_date=self.by_date,
            organize_by_camera=self.by_camera,
            organize_by_location=self.by_gps,
            date_format=self.date_format,
            copy_not_move=self.copy,
            auto_rename=True,
        )
        organizer = SmartOrganizer(file_manager=fm)
        result = organizer.organize(
            file_paths=[str(file_path)],
            target_dir=str(self.dest),
            options=opts,
        )
        return result.success >= 1

    # -----------------------------------------------------------------
    # Boucles d'exécution
    # -----------------------------------------------------------------
    def run(self) -> int:
        """Lance la surveillance. Retourne le code de sortie."""
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
                "watchdog non installé — fallback polling 10s. "
                "Pour de meilleures performances : pip install watchdog",
                file=sys.stderr,
            )
            return self._run_polling()

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_created(self, event):  # noqa: D401
                if not event.is_directory:
                    watcher.handle_path(Path(event.src_path))

            def on_moved(self, event):  # noqa: D401
                if event.is_directory:
                    return
                dest_path = Path(event.dest_path)
                try:
                    if dest_path.is_relative_to(watcher.source):
                        watcher.handle_path(dest_path)
                except (ValueError, AttributeError):
                    # is_relative_to peut lever ValueError sur Py < 3.9 ;
                    # on retombe sur l'ancienne forme.
                    try:
                        dest_path.relative_to(watcher.source)
                        watcher.handle_path(dest_path)
                    except ValueError:
                        pass

        observer = Observer()
        observer.schedule(_Handler(), str(self.source), recursive=True)
        observer.start()
        try:
            while observer.is_alive():
                observer.join(1)
        except KeyboardInterrupt:
            print("\nArrêt utilisateur (Ctrl+C).", file=sys.stderr)
            observer.stop()
        observer.join()
        return 0

    def poll_once(self, seen: Optional[Set[str]] = None) -> Set[str]:
        """Un tour de polling. Retourne l'ensemble courant des chemins.

        Exposée publiquement pour les tests : permet de simuler
        l'apparition de nouveaux fichiers en injectant un ``seen`` initial
        partiel.
        """
        current: Set[str] = set()
        if not self.source.exists():
            return current
        for p in self.source.rglob("*"):
            if p.is_file():
                key = str(p.resolve())
                current.add(key)
                if seen is not None and key not in seen:
                    self.handle_path(p)
        return current

    def _run_polling(self) -> int:
        seen = self.poll_once(seen=None)  # initial scan : on marque tout comme "déjà vu"
        try:
            while True:
                self._sleep(10)
                seen = self.poll_once(seen=seen)
        except KeyboardInterrupt:
            print("\nArrêt utilisateur (Ctrl+C).", file=sys.stderr)
            return 0


# -----------------------------------------------------------------
# Entry point CLI
# -----------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
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

    from src.photoorganizer_pro.license import load_active_license

    if load_active_license() is None:
        print(
            "ERREUR : aucune licence Pro valide trouvée.\n"
            "  Achète ou active ta licence : https://photoorganizer.lemonsqueezy.com",
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
