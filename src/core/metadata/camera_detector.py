"""
Module de détection des informations d'appareil photo.
Extraction et normalisation des données fabricant/modèle.
"""

import os
import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class CameraDetector:
    """Classe pour détecter les informations d'appareil photo."""

    # Mapping des noms de fabricants
    MAKE_MAPPING = {
        'Google Inc': 'Google',
        'Google Inc.': 'Google',
        'Samsung Electronics': 'Samsung',
        'Samsung Electronics Co., Ltd.': 'Samsung',
        'Samsung Electronics Co.,Ltd.': 'Samsung',
        'NIKON CORPORATION': 'Nikon',
        'Canon Inc.': 'Canon',
        'SONY': 'Sony',
        'Apple': 'Apple',
        'HUAWEI': 'Huawei',
        'OnePlus': 'OnePlus',
        'Xiaomi': 'Xiaomi',
        'OPPO': 'Oppo',
        'vivo': 'Vivo',
        'DJI': 'DJI',
        'GoPro': 'GoPro',
    }

    # Mapping des modèles Samsung
    SAMSUNG_MODELS = {
        'SM-S911': 'Galaxy S23',
        'SM-S916': 'Galaxy S23+',
        'SM-S918': 'Galaxy S23 Ultra',
        'SM-S901': 'Galaxy S22',
        'SM-S906': 'Galaxy S22+',
        'SM-S908': 'Galaxy S22 Ultra',
        'SM-G99': 'Galaxy S21',
        'SM-A': 'Galaxy A',
        'SM-N': 'Galaxy Note',
        'SM-F': 'Galaxy Fold',
        'SM-Z': 'Galaxy Z Flip',
    }

    # Patterns de détection par nom de fichier
    FILENAME_PATTERNS = {
        r'^IMG_\d{4}\.HEIC$': ('Apple', 'iPhone'),
        r'^IMG_\d{8}_\d{6}': ('Apple', 'iPhone'),
        r'^PXL_\d{8}_\d{9}': ('Google', 'Pixel'),
        r'^PXL_\d{8}_\d{6}\.mp4$': ('Google', 'Pixel'),
        r'^\d{8}_\d{6}': ('Samsung', 'Galaxy'),
        r'^DCIM_\d+': ('Generic', 'Camera'),
        r'^DSC_\d+': ('Nikon', 'DSLR'),
        r'^_DSC\d+': ('Sony', 'Camera'),
        r'^GoPro\d+': ('GoPro', 'Camera'),
        r'^DJI_\d+': ('DJI', 'Drone'),
        r'^IMG-\d{8}-WA': ('WhatsApp', 'Image'),
        r'^VID-\d{8}-WA': ('WhatsApp', 'Video'),
    }

    def __init__(self):
        """Initialise le détecteur."""
        pass

    def detect(
        self,
        exif_data: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        format_output: bool = True
    ) -> Tuple[str, str]:
        """
        Détecte la marque et le modèle de l'appareil.

        Args:
            exif_data: Données EXIF
            file_path: Chemin du fichier (pour détection par nom)
            format_output: Formater les noms pour l'affichage

        Returns:
            Tuple (make, model)
        """
        make = 'Unknown'
        model = 'Unknown'

        # 1. Extraction depuis EXIF
        if exif_data:
            exif_make = exif_data.get('Make', '')
            exif_model = exif_data.get('Model', '')

            if exif_make:
                make = str(exif_make).strip()
            if exif_model:
                model = str(exif_model).strip()

        # 2. Détection par nom de fichier si EXIF incomplet
        if (make == 'Unknown' or model == 'Unknown') and file_path:
            filename = os.path.basename(file_path)
            detected_make, detected_model = self._detect_from_filename(filename)

            if make == 'Unknown' and detected_make:
                make = detected_make
            if model == 'Unknown' and detected_model:
                model = detected_model

        # 3. Normalisation et formatage
        if format_output:
            make, model = self._format_names(make, model)

        return make, model

    def _detect_from_filename(self, filename: str) -> Tuple[str, str]:
        """Détecte le fabricant/modèle depuis le nom de fichier."""
        for pattern, (make, model) in self.FILENAME_PATTERNS.items():
            if re.match(pattern, filename, re.IGNORECASE):
                return make, model
        return '', ''

    def _format_names(self, make: str, model: str) -> Tuple[str, str]:
        """Formate et normalise les noms."""
        # Normaliser le fabricant
        make = make.strip().replace('_', ' ')
        if make in self.MAKE_MAPPING:
            make = self.MAKE_MAPPING[make]
        else:
            # Capitaliser correctement
            make = self._smart_capitalize(make)

        # Normaliser le modèle Samsung
        if make == 'Samsung':
            model = self._normalize_samsung_model(model)
        else:
            model = model.strip().replace('_', ' ')
            model = self._smart_capitalize(model)

        return make, model

    def _normalize_samsung_model(self, model: str) -> str:
        """Normalise les modèles Samsung."""
        model = model.strip()

        # Chercher une correspondance directe
        for prefix, friendly_name in self.SAMSUNG_MODELS.items():
            if model.startswith(prefix):
                return friendly_name

        return self._smart_capitalize(model)

    def _smart_capitalize(self, text: str) -> str:
        """Capitalisation intelligente préservant les acronymes."""
        if not text:
            return 'Unknown'

        words = text.split()
        result = []

        for word in words:
            # Préserver les acronymes (tout en majuscules, <= 4 caractères)
            if word.isupper() and len(word) <= 4:
                result.append(word)
            # Préserver les numéros de modèle
            elif re.match(r'^[A-Z]{1,2}\d+', word):
                result.append(word)
            else:
                result.append(word.capitalize())

        return ' '.join(result)


# Instance globale
_detector: Optional[CameraDetector] = None


def get_detector() -> CameraDetector:
    """Retourne l'instance globale du détecteur."""
    global _detector
    if _detector is None:
        _detector = CameraDetector()
    return _detector


def get_camera_info(
    exif_data: Optional[Dict[str, Any]] = None,
    file_path: Optional[str] = None,
    format_output: bool = True
) -> Tuple[str, str]:
    """
    Fonction utilitaire pour obtenir les infos appareil photo.

    Args:
        exif_data: Données EXIF
        file_path: Chemin du fichier
        format_output: Formater la sortie

    Returns:
        Tuple (make, model)
    """
    return get_detector().detect(exif_data, file_path, format_output)
