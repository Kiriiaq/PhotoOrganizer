"""
File hashing utilities for duplicate detection and file comparison
"""

import hashlib
import os
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str, algorithm: str = 'md5', block_size: int = 65536) -> Optional[str]:
    """
    Calculate hash of a file using specified algorithm

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256', 'sha512')
        block_size: Size of blocks to read (default 64KB)

    Returns:
        Hexadecimal hash string or None if error
    """
    try:
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha1':
            hasher = hashlib.sha1()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        elif algorithm == 'sha512':
            hasher = hashlib.sha512()
        else:
            logger.error(f"Unsupported hash algorithm: {algorithm}")
            return None

        with open(file_path, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                hasher.update(data)

        return hasher.hexdigest()

    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None


def calculate_quick_hash(file_path: str, sample_size: int = 8192) -> Optional[str]:
    """
    Calculate a quick hash by sampling beginning, middle, and end of file
    Useful for quickly identifying likely duplicates before full hash

    Args:
        file_path: Path to the file
        sample_size: Number of bytes to sample from each section

    Returns:
        Hexadecimal hash string or None if error
    """
    try:
        file_size = os.path.getsize(file_path)

        if file_size <= sample_size * 3:
            # File is small, just hash the whole thing
            return calculate_file_hash(file_path, algorithm='md5')

        hasher = hashlib.md5()

        with open(file_path, 'rb') as f:
            # Hash from beginning
            hasher.update(f.read(sample_size))

            # Hash from middle
            f.seek(file_size // 2 - sample_size // 2)
            hasher.update(f.read(sample_size))

            # Hash from end
            f.seek(-sample_size, 2)
            hasher.update(f.read(sample_size))

        # Include file size in hash to differentiate files of different sizes
        hasher.update(str(file_size).encode())

        return hasher.hexdigest()

    except Exception as e:
        logger.error(f"Error calculating quick hash for {file_path}: {e}")
        return None


def find_duplicate_files(file_paths: List[str], use_quick_hash: bool = True) -> Dict[str, List[str]]:
    """
    Find duplicate files by comparing their hashes

    Args:
        file_paths: List of file paths to check
        use_quick_hash: Use quick hash first for performance (default True)

    Returns:
        Dictionary mapping hash to list of duplicate file paths
        Only includes hashes with 2+ files
    """
    hash_map: Dict[str, List[str]] = {}
    duplicates: Dict[str, List[str]] = {}

    # First pass: quick hash if enabled
    if use_quick_hash:
        logger.info("Phase 1: Quick hash scan")
        for file_path in file_paths:
            quick_hash = calculate_quick_hash(file_path)
            if quick_hash:
                if quick_hash not in hash_map:
                    hash_map[quick_hash] = []
                hash_map[quick_hash].append(file_path)

        # Second pass: full hash only for potential duplicates
        logger.info("Phase 2: Full hash verification for potential duplicates")
        potential_duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}

        full_hash_map: Dict[str, List[str]] = {}
        for files in potential_duplicates.values():
            for file_path in files:
                full_hash = calculate_file_hash(file_path, algorithm='sha256')
                if full_hash:
                    if full_hash not in full_hash_map:
                        full_hash_map[full_hash] = []
                    full_hash_map[full_hash].append(file_path)

        duplicates = {h: files for h, files in full_hash_map.items() if len(files) > 1}

    else:
        # Single pass: full hash all files
        logger.info("Full hash scan")
        for file_path in file_paths:
            file_hash = calculate_file_hash(file_path, algorithm='sha256')
            if file_hash:
                if file_hash not in hash_map:
                    hash_map[file_hash] = []
                hash_map[file_hash].append(file_path)

        duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}

    logger.info(f"Found {len(duplicates)} groups of duplicate files")
    return duplicates


def compare_files_by_hash(file1: str, file2: str, algorithm: str = 'sha256') -> bool:
    """
    Compare two files by their hash values

    Args:
        file1: Path to first file
        file2: Path to second file
        algorithm: Hash algorithm to use

    Returns:
        True if files are identical, False otherwise
    """
    hash1 = calculate_file_hash(file1, algorithm)
    hash2 = calculate_file_hash(file2, algorithm)

    if hash1 is None or hash2 is None:
        return False

    return hash1 == hash2


def get_file_info_with_hash(file_path: str) -> Optional[Dict]:
    """
    Get file information including hash

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file info or None if error
    """
    try:
        stat_info = os.stat(file_path)

        return {
            'path': file_path,
            'name': os.path.basename(file_path),
            'size': stat_info.st_size,
            'modified': stat_info.st_mtime,
            'created': stat_info.st_ctime,
            'quick_hash': calculate_quick_hash(file_path),
            'full_hash': None  # Calculate on demand
        }

    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return None


def batch_hash_files(file_paths: List[str], algorithm: str = 'sha256',
                     progress_callback=None) -> Dict[str, str]:
    """
    Calculate hashes for multiple files with progress tracking

    Args:
        file_paths: List of file paths
        algorithm: Hash algorithm to use
        progress_callback: Optional callback(current, total) for progress

    Returns:
        Dictionary mapping file path to hash
    """
    results = {}
    total = len(file_paths)

    for i, file_path in enumerate(file_paths, 1):
        file_hash = calculate_file_hash(file_path, algorithm)
        if file_hash:
            results[file_path] = file_hash

        if progress_callback:
            progress_callback(i, total)

    return results


def verify_file_integrity(file_path: str, expected_hash: str, algorithm: str = 'sha256') -> bool:
    """
    Verify file integrity by comparing with expected hash

    Args:
        file_path: Path to the file
        expected_hash: Expected hash value
        algorithm: Hash algorithm used

    Returns:
        True if hash matches, False otherwise
    """
    actual_hash = calculate_file_hash(file_path, algorithm)

    if actual_hash is None:
        return False

    return actual_hash.lower() == expected_hash.lower()
