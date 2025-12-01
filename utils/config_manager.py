"""
Configuration Manager for Photo Organizer
Handles user preferences and application settings
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration and user preferences"""

    DEFAULT_CONFIG = {
        'api_keys': {
            'positionstack': '',  # User should add their own API key
        },
        'preferences': {
            'last_source_dir': '',
            'last_destination_dir': '',
            'default_action': 'copy',  # 'copy' or 'move'
            'use_geocoding': False,
            'window_width': 1200,
            'window_height': 800,
            'theme': 'light',  # 'light' or 'dark'
            'language': 'fr',  # 'fr' or 'en'
            'log_level': 'INFO',
        },
        'recent_folders': {
            'source': [],  # Last 10 source folders
            'destination': [],  # Last 10 destination folders
        },
        'organization_presets': {},  # User-defined organization presets
        'metadata_cache_enabled': True,
        'metadata_cache_ttl': 86400,  # 24 hours in seconds
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager

        Args:
            config_file: Path to config file. If None, uses default location
        """
        if config_file is None:
            # Use AppData on Windows, ~/.config on Unix
            if os.name == 'nt':
                config_dir = Path(os.environ.get('APPDATA', '')) / 'PhotoOrganizer'
            else:
                config_dir = Path.home() / '.config' / 'PhotoOrganizer'

            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / 'config.json'
        else:
            self.config_file = Path(config_file)

        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                config = self._merge_configs(self.DEFAULT_CONFIG.copy(), user_config)
                logger.info(f"Configuration loaded from {self.config_file}")
                return config
            except Exception as e:
                logger.error(f"Error loading config: {e}. Using defaults.")
                return self.DEFAULT_CONFIG.copy()
        else:
            logger.info("No config file found. Using defaults.")
            return self.DEFAULT_CONFIG.copy()

    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Recursively merge user config with defaults"""
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                default[key] = self._merge_configs(default[key], value)
            else:
                default[key] = value
        return default

    def save(self) -> bool:
        """
        Save current configuration to file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation

        Args:
            key_path: Dot-separated path (e.g., 'preferences.theme')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation

        Args:
            key_path: Dot-separated path (e.g., 'preferences.theme')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config

        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value

    def add_recent_folder(self, folder_type: str, path: str, max_items: int = 10) -> None:
        """
        Add a folder to recent folders list

        Args:
            folder_type: 'source' or 'destination'
            path: Folder path
            max_items: Maximum number of recent items to keep
        """
        if folder_type not in ['source', 'destination']:
            return

        recent = self.config['recent_folders'][folder_type]

        # Remove if already exists
        if path in recent:
            recent.remove(path)

        # Add to beginning
        recent.insert(0, path)

        # Limit to max_items
        self.config['recent_folders'][folder_type] = recent[:max_items]

    def get_recent_folders(self, folder_type: str) -> list:
        """
        Get recent folders list

        Args:
            folder_type: 'source' or 'destination'

        Returns:
            List of recent folder paths
        """
        return self.config['recent_folders'].get(folder_type, [])

    def save_preset(self, name: str, preset_data: Dict) -> None:
        """
        Save an organization preset

        Args:
            name: Preset name
            preset_data: Dictionary containing preset configuration
        """
        self.config['organization_presets'][name] = preset_data

    def get_preset(self, name: str) -> Optional[Dict]:
        """
        Get an organization preset

        Args:
            name: Preset name

        Returns:
            Preset data or None if not found
        """
        return self.config['organization_presets'].get(name)

    def delete_preset(self, name: str) -> bool:
        """
        Delete an organization preset

        Args:
            name: Preset name

        Returns:
            True if deleted, False if not found
        """
        if name in self.config['organization_presets']:
            del self.config['organization_presets'][name]
            return True
        return False

    def list_presets(self) -> list:
        """Get list of all preset names"""
        return list(self.config['organization_presets'].keys())

    def get_api_key(self, service: str) -> str:
        """
        Get API key for a service

        Args:
            service: Service name (e.g., 'positionstack')

        Returns:
            API key or empty string if not set
        """
        return self.config['api_keys'].get(service, '')

    def set_api_key(self, service: str, key: str) -> None:
        """
        Set API key for a service

        Args:
            service: Service name
            key: API key
        """
        self.config['api_keys'][service] = key

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self.config = self.DEFAULT_CONFIG.copy()
        logger.info("Configuration reset to defaults")


# Global config instance
_config_instance = None


def get_config() -> ConfigManager:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
