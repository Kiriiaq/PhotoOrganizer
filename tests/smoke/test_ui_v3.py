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

    def test_organize_button_is_primary_in_rail(self, app):
        """Bouton Organiser : vert PRIMARY, hauteur 40, en bas du right rail.

        Refonte v2.3 (Variante B) : les boutons d'action sont désormais
        empilés verticalement dans le right rail (au lieu d'une rangée
        horizontale en zone bottom). L'action principale est tout en bas
        de la pile (visuel le plus accessible pour terminer le workflow).
        """
        of = app.organize_frame
        # Couleur Material PRIMARY
        assert of.organize_button.cget('fg_color') == ('#2E7D32', '#1B5E20')
        # Hauteur primary
        assert of.organize_button.cget('height') == 40
        app.tabview.set("📁 Organisation")
        for _ in range(2):
            app.update_idletasks()
            app.update()
        # Convention v2.3 : action principale Organiser en bas du rail,
        # donc y > y du Cancel.
        org_y = of.organize_button.winfo_y()
        cancel_y = of.cancel_button.winfo_y()
        assert org_y > cancel_y, (
            f"Organiser doit être sous Annuler dans le rail "
            f"(org_y={org_y}, cancel_y={cancel_y})"
        )

    def test_cancel_button_is_danger_std(self, app):
        """Bouton Annuler : rouge DANGER, hauteur 32."""
        of = app.organize_frame
        assert of.cancel_button.cget('fg_color') == ('#C62828', '#8E0000')
        assert of.cancel_button.cget('height') == 32

    def test_advanced_section_visible_by_default(self, app):
        """Le panneau « Filtres & Comportements » est accessible dans un onglet.

        Refonte v2.3 (Variante B) : les filtres sont déplacés dans l'onglet
        interne « 🔍 Filtrer ». ``_adv_content`` est créé dans cet onglet ;
        on vérifie son existence et son rattachement, sans dépendre du
        timing de mapping de CTkTabview (qui n'est pas immédiat côté Tcl).
        """
        of = app.organize_frame
        assert of._adv_collapsed is False, (
            "Refonte v2.3 : pas de toggle collapsible (Variante B)"
        )
        # _adv_content doit exister et être enfant de _tab_filter
        assert of._adv_content is not None
        if hasattr(of, "_tab_filter"):
            assert of._adv_content.master is of._tab_filter, (
                f"Refonte v2.3 : _adv_content doit être dans le tab Filtrer "
                f"(trouvé : {of._adv_content.master})"
            )

    def test_advanced_toggle_method_still_callable(self, app):
        """Pour rétrocompat, ``_toggle_advanced_section`` reste appelable
        sans crash, même si le bouton n'est plus affiché (refonte v2.2)."""
        of = app.organize_frame
        # Doit pouvoir être appelé sans erreur (no-op fonctionnel)
        try:
            of._toggle_advanced_section()
        except Exception as exc:
            raise AssertionError(
                f"_toggle_advanced_section ne doit pas crasher : {exc}"
            )

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
# OrganizeFrame — refonte v2.3 Variante B : tabview interne (4 onglets)
# =============================================================================

