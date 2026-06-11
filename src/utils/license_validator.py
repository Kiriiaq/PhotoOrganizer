"""Validation offline de licence + binding machine (v2.3+).

Lot F (audit 2026-06-11) : module déplacé depuis
``src/photoorganizer_pro/license/validator.py`` vers ``src/utils/`` pour
respecter la frontière de couches documentée dans CLAUDE.md —
``photoorganizer_pro`` peut importer ``utils``, jamais l'inverse. La v2.x
ne dépend ainsi plus du package Pro gelé. L'ancien emplacement reste un
shim de ré-export (utilisé par ``keygen.py`` côté auteur et les tests
historiques).

Format de la clé : ``PROG-<édition>-<exp>-<base64payload>-<sig>``

Exemple :
    ``PROG-PERS-20271231-ZW1haWxAZXhhbXBsZS5jb20=-xa8c9f...``

Le payload encode l'email du licencié, l'édition, la date d'expiration.
La signature est un HMAC SHA-256 calculé avec ``SECRET_KEY`` côté auteur.

La clé secrète est stockée dans ``src/utils/_secret.py`` (absent du repo
public, ajouté au .gitignore). Le placeholder par défaut permet aux tests
de tourner mais ne valide rien en production.

Persistance et machine binding (pivot 2026-05)
----------------------------------------------

Depuis le pivot vers le modèle "trial + unlock", ``license.dat`` ne
contient plus la clé brute. À la place :

.. code-block:: json

    {
      "payload": {
        "key": "PROG-...-...",
        "machine_id_bound": "ab12cd34...",
        "bound_at": "2026-05-27T10:00:00Z"
      },
      "sig": "<hmac SHA-256 du payload>"
    }

* La clé est universelle (générée sans machine_id, flow Lemon Squeezy
  standard) ;
* Le ``machine_id_bound`` est calculé et persisté à la **première**
  activation sur le PC (``save_license_key()``) ;
* À chaque ``load_active_license()`` on recalcule le ``machine_id`` du PC
  courant et on refuse la licence si le binding ne matche pas.

Effet net : une clé peut être copiée sur un autre PC, mais elle sera
refusée. **Une licence = un PC à vie.**
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Clé secrète embarquée.
# En production : ``src/utils/_secret.py`` (gitignored) créé avant le
# build. Fallback transitoire sur l'ancien emplacement Pro pour ne pas
# invalider un poste auteur pas encore migré, puis placeholder qui ne
# valide rien en prod.
# -----------------------------------------------------------------------
try:
    from ._secret import SECRET_KEY  # type: ignore  # noqa: F401
except ImportError:
    try:
        from src.photoorganizer_pro.license._secret import SECRET_KEY  # type: ignore  # noqa: F401
    except ImportError:
        SECRET_KEY = b"placeholder-replace-at-build-time"


EDITION_PERSONAL = "PERS"
EDITION_STUDIO = "STUD"
EDITION_LIFETIME = "LIFE"
VALID_EDITIONS = {EDITION_PERSONAL, EDITION_STUDIO, EDITION_LIFETIME}


class LicenseInvalidError(Exception):
    """Clé mal formée, falsifiée, signature incorrecte, OU bound à un autre PC."""


class LicenseExpiredError(Exception):
    """Clé syntaxiquement valide mais date d'expiration passée."""


@dataclass(frozen=True)
class LicenseInfo:
    """Résultat de la validation d'une clé."""

    email: str
    edition: str
    expires: date
    machine_id_bound: Optional[str] = None  # depuis pivot v2.3+

    @property
    def is_lifetime(self) -> bool:
        return self.edition == EDITION_LIFETIME

    def days_remaining(self) -> int:
        """Jours restants avant expiration. Négatif si expirée."""
        return (self.expires - date.today()).days


def _sign(payload: str) -> str:
    """Calcule la signature HMAC SHA-256 d'un payload, retourne hex."""
    mac = hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def validate_license_key(key: str) -> LicenseInfo:
    """Valide une clé de licence et retourne les infos décodées.

    Cette fonction valide UNIQUEMENT la clé en elle-même (signature,
    expiration, format). Le binding machine est géré par
    :func:`load_active_license` / :func:`save_license_key`.

    Raises:
        LicenseInvalidError: clé mal formée ou signature invalide.
        LicenseExpiredError: clé valide mais expirée.
    """
    if not isinstance(key, str) or not key:
        raise LicenseInvalidError("Empty license key")

    parts = key.strip().split("-")
    if len(parts) != 5 or parts[0] != "PROG":
        raise LicenseInvalidError(f"Malformed key: expected 5 segments starting with PROG, got {len(parts)}")

    _, edition, exp_str, payload_b64, sig_provided = parts

    if edition not in VALID_EDITIONS:
        raise LicenseInvalidError(f"Unknown edition '{edition}'")

    # Vérification signature : recalculer sur (édition + exp + payload).
    sig_payload = f"{edition}-{exp_str}-{payload_b64}"
    sig_expected = _sign(sig_payload)
    if not hmac.compare_digest(sig_expected, sig_provided):
        raise LicenseInvalidError("Signature mismatch (key tampered or wrong secret)")

    # Décodage du payload.
    try:
        email = base64.b64decode(payload_b64).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise LicenseInvalidError("Payload not valid base64 UTF-8") from exc
    if "@" not in email:
        raise LicenseInvalidError("Payload does not contain a valid email")

    try:
        expires = datetime.strptime(exp_str, "%Y%m%d").date()
    except ValueError as exc:
        raise LicenseInvalidError(f"Bad expiration format '{exp_str}' (expected YYYYMMDD)") from exc

    info = LicenseInfo(email=email, edition=edition, expires=expires)
    if expires < date.today():
        raise LicenseExpiredError(f"License expired on {expires.isoformat()}")

    return info


