# -*- coding: utf-8 -*-
"""
Smoke tests structure UI après refonte v3.

Vérifie les invariants posés par le plan de refonte (cf. audit/01_inventaire.md
phase 3) — ces tests **bloquent** toute régression visuelle de l'IHM :
zones sticky, ordre des boutons, couleurs sémantiques, présence des sections.

Ils complètent les tests fonctionnels existants en ajoutant une couche
"contract UI" : si quelqu'un casse le layout sans s'en rendre compte
(ex. retire la zone bottom, change la couleur d'un bouton, déplace
l'action principale à gauche), ces tests échouent immédiatement.

Note : tous les tests créent une vraie instance ``PhotoOrganizerApp`` via
la fixture ``app`` (téléchargée plusieurs fois → marqueur ``slow`` n'est
PAS appliqué car les tests doivent tourner à chaque CI).
"""

import customtkinter as ctk

# La fixture `app` est définie dans tests/conftest.py (session-scoped)
# pour partager une seule instance Tk entre tous les modules UI smoke.


# =============================================================================
# OrganizeFrame — refonte v3 : 3 zones + design system
# =============================================================================

class TestOrganizeFrameV3:
    def test_three_zones_present(self, app):
        """Les 3 zones top/scroll/bottom existent et sont attachées."""
        of = app.organize_frame
        assert hasattr(of, '_top_zone'), "Zone TOP manquante"
        assert hasattr(of, '_scroll'), "Zone CENTRE scroll manquante"
        assert hasattr(of, '_bottom_zone'), "Zone BOTTOM manquante"

    def test_three_zones_mapped(self, app):
        """Les 3 zones sont effectivement visibles à l'écran."""
        app.tabview.set("📁 Organisation")
        for _ in range(2):
            app.update_idletasks()
            app.update()
        of = app.organize_frame
        assert of._top_zone.winfo_ismapped(), "Zone TOP pas mappée"
        assert of._scroll.winfo_ismapped(), "Zone CENTRE pas mappée"
        assert of._bottom_zone.winfo_ismapped(), "Zone BOTTOM pas mappée"

    def test_organize_button_is_primary_right(self, app):
        """Bouton Organiser : vert PRIMARY, hauteur 40, à droite du Cancel."""
        of = app.organize_frame
        # Couleur Material PRIMARY
        assert of.organize_button.cget('fg_color') == ('#2E7D32', '#1B5E20')
        # Hauteur primary
        assert of.organize_button.cget('height') == 40
        # Convention desktop : action principale à droite
        app.tabview.set("📁 Organisation")
        for _ in range(2):
            app.update_idletasks()
            app.update()
        org_x = of.organize_button.winfo_x()
        cancel_x = of.cancel_button.winfo_x()
        assert org_x > cancel_x, (
            f"Organiser doit être à droite du Cancel (org_x={org_x}, cancel_x={cancel_x})"
        )

    def test_cancel_button_is_danger_std(self, app):
        """Bouton Annuler : rouge DANGER, hauteur 32."""
        of = app.organize_frame
        assert of.cancel_button.cget('fg_color') == ('#C62828', '#8E0000')
        assert of.cancel_button.cget('height') == 32

    def test_advanced_section_collapsed_by_default(self, app):
        """Le panneau « Avancé » démarre replié."""
        of = app.organize_frame
        assert of._adv_collapsed is True, (
            "Panneau Avancé devrait être replié par défaut"
        )
        assert not of._adv_content.winfo_ismapped(), (
            "Contenu Avancé ne devrait pas être visible au démarrage"
        )

    def test_advanced_toggle_expand_collapse(self, app):
        """Toggle ▶/▼ déploie puis replie le panneau Avancé."""
        of = app.organize_frame
        # Reset à l'état initial collapsed
        if not of._adv_collapsed:
            of._toggle_advanced_section()
            for _ in range(2):
                app.update_idletasks()
                app.update()

        # Expand
        of._toggle_advanced_section()
        for _ in range(2):
            app.update_idletasks()
            app.update()
        assert of._adv_collapsed is False
        assert of._adv_content.winfo_ismapped()

        # Re-collapse
        of._toggle_advanced_section()
        for _ in range(2):
            app.update_idletasks()
            app.update()
        assert of._adv_collapsed is True
        assert not of._adv_content.winfo_ismapped()

    def test_file_count_in_top_zone_not_scroll(self, app):
        """Le compteur fichiers est en zone TOP (toujours visible),
        pas dans le scroll central."""
        of = app.organize_frame
        # Le compteur doit être un descendant de _top_zone, PAS de _scroll
        parent = of.file_count_label.master
        # Remonter la chaîne des parents
        seen_top = False
        seen_scroll = False
        while parent is not None:
            if parent is of._top_zone:
                seen_top = True
                break
            if parent is of._scroll:
                seen_scroll = True
                break
            parent = getattr(parent, 'master', None)
        assert seen_top and not seen_scroll, (
            "file_count_label doit être dans _top_zone, pas _scroll"
        )

    def test_no_separate_schedule_section(self, app):
        """La section Planification a été DÉPLACÉE vers Settings (refonte v3)."""
        of = app.organize_frame
        # _create_schedule_section doit exister mais être un no-op
        # (les vars schedule_* sont conservées dans __init__)
        assert hasattr(of, 'schedule_enabled')
        assert hasattr(of, 'schedule_time')
        # En revanche, plus de schedule_switch sur OrganizeFrame
        assert not hasattr(of, 'schedule_switch'), (
            "schedule_switch doit avoir été déplacé vers SettingsFrame"
        )