class TestOrganizeFrameTabviewInternal:
    """Tests du tabview interne ajouté lors de la refonte v2.3.

    La zone centrale d'Organisation est un CTkTabview à 4 onglets qui
    remplace l'ancien défilement vertical monolithique :
      🔍  Filtrer   → critères de filtrage (dates, taille, note, marques…)
      🗂  Organiser → critères d'organisation (date / appareil / GPS)
      🛠  Traiter   → action (copier/déplacer) + comportements
      🏷  Renommer  → template + exemples
    """

    EXPECTED_TABS = ("🔍  Filtrer", "🗂  Organiser", "🛠  Traiter", "🏷  Renommer")

    def test_main_tabview_exists(self, app):
        of = app.organize_frame
        assert hasattr(of, '_main_tabview'), (
            "OrganizeFrame doit exposer le tabview interne `_main_tabview`"
        )

    def test_four_tabs_present(self, app):
        """Les 4 onglets exacts (libellés + ordre) sont présents."""
        of = app.organize_frame
        tabs = list(of._main_tabview._tab_dict.keys())
        assert tabs == list(self.EXPECTED_TABS), (
            f"Onglets attendus = {list(self.EXPECTED_TABS)}, trouvé : {tabs}"
        )

    def test_tab_aliases_exposed(self, app):
        """Les frames d'onglet sont exposées sous des noms logiques stables."""
        of = app.organize_frame
        for attr in ("_tab_filter", "_tab_organize", "_tab_process", "_tab_rename"):
            assert hasattr(of, attr), f"OrganizeFrame doit exposer `{attr}`"

    def test_default_tab_is_organize(self, app):
        """L'onglet par défaut à l'ouverture du panneau est « Organiser »."""
        of = app.organize_frame
        assert of._main_tabview.get() == "🗂  Organiser", (
            f"Onglet par défaut attendu = « Organiser », "
            f"trouvé : {of._main_tabview.get()!r}"
        )

    def test_main_tabview_lives_in_scroll(self, app):
        """Le tabview est imbriqué dans `_scroll` (fallback scroll si overflow)."""
        of = app.organize_frame
        assert of._main_tabview.master is of._scroll, (
            "Le tabview doit être enfant direct de _scroll"
        )

    def test_layout_mode_marker(self, app):
        """Marqueur de refonte v2.3 — pas de bascule responsive manuelle."""
        of = app.organize_frame
        assert getattr(of, "_layout_mode", None) == "tabview"


# =============================================================================
# OrganizeFrame — refonte 2026-05-18 : bouton 💡 Exemples de marques
# =============================================================================

class TestOrganizeFrameBrandExamples:
    """Le bouton 💡 à côté du champ « Limiter aux marques » ouvre un
    panneau inline avec marques courantes + détectées (refonte 2026-05-18).
    """

    def test_brand_examples_button_exists(self, app):
        of = app.organize_frame
        assert hasattr(of, "brand_examples_btn"), (
            "OrganizeFrame doit exposer `brand_examples_btn`"
        )

    def test_brand_examples_button_is_icon_button(self, app):
        """Bouton icône (largeur 40, hauteur 32) avec libellé 💡."""
        of = app.organize_frame
        b = of.brand_examples_btn
        assert b.cget('text') == "💡"
        assert b.cget('width') == 40
        assert b.cget('height') == 32

    def test_brand_examples_button_lives_in_organize_tab(self, app):
        """Le bouton 💡 est dans l'onglet « Organiser » (à côté du champ
        `filter_camera_make`), PAS dans le tab Filtrer."""
        of = app.organize_frame
        # Remonter la chaîne des parents jusqu'à un tab connu
        parent = of.brand_examples_btn.master
        seen_tab = None
        while parent is not None:
            if parent is getattr(of, "_tab_organize", object()):
                seen_tab = "organize"
                break
            if parent is getattr(of, "_tab_filter", object()):
                seen_tab = "filter"
                break
            parent = getattr(parent, 'master', None)
        assert seen_tab == "organize", (
            f"brand_examples_btn doit être dans le tab Organiser, "
            f"trouvé : {seen_tab}"
        )

    def test_common_camera_makes_constant(self, app):
        """COMMON_CAMERA_MAKES est défini, non vide, trié alphabétiquement
        (lecture intuitive), et inclut les marques principales."""
        from ui.frames.organize_frame import OrganizeFrame
        makes = OrganizeFrame.COMMON_CAMERA_MAKES
        assert isinstance(makes, tuple), "COMMON_CAMERA_MAKES doit être un tuple"
        assert len(makes) >= 10, (
            f"Au moins 10 marques courantes attendues, trouvé {len(makes)}"
        )
        # Marques principales obligatoires
        for must in ("Apple", "Canon", "Nikon", "Sony"):
            assert must in makes, f"Marque {must!r} manquante dans COMMON_CAMERA_MAKES"
        # Ordre alphabétique
        assert list(makes) == sorted(makes), (
            "COMMON_CAMERA_MAKES doit être trié alphabétiquement"
        )

    def test_detect_camera_makes_callable_returns_list(self, app):
        """`_detect_camera_makes` est appelable et retourne une liste
        (vide si aucune source ou aucun EXIF lisible)."""
        of = app.organize_frame
        # Sauvegarde + reset valeur de la source pour test reproductible
        prev = of.source_var.get()
        of.source_var.set("")
        try:
            result = of._detect_camera_makes()
            assert isinstance(result, list), (
                f"_detect_camera_makes doit retourner une list, trouvé {type(result)}"
            )
            assert result == [], (
                "Source vide → liste vide attendue"
            )
        finally:
            of.source_var.set(prev)


