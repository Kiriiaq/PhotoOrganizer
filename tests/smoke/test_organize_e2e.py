"""E2E du worker d'organisation — non-régression B-01 (audit 2026-06-11).

Le bug B-01 : `_organize_files` testait `result.success` (attribut
inexistant sur `OrganizationResult`) → AttributeError dans le thread
worker APRÈS le tri. Conséquences invisibles en test unitaire :

* le panneau « Organisation terminée » n'apparaissait jamais ;
* `licensing.record_successful_organize()` n'était jamais appelé
  (le compteur trial restait gelé à 0 en conditions réelles).

Les E2E trial existants (test_ux_v4) mockent le gate licensing mais ne
font jamais tourner le worker réel — ce test comble exactement ce trou :
il exécute le flux complet clic → confirmation → thread → résultats sur
de vraies images dans un dossier temporaire.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from utils import licensing  # noqa: E402  (même objet module que organize_frame)
from utils.licensing import TRIAL_LIMIT, LicenseState  # noqa: E402


def _fake_state(**overrides) -> LicenseState:
    defaults = dict(
        has_valid_license=False,
        trial_count=0,
        trial_remaining=TRIAL_LIMIT,
        machine_id="a" * 64,
        machine_id_short="MAC-AAAA-AAAA",
        license_email=None,
        is_blocked=False,
        should_warn=False,
    )
    defaults.update(overrides)
    return LicenseState(**defaults)


def test_organize_worker_records_trial_and_shows_results(app, tmp_path, monkeypatch):
    """Tri réel de 2 JPEG : le worker doit incrémenter le compteur trial
    (via record_successful_organize) ET afficher le panneau résultats."""
    from PIL import Image

    src_dir = tmp_path / "source"
    src_dir.mkdir()
    dst_dir = tmp_path / "dest"
    for i in range(2):
        Image.new("RGB", (40, 30), color=(i * 60, 80, 120)).save(src_dir / f"photo_{i}.jpg")

    of = app.organize_frame

    # --- Isolation licensing : aucun accès au vrai usage.dat/license.dat ---
    recorded = {"count": 0}

    def fake_record():
        recorded["count"] += 1
        return _fake_state(trial_count=recorded["count"])

    monkeypatch.setattr(licensing, "can_organize_now", lambda: (True, _fake_state()))
    monkeypatch.setattr(licensing, "get_state", lambda: _fake_state())
    monkeypatch.setattr(licensing, "record_successful_organize", fake_record)

    # --- Dialogues neutralisés (confirmation auto-acceptée) ---
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: True)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **k: None)

    old_source, old_dest = of.source_var.get(), of.dest_var.get()
    old_notify = of.notify_on_finish.get()
    try:
        of.notify_on_finish.set(False)  # pas de toast système pendant le test
        of.source_var.set(str(src_dir))
        of.dest_var.set(str(dst_dir))
        # Mode copie (défaut) — on force pour rendre le test auto-suffisant
        of.copy_not_move.set(True)

        of._organize_files()

        # Le worker lit des variables Tk depuis son thread : cela exige que
        # le main thread soit DANS mainloop (comme en production). On lance
        # donc un vrai mainloop avec un poller qui quitte dès que le worker
        # a fini et que le panneau résultats est affiché (timeout 30 s).
        deadline = time.time() + 30

        def poll():
            done = (
                not getattr(of, "_operation_running", False)
                and getattr(of, "_inline_panel", None) is not None
            )
            if done or time.time() > deadline:
                app.quit()
            else:
                app.after(50, poll)

        app.after(50, poll)
        app.mainloop()

        assert recorded["count"] == 1, (
            "record_successful_organize doit être appelé exactement 1 fois "
            "après un tri réussi (régression B-01 si 0)"
        )
        assert getattr(of, "_inline_panel", None) is not None, (
            "le panneau « Organisation terminée » doit s'afficher (régression B-01)"
        )
        copied = list(dst_dir.rglob("*.jpg"))
        assert len(copied) == 2, f"2 fichiers attendus à destination, trouvé {len(copied)}"
    finally:
        # Remise en état de l'app partagée (fixture session-scoped)
        panel = getattr(of, "_inline_panel", None)
        if panel is not None:
            try:
                panel.destroy()
            except Exception:
                pass
            of._inline_panel = None
        try:
            of._main_tabview.grid()
        except Exception:
            pass
        of.notify_on_finish.set(old_notify)
        of.source_var.set(old_source)
        of.dest_var.set(old_dest)
