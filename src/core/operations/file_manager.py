"""
Module de gestion des fichiers.
Copie, déplacement et opérations de base.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileOperation:
    """Représente une opération sur un fichier."""
    operation_type: str  # 'copy', 'move', 'rename', 'delete'
    source: str
    destination: str
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.operation_type,
            'source': self.source,
            'destination': self.destination,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'error': self.error
        }


class FileManager:
    """Gestionnaire d'opérations sur les fichiers."""

    # Extensions supportées par catégorie
    EXTENSIONS = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
                  '.webp', '.jfif', '.jp2', '.avif', '.heic', '.heif'],
        'raw': ['.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng',
                '.3fr', '.raf', '.pef', '.srw', '.sr2', '.x3f', '.mef', '.iiq', '.rwl'],
        'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
                  '.3gp', '.m4v', '.mpg', '.mpeg', '.mts', '.ts', '.vob']
    }

    def __init__(self, rollback_enabled: bool = True):
        """
        Initialise le gestionnaire de fichiers.

        Args:
            rollback_enabled: Activer l'enregistrement pour rollback
        """
        self.rollback_enabled = rollback_enabled
        self._operations_history: List[FileOperation] = []
        self._current_session_id: Optional[str] = None

    def start_session(self) -> str:
        """Démarre une nouvelle session d'opérations."""
        self._current_session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._operations_history.clear()
        logger.info(f"Session démarrée: {self._current_session_id}")
        return self._current_session_id

    def copy_file(
        self,
        source: str,
        destination: str,
        preserve_metadata: bool = True,
        auto_rename: bool = True
    ) -> FileOperation:
        """
        Copie un fichier avec préservation des métadonnées.

        Args:
            source: Chemin source
            destination: Chemin destination
            preserve_metadata: Préserver les métadonnées
            auto_rename: Renommer automatiquement si conflit

        Returns:
            FileOperation avec le résultat
        """
        operation = FileOperation(
            operation_type='copy',
            source=source,
            destination=destination
        )

        try:
            # Vérifier le fichier source
            if not os.path.exists(source):
                raise FileNotFoundError(f"Fichier source inexistant: {source}")

            # Créer le répertoire de destination
            dest_dir = os.path.dirname(destination)
            os.makedirs(dest_dir, exist_ok=True)

            # Gérer les conflits
            final_dest = destination
            if os.path.exists(destination) and auto_rename:
                final_dest = self._get_unique_name(destination)
                operation.destination = final_dest

            # Copier le fichier
            if preserve_metadata:
                shutil.copy2(source, final_dest)
            else:
                shutil.copy(source, final_dest)

            operation.success = True
            logger.debug(f"Copié: {source} -> {final_dest}")

        except Exception as e:
            operation.success = False
            operation.error = str(e)
            logger.error(f"Erreur copie {source}: {e}")

        if self.rollback_enabled:
            self._operations_history.append(operation)

        return operation

    def move_file(
        self,
        source: str,
        destination: str,
        auto_rename: bool = True
    ) -> FileOperation:
        """
        Déplace un fichier.

        Args:
            source: Chemin source
            destination: Chemin destination
            auto_rename: Renommer automatiquement si conflit

        Returns:
            FileOperation avec le résultat
        """
        operation = FileOperation(
            operation_type='move',
            source=source,
            destination=destination
        )

        try:
            # Vérifier le fichier source
            if not os.path.exists(source):
                raise FileNotFoundError(f"Fichier source inexistant: {source}")

            # Créer le répertoire de destination
            dest_dir = os.path.dirname(destination)
            os.makedirs(dest_dir, exist_ok=True)

            # Gérer les conflits
            final_dest = destination
            if os.path.exists(destination) and auto_rename:
                final_dest = self._get_unique_name(destination)
                operation.destination = final_dest

            # Déplacer le fichier
            shutil.move(source, final_dest)

            operation.success = True
            logger.debug(f"Déplacé: {source} -> {final_dest}")

        except Exception as e:
            operation.success = False
            operation.error = str(e)
            logger.error(f"Erreur déplacement {source}: {e}")

        if self.rollback_enabled:
            self._operations_history.append(operation)

        return operation

    def _get_unique_name(self, path: str) -> str:
        """Génère un nom unique pour éviter les conflits."""
        if not os.path.exists(path):
            return path

        base, ext = os.path.splitext(path)
        counter = 1

        while True:
            new_path = f"{base}_{counter}{ext}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def list_files(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
        include_images: bool = True,
        include_raw: bool = True,
        include_videos: bool = False
    ) -> List[str]:
        """
        Liste les fichiers média dans un répertoire.

        Args:
            directory: Répertoire à scanner
            extensions: Liste d'extensions (ou None pour auto)
            recursive: Parcourir récursivement
            include_images: Inclure les images
            include_raw: Inclure les RAW
            include_videos: Inclure les vidéos

        Returns:
            Liste des chemins de fichiers
        """
        if extensions is None:
            extensions = []
            if include_images:
                extensions.extend(self.EXTENSIONS['image'])
            if include_raw:
                extensions.extend(self.EXTENSIONS['raw'])
            if include_videos:
                extensions.extend(self.EXTENSIONS['video'])

        extensions = [ext.lower() for ext in extensions]
        files = []

        if recursive:
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    if any(filename.lower().endswith(ext) for ext in extensions):
                        files.append(os.path.join(root, filename))
        else:
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                if os.path.isfile(path):
                    if any(item.lower().endswith(ext) for ext in extensions):
                        files.append(path)

        return sorted(files)

    def get_operations_history(self) -> List[FileOperation]:
        """Retourne l'historique des opérations."""
        return self._operations_history.copy()

    def rollback_last(self) -> bool:
        """Annule la dernière opération."""
        if not self._operations_history:
            return False

        operation = self._operations_history.pop()

        if operation.operation_type == 'copy':
            # Supprimer le fichier copié
            try:
                if os.path.exists(operation.destination):
                    os.remove(operation.destination)
                return True
            except Exception as e:
                logger.error(f"Erreur rollback copie: {e}")
                return False

        elif operation.operation_type == 'move':
            # Déplacer le fichier à son emplacement original
            try:
                if os.path.exists(operation.destination):
                    shutil.move(operation.destination, operation.source)
                return True
            except Exception as e:
                logger.error(f"Erreur rollback déplacement: {e}")
                return False

        return False

    def rollback_all(self) -> int:
        """Annule toutes les opérations de la session."""
        count = 0
        while self._operations_history:
            if self.rollback_last():
                count += 1
        return count


# Instance globale
_manager: Optional[FileManager] = None


def get_manager() -> FileManager:
    """Retourne l'instance globale du gestionnaire."""
    global _manager
    if _manager is None:
        _manager = FileManager()
    return _manager


def copy_file(source: str, destination: str, **kwargs) -> bool:
    """Fonction utilitaire pour copier un fichier."""
    result = get_manager().copy_file(source, destination, **kwargs)
    return result.success


def move_file(source: str, destination: str, **kwargs) -> bool:
    """Fonction utilitaire pour déplacer un fichier."""
    result = get_manager().move_file(source, destination, **kwargs)
    return result.success
