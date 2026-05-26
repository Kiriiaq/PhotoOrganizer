"""PhotoOrganizer Pro — Plugin API (**DEFERRED v3.0+**).

⚠️ Gelé depuis le pivot économique 2026-05-26.
Entry point group ``photoorganizer_pro.plugins`` commenté dans ``pyproject.toml``.
Tests skippés via ``@pytest.mark.skip(reason="Deferred to v3.0+")``.
Code conservé intact pour réactivation conditionnelle. Cf. ``../__init__.py``.

Permet à des utilisateurs avancés ou des intégrateurs d'étendre la
logique d'organisation **sans modifier le core**. Hooks supportés :

* ``pre_organize(context)`` — appelé une fois avant un batch ; peut
  initialiser un état (connexion DB, log spécial, etc.).
* ``filter_file(path, metadata) -> bool`` — autorise ou refuse un
  fichier. Le faux exclut le fichier du batch.
* ``rename(path, metadata, proposed_name) -> str | None`` — peut
  proposer un autre nom (None = on garde ``proposed_name``).
* ``post_action(path, source, destination, action)`` — appelé après
  copy/move d'un fichier. Idéal pour logger, taguer, déclencher un
  upload cloud, etc.

Découverte des plugins
----------------------

1. **Entry points** : un paquet pip qui déclare un entry point dans le
   groupe ``photoorganizer_pro.plugins`` est chargé automatiquement.
   Exemple dans le ``pyproject.toml`` du plugin externe ::

       [project.entry-points."photoorganizer_pro.plugins"]
       myrenamer = "myrenamer.plugin:MyRenamerPlugin"

2. **Dossier local** : un fichier ``.py`` placé dans
   ``%LOCALAPPDATA%\\PhotoOrganizer\\plugins\\`` qui contient une
   sous-classe de :class:`BasePlugin` est chargé automatiquement.

Voir ``examples/plugin_geotag_renamer.py`` pour un exemple complet.
"""

from .base import BasePlugin, OrganizeContext, PluginAction
from .manager import PluginManager, get_plugin_manager

__all__ = [
    "BasePlugin",
    "OrganizeContext",
    "PluginAction",
    "PluginManager",
    "get_plugin_manager",
]
