"""
Module de cache pour les métadonnées.
Améliore les performances en évitant les extractions répétées.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrée de cache."""
    data: Dict[str, Any]
    file_mtime: float
    created_at: str
    file_size: int


class MetadataCache:
    """Cache pour les métadonnées des fichiers."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl_hours: int = 24,
        max_size_mb: int = 100
    ):
        """
        Initialise le cache.

        Args:
            cache_dir: Répertoire du cache
            ttl_hours: Durée de vie des entrées en heures
            max_size_mb: Taille maximale du cache en Mo
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = self._get_default_cache_dir()

        self.ttl = timedelta(hours=ttl_hours)
        self.max_size = max_size_mb * 1024 * 1024

        # Cache en mémoire
        self._memory_cache: Dict[str, CacheEntry] = {}

        # Statistiques
        self._hits = 0
        self._misses = 0

        # Créer le répertoire de cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_cache_dir(self) -> Path:
        """Retourne le répertoire de cache par défaut."""
        if os.name == 'nt':
            base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            return Path(base) / 'PhotoOrganizer' / 'cache'
        else:
            return Path.home() / '.cache' / 'PhotoOrganizer'

    def _get_cache_key(self, file_path: str) -> str:
        """Génère une clé de cache unique pour un fichier."""
        return hashlib.md5(file_path.encode()).hexdigest()

    def _get_cache_file(self, cache_key: str) -> Path:
        """Retourne le chemin du fichier de cache."""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les métadonnées depuis le cache.

        Args:
            file_path: Chemin du fichier

        Returns:
            Métadonnées ou None si non trouvé/invalide
        """
        cache_key = self._get_cache_key(file_path)

        # Vérifier le cache mémoire d'abord
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if self._is_valid(entry, file_path):
                self._hits += 1
                return entry.data

        # Vérifier le cache disque
        cache_file = self._get_cache_file(cache_key)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    entry = CacheEntry(**data)

                    if self._is_valid(entry, file_path):
                        # Mettre en cache mémoire
                        self._memory_cache[cache_key] = entry
                        self._hits += 1
                        return entry.data

            except Exception as e:
                logger.debug(f"Erreur lecture cache: {e}")

        self._misses += 1
        return None

    def set(self, file_path: str, metadata: Dict[str, Any]):
        """
        Stocke les métadonnées dans le cache.

        Args:
            file_path: Chemin du fichier
            metadata: Métadonnées à stocker
        """
        try:
            stat = os.stat(file_path)
            entry = CacheEntry(
                data=metadata,
                file_mtime=stat.st_mtime,
                created_at=datetime.now().isoformat(),
                file_size=stat.st_size
            )

            cache_key = self._get_cache_key(file_path)

            # Cache mémoire
            self._memory_cache[cache_key] = entry

            # Cache disque
            cache_file = self._get_cache_file(cache_key)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'data': entry.data,
                    'file_mtime': entry.file_mtime,
                    'created_at': entry.created_at,
                    'file_size': entry.file_size
                }, f)

        except Exception as e:
            logger.debug(f"Erreur écriture cache: {e}")

    def _is_valid(self, entry: CacheEntry, file_path: str) -> bool:
        """Vérifie si une entrée de cache est valide."""
        try:
            # Vérifier l'expiration
            created = datetime.fromisoformat(entry.created_at)
            if datetime.now() - created > self.ttl:
                return False

            # Vérifier si le fichier a été modifié
            stat = os.stat(file_path)
            if stat.st_mtime != entry.file_mtime:
                return False
            if stat.st_size != entry.file_size:
                return False

            return True

        except Exception:
            return False

    def invalidate(self, file_path: str):
        """Invalide le cache pour un fichier."""
        cache_key = self._get_cache_key(file_path)

        # Supprimer du cache mémoire
        self._memory_cache.pop(cache_key, None)

        # Supprimer du cache disque
        cache_file = self._get_cache_file(cache_key)
        if cache_file.exists():
            cache_file.unlink()

    def clear(self):
        """Vide complètement le cache."""
        self._memory_cache.clear()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception:
                pass

        self._hits = 0
        self._misses = 0

    def cleanup_expired(self) -> int:
        """
        Supprime les entrées expirées.

        Returns:
            Nombre d'entrées supprimées
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    created = datetime.fromisoformat(data['created_at'])

                    if datetime.now() - created > self.ttl:
                        cache_file.unlink()
                        count += 1
            except Exception:
                # Fichier corrompu, supprimer
                cache_file.unlink()
                count += 1

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        # Calculer la taille du cache
        cache_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))

        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'memory_entries': len(self._memory_cache),
            'disk_size': cache_size,
            'disk_size_formatted': self._format_size(cache_size)
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Formate une taille en format lisible."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# Instance globale
_cache: Optional[MetadataCache] = None


def get_cache() -> MetadataCache:
    """Retourne l'instance globale du cache."""
    global _cache
    if _cache is None:
        _cache = MetadataCache()
    return _cache