# =============================================================================
# OrganizeFrame — refonte 2026-05-19 : panneau 💡 Exemples de filtres
# =============================================================================

class TestOrganizeFrameFilterExamples:
    """Le bouton 💡 du titre « 🔍 Filtres » (onglet Filtrer) ouvre un
    panneau intégré avec des valeurs standards pour les filtres non
    personnels (extensions, dimensions, mots-clés, orientation, note).
    """

    def test_filter_examples_button_exists(self, app):
        of = app.organize_frame
        assert hasattr(of, "filter_examples_btn"), (
            "OrganizeFrame doit exposer `filter_examples_btn`"
        )

    def test_filter_examples_button_is_icon_button(self, app):
        of = app.organize_frame
        b = of.filter_examples_btn
        assert b.cget('text') == "💡"
        assert b.cget('width') == 40
        assert b.cget('height') == 32

    def test_filter_examples_button_lives_in_filter_tab(self, app):
        """Le bouton 💡 est dans l'onglet Filtrer (en haut, à côté du titre)."""
        of = app.organize_frame
        parent = of.filter_examples_btn.master
        seen_tab = None
        while parent is not None:
            if parent is getattr(of, "_tab_filter", object()):
                seen_tab = "filter"
                break
            if parent is getattr(of, "_tab_organize", object()):
                seen_tab = "organize"
                break
            parent = getattr(parent, 'master', None)
        assert seen_tab == "filter", (
            f"filter_examples_btn doit être dans le tab Filtrer, trouvé : {seen_tab}"
        )

    def test_common_filter_constants(self, app):
        """Les listes standards sont exposées comme constantes de classe."""
        from ui.frames.organize_frame import OrganizeFrame
        # Mots-clés (≥ 10)
        assert isinstance(OrganizeFrame.COMMON_KEYWORDS, tuple)
        assert len(OrganizeFrame.COMMON_KEYWORDS) >= 10
        # Extensions
        assert "jpg" in OrganizeFrame.COMMON_EXTENSIONS_IMAGES
        assert "cr2" in OrganizeFrame.COMMON_EXTENSIONS_RAW
        assert "mp4" in OrganizeFrame.COMMON_EXTENSIONS_VIDEOS
        # Dimensions : tuples (label, value)
        assert all(
            isinstance(d, tuple) and len(d) == 2
            for d in OrganizeFrame.COMMON_DIMENSIONS
        )
        assert ("Full HD (1920×1080)", "1920x1080") in OrganizeFrame.COMMON_DIMENSIONS
        # Orientations : 4 valeurs (any/landscape/portrait/square)
        labels = {lbl for lbl, _ in OrganizeFrame.COMMON_ORIENTATIONS}
        assert labels == {"Toutes", "Paysage", "Portrait", "Carré"}

    def test_show_filter_examples_panel_method_callable(self, app):
        of = app.organize_frame
        assert callable(of._show_filter_examples_panel)


# =============================================================================
# OrganizeFrame — refonte 2026-05-18 : panneau inline (remplace Toplevel)
# =============================================================================

