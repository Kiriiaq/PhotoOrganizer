"""Batch CLI Pro — organisation et détection de doublons depuis le terminal.

Réutilise les modules ``core/operations`` sans duplication. Le seul code
propre à cette feature est la couche argparse, la vérification de
licence, et un mode dry-run qui n'invoque pas l'organiseur.

Sous-commandes
--------------

``organize`` — trier un dossier (équivalent du clic GUI)
::

    photo-organizer-pro-batch organize \\
        --source D:/Photos/import --dest D:/Photos/library \\
        --by-date --by-camera --copy

``dedup`` — détecter et gérer les doublons d'un dossier
::

    photo-organizer-pro-batch dedup \\
        D:/Photos --recursive --algorithm blake3 --report json

``info`` — afficher l'état de la licence Pro
::

    photo-organizer-pro-batch info

Pré-requis : licence Pro active dans
``%LOCALAPPDATA%\\PhotoOrganizer\\license.dat``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Licence
# ---------------------------------------------------------------------
def _require_license() -> "LicenseInfo":  # noqa: F821 — forward ref
    """Vérifie la licence Pro et la retourne. Sort en code 2 si invalide."""
    from src.photoorganizer_pro.license import load_active_license

    info = load_active_license()
    if info is None:
        print(
            "ERREUR : aucune licence Pro valide trouvée.\n"
            "  Vérifie %LOCALAPPDATA%\\PhotoOrganizer\\license.dat\n"
            "  Achète ou réactive ta licence : https://photoorganizer.lemonsqueezy.com",
            file=sys.stderr,
        )
        sys.exit(2)
    days = info.days_remaining()
    if 0 <= days <= 30:
        print(f"AVERTISSEMENT : licence Pro expire dans {days} jour(s).", file=sys.stderr)
    return info


# ---------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------
def _resolve_dir(path_str: str, must_exist: bool = True, create: bool = False) -> Path:
    p = Path(path_str).expanduser().resolve()
    if create and not p.exists():
        p.mkdir(parents=True, exist_ok=True)
    elif must_exist and not p.exists():
        print(f"ERREUR : dossier introuvable : {p}", file=sys.stderr)
        sys.exit(1)
    return p


def _make_progress_callback(prefix: str = "") -> Callable[[int, int, str], None]:
    """Callback de progression qui imprime tous les N fichiers."""

    def cb(current: int, total: int, message: str) -> None:
        if total <= 0:
            return
        # Toutes les 50 unités OU pile à la fin OU au début
        if current == 1 or current % 50 == 0 or current >= total:
            pct = int(current * 100 / max(total, 1))
            short = Path(message).name if message else ""
            print(f"  {prefix}[{current}/{total}] {pct}%  {short}", flush=True)

    return cb


# ---------------------------------------------------------------------
# organize
# ---------------------------------------------------------------------
def _build_organize_options(args: argparse.Namespace) -> Any:
    from src.core.operations import OrganizationOptions

    return OrganizationOptions(
        organize_by_date=args.by_date,
        organize_by_camera=args.by_camera,
        organize_by_location=args.by_gps,
        date_format=args.date_format,
        copy_not_move=args.copy,
        auto_rename=True,
        skip_existing=args.skip_existing,
    )


def _cmd_organize(args: argparse.Namespace) -> int:
    from src.core.operations import FileManager, SmartOrganizer

    source = _resolve_dir(args.source, must_exist=True)
    dest = _resolve_dir(args.dest, must_exist=False, create=args.create_dest)
    if not dest.exists():
        print(
            f"ERREUR : destination introuvable : {dest}. Ajoute --create-dest pour la créer.",
            file=sys.stderr,
        )
        return 1

    fm = FileManager()
    files = fm.list_files(str(source), recursive=args.recursive)
    if not files:
        print(f"Aucun fichier média trouvé sous {source}.")
        return 0

    print(f"Source : {source}")
    print(f"Dest   : {dest}")
    print(f"Fichiers détectés : {len(files)}")

    opts = _build_organize_options(args)

    # ----------------------------------------------------------------
    # Mode dry-run : on n'invoque PAS l'organiseur (qui copie / déplace).
    # À la place on construit la liste des destinations prévues via
    # ``SmartOrganizer._compute_destination`` (méthode interne stable
    # depuis v2.0). Pour rester robuste si l'API privée change, on log
    # juste les fichiers + options et un échantillon.
    # ----------------------------------------------------------------
    if args.dry_run:
        print("[DRY-RUN] Aucun fichier ne sera modifié.")
        print(f"Options : by-date={opts.organize_by_date} by-camera={opts.organize_by_camera} "
              f"by-gps={opts.organize_by_location} date-format={opts.date_format} "
              f"copy={opts.copy_not_move}")
        # Affiche les 10 premiers fichiers détectés à titre indicatif.
        sample = files[:10]
        print(f"Échantillon de {len(sample)} fichier(s) :")
        for f in sample:
            print(f"  - {Path(f).relative_to(source) if Path(f).is_relative_to(source) else f}")
        if len(files) > 10:
            print(f"  ... +{len(files) - 10} autres")
        return 0

    organizer = SmartOrganizer(file_manager=fm)
    progress = _make_progress_callback() if args.verbose else None

    try:
        result = organizer.organize(
            file_paths=files,
            target_dir=str(dest),
            options=opts,
            progress_callback=progress,
        )
    except KeyboardInterrupt:
        print("\nAnnulation utilisateur (Ctrl+C).", file=sys.stderr)
        organizer.cancel()
        return 130

    print(
        f"Terminé : {result.success} succès · {result.failed} échecs · "
        f"{result.skipped} ignorés (total {result.total})."
    )
    return 0 if result.failed == 0 else 1


# ---------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------
def _cmd_dedup(args: argparse.Namespace) -> int:
    from src.core.operations import FileManager
    from src.core.operations.duplicate_finder import get_finder

    source = _resolve_dir(args.source, must_exist=True)

    fm = FileManager()
    files = fm.list_files(str(source), recursive=args.recursive)
    if not files:
        print(f"Aucun fichier trouvé sous {source}.")
        return 0

    print(f"Scan : {len(files)} fichier(s) avec algo {args.algorithm}…")

    finder = get_finder(algorithm=args.algorithm, quick_mode=True, use_cache=True)
    progress = _make_progress_callback("hash ") if args.verbose else None
    result = finder.find_duplicates(files, progress_callback=progress)

    # Métriques
    total = result.total_files
    unique = result.unique_files
    dups = result.duplicate_count
    waste = result.total_wasted_space
    waste_h = finder.format_size(waste) if hasattr(finder, "format_size") else f"{waste} B"

    print()
    print(f"Total fichiers   : {total}")
    print(f"Fichiers uniques : {unique}")
    print(f"Doublons         : {dups}  (espace gaspillé : {waste_h})")
    print(f"Temps de scan    : {result.scan_time:.2f}s")

    # Export rapport si demandé
    if args.report:
        from src.reports.duplicate_reporter import DuplicateReporter

        reporter = DuplicateReporter()
        out_path = Path(args.report_out) if args.report_out else source / f"duplicates_report.{args.report}"
        fmt = args.report.lower()
        if fmt == "csv":
            reporter.export_csv(result, str(out_path))
        elif fmt == "json":
            reporter.export_json(result, str(out_path))
        elif fmt == "html":
            reporter.export_html(result, str(out_path))
        elif fmt == "markdown":
            reporter.export_markdown(result, str(out_path))
        else:
            print(f"AVERTISSEMENT : format de rapport inconnu '{args.report}'.", file=sys.stderr)
        print(f"Rapport écrit : {out_path}")

    return 0


# ---------------------------------------------------------------------
# info
# ---------------------------------------------------------------------
def _cmd_info(_args: argparse.Namespace) -> int:
    from src.photoorganizer_pro.license import load_active_license

    info = load_active_license()
    if info is None:
        print("Aucune licence Pro active.")
        print("  Achète : https://photoorganizer.lemonsqueezy.com")
        return 2
    print("Licence PhotoOrganizer Pro active :")
    print(f"  Email       : {info.email}")
    print(f"  Édition     : {info.edition}")
    print(f"  Expire le   : {info.expires.isoformat()}")
    days = info.days_remaining()
    print(f"  Jours restants : {days}")
    return 0


# ---------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="photo-organizer-pro-batch",
        description="CLI batch d'organisation et de détection de doublons (édition Pro).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Logs détaillés (progress par 50)")
    sub = parser.add_subparsers(dest="command", required=True)

    # organize
    org = sub.add_parser("organize", help="Organiser un dossier par EXIF")
    org.add_argument("--source", "-s", required=True, help="Dossier source à scanner")
    org.add_argument("--dest", "-d", required=True, help="Dossier destination")
    org.add_argument("--create-dest", action="store_true", help="Créer la destination si absente")
    org.add_argument("--recursive", "-r", action="store_true", default=True, help="Scan récursif (défaut)")
    org.add_argument("--no-recursive", dest="recursive", action="store_false", help="Désactiver récursif")
    org.add_argument("--by-date", action="store_true", default=True, help="Organiser par date EXIF (défaut)")
    org.add_argument("--no-by-date", dest="by_date", action="store_false")
    org.add_argument("--by-camera", action="store_true", help="Organiser par modèle d'appareil")
    org.add_argument("--by-gps", action="store_true", help="Organiser par coordonnées GPS")
    org.add_argument(
        "--date-format",
        default="year/month",
        help='Format date. Ex : year/month/day → 2024/03/15. Défaut : year/month',
    )
    org.add_argument("--copy", action="store_true", default=True, help="Copier (défaut)")
    org.add_argument("--move", dest="copy", action="store_false", help="Déplacer au lieu de copier")
    org.add_argument(
        "--skip-existing",
        action="store_true",
        help="Si la destination existe déjà, ne pas re-organiser",
    )
    org.add_argument("--dry-run", action="store_true", help="Simulation : aucun fichier modifié")

    # dedup
    dd = sub.add_parser("dedup", help="Détecter les doublons d'un dossier")
    dd.add_argument("--source", "-s", required=True, help="Dossier à analyser")
    dd.add_argument("--recursive", "-r", action="store_true", default=True)
    dd.add_argument("--no-recursive", dest="recursive", action="store_false")
    dd.add_argument(
        "--algorithm",
        "-a",
        default="md5",
        choices=["md5", "sha1", "blake3"],
        help="Algorithme de hashing. blake3 est 2-3× plus rapide si disponible.",
    )
    dd.add_argument(
        "--report",
        choices=["csv", "json", "html", "markdown"],
        help="Exporter le rapport dans le format choisi.",
    )
    dd.add_argument("--report-out", help="Chemin du rapport (défaut : <source>/duplicates_report.<fmt>)")

    # info
    sub.add_parser("info", help="Afficher l'état de la licence Pro")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    # info ne nécessite pas une licence valide (au contraire, c'est le diagnostic).
    if args.command == "info":
        return _cmd_info(args)

    # Toutes les autres commandes nécessitent une licence valide.
    _require_license()

    if args.command == "organize":
        return _cmd_organize(args)
    if args.command == "dedup":
        return _cmd_dedup(args)

    parser.error(f"Commande inconnue : {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
