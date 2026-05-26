#!/usr/bin/env python3
"""
PhotoOrganizer - Point d'entree principal
Outil d'organisation automatique de photos par metadonnees EXIF.

Auteur: Kiriiaq
Email: manugrolleau48@gmail.com
Ko-fi: https://ko-fi.com/kiriiaq
"""

import logging
import os
import sys

# Configuration Windows pour l'icone dans la barre des taches
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PhotoOrganizer.v1.0")
    except Exception:
        pass

# Debug mode via environment variable
if os.environ.get("PHOTOORGANIZER_DEBUG") == "1":
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("PhotoOrganizer DEBUG mode enabled")

# Ajouter le dossier src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main

if __name__ == "__main__":
    main()
