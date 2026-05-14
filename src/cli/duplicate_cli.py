# -*- coding: utf-8 -*-
"""
Command-line interface for advanced duplicate detection and management.

This module provides a complete CLI for the duplicate management system
with support for all execution modes, filters, and report generation.

Usage:
    python -m src.cli.duplicate_cli [OPTIONS] DIRECTORIES...

Examples:
    # Dry-run scan (default)
    python -m src.cli.duplicate_cli D:/Photos

    # Delete duplicates
    python -m src.cli.duplicate_cli --delete D:/Photos

    # Move duplicates to folder
    python -m src.cli.duplicate_cli --move-to D:/Duplicates D:/Photos

    # Interactive mode with reports
    python -m src.cli.duplicate_cli -i --all-reports D:/Photos

    # Use BLAKE3 with custom priority folders
    python -m src.cli.duplicate_cli --algorithm blake3 --priority-dirs D:/Masters D:/Photos
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

from src.config.duplicate_config import (
    ConservationCriterion,
    DuplicateGroupDecision,
    DuplicateManagerConfig,
    ExecutionMode,
    FileAction,
    HashAlgorithm,
    load_config_from_yaml,
    save_config_to_yaml,
)
from src.core.operations.duplicate_finder import DuplicateFinder
from src.core.operations.duplicate_manager import DuplicateManager
from src.reports.duplicate_reporter import DuplicateReporter

logger = logging.getLogger(__name__)


def parse_size(size_str: str) -> int:
    """
    Parse a size string (e.g., '1KB', '10MB') to bytes.

    Args:
        size_str: Size string with optional unit

    Returns:
        Size in bytes
    """
    size_str = size_str.strip().upper()

    units = {
        'B': 1,
        'KB': 1024,
        'K': 1024,
        'MB': 1024 * 1024,
        'M': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'G': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024,
        'T': 1024 * 1024 * 1024 * 1024,
    }

    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            number = size_str[:-len(unit)].strip()
            return int(float(number) * multiplier)

    # No unit, assume bytes
    return int(size_str)


def format_size(size_bytes: int) -> str:
    """Format size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


