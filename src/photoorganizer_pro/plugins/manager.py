"""PluginManager — découverte + invocation des plugins.

Découverte
----------

* **Entry points** (``photoorganizer_pro.plugins``) — la voie officielle
  pour les plugins distribués via pip.
* **Dossier local** (``%LOCALAPPDATA%\\PhotoOrganizer\\plugins\\``) — un
  ``.py`` posé là est chargé dynamiquement (utile pour des plugins
  perso ou des tests).

Invocation
----------

Chaque hook (``pre_organize``, ``filter_file``, ``rename``,
``post_action``, ``post_organize``) est appelé sur tous les plugins
dans l'ordre d'enregistrement. Les exceptions levées par un plugin sont
attrapées et loguées via le ``logging`` standard, le batch continue.

Sécurité
--------

Charger un ``.py`` arbitraire = exécuter du code arbitraire. Le dossier
de plugins local est sous ``%LOCALAPPDATA%`` (donc privé à l'utilisateur)
et le chargement émet un warning au démarrage. Pour les plugins via
entry points, l'utilisateur a explicitement fait ``pip install`` du
paquet.
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BasePlugin, OrganizeContext, PluginAction

logger = logging.getLogger(__name__)


def _user_plugins_dir() -> Path:
    """Dossier local où l'utilisateur dépose ses plugins ``.py``."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    return base / "PhotoOrganizer" / "plugins"


