"""PhotoOrganizer Pro — CLI batch d'organisation (**DEFERRED v3.0+**).

⚠️ Gelé depuis le pivot économique 2026-05-26.
Entry point ``photo-organizer-pro-batch`` commenté dans ``pyproject.toml``.
Tests skippés via ``@pytest.mark.skip(reason="Deferred to v3.0+")``.
Code conservé intact pour réactivation conditionnelle. Cf. ``../__init__.py``.

Permet de scripter l'organisation depuis le terminal, sans GUI. Idéal
pour Task Scheduler Windows, cron Linux, ou un build CI/CD qui traite
des photos en lot.

Voir ``batch_organize.py`` pour l'entrée principale.
"""

from .batch_organize import main

__all__ = ["main"]
