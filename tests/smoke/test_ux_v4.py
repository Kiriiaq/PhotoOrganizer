# -*- coding: utf-8 -*-
"""
Smoke tests refonte UX v4 — tooltips, panneau Renommage repliable,
sidebar Doublons élargie.

Couvre les exigences :
  - Tooltip module et factory ``attach_tooltip``
  - Dictionnaires tooltips_fr complets pour les 4 panneaux
  - Bibliothèque de templates de renommage (≥ 5 exemples)
  - Panneau Renommage repliable + 2 colonnes + exemples cliquables
  - Sidebar Doublons élargie ≥ 500 px
"""

import customtkinter as ctk
import pytest

# La fixture `app` est définie dans tests/conftest.py (session-scoped)
# pour partager une seule instance Tk entre tous les modules UI smoke.


# =============================================================================
# Module tooltip
# =============================================================================

class TestTooltipModule:
    def test_tooltip_class_importable(self):
        from ui.tooltip import Tooltip, attach_tooltip
        assert Tooltip is not None
        assert callable(attach_tooltip)

    def test_attach_tooltip_returns_instance(self, app):
        from ui.tooltip import Tooltip, attach_tooltip, has_tooltip
        btn = ctk.CTkButton(app, text="Test")
        tip = attach_tooltip(btn, "Texte de test")
        assert isinstance(tip, Tooltip)
        # Le widget est enregistré dans le registre de tooltips
        assert has_tooltip(btn)

    def test_attach_tooltip_no_op_with_empty_text(self, app):
        from ui.tooltip import attach_tooltip
        btn = ctk.CTkButton(app, text="X")
        assert attach_tooltip(btn, "") is None
        assert attach_tooltip(btn, None) is None

    def test_tooltip_truncates_long_text(self, app):
        from ui.tooltip import Tooltip
        long_text = "a" * 1000
        btn = ctk.CTkButton(app, text="X")
        tip = Tooltip(btn, long_text)
        assert len(tip.text) <= 400


# =============================================================================
# Dictionnaires tooltips_fr
# =============================================================================

class TestTooltipsFr:
    def test_organize_dictionary_has_keys(self):
        from ui.tooltips_fr import ORGANIZE
        # Au moins les clés essentielles
        for key in ['btn_organize', 'btn_cancel', 'btn_analyze', 'btn_preview',
                    'source_entry', 'dest_entry', 'rename_template',
                    'multilayer', 'advanced_toggle']:
            assert key in ORGANIZE, f"Clé manquante : {key!r}"
            assert ORGANIZE[key], f"Tooltip vide pour : {key!r}"

    def test_duplicates_dictionary_has_keys(self):
        from ui.tooltips_fr import DUPLICATES
        for key in ['btn_search', 'btn_execute', 'btn_cancel',
                    'mode_dry_run', 'mode_delete', 'algorithm']:
            assert key in DUPLICATES, f"Clé manquante : {key!r}"

    def test_history_dictionary_has_keys(self):
        from ui.tooltips_fr import HISTORY
        for key in ['rollback_one', 'rollback_all', 'btn_clear', 'history_textbox']:
            assert key in HISTORY

    def test_settings_dictionary_has_keys(self):
        from ui.tooltips_fr import SETTINGS
        for key in ['schedule_enabled', 'btn_save', 'btn_reset', 'cache_enabled']:
            assert key in SETTINGS

    def test_all_tooltips_are_strings(self):
        from ui.tooltips_fr import APP, DUPLICATES, HISTORY, ORGANIZE, SETTINGS
        for d in (ORGANIZE, DUPLICATES, HISTORY, SETTINGS, APP):
            for k, v in d.items():
                assert isinstance(v, str), f"Clé {k} : valeur non-str ({type(v)})"
                assert len(v) >= 10, f"Clé {k} : tooltip trop court ({v!r})"


# =============================================================================
# Bibliothèque de templates de renommage
# =============================================================================

class TestRenameTemplatesLibrary:
    def test_at_least_5_examples(self):
        from ui.prompt_examples import RENAME_TEMPLATES
        assert len(RENAME_TEMPLATES) >= 5, \
            f"Au moins 5 templates attendus, trouvé {len(RENAME_TEMPLATES)}"

    def test_each_example_has_label_template_description(self):
        from ui.prompt_examples import RENAME_TEMPLATES
        for tpl in RENAME_TEMPLATES:
            assert tpl.label, "Label vide"
            # template peut être vide (cas "Garder le nom d'origine")
            assert isinstance(tpl.template, str)
            assert tpl.description, f"Description vide pour {tpl.label}"
            assert tpl.preview, f"Preview vide pour {tpl.label}"

    def test_get_template_by_label(self):
        from ui.prompt_examples import RENAME_TEMPLATES, get_template_by_label
        # Premier exemple connu
        first = RENAME_TEMPLATES[0]
        assert get_template_by_label(first.label) == first.template
        # Inexistant
        assert get_template_by_label("inexistant") == ""


