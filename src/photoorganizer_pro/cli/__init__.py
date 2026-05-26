"""PhotoOrganizer Pro — CLI batch d'organisation.

Permet de scripter l'organisation depuis le terminal, sans GUI. Idéal
pour Task Scheduler Windows, cron Linux, ou un build CI/CD qui traite
des photos en lot.

Voir ``batch_organize.py`` pour l'entrée principale.
"""

from .batch_organize import main

__all__ = ["main"]
