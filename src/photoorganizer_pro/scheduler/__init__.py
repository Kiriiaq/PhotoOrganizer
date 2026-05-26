"""PhotoOrganizer Pro — surveillance de dossier watch-folder (**DEFERRED v3.0+**).

⚠️ Gelé depuis le pivot économique 2026-05-26.
Entry point ``photo-organizer-pro-watch`` commenté dans ``pyproject.toml``.
Tests skippés via ``@pytest.mark.skip(reason="Deferred to v3.0+")``.
Code conservé intact pour réactivation conditionnelle. Cf. ``../__init__.py``.

Surveille un dossier source et déclenche automatiquement
l'organisation à chaque nouveau fichier détecté. Idéal pour les
photographes qui importent en continu depuis leur appareil.

Voir ``watch_folder.py`` pour l'entrée principale.
"""

from .watch_folder import WatchFolder, main

__all__ = ["WatchFolder", "main"]
