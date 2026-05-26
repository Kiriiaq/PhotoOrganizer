"""Classes de base de l'API plugin.

Conception
----------

* Chaque plugin hérite de :class:`BasePlugin`. Toutes les méthodes ont
  une implémentation **no-op** par défaut → un plugin ne surcharge que
  les hooks qui l'intéressent.
* Le ``PluginManager`` invoque chaque hook sur tous les plugins
  enregistrés, dans l'ordre des plugins. Les exceptions levées par un
  plugin sont attrapées et loguées sans arrêter le batch.
* Les hooks reçoivent un :class:`OrganizeContext` contenant les options,
  source, destination, et un dict utilisateur libre ``state`` partagé
  entre les invocations du même batch.

Contrat de stabilité
--------------------

Cette API est **publique** à partir de la version 2.2.0. Toute
modification cassante sera signalée par un bump majeur de
PhotoOrganizer Pro et accompagnée d'une période de compatibilité de 6
mois minimum (via décorateur ``@deprecated``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class PluginAction(str, Enum):
    """Action appliquée à un fichier lors de l'organisation."""

    COPY = "copy"
    MOVE = "move"
    SKIP = "skip"


@dataclass
class OrganizeContext:
    """État partagé entre les hooks d'un même batch d'organisation."""

    source_dir: Path
    target_dir: Path
    #: Options brutes du batch. Type ``Any`` pour éviter de coupler le
    #: package plugins à ``core.operations.OrganizationOptions``.
    options: Any = None
    #: Dictionnaire libre. Les plugins peuvent y stocker un état entre
    #: ``pre_organize`` et ``post_action`` (ex : connexion DB, compteur,
    #: dossier de log temporaire).
    state: Dict[str, Any] = field(default_factory=dict)


class BasePlugin:
    """Classe de base à étendre par tout plugin PhotoOrganizer Pro.

    Toutes les méthodes ont une implémentation par défaut qui ne fait
    rien. Surcharger uniquement les hooks pertinents.

    Attributes:
        name: Nom unique du plugin (utilisé en log et dans la GUI).
        version: Version sémantique du plugin.
    """

    #: Identifiant unique du plugin. À surcharger dans la sous-classe.
    name: str = "unnamed"
    #: Version sémantique du plugin.
    version: str = "0.0.0"

    # -----------------------------------------------------------------
    # Hooks
    # -----------------------------------------------------------------
    def pre_organize(self, context: OrganizeContext) -> None:
        """Appelé une fois avant le batch. Peut initialiser ``context.state``."""

    def filter_file(self, path: Path, metadata: Dict[str, Any], context: OrganizeContext) -> bool:
        """Décide si un fichier doit être inclus dans le batch.

        Returns:
            True (défaut) pour inclure, False pour exclure.
        """
        return True

    def rename(
        self,
        path: Path,
        metadata: Dict[str, Any],
        proposed_name: str,
        context: OrganizeContext,
    ) -> Optional[str]:
        """Peut proposer un nouveau nom pour le fichier.

        Args:
            path: Chemin source du fichier.
            metadata: Métadonnées EXIF extraites.
            proposed_name: Nom proposé par le core (sans dossier).
            context: État partagé du batch.

        Returns:
            Le nouveau nom souhaité (avec extension), ou ``None`` pour
            conserver ``proposed_name``.
        """
        return None

    def post_action(
        self,
        source: Path,
        destination: Path,
        action: PluginAction,
        context: OrganizeContext,
    ) -> None:
        """Appelé après copy/move/skip d'un fichier.

        Idéal pour : logger, taguer, déclencher un upload cloud,
        envoyer une notification.
        """

    def post_organize(self, context: OrganizeContext) -> None:
        """Appelé une fois après la fin du batch (succès ou erreur)."""

    # -----------------------------------------------------------------
    # Utilitaires pour les tests / introspection
    # -----------------------------------------------------------------
    def describe(self) -> str:
        """Retourne une description lisible. Surchargeable."""
        return f"{self.name} v{self.version}"

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r} version={self.version!r}>"