# =============================================================================
# DuplicatesFrame — refonte v3 : split sidebar + résultats permanents
# =============================================================================

class TestDuplicatesFrameV3:
    def test_tabview_only_results_and_details(self, app):
        """Le tabview ne contient plus que Resultats/Details (Options
        est passé en sidebar)."""
        df = app.duplicates_frame
        tabs = list(df.main_tabview._tab_dict.keys())
        assert tabs == ['Resultats', 'Details'], (
            f"Tabview attendu = ['Resultats', 'Details'], trouvé : {tabs}"
        )

    def test_execute_button_primary_40(self, app):
        """Bouton Exécuter : primary 40px, change de couleur selon le mode."""
        df = app.duplicates_frame
        assert df.execute_button.cget('height') == 40
        # Mode initial DRY_RUN → vert PRIMARY
        assert df.execute_button.cget('fg_color') == ('#2E7D32', '#1B5E20')

    def test_cancel_button_danger_32(self, app):
        """Bouton Annuler : rouge DANGER 32."""
        df = app.duplicates_frame
        assert df.cancel_button.cget('height') == 32
        assert df.cancel_button.cget('fg_color') == ('#C62828', '#8E0000')

    def test_mode_change_recolors_execute(self, app):
        """Le bouton Exécuter change de couleur selon le mode sélectionné."""
        df = app.duplicates_frame
        # DELETE → rouge
        df.execution_mode.set('DELETE')
        df._on_mode_change()
        assert df.execute_button.cget('fg_color') == ('#C62828', '#8E0000')
        # TRASH → orange
        df.execution_mode.set('TRASH')
        df._on_mode_change()
        assert df.execute_button.cget('fg_color') == ('#EF6C00', '#B53D00')
        # MOVE → bleu
        df.execution_mode.set('MOVE')
        df._on_mode_change()
        assert df.execute_button.cget('fg_color') == ('#1565C0', '#0D47A1')
        # Reset DRY_RUN
        df.execution_mode.set('DRY_RUN')
        df._on_mode_change()


# =============================================================================
# HistoryFrame — refonte v3 : compactage
# =============================================================================

class TestHistoryFrameV3:
    def test_no_warning_label(self, app):
        """Le warning orange permanent a été supprimé (info dans confirmation)."""
        hf = app.history_frame
        assert not hasattr(hf, 'warning_label'), (
            "warning_label devrait avoir été supprimé en v3"
        )

    def test_rollback_buttons_warning_orange(self, app):
        """Boutons rollback : orange WARNING."""
        hf = app.history_frame
        expected = ('#EF6C00', '#B53D00')
        assert hf.rollback_one_button.cget('fg_color') == expected
        assert hf.rollback_all_button.cget('fg_color') == expected

    def test_clear_button_danger_red(self, app):
        """Bouton Effacer : rouge DANGER (action destructrice)."""
        hf = app.history_frame
        assert hf.clear_button.cget('fg_color') == ('#C62828', '#8E0000')

    def test_stats_inline_compact(self, app):
        """Le stats_label démarre avec un texte court (1 ligne)."""
        hf = app.history_frame
        text = hf.stats_label.cget('text')
        assert text == "Aucune opération", f"Stats label inattendu : {text!r}"