class ProgressBar:
    """Progress bar wrapper that works with or without tqdm."""

    def __init__(self, total: int, desc: str = "", disable: bool = False):
        self.total = total
        self.desc = desc
        self.disable = disable
        self.current = 0
        self._pbar = None

        if TQDM_AVAILABLE and not disable:
            self._pbar = tqdm(total=total, desc=desc, unit="files")

    def update(self, current: int, message: str = ""):
        """Update progress."""
        if self._pbar:
            increment = current - self.current
            if increment > 0:
                self._pbar.update(increment)
            if message:
                self._pbar.set_description(message[:40])
        else:
            if not self.disable and self.total > 0:
                pct = current / self.total * 100
                print(f"\r{message[:50]:50} [{pct:5.1f}%]", end="", flush=True)

        self.current = current

    def close(self):
        """Close the progress bar."""
        if self._pbar:
            self._pbar.close()
        elif not self.disable:
            print()  # New line after progress


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog='duplicate_cli',
        description='Advanced duplicate file detection and management.',
        epilog='Example: python -m src.cli.duplicate_cli --dry-run D:/Photos',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Positional arguments
    parser.add_argument(
        'directories',
        nargs='*',
        help='Directories to scan for duplicates'
    )

    # Execution mode (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Simulation mode, no changes (default)'
    )
    mode_group.add_argument(
        '--delete',
        action='store_true',
        help='Permanently delete duplicate files'
    )
    mode_group.add_argument(
        '--move-to',
        metavar='DIR',
        help='Move duplicates to specified directory'
    )
    mode_group.add_argument(
        '--trash',
        action='store_true',
        help='Move duplicates to system trash'
    )
    mode_group.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Interactive mode: confirm each group'
    )

    # Hash options
    hash_group = parser.add_argument_group('Hashing options')
    hash_group.add_argument(
        '--algorithm',
        choices=['md5', 'sha1', 'sha256', 'blake3'],
        default='sha256',
        help='Hash algorithm (default: sha256)'
    )
    hash_group.add_argument(
        '--chunk-size',
        type=int,
        default=4,
        metavar='MB',
        help='Chunk size for reading files in MB (default: 4)'
    )
    hash_group.add_argument(
        '--no-quick-mode',
        action='store_true',
        help='Disable quick hash filtering'
    )
    hash_group.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable hash caching'
    )

    # Filter options
    filter_group = parser.add_argument_group('Filter options')
    filter_group.add_argument(
        '--extensions',
        nargs='+',
        metavar='EXT',
        help='Include only these extensions (e.g., .jpg .png .raw)'
    )
    filter_group.add_argument(
        '--exclude-ext',
        nargs='+',
        metavar='EXT',
        help='Exclude these extensions (e.g., .tmp .bak)'
    )
    filter_group.add_argument(
        '--exclude-dir',
        nargs='+',
        metavar='PATTERN',
        help='Exclude directories matching patterns (e.g., "**/node_modules")'
    )
    filter_group.add_argument(
        '--min-size',
        type=str,
        default='0',
        metavar='SIZE',
        help='Minimum file size (e.g., 1KB, 10MB)'
    )
    filter_group.add_argument(
        '--max-size',
        type=str,
        metavar='SIZE',
        help='Maximum file size (e.g., 100MB, 1GB)'
    )
    filter_group.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not scan subdirectories'
    )

    # Conservation options
    conservation_group = parser.add_argument_group('Conservation options')
    conservation_group.add_argument(
        '--priority-dirs',
        nargs='+',
        metavar='DIR',
        help='Priority directories for keeping files'
    )
    conservation_group.add_argument(
        '--prefer-extensions',
        nargs='+',
        metavar='EXT',
        help='Preferred extensions order (e.g., .raw .tiff .jpg)'
    )
    conservation_group.add_argument(
        '--keep-oldest',
        action='store_true',
        help='Keep the oldest file in each group'
    )
    conservation_group.add_argument(
        '--keep-newest',
        action='store_true',
        help='Keep the newest file in each group'
    )
    conservation_group.add_argument(
        '--keep-shortest-path',
        action='store_true',
        help='Keep the file with shortest path'
    )
    conservation_group.add_argument(
        '--keep-longest-path',
        action='store_true',
        help='Keep the file with longest path'
    )

    # Performance options
    perf_group = parser.add_argument_group('Performance options')
    perf_group.add_argument(
        '-j', '--workers',
        type=int,
        default=0,
        metavar='N',
        help='Number of parallel workers (default: auto)'
    )
    perf_group.add_argument(
        '--memory-limit',
        type=int,
        default=512,
        metavar='MB',
        help='Memory limit in MB (default: 512)'
    )
    perf_group.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    # Safety options
    safety_group = parser.add_argument_group('Safety options')
    safety_group.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompts'
    )
    safety_group.add_argument(
        '--verify-before-delete',
        action='store_true',
        help='Re-verify hash before deleting files'
    )

    # Report options
    report_group = parser.add_argument_group('Report options')
    report_group.add_argument(
        '--csv',
        action='store_true',
        help='Generate CSV report'
    )
    report_group.add_argument(
        '--json',
        action='store_true',
        help='Generate JSON report'
    )
    report_group.add_argument(
        '--txt',
        action='store_true',
        help='Generate TXT report'
    )
    report_group.add_argument(
        '--all-reports',
        action='store_true',
        help='Generate all report formats'
    )
    report_group.add_argument(
        '-o', '--output-dir',
        metavar='DIR',
        help='Output directory for reports'
    )

    # Logging options
    log_group = parser.add_argument_group('Logging options')
    log_group.add_argument(
        '--log-file',
        metavar='FILE',
        help='Log file path'
    )
    log_group.add_argument(
        '-v', '--verbose',
        action='count',
        default=1,
        help='Increase verbosity (use -vv or -vvv for more)'
    )
    log_group.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress non-essential output'
    )

    # Configuration file options
    config_group = parser.add_argument_group('Configuration options')
    config_group.add_argument(
        '-c', '--config',
        metavar='FILE',
        help='Load configuration from YAML file'
    )
    config_group.add_argument(
        '--save-config',
        metavar='FILE',
        help='Save current configuration to YAML file'
    )

    return parser


