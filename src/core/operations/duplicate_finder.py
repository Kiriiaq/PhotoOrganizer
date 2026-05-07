# -*- coding: utf-8 -*-
"""
Module de détection des fichiers en double.
Utilise le hashing pour identifier les doublons.

Supports SHA-256 (default), SHA-1, MD5, and BLAKE3 algorithms.
Optimized with 4MB chunk size for large files and optional hash caching.
"""

import hashlib
import logging
import os
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# Try to import blake3 for faster hashing
try:
    import blake3
    BLAKE3_AVAILABLE = True
except ImportError:
    BLAKE3_AVAILABLE = False

logger = logging.getLogger(__name__)

# Constants
DEFAULT_ALGORITHM = 'sha256'
DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB
QUICK_HASH_CHUNK_SIZE = 64 * 1024  # 64 KB
SUPPORTED_ALGORITHMS = ['md5', 'sha1', 'sha256', 'blake3']


@dataclass
class DuplicateGroup:
    """Groupe de fichiers identiques."""
    hash_value: str
    files: List[str] = field(default_factory=list)
    file_size: int = 0

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def wasted_space(self) -> int:
        """Espace gaspillé par les doublons."""
        return self.file_size * (self.count - 1) if self.count > 1 else 0


@dataclass
class DuplicateResult:
    """Résultat de la recherche de doublons."""
    total_files: int = 0
    unique_files: int = 0
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    total_wasted_space: int = 0
    scan_time: float = 0.0

    @property
    def duplicate_count(self) -> int:
        """Nombre total de fichiers en double."""
        return sum(g.count - 1 for g in self.duplicate_groups)


