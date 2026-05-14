# -*- coding: utf-8 -*-
"""
Reports module for PhotoOrganizer.

This module provides report generation capabilities for duplicate detection
and management operations, supporting CSV, JSON, and TXT formats.
"""

from .duplicate_reporter import (
    DuplicateReporter,
    generate_all_reports,
    generate_csv_report,
    generate_json_report,
    generate_txt_report,
)

__all__ = [
    'DuplicateReporter',
    'generate_csv_report',
    'generate_json_report',
    'generate_txt_report',
    'generate_all_reports',
]
