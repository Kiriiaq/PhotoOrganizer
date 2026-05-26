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
                    'multilayer', 'advanced_toggle',
                    # Refonte 2026-05-18 — bouton 💡 et champ marques
                    'filter_camera_make', 'brand_examples_btn',
                    # Refonte 2026-05-19 — bouton 💡 Exemples de filtres
                    'filter_examples_btn']:
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

    def test_rename_section_always_visible(self, app):
        """Refonte v2.3 (Variante B) : Renommage accessible dans son onglet.

        Le panneau Renommage est déplacé dans l'onglet interne
        « 🏷️ Renommer ». ``_rename_content`` est créé et géré par grid
        dans son onglet ; il est mappé dès que l'onglet est activé.
        ``_rename_collapsed`` reste à False (rétrocompat).
        """
        of = app.organize_frame
        assert of._rename_collapsed is False, (
            "Refonte v2.3 : pas de toggle collapsible Renommage (Variante B)"
        )
        # Vérifier que _rename_content est bien créé et géré par grid.
        # L'invariant Variante B est : « le contenu existe, est dans le bon
        # onglet, et son master est la wrapper de l'onglet Renommer ».
        # winfo_ismapped() est trop dépendant de l'ordre d'activation des
        # onglets et n'est PAS un invariant fiable cross-test (CTkTabview
        # n'applique pas immédiatement le mapping côté Tcl).
        assert of._rename_content.grid_info(), (
            "Refonte v2.3 : _rename_content doit être managé par grid"
        )
        # Vérifier la chaîne de parents : _rename_content → wrapper → _tab_rename
        parent = of._rename_content.master
        assert parent is not None
        grandparent = parent.master
        if hasattr(of, "_tab_rename"):
            assert grandparent is of._tab_rename, (
                f"Refonte v2.3 : _rename_content doit être dans le tab "
                f"Renommer (trouvé : {grandparent})"
            )

    def test_toggle_rename_method_still_callable(self, app):
        """Rétrocompat : ``_toggle_rename_section`` reste appelable sans crash
        même si le bouton n'est plus affiché (refonte v2.2)."""
        of = app.organize_frame
        try:
            of._toggle_rename_section()
        except Exception as exc:
            raise AssertionError(
                f"_toggle_rename_section ne doit pas crasher : {exc}"
            )


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
                     '_adv_toggle_btn',
                     # Refonte 2026-05-18 — bouton 💡 Exemples de marques
                     'brand_examples_btn',
                     # Refonte 2026-05-19 — bouton 💡 Exemples de filtres
                     'filter_examples_btn'):
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


# =============================================================================
# Refonte 2026-05-18 — invariant « pas de nouvelles fenêtres »
# =============================================================================

class TestNoToplevelInOrganizePanels:
    """Invariant utilisateur : les actions du panneau Organisation
    (Aperçu, Fichiers détectés, Exemples de marques, Sauvegarder preset,
    Organisation terminée) ne créent PAS de fenêtre CTkToplevel — elles
    affichent un panneau inline qui remplace temporairement le tabview.

    On vérifie ici les méthodes qui n'ont pas d'effet de bord disque
    (les autres demandent un dossier source/destination valide).
    """

    @staticmethod
    def _count_toplevels(app):
        """Compte les CTkToplevel actifs sous la fenêtre principale."""
        import customtkinter as ctk_local
        return sum(
            1 for w in app.winfo_children()
            if isinstance(w, ctk_local.CTkToplevel)
        )

    def test_brand_examples_panel_does_not_create_toplevel(self, app):
        of = app.organize_frame
        before = self._count_toplevels(app)
        of._show_brand_examples_panel()
        for _ in range(2):
            app.update_idletasks()
            app.update()
        try:
            after = self._count_toplevels(app)
            assert after == before, (
                f"_show_brand_examples_panel doit utiliser un panneau "
                f"inline, pas un Toplevel (avant={before}, après={after})"
            )
            # Et un panneau inline doit avoir été créé
            assert of._inline_panel is not None
        finally:
            # Fermer le panneau pour ne pas polluer les tests suivants
            if of._inline_panel is not None:
                try:
                    of._inline_panel.destroy()
                except Exception:
                    pass
                of._inline_panel = None
            try:
                of._main_tabview.grid()
            except Exception:
                pass

    def test_files_list_panel_does_not_create_toplevel(self, app):
        """`_show_files_list` (déclenché par le bouton 📋) doit aussi
        utiliser le panneau inline — même quand la source est vide."""
        of = app.organize_frame
        prev_source = of.source_var.get()
        of.source_var.set("")  # cas « aucun fichier trouvé »
        before = self._count_toplevels(app)
        try:
            of._show_files_list()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            after = self._count_toplevels(app)
            assert after == before, (
                f"_show_files_list doit utiliser un panneau inline "
                f"(avant={before}, après={after})"
            )
            assert of._inline_panel is not None
        finally:
            if of._inline_panel is not None:
                try:
                    of._inline_panel.destroy()
                except Exception:
                    pass
                of._inline_panel = None
            try:
                of._main_tabview.grid()
            except Exception:
                pass
            of.source_var.set(prev_source)


