"""Tests fonctionnels du compteur trial + machine binding (v2.3+).

Couvre les 10 scénarios listés dans ``NEXT_STEPS.html`` §A.3 :

1. Premier lancement : compteur = 0
2. ``record_successful_organize()`` incrémente
3. 10e tri autorisé
4. 11e tri bloqué
5. Compteur falsifié → reset à 0 (HMAC mismatch)
6. ``activate_key()`` valide → débloque (illimité)
7. Clé bound à machine A → refusée sur machine B
8. Clé bound → re-validée sur même machine (reload app)
9. Clé mal formée → erreur, compteur intact
10. Clé expirée → ``LicenseExpiredError``

Isolation : chaque test reçoit un ``%LOCALAPPDATA%`` privé via fixture.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.photoorganizer_pro.license import validator as validator_mod  # noqa: E402
from src.photoorganizer_pro.license.keygen import generate_key  # noqa: E402
from src.photoorganizer_pro.license.validator import (  # noqa: E402
    EDITION_LIFETIME,
    LicenseExpiredError,
    LicenseInvalidError,
)
from src.utils import licensing  # noqa: E402


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------
@pytest.fixture
def isolated_appdata(tmp_path, monkeypatch):
    """Redirige ``%LOCALAPPDATA%`` vers ``tmp_path`` pour ce test.

    Le test reçoit un disque vierge (pas de usage.dat ni license.dat
    préexistants).
    """
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    # Sur OS non Windows, on patch aussi le fallback de _localappdata_root.
    monkeypatch.setattr(licensing.Path, "home", staticmethod(lambda: tmp_path / "home"))
    yield tmp_path


@pytest.fixture
def fixed_machine_id(monkeypatch):
    """Force une machine_id stable et permet de la changer en cours de test.

    Usage::

        def test_xx(fixed_machine_id):
            fixed_machine_id.set("a" * 64)
            ...
            fixed_machine_id.set("b" * 64)
            ...
    """

    class _MachineIdHolder:
        value: str = "a" * 64

        def set(self, mid: str) -> None:
            self.value = mid

    holder = _MachineIdHolder()
    monkeypatch.setattr(licensing, "_compute_machine_id", lambda: holder.value)
    monkeypatch.setattr(validator_mod, "_get_current_machine_id", lambda: holder.value)
    return holder


# ---------------------------------------------------------------------
# Compteur trial
# ---------------------------------------------------------------------
class TestTrialCounter:
    def test_first_run_count_zero(self, isolated_appdata, fixed_machine_id):
        """Scénario 1 : premier lancement, count = 0, 10 tris disponibles."""
        state = licensing.get_state()
        assert state.trial_count == 0
        assert state.trial_remaining == licensing.TRIAL_LIMIT
        assert not state.is_blocked
        assert not state.should_warn

    def test_record_increments(self, isolated_appdata, fixed_machine_id):
        """Scénario 2 : un tri réussi → count = 1."""
        state = licensing.record_successful_organize()
        assert state.trial_count == 1
        assert state.trial_remaining == 9

    def test_tenth_organize_still_allowed(self, isolated_appdata, fixed_machine_id):
        """Scénario 3 : le 10e tri est autorisé (avant de bloquer au 11e)."""
        for _ in range(9):
            licensing.record_successful_organize()
        allowed, state = licensing.can_organize_now()
        assert allowed
        assert state.trial_count == 9
        # Le 10e tri lui-même
        state = licensing.record_successful_organize()
        assert state.trial_count == 10
        assert state.is_blocked  # devient bloqué APRÈS le 10e

    def test_eleventh_organize_blocked(self, isolated_appdata, fixed_machine_id):
        """Scénario 4 : 11e tentative → bloqué."""
        for _ in range(10):
            licensing.record_successful_organize()
        allowed, state = licensing.can_organize_now()
        assert not allowed
        assert state.is_blocked

    def test_warning_at_8_and_9(self, isolated_appdata, fixed_machine_id):
        """should_warn vrai uniquement aux seuils 8 et 9."""
        for _ in range(7):
            licensing.record_successful_organize()
        assert not licensing.get_state().should_warn  # count=7

        licensing.record_successful_organize()
        assert licensing.get_state().should_warn  # count=8

        licensing.record_successful_organize()
        assert licensing.get_state().should_warn  # count=9

        licensing.record_successful_organize()
        assert not licensing.get_state().should_warn  # count=10, on bloque

    def test_tampered_counter_resets(self, isolated_appdata, fixed_machine_id):
        """Scénario 5 : count modifié sans regénérer HMAC → reset."""
        for _ in range(5):
            licensing.record_successful_organize()
        assert licensing.get_state().trial_count == 5

        # Tampering manuel : on remplace count=5 par count=0 sans
        # recalculer la signature (= ce que ferait un user "malin").
        path = licensing._usage_path()
        full = json.loads(path.read_text(encoding="utf-8"))
        full["payload"]["count"] = 0
        path.write_text(json.dumps(full, separators=(",", ":")), encoding="utf-8")

        # Le mismatch HMAC fait reset à 0 — comportement attendu côté
        # appli (l'utilisateur a "réussi" à reset à 0, mais ne pourra pas
        # remonter le compteur sans la clé HMAC).
        state = licensing.get_state()
        assert state.trial_count == 0


# ---------------------------------------------------------------------
# Activation + binding
# ---------------------------------------------------------------------
class TestActivationAndBinding:
    def _make_valid_key(self, email="user@example.com") -> str:
        future = date.today() + timedelta(days=365 * 30)
        return generate_key(email, EDITION_LIFETIME, future)

    def test_valid_key_unlocks(self, isolated_appdata, fixed_machine_id):
        """Scénario 6 : activation → illimité."""
        # On consomme 5 tris pour vérifier que l'activation persiste l'état
        for _ in range(5):
            licensing.record_successful_organize()
        assert licensing.get_state().trial_count == 5

        key = self._make_valid_key("alice@example.com")
        state = licensing.activate_key(key)
        assert state.has_valid_license
        assert state.license_email == "alice@example.com"

        # Désormais, peu importe le compteur, can_organize_now est True
        allowed, state2 = licensing.can_organize_now()
        assert allowed
        assert not state2.is_blocked

    def test_record_does_not_increment_after_activation(self, isolated_appdata, fixed_machine_id):
        """Avec licence active, record_successful_organize ne touche pas au count."""
        key = self._make_valid_key()
        licensing.activate_key(key)
        before = licensing.get_state().trial_count

        for _ in range(20):
            licensing.record_successful_organize()

        after = licensing.get_state().trial_count
        assert after == before  # gelé

    def test_key_bound_rejected_on_other_machine(self, isolated_appdata, fixed_machine_id):
        """Scénario 7 : clé activée sur machine A → refusée sur machine B."""
        fixed_machine_id.set("a" * 64)
        key = self._make_valid_key("alice@example.com")
        licensing.activate_key(key)
        assert licensing.get_state().has_valid_license

        # Simule un déménagement vers une autre machine (même license.dat
        # mais machine_id différent — équivalent à copier le fichier).
        fixed_machine_id.set("b" * 64)
        state = licensing.get_state()
        assert not state.has_valid_license

    def test_key_validates_on_same_machine(self, isolated_appdata, fixed_machine_id):
        """Scénario 8 : reload app sur même PC → licence toujours valide."""
        fixed_machine_id.set("c" * 64)
        key = self._make_valid_key("bob@example.com")
        licensing.activate_key(key)

        # Simule un nouveau lancement de l'app (machine_id inchangé).
        # On vide le module-level state en relisant via get_state().
        state = licensing.get_state()
        assert state.has_valid_license
        assert state.license_email == "bob@example.com"

    def test_malformed_key_rejected(self, isolated_appdata, fixed_machine_id):
        """Scénario 9 : clé mal formée → exception, compteur intact."""
        for _ in range(3):
            licensing.record_successful_organize()
        before_count = licensing.get_state().trial_count

        with pytest.raises(LicenseInvalidError):
            licensing.activate_key("not a real key")

        # Le compteur n'a pas bougé.
        assert licensing.get_state().trial_count == before_count

    def test_expired_key_rejected(self, isolated_appdata, fixed_machine_id):
        """Scénario 10 : clé valide mais expirée → LicenseExpiredError."""
        past = date.today() - timedelta(days=1)
        key = generate_key("user@example.com", EDITION_LIFETIME, past)
        with pytest.raises(LicenseExpiredError):
            licensing.activate_key(key)


# ---------------------------------------------------------------------
# Machine ID
# ---------------------------------------------------------------------
class TestMachineId:
    def test_machine_id_short_format(self):
        """``MAC-XXXX-XXXX`` à partir d'un hex 64 chars."""
        hex_id = "abcdef0123456789" * 4
        short = licensing.get_machine_id_short(hex_id)
        assert short == "MAC-ABCD-EF01"

    def test_machine_id_stable(self, fixed_machine_id):
        """Deux appels successifs renvoient le même hash sur la même machine."""
        fixed_machine_id.set("z" * 64)
        a = licensing.get_machine_id()
        b = licensing.get_machine_id()
        assert a == b


# ---------------------------------------------------------------------
# Badge text
# ---------------------------------------------------------------------
class TestBadgeText:
    def test_badge_trial(self, isolated_appdata, fixed_machine_id):
        for _ in range(3):
            licensing.record_successful_organize()
        state = licensing.get_state()
        assert state.status_badge_text == "Essai 3/10"

    def test_badge_blocked(self, isolated_appdata, fixed_machine_id):
        for _ in range(10):
            licensing.record_successful_organize()
        state = licensing.get_state()
        assert state.status_badge_text == "Limite atteinte · Activer"

    def test_badge_activated(self, isolated_appdata, fixed_machine_id):
        fixed_machine_id.set("f" * 64)
        future = date.today() + timedelta(days=365 * 30)
        key = generate_key("user@example.com", EDITION_LIFETIME, future)
        licensing.activate_key(key)
        state = licensing.get_state()
        assert state.status_badge_text.startswith("Activée · MAC-FFFF")
