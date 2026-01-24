"""
Module d'organisation intelligente des fichiers média.
Organisation par date, appareil photo, localisation.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from ..metadata import get_exif_data, extract_date, get_camera_info, get_gps_coordinates
from ..metadata.gps_processor import get_processor as get_gps_processor
from .file_manager import FileManager

logger = logging.getLogger(__name__)


@dataclass
class OrganizationOptions:
    """Options d'organisation des fichiers."""
    organize_by_date: bool = True
    organize_by_camera: bool = False
    organize_by_location: bool = False
    multilayer: bool = False
    criteria_order: List[str] = field(default_factory=lambda: ['date', 'camera', 'location'])
    copy_not_move: bool = True
    date_format: str = "year/month/day"
    max_distance_km: float = 1.0
    use_geocoding: bool = True
    auto_rename: bool = True
    skip_existing: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrganizationOptions':
        """Crée une instance depuis un dictionnaire."""
        return cls(
            organize_by_date=data.get('organize_by_date', True),
            organize_by_camera=data.get('organize_by_camera', False),
            organize_by_location=data.get('organize_by_location', False),
            multilayer=data.get('multilayer', False),
            criteria_order=data.get('criteria_order', ['date', 'camera', 'location']),
            copy_not_move=data.get('copy_not_move', True),
            date_format=data.get('date_format', 'year/month/day'),
            max_distance_km=data.get('max_distance_km', 1.0),
            use_geocoding=data.get('use_geocoding', True),
            auto_rename=data.get('auto_rename', True),
            skip_existing=data.get('skip_existing', False)
        )


@dataclass
class OrganizationResult:
    """Résultat d'une organisation."""
    total: int = 0
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)
    operations: List[Dict] = field(default_factory=list)


