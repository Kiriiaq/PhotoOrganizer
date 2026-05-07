#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Audit visuel de l'IHM PhotoOrganizer.

Démarre l'application en mode headless mais avec layout calculé, puis
imprime un snapshot textuel de la géométrie de tous les widgets clés
de chaque panneau. Sert de "screenshot ASCII" pour valider la refonte
v3 sans dépendre d'un outil de capture d'écran.

Usage :
    python tools/visual_audit.py
    python tools/visual_audit.py --geometry 1200x800
    python tools/visual_audit.py --tab Doublons   # ne dump qu'un panneau

Sortie : arbre indenté avec géométrie (x, y, w, h) et état mappé.
Codes :
    [✓]  widget mappé (visible)
    [×]  widget créé mais pas mappé (caché par grid_forget/pack_forget)
    [+N] N widgets enfants supplémentaires non listés (limite à 1 niveau)
"""

import argparse
import os
import sys

# Force UTF-8 sur stdout pour les caractères box-drawing et emojis
# (Git Bash sous Windows défaut cp1252).
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass

# Path setup pour permettre l'import en standalone
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import customtkinter as ctk  # noqa: E402,F401

# Largeur max d'une ligne d'audit (label + géométrie)
LINE_W = 100

# Widgets dont on veut ABSOLUMENT vérifier la position et la couleur
KEY_WIDGETS = {
    'organize': [
        ('_top_zone',          'zone top sticky (Source/Dest/compteur)'),
        ('_scroll',            'zone centre scrollable'),
        ('_bottom_zone',       'zone bottom sticky (boutons)'),
        ('source_entry',       'entry Source(s)'),
        ('dest_entry',         'entry Destination'),
        ('file_count_label',   'compteur fichiers'),
        ('progress_bar',       'barre de progression'),
        ('progress_label',     'label progression'),
        ('analyze_button',     'bouton Analyser'),
        ('preview_button',     'bouton Aperçu'),
        ('cancel_button',      'bouton Annuler (rouge, gauche-spacer)'),
        ('organize_button',    'bouton Organiser (vert 40px, droite)'),
        ('multilayer_switch',  'switch multicouche'),
        ('_adv_toggle_btn',    'toggle Avancé ▶/▼'),
        ('_adv_content',       'contenu Avancé (replié par défaut)'),
    ],
    'duplicates': [
        ('search_button',      'bouton Rechercher'),
        ('execute_button',     'bouton Exécuter (primary 40px)'),
        ('cancel_button',      'bouton Annuler (rouge 32px)'),
        ('progress_bar',       'barre de progression'),
        ('main_tabview',       'tabview Resultats/Details'),
        ('results_textbox',    'textbox résultats'),
    ],
    'history': [
        ('stats_label',        'stats compactes inline'),
        ('history_textbox',    'textbox historique (plein écran)'),
        ('rollback_one_button','rollback dernière (orange)'),
        ('rollback_all_button','rollback tout (orange)'),
        ('clear_button',       'effacer (rouge)'),
    ],
    'settings': [
        ('schedule_switch',    'switch Planification'),
    ],
}


def fmt_geom(w):
    """Retourne 'x×y  WIDTHxHEIGHT  [✓/×]' ou 'NOT MAPPED' pour un widget tk."""
    try:
        mapped = bool(w.winfo_ismapped())
    except Exception:
        return "  ERREUR géométrie"
    if not mapped:
        return f"  [×] non mappé (créé mais caché)"
    x, y = w.winfo_x(), w.winfo_y()
    width, height = w.winfo_width(), w.winfo_height()
    return f"  [✓]  pos ({x:>4},{y:>4})  size {width:>4}×{height:<4}"


def fmt_widget_info(w):
    """Infos additionnelles selon le type de widget."""
    cls = type(w).__name__
    info = [cls]
    try:
        text = w.cget('text')
        if text:
            info.append(f"text={text!r:.40}")
    except Exception:
        pass
    try:
        fg = w.cget('fg_color')
        if fg and fg != 'transparent':
            info.append(f"fg={fg}")
    except Exception:
        pass
    try:
        h = w.cget('height')
        if h and isinstance(h, int):
            info.append(f"h={h}")
    except Exception:
        pass
    return "  ".join(info)


def audit_panel(name, frame, key_widgets):
    print()
    print(f"{'═' * LINE_W}")
    print(f"  📐 PANNEAU : {name.upper()}")
    print(f"{'═' * LINE_W}")
    print(f"{'Widget':30} {'Description':45} Géométrie & couleur")
    print(f"{'-' * LINE_W}")

    for attr, description in key_widgets:
        widget = getattr(frame, attr, None)
        if widget is None:
            print(f"  {attr:28} {description:45} ⚠️  ATTRIBUT MANQUANT")
            continue
        geom = fmt_geom(widget)
        info = fmt_widget_info(widget)
        print(f"  {attr:28} {description:45}{geom}")
        print(f"  {'':28} {'':45}    └─ {info}")


def audit_layout_consistency(app):
    """Vérifie quelques invariants critiques de la refonte v3."""
    print()
    print(f"{'═' * LINE_W}")
    print(f"  ✅ INVARIANTS UI v3")
    print(f"{'═' * LINE_W}")

    # Important : forcer le retour sur l'onglet Organisation pour que
    # winfo_ismapped() reflète bien l'état des widgets de OrganizeFrame.
    app.tabview.set("📁 Organisation")
    for _ in range(2):
        app.update_idletasks()
        app.update()

    of = app.organize_frame
    df = app.duplicates_frame
    hf = app.history_frame
    sf = app.settings_frame

    checks = []

    # OrganizeFrame : 3 zones mappées (vérifier sur l'onglet actif)
    checks.append((
        "Organize a 3 zones mappées (top, scroll, bottom)",
        all([of._top_zone.winfo_ismapped(),
             of._scroll.winfo_ismapped(),
             of._bottom_zone.winfo_ismapped()]),
    ))

    # OrganizeFrame : Avancé replié par défaut
    checks.append((
        "Panneau « Avancé » collapsed par défaut",
        of._adv_collapsed is True and not of._adv_content.winfo_ismapped(),
    ))

    # OrganizeFrame : organize_button vert 40px à droite du cancel
    org_x = of.organize_button.winfo_x()
    can_x = of.cancel_button.winfo_x()
    checks.append((
        "Organiser à droite (x=%d) > Annuler (x=%d)" % (org_x, can_x),
        org_x > can_x,
    ))
    checks.append((
        "Organiser height=40 (primary) ; Annuler height=32 (std)",
        of.organize_button.cget('height') == 40
        and of.cancel_button.cget('height') == 32,
    ))
    checks.append((
        "Organiser couleur Material PRIMARY (#2E7D32)",
        of.organize_button.cget('fg_color') == ('#2E7D32', '#1B5E20'),
    ))
    checks.append((
        "Annuler couleur Material DANGER (#C62828)",
        of.cancel_button.cget('fg_color') == ('#C62828', '#8E0000'),
    ))

    # DuplicatesFrame : main_tabview a EXACTEMENT 2 onglets (Resultats/Details)
    tabs = list(df.main_tabview._tab_dict.keys()) if hasattr(df.main_tabview, '_tab_dict') else []
    checks.append((
        "Duplicates tabview = 2 onglets (Resultats, Details) — Options en sidebar",
        tabs == ['Resultats', 'Details'],
    ))
    checks.append((
        "Duplicates Exécuter = primary 40 ; Annuler = danger 32",
        df.execute_button.cget('height') == 40
        and df.cancel_button.cget('height') == 32,
    ))

    # HistoryFrame : pas de warning_label permanent (refonte v3 a supprimé)
    checks.append((
        "History n'a plus de warning_label permanent (compactage v3)",
        not hasattr(hf, 'warning_label'),
    ))
    checks.append((
        "History rollback_one_button = warning orange (#EF6C00)",
        hf.rollback_one_button.cget('fg_color') == ('#EF6C00', '#B53D00'),
    ))

    # SettingsFrame : schedule_switch présent (déplacé d'Organize)
    checks.append((
        "Settings contient schedule_switch (déplacé d'Organize)",
        hasattr(sf, 'schedule_switch'),
    ))

    # app : minsize 800x550 — wm_minsize() peut être scaled selon le DPI
    # (ex: x1.5 sur écran 4K → 1200x825). On vérifie ≥ et non strict ==.
    mw, mh = app.wm_minsize()
    checks.append((
        f"App minsize ≥ 800×550 (effectif {mw}×{mh})",
        mw >= 800 and mh >= 550,
    ))

    # Récap
    print(f"{'Invariant':80} {'État'}")
    print(f"{'-' * LINE_W}")
    failed = 0
    for label, ok in checks:
        sign = "✓" if ok else "✗"
        if not ok:
            failed += 1
        print(f"  [{sign}] {label[:78]}")
    print()
    if failed:
        print(f"  ⚠️  {failed} invariant(s) en échec sur {len(checks)}")
    else:
        print(f"  🎉  {len(checks)} / {len(checks)} invariants OK")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Audit visuel PhotoOrganizer UI")
    parser.add_argument("--geometry", default="1200x800",
                        help="Taille de la fenêtre (défaut 1200x800)")
    parser.add_argument("--tab", choices=['organize', 'duplicates', 'history', 'settings'],
                        help="N'auditer qu'un panneau")
    args = parser.parse_args()

    # Démarrage app + force layout
    from ui.app import PhotoOrganizerApp
    app = PhotoOrganizerApp()
    app.geometry(args.geometry)
    # Forcer un cycle complet de layout (3 update_idletasks pour propager)
    for _ in range(3):
        app.update_idletasks()
        app.update()

    # Activer chaque onglet pour que les widgets enfants soient mappés
    for tab_name in ['📁 Organisation', '🔍 Doublons', '📜 Historique', '⚙️ Paramètres']:
        app.tabview.set(tab_name)
        for _ in range(2):
            app.update_idletasks()
            app.update()

    # Re-revenir sur Organisation (tab par défaut)
    app.tabview.set("📁 Organisation")
    app.update()

    panels = {
        'organize':   ('Organisation', app.organize_frame),
        'duplicates': ('Doublons',    app.duplicates_frame),
        'history':    ('Historique',  app.history_frame),
        'settings':   ('Paramètres',  app.settings_frame),
    }

    if args.tab:
        # Activer le bon onglet
        tab_map = {
            'organize': '📁 Organisation', 'duplicates': '🔍 Doublons',
            'history': '📜 Historique', 'settings': '⚙️ Paramètres',
        }
        app.tabview.set(tab_map[args.tab])
        app.update()
        name, frame = panels[args.tab]
        audit_panel(name, frame, KEY_WIDGETS[args.tab])
    else:
        for key, (name, frame) in panels.items():
            audit_panel(name, frame, KEY_WIDGETS[key])

    ok = audit_layout_consistency(app)
    app.destroy()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