# =============================================================================
# SettingsFrame — refonte v3 : sticky bottom + section Planification
# =============================================================================

class TestSettingsFrameV3:
    def test_schedule_section_present(self, app):
        """Section Planification déplacée d'Organize vers Settings."""
        sf = app.settings_frame
        assert hasattr(sf, 'schedule_switch'), (
            "schedule_switch devrait être créé sur SettingsFrame"
        )

    def test_schedule_switch_writes_back_to_organize_var(self, app):
        """Le switch Settings.schedule_switch utilise les vars d'OrganizeFrame
        (référencement croisé via winfo_toplevel().organize_frame)."""
        sf = app.settings_frame
        of = app.organize_frame
        # Toggle le switch
        previous = of.schedule_enabled.get()
        sf.schedule_switch.toggle()
        for _ in range(2):
            app.update_idletasks()
            app.update()
        assert of.schedule_enabled.get() != previous
        # Reset
        sf.schedule_switch.toggle()
        for _ in range(2):
            app.update_idletasks()
            app.update()


# =============================================================================
# App root — refonte v3 : minsize + header
# =============================================================================

class TestAppRootV3:
    def test_minsize_at_least_800x550(self, app):
        """minsize ≥ 800×550 pour garantir le layout 3-zones d'Organize.

        Sur écrans HiDPI le minsize effectif peut être scaled (ex. 1200×825
        à scaling 1.5). On vérifie ≥, pas ==.
        """
        mw, mh = app.wm_minsize()
        assert mw >= 800, f"minsize width {mw} < 800"
        assert mh >= 550, f"minsize height {mh} < 550"

    def test_header_buttons_normalized(self, app):
        """Boutons header thème/aide : largeur 40, hauteur 32 (icon-only std)."""
        assert app.theme_button.cget('width') == 40
        assert app.theme_button.cget('height') == 32

    def test_four_panels_instantiated(self, app):
        """Les 4 panneaux sont accessibles depuis l'app."""
        assert hasattr(app, 'organize_frame')
        assert hasattr(app, 'duplicates_frame')
        assert hasattr(app, 'history_frame')
        assert hasattr(app, 'settings_frame')

    def test_keyboard_shortcuts_navigate_tabs(self, app):
        """Ctrl+1..4 doit naviguer entre les onglets — bind via ``bind_all``
        pour fonctionner quel que soit le widget focus."""
        # bind_all utilise le namespace global Tcl 'all', pas la liaison
        # locale du widget. On interroge via tk.call('bind', 'all', ...).
        for i in range(1, 5):
            cmd = app.tk.call('bind', 'all', f'<Control-Key-{i}>')
            assert cmd, f"Ctrl+{i} non bindé via bind_all"


# =============================================================================
# Theme module — design system
# =============================================================================

class TestThemeModule:
    def test_constants_present(self):
        """theme.py expose les constantes attendues."""
        from ui import theme
        # Espacements
        assert theme.PAD_S == 4
        assert theme.PAD_M == 8
        assert theme.PAD_L == 16
        # Boutons
        assert theme.BTN_H_STD == 32
        assert theme.BTN_H_PRIMARY == 40
        # Couleurs sémantiques
        assert theme.COLOR_PRIMARY == ("#2E7D32", "#1B5E20")
        assert theme.COLOR_DANGER == ("#C62828", "#8E0000")
        assert theme.COLOR_WARNING == ("#EF6C00", "#B53D00")
        assert theme.COLOR_INFO == ("#1565C0", "#0D47A1")

    def test_factories_apply_design_system(self, app):
        """Les factories produisent des boutons conformes au design system."""
        from ui import theme
        # primary_button
        b = theme.primary_button(app, "Test")
        assert b.cget('height') == 40
        assert b.cget('fg_color') == ("#2E7D32", "#1B5E20")
        # danger_button
        b = theme.danger_button(app, "Test")
        assert b.cget('height') == 32
        assert b.cget('fg_color') == ("#C62828", "#8E0000")
        # icon_button
        b = theme.icon_button(app, "📂")
        assert b.cget('width') == 40
        assert b.cget('height') == 32
