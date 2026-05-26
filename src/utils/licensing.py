"""Trial counter + machine binding — modèle économique v2.3+.

Implémente le modèle "trial + unlock" décrit dans
``docs/MONETIZATION.md`` §3 :

* Compteur d'usages signé HMAC dans
  ``%LOCALAPPDATA%\\PhotoOrganizer\\usage.dat``.
* Machine binding (``MachineGuid + VolumeSerial`` → SHA-256) au premier
  ``save_license_key()``.
* États possibles : *trial-N/10*, *limite-atteinte*, *activée*.

Frontière de couche
-------------------

Ce module est utilitaire (``src/utils/``) :

* il **ne dépend ni de** ``src/core/`` **ni de** ``src/ui/`` ;
* il peut être importé par n'importe quelle couche supérieure ;
* il **réutilise le même secret HMAC** que
  ``src/photoorganizer_pro/license/`` pour rester aligné sur la signature
  des clés (un seul secret = une seule source de confiance crypto).

Caveat sécurité
---------------

Aucun DRM offline n'est incassable :

* L'utilisateur peut supprimer ``usage.dat`` → compteur reset à 0
  (faille assumée). Pour rendre le contournement plus pénible en v2.3.1,
  on duplicera dans le registre Windows.
* L'utilisateur peut patcher le binaire PyInstaller → on accepte. À 10 €
  l'effort de crack > prix d'achat.
* L'utilisateur peut copier ``license.dat`` sur un autre PC → bloqué par
  le machine binding (le fichier est signé HMAC incluant le
  ``machine_id``, et la signature est revérifiée au load).

L'objectif n'est pas l'incassabilité mais "contournement plus chiant que
payer 10 €".
"""

from __future__ import annotations

import ctypes
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Secret HMAC : partagé avec ``photoorganizer_pro.license``.
# En prod, le ``_secret.py`` est gitignored et embarqué au build.
# En dev/contributeur sans ``_secret.py``, on utilise un placeholder qui
# permet aux tests de tourner mais ne valide rien en production.
# -----------------------------------------------------------------------
try:
    from src.photoorganizer_pro.license._secret import SECRET_KEY  # type: ignore  # noqa: F401
except ImportError:
    SECRET_KEY = b"placeholder-replace-at-build-time"

# -----------------------------------------------------------------------
# Constantes du modèle
# -----------------------------------------------------------------------
TRIAL_LIMIT = 10  # nombre de tris gratuits avant blocage
WARNING_THRESHOLDS = (8, 9)  # bandeau d'avertissement à ces compteurs

USAGE_FILE_NAME = "usage.dat"


# -----------------------------------------------------------------------
# Dataclass d'état
# -----------------------------------------------------------------------
@dataclass(frozen=True)
class LicenseState:
    """Snapshot complet de l'état licence/trial d'une session.

    Attributes
    ----------
    has_valid_license:
        True si une licence est activée et valide sur ce PC.
    trial_count:
        Nombre de tris déjà consommés (0..N).
    trial_remaining:
        ``max(0, TRIAL_LIMIT - trial_count)``.
    machine_id:
        Empreinte hex SHA-256 complète (64 chars).
    machine_id_short:
        Forme courte ``"MAC-7A3F-9C2E"`` pour affichage UI/support.
    license_email:
        Email du licencié si activé, None sinon.
    is_blocked:
        True si compteur >= TRIAL_LIMIT **et** pas de licence valide.
    should_warn:
        True si on doit afficher un bandeau "avant-dernier / dernier
        tri gratuit" (compteur dans :data:`WARNING_THRESHOLDS`).
    """

    has_valid_license: bool
    trial_count: int
    trial_remaining: int
    machine_id: str
    machine_id_short: str
    license_email: Optional[str]
    is_blocked: bool
    should_warn: bool

    @property
    def status_badge_text(self) -> str:
        """Texte court pour le badge global de la barre titre.

        * ``"Activée · MAC-XXXX"`` si licence OK
        * ``"Essai N/10"`` sinon (avec N = trial_count)
        * ``"Limite atteinte"`` si bloqué
        """
        if self.has_valid_license:
            return f"Activée · {self.machine_id_short}"
        if self.is_blocked:
            return "Limite atteinte · Activer"
        return f"Essai {min(self.trial_count, TRIAL_LIMIT)}/{TRIAL_LIMIT}"