def build_config_from_args(args: argparse.Namespace) -> DuplicateManagerConfig:
    """Build configuration from parsed arguments."""

    # Load base config from file if specified
    if args.config:
        config = load_config_from_yaml(args.config)
    else:
        config = DuplicateManagerConfig()

    # Override with command-line arguments
    if args.directories:
        config.source_directories = [str(Path(d).resolve()) for d in args.directories]

    config.recursive = not args.no_recursive

    # Execution mode
    if args.delete:
        config.execution_mode = ExecutionMode.DELETE
    elif args.move_to:
        config.execution_mode = ExecutionMode.MOVE
        config.move_destination = str(Path(args.move_to).resolve())
    elif args.trash:
        config.execution_mode = ExecutionMode.TRASH
    elif args.interactive:
        config.execution_mode = ExecutionMode.INTERACTIVE
    else:
        config.execution_mode = ExecutionMode.DRY_RUN

    # Hashing
    config.hashing.algorithm = HashAlgorithm(args.algorithm)
    config.hashing.chunk_size_mb = args.chunk_size
    config.hashing.use_quick_mode = not args.no_quick_mode
    config.hashing.use_cache = not args.no_cache

    # Filters
    if args.extensions:
        config.extensions.include = [
            ext if ext.startswith('.') else f'.{ext}'
            for ext in args.extensions
        ]
    if args.exclude_ext:
        config.extensions.exclude = [
            ext if ext.startswith('.') else f'.{ext}'
            for ext in args.exclude_ext
        ]
    if args.exclude_dir:
        config.folders.exclude.extend(args.exclude_dir)

    config.min_file_size = parse_size(args.min_size)
    if args.max_size:
        config.max_file_size = parse_size(args.max_size)

    # Conservation
    if args.priority_dirs:
        config.folders.priority = [str(Path(d).resolve()) for d in args.priority_dirs]
    if args.prefer_extensions:
        config.extensions.preferred_order = [
            ext if ext.startswith('.') else f'.{ext}'
            for ext in args.prefer_extensions
        ]

    # Build conservation criteria order
    criteria = []
    if args.priority_dirs:
        criteria.append(ConservationCriterion.PRIORITY_FOLDER)
    if args.prefer_extensions:
        criteria.append(ConservationCriterion.PREFERRED_EXTENSION)
    if args.keep_oldest:
        criteria.append(ConservationCriterion.OLDEST_DATE)
    elif args.keep_newest:
        criteria.append(ConservationCriterion.NEWEST_DATE)
    if args.keep_shortest_path:
        criteria.append(ConservationCriterion.SHORTEST_PATH)
    elif args.keep_longest_path:
        criteria.append(ConservationCriterion.LONGEST_PATH)

    if criteria:
        config.conservation.criteria_order = criteria
    elif not config.conservation.criteria_order:
        # Default criteria
        config.conservation.criteria_order = [
            ConservationCriterion.PRIORITY_FOLDER,
            ConservationCriterion.PREFERRED_EXTENSION,
            ConservationCriterion.OLDEST_DATE,
            ConservationCriterion.SHORTEST_PATH,
        ]

    # Performance
    config.performance.max_workers = args.workers
    config.performance.memory_limit_mb = args.memory_limit
    config.performance.show_progress = not args.no_progress

    # Safety
    config.skip_confirmation = args.yes
    config.verify_before_delete = args.verify_before_delete

    # Reports
    config.generate_csv = args.csv or args.all_reports
    config.generate_json = args.json or args.all_reports
    config.generate_txt = args.txt or args.all_reports
    if args.output_dir:
        config.report_output_dir = str(Path(args.output_dir).resolve())

    # Logging
    config.logging.verbose = args.verbose
    if args.log_file:
        config.logging.log_file = args.log_file
        config.logging.log_to_file = True

    if args.quiet:
        config.logging.verbose = 0

    return config