class SmartOrganizer:
    """Organiseur intelligent de fichiers média."""

    DATE_FORMATS = {
        'year/month/day': '{year}/{month}/{year}_{month}_{day}',
        'year/month': '{year}/{year}_{month}',
        'year': '{year}',
        'year_month_day': '{year}_{month}_{day}',
        'year_month': '{year}_{month}',
    }

    def __init__(self, file_manager: Optional[FileManager] = None):
        """
        Initialise l'organiseur.

        Args:
            file_manager: Gestionnaire de fichiers (créé si non fourni)
        """
        self.file_manager = file_manager or FileManager()
        self.gps_processor = get_gps_processor()
        self._cancel_requested = False

    def organize(
        self,
        file_paths: List[str],
        target_dir: str,
        options: OrganizationOptions,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> OrganizationResult:
        """
        Organise les fichiers selon les options spécifiées.

        Args:
            file_paths: Liste des fichiers à organiser
            target_dir: Répertoire de destination
            options: Options d'organisation
            progress_callback: Callback de progression (current, total, message)

        Returns:
            OrganizationResult avec les statistiques
        """
        self._cancel_requested = False
        result = OrganizationResult(total=len(file_paths))

        if not file_paths:
            return result

        # Créer le répertoire de destination
        os.makedirs(target_dir, exist_ok=True)

        # Démarrer une session
        self.file_manager.start_session()

        # Traiter chaque fichier
        for i, file_path in enumerate(file_paths):
            if self._cancel_requested:
                logger.info("Organisation annulée par l'utilisateur")
                break

            # Callback de progression
            if progress_callback:
                progress_callback(i + 1, len(file_paths), os.path.basename(file_path))

            try:
                success = self._process_file(file_path, target_dir, options)
                if success:
                    result.processed += 1
                else:
                    result.skipped += 1
            except Exception as e:
                result.errors += 1
                result.error_messages.append(f"{os.path.basename(file_path)}: {str(e)}")
                logger.error(f"Erreur traitement {file_path}: {e}")

        return result

    def _process_file(
        self,
        file_path: str,
        target_dir: str,
        options: OrganizationOptions
    ) -> bool:
        """Traite un seul fichier."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier inexistant: {file_path}")

        # Extraire les métadonnées
        exif_data = get_exif_data(file_path)
        date_taken, date_origin = extract_date(file_path, exif_data, return_origin=True)
        make, model = get_camera_info(exif_data, file_path)
        gps_coords = get_gps_coordinates(file_path)

        # Construire le chemin de destination
        current_path = target_dir

        # Déterminer l'ordre des critères
        if options.multilayer:
            criteria = options.criteria_order
        else:
            # Mode non-multicouche: un seul critère actif
            if options.organize_by_date:
                criteria = ['date']
            elif options.organize_by_camera:
                criteria = ['camera']
            elif options.organize_by_location:
                criteria = ['location']
            else:
                criteria = []

        # Appliquer chaque critère
        for criterion in criteria:
            if criterion == 'date' and options.organize_by_date:
                current_path = self._apply_date_organization(
                    current_path, date_taken, options.date_format
                )

            elif criterion == 'camera' and options.organize_by_camera:
                current_path = self._apply_camera_organization(
                    current_path, make, model
                )

            elif criterion == 'location' and options.organize_by_location:
                current_path = self._apply_location_organization(
                    current_path, gps_coords, options.use_geocoding
                )

        # Déterminer le chemin final
        filename = os.path.basename(file_path)
        dest_path = os.path.join(current_path, filename)

        # Vérifier si on doit ignorer les existants
        if options.skip_existing and os.path.exists(dest_path):
            return False

        # Copier ou déplacer
        if options.copy_not_move:
            operation = self.file_manager.copy_file(
                file_path, dest_path, auto_rename=options.auto_rename
            )
        else:
            operation = self.file_manager.move_file(
                file_path, dest_path, auto_rename=options.auto_rename
            )

        return operation.success

    def _apply_date_organization(
        self,
        base_path: str,
        date_taken: Optional[datetime],
        date_format: str
    ) -> str:
        """Applique l'organisation par date."""
        if not date_taken:
            return os.path.join(base_path, "Sans date")

        # Formater la date
        year = str(date_taken.year)
        month = f"{date_taken.month:02d}"
        day = f"{date_taken.day:02d}"

        # Construire le chemin selon le format
        if date_format == "year/month/day":
            path = os.path.join(base_path, year, month, f"{year}_{month}_{day}")
        elif date_format == "year/month":
            path = os.path.join(base_path, year, f"{year}_{month}")
        elif date_format == "year":
            path = os.path.join(base_path, year)
        elif date_format == "year_month_day":
            path = os.path.join(base_path, f"{year}_{month}_{day}")
        elif date_format == "year_month":
            path = os.path.join(base_path, f"{year}_{month}")
        else:
            path = os.path.join(base_path, year, month, f"{year}_{month}_{day}")

        os.makedirs(path, exist_ok=True)
        return path

    def _apply_camera_organization(
        self,
        base_path: str,
        make: str,
        model: str
    ) -> str:
        """Applique l'organisation par appareil photo."""
        if make == 'Unknown' and model == 'Unknown':
            camera_name = "Appareil inconnu"
        else:
            camera_name = f"{make} {model}".strip()

        # Nettoyer le nom pour le système de fichiers
        camera_name = self._sanitize_dirname(camera_name)

        path = os.path.join(base_path, camera_name)
        os.makedirs(path, exist_ok=True)
        return path

    def _apply_location_organization(
        self,
        base_path: str,
        gps_coords: Tuple[Optional[float], Optional[float]],
        use_geocoding: bool
    ) -> str:
        """Applique l'organisation par localisation."""
        lat, lon = gps_coords

        if lat is None or lon is None:
            location_name = "Sans localisation GPS"
        elif use_geocoding:
            location_name = self.gps_processor.get_location_name(lat, lon)
        else:
            location_name = f"Lat_{lat:.4f}_Lon_{lon:.4f}"

        # Nettoyer le nom pour le système de fichiers
        location_name = self._sanitize_dirname(location_name)

        path = os.path.join(base_path, location_name)
        os.makedirs(path, exist_ok=True)
        return path

    def _sanitize_dirname(self, name: str) -> str:
        """Nettoie un nom pour être utilisé comme nom de dossier."""
        # Caractères interdits sous Windows
        forbidden = '<>:"/\\|?*'
        for char in forbidden:
            name = name.replace(char, '_')

        # Limiter la longueur
        if len(name) > 80:
            name = name[:80]

        return name.strip()

    def cancel(self):
        """Demande l'annulation de l'organisation en cours."""
        self._cancel_requested = True

    def rollback(self) -> int:
        """Annule toutes les opérations de la session."""
        return self.file_manager.rollback_all()


# Instance globale
_organizer: Optional[SmartOrganizer] = None


def get_organizer() -> SmartOrganizer:
    """Retourne l'instance globale de l'organiseur."""
    global _organizer
    if _organizer is None:
        _organizer = SmartOrganizer()
    return _organizer


def organize_files(
    file_paths: List[str],
    target_dir: str,
    options: Dict[str, Any],
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour organiser des fichiers.

    Args:
        file_paths: Liste des fichiers
        target_dir: Répertoire de destination
        options: Options d'organisation (dictionnaire)
        progress_callback: Callback de progression

    Returns:
        Dictionnaire des résultats
    """
    organizer = get_organizer()
    opts = OrganizationOptions.from_dict(options)
    result = organizer.organize(file_paths, target_dir, opts, progress_callback)

    return {
        'total': result.total,
        'processed': result.processed,
        'skipped': result.skipped,
        'errors': result.errors,
        'error_messages': result.error_messages
    }