class PluginManager:
    """Découvre et invoque les plugins enregistrés."""

    ENTRY_POINT_GROUP = "photoorganizer_pro.plugins"

    def __init__(self):
        self._plugins: List[BasePlugin] = []

    # -----------------------------------------------------------------
    # Enregistrement
    # -----------------------------------------------------------------
    def register(self, plugin: BasePlugin) -> None:
        """Enregistre un plugin déjà instancié."""
        if not isinstance(plugin, BasePlugin):
            raise TypeError(f"register() attend une instance de BasePlugin, reçu {type(plugin)!r}")
        # Refuse les doublons (même name) — un plugin doit être nommé uniquement
        existing_names = {p.name for p in self._plugins}
        if plugin.name in existing_names and plugin.name != "unnamed":
            logger.warning("Plugin '%s' déjà enregistré — duplication ignorée", plugin.name)
            return
        self._plugins.append(plugin)
        logger.info("Plugin enregistré : %s", plugin.describe())

    def clear(self) -> None:
        """Vide la liste des plugins. Surtout utile en tests."""
        self._plugins = []

    def list_plugins(self) -> List[BasePlugin]:
        """Liste les plugins enregistrés (copie défensive)."""
        return list(self._plugins)

    # -----------------------------------------------------------------
    # Découverte automatique
    # -----------------------------------------------------------------
    def discover_entry_points(self) -> int:
        """Cherche les plugins déclarés via entry points pip. Retourne le compte."""
        try:
            # Python 3.10+ : importlib.metadata.entry_points(group=...)
            from importlib.metadata import entry_points

            try:
                eps = entry_points(group=self.ENTRY_POINT_GROUP)
            except TypeError:
                # Compat Python 3.9 (rare ici car requires-python>=3.11)
                eps = entry_points().get(self.ENTRY_POINT_GROUP, [])
        except ImportError:
            return 0

        count = 0
        for ep in eps:
            try:
                klass = ep.load()
                instance = klass()
                if isinstance(instance, BasePlugin):
                    self.register(instance)
                    count += 1
                else:
                    logger.warning(
                        "Entry point %s ne renvoie pas un BasePlugin (got %s)", ep.name, type(instance)
                    )
            except Exception as exc:  # noqa: BLE001
                logger.error("Échec chargement entry point %s : %s", ep.name, exc)
        return count

    def discover_user_plugins(self, plugins_dir: Optional[Path] = None) -> int:
        """Charge tous les ``.py`` du dossier utilisateur. Retourne le compte."""
        plugins_dir = plugins_dir or _user_plugins_dir()
        if not plugins_dir.exists():
            return 0

        count = 0
        for py in sorted(plugins_dir.glob("*.py")):
            if py.name.startswith("_"):
                continue  # convention : _foo.py = privé
            try:
                module = self._load_module_from_file(py)
                added = self._register_plugins_from_module(module)
                count += added
            except Exception as exc:  # noqa: BLE001
                logger.error("Échec chargement %s : %s", py, exc)
        if count:
            logger.warning(
                "%d plugin(s) chargé(s) depuis %s — du code arbitraire a été exécuté.",
                count,
                plugins_dir,
            )
        return count

    @staticmethod
    def _load_module_from_file(py: Path) -> Any:
        spec = importlib.util.spec_from_file_location(f"_user_plugin_{py.stem}", py)
        if spec is None or spec.loader is None:
            raise ImportError(f"Impossible de charger {py}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def _register_plugins_from_module(self, module: Any) -> int:
        """Enregistre toutes les sous-classes BasePlugin trouvées dans ``module``."""
        count = 0
        for _name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BasePlugin)
                and obj is not BasePlugin
                and obj.__module__ == module.__name__
            ):
                try:
                    instance = obj()
                    self.register(instance)
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    logger.error("Plugin %s instanciation échouée : %s", obj.__name__, exc)
        return count

    def discover_all(self, user_plugins_dir: Optional[Path] = None) -> int:
        """Découvre via entry points + dossier utilisateur. Retourne le total."""
        return self.discover_entry_points() + self.discover_user_plugins(user_plugins_dir)

    # -----------------------------------------------------------------
    # Invocation des hooks (avec garde try/except autour de chaque)
    # -----------------------------------------------------------------
    def call_pre_organize(self, context: OrganizeContext) -> None:
        for p in self._plugins:
            self._safe_call(p, "pre_organize", context)

    def call_filter_file(self, path: Path, metadata: Dict[str, Any], context: OrganizeContext) -> bool:
        """True ssi TOUS les plugins acceptent le fichier."""
        for p in self._plugins:
            try:
                if not p.filter_file(path, metadata, context):
                    logger.debug("Plugin %s a exclu %s", p.name, path.name)
                    return False
            except Exception as exc:  # noqa: BLE001
                logger.error("Plugin %s.filter_file a levé : %s", p.name, exc)
                # On considère qu'une exception ne doit pas masquer le fichier.
                continue
        return True

    def call_rename(
        self,
        path: Path,
        metadata: Dict[str, Any],
        proposed_name: str,
        context: OrganizeContext,
    ) -> str:
        """Donne la dernière proposition non-None. Sinon ``proposed_name``."""
        result = proposed_name
        for p in self._plugins:
            try:
                new = p.rename(path, metadata, result, context)
                if new is not None:
                    if not isinstance(new, str) or not new:
                        logger.warning(
                            "Plugin %s.rename a renvoyé '%r', ignoré", p.name, new
                        )
                        continue
                    result = new
            except Exception as exc:  # noqa: BLE001
                logger.error("Plugin %s.rename a levé : %s", p.name, exc)
        return result

    def call_post_action(
        self,
        source: Path,
        destination: Path,
        action: PluginAction,
        context: OrganizeContext,
    ) -> None:
        for p in self._plugins:
            self._safe_call(p, "post_action", source, destination, action, context)

    def call_post_organize(self, context: OrganizeContext) -> None:
        for p in self._plugins:
            self._safe_call(p, "post_organize", context)

    # -----------------------------------------------------------------
    # Internes
    # -----------------------------------------------------------------
    def _safe_call(self, plugin: BasePlugin, method_name: str, *args: Any) -> None:
        try:
            getattr(plugin, method_name)(*args)
        except Exception as exc:  # noqa: BLE001
            logger.error("Plugin %s.%s a levé : %s", plugin.name, method_name, exc)


# ---------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------
_default_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Singleton process-wide. Lazy-init."""
    global _default_manager
    if _default_manager is None:
        _default_manager = PluginManager()
    return _default_manager


def reset_plugin_manager() -> None:
    """Réinitialise le singleton. Surtout utile en tests."""
    global _default_manager
    _default_manager = None