class DuplicateFinder:
    """
    Détecteur de fichiers en double.

    Features:
    - Multi-algorithm support (SHA-256 default, SHA-1, MD5, BLAKE3)
    - Optimized 4MB chunk reading for large files
    - Quick hash filtering (beginning + middle + end)
    - Optional hash caching for performance
    - Multi-threaded hashing support
    - Cancellation support
    """

    def __init__(
        self,
        algorithm: str = DEFAULT_ALGORITHM,
        quick_mode: bool = True,
        min_size: int = 0,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        quick_chunk_size: int = QUICK_HASH_CHUNK_SIZE,
        use_cache: bool = True,
        max_workers: int = 0
    ):
        """
        Initialise le détecteur de doublons.

        Args:
            algorithm: Algorithme de hash ('md5', 'sha1', 'sha256', 'blake3')
            quick_mode: Mode rapide (hash partiel d'abord)
            min_size: Taille minimale des fichiers à scanner (octets)
            chunk_size: Taille des chunks pour la lecture (octets)
            quick_chunk_size: Taille des chunks pour le hash rapide (octets)
            use_cache: Utiliser le cache de hash
            max_workers: Nombre de workers pour le hashing parallèle (0 = auto)
        """
        # Validate algorithm
        algorithm = algorithm.lower()
        if algorithm not in SUPPORTED_ALGORITHMS:
            logger.warning(f"Unsupported algorithm '{algorithm}', using {DEFAULT_ALGORITHM}")
            algorithm = DEFAULT_ALGORITHM

        if algorithm == 'blake3' and not BLAKE3_AVAILABLE:
            logger.warning("BLAKE3 not available, falling back to SHA-256")
            algorithm = 'sha256'

        self.algorithm = algorithm
        self.quick_mode = quick_mode
        self.min_size = min_size
        self.chunk_size = chunk_size
        self.quick_chunk_size = quick_chunk_size
        self.use_cache = use_cache
        self.max_workers = max_workers if max_workers > 0 else (os.cpu_count() or 4)

        self._cancel_requested = False
        self._lock = threading.Lock()

        # Initialize cache if enabled
        self._cache = None
        if self.use_cache:
            try:
                from src.utils.hash_cache import get_hash_cache
                self._cache = get_hash_cache()
            except ImportError:
                logger.debug("Hash cache not available")

    def _create_hasher(self):
        """Create a new hasher instance for the configured algorithm."""
        if self.algorithm == 'blake3':
            return blake3.blake3()
        return hashlib.new(self.algorithm)

    def find_duplicates(
        self,
        file_paths: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> DuplicateResult:
        """
        Recherche les fichiers en double.

        Args:
            file_paths: Liste des fichiers à analyser
            progress_callback: Callback de progression (current, total, message)

        Returns:
            DuplicateResult avec les groupes de doublons
        """
        import time
        start_time = time.time()

        self._cancel_requested = False
        result = DuplicateResult(total_files=len(file_paths))

        if not file_paths:
            return result

        # Stage 1: Group by size
        size_groups = self._group_by_size(file_paths, progress_callback)

        if self._cancel_requested:
            return result

        # Stage 2: Quick hash filter for same-size groups
        if self.quick_mode:
            hash_candidates = self._quick_hash_filter(size_groups, progress_callback)
        else:
            hash_candidates = size_groups

        if self._cancel_requested:
            return result

        # Stage 3: Full hash to confirm duplicates
        duplicate_groups = self._full_hash_check(hash_candidates, progress_callback)

        if self._cancel_requested:
            return result

        # Build result
        result.duplicate_groups = duplicate_groups
        result.unique_files = len(file_paths) - sum(g.count - 1 for g in duplicate_groups)
        result.total_wasted_space = sum(g.wasted_space for g in duplicate_groups)
        result.scan_time = time.time() - start_time

        return result

    def _group_by_size(
        self,
        file_paths: List[str],
        progress_callback: Optional[Callable]
    ) -> Dict[int, List[str]]:
        """Groupe les fichiers par taille."""
        size_groups: Dict[int, List[str]] = defaultdict(list)

        for i, file_path in enumerate(file_paths):
            if self._cancel_requested:
                break

            if progress_callback:
                progress_callback(i + 1, len(file_paths), "Analyse des tailles...")

            try:
                size = os.path.getsize(file_path)
                if size >= self.min_size:
                    size_groups[size].append(file_path)
            except OSError as e:
                logger.debug(f"Erreur lecture taille {file_path}: {e}")

        # Filter groups with only one file
        return {size: files for size, files in size_groups.items() if len(files) > 1}

    def _quick_hash_filter(
        self,
        size_groups: Dict[int, List[str]],
        progress_callback: Optional[Callable]
    ) -> Dict[int, List[str]]:
        """Filtre avec un hash rapide (début + milieu + fin du fichier)."""
        filtered_groups: Dict[int, List[str]] = {}

        total_files = sum(len(files) for files in size_groups.values())
        processed = 0

        for size, files in size_groups.items():
            if self._cancel_requested:
                break

            quick_hash_groups: Dict[str, List[str]] = defaultdict(list)

            for file_path in files:
                if self._cancel_requested:
                    break

                if progress_callback:
                    processed += 1
                    progress_callback(processed, total_files, "Hash rapide...")

                quick_hash = self._calculate_quick_hash(file_path, size)
                if quick_hash:
                    quick_hash_groups[quick_hash].append(file_path)

            # Keep only groups with multiple files
            for qhash, files_group in quick_hash_groups.items():
                if len(files_group) > 1:
                    if size not in filtered_groups:
                        filtered_groups[size] = []
                    filtered_groups[size].extend(files_group)

        return filtered_groups

    def _full_hash_check(
        self,
        size_groups: Dict[int, List[str]],
        progress_callback: Optional[Callable]
    ) -> List[DuplicateGroup]:
        """Calcule le hash complet pour confirmer les doublons."""
        duplicate_groups: List[DuplicateGroup] = []

        total_files = sum(len(files) for files in size_groups.values())
        processed = 0

        for size, files in size_groups.items():
            if self._cancel_requested:
                break

            hash_groups: Dict[str, List[str]] = defaultdict(list)

            # Use thread pool for parallel hashing of large files
            if len(files) > 2 and size > 1024 * 1024:  # More than 2 files and > 1MB
                with ThreadPoolExecutor(max_workers=min(self.max_workers, len(files))) as executor:
                    future_to_file = {
                        executor.submit(self._calculate_full_hash, fp): fp
                        for fp in files
                    }

                    for future in as_completed(future_to_file):
                        if self._cancel_requested:
                            break

                        file_path = future_to_file[future]
                        if progress_callback:
                            with self._lock:
                                processed += 1
                                progress_callback(processed, total_files, "Hash complet...")

                        try:
                            file_hash = future.result()
                            if file_hash:
                                hash_groups[file_hash].append(file_path)
                        except Exception as e:
                            logger.debug(f"Error hashing {file_path}: {e}")
            else:
                # Sequential for small number of files
                for file_path in files:
                    if self._cancel_requested:
                        break

                    if progress_callback:
                        processed += 1
                        progress_callback(processed, total_files, "Hash complet...")

                    file_hash = self._calculate_full_hash(file_path)
                    if file_hash:
                        hash_groups[file_hash].append(file_path)

            # Create duplicate groups
            for hash_value, group_files in hash_groups.items():
                if len(group_files) > 1:
                    duplicate_groups.append(DuplicateGroup(
                        hash_value=hash_value,
                        files=sorted(group_files),
                        file_size=size
                    ))

        return duplicate_groups

    def _calculate_quick_hash(self, file_path: str, file_size: int) -> Optional[str]:
        """
        Calcule un hash rapide (début + milieu + fin).

        Uses cache if available.
        """
        # Check cache first
        if self._cache:
            cached = self._cache.get_quick_hash(file_path)
            if cached:
                return cached

        try:
            chunk_size = min(self.quick_chunk_size, file_size // 3) if file_size > self.quick_chunk_size * 3 else file_size

            hasher = self._create_hasher()

            with open(file_path, 'rb') as f:
                # Beginning
                hasher.update(f.read(chunk_size))

                # Middle
                if file_size > chunk_size * 2:
                    f.seek(file_size // 2)
                    hasher.update(f.read(chunk_size))

                # End
                if file_size > chunk_size:
                    f.seek(-chunk_size, 2)
                    hasher.update(f.read(chunk_size))

            quick_hash = hasher.hexdigest()

            # Store in cache
            if self._cache:
                self._cache.set_quick_hash(file_path, quick_hash, self.algorithm)

            return quick_hash

        except Exception as e:
            logger.debug(f"Erreur hash rapide {file_path}: {e}")
            return None

    def _calculate_full_hash(self, file_path: str) -> Optional[str]:
        """
        Calcule le hash complet d'un fichier.

        Uses optimized 4MB chunk reading and cache if available.
        """
        # Check cache first
        if self._cache:
            cached = self._cache.get_full_hash(file_path)
            if cached:
                return cached

        try:
            hasher = self._create_hasher()

            with open(file_path, 'rb') as f:
                # Read in chunks for memory efficiency
                for chunk in iter(lambda: f.read(self.chunk_size), b''):
                    hasher.update(chunk)

            full_hash = hasher.hexdigest()

            # Store in cache
            if self._cache:
                self._cache.set_full_hash(file_path, full_hash, self.algorithm)

            return full_hash

        except Exception as e:
            logger.debug(f"Erreur hash complet {file_path}: {e}")
            return None

    def calculate_hash(self, file_path: str) -> Optional[str]:
        """
        Calculate the full hash of a single file.

        Public method for external use (e.g., verification before delete).

        Args:
            file_path: Path to the file

        Returns:
            Hash string or None on error
        """
        return self._calculate_full_hash(file_path)

    def verify_hash(self, file_path: str, expected_hash: str) -> bool:
        """
        Verify that a file has the expected hash.

        Args:
            file_path: Path to the file
            expected_hash: Expected hash value

        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = self._calculate_full_hash(file_path)
        return actual_hash == expected_hash

    def cancel(self):
        """Annule la recherche en cours."""
        self._cancel_requested = True

    def clear_cache(self):
        """Clear the hash cache."""
        if self._cache:
            self._cache.clear()

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Formate une taille en bytes en format lisible."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def is_algorithm_available(algorithm: str) -> bool:
        """Check if a hash algorithm is available."""
        algorithm = algorithm.lower()
        if algorithm == 'blake3':
            return BLAKE3_AVAILABLE
        return algorithm in ['md5', 'sha1', 'sha256']

    @staticmethod
    def get_available_algorithms() -> List[str]:
        """Get list of available hash algorithms."""
        algorithms = ['md5', 'sha1', 'sha256']
        if BLAKE3_AVAILABLE:
            algorithms.append('blake3')
        return algorithms


# Global instance
_finder: Optional[DuplicateFinder] = None


def get_finder(
    algorithm: str = DEFAULT_ALGORITHM,
    quick_mode: bool = True,
    use_cache: bool = True
) -> DuplicateFinder:
    """
    Retourne l'instance globale du détecteur.

    Args:
        algorithm: Hash algorithm to use
        quick_mode: Use quick hash filtering
        use_cache: Use hash caching

    Returns:
        DuplicateFinder instance
    """
    global _finder
    if _finder is None:
        _finder = DuplicateFinder(
            algorithm=algorithm,
            quick_mode=quick_mode,
            use_cache=use_cache
        )
    return _finder


def reset_finder():
    """Reset the global finder instance."""
    global _finder
    _finder = None


def find_duplicates(
    file_paths: List[str],
    progress_callback: Optional[Callable] = None,
    algorithm: str = DEFAULT_ALGORITHM
) -> Dict[str, any]:
    """
    Fonction utilitaire pour trouver les doublons.

    Args:
        file_paths: Liste des fichiers
        progress_callback: Callback de progression
        algorithm: Hash algorithm to use

    Returns:
        Dictionnaire des résultats
    """
    finder = get_finder(algorithm=algorithm)
    result = finder.find_duplicates(file_paths, progress_callback)

    return {
        'total_files': result.total_files,
        'unique_files': result.unique_files,
        'duplicate_count': result.duplicate_count,
        'wasted_space': result.total_wasted_space,
        'wasted_space_formatted': DuplicateFinder.format_size(result.total_wasted_space),
        'scan_time': result.scan_time,
        'groups': [
            {
                'hash': g.hash_value,
                'files': g.files,
                'size': g.file_size,
                'count': g.count
            }
            for g in result.duplicate_groups
        ]
    }
