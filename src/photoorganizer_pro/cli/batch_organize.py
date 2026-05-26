"""Batch CLI d'organisation — feature Pro.

Réutilise les modules core ``FileManager`` + ``SmartOrganizer`` sans
duplication. Le seul code propre à cette feature est la couche
argparse + le check de licence.

Usage typique
-------------

::

    # Organiser une fois (équivalent du clic "Organiser" dans la GUI)
    photo-organizer-pro-batch organize \\
        --source "D:/Photos/import" \\
        --dest "D:/Photos/library" \\
        --by-date --by-camera --copy

    # Avec un template de renommage
    photo-organizer-pro-batch organize \\
        --source "D:/Photos/import" \\
        --dest "D:/Photos/library" \\
        --by-date \\
        --rename "{date:%Y-%m-%d}_{model}_{counter:04d}"

    # Mode dry-run (n'écrit rien, montre ce qui serait fait)
    photo-organizer-pro-batch organize -s "D:/Photos" -d "D:/Sorted" --by-date --dry-run

Pré-requis : licence Pro active. Le binaire libère cette CLI uniquement
si ``%LOCALAPPDATA%\\PhotoOrganizer\\license.dat`` contient une clé
valide (cf. ``src/photoorganizer_pro/license/validator.py``).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def _require_license() -> None:
    """Vérifie la licence Pro. Sort proprement si absente / expirée."""
    from src.photoorganizer_pro.license import load_active_license

    info = load_active_license()
    if info is None:
        print(
            "ERREUR : aucune licence Pro valide trouvée.\n"
            "  Vérifiez %LOCALAPPDATA%\\PhotoOrganizer\\license.dat\n"
            "  Achetez ou réactivez votre licence sur :\n"
            "    https://photoorganizer.lemonsqueezy.com",
            file=sys.stderr,
        )
        sys.exit(2)
    days = info.days_remaining()
    if 0 <= days <= 30:
        print(f"AVERTISSEMENT : licence Pro expire dans {days} jour(s).", file=sys.stderr)


def _organize_command(args: argparse.Namespace) -> int:
    """Exécute l'organisation. Délègue au core."""
    # Import différé pour éviter de charger Pillow tant que --help suffit.
    from src.core.operations import FileManager, OrganizationOptions, SmartOrganizer

    source = Path(args.source).resolve()
    dest = Path(args.dest).resolve()
    if not source.exists():
        print(f"ERREUR : source introuvable : {source}", file=sys.stderr)
        return 1
    if not dest.exists():
        if args.create_dest:
            dest.mkdir(parents=True, exist_ok=True)
        else:
            print(
                f"ERREUR : destination introuvable : {dest}. Utiliser --create-dest pour la créer.",
                file=sys.stderr,
            )
            return 1

    fm = FileManager()
    files = fm.list_files(str(source), recursive=args.recursive)
    if not files:
        print(f"Aucun fichier trouvé sous {source}.", file=sys.stderr)
        return 0
    print(f"{len(files)} fichier(s) à traiter.")

    opts = OrganizationOptions(
        organize_by_date=args.by_date,
        organize_by_camera=args.by_camera,
        organize_by_location=args.by_gps,
        date_format=args.date_format,
        copy_instead_of_move=args.copy,
        rename_template=args.rename or "",
    )

    if args.dry_run:
        print("[DRY-RUN] aucun fichier ne sera modifié.")
        # Le core n'a pas (encore) de vrai mode dry-run sur l'organisation
        # complète. En attendant, on affiche les options et le nombre de
        # fichiers. TODO PRO-V1.1 : exposer ``SmartOrganizer.plan_only()``.
        print(f"Options : {opts}")
        return 0

    organizer = SmartOrganizer(file_manager=fm)

    def _progress(current: int, total: int, file_path: str) -> bool:
        if current % 50 == 0 or current == total:
            print(f"  [{current}/{total}] {Path(file_path).name}")
        return True  # ne pas annuler

    result = organizer.organize(
        files=files,
        source_dir=str(source),
        dest_dir=str(dest),
        options=opts,
        progress_callback=_progress,
    )
    print(
        f"Terminé : {result.success} succès · {result.failed} échecs · {result.skipped} ignorés "
        f"(sur {result.total})."
    )
    return 0 if result.failed == 0 else 1


def main(argv: Optional[List[str]] = None) -> int:
    """Point d'entrée CLI. Retourne le code de sortie shell."""
    parser = argparse.ArgumentParser(
        prog="photo-organizer-pro-batch",
        description="CLI batch d'organisation de photos par EXIF (édition Pro).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    org = sub.add_parser("organize", help="Organiser un dossier")
    org.add_argument("--source", "-s", required=True, help="Dossier source à scanner")
    org.add_argument("--dest", "-d", required=True, help="Dossier destination")
    org.add_argument("--create-dest", action="store_true", help="Créer la destination si absente")
    org.add_argument("--recursive", "-r", action="store_true", default=True, help="Scan récursif (défaut)")
    org.add_argument("--no-recursive", dest="recursive", action="store_false", help="Désactiver récursif")
    org.add_argument("--by-date", action="store_true", help="Organiser par date EXIF")
    org.add_argument("--by-camera", action="store_true", help="Organiser par modèle d'appareil")
    org.add_argument("--by-gps", action="store_true", help="Organiser par coordonnées GPS")
    org.add_argument(
        "--date-format",
        default="year/month",
        help='Format date. Ex: "year/month/day" → 2024/03/15. Défaut : "year/month".',
    )
    org.add_argument(
        "--copy",
        action="store_true",
        default=True,
        help="Copier au lieu de déplacer (défaut). Utiliser --move pour déplacer.",
    )
    org.add_argument("--move", dest="copy", action="store_false", help="Déplacer au lieu de copier")
    org.add_argument(
        "--rename",
        help='Template renommage. Variables : {date:%%Y-%%m-%%d}, {counter:04d}, {model}, {ext}',
    )
    org.add_argument("--dry-run", action="store_true", help="Simulation sans modifier les fichiers")

    args = parser.parse_args(argv)

    # Configuration logging minimal.
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    # Vérification licence avant toute opération.
    _require_license()

    if args.command == "organize":
        return _organize_command(args)
    parser.error(f"Commande inconnue : {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