def setup_logging(config: DuplicateManagerConfig):
    """Setup logging based on configuration."""
    level_map = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: logging.DEBUG,
    }
    level = level_map.get(config.logging.verbose, logging.DEBUG)

    handlers = [logging.StreamHandler()]

    if config.logging.log_to_file and config.logging.log_file:
        handlers.append(logging.FileHandler(config.logging.log_file, encoding='utf-8'))

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def confirm_action(config: DuplicateManagerConfig, result) -> bool:
    """Ask user to confirm the action."""
    if config.skip_confirmation:
        return True

    if config.execution_mode == ExecutionMode.DRY_RUN:
        return True

    print("\n" + "=" * 60)
    print("CONFIRMATION REQUIRED")
    print("=" * 60)
    print(f"\nMode: {config.execution_mode.name}")
    print(f"Duplicate groups: {result.duplicate_groups}")
    print(f"Files to process: {result.total_duplicates}")
    print(f"Space to recover: {format_size(result.space_recovered)}")

    if config.execution_mode == ExecutionMode.DELETE:
        print("\nWARNING: Files will be PERMANENTLY DELETED!")
    elif config.execution_mode == ExecutionMode.TRASH:
        print("\nFiles will be moved to system trash.")
    elif config.execution_mode == ExecutionMode.MOVE:
        print(f"\nFiles will be moved to: {config.move_destination}")

    response = input("\nProceed? [y/N]: ").strip().lower()
    return response in ('y', 'yes')