# =============================================================================
# Refonte 2026-05-18 — bouton 💡 ajoute / déduplique les marques
# =============================================================================

class TestBrandExamplesPanelBehavior:
    """Tests fonctionnels sur le panneau « Exemples de marques » :
       - un clic sur une marque met à jour `filter_camera_make`
       - la déduplication empêche d'ajouter 2× la même marque
       - le bouton 🗑 Vider remet le champ à vide
    """

    def test_panel_renders_common_brands_buttons(self, app):
        of = app.organize_frame
        prev = of.filter_camera_make.get()
        of.filter_camera_make.set("")
        try:
            of._show_brand_examples_panel()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            assert of._inline_panel is not None

            from ui.frames.organize_frame import OrganizeFrame
            labels = {
                w.cget('text')
                for w in OrganizeFrame._iter_descendants(of._inline_panel)
                if hasattr(w, 'cget') and 'text' in w.keys()
            }
            # Au moins 3 marques courantes doivent être présentes
            common = set(OrganizeFrame.COMMON_CAMERA_MAKES)
            present = labels & common
            assert len(present) >= 3, (
                f"Marques courantes manquantes dans le panneau (trouvées : {present})"
            )
        finally:
            if of._inline_panel is not None:
                try:
                    of._inline_panel.destroy()
                except Exception:
                    pass
                of._inline_panel = None
            try:
                of._main_tabview.grid()
            except Exception:
                pass
            of.filter_camera_make.set(prev)

    def test_filter_examples_panel_does_not_create_toplevel(self, app):
        """Le panneau 💡 Exemples de filtres est intégré (refonte 2026-05-19)."""
        of = app.organize_frame
        before = TestNoToplevelInOrganizePanels._count_toplevels(app)
        of._show_filter_examples_panel()
        for _ in range(2):
            app.update_idletasks()
            app.update()
        try:
            after = TestNoToplevelInOrganizePanels._count_toplevels(app)
            assert after == before, (
                f"_show_filter_examples_panel doit utiliser un panneau intégré, "
                f"pas une nouvelle fenêtre (avant={before}, après={after})"
            )
            assert of._inline_panel is not None
        finally:
            if of._inline_panel is not None:
                try:
                    of._inline_panel.destroy()
                except Exception:
                    pass
                of._inline_panel = None
            try:
                of._main_tabview.grid()
            except Exception:
                pass

    def test_clicking_brand_button_appends_to_csv(self, app):
        """Cliquer un bouton de marque ajoute son label au champ CSV
        `filter_camera_make`. Le doublon est ignoré."""
        of = app.organize_frame
        prev = of.filter_camera_make.get()
        of.filter_camera_make.set("")
        try:
            of._show_brand_examples_panel()
            for _ in range(2):
                app.update_idletasks()
                app.update()

            import customtkinter as ctk_local

            from ui.frames.organize_frame import OrganizeFrame
            # Trouver le bouton « Sony » (présent dans COMMON_CAMERA_MAKES).
            # Filtrer sur CTkButton car le panneau contient aussi des Labels
            # avec le même texte (récap « ✏️ Champ actuel ») qui ne sont pas
            # cliquables.
            sony_btn = None
            for w in OrganizeFrame._iter_descendants(of._inline_panel):
                if not isinstance(w, ctk_local.CTkButton):
                    continue
                try:
                    if w.cget('text') == "Sony":
                        sony_btn = w
                        break
                except Exception:
                    continue
            assert sony_btn is not None, "Bouton « Sony » introuvable dans le panneau"

            # 1er clic : ajoute Sony
            sony_btn.invoke()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            assert of.filter_camera_make.get() == "Sony", (
                f"Attendu 'Sony', trouvé : {of.filter_camera_make.get()!r}"
            )
            # 2e clic : pas de doublon
            sony_btn.invoke()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            assert of.filter_camera_make.get() == "Sony", (
                "La déduplication n'a pas fonctionné — "
                f"trouvé : {of.filter_camera_make.get()!r}"
            )
        finally:
            if of._inline_panel is not None:
                try:
                    of._inline_panel.destroy()
                except Exception:
                    pass
                of._inline_panel = None
            try:
                of._main_tabview.grid()
            except Exception:
                pass
            of.filter_camera_make.set(prev)


