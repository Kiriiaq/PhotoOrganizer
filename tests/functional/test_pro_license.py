"""Tests fonctionnels du module licence Pro.

Vérifie :
  - génération + validation d'une clé valide ;
  - rejet des clés malformées, falsifiées, ou expirées ;
  - aller-retour persistance disque (save / load).

Le secret est le placeholder par défaut (cf.
``photoorganizer_pro/license/validator.py``). En prod, le secret est
remplacé au build Pro.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

# Le src layout impose ce hack en tests : les tests sont à la racine,
# le code à src/. Voir conftest.py.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.photoorganizer_pro.license import (  # noqa: E402
    EDITION_LIFETIME,
    EDITION_PERSONAL,
    EDITION_STUDIO,
    LicenseExpiredError,
    LicenseInvalidError,
    validate_license_key,
)
from src.photoorganizer_pro.license.keygen import generate_key  # noqa: E402
from src.photoorganizer_pro.license.validator import (  # noqa: E402
    _license_storage_path,
    load_active_license,
    save_license_key,
)


# ---------------------------------------------------------------------
# Génération + validation roundtrip
# ---------------------------------------------------------------------
class TestKeyGeneration:
    def test_generate_personal_one_year(self):
        future = date.today() + timedelta(days=365)
        key = generate_key("user@example.com", EDITION_PERSONAL, future)
        info = validate_license_key(key)
        assert info.email == "user@example.com"
        assert info.edition == EDITION_PERSONAL
        assert info.expires == future
        assert info.days_remaining() > 360

    def test_generate_studio(self):
        future = date.today() + timedelta(days=730)
        key = generate_key("studio@acme.io", EDITION_STUDIO, future)
        info = validate_license_key(key)
        assert info.edition == EDITION_STUDIO
        assert not info.is_lifetime

    def test_generate_lifetime(self):
        future = date.today() + timedelta(days=365 * 30)
        key = generate_key("forever@example.com", EDITION_LIFETIME, future)
        info = validate_license_key(key)
        assert info.is_lifetime
        assert info.days_remaining() > 365 * 29

    def test_invalid_edition_rejected(self):
        with pytest.raises(ValueError):
            generate_key("user@example.com", "XYZW", date.today() + timedelta(days=30))

    def test_invalid_email_rejected(self):
        with pytest.raises(ValueError):
            generate_key("not-an-email", EDITION_PERSONAL, date.today() + timedelta(days=30))


# ---------------------------------------------------------------------
# Rejets
# ---------------------------------------------------------------------
class TestKeyValidation:
    def test_empty_key_rejected(self):
        with pytest.raises(LicenseInvalidError):
            validate_license_key("")

    def test_random_string_rejected(self):
        with pytest.raises(LicenseInvalidError):
            validate_license_key("hello world")

    def test_wrong_prefix_rejected(self):
        with pytest.raises(LicenseInvalidError):
            validate_license_key("FAKE-PERS-20271231-aGVsbG8=-deadbeef")

    def test_tampered_signature_rejected(self):
        future = date.today() + timedelta(days=365)
        key = generate_key("user@example.com", EDITION_PERSONAL, future)
        # On change le dernier caractère de la signature.
        tampered = key[:-1] + ("0" if key[-1] != "0" else "1")
        with pytest.raises(LicenseInvalidError):
            validate_license_key(tampered)

    def test_expired_key_rejected(self):
        past = date.today() - timedelta(days=1)
        key = generate_key("user@example.com", EDITION_PERSONAL, past)
        with pytest.raises(LicenseExpiredError):
            validate_license_key(key)

    def test_modified_email_rejected(self):
        """Si on swap le payload (email), la signature ne matche plus."""
        future = date.today() + timedelta(days=365)
        key = generate_key("original@example.com", EDITION_PERSONAL, future)
        parts = key.split("-")
        # Replace base64 payload by another email's base64, sig reste celle de l'original.
        import base64

        parts[3] = base64.b64encode(b"attacker@example.com").decode("ascii")
        forged = "-".join(parts)
        with pytest.raises(LicenseInvalidError):
            validate_license_key(forged)


# ---------------------------------------------------------------------
# Persistance disque
# ---------------------------------------------------------------------
class TestLicensePersistence:
    def _cleanup(self):
        p = _license_storage_path()
        if p.exists():
            p.unlink()

    def setup_method(self):
        self._cleanup()

    def teardown_method(self):
        self._cleanup()

    def test_no_license_returns_none(self):
        assert load_active_license() is None

    def test_save_and_reload_valid_key(self):
        future = date.today() + timedelta(days=365)
        key = generate_key("user@example.com", EDITION_PERSONAL, future)
        save_license_key(key)
        info = load_active_license()
        assert info is not None
        assert info.email == "user@example.com"

    def test_expired_stored_key_treated_as_none(self):
        past = date.today() - timedelta(days=1)
        key = generate_key("user@example.com", EDITION_PERSONAL, past)
        save_license_key(key)
        assert load_active_license() is None  # silent rejection
