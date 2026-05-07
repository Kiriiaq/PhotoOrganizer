"""
Module des opérations sur les fichiers.
Réexporte les composants depuis core.operations.
"""

from ..core.operations.file_manager import FileManager, copy_file, move_file
from ..core.operations.organizer import SmartOrganizer, organize_files, OrganizationOptions, OrganizationResult
from ..core.operations.duplicate_finder import (
    DuplicateFinder,
    DuplicateGroup,
    DuplicateResult,
    find_duplicates,
    get_finder,
    reset_finder,
)
from ..core.operations.duplicate_manager import (
    DuplicateManager,
    get_manager,
    reset_manager,
)

__all__ = [
    'FileManager', 'copy_file', 'move_file',
    'SmartOrganizer', 'organize_files', 'OrganizationOptions', 'OrganizationResult',
    'DuplicateFinder', 'DuplicateGroup', 'DuplicateResult',
    'find_duplicates', 'get_finder', 'reset_finder',
    'DuplicateManager', 'get_manager', 'reset_manager',
]