# =============================================================================
# Refonte 2026-05-19 — panneau 💡 Exemples de filtres (comportement)
# =============================================================================

class TestFilterExamplesPanelBehavior:
    """Tests fonctionnels sur le panneau « Exemples de filtres » :
       - un clic sur un mot-clé met à jour `filter_keywords` (CSV cumulatif)
       - un clic sur une extension cumule dans `filter_extensions`
       - les boutons ↧ min / ↥ max appliquent une dimension au bon champ
       - les boutons d'orientation et de note appliquent la bonne valeur
    """

    @staticmethod
    def _open_panel_and_get_buttons(app):
        """Ouvre le panneau filtres et retourne ses boutons cliquables."""
        import customtkinter as ctk_local

        from ui.frames.organize_frame import OrganizeFrame
        of = app.organize_frame
        of._show_filter_examples_panel()
        for _ in range(2):
            app.update_idletasks()
            app.update()
        assert of._inline_panel is not None
        buttons = [
            w for w in OrganizeFrame._iter_descendants(of._inline_panel)
            if isinstance(w, ctk_local.CTkButton)
        ]
        return of, buttons

    @staticmethod
    def _find_button(buttons, text):
        for b in buttons:
            try:
                if b.cget('text') == text:
                    return b
            except Exception:
                continue
        return None

    @staticmethod
    def _close_panel(of):
        if of._inline_panel is not None:
            try:
                of._inline_panel.destroy()
            except Exception:
                pass
            of._inline_panel = None
        try:
            of._main_tabview.grid()
        except Exception:
            pass

    def test_clicking_keyword_appends_to_csv(self, app):
        of = app.organize_frame
        prev = of.filter_keywords.get()
        of.filter_keywords.set("")
        try:
            of, buttons = self._open_panel_and_get_buttons(app)
            btn = self._find_button(buttons, "vacances")
            assert btn is not None, "Bouton « vacances » introuvable"
            btn.invoke()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            assert of.filter_keywords.get() == "vacances"
            # 2e clic : pas de doublon
            btn.invoke()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            assert of.filter_keywords.get() == "vacances"
        finally:
            self._close_panel(of)
            of.filter_keywords.set(prev)

    def test_clicking_extension_appends_to_csv(self, app):
        of = app.organize_frame
        prev = of.filter_extensions.get()
        of.filter_extensions.set("")
        try:
            of, buttons = self._open_panel_and_get_buttons(app)
            jpg = self._find_button(buttons, "jpg")
            cr2 = self._find_button(buttons, "cr2")
            assert jpg is not None and cr2 is not None
            jpg.invoke()
            cr2.invoke()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            # CSV cumule jpg + cr2 (sections images puis RAW partagent le champ)
            assert of.filter_extensions.get() == "jpg,cr2"
        finally:
            self._close_panel(of)
            of.filter_extensions.set(prev)

    def test_clicking_dimension_min_max(self, app):
        of = app.organize_frame
        prev_min = of.filter_dim_min.get()
        prev_max = of.filter_dim_max.get()
        of.filter_dim_min.set("")
        of.filter_dim_max.set("")
        try:
            of, buttons = self._open_panel_and_get_buttons(app)
            mins = [b for b in buttons if b.cget('text') == "↧ min"]
            maxs = [b for b in buttons if b.cget('text') == "↥ max"]
            assert len(mins) == len(of.COMMON_DIMENSIONS), (
                f"Nombre de boutons ↧ min ({len(mins)}) ≠ COMMON_DIMENSIONS ({len(of.COMMON_DIMENSIONS)})"
            )
            assert len(maxs) == len(of.COMMON_DIMENSIONS)
            # Premier min (la plus petite dimension) puis dernier max (8K)
            mins[0].invoke()
            maxs[-1].invoke()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            assert of.filter_dim_min.get() == of.COMMON_DIMENSIONS[0][1]
            assert of.filter_dim_max.get() == of.COMMON_DIMENSIONS[-1][1]
        finally:
            self._close_panel(of)
            of.filter_dim_min.set(prev_min)
            of.filter_dim_max.set(prev_max)

    def test_clicking_orientation_sets_value(self, app):
        of = app.organize_frame
        prev = of.filter_orientation.get()
        of.filter_orientation.set("any")
        try:
            of, buttons = self._open_panel_and_get_buttons(app)
            btn = self._find_button(buttons, "Portrait")
            assert btn is not None, "Bouton « Portrait » introuvable"
            btn.invoke()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            assert of.filter_orientation.get() == "portrait"
        finally:
            self._close_panel(of)
            of.filter_orientation.set(prev)

    def test_clicking_rating_sets_value(self, app):
        of = app.organize_frame
        prev = of.filter_rating_min.get()
        of.filter_rating_min.set(0)
        try:
            of, buttons = self._open_panel_and_get_buttons(app)
            btn4 = self._find_button(buttons, "★" * 4)
            assert btn4 is not None, "Bouton 4 étoiles introuvable"
            btn4.invoke()
            for _ in range(2):
                app.update_idletasks()
                app.update()
            assert of.filter_rating_min.get() == 4
        finally:
            self._close_panel(of)
            of.filter_rating_min.set(prev)


