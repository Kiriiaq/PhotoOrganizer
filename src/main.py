#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoOrganizer — Organiseur intelligent de photos et vidéos.

Point d'entrée principal de l'application. La version effective est lue
depuis ``src/__init__.__version__`` (source de vérité unique).
"""

import os
import sys

# Ajouter le répertoire source au path
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


def check_dependencies():
    """Vérifie que les dépendances requises sont installées."""
    missing = []

    # CustomTkinter (interface)
    try:
        import customtkinter  # noqa: F401  (availability sentinel)
    except ImportError:
        missing.append("customtkinter")

    # Pillow (images)
    try:
        from PIL import Image  # noqa: F401  (availability sentinel)
    except ImportError:
        missing.append("Pillow")

    if missing:
        print("=" * 60)
        print("ERREUR: Dépendances manquantes")
        print("=" * 60)
        print("\nVeuillez installer les packages suivants:\n")
        print(f"  pip install {' '.join(missing)}")
        print("\nOu installez toutes les dépendances avec:")
        print("  pip install -r requirements.txt")
        print("=" * 60)
        sys.exit(1)


def main():
    """Point d'entrée principal."""
    # Vérifier les dépendances
    check_dependencies()

    # Importer et lancer l'application
    from ui.app import PhotoOrganizerApp
    from utils.logger import setup_logging

    # Configurer le logging
    logger = setup_logging(level="INFO")
    # Version lue depuis src/__init__.py (source de vérité unique)
    try:
        from src import __version__ as _app_version
    except ImportError:
        # Fallback si on tourne sans le préfixe ``src.`` (cas de l'EXE
        # PyInstaller où ``src`` n'est pas un package importable).
        from __init__ import __version__ as _app_version  # type: ignore
    logger.info(f"Démarrage de PhotoOrganizer v{_app_version}")

    try:
        # Créer et lancer l'application
        app = PhotoOrganizerApp()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Erreur fatale: {e}", exc_info=True)
        raise
    finally:
        logger.info("Fermeture de PhotoOrganizer")


if __name__ == "__main__":
    main()