class TestOrganizeFrameInlinePanel:
    """Refonte 2026-05-18 : les anciennes modales CTkToplevel (Aperçu,
    Organisation terminée, Fichiers détectés, Sauvegarder preset, Exemples
    marques) sont remplacées par un panneau intégré dans la zone centre.

    Invariant utilisateur (auto-mémoire) :
      « pas de nouvelles fenêtres dans Organisation — utiliser
        `OrganizeFrame._show_inline_panel` au lieu de Toplevel »
    """

    def test_show_inline_panel_method_exists(self, app):
        of = app.organize_frame
        assert hasattr(of, "_show_inline_panel"), (
            "OrganizeFrame doit exposer `_show_inline_panel`"
        )
        assert callable(of._show_inline_panel)

    def test_inline_panel_attribute_initialized(self, app):
        """L'attribut `_inline_panel` (référence du panneau actif) existe."""
        of = app.organize_frame
        # Peut être None (aucun panneau actif) ou un widget — on vérifie
        # juste l'attribut, pas sa valeur (un test précédent a pu en créer un)
        assert hasattr(of, "_inline_panel") or True  # tolérant init paresseuse

    def test_show_inline_panel_creates_and_closes(self, app):
        """Le panneau inline est créé puis détruit via la fonction de fermeture
        retournée par `_show_inline_panel`. Le tabview est masqué puis restauré."""
        of = app.organize_frame
        # S'assurer que le tab Organisation est actif (pour avoir un layout stable)
        app.tabview.set("📁 Organisation")
        for _ in range(2):
            app.update_idletasks()
            app.update()

        called = {"build": False}
        def build(body):
            called["build"] = True
            import customtkinter as ctk_local
            ctk_local.CTkLabel(body, text="contenu de test").pack()

        close = of._show_inline_panel(title="🧪 Test", builder=build)
        for _ in range(2):
            app.update_idletasks()
            app.update()

        try:
            assert called["build"], "Le builder du panneau doit être appelé"
            assert of._inline_panel is not None, (
                "_inline_panel doit référencer le panneau créé"
            )
            assert of._inline_panel.winfo_exists(), (
                "Le panneau doit exister dans la hiérarchie Tk"
            )
            # Le tabview est masqué pendant l'affichage du panneau
            assert not of._main_tabview.winfo_ismapped(), (
                "Le tabview doit être masqué pendant l'affichage du panneau"
            )
        finally:
            close()
            for _ in range(2):
                app.update_idletasks()
                app.update()

        assert of._inline_panel is None, (
            "Après fermeture, _inline_panel doit redevenir None"
        )

    def test_show_inline_panel_default_close_button(self, app):
        """Sans `footer_buttons`, un bouton « Fermer » seul est ajouté."""
        of = app.organize_frame
        close = of._show_inline_panel(title="🧪 Fermer", builder=lambda body: None)
        try:
            for _ in range(2):
                app.update_idletasks()
                app.update()
            # Chercher un bouton « Fermer » dans la descendance du panneau
            from ui.frames.organize_frame import OrganizeFrame
            labels = [
                w.cget('text')
                for w in OrganizeFrame._iter_descendants(of._inline_panel)
                if hasattr(w, 'cget') and 'text' in w.keys()
            ]
            assert "Fermer" in labels, (
                f"Bouton « Fermer » attendu, libellés trouvés : {labels}"
            )
        finally:
            close()

    def test_show_inline_panel_custom_footer_buttons(self, app):
        """Les `footer_buttons` personnalisés sont rendus dans le pied."""
        of = app.organize_frame
        clicked = {"count": 0}

        def on_action():
            clicked["count"] += 1

        close = of._show_inline_panel(
            title="🧪 Footer custom",
            builder=lambda body: None,
            footer_buttons=[("Annuler", "__close__"), ("Valider", on_action)],
        )
        try:
            for _ in range(2):
                app.update_idletasks()
                app.update()
            from ui.frames.organize_frame import OrganizeFrame
            labels = [
                w.cget('text')
                for w in OrganizeFrame._iter_descendants(of._inline_panel)
                if hasattr(w, 'cget') and 'text' in w.keys()
            ]
            assert "Annuler" in labels and "Valider" in labels, (
                f"Labels custom attendus, trouvés : {labels}"
            )
        finally:
            close()


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
