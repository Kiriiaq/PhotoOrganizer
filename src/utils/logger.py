"""
Module de configuration du logging.
Gestion centralisée des logs de l'application.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


def get_log_dir() -> Path:
    """Retourne le répertoire des logs."""
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        log_dir = Path(base) / 'PhotoOrganizer' / 'logs'
    else:
        log_dir = Path.home() / '.local' / 'share' / 'PhotoOrganizer' / 'logs'

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure le système de logging.

    Args:
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Écrire dans un fichier
        log_file: Nom du fichier de log (auto-généré si non fourni)

    Returns:
        Logger racine configuré
    """
    # Niveau de log
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Logger racine
    root_logger = logging.getLogger('PhotoOrganizer')
    root_logger.setLevel(log_level)

    # Supprimer les handlers existants
    root_logger.handlers.clear()

    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler fichier
    if log_to_file:
        log_dir = get_log_dir()

        if log_file:
            log_path = log_dir / log_file
        else:
            timestamp = datetime.now().strftime('%Y%m%d')
            log_path = log_dir / f"photoorganizer_{timestamp}.log"

        try:
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Impossible de créer le fichier de log: {e}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger pour un module spécifique.

    Args:
        name: Nom du module

    Returns:
        Logger configuré
    """
    return logging.getLogger(f'PhotoOrganizer.{name}')


def cleanup_old_logs(max_age_days: int = 30):
    """
    Supprime les fichiers de log anciens.

    Args:
        max_age_days: Âge maximum des logs en jours
    """
    log_dir = get_log_dir()
    cutoff = datetime.now().timestamp() - (max_age_days * 24 * 3600)

    for log_file in log_dir.glob("*.log"):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
        except Exception:
            pass
