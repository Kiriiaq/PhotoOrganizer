# -*- coding: utf-8 -*-
"""
Quarantaine interne pour les suppressions réversibles.

Problème résolu (refonte 2026-05-19) :
    ``send2trash`` envoie un fichier dans la corbeille système (Windows
    Recycle Bin, macOS Trash, Linux XDG Trash) — mais cette opération est
    **un aller simple** côté Python : la lib ne fournit aucune API
    de restauration. Conséquence : le bouton « ↩️ Annuler dernière » du
    panneau Historique ne pouvait pas défaire un envoi en corbeille.

Solution :
    Au lieu d'envoyer directement à la corbeille système, on déplace
    le fichier dans un **dossier de quarantaine interne** géré par l'app :

        <quarantine_root>/<session_id>/<hash>_<basename>

    où ``hash`` est un préfixe unique pour éviter les collisions de noms.
    Un manifest JSON conserve le mapping ``destination → source`` pour
    chaque session, ce qui rend la restauration triviale (``shutil.move``).

    Quand l'utilisateur est sûr qu'il n'a plus besoin des fichiers, il
    appuie sur **« 🗑 Vider quarantaine »** qui envoie alors le tampon
    à la vraie corbeille système (``send2trash``).

Sécurité :
    - Le dossier de quarantaine est créé hors des sources/destinations
      organisées pour éviter les boucles infinies de détection de
      doublons.
    - Chaque session a son propre sous-dossier horodaté → on peut purger
      sélectivement par âge.
    - Le manifest est écrit à chaque opération (pas seulement à la fin)
      pour survivre à un crash de l'app.
"""

import hashlib
import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import optionnel : si send2trash est absent on garde une quarantaine
# permanente que l'utilisateur peut effacer à la main.
try:
    from send2trash import send2trash
    _TRASH_AVAILABLE = True
except ImportError:
    _TRASH_AVAILABLE = False

logger = logging.getLogger(__name__)

# Nom du sous-dossier de quarantaine, créé sous le répertoire utilisateur
# configurable (par défaut : ``%LOCALAPPDATA%/PhotoOrganizer/quarantine``
# sous Windows). Le préfixe ``.`` masque le dossier sur macOS/Linux.
DEFAULT_QUARANTINE_DIRNAME = ".photoorganizer_trash"
MANIFEST_FILENAME = "manifest.json"


@dataclass
class QuarantineEntry:
    """Une entrée du manifest = un fichier déplacé en quarantaine."""
    source: str            # chemin d'origine (où le fichier était avant)
    destination: str       # chemin actuel dans la quarantaine
    timestamp: str         # ISO 8601, pour purge par âge
    size_bytes: int = 0    # pour stats / décisions de purge
    reason: str = ""       # libellé court : "duplicate", "test", ...

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "destination": self.destination,
            "timestamp": self.timestamp,
            "size_bytes": self.size_bytes,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "QuarantineEntry":
        return cls(
            source=d["source"],
            destination=d["destination"],
            timestamp=d.get("timestamp", ""),
            size_bytes=int(d.get("size_bytes", 0)),
            reason=d.get("reason", ""),
        )


def _default_quarantine_root() -> Path:
    """Détermine un dossier racine sûr pour la quarantaine.

    Windows : ``%LOCALAPPDATA%/PhotoOrganizer/quarantine``
    Autres  : ``~/.photoorganizer/quarantine``
    """
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        return Path(localappdata) / "PhotoOrganizer" / "quarantine"
    return Path.home() / DEFAULT_QUARANTINE_DIRNAME / "quarantine"


