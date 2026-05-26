"""PhotoOrganizer Pro — surveillance de dossier (watch-folder).

Surveille un dossier source et déclenche automatiquement
l'organisation à chaque nouveau fichier détecté. Idéal pour les
photographes qui importent en continu depuis leur appareil.

Voir ``watch_folder.py`` pour l'entrée principale.
"""

from .watch_folder import WatchFolder, main

__all__ = ["WatchFolder", "main"]
