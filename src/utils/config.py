"""
Module de gestion de la configuration.
Sauvegarde et chargement des préférences utilisateur.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Configuration de l'application."""
    # Interface
    theme: str = "dark"
    language: str = "fr"
    window_width: int = 1200
    window_height: int = 800
    window_x: Optional[int] = None
    window_y: Optional[int] = None

    # Dossiers récents
    recent_sources: List[str] = field(default_factory=list)
    recent_destinations: List[str] = field(default_factory=list)
    max_recent: int = 10

    # Organisation par défaut
    default_action: str = "copy"  # "copy" ou "move"
    default_organize_by: str = "date"
    default_date_format: str = "year/month/day"
    default_recursive: bool = True
    include_images: bool = True
    include_raw: bool = True
    include_videos: bool = False

    # GPS
    geocoding_enabled: bool = True
    max_distance_km: float = 1.0

    # Cache
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    max_cache_size_mb: int = 100

    # Logs
    log_level: str = "INFO"
    log_to_file: bool = True

    # API Keys
    positionstack_api_key: str = ""

    # ---- Planification automatique (Lot E5) ----
    # Une seule planification quotidienne ; pour des règles plus fines
    # l'utilisateur peut combiner avec le Planificateur Windows natif.
    schedule_enabled: bool = False
    schedule_time: str = "23:00"            # format HH:MM
    schedule_source: str = ""               # source(s), séparées par ;
    schedule_destination: str = ""
    schedule_preset: str = ""               # nom du preset à appliquer (vide = défauts)

    # ---- État UI persisté entre sessions ----
    rename_collapsed: bool = False          # pliage de la section Renommage


class ConfigManager:
    """Gestionnaire de configuration."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialise le gestionnaire de configuration.

        Args:
            config_dir: Répertoire de configuration (auto-détecté si non fourni)
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = self._get_default_config_dir()

        self.config_file = self.config_dir / "config.json"
        self.presets_dir = self.config_dir / "presets"

        # Créer les répertoires
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.presets_dir.mkdir(parents=True, exist_ok=True)

        # Charger la configuration
        self._config = self._load_config()

    def _get_default_config_dir(self) -> Path:
        """Retourne le répertoire de configuration par défaut."""
        if os.name == 'nt':  # Windows
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
            return Path(base) / 'PhotoOrganizer'
        else:  # Linux/Mac
            return Path.home() / '.config' / 'PhotoOrganizer'

    def _load_config(self) -> AppConfig:
        """Charge la configuration depuis le fichier."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return AppConfig(**{k: v for k, v in data.items()
                                   if k in AppConfig.__dataclass_fields__})
            except Exception as e:
                logger.warning(f"Erreur chargement config: {e}")

        return AppConfig()

    def save(self):
        """Sauvegarde la configuration."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration."""
        return getattr(self._config, key, default)

    def set(self, key: str, value: Any):
        """Définit une valeur de configuration."""
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            self.save()

    @property
    def config(self) -> AppConfig:
        """Accès direct à la configuration."""
        return self._config

    def add_recent_source(self, path: str):
        """Ajoute un dossier source aux récents."""
        self._add_recent(self._config.recent_sources, path)

    def add_recent_destination(self, path: str):
        """Ajoute un dossier destination aux récents."""
        self._add_recent(self._config.recent_destinations, path)

    def _add_recent(self, recent_list: List[str], path: str):
        """Ajoute un chemin à une liste de récents."""
        if path in recent_list:
            recent_list.remove(path)
        recent_list.insert(0, path)

        # Limiter la taille
        while len(recent_list) > self._config.max_recent:
            recent_list.pop()

        self.save()

    def save_preset(self, name: str, options: Dict[str, Any]):
        """Sauvegarde un preset d'organisation."""
        preset_file = self.presets_dir / f"{name}.json"
        try:
            with open(preset_file, 'w', encoding='utf-8') as f:
                json.dump(options, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde preset: {e}")

    def load_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """Charge un preset d'organisation."""
        preset_file = self.presets_dir / f"{name}.json"
        if preset_file.exists():
            try:
                with open(preset_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur chargement preset: {e}")
        return None

    def list_presets(self) -> List[str]:
        """Liste les presets disponibles."""
        return [f.stem for f in self.presets_dir.glob("*.json")]

    def delete_preset(self, name: str):
        """Supprime un preset."""
        preset_file = self.presets_dir / f"{name}.json"
        if preset_file.exists():
            preset_file.unlink()

    def reset_to_defaults(self):
        """Réinitialise la configuration aux valeurs par défaut."""
        self._config = AppConfig()
        self.save()


# Instance globale
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Retourne l'instance globale du gestionnaire de configuration."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
