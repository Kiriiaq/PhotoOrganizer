"""
Module des opérations sur les fichiers.
Organisation, copie, déplacement et gestion des fichiers média.
"""

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
from .file_manager import FileManager
from .organizer import OrganizationOptions, OrganizationResult, SmartOrganizer

__all__ = [
    # File manager
    'FileManager',

    # Organizer
    'SmartOrganizer', 'OrganizationOptions', 'OrganizationResult',

    # Duplicate finder
    'DuplicateFinder', 'DuplicateGroup', 'DuplicateResult',
    'find_duplicates', 'get_finder', 'reset_finder',

    # Duplicate manager
    'DuplicateManager', 'get_manager', 'reset_manager',
]
