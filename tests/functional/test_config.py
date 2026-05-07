"""Tests fonctionnels du gestionnaire de config."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from utils.config import ConfigManager, AppConfig  # noqa: E402


def test_config_creates_dir(tmp_path):
    cm = ConfigManager(config_dir=str(tmp_path))
    assert cm.config_dir.exists()
    assert cm.presets_dir.exists()


def test_config_save_load_roundtrip(tmp_path):
    cm = ConfigManager(config_dir=str(tmp_path))
    cm.set("theme", "light")
    cm.set("default_action", "move")
    cm.save()
    # Recharger
    cm2 = ConfigManager(config_dir=str(tmp_path))
    assert cm2.config.theme == "light"
    assert cm2.config.default_action == "move"


def test_recent_sources_limit(tmp_path):
    cm = ConfigManager(config_dir=str(tmp_path))
    for i in range(15):
        cm.add_recent_source(f"/some/path/{i}")
    assert len(cm.config.recent_sources) <= cm.config.max_recent
    # Le plus récent en tête
    assert cm.config.recent_sources[0] == "/some/path/14"


def test_preset_save_load_delete(tmp_path):
    cm = ConfigManager(config_dir=str(tmp_path))
    cm.save_preset("my_preset", {"foo": "bar"})
    loaded = cm.load_preset("my_preset")
    assert loaded == {"foo": "bar"}
    assert "my_preset" in cm.list_presets()
    cm.delete_preset("my_preset")
    assert "my_preset" not in cm.list_presets()


def test_reset_to_defaults(tmp_path):
    cm = ConfigManager(config_dir=str(tmp_path))
    cm.set("theme", "light")
    cm.reset_to_defaults()
    assert cm.config.theme == AppConfig().theme


def test_corrupt_config_falls_back_to_default(tmp_path):
    """Un fichier config.json corrompu ne doit pas crasher l'init."""
    config_dir = tmp_path
    config_dir.mkdir(exist_ok=True)
    (config_dir / "config.json").write_text("not-json{")
    cm = ConfigManager(config_dir=str(config_dir))
    # Charge les valeurs par défaut
    assert cm.config.theme == AppConfig().theme