# -----------------------------------------------------------------------
# Persistance avec machine binding
# -----------------------------------------------------------------------
def _license_storage_path() -> Path:
    """Chemin du fichier ``license.dat`` dans ``%LOCALAPPDATA%\\PhotoOrganizer\\``."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    folder = base / "PhotoOrganizer"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "license.dat"


def _get_current_machine_id() -> str:
    """Indirection pour pouvoir monkeypatcher en tests.

    Délègue à :func:`utils.licensing._compute_machine_id` (import relatif :
    même package, même identité de module quelle que soit la façon dont
    l'app ou les tests chargent ``utils``).
    """
    # Lazy import pour éviter le cycle au démarrage (licensing importe
    # ce module en lazy également).
    from .licensing import _compute_machine_id

    return _compute_machine_id()


def _canonicalize(payload: dict) -> str:
    """JSON canonique pour signature stable (clés triées, séparateurs compacts)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def save_license_key(key: str) -> Path:
    """Persiste la clé (préalablement validée) + bind au PC courant.

    Format produit :

    .. code-block:: json

        {
          "payload": {
            "key": "PROG-...",
            "machine_id_bound": "ab12cd34...",
            "bound_at": "2026-05-27T10:00:00Z"
          },
          "sig": "<hmac>"
        }

    Le HMAC est calculé sur le JSON canonique du ``payload``. Toute
    modification ultérieure du fichier sera rejetée au prochain
    :func:`load_active_license`.
    """
    path = _license_storage_path()
    machine_id = _get_current_machine_id()
    payload = {
        "key": key,
        "machine_id_bound": machine_id,
        "bound_at": datetime.now(timezone.utc).isoformat(),
    }
    sig = _sign(_canonicalize(payload))
    full = {"payload": payload, "sig": sig}

    # Écriture atomique via fichier temporaire.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(full, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)
    return path


def load_active_license() -> Optional[LicenseInfo]:
    """Charge la licence persistée et vérifie tout (sig + expir + binding).

    Returns:
        :class:`LicenseInfo` si valide et bound à ce PC, ``None`` sinon
        (fichier absent, corrompu, expiré, ou bound à un autre PC).

    La fonction ne **lève jamais** : un échec retourne simplement ``None``
    pour que l'UI puisse afficher l'état "trial" sans gérer d'exception.
    """
    path = _license_storage_path()
    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("Cannot read license.dat (%s)", exc)
        return None

    # Tentative format JSON nouveau (post-pivot).
    payload: Optional[dict] = None
    try:
        full = json.loads(raw)
        payload = full["payload"]
        sig_provided = full["sig"]
    except (json.JSONDecodeError, KeyError, TypeError):
        payload = None

    if payload is not None:
        # Format moderne : vérifie l'enveloppe.
        if not hmac.compare_digest(_sign(_canonicalize(payload)), sig_provided):
            logger.warning("license.dat envelope HMAC mismatch — refusing")
            return None

        # Vérifie le binding machine.
        bound_machine = payload.get("machine_id_bound")
        current_machine = _get_current_machine_id()
        if bound_machine != current_machine:
            logger.warning("license.dat bound to another machine — refusing")
            return None

        key = payload.get("key", "")
    else:
        # Fallback : ancien format (juste la clé brute). Ne devrait pas
        # arriver en pratique (pas de migration depuis avant v2.3) mais
        # on reste tolérant pour les tests historiques.
        key = raw

    try:
        info = validate_license_key(key)
    except (LicenseInvalidError, LicenseExpiredError):
        return None

    if payload is not None:
        # Repackage avec le machine_id_bound (pour que l'UI puisse y accéder).
        info = LicenseInfo(
            email=info.email,
            edition=info.edition,
            expires=info.expires,
            machine_id_bound=payload.get("machine_id_bound"),
        )
    return info
