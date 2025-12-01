"""
Preview and dry-run utilities for file operations
Allows users to see what will happen before executing operations
"""

import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FileOperationPreview:
    """Preview file operations without executing them"""

    def __init__(self):
        """Initialize preview tracker"""
        self.operations = []
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'operations_by_type': {},
            'files_by_destination': {},
            'errors': []
        }

    def add_operation(self, operation_type: str, source: str, destination: str,
                     metadata: Optional[Dict] = None) -> None:
        """
        Add a file operation to preview

        Args:
            operation_type: Type of operation ('copy', 'move', 'rename', 'delete')
            source: Source file path
            destination: Destination file path (or None for delete)
            metadata: Optional metadata about the file
        """
        try:
            file_size = os.path.getsize(source) if os.path.exists(source) else 0

            operation = {
                'type': operation_type,
                'source': source,
                'destination': destination,
                'source_name': os.path.basename(source),
                'destination_name': os.path.basename(destination) if destination else None,
                'file_size': file_size,
                'metadata': metadata or {}
            }

            self.operations.append(operation)

            # Update stats
            self.stats['total_files'] += 1
            self.stats['total_size'] += file_size

            if operation_type not in self.stats['operations_by_type']:
                self.stats['operations_by_type'][operation_type] = 0
            self.stats['operations_by_type'][operation_type] += 1

            if destination:
                dest_dir = os.path.dirname(destination)
                if dest_dir not in self.stats['files_by_destination']:
                    self.stats['files_by_destination'][dest_dir] = 0
                self.stats['files_by_destination'][dest_dir] += 1

        except Exception as e:
            logger.error(f"Error adding operation preview: {e}")
            self.stats['errors'].append(str(e))

    def get_operations(self) -> List[Dict]:
        """Get list of all operations"""
        return self.operations

    def get_stats(self) -> Dict:
        """Get preview statistics"""
        return self.stats

    def get_summary(self) -> str:
        """
        Get human-readable summary of operations

        Returns:
            Summary string
        """
        lines = [
            "=" * 60,
            "FILE OPERATIONS PREVIEW",
            "=" * 60,
            f"Total files: {self.stats['total_files']}",
            f"Total size: {self._format_size(self.stats['total_size'])}",
            "",
            "Operations by type:"
        ]

        for op_type, count in self.stats['operations_by_type'].items():
            lines.append(f"  {op_type}: {count} files")

        if self.stats['files_by_destination']:
            lines.append("")
            lines.append("Top destination directories:")
            sorted_dests = sorted(
                self.stats['files_by_destination'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for dest, count in sorted_dests[:10]:
                lines.append(f"  {count} files -> {dest}")

        if self.stats['errors']:
            lines.append("")
            lines.append(f"Errors encountered: {len(self.stats['errors'])}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def get_detailed_preview(self, max_items: int = 50) -> str:
        """
        Get detailed preview of operations

        Args:
            max_items: Maximum number of operations to show

        Returns:
            Detailed preview string
        """
        lines = [self.get_summary(), "", "Detailed operations:"]

        for i, op in enumerate(self.operations[:max_items], 1):
            lines.append(f"\n{i}. {op['type'].upper()}")
            lines.append(f"   From: {op['source']}")
            if op['destination']:
                lines.append(f"   To:   {op['destination']}")
            lines.append(f"   Size: {self._format_size(op['file_size'])}")

            if op['metadata']:
                lines.append(f"   Metadata: {op['metadata']}")

        if len(self.operations) > max_items:
            lines.append(f"\n... and {len(self.operations) - max_items} more operations")

        return "\n".join(lines)

    def check_conflicts(self) -> List[Dict]:
        """
        Check for potential conflicts in operations

        Returns:
            List of conflict warnings
        """
        conflicts = []
        destination_map = {}

        for i, op in enumerate(self.operations):
            if not op['destination']:
                continue

            dest = op['destination']

            # Check for duplicate destinations
            if dest in destination_map:
                conflicts.append({
                    'type': 'duplicate_destination',
                    'message': f"Multiple files will be written to {dest}",
                    'operations': [destination_map[dest], i],
                    'severity': 'error'
                })
            else:
                destination_map[dest] = i

            # Check if destination already exists
            if os.path.exists(dest):
                conflicts.append({
                    'type': 'file_exists',
                    'message': f"Destination file already exists: {dest}",
                    'operation': i,
                    'severity': 'warning'
                })

            # Check if destination directory is writable
            dest_dir = os.path.dirname(dest)
            if dest_dir and not os.access(dest_dir, os.W_OK):
                if not os.path.exists(dest_dir):
                    conflicts.append({
                        'type': 'directory_missing',
                        'message': f"Destination directory does not exist: {dest_dir}",
                        'operation': i,
                        'severity': 'error'
                    })
                else:
                    conflicts.append({
                        'type': 'permission_denied',
                        'message': f"No write permission for directory: {dest_dir}",
                        'operation': i,
                        'severity': 'error'
                    })

        return conflicts

    def estimate_time(self, avg_speed_mbps: float = 50.0) -> Dict:
        """
        Estimate time to complete operations

        Args:
            avg_speed_mbps: Average copy speed in MB/s

        Returns:
            Dictionary with time estimates
        """
        total_mb = self.stats['total_size'] / (1024 * 1024)
        estimated_seconds = total_mb / avg_speed_mbps

        return {
            'total_mb': round(total_mb, 2),
            'estimated_seconds': round(estimated_seconds, 2),
            'estimated_minutes': round(estimated_seconds / 60, 2),
            'estimated_hours': round(estimated_seconds / 3600, 2)
        }

    def check_disk_space(self, operation_type: str = 'copy') -> Dict:
        """
        Check if there's enough disk space for operations

        Args:
            operation_type: Type of operation ('copy' requires space, 'move' may not)

        Returns:
            Dictionary with disk space info
        """
        results = {}

        if operation_type == 'copy':
            # Group by destination drive
            space_needed_by_drive = {}

            for op in self.operations:
                if not op['destination']:
                    continue

                # Get drive/mount point
                dest_drive = os.path.splitdrive(op['destination'])[0] or '/'

                if dest_drive not in space_needed_by_drive:
                    space_needed_by_drive[dest_drive] = 0

                space_needed_by_drive[dest_drive] += op['file_size']

            # Check available space on each drive
            for drive, needed in space_needed_by_drive.items():
                try:
                    stat = os.statvfs(drive) if hasattr(os, 'statvfs') else None
                    if stat:
                        available = stat.f_bavail * stat.f_frsize
                    else:
                        # Windows
                        import shutil
                        available = shutil.disk_usage(drive).free

                    results[drive] = {
                        'needed': needed,
                        'available': available,
                        'sufficient': available > needed,
                        'margin': available - needed
                    }

                except Exception as e:
                    logger.error(f"Error checking disk space for {drive}: {e}")
                    results[drive] = {'error': str(e)}

        return results

    def _format_size(self, bytes_size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"

    def export_to_file(self, output_path: str, format: str = 'txt') -> bool:
        """
        Export preview to file

        Args:
            output_path: Path to output file
            format: Output format ('txt', 'json', 'csv')

        Returns:
            True if successful
        """
        try:
            if format == 'txt':
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(self.get_detailed_preview(max_items=len(self.operations)))

            elif format == 'json':
                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'operations': self.operations,
                        'stats': self.stats,
                        'conflicts': self.check_conflicts()
                    }, f, indent=2, default=str)

            elif format == 'csv':
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Operation', 'Source', 'Destination', 'Size'])
                    for op in self.operations:
                        writer.writerow([
                            op['type'],
                            op['source'],
                            op['destination'] or '',
                            op['file_size']
                        ])

            logger.info(f"Preview exported to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting preview: {e}")
            return False

    def clear(self):
        """Clear all operations and reset stats"""
        self.operations.clear()
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'operations_by_type': {},
            'files_by_destination': {},
            'errors': []
        }
