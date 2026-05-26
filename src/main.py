#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoOrganizer v2.0.0
Organiseur intelligent de photos et vidéos.

Point d'entrée principal de l'application.
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
    logger.info("Démarrage de PhotoOrganizer v2.0.0")

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