# -----------------------------------------------------------------------
# Chemins disque
# -----------------------------------------------------------------------
def _localappdata_root() -> Path:
    """Racine ``%LOCALAPPDATA%\\PhotoOrganizer\\``."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        # Linux/macOS : on calque le layout (utile pour les tests CI).
        base = Path.home() / ".local" / "share"
    folder = base / "PhotoOrganizer"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _usage_path() -> Path:
    """Chemin du fichier compteur ``usage.dat``."""
    return _localappdata_root() / USAGE_FILE_NAME


# -----------------------------------------------------------------------
# Machine ID
# -----------------------------------------------------------------------
def _read_machine_guid() -> str:
    """Lit le ``MachineGuid`` Windows (clé registre).

    Sur OS non Windows ou en cas d'erreur d'accès, renvoie un placeholder
    stable qui permet aux tests de tourner sans privilèges spéciaux.
    """
    if os.name != "nt":
        return "non-windows-machine-guid"
    try:
        import winreg  # stdlib Windows uniquement

        key = winreg.OpenKey(  # type: ignore[attr-defined]
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        )
        try:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")  # type: ignore[attr-defined]
            return str(value)
        finally:
            winreg.CloseKey(key)  # type: ignore[attr-defined]
    except OSError as exc:
        logger.warning("Cannot read MachineGuid (%s) — using fallback", exc)
        return "machine-guid-unavailable"


def _read_volume_serial_c() -> str:
    """Lit le numéro de série du volume ``C:\\`` (Windows).

    Renvoie un placeholder stable sur autres OS / en cas d'erreur.
    """
    if os.name != "nt":
        return "non-windows-volume-serial"
    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        serial = ctypes.c_ulong(0)
        ok = kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p("C:\\"),
            None, 0,
            ctypes.byref(serial),
            None, None,
            None, 0,
        )
        if ok:
            return f"{serial.value:08X}"
    except (OSError, AttributeError) as exc:
        logger.warning("Cannot read volume serial (%s) — using fallback", exc)
    return "volume-serial-unavailable"


def _compute_machine_id() -> str:
    """``SHA-256(MachineGuid || '|' || VolumeSerial)``."""
    guid = _read_machine_guid()
    serial = _read_volume_serial_c()
    combo = f"{guid}|{serial}".encode("utf-8")
    return hashlib.sha256(combo).hexdigest()


def get_machine_id() -> str:
    """Hex complet de l'empreinte machine (64 chars)."""
    return _compute_machine_id()


def get_machine_id_short(machine_id: Optional[str] = None) -> str:
    """Forme courte affichable, ex. ``"MAC-7A3F-9C2E"``.

    Composée des caractères 0-3 et 4-7 du hex (séparés par un tiret) —
    8 chars hex visibles, suffisants pour le support et discrets dans
    la barre titre.
    """
    if machine_id is None:
        machine_id = _compute_machine_id()
    h = machine_id.upper()
    return f"MAC-{h[0:4]}-{h[4:8]}"


