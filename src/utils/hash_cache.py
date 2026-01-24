# -*- coding: utf-8 -*-
"""
Persistent hash cache for duplicate detection.

This module provides a specialized cache for file hashes, optimized for
the duplicate detection workflow with support for quick hashes and full hashes.
"""

import os
import json
import hashlib
import logging
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class HashCacheEntry:
    """
    Cache entry for file hash data.

    Attributes:
        file_path: Absolute path to the file
        file_size: Size of the file in bytes
        file_mtime: Modification time of the file
        quick_hash: Quick hash (partial file hash)
        full_hash: Full file hash
        algorithm: Hash algorithm used
        created_at: Cache entry creation timestamp
    """
    file_path: str
    file_size: int
    file_mtime: float
    quick_hash: Optional[str] = None
    full_hash: Optional[str] = None
    algorithm: str = "sha256"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class HashCache:
    """
    Persistent hash cache with SQLite backend.

    Features:
    - Two-tier caching (memory + SQLite)
    - Validation based on file modification time and size
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - Statistics tracking
    """

    DB_SCHEMA = """
        CREATE TABLE IF NOT EXISTS hash_cache (
            file_path TEXT PRIMARY KEY,
            file_size INTEGER NOT NULL,
            file_mtime REAL NOT NULL,
            quick_hash TEXT,
            full_hash TEXT,
            algorithm TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_file_size ON hash_cache(file_size);
        CREATE INDEX IF NOT EXISTS idx_full_hash ON hash_cache(full_hash);
        CREATE INDEX IF NOT EXISTS idx_created_at ON hash_cache(created_at);
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl_days: int = 7,
        max_memory_entries: int = 10000
    ):
        """
        Initialize the hash cache.

        Args:
            cache_dir: Directory for the cache database (auto-detected if None)
            ttl_days: Time-to-live for cache entries in days
            max_memory_entries: Maximum entries in memory cache
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = self._get_default_cache_dir()

        self.ttl = timedelta(days=ttl_days)
        self.max_memory_entries = max_memory_entries

        # Memory cache (LRU-like)
        self._memory_cache: Dict[str, HashCacheEntry] = {}
        self._access_order: List[str] = []

        # Statistics
        self._hits = 0
        self._misses = 0
        self._quick_hits = 0
        self._full_hits = 0

        # Thread safety
        self._lock = threading.RLock()

        # Initialize database
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.cache_dir / "hash_cache.db"
        self._init_database()

    def _get_default_cache_dir(self) -> Path:
        """Get the default cache directory based on platform."""
        if os.name == 'nt':
            base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            return Path(base) / 'PhotoOrganizer' / 'hash_cache'
        else:
            return Path.home() / '.cache' / 'PhotoOrganizer' / 'hash_cache'

    def _init_database(self):
        """Initialize the SQLite database."""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.executescript(self.DB_SCHEMA)
        except Exception as e:
            logger.error(f"Failed to initialize hash cache database: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(str(self._db_path), timeout=30)

    def _is_valid(self, entry: HashCacheEntry, file_path: str) -> bool:
        """Check if a cache entry is still valid."""
        try:
            # Check TTL
            created = datetime.fromisoformat(entry.created_at)
            if datetime.now() - created > self.ttl:
                return False

            # Check if file has changed
            stat = os.stat(file_path)
            if stat.st_mtime != entry.file_mtime:
                return False
            if stat.st_size != entry.file_size:
                return False

            return True

        except Exception:
            return False

    def _update_access_order(self, file_path: str):
        """Update LRU access order."""
        if file_path in self._access_order:
            self._access_order.remove(file_path)
        self._access_order.append(file_path)

        # Evict old entries if over limit
        while len(self._memory_cache) > self.max_memory_entries:
            if self._access_order:
                oldest = self._access_order.pop(0)
                self._memory_cache.pop(oldest, None)

    def get_quick_hash(self, file_path: str) -> Optional[str]:
        """
        Get quick hash from cache.

        Args:
            file_path: Path to the file

        Returns:
            Quick hash or None if not cached/invalid
        """
        entry = self._get_entry(file_path)
        if entry and entry.quick_hash:
            self._quick_hits += 1
            return entry.quick_hash
        return None

    def get_full_hash(self, file_path: str) -> Optional[str]:
        """
        Get full hash from cache.

        Args:
            file_path: Path to the file

        Returns:
            Full hash or None if not cached/invalid
        """
        entry = self._get_entry(file_path)
        if entry and entry.full_hash:
            self._full_hits += 1
            return entry.full_hash
        return None

    def get(self, file_path: str) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """
        Get both quick and full hash from cache.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (quick_hash, full_hash) or None if not cached/invalid
        """
        entry = self._get_entry(file_path)
        if entry:
            return (entry.quick_hash, entry.full_hash)
        return None

    def _get_entry(self, file_path: str) -> Optional[HashCacheEntry]:
        """Get cache entry for a file."""
        with self._lock:
            # Check memory cache first
            if file_path in self._memory_cache:
                entry = self._memory_cache[file_path]
                if self._is_valid(entry, file_path):
                    self._hits += 1
                    self._update_access_order(file_path)
                    return entry
                else:
                    # Invalid entry, remove from memory
                    del self._memory_cache[file_path]

            # Check database
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT * FROM hash_cache WHERE file_path = ?",
                        (file_path,)
                    )
                    row = cursor.fetchone()

                    if row:
                        entry = HashCacheEntry(
                            file_path=row[0],
                            file_size=row[1],
                            file_mtime=row[2],
                            quick_hash=row[3],
                            full_hash=row[4],
                            algorithm=row[5],
                            created_at=row[6]
                        )

                        if self._is_valid(entry, file_path):
                            # Add to memory cache
                            self._memory_cache[file_path] = entry
                            self._update_access_order(file_path)
                            self._hits += 1
                            return entry
                        else:
                            # Invalid entry, remove from database
                            conn.execute(
                                "DELETE FROM hash_cache WHERE file_path = ?",
                                (file_path,)
                            )

            except Exception as e:
                logger.debug(f"Error reading from hash cache: {e}")

            self._misses += 1
            return None

    def set_quick_hash(self, file_path: str, quick_hash: str, algorithm: str = "sha256"):
        """
        Store a quick hash in the cache.

        Args:
            file_path: Path to the file
            quick_hash: The quick hash value
            algorithm: Hash algorithm used
        """
        self._update_or_create_entry(file_path, quick_hash=quick_hash, algorithm=algorithm)

    def set_full_hash(self, file_path: str, full_hash: str, algorithm: str = "sha256"):
        """
        Store a full hash in the cache.

        Args:
            file_path: Path to the file
            full_hash: The full hash value
            algorithm: Hash algorithm used
        """
        self._update_or_create_entry(file_path, full_hash=full_hash, algorithm=algorithm)

    def set(
        self,
        file_path: str,
        quick_hash: Optional[str] = None,
        full_hash: Optional[str] = None,
        algorithm: str = "sha256"
    ):
        """
        Store hash values in the cache.

        Args:
            file_path: Path to the file
            quick_hash: The quick hash value (optional)
            full_hash: The full hash value (optional)
            algorithm: Hash algorithm used
        """
        self._update_or_create_entry(
            file_path,
            quick_hash=quick_hash,
            full_hash=full_hash,
            algorithm=algorithm
        )

    def _update_or_create_entry(
        self,
        file_path: str,
        quick_hash: Optional[str] = None,
        full_hash: Optional[str] = None,
        algorithm: str = "sha256"
    ):
        """Update existing entry or create new one."""
        with self._lock:
            try:
                stat = os.stat(file_path)

                # Check if we have an existing valid entry
                existing = self._get_entry(file_path)

                if existing and existing.file_mtime == stat.st_mtime:
                    # Update existing entry
                    if quick_hash:
                        existing.quick_hash = quick_hash
                    if full_hash:
                        existing.full_hash = full_hash
                    entry = existing
                else:
                    # Create new entry
                    entry = HashCacheEntry(
                        file_path=file_path,
                        file_size=stat.st_size,
                        file_mtime=stat.st_mtime,
                        quick_hash=quick_hash,
                        full_hash=full_hash,
                        algorithm=algorithm
                    )

                # Update memory cache
                self._memory_cache[file_path] = entry
                self._update_access_order(file_path)

                # Update database
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO hash_cache
                        (file_path, file_size, file_mtime, quick_hash, full_hash, algorithm, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.file_path,
                        entry.file_size,
                        entry.file_mtime,
                        entry.quick_hash,
                        entry.full_hash,
                        entry.algorithm,
                        entry.created_at
                    ))

            except Exception as e:
                logger.debug(f"Error writing to hash cache: {e}")

    def invalidate(self, file_path: str):
        """
        Invalidate cache entry for a file.

        Args:
            file_path: Path to the file
        """
        with self._lock:
            # Remove from memory
            self._memory_cache.pop(file_path, None)
            if file_path in self._access_order:
                self._access_order.remove(file_path)

            # Remove from database
            try:
                with self._get_connection() as conn:
                    conn.execute(
                        "DELETE FROM hash_cache WHERE file_path = ?",
                        (file_path,)
                    )
            except Exception as e:
                logger.debug(f"Error invalidating cache entry: {e}")

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._memory_cache.clear()
            self._access_order.clear()
            self._hits = 0
            self._misses = 0
            self._quick_hits = 0
            self._full_hits = 0

            try:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM hash_cache")
            except Exception as e:
                logger.debug(f"Error clearing cache: {e}")

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            cutoff = (datetime.now() - self.ttl).isoformat()
            count = 0

            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM hash_cache WHERE created_at < ?",
                        (cutoff,)
                    )
                    count = cursor.fetchone()[0]

                    conn.execute(
                        "DELETE FROM hash_cache WHERE created_at < ?",
                        (cutoff,)
                    )

                # Clear memory cache of expired entries
                expired_keys = [
                    k for k, v in self._memory_cache.items()
                    if datetime.fromisoformat(v.created_at) < datetime.now() - self.ttl
                ]
                for key in expired_keys:
                    del self._memory_cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)

            except Exception as e:
                logger.debug(f"Error cleaning up expired entries: {e}")

            return count

    def get_entries_by_size(self, file_size: int) -> List[HashCacheEntry]:
        """
        Get all cache entries for files of a specific size.

        Useful for quick duplicate detection by size grouping.

        Args:
            file_size: Size in bytes

        Returns:
            List of cache entries
        """
        entries = []

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM hash_cache WHERE file_size = ?",
                    (file_size,)
                )

                for row in cursor:
                    entry = HashCacheEntry(
                        file_path=row[0],
                        file_size=row[1],
                        file_mtime=row[2],
                        quick_hash=row[3],
                        full_hash=row[4],
                        algorithm=row[5],
                        created_at=row[6]
                    )
                    entries.append(entry)

        except Exception as e:
            logger.debug(f"Error querying by size: {e}")

        return entries

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        db_size = 0
        entry_count = 0

        try:
            db_size = self._db_path.stat().st_size if self._db_path.exists() else 0

            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM hash_cache")
                entry_count = cursor.fetchone()[0]

        except Exception:
            pass

        return {
            'hits': self._hits,
            'misses': self._misses,
            'quick_hits': self._quick_hits,
            'full_hits': self._full_hits,
            'hit_rate': f"{hit_rate:.1f}%",
            'memory_entries': len(self._memory_cache),
            'db_entries': entry_count,
            'db_size': db_size,
            'db_size_formatted': self._format_size(db_size),
            'ttl_days': self.ttl.days,
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def vacuum(self):
        """Optimize the database by running VACUUM."""
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
        except Exception as e:
            logger.debug(f"Error vacuuming database: {e}")


# Global instance
_hash_cache: Optional[HashCache] = None


def get_hash_cache(
    cache_dir: Optional[str] = None,
    ttl_days: int = 7
) -> HashCache:
    """
    Get the global hash cache instance.

    Args:
        cache_dir: Cache directory (used only on first call)
        ttl_days: TTL in days (used only on first call)

    Returns:
        HashCache instance
    """
    global _hash_cache
    if _hash_cache is None:
        _hash_cache = HashCache(cache_dir=cache_dir, ttl_days=ttl_days)
    return _hash_cache


def reset_hash_cache():
    """Reset the global hash cache instance."""
    global _hash_cache
    _hash_cache = None
