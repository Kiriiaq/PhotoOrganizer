"""
Module d'extraction des dates des fichiers média.
Supporte EXIF, nom de fichier et métadonnées système.
"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Formats de date EXIF
EXIF_DATE_FORMATS = [
    '%Y:%m:%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S',
    '%Y/%m/%d %H:%M:%S',
    '%Y:%m:%d %H:%M:%S.%f',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%SZ',
]

# Champs EXIF contenant des dates (par priorité)
DATE_FIELDS = [
    'DateTimeOriginal',
    'DateTime',
    'CreateDate',
    'DateTimeDigitized',
    'ModifyDate',
    'TrackCreateDate',
    'MediaCreateDate'
]


class DateExtractor:
    """Classe pour extraire les dates des fichiers média."""

    # Patterns par fabricant
    MANUFACTURER_PATTERNS: Dict[str, List[Tuple[str, Callable]]] = {
        'samsung': [
            (r'(\d{8})_(\d{6})(?:_\d+)?',
             lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
        ],
        'iphone': [
            (r'IMG_(\d{8})_(\d{6})',
             lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
        ],
        'pixel': [
            (r'PXL_(\d{8})_(\d{9})',
             lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)[:6]}", "%Y%m%d_%H%M%S")),
        ],
        'whatsapp': [
            (r'IMG-(\d{8})-WA',
             lambda m: datetime.strptime(m.group(1), "%Y%m%d")),
            (r'VID-(\d{8})-WA',
             lambda m: datetime.strptime(m.group(1), "%Y%m%d")),
        ],
        'gopro': [
            (r'GoPro(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',
             lambda m: datetime(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)),
                               int(m.group(4)), int(m.group(5)), int(m.group(6)))),
        ],
        'dji': [
            (r'DJI_(\d{8})_(\d{6})',
             lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
        ],
    }

    # Patterns génériques
    GENERIC_PATTERNS: List[Tuple[str, Callable]] = [
        # YYYYMMDD_HHMMSS
        (r'(?:^|[^0-9])(\d{8})_(\d{6})(?:[^0-9]|$)',
         lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
        # YYYY-MM-DD_HH-MM-SS
        (r'(\d{4})-(\d{2})-(\d{2})[\s_-](\d{2})[-_](\d{2})[-_](\d{2})',
         lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                           int(m.group(4)), int(m.group(5)), int(m.group(6)))),
        # YYYYMMDD simple
        (r'(?:^|[^0-9])(\d{4})(\d{2})(\d{2})(?:[^0-9]|$)',
         lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
         if 1900 <= int(m.group(1)) <= 2100 and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31
         else None),
    ]

    def __init__(self):
        """Initialise l'extracteur de dates."""
        pass

    def extract(
        self,
        file_path: str,
        exif_data: Optional[Dict[str, Any]] = None,
        fallback_to_file_date: bool = True,
        return_origin: bool = False
    ) -> Optional[datetime] | Tuple[Optional[datetime], Optional[str]]:
        """
        Extrait la date d'un fichier avec plusieurs méthodes.

        Args:
            file_path: Chemin du fichier
            exif_data: Données EXIF (optionnel, sera extrait si non fourni)
            fallback_to_file_date: Utiliser la date système en dernier recours
            return_origin: Retourner aussi l'origine de la date

        Returns:
            datetime ou tuple (datetime, origin) selon return_origin
        """
        date_result = None
        origin = None
        filename = os.path.basename(file_path)

        # 1. Extraction depuis EXIF
        if exif_data is None and os.path.exists(file_path):
            from .exif_extractor import get_exif_data
            exif_data = get_exif_data(file_path)

        if exif_data:
            date_result = self._extract_from_exif(exif_data)
            if date_result:
                origin = 'exif'

        # 2. Extraction depuis le nom de fichier
        if date_result is None:
            date_result, manufacturer = self._extract_from_filename(filename)
            if date_result:
                origin = f'filename:{manufacturer}'

        # 3. Fallback: date du système de fichiers
        if date_result is None and fallback_to_file_date and os.path.exists(file_path):
            date_result = self._extract_from_filesystem(file_path)
            if date_result:
                origin = 'filesystem'

        if return_origin:
            return date_result, origin
        return date_result

    def _extract_from_exif(self, exif_data: Dict[str, Any]) -> Optional[datetime]:
        """Extrait la date depuis les données EXIF."""
        for field in DATE_FIELDS:
            if field not in exif_data:
                continue

            date_str = exif_data[field]
            if not isinstance(date_str, str):
                continue

            for fmt in EXIF_DATE_FORMATS:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

        return None

    def _extract_from_filename(self, filename: str) -> Tuple[Optional[datetime], str]:
        """Extrait la date depuis le nom de fichier."""
        # Patterns spécifiques aux fabricants
        for manufacturer, patterns in self.MANUFACTURER_PATTERNS.items():
            for pattern, parser in patterns:
                match = re.search(pattern, filename)
                if match:
                    try:
                        result = parser(match)
                        if result:
                            return result, manufacturer
                    except (ValueError, Exception):
                        continue

        # Patterns génériques
        for pattern, parser in self.GENERIC_PATTERNS:
            match = re.search(pattern, filename)
            if match:
                try:
                    result = parser(match)
                    if result:
                        return result, 'generic'
                except (ValueError, Exception):
                    continue

        return None, ''

    def _extract_from_filesystem(self, file_path: str) -> Optional[datetime]:
        """Extrait la date depuis les métadonnées du système de fichiers."""
        try:
            stat = os.stat(file_path)

            # Préférer la date de création si disponible (Windows)
            if hasattr(stat, 'st_birthtime'):
                return datetime.fromtimestamp(stat.st_birthtime)

            # Sinon utiliser la date de modification
            return datetime.fromtimestamp(stat.st_mtime)

        except Exception as e:
            logger.debug(f"Erreur extraction date système pour {file_path}: {e}")
            return None


# Instance globale
_extractor: Optional[DateExtractor] = None


def get_extractor() -> DateExtractor:
    """Retourne l'instance globale de l'extracteur de dates."""
    global _extractor
    if _extractor is None:
        _extractor = DateExtractor()
    return _extractor


def extract_date(
    file_path: str,
    exif_data: Optional[Dict] = None,
    fallback_to_file_date: bool = True,
    return_origin: bool = False
) -> Optional[datetime] | Tuple[Optional[datetime], Optional[str]]:
    """
    Fonction utilitaire pour extraire la date d'un fichier.

    Args:
        file_path: Chemin du fichier
        exif_data: Données EXIF (optionnel)
        fallback_to_file_date: Utiliser la date système en fallback
        return_origin: Retourner l'origine de la date

    Returns:
        datetime ou tuple (datetime, origin)
    """
    return get_extractor().extract(
        file_path, exif_data, fallback_to_file_date, return_origin
    )
