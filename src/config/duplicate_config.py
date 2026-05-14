# -*- coding: utf-8 -*-
"""
Configuration classes for the advanced duplicate detection and management system.

This module defines all configuration dataclasses, enums, and result structures
used by the duplicate manager, CLI, and reporters.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# =============================================================================
# ENUMS
# =============================================================================

class ExecutionMode(Enum):
    """Execution mode for duplicate management."""
    DRY_RUN = auto()      # Simulation only, no changes
    DELETE = auto()        # Permanently delete duplicates
    MOVE = auto()          # Move duplicates to destination folder
    TRASH = auto()         # Move duplicates to system trash
    INTERACTIVE = auto()   # Ask user for each group


class ConservationCriterion(Enum):
    """Criteria for selecting which file to keep in a duplicate group."""
    PRIORITY_FOLDER = "priority_folder"      # File in priority folder
    PREFERRED_EXTENSION = "preferred_extension"  # Preferred file extension
    OLDEST_DATE = "oldest_date"              # Oldest creation/modification date
    NEWEST_DATE = "newest_date"              # Newest creation/modification date
    SHORTEST_PATH = "shortest_path"          # Shortest file path
    LONGEST_PATH = "longest_path"            # Longest file path
    LARGEST_FILE = "largest_file"            # Largest file size (for same hash)
    SMALLEST_FILE = "smallest_file"          # Smallest file size


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    BLAKE3 = "blake3"


class FileAction(Enum):
    """Action to take on a file."""
    KEEP = "keep"
    DELETE = "delete"
    MOVE = "move"
    TRASH = "trash"
    IGNORE = "ignore"
    ERROR = "error"


# =============================================================================
# SUB-CONFIGURATIONS
# =============================================================================

@dataclass
class FolderFilter:
    """
    Folder filtering configuration.

    Attributes:
        include: Glob patterns for folders to include (empty = all)
        exclude: Glob patterns for folders to exclude
        priority: Ordered list of priority folders for conservation
    """
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=lambda: [
        "**/node_modules",
        "**/.git",
        "**/venv",
        "**/__pycache__",
        "**/Thumbs.db",
        "**/.DS_Store",
        "**/Trash",
        "**/Recycle.Bin",
    ])
    priority: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'include': self.include,
            'exclude': self.exclude,
            'priority': self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FolderFilter':
        return cls(
            include=data.get('include', []),
            exclude=data.get('exclude', cls.__dataclass_fields__['exclude'].default_factory()),
            priority=data.get('priority', []),
        )


@dataclass
class ExtensionFilter:
    """
    File extension filtering configuration.

    Attributes:
        include: Extensions to include (empty = all supported)
        exclude: Extensions to exclude
        preferred_order: Ordered list for conservation preference (.raw > .tiff > .jpg)
    """
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    preferred_order: List[str] = field(default_factory=lambda: [
        ".dng", ".raw", ".arw", ".cr2", ".cr3", ".nef", ".orf", ".rw2",
        ".tiff", ".tif",
        ".png",
        ".heic", ".heif",
        ".jpg", ".jpeg",
        ".webp",
        ".bmp", ".gif",
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            'include': self.include,
            'exclude': self.exclude,
            'preferred_order': self.preferred_order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtensionFilter':
        return cls(
            include=data.get('include', []),
            exclude=data.get('exclude', []),
            preferred_order=data.get('preferred_order',
                                     cls.__dataclass_fields__['preferred_order'].default_factory()),
        )


@dataclass
class ConservationPolicy:
    """
    Policy for deciding which file to keep in a duplicate group.

    The criteria are applied in order. The first criterion that produces
    a clear winner is used.

    Attributes:
        criteria_order: Ordered list of conservation criteria
        keep_all_in_priority: If True, keep all files in priority folders
    """
    criteria_order: List[ConservationCriterion] = field(default_factory=lambda: [
        ConservationCriterion.PRIORITY_FOLDER,
        ConservationCriterion.PREFERRED_EXTENSION,
        ConservationCriterion.OLDEST_DATE,
        ConservationCriterion.SHORTEST_PATH,
    ])
    keep_all_in_priority: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'criteria_order': [c.value for c in self.criteria_order],
            'keep_all_in_priority': self.keep_all_in_priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConservationPolicy':
        criteria = data.get('criteria_order', [])
        return cls(
            criteria_order=[ConservationCriterion(c) for c in criteria] if criteria
                          else cls.__dataclass_fields__['criteria_order'].default_factory(),
            keep_all_in_priority=data.get('keep_all_in_priority', False),
        )


@dataclass
class HashingConfig:
    """
    Hashing configuration for duplicate detection.

    Attributes:
        algorithm: Hash algorithm to use
        chunk_size_mb: Size of chunks for reading large files (MB)
        use_quick_mode: Use quick hash filtering before full hash
        quick_chunk_size: Size of quick hash chunks (bytes)
        use_cache: Enable hash caching
        cache_ttl_days: Cache time-to-live in days
    """
    algorithm: HashAlgorithm = HashAlgorithm.SHA256
    chunk_size_mb: int = 4
    use_quick_mode: bool = True
    quick_chunk_size: int = 65536  # 64KB
    use_cache: bool = True
    cache_ttl_days: int = 7

    @property
    def chunk_size_bytes(self) -> int:
        return self.chunk_size_mb * 1024 * 1024

    def to_dict(self) -> Dict[str, Any]:
        return {
            'algorithm': self.algorithm.value,
            'chunk_size_mb': self.chunk_size_mb,
            'use_quick_mode': self.use_quick_mode,
            'quick_chunk_size': self.quick_chunk_size,
            'use_cache': self.use_cache,
            'cache_ttl_days': self.cache_ttl_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HashingConfig':
        algo = data.get('algorithm', 'sha256')
        return cls(
            algorithm=HashAlgorithm(algo) if isinstance(algo, str) else HashAlgorithm.SHA256,
            chunk_size_mb=data.get('chunk_size_mb', 4),
            use_quick_mode=data.get('use_quick_mode', True),
            quick_chunk_size=data.get('quick_chunk_size', 65536),
            use_cache=data.get('use_cache', True),
            cache_ttl_days=data.get('cache_ttl_days', 7),
        )


@dataclass
class PerformanceConfig:
    """
    Performance configuration.

    Attributes:
        max_workers: Maximum number of parallel workers (0 = auto)
        memory_limit_mb: Maximum memory usage in MB (0 = unlimited)
        show_progress: Show progress bar
        batch_size: Number of files to process in each batch
    """
    max_workers: int = 0  # 0 = auto (cpu_count)
    memory_limit_mb: int = 512
    show_progress: bool = True
    batch_size: int = 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_workers': self.max_workers,
            'memory_limit_mb': self.memory_limit_mb,
            'show_progress': self.show_progress,
            'batch_size': self.batch_size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceConfig':
        return cls(
            max_workers=data.get('max_workers', 0),
            memory_limit_mb=data.get('memory_limit_mb', 512),
            show_progress=data.get('show_progress', True),
            batch_size=data.get('batch_size', 1000),
        )


@dataclass
class LoggingConfig:
    """
    Logging configuration.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Write logs to file
        log_file: Path to log file (auto-generated if None)
        verbose: Verbosity level (0-3)
    """
    level: str = "INFO"
    log_to_file: bool = True
    log_file: Optional[str] = None
    verbose: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level,
            'log_to_file': self.log_to_file,
            'log_file': self.log_file,
            'verbose': self.verbose,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoggingConfig':
        return cls(
            level=data.get('level', 'INFO'),
            log_to_file=data.get('log_to_file', True),
            log_file=data.get('log_file'),
            verbose=data.get('verbose', 1),
        )


# =============================================================================
# RESULT DATACLASSES
# =============================================================================

@dataclass
class FileDecision:
    """
    Decision for a single file within a duplicate group.

    Attributes:
        file_path: Absolute path to the file
        action: Action to take on this file
        reason: Human-readable reason for the decision
        target_path: Destination path for MOVE action
        file_size: Size of the file in bytes
        creation_time: File creation timestamp
        modification_time: File modification timestamp
    """
    file_path: str
    action: FileAction
    reason: str
    target_path: Optional[str] = None
    file_size: int = 0
    creation_time: Optional[datetime] = None
    modification_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'action': self.action.value,
            'reason': self.reason,
            'target_path': self.target_path,
            'file_size': self.file_size,
            'creation_time': self.creation_time.isoformat() if self.creation_time else None,
            'modification_time': self.modification_time.isoformat() if self.modification_time else None,
        }


@dataclass
class DuplicateGroupDecision:
    """
    Decision for a group of duplicate files.

    Attributes:
        group_id: Unique identifier for the group
        hash_value: Hash value shared by all files
        file_size: Size of each file in the group
        decisions: List of decisions for each file
    """
    group_id: int
    hash_value: str
    file_size: int
    decisions: List[FileDecision] = field(default_factory=list)

    @property
    def files_count(self) -> int:
        return len(self.decisions)

    @property
    def files_to_keep(self) -> List[FileDecision]:
        return [d for d in self.decisions if d.action == FileAction.KEEP]

    @property
    def files_to_remove(self) -> List[FileDecision]:
        return [d for d in self.decisions if d.action in (FileAction.DELETE, FileAction.MOVE, FileAction.TRASH)]

    @property
    def space_recoverable(self) -> int:
        return len(self.files_to_remove) * self.file_size

    def to_dict(self) -> Dict[str, Any]:
        return {
            'group_id': self.group_id,
            'hash_value': self.hash_value,
            'file_size': self.file_size,
            'files_count': self.files_count,
            'space_recoverable': self.space_recoverable,
            'decisions': [d.to_dict() for d in self.decisions],
        }


@dataclass
class ExecutionResult:
    """
    Result of a duplicate management execution.

    Attributes:
        total_files_scanned: Total number of files scanned
        duplicate_groups: Number of duplicate groups found
        total_duplicates: Total number of duplicate files (excluding originals)
        files_kept: Number of files kept
        files_deleted: Number of files deleted
        files_moved: Number of files moved
        files_trashed: Number of files sent to trash
        files_errored: Number of files with errors
        space_scanned: Total size of scanned files
        space_duplicates: Total size of duplicate files
        space_recovered: Total space recovered (or recoverable in dry-run)
        group_decisions: Detailed decisions for each group
        errors: List of error messages
        start_time: Execution start timestamp
        end_time: Execution end timestamp
        execution_mode: Mode used for execution
    """
    total_files_scanned: int = 0
    duplicate_groups: int = 0
    total_duplicates: int = 0
    files_kept: int = 0
    files_deleted: int = 0
    files_moved: int = 0
    files_trashed: int = 0
    files_errored: int = 0
    space_scanned: int = 0
    space_duplicates: int = 0
    space_recovered: int = 0
    group_decisions: List[DuplicateGroupDecision] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_mode: ExecutionMode = ExecutionMode.DRY_RUN

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def success(self) -> bool:
        return self.files_errored == 0 and len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'summary': {
                'total_files_scanned': self.total_files_scanned,
                'duplicate_groups': self.duplicate_groups,
                'total_duplicates': self.total_duplicates,
                'files_kept': self.files_kept,
                'files_deleted': self.files_deleted,
                'files_moved': self.files_moved,
                'files_trashed': self.files_trashed,
                'files_errored': self.files_errored,
                'space_scanned': self.space_scanned,
                'space_duplicates': self.space_duplicates,
                'space_recovered': self.space_recovered,
                'duration_seconds': self.duration_seconds,
                'success': self.success,
            },
            'execution_mode': self.execution_mode.name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'groups': [g.to_dict() for g in self.group_decisions],
            'errors': self.errors,
        }


# =============================================================================
# MAIN CONFIGURATION
# =============================================================================

@dataclass
class DuplicateManagerConfig:
    """
    Complete configuration for the duplicate manager.

    Attributes:
        source_directories: List of directories to scan
        recursive: Scan subdirectories
        folders: Folder filtering configuration
        extensions: Extension filtering configuration
        min_file_size: Minimum file size to consider (bytes)
        max_file_size: Maximum file size to consider (bytes, None = unlimited)
        conservation: Conservation policy configuration
        hashing: Hashing configuration
        execution_mode: How to handle duplicates
        move_destination: Destination folder for MOVE mode
        performance: Performance configuration
        logging: Logging configuration
        generate_csv: Generate CSV report
        generate_json: Generate JSON report
        generate_txt: Generate TXT report
        report_output_dir: Directory for report files
        verify_before_delete: Re-hash files before deletion
        skip_confirmation: Skip confirmation prompts
    """
    # Sources
    source_directories: List[str] = field(default_factory=list)
    recursive: bool = True

    # Filters
    folders: FolderFilter = field(default_factory=FolderFilter)
    extensions: ExtensionFilter = field(default_factory=ExtensionFilter)
    min_file_size: int = 0
    max_file_size: Optional[int] = None

    # Conservation
    conservation: ConservationPolicy = field(default_factory=ConservationPolicy)

    # Hashing
    hashing: HashingConfig = field(default_factory=HashingConfig)

    # Execution
    execution_mode: ExecutionMode = ExecutionMode.DRY_RUN
    move_destination: Optional[str] = None

    # Performance
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    # Logging
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Reports
    generate_csv: bool = False
    generate_json: bool = False
    generate_txt: bool = False
    report_output_dir: Optional[str] = None

    # Safety
    verify_before_delete: bool = False
    skip_confirmation: bool = False

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Check source directories
        if not self.source_directories:
            errors.append("At least one source directory is required")
        else:
            for src in self.source_directories:
                if not Path(src).exists():
                    errors.append(f"Source directory does not exist: {src}")
                elif not Path(src).is_dir():
                    errors.append(f"Source path is not a directory: {src}")

        # Check move destination for MOVE mode
        if self.execution_mode == ExecutionMode.MOVE:
            if not self.move_destination:
                errors.append("Move destination is required for MOVE mode")
            elif not Path(self.move_destination).parent.exists():
                errors.append(f"Parent of move destination does not exist: {self.move_destination}")

        # Check file size constraints
        if self.max_file_size is not None and self.max_file_size < self.min_file_size:
            errors.append("max_file_size must be greater than min_file_size")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for YAML serialization."""
        return {
            'source_directories': self.source_directories,
            'recursive': self.recursive,
            'folders': self.folders.to_dict(),
            'extensions': self.extensions.to_dict(),
            'min_file_size': self.min_file_size,
            'max_file_size': self.max_file_size,
            'conservation': self.conservation.to_dict(),
            'hashing': self.hashing.to_dict(),
            'execution_mode': self.execution_mode.name,
            'move_destination': self.move_destination,
            'performance': self.performance.to_dict(),
            'logging': self.logging.to_dict(),
            'generate_csv': self.generate_csv,
            'generate_json': self.generate_json,
            'generate_txt': self.generate_txt,
            'report_output_dir': self.report_output_dir,
            'verify_before_delete': self.verify_before_delete,
            'skip_confirmation': self.skip_confirmation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DuplicateManagerConfig':
        """Create configuration from dictionary."""
        exec_mode_str = data.get('execution_mode', 'DRY_RUN')
        try:
            exec_mode = ExecutionMode[exec_mode_str]
        except KeyError:
            exec_mode = ExecutionMode.DRY_RUN

        return cls(
            source_directories=data.get('source_directories', []),
            recursive=data.get('recursive', True),
            folders=FolderFilter.from_dict(data.get('folders', {})),
            extensions=ExtensionFilter.from_dict(data.get('extensions', {})),
            min_file_size=data.get('min_file_size', 0),
            max_file_size=data.get('max_file_size'),
            conservation=ConservationPolicy.from_dict(data.get('conservation', {})),
            hashing=HashingConfig.from_dict(data.get('hashing', {})),
            execution_mode=exec_mode,
            move_destination=data.get('move_destination'),
            performance=PerformanceConfig.from_dict(data.get('performance', {})),
            logging=LoggingConfig.from_dict(data.get('logging', {})),
            generate_csv=data.get('generate_csv', False),
            generate_json=data.get('generate_json', False),
            generate_txt=data.get('generate_txt', False),
            report_output_dir=data.get('report_output_dir'),
            verify_before_delete=data.get('verify_before_delete', False),
            skip_confirmation=data.get('skip_confirmation', False),
        )


# =============================================================================
# YAML LOADERS
# =============================================================================

def load_config_from_yaml(file_path: str) -> DuplicateManagerConfig:
    """
    Load configuration from a YAML file.

    Args:
        file_path: Path to the YAML configuration file

    Returns:
        DuplicateManagerConfig instance

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the file is not valid YAML
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    return DuplicateManagerConfig.from_dict(data or {})


def save_config_to_yaml(config: DuplicateManagerConfig, file_path: str) -> None:
    """
    Save configuration to a YAML file.

    Args:
        config: Configuration to save
        file_path: Path to the output YAML file
    """
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(
            config.to_dict(),
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