# =============================================================================
# Pivot 2026-05-26 — Badge licence + panneau d'activation inline
# =============================================================================

class TestLicenseBadge:
    """Vérifie l'intégration UI du système trial+unlock (cf. pivot 2026-05)."""

    def test_license_badge_attribute_present(self, app):
        """L'app expose ``license_badge`` dans son header (header v3+)."""
        assert hasattr(app, "license_badge"), (
            "PhotoOrganizerApp doit exposer un attribut license_badge "
            "(badge cliquable d'état essai/licence dans le header)"
        )
        # Et il a bien un texte non vide après initialisation
        text = app.license_badge.cget("text")
        assert isinstance(text, str) and len(text) > 0

    def test_refresh_license_badge_method_callable(self, app):
        """``refresh_license_badge()`` est appelable et idempotent."""
        assert hasattr(app, "refresh_license_badge")
        # Doit pouvoir être appelée plusieurs fois sans crash
        app.refresh_license_badge()
        app.refresh_license_badge()
        app.update_idletasks()

    def test_badge_text_matches_state(self, app):
        """Le texte du badge reflète l'état renvoyé par licensing.get_state()."""
        from utils import licensing
        state = licensing.get_state()
        expected = state.status_badge_text
        # On force un refresh pour synchroniser
        app.refresh_license_badge()
        app.update_idletasks()
        actual = app.license_badge.cget("text")
        assert actual == expected, f"Badge='{actual}' mais get_state()='{expected}'"


class TestUnlockPanel:
    """Vérifie le panneau d'activation inline dans OrganizeFrame."""

    @staticmethod
    def _close_panel(of):
        if of._inline_panel is not None:
            try:
                of._inline_panel.destroy()
            except Exception:
                pass
            of._inline_panel = None
        try:
            of._main_tabview.grid()
        except Exception:
            pass

    def test_show_unlock_panel_method_exists(self, app):
        of = app.organize_frame
        assert hasattr(of, "_show_unlock_panel")
        assert callable(of._show_unlock_panel)

    def test_show_unlock_panel_creates_inline_panel(self, app):
        """L'appel à _show_unlock_panel ne lève pas et crée un panneau inline."""
        import tkinter as tk
        of = app.organize_frame

        # État avant
        toplevels_before = [
            w for w in app.winfo_children() if isinstance(w, tk.Toplevel)
        ]

        try:
            of._show_unlock_panel()
            for _ in range(3):
                app.update_idletasks()
                app.update()

            # Le panneau inline est bien créé
            assert of._inline_panel is not None, "Inline panel doit être créé"

            # Aucun Toplevel n'a été spawned (préférence projet stricte)
            toplevels_after = [
                w for w in app.winfo_children() if isinstance(w, tk.Toplevel)
            ]
            assert len(toplevels_after) == len(toplevels_before), (
                "Le panneau d'activation NE DOIT PAS créer de Toplevel "
                "(cf. préférence durable : OrganizeFrame._show_inline_panel)"
            )
        finally:
            self._close_panel(of)

    def test_open_purchase_page_method_exists(self, app):
        of = app.organize_frame
        assert hasattr(of, "_open_purchase_page")
        assert callable(of._open_purchase_page)

    def test_refresh_license_badge_proxy(self, app):
        """OrganizeFrame doit pouvoir déclencher le refresh du badge global."""
        of = app.organize_frame
        # La méthode existe et ne lève pas même si l'app parent change
        assert callable(of._refresh_license_badge)
        of._refresh_license_badge()  # doit être no-op si l'app n'expose pas la méthode