# =============================================================================
# Panneau Renommage refondu (Lot 4)
# =============================================================================

class TestRenameSectionV4:
    def test_collapsible_toggle_button_present(self, app):
        of = app.organize_frame
        assert hasattr(of, "_rename_toggle_btn"), \
            "Bouton de pliage manquant"
        assert hasattr(of, "_rename_content"), \
            "Container content manquant"
        assert hasattr(of, "_rename_collapsed"), \
            "Attribut d'état manquant"

    def test_examples_buttons_created(self, app):
        of = app.organize_frame
        assert hasattr(of, "_rename_example_btns"), \
            "Liste des boutons exemples manquante"
        assert len(of._rename_example_btns) >= 5

    def test_apply_example_updates_template(self, app):
        of = app.organize_frame
        # Sauvegarde valeur courante
        prev = of.rename_template.get()
        of._apply_rename_example("{date:%Y%m%d}_test")
        assert of.rename_template.get() == "{date:%Y%m%d}_test"
        # Reset
        of._apply_rename_example(prev)

    def test_toggle_persists_state(self, app):
        of = app.organize_frame
        initial = of._rename_collapsed
        of._toggle_rename_section()
        assert of._rename_collapsed != initial
        # Vérifier que get_config a bien été mis à jour
        from utils.config import get_config
        cfg = get_config().config
        assert cfg.rename_collapsed == of._rename_collapsed
        # Reset
        of._toggle_rename_section()


# =============================================================================
# Sidebar Doublons élargie (Lot 5)
# =============================================================================

class TestDuplicatesSidebarWidth:
    def test_sidebar_minsize_increased(self, app):
        """La sidebar Options a été passée de 320 à ≥ 500 px."""
        df = app.duplicates_frame
        # Activer l'onglet Doublons pour propager le layout
        app.tabview.set("🔍 Doublons")
        for _ in range(3):
            app.update_idletasks()
            app.update()

        # La column 0 du split-frame doit avoir minsize ≥ 500
        # On parcourt les enfants de DuplicatesFrame pour trouver la grille
        for child in df.winfo_children():
            try:
                cfg = child.grid_columnconfigure(0)
                minsize = cfg.get("minsize", 0)
                if minsize and minsize >= 500:
                    return  # OK trouvé
            except Exception:
                continue
        pytest.fail("Aucun enfant de DuplicatesFrame n'a column 0 minsize ≥ 500")


# =============================================================================
# Tooltips effectivement attachés
# =============================================================================

class TestTooltipsAttachedToKeyWidgets:
    """Vérifie via ``ui.tooltip.has_tooltip`` que les widgets clés ont
    bien un tooltip attaché. Plus fiable que l'inspection des bindings
    Tcl car CTk* surcharge ``bind()`` et route vers des sous-widgets."""

    def test_organize_buttons_have_tooltips(self, app):
        from ui.tooltip import has_tooltip
        of = app.organize_frame
        for name in ('organize_button', 'cancel_button',
                     'analyze_button', 'preview_button',
                     'source_entry', 'dest_entry',
                     'file_count_label', 'multilayer_switch',
                     '_adv_toggle_btn'):
            widget = getattr(of, name)
            assert has_tooltip(widget), \
                f"organize_frame.{name} sans tooltip"

    def test_duplicates_buttons_have_tooltips(self, app):
        from ui.tooltip import has_tooltip
        df = app.duplicates_frame
        for name in ('search_button', 'execute_button', 'cancel_button'):
            widget = getattr(df, name)
            assert has_tooltip(widget), \
                f"duplicates_frame.{name} sans tooltip"

    def test_history_buttons_have_tooltips(self, app):
        from ui.tooltip import has_tooltip
        hf = app.history_frame
        for name in ('rollback_one_button', 'rollback_all_button',
                     'clear_button', 'history_textbox'):
            widget = getattr(hf, name)
            assert has_tooltip(widget), \
                f"history_frame.{name} sans tooltip"

    def test_settings_schedule_switch_has_tooltip(self, app):
        from ui.tooltip import has_tooltip
        sf = app.settings_frame
        assert has_tooltip(sf.schedule_switch), \
            "settings_frame.schedule_switch sans tooltip"
