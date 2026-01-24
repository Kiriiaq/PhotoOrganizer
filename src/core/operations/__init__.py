"""
Module des opérations sur les fichiers.
Organisation, copie, déplacement et gestion des fichiers média.
"""

from .file_manager import FileManager, copy_file, move_file
from .organizer import SmartOrganizer, organize_files, OrganizationOptions, OrganizationResult
from .duplicate_finder import (
    DuplicateFinder,
    DuplicateGroup,
    DuplicateResult,
    find_duplicates,
    get_finder,
    reset_finder,
)
from .duplicate_manager import (
    DuplicateManager,
    get_manager,
    reset_manager,
)

__all__ = [
    # File manager
    'FileManager', 'copy_file', 'move_file',

    # Organizer
    'SmartOrganizer', 'organize_files', 'OrganizationOptions', 'OrganizationResult',

    # Duplicate finder
    'DuplicateFinder', 'DuplicateGroup', 'DuplicateResult',
    'find_duplicates', 'get_finder', 'reset_finder',

    # Duplicate manager
    'DuplicateManager', 'get_manager', 'reset_manager',
]
