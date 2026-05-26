"""Plugin exemple : ``geotag_renamer``.

Préfixe les noms de fichiers par un slug géographique court basé sur
les coordonnées EXIF GPS. Démonstration des hooks :class:`BasePlugin`.

Comportement
------------

Pour ``IMG_4567.jpg`` avec GPS ``(48.85, 2.35)`` (Paris) :
    → ``48N002E_IMG_4567.jpg``

Pour ``IMG_4568.jpg`` sans GPS :
    → ``IMG_4568.jpg`` (inchangé)

Hooks utilisés : ``pre_organize`` (compteur), ``rename`` (préfixe),
``post_organize`` (résumé), ``post_action`` (log).

Utilisation
-----------

Pour activer ce plugin localement, copier ce fichier dans
``%LOCALAPPDATA%\\PhotoOrganizer\\plugins\\geotag_renamer.py`` puis
relancer PhotoOrganizer Pro.

Pour le distribuer via pip, créer un paquet qui déclare ::

    [project.entry-points."photoorganizer_pro.plugins"]
    geotag = "geotag_renamer:GeotagRenamerPlugin"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.photoorganizer_pro.plugins import BasePlugin, OrganizeContext, PluginAction

logger = logging.getLogger(__name__)


def _slug_from_coords(lat: float, lon: float) -> str:
    """Retourne ex ``48N002E`` à partir de ``(48.85, 2.35)``.

    2 chiffres pour la latitude (degrés entiers), 3 pour la longitude.
    Les hémisphères Nord/Sud / Est/Ouest sont encodés en lettre.
    """
    lat_letter = "N" if lat >= 0 else "S"
    lon_letter = "E" if lon >= 0 else "W"
    return f"{abs(int(lat)):02d}{lat_letter}{abs(int(lon)):03d}{lon_letter}"


def _extract_coords(metadata: Dict[str, Any]) -> Optional[tuple]:
    """Cherche ``(lat, lon)`` dans les métadonnées. Retourne None sinon."""
    lat = metadata.get("GPSLatitude") or metadata.get("latitude")
    lon = metadata.get("GPSLongitude") or metadata.get("longitude")
    if lat is None or lon is None:
        return None
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


class GeotagRenamerPlugin(BasePlugin):
    """Préfixe les noms de fichiers avec un slug GPS court."""

    name = "geotag_renamer"
    version = "1.0.0"

    def pre_organize(self, context: OrganizeContext) -> None:
        # Initialise un compteur dans le state partagé.
        context.state.setdefault("geotag_renamer", {"renamed": 0, "skipped": 0})
        logger.info("geotag_renamer : démarrage batch (source=%s)", context.source_dir)

    def rename(
        self,
        path: Path,
        metadata: Dict[str, Any],
        proposed_name: str,
        context: OrganizeContext,
    ) -> Optional[str]:
        coords = _extract_coords(metadata)
        if coords is None:
            context.state["geotag_renamer"]["skipped"] += 1
            return None  # garde le nom proposé par le core

        slug = _slug_from_coords(*coords)
        # Évite la double-préfixation si déjà présent
        if proposed_name.startswith(slug):
            return None
        new_name = f"{slug}_{proposed_name}"
        context.state["geotag_renamer"]["renamed"] += 1
        return new_name

    def post_action(
        self,
        source: Path,
        destination: Path,
        action: PluginAction,
        context: OrganizeContext,
    ) -> None:
        if action != PluginAction.SKIP:
            logger.debug("geotag_renamer : %s → %s (%s)", source.name, destination.name, action.value)

    def post_organize(self, context: OrganizeContext) -> None:
        stats = context.state.get("geotag_renamer", {})
        logger.info(
            "geotag_renamer : terminé — %d renommés, %d sans GPS (gardé tel quel)",
            stats.get("renamed", 0),
            stats.get("skipped", 0),
        )
