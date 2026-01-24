# -*- coding: utf-8 -*-
"""
Configuration module for PhotoOrganizer.

This module provides configuration management for the duplicate detection
and management system, including YAML-based configuration loading.
"""

from .duplicate_config import (
    # Main configuration
    DuplicateManagerConfig,

    # Sub-configurations
    FolderFilter,
    ExtensionFilter,
    ConservationPolicy,
    HashingConfig,
    PerformanceConfig,
    LoggingConfig,

    # Enums
    ExecutionMode,
    ConservationCriterion,
    HashAlgorithm,
    FileAction,

    # Results
    FileDecision,
    DuplicateGroupDecision,
    ExecutionResult,

    # Loaders
    load_config_from_yaml,
    save_config_to_yaml,
)

__all__ = [
    # Main configuration
    'DuplicateManagerConfig',

    # Sub-configurations
    'FolderFilter',
    'ExtensionFilter',
    'ConservationPolicy',
    'HashingConfig',
    'PerformanceConfig',
    'LoggingConfig',

    # Enums
    'ExecutionMode',
    'ConservationCriterion',
    'HashAlgorithm',
    'FileAction',

    # Results
    'FileDecision',
    'DuplicateGroupDecision',
    'ExecutionResult',

    # Loaders
    'load_config_from_yaml',
    'save_config_to_yaml',
]