def interactive_callback(group: DuplicateGroupDecision) -> bool:
    """Interactive callback for group-by-group confirmation."""
    print("\n" + "-" * 60)
    print(f"GROUP #{group.group_id} ({group.files_count} files, {format_size(group.file_size)} each)")
    print(f"Hash: {group.hash_value}")
    print(f"Recoverable space: {format_size(group.space_recoverable)}")
    print()

    for decision in group.decisions:
        symbol = "[KEEP]  " if decision.action == FileAction.KEEP else "[REMOVE]"
        print(f"  {symbol} {decision.file_path}")
        print(f"           Reason: {decision.reason}")

    response = input("\nProcess this group? [Y/n/q]: ").strip().lower()

    if response == 'q':
        print("Aborting...")
        sys.exit(0)

    return response not in ('n', 'no')


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_argument_parser()
    parsed_args = parser.parse_args(args)

    # Build configuration
    try:
        config = build_config_from_args(parsed_args)
    except Exception as e:
        print(f"Error building configuration: {e}", file=sys.stderr)
        return 1

    # Save config if requested
    if parsed_args.save_config:
        try:
            save_config_to_yaml(config, parsed_args.save_config)
            print(f"Configuration saved to: {parsed_args.save_config}")
            if not config.source_directories:
                return 0
        except Exception as e:
            print(f"Error saving configuration: {e}", file=sys.stderr)
            return 1

    # Validate required arguments
    if not config.source_directories:
        parser.print_help()
        print("\nError: At least one directory is required.", file=sys.stderr)
        return 1

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    # Setup logging
    setup_logging(config)

    # Check algorithm availability
    if not DuplicateFinder.is_algorithm_available(config.hashing.algorithm.value):
        print(f"Error: Algorithm '{config.hashing.algorithm.value}' is not available.", file=sys.stderr)
        print(f"Available algorithms: {', '.join(DuplicateFinder.get_available_algorithms())}", file=sys.stderr)
        return 1

    # Print header
    if config.logging.verbose > 0:
        print("\n" + "=" * 60)
        print("  PhotoOrganizer - Duplicate Manager")
        print("=" * 60)
        print(f"\nMode: {config.execution_mode.name}")
        print(f"Algorithm: {config.hashing.algorithm.value.upper()}")
        print(f"Directories: {', '.join(config.source_directories)}")
        print()

    # Create manager
    manager = DuplicateManager(config)

    # Progress callback
    pbar = None

    def progress_callback(current: int, total: int, message: str):
        nonlocal pbar
        if config.performance.show_progress:
            if pbar is None or pbar.total != total:
                if pbar:
                    pbar.close()
                pbar = ProgressBar(total, message, disable=config.logging.verbose == 0)
            pbar.update(current, message)

    try:
        # Phase 1: Scan
        if config.logging.verbose > 0:
            print("Scanning for duplicates...")

        all_files, duplicate_result = manager.scan(progress_callback)

        if pbar:
            pbar.close()
            pbar = None

        if config.logging.verbose > 0:
            print(f"\nFiles scanned: {duplicate_result.total_files:,}")
            print(f"Duplicate groups: {len(duplicate_result.duplicate_groups):,}")
            print(f"Wasted space: {format_size(duplicate_result.total_wasted_space)}")

        if not duplicate_result.duplicate_groups:
            print("\nNo duplicates found.")
            return 0

        # Phase 2: Analyze
        if config.logging.verbose > 0:
            print("\nAnalyzing duplicate groups...")

        analysis_result = manager.analyze(duplicate_result, progress_callback)

        if pbar:
            pbar.close()
            pbar = None

        # Confirm action
        if not confirm_action(config, analysis_result):
            print("Aborted by user.")
            return 0

        # Phase 3: Execute
        if config.execution_mode != ExecutionMode.DRY_RUN:
            if config.logging.verbose > 0:
                print("\nExecuting actions...")

            int_callback = interactive_callback if config.execution_mode == ExecutionMode.INTERACTIVE else None
            final_result = manager.execute(analysis_result, progress_callback, int_callback)

            if pbar:
                pbar.close()
                pbar = None
        else:
            final_result = analysis_result

        # Print summary
        if config.logging.verbose > 0:
            print("\n" + "=" * 60)
            print("  SUMMARY")
            print("=" * 60)
            print(f"\n  Files scanned:     {final_result.total_files_scanned:,}")
            print(f"  Duplicate groups:  {final_result.duplicate_groups:,}")
            print(f"  Files kept:        {final_result.files_kept:,}")
            print(f"  Files deleted:     {final_result.files_deleted:,}")
            print(f"  Files moved:       {final_result.files_moved:,}")
            print(f"  Files trashed:     {final_result.files_trashed:,}")
            print(f"  Files errored:     {final_result.files_errored:,}")
            print(f"  Space recovered:   {format_size(final_result.space_recovered)}")

            if config.execution_mode == ExecutionMode.DRY_RUN:
                print("\n  [DRY-RUN] No files were actually modified.")

        # Generate reports
        if config.generate_csv or config.generate_json or config.generate_txt:
            output_dir = config.report_output_dir or os.getcwd()
            reporter = DuplicateReporter(final_result, output_dir)

            print("\nGenerating reports...")

            if config.generate_csv:
                csv_path = reporter.generate_csv()
                print(f"  CSV: {csv_path}")

            if config.generate_json:
                json_path = reporter.generate_json()
                print(f"  JSON: {json_path}")

            if config.generate_txt:
                txt_path = reporter.generate_txt()
                print(f"  TXT: {txt_path}")

        # Print errors if any
        if final_result.errors:
            print(f"\nErrors ({len(final_result.errors)}):")
            for error in final_result.errors[:10]:
                print(f"  - {error}")
            if len(final_result.errors) > 10:
                print(f"  ... and {len(final_result.errors) - 10} more")

        return 0 if final_result.success else 1

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 130

    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    finally:
        if pbar:
            pbar.close()


if __name__ == '__main__':
    sys.exit(main())
