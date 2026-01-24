# -*- coding: utf-8 -*-
"""
CLI module for PhotoOrganizer.

This module provides command-line interfaces for duplicate detection
and management operations.
"""

from .duplicate_cli import main as duplicate_main

__all__ = [
    'duplicate_main',
]
