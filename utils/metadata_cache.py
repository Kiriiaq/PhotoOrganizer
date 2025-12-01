"""
Metadata caching system to avoid re-reading file metadata
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MetadataCache:
    """Cache for file metadata to improve performance"""

    def __init__(self, cache_dir: Optional[str] = None, ttl: int = 86400):
        """
        Initialize metadata cache

        Args:
            cache_dir: Directory to store cache files (default: user cache dir)
            ttl: Time to live in seconds (default: 24 hours)
        """
        if cache_dir is None:
            # Use standard cache directory
            if os.name == 'nt':
                base = Path(os.environ.get('LOCALAPPDATA', ''))
            else:
                base = Path.home() / '.cache'

            self.cache_dir = base / 'PhotoOrganizer' / 'metadata_cache'
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self.memory_cache: Dict[str, Dict] = {}

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'memory_hits': 0
        }

        logger.info(f"Metadata cache initialized at {self.cache_dir}")

    def _get_cache_key(self, file_path: str) -> str:
        """Generate cache key for a file"""
        # Use absolute path normalized
        abs_path = os.path.abspath(file_path)
        # Hash the path to create a safe filename
        import hashlib
        return hashlib.md5(abs_path.encode()).hexdigest()

    def _get_cache_file(self, cache_key: str) -> Path:
        """Get cache file path for a cache key"""
        return self.cache_dir / f"{cache_key}.json"

    def _is_cache_valid(self, cache_data: Dict, file_path: str) -> bool:
        """Check if cached data is still valid"""
        try:
            # Check if file still exists
            if not os.path.exists(file_path):
                return False

            # Check TTL
            cached_time = cache_data.get('cached_at', 0)
            if time.time() - cached_time > self.ttl:
                return False

            # Check if file has been modified
            file_mtime = os.path.getmtime(file_path)
            cached_mtime = cache_data.get('file_mtime', 0)

            if file_mtime != cached_mtime:
                return False

            # Check file size
            file_size = os.path.getsize(file_path)
            cached_size = cache_data.get('file_size', -1)

            if file_size != cached_size:
                return False

            return True

        except Exception as e:
            logger.debug(f"Cache validation error: {e}")
            return False

    def get(self, file_path: str) -> Optional[Dict]:
        """
        Get cached metadata for a file

        Args:
            file_path: Path to the file

        Returns:
            Cached metadata dict or None if not cached/invalid
        """
        cache_key = self._get_cache_key(file_path)

        # Check memory cache first
        if cache_key in self.memory_cache:
            cache_data = self.memory_cache[cache_key]
            if self._is_cache_valid(cache_data, file_path):
                self.stats['hits'] += 1
                self.stats['memory_hits'] += 1
                logger.debug(f"Memory cache hit for {file_path}")
                return cache_data.get('metadata')

        # Check disk cache
        cache_file = self._get_cache_file(cache_key)

        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                if self._is_cache_valid(cache_data, file_path):
                    # Store in memory cache
                    self.memory_cache[cache_key] = cache_data
                    self.stats['hits'] += 1
                    logger.debug(f"Disk cache hit for {file_path}")
                    return cache_data.get('metadata')
                else:
                    # Invalid cache, delete it
                    cache_file.unlink()
                    self.stats['invalidations'] += 1

        except Exception as e:
            logger.debug(f"Error reading cache for {file_path}: {e}")

        self.stats['misses'] += 1
        return None

    def set(self, file_path: str, metadata: Dict) -> bool:
        """
        Cache metadata for a file

        Args:
            file_path: Path to the file
            metadata: Metadata dictionary to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._get_cache_key(file_path)
            cache_file = self._get_cache_file(cache_key)

            # Get file stats
            file_stat = os.stat(file_path)

            cache_data = {
                'file_path': os.path.abspath(file_path),
                'file_mtime': file_stat.st_mtime,
                'file_size': file_stat.st_size,
                'cached_at': time.time(),
                'metadata': metadata
            }

            # Store in memory cache
            self.memory_cache[cache_key] = cache_data

            # Store in disk cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)

            logger.debug(f"Cached metadata for {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error caching metadata for {file_path}: {e}")
            return False

    def invalidate(self, file_path: str) -> bool:
        """
        Invalidate cache for a specific file

        Args:
            file_path: Path to the file

        Returns:
            True if cache was invalidated, False if not found
        """
        cache_key = self._get_cache_key(file_path)

        # Remove from memory cache
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]

        # Remove from disk cache
        cache_file = self._get_cache_file(cache_key)
        if cache_file.exists():
            try:
                cache_file.unlink()
                self.stats['invalidations'] += 1
                logger.debug(f"Invalidated cache for {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error invalidating cache for {file_path}: {e}")

        return False

    def clear(self) -> int:
        """
        Clear all cached data

        Returns:
            Number of cache entries deleted
        """
        count = 0

        # Clear memory cache
        self.memory_cache.clear()

        # Clear disk cache
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1

            logger.info(f"Cleared {count} cache entries")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

        return count

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries

        Returns:
            Number of entries removed
        """
        count = 0
        current_time = time.time()

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)

                    cached_time = cache_data.get('cached_at', 0)
                    if current_time - cached_time > self.ttl:
                        cache_file.unlink()
                        count += 1

                        # Also remove from memory cache
                        cache_key = cache_file.stem
                        if cache_key in self.memory_cache:
                            del self.memory_cache[cache_key]

                except Exception as e:
                    logger.debug(f"Error processing {cache_file}: {e}")
                    # If we can't read it, delete it
                    cache_file.unlink()
                    count += 1

            logger.info(f"Cleaned up {count} expired cache entries")

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")

        return count

    def get_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'memory_hits': self.stats['memory_hits'],
            'invalidations': self.stats['invalidations'],
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_dir': str(self.cache_dir),
            'ttl_seconds': self.ttl,
            'memory_cache_size': len(self.memory_cache)
        }

    def get_cache_size(self) -> Dict:
        """
        Get cache size information

        Returns:
            Dictionary with size information
        """
        try:
            total_size = 0
            file_count = 0

            for cache_file in self.cache_dir.glob("*.json"):
                total_size += cache_file.stat().st_size
                file_count += 1

            return {
                'file_count': file_count,
                'total_bytes': total_size,
                'total_mb': round(total_size / (1024 * 1024), 2),
                'cache_dir': str(self.cache_dir)
            }

        except Exception as e:
            logger.error(f"Error getting cache size: {e}")
            return {'error': str(e)}


# Global cache instance
_cache_instance = None


def get_metadata_cache(ttl: int = 86400) -> MetadataCache:
    """
    Get the global metadata cache instance

    Args:
        ttl: Time to live in seconds (only used on first call)

    Returns:
        MetadataCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MetadataCache(ttl=ttl)
    return _cache_instance


def clear_global_cache():
    """Clear the global cache instance"""
    global _cache_instance
    if _cache_instance is not None:
        _cache_instance.clear()
        _cache_instance = None
