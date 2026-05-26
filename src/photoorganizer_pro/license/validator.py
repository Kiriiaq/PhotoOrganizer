"""Validation offline de licence Pro.

Format de la clé : ``PROG-<édition>-<exp>-<base64payload>-<sig>``

Exemple :
    ``PROG-PERS-20271231-ZW1haWxAZXhhbXBsZS5jb20=-xa8c9f...``

Le payload encode l'email du licencié, l'édition, la date d'expiration.
La signature est un HMAC SHA-256 calculé avec ``SECRET_KEY`` côté auteur.

La clé secrète est stockée dans ``photoorganizer_pro/license/_secret.py``
(absent du repo public, ajoutée au .gitignore). En attendant cette
release, ce module utilise une clé placeholder pour permettre les tests.

Activation utilisateur : la clé est écrite dans
``%LOCALAPPDATA%\\PhotoOrganizer\\license.dat`` après validation. Au
lancement, l'app cherche ce fichier et déverrouille les modules Pro si
la signature et la date sont valides.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# -----------------------------------------------------------------------
# Clé secrète embarquée.
# En production : remplacée par PyInstaller au moment du build Pro via
# une injection de string. Pour ce squelette open-source, on garde un
# placeholder qui ne valide rien en prod (sécurité par obscurité = nulle
# si la clé reste celle-ci, donc le build Pro DOIT la changer).
# -----------------------------------------------------------------------
try:
    from ._secret import SECRET_KEY  # type: ignore  # noqa: F401
except ImportError:
    SECRET_KEY = b"placeholder-replace-at-build-time"


EDITION_PERSONAL = "PERS"
EDITION_STUDIO = "STUD"
EDITION_LIFETIME = "LIFE"
VALID_EDITIONS = {EDITION_PERSONAL, EDITION_STUDIO, EDITION_LIFETIME}


class LicenseInvalidError(Exception):
    """La clé est mal formée, falsifiée, ou la signature est incorrecte."""


class LicenseExpiredError(Exception):
    """La clé est syntaxiquement valide mais sa date d'expiration est passée."""


@dataclass(frozen=True)
class LicenseInfo:
    """Résultat de la validation d'une clé."""

    email: str
    edition: str
    expires: date

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


def _license_storage_path() -> Path:
    """Chemin du fichier license.dat dans %LOCALAPPDATA%\\PhotoOrganizer\\."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    folder = base / "PhotoOrganizer"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "license.dat"


def save_license_key(key: str) -> Path:
    """Persiste la clé (préalablement validée) sur disque.

    Le fichier ne contient PAS de secret : juste la clé brute. Sa
    confidentialité n'est pas critique (la sécurité repose sur la
    signature HMAC, pas sur l'opacité du fichier).
    """
    path = _license_storage_path()
    path.write_text(key, encoding="ascii")
    return path


def load_active_license() -> Optional[LicenseInfo]:
    """Charge et valide la licence persistée, si présente.

    Returns:
        LicenseInfo si valide, None si aucune licence n'est trouvée ou si
        elle est invalide/expirée (le caller décidera quoi afficher).
    """
    path = _license_storage_path()
    if not path.exists():
        return None
    try:
        key = path.read_text(encoding="ascii").strip()
        return validate_license_key(key)
    except (LicenseInvalidError, LicenseExpiredError):
        return None