# -----------------------------------------------------------------------
# Signature HMAC du compteur
# -----------------------------------------------------------------------
def _sign(payload: str) -> str:
    """HMAC SHA-256 hex d'un payload texte."""
    return hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _canonicalize(payload: dict) -> str:
    """JSON canonique (clés triées, séparateurs compacts) pour la signature."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


# -----------------------------------------------------------------------
# Lecture/écriture du compteur
# -----------------------------------------------------------------------
def _empty_usage(machine_id: str) -> dict:
    return {
        "count": 0,
        "machine_id": machine_id,
        "first_run": datetime.now(timezone.utc).isoformat(),
    }


def _read_usage() -> dict:
    """Charge le compteur. Reset à 0 si fichier absent, corrompu ou tampered.

    Le reset à 0 est volontairement *silencieux* (juste un log warning)
    pour ne pas révéler à un utilisateur curieux la nature de l'anti-tampering.
    """
    path = _usage_path()
    machine_id = _compute_machine_id()

    if not path.exists():
        return _empty_usage(machine_id)

    try:
        raw = path.read_text(encoding="utf-8")
        full = json.loads(raw)
        payload = full["payload"]
        sig_provided = full["sig"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Usage file corrupt (%s) — resetting counter", exc)
        return _empty_usage(machine_id)

    if not hmac.compare_digest(_sign(_canonicalize(payload)), sig_provided):
        logger.warning("Usage file tampered (HMAC mismatch) — resetting counter")
        return _empty_usage(machine_id)

    # Anti-copie : si le machine_id stocké ne matche pas le PC courant,
    # on considère que c'est un usage.dat copié → reset.
    if payload.get("machine_id") != machine_id:
        logger.warning("Usage file from another machine — resetting counter")
        return _empty_usage(machine_id)

    # Sanity-check minimal (count int >= 0)
    count = payload.get("count")
    if not isinstance(count, int) or count < 0:
        logger.warning("Usage file count invalid (%r) — resetting", count)
        return _empty_usage(machine_id)

    return payload


def _write_usage(payload: dict) -> None:
    """Écrit le compteur signé HMAC. Atomique via fichier temporaire."""
    path = _usage_path()
    sig = _sign(_canonicalize(payload))
    full = {"payload": payload, "sig": sig}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(full, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


# -----------------------------------------------------------------------
# API publique
# -----------------------------------------------------------------------
def get_state() -> LicenseState:
    """Snapshot complet de l'état trial + licence à un instant T.

    N'effectue **aucune** mutation (pas d'incrément, pas de save).
    """
    # Import paresseux : évite un cycle si le validator importe utils plus tard.
    from src.photoorganizer_pro.license.validator import load_active_license

    machine_id = _compute_machine_id()
    short = get_machine_id_short(machine_id)
    usage = _read_usage()
    count = int(usage["count"])

    info = load_active_license()  # peut être None
    has_license = info is not None
    license_email = info.email if info else None

    is_blocked = (not has_license) and count >= TRIAL_LIMIT
    should_warn = (not has_license) and (count in WARNING_THRESHOLDS)
    trial_remaining = max(0, TRIAL_LIMIT - count)

    return LicenseState(
        has_valid_license=has_license,
        trial_count=count,
        trial_remaining=trial_remaining,
        machine_id=machine_id,
        machine_id_short=short,
        license_email=license_email,
        is_blocked=is_blocked,
        should_warn=should_warn,
    )


def can_organize_now() -> Tuple[bool, LicenseState]:
    """Renvoie ``(allowed, state)``.

    ``allowed`` est False si l'utilisateur est en mode essai et a déjà
    consommé ses 10 tris.
    """
    state = get_state()
    return (not state.is_blocked, state)


def record_successful_organize() -> LicenseState:
    """À appeler **uniquement après un tri réussi** (pas au clic).

    Si une licence est active, ne touche pas au compteur (illimité).
    Sinon, incrémente de 1 et persiste.
    """
    state = get_state()
    if state.has_valid_license:
        return state  # illimité, on n'incrémente pas

    usage = _read_usage()
    usage["count"] = int(usage["count"]) + 1
    usage["last_run"] = datetime.now(timezone.utc).isoformat()
    _write_usage(usage)

    return get_state()


def activate_key(key: str) -> LicenseState:
    """Valide une clé et la persiste (avec binding machine).

    Délègue à ``photoorganizer_pro.license.validator`` :

    * ``validate_license_key()`` vérifie la signature + l'expiration ;
    * ``save_license_key()`` écrit ``license.dat`` avec le ``machine_id``
      courant comme binding.

    Raises:
        Les exceptions de ``validator`` :
        :class:`LicenseInvalidError`, :class:`LicenseExpiredError`.
    """
    # Lazy import (cf. get_state).
    from src.photoorganizer_pro.license.validator import (
        save_license_key,
        validate_license_key,
    )

    # Lève si invalide / expirée — laisse remonter à l'appelant pour
    # affichage du bon message d'erreur.
    validate_license_key(key.strip())
    save_license_key(key.strip())
    return get_state()


def reset_for_tests() -> None:
    """Détruit ``usage.dat`` et ``license.dat`` — *réservé aux tests*.

    Ne JAMAIS appeler en prod.
    """
    from src.photoorganizer_pro.license.validator import _license_storage_path

    for path in (_usage_path(), _license_storage_path()):
        if path.exists():
            path.unlink()
