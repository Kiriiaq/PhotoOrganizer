# -*- coding: utf-8 -*-
"""
Report generation for duplicate detection and management.

This module generates detailed reports in CSV, JSON, and TXT formats
for duplicate file analysis and management operations.
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from src.config.duplicate_config import (
    ExecutionResult,
    DuplicateGroupDecision,
    FileDecision,
    FileAction,
    ExecutionMode,
)

logger = logging.getLogger(__name__)


class DuplicateReporter:
    """
    Report generator for duplicate management operations.

    Supports CSV, JSON, and human-readable TXT formats.
    """

    def __init__(
        self,
        result: ExecutionResult,
        output_dir: Optional[str] = None,
        base_filename: str = "duplicate_report"
    ):
        """
        Initialize the reporter.

        Args:
            result: ExecutionResult from duplicate management
            output_dir: Directory for output files (defaults to current dir)
            base_filename: Base name for report files
        """
        self.result = result
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.base_filename = base_filename

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_timestamp(self) -> str:
        """Get formatted timestamp for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def generate_csv(self, include_timestamp: bool = True) -> str:
        """
        Generate CSV report.

        Format:
        group_id,hash,file_size,file_path,action,reason,target_path

        Args:
            include_timestamp: Include timestamp in filename

        Returns:
            Path to generated CSV file
        """
        timestamp = f"_{self._get_timestamp()}" if include_timestamp else ""
        filename = f"{self.base_filename}{timestamp}.csv"
        filepath = self.output_dir / filename

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    'group_id',
                    'hash',
                    'file_size',
                    'file_size_formatted',
                    'file_path',
                    'action',
                    'reason',
                    'target_path',
                    'creation_time',
                    'modification_time'
                ])

                # Data rows
                for group in self.result.group_decisions:
                    for decision in group.decisions:
                        writer.writerow([
                            group.group_id,
                            group.hash_value,
                            decision.file_size,
                            self._format_size(decision.file_size),
                            decision.file_path,
                            decision.action.value,
                            decision.reason,
                            decision.target_path or '',
                            decision.creation_time.isoformat() if decision.creation_time else '',
                            decision.modification_time.isoformat() if decision.modification_time else ''
                        ])

            logger.info(f"CSV report generated: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error generating CSV report: {e}")
            raise

    def generate_json(self, include_timestamp: bool = True, pretty: bool = True) -> str:
        """
        Generate JSON report.

        Args:
            include_timestamp: Include timestamp in filename
            pretty: Use pretty formatting (indentation)

        Returns:
            Path to generated JSON file
        """
        timestamp = f"_{self._get_timestamp()}" if include_timestamp else ""
        filename = f"{self.base_filename}{timestamp}.json"
        filepath = self.output_dir / filename

        try:
            report_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'execution_mode': self.result.execution_mode.name,
                    'start_time': self.result.start_time.isoformat() if self.result.start_time else None,
                    'end_time': self.result.end_time.isoformat() if self.result.end_time else None,
                    'duration_seconds': self.result.duration_seconds,
                },
                'summary': {
                    'total_files_scanned': self.result.total_files_scanned,
                    'duplicate_groups': self.result.duplicate_groups,
                    'total_duplicates': self.result.total_duplicates,
                    'files_kept': self.result.files_kept,
                    'files_deleted': self.result.files_deleted,
                    'files_moved': self.result.files_moved,
                    'files_trashed': self.result.files_trashed,
                    'files_errored': self.result.files_errored,
                    'space_scanned': self.result.space_scanned,
                    'space_scanned_formatted': self._format_size(self.result.space_scanned),
                    'space_duplicates': self.result.space_duplicates,
                    'space_duplicates_formatted': self._format_size(self.result.space_duplicates),
                    'space_recovered': self.result.space_recovered,
                    'space_recovered_formatted': self._format_size(self.result.space_recovered),
                    'success': self.result.success,
                },
                'groups': [
                    {
                        'group_id': group.group_id,
                        'hash': group.hash_value,
                        'file_size': group.file_size,
                        'file_size_formatted': self._format_size(group.file_size),
                        'files_count': group.files_count,
                        'space_recoverable': group.space_recoverable,
                        'space_recoverable_formatted': self._format_size(group.space_recoverable),
                        'files': [
                            {
                                'path': decision.file_path,
                                'action': decision.action.value,
                                'reason': decision.reason,
                                'target_path': decision.target_path,
                                'creation_time': decision.creation_time.isoformat() if decision.creation_time else None,
                                'modification_time': decision.modification_time.isoformat() if decision.modification_time else None,
                            }
                            for decision in group.decisions
                        ]
                    }
                    for group in self.result.group_decisions
                ],
                'errors': self.result.errors,
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2 if pretty else None, ensure_ascii=False)

            logger.info(f"JSON report generated: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")
            raise

    def generate_txt(self, include_timestamp: bool = True) -> str:
        """
        Generate human-readable TXT report.

        Args:
            include_timestamp: Include timestamp in filename

        Returns:
            Path to generated TXT file
        """
        timestamp = f"_{self._get_timestamp()}" if include_timestamp else ""
        filename = f"{self.base_filename}{timestamp}.txt"
        filepath = self.output_dir / filename

        try:
            lines = []

            # Header
            lines.append("=" * 70)
            lines.append("  PhotoOrganizer - Duplicate Report")
            lines.append("=" * 70)
            lines.append("")
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"Mode: {self.result.execution_mode.name}")

            if self.result.start_time and self.result.end_time:
                lines.append(f"Duration: {self.result.duration_seconds:.2f} seconds")

            lines.append("")

            # Summary section
            lines.append("-" * 70)
            lines.append("  SUMMARY")
            lines.append("-" * 70)
            lines.append("")
            lines.append(f"  Files scanned:     {self.result.total_files_scanned:,}")
            lines.append(f"  Duplicate groups:  {self.result.duplicate_groups:,}")
            lines.append(f"  Total duplicates:  {self.result.total_duplicates:,}")
            lines.append("")
            lines.append(f"  Files kept:        {self.result.files_kept:,}")
            lines.append(f"  Files deleted:     {self.result.files_deleted:,}")
            lines.append(f"  Files moved:       {self.result.files_moved:,}")
            lines.append(f"  Files trashed:     {self.result.files_trashed:,}")
            lines.append(f"  Files with errors: {self.result.files_errored:,}")
            lines.append("")
            lines.append(f"  Space in duplicates: {self._format_size(self.result.space_duplicates)}")
            lines.append(f"  Space recovered:     {self._format_size(self.result.space_recovered)}")
            lines.append("")

            # Status
            if self.result.execution_mode == ExecutionMode.DRY_RUN:
                lines.append("  [DRY-RUN MODE] No files were actually modified.")
                lines.append("")

            if self.result.success:
                lines.append("  Status: SUCCESS")
            else:
                lines.append("  Status: COMPLETED WITH ERRORS")

            lines.append("")

            # Groups section
            lines.append("-" * 70)
            lines.append("  DUPLICATE GROUPS")
            lines.append("-" * 70)
            lines.append("")

            for group in self.result.group_decisions:
                lines.append(f"GROUP #{group.group_id} ({group.files_count} files, {self._format_size(group.file_size)} each)")
                lines.append(f"  Hash: {group.hash_value}")
                lines.append(f"  Recoverable space: {self._format_size(group.space_recoverable)}")
                lines.append("")

                for decision in group.decisions:
                    action_symbol = self._get_action_symbol(decision.action)
                    lines.append(f"  [{action_symbol}] {decision.file_path}")
                    lines.append(f"       Reason: {decision.reason}")

                    if decision.target_path:
                        lines.append(f"       Target: {decision.target_path}")

                    if decision.creation_time:
                        lines.append(f"       Created: {decision.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")

                lines.append("")

            # Errors section
            if self.result.errors:
                lines.append("-" * 70)
                lines.append("  ERRORS")
                lines.append("-" * 70)
                lines.append("")

                for error in self.result.errors:
                    lines.append(f"  - {error}")

                lines.append("")

            # Footer
            lines.append("=" * 70)
            lines.append("  End of Report")
            lines.append("=" * 70)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            logger.info(f"TXT report generated: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error generating TXT report: {e}")
            raise

    def _get_action_symbol(self, action: FileAction) -> str:
        """Get a symbol for file action display."""
        symbols = {
            FileAction.KEEP: "KEEP   ",
            FileAction.DELETE: "DELETE ",
            FileAction.MOVE: "MOVE   ",
            FileAction.TRASH: "TRASH  ",
            FileAction.IGNORE: "IGNORE ",
            FileAction.ERROR: "ERROR  ",
        }
        return symbols.get(action, "UNKNOWN")

    def generate_all(self, include_timestamp: bool = True) -> dict:
        """
        Generate all report formats.

        Args:
            include_timestamp: Include timestamp in filenames

        Returns:
            Dictionary with paths to generated files
        """
        return {
            'csv': self.generate_csv(include_timestamp),
            'json': self.generate_json(include_timestamp),
            'txt': self.generate_txt(include_timestamp),
        }


# Utility functions for direct use

def generate_csv_report(
    result: ExecutionResult,
    output_dir: Optional[str] = None,
    base_filename: str = "duplicate_report"
) -> str:
    """Generate CSV report."""
    reporter = DuplicateReporter(result, output_dir, base_filename)
    return reporter.generate_csv()


def generate_json_report(
    result: ExecutionResult,
    output_dir: Optional[str] = None,
    base_filename: str = "duplicate_report"
) -> str:
    """Generate JSON report."""
    reporter = DuplicateReporter(result, output_dir, base_filename)
    return reporter.generate_json()


def generate_txt_report(
    result: ExecutionResult,
    output_dir: Optional[str] = None,
    base_filename: str = "duplicate_report"
) -> str:
    """Generate TXT report."""
    reporter = DuplicateReporter(result, output_dir, base_filename)
    return reporter.generate_txt()


def generate_all_reports(
    result: ExecutionResult,
    output_dir: Optional[str] = None,
    base_filename: str = "duplicate_report"
) -> dict:
    """Generate all report formats."""
    reporter = DuplicateReporter(result, output_dir, base_filename)
    return reporter.generate_all()
