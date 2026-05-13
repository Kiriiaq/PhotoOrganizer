"""
Module d'extraction des métadonnées EXIF.
Supporte JPEG, HEIC/HEIF, RAW et vidéos.
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from PIL import ExifTags, Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

logger = logging.getLogger(__name__)


# Extensions supportées
EXTENSIONS = {
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
              '.webp', '.jfif', '.jp2', '.avif'],
    'heic': ['.heic', '.heif'],
    'raw': ['.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng',
            '.3fr', '.raf', '.pef', '.srw', '.sr2', '.x3f', '.mef', '.iiq', '.rwl'],
    'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
              '.3gp', '.m4v', '.mpg', '.mpeg', '.mts', '.ts', '.vob']
}


class ExifExtractor:
    """Classe pour extraire les métadonnées EXIF des fichiers média."""

    def __init__(self, exiftool_path: Optional[str] = None):
        """
        Initialise l'extracteur EXIF.

        Args:
            exiftool_path: Chemin vers l'exécutable ExifTool (optionnel)
        """
        self.exiftool_path = exiftool_path or self._find_exiftool()
        self._cache: Dict[str, Dict] = {}

    def _find_exiftool(self) -> Optional[str]:
        """Recherche ExifTool dans les emplacements courants.

        Robuste : ignore les chemins vides, attrape OSError (cf. WinError
        87 quand l'exécutable n'est pas trouvé du tout dans PATH).
        """
        possible_paths = [
            os.environ.get('EXIFTOOL_PATH', ''),
            'exiftool',
            'exiftool.exe',
            os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'exiftool.exe'),
        ]

        for path in possible_paths:
            if not path:
                continue
            if os.path.exists(path):
                return path
            try:
                result = subprocess.run(
                    [path, '-ver'],
                    capture_output=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue

        return None

    def extract(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Extrait les métadonnées d'un fichier.

        T-114 (retour qualif 2026-05-13) : double couche de cache
          1. ``self._cache`` mémoire (rapide, par-instance)
          2. ``utils.cache.get_cache()`` (persistant SQLite/JSON, partagé)

        Avant le fix, seul le cache mémoire local était utilisé : le cache
        global affichait toujours 0 hit. Désormais sur un miss mémoire on
        consulte le cache global ; un miss global déclenche l'extraction
        et alimente les deux couches.

        Args:
            file_path: Chemin du fichier
            use_cache: Utiliser le cache si disponible

        Returns:
            Dictionnaire des métadonnées
        """
        file_path = str(Path(file_path).resolve())

        # Couche 1 : cache mémoire interne (le plus rapide)
        if use_cache and file_path in self._cache:
            return self._cache[file_path]

        # Couche 2 : cache global persistant (hits comptabilisés)
        if use_cache:
            try:
                # Import différé pour éviter une dépendance circulaire à
                # l'import (utils.cache n'est pas critique au démarrage).
                from utils.cache import get_cache
                cached = get_cache().get(file_path)
                if cached is not None:
                    self._cache[file_path] = cached  # promote en mémoire
                    return cached
            except Exception as exc:
                logger.debug(f"Cache global indisponible : {exc}")

        if not os.path.exists(file_path):
            logger.warning(f"Fichier inexistant: {file_path}")
            return {}

        ext = os.path.splitext(file_path)[1].lower()

        # Sélectionner la méthode d'extraction
        if ext in EXTENSIONS['heic']:
            metadata = self._extract_heic(file_path)
        elif ext in EXTENSIONS['raw']:
            metadata = self._extract_raw(file_path)
        elif ext in EXTENSIONS['video']:
            metadata = self._extract_video(file_path)
        elif ext in EXTENSIONS['image']:
            metadata = self._extract_image(file_path)
        else:
            metadata = self._extract_basic(file_path)

        # Ajouter les métadonnées de base
        metadata.update(self._extract_basic(file_path))

        if use_cache:
            # Alimenter les deux couches
            self._cache[file_path] = metadata
            try:
                from utils.cache import get_cache
                get_cache().set(file_path, metadata)
            except Exception as exc:
                logger.debug(f"Cache global set échoué : {exc}")

        return metadata

    def _extract_image(self, file_path: str) -> Dict[str, Any]:
        """Extrait les métadonnées d'une image standard."""
        metadata = {}

        # Méthode 1: exifread
        if EXIFREAD_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    tags = exifread.process_file(f, details=False)
                    for tag, value in tags.items():
                        key = tag.split(' ', 1)[-1] if ' ' in tag else tag
                        metadata[key] = str(value)
                if metadata:
                    return metadata
            except Exception as e:
                logger.debug(f"exifread échoué pour {file_path}: {e}")

        # Méthode 2: Pillow
        if PIL_AVAILABLE:
            try:
                with Image.open(file_path) as img:
                    exif = img._getexif() if hasattr(img, '_getexif') else None
                    if exif:
                        for tag_id, value in exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8')
                                except:
                                    continue
                            metadata[tag_name] = value

                    # Dimensions
                    metadata['ImageWidth'] = img.width
                    metadata['ImageHeight'] = img.height
                    metadata['Format'] = img.format

                if metadata:
                    return metadata
            except Exception as e:
                logger.debug(f"Pillow échoué pour {file_path}: {e}")

        # Méthode 3: ExifTool
        exiftool_data = self._try_exiftool(file_path)
        if exiftool_data:
            return exiftool_data

        return metadata

    def _extract_heic(self, file_path: str) -> Dict[str, Any]:
        """Extrait les métadonnées d'un fichier HEIC/HEIF."""
        metadata = {}

        if HEIF_AVAILABLE and PIL_AVAILABLE:
            try:
                with Image.open(file_path) as img:
                    exif = img.getexif() if hasattr(img, 'getexif') else None
                    if exif:
                        for tag_id, value in exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            metadata[tag_name] = value

                        # GPS IFD
                        if hasattr(exif, 'get_ifd'):
                            gps_ifd = exif.get_ifd(0x8825)
                            if gps_ifd:
                                metadata['GPSInfo'] = gps_ifd

                    metadata['ImageWidth'] = img.width
                    metadata['ImageHeight'] = img.height

                if metadata:
                    return metadata
            except Exception as e:
                logger.debug(f"pillow_heif échoué pour {file_path}: {e}")

        # Fallback: ExifTool
        return self._try_exiftool(file_path) or {}

    def _extract_raw(self, file_path: str) -> Dict[str, Any]:
        """Extrait les métadonnées d'un fichier RAW."""
        # exifread est souvent efficace pour les RAW
        if EXIFREAD_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    tags = exifread.process_file(f, details=False)
                    metadata = {}
                    for tag, value in tags.items():
                        key = tag.split(' ', 1)[-1] if ' ' in tag else tag
                        metadata[key] = str(value)
                    if metadata:
                        return metadata
            except Exception as e:
                logger.debug(f"exifread échoué pour RAW {file_path}: {e}")

        # Fallback: ExifTool
        return self._try_exiftool(file_path) or {}

    def _extract_video(self, file_path: str) -> Dict[str, Any]:
        """Extrait les métadonnées d'un fichier vidéo."""
        metadata = {
            'MediaType': 'Video',
            'FileName': os.path.basename(file_path)
        }

        # Détection du fabricant par le nom de fichier
        filename = os.path.basename(file_path)
        if filename.startswith('PXL_'):
            metadata['Make'] = 'Google'
            metadata['Model'] = 'Pixel'
        elif filename.startswith('VID_'):
            metadata['Make'] = 'Samsung'

        # ExifTool pour les vidéos
        exiftool_data = self._try_exiftool(file_path)
        if exiftool_data:
            metadata.update(exiftool_data)

        return metadata

    def _extract_basic(self, file_path: str) -> Dict[str, Any]:
        """Extrait les métadonnées de base du système de fichiers."""
        try:
            stat = os.stat(file_path)
            return {
                'FileName': os.path.basename(file_path),
                'FileSize': stat.st_size,
                'FileModifyDate': datetime.fromtimestamp(stat.st_mtime).strftime('%Y:%m:%d %H:%M:%S'),
                'FileAccessDate': datetime.fromtimestamp(stat.st_atime).strftime('%Y:%m:%d %H:%M:%S'),
                'Directory': os.path.dirname(file_path)
            }
        except Exception as e:
            logger.error(f"Erreur extraction basique pour {file_path}: {e}")
            return {'FileName': os.path.basename(file_path)}

    def _try_exiftool(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Tente d'extraire les métadonnées avec ExifTool."""
        if not self.exiftool_path:
            return None

        try:
            result = subprocess.run(
                [self.exiftool_path, '-j', '-charset', 'UTF8', file_path],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                if data and isinstance(data, list) and data[0]:
                    return {k.replace(' ', ''): v for k, v in data[0].items()}
        except Exception as e:
            logger.debug(f"ExifTool échoué pour {file_path}: {e}")

        return None

    def clear_cache(self):
        """Vide le cache des métadonnées."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Retourne les statistiques du cache."""
        return {
            'entries': len(self._cache),
            'size_bytes': sum(len(str(v)) for v in self._cache.values())
        }


# Instance globale
_extractor: Optional[ExifExtractor] = None


def get_extractor() -> ExifExtractor:
    """Retourne l'instance globale de l'extracteur."""
    global _extractor
    if _extractor is None:
        _extractor = ExifExtractor()
    return _extractor


def get_exif_data(file_path: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Fonction utilitaire pour extraire les métadonnées EXIF.

    Args:
        file_path: Chemin du fichier
        use_cache: Utiliser le cache

    Returns:
        Dictionnaire des métadonnées
    """
    return get_extractor().extract(file_path, use_cache)