class QuarantineManager:
    """Gère le déplacement vers une quarantaine interne réversible.

    Une instance = une « session » de quarantaine. Plusieurs sessions
    peuvent coexister dans le même ``root``, identifiées par leur
    sous-dossier horodaté.
    """

    def __init__(
        self,
        root: Optional[Path] = None,
        session_id: Optional[str] = None,
    ):
        """
        Args:
            root: dossier racine où créer la quarantaine. Si None, utilise
                  un emplacement sûr et persistent (%LOCALAPPDATA% sur
                  Windows, ~/.photoorganizer/quarantine ailleurs).
            session_id: identifiant unique de cette session (par défaut :
                        horodatage YYYYMMDD_HHMMSS). Si None, généré.
        """
        self.root: Path = Path(root) if root else _default_quarantine_root()
        self.session_id: str = (
            session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        self.session_dir: Path = self.root / self.session_id
        self._entries: List[QuarantineEntry] = []
        # Création paresseuse : on n'instancie le dossier qu'à la première
        # opération réelle pour éviter de polluer le filesystem si
        # l'utilisateur n'utilise jamais la quarantaine.
        self._initialized = False

    # ------------------------------------------------------------------
    # API principale
    # ------------------------------------------------------------------
    def quarantine_file(
        self, file_path: str, reason: str = "duplicate"
    ) -> QuarantineEntry:
        """Déplace un fichier en quarantaine et retourne son entrée.

        Args:
            file_path: chemin absolu du fichier à mettre en quarantaine.
            reason: libellé court qui sera stocké dans le manifest
                    (pratique pour filtrer par usage : doublon, etc.).

        Returns:
            ``QuarantineEntry`` du fichier déplacé.

        Raises:
            FileNotFoundError: si le fichier source n'existe pas.
            OSError: si le déplacement échoue (permissions, disque plein).
        """
        src = Path(file_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Fichier introuvable : {src}")

        self._ensure_session_dir()

        # Calcule un préfixe unique pour éviter les collisions de noms
        # entre des fichiers identiques placés dans des dossiers différents.
        # On hashe le chemin source absolu, pas le contenu (trop coûteux).
        # usedforsecurity=False : ce hash sert d'identifiant court, pas de
        # vérification d'intégrité. Bandit B324 ne s'applique pas ici.
        prefix = hashlib.sha1(str(src).encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
        dest = self.session_dir / f"{prefix}_{src.name}"

        # En cas de collision improbable (même hash + même nom = même fichier
        # placé deux fois), on suffixe avec un compteur.
        counter = 1
        while dest.exists():
            dest = self.session_dir / f"{prefix}_{counter}_{src.name}"
            counter += 1

        size = src.stat().st_size
        shutil.move(str(src), str(dest))
        entry = QuarantineEntry(
            source=str(src),
            destination=str(dest),
            timestamp=datetime.now().isoformat(timespec="seconds"),
            size_bytes=size,
            reason=reason,
        )
        self._entries.append(entry)
        self._write_manifest()
        logger.info(
            "Quarantine: %s -> %s (%.1f Ko)",
            src.name, dest.name, size / 1024
        )
        return entry

    def restore_entry(self, entry: QuarantineEntry) -> bool:
        """Restaure un fichier depuis la quarantaine vers son chemin d'origine.

        Returns:
            True si le fichier a été restauré, False sinon (fichier déjà
            disparu de la quarantaine, ou chemin source occupé).
        """
        dest_path = Path(entry.destination)
        src_path = Path(entry.source)

        if not dest_path.exists():
            logger.warning("Fichier introuvable en quarantaine: %s", dest_path)
            return False

        # On reconstruit le dossier d'origine si besoin (l'utilisateur a pu
        # vider sa source entre temps).
        src_path.parent.mkdir(parents=True, exist_ok=True)

        # Si un fichier portant le même nom existe déjà à la source, on
        # suffixe pour ne pas écraser silencieusement.
        target = src_path
        if target.exists():
            counter = 1
            while True:
                target = src_path.with_name(
                    f"{src_path.stem}_restored{counter}{src_path.suffix}"
                )
                if not target.exists():
                    break
                counter += 1

        shutil.move(str(dest_path), str(target))
        # Retire l'entrée du manifest
        self._entries = [e for e in self._entries if e.destination != entry.destination]
        self._write_manifest()
        logger.info("Restored: %s -> %s", dest_path.name, target)
        return True

    def list_entries(self) -> List[QuarantineEntry]:
        """Retourne la liste des entrées en quarantaine de cette session."""
        return list(self._entries)

    def total_size_bytes(self) -> int:
        """Taille totale occupée par la quarantaine de cette session."""
        return sum(e.size_bytes for e in self._entries)

    def empty_to_system_trash(self) -> Dict[str, int]:
        """Vide la quarantaine en envoyant tout à la corbeille système.

        C'est l'action « 🗑 Vider définitivement » de l'IHM. Si
        ``send2trash`` est indisponible (env sans la lib), on supprime
        définitivement les fichiers (avec avertissement dans les logs).

        Returns:
            dict avec ``trashed``, ``deleted``, ``failed``, ``total``.
            - ``trashed`` : envoyés en corbeille système (réversible via
                            l'Explorateur Windows / Finder / `gio trash`).
            - ``deleted`` : supprimés définitivement (fallback si pas de
                            send2trash).
            - ``failed``  : échecs (permission, fichier disparu, etc.).
        """
        trashed = 0
        deleted = 0
        failed = 0
        total = len(self._entries)

        for entry in list(self._entries):
            dest = Path(entry.destination)
            if not dest.exists():
                failed += 1
                continue
            try:
                if _TRASH_AVAILABLE:
                    send2trash(str(dest))
                    trashed += 1
                else:
                    # Fallback : suppression dure si send2trash absent.
                    # On loggue à WARNING car c'est une perte définitive.
                    dest.unlink()
                    deleted += 1
                    logger.warning(
                        "send2trash indisponible, suppression definitive: %s",
                        dest,
                    )
            except Exception as e:
                logger.error("Echec vidage quarantaine %s: %s", dest, e)
                failed += 1
                continue
            self._entries = [e for e in self._entries if e.destination != entry.destination]

        # Nettoyage du dossier de session s'il est vide
        if self.session_dir.exists():
            try:
                # Réécriture manifest avant suppression éventuelle
                self._write_manifest()
                if not any(
                    p for p in self.session_dir.iterdir()
                    if p.name != MANIFEST_FILENAME
                ):
                    # Plus aucun fichier en quarantaine → on peut purger
                    manifest = self.session_dir / MANIFEST_FILENAME
                    if manifest.exists():
                        manifest.unlink()
                    self.session_dir.rmdir()
            except OSError as e:
                logger.debug("Nettoyage session_dir ignore: %s", e)

        return {
            "trashed": trashed,
            "deleted": deleted,
            "failed": failed,
            "total": total,
        }

    # ------------------------------------------------------------------
    # Persistance manifest
    # ------------------------------------------------------------------
    def _ensure_session_dir(self):
        if self._initialized:
            return
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def _write_manifest(self):
        if not self.session_dir.exists():
            return
        payload = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "entries": [e.to_dict() for e in self._entries],
        }
        manifest_path = self.session_dir / MANIFEST_FILENAME
        try:
            manifest_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("Echec ecriture manifest %s: %s", manifest_path, e)

    @classmethod
    def load_session(cls, session_dir: Path) -> "QuarantineManager":
        """Recharge un ``QuarantineManager`` depuis un dossier de session.

        Utile pour permettre à l'utilisateur de restaurer des fichiers
        d'une session précédente (ex. crash de l'app).
        """
        session_dir = Path(session_dir)
        manifest_path = session_dir / MANIFEST_FILENAME
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest absent : {manifest_path}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        inst = cls(root=session_dir.parent, session_id=session_dir.name)
        inst._entries = [QuarantineEntry.from_dict(e) for e in data.get("entries", [])]
        inst._initialized = True
        return inst
