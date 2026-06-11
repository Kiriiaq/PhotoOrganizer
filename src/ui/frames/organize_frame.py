"""
Frame d'organisation des fichiers.
Interface principale pour organiser les photos et vidéos.
"""

import logging
import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Callable, List, Optional

import customtkinter as ctk

from core.metadata import extract_date, get_camera_info, get_exif_data, get_gps_coordinates
from core.operations import FileManager, OrganizationOptions, SmartOrganizer

# Design system unifié — couleurs, espacements, factories de boutons.
# Importe en absolu (ui.theme) pour rester compatible avec PyInstaller.
from ui.theme import (
    BTN_H_PRIMARY,
    BTN_H_STD,
    HINT_COLOR,
    LABEL_MUTED,
    PAD_L,
    PAD_M,
    PAD_S,
    SEPARATOR_COLOR,
    danger_button,
    font_hint,
    font_label,
    font_section,
    icon_button,
    neutral_button,
    primary_button,
)
from ui.tooltip import attach_tooltip
from ui.tooltips_fr import ORGANIZE as TIPS
from utils import licensing
from utils.config import get_config

logger = logging.getLogger(__name__)

# Drag-and-drop optionnel : la lib n'est pas dans requirements.txt par défaut.
# Si absente, l'app fonctionne normalement, juste sans le glisser-déposer.
try:
    from tkinterdnd2 import DND_FILES  # noqa: F401

    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    logger.debug("tkinterdnd2 absent : drag-and-drop desactive")


def _open_folder(path: str):
    """Ouvre un dossier dans l'explorateur natif (Windows / macOS / Linux)."""
    if not path or not os.path.isdir(path):
        logger.warning(f"_open_folder: chemin introuvable {path}")
        return
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        logger.warning(f"Impossible d'ouvrir {path}: {exc}")


def _windows_toast(title: str, message: str):
    """Notification non-modale fin d'organisation.

    Tente une vraie toast Windows via plyer, sinon retombe sur un Toplevel
    auto-dismiss après 4 s (cross-platform). Le but est de prévenir
    l'utilisateur sans bloquer l'IHM.
    """
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="PhotoOrganizer",
            timeout=5,
        )
        return
    except Exception as exc:
        logger.debug(f"plyer notification indisponible : {exc}")

    # Fallback : petit Toplevel discret. On le crée caché puis on le détruit
    # automatiquement. (Ne pas dépendre d'une fenêtre parente pour rester
    # appelable depuis n'importe où.)
    try:
        win = ctk.CTkToplevel()
        win.title(title)
        win.geometry("360x90+1400+50")
        win.attributes("-topmost", True)
        ctk.CTkLabel(
            win,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=10, pady=(8, 2))
        ctk.CTkLabel(win, text=message, wraplength=340).pack(padx=10, pady=(0, 8))
        win.after(4000, win.destroy)
    except Exception as exc:
        logger.debug(f"Fallback toast Toplevel echoue : {exc}")


def _parse_size_input(text: str) -> int:
    """Parse une chaîne 'taille' (ex: '1.5 MB', '500KB', '2GB') en octets.

    Retourne 0 si vide ou non parsable.
    """
    if not text:
        return 0
    text = text.strip().upper().replace(" ", "")
    units = {"B": 1, "KB": 1024, "K": 1024, "MB": 1024**2, "M": 1024**2, "GB": 1024**3, "G": 1024**3}
    for unit, mult in units.items():
        if text.endswith(unit):
            try:
                return int(float(text[: -len(unit)]) * mult)
            except ValueError:
                return 0
    try:
        return int(text)
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Constantes de style (visibilité IHM)
# ---------------------------------------------------------------------------
# CTk a des défauts conservateurs (font 12, border 3px peu contrasté). On
# centralise ici les paramètres pour assurer la lisibilité dans les deux
# thèmes (clair/sombre) et faciliter une éventuelle harmonisation globale.
CHECKBOX_FONT_SIZE = 13
LABEL_FONT_SIZE = 13
SECTION_TITLE_SIZE = 14
HEADER_TITLE_SIZE = 16

# Couleurs explicites pour les checkboxes/radios — la couleur active rend
# l'état coché beaucoup plus visible qu'en gris CTk par défaut.
CHECK_FG = ("#1f6aa5", "#1f6aa5")  # bleu cohérent avec color_theme=blue
CHECK_HOVER = ("#144870", "#144870")
CHECK_BORDER = ("gray40", "gray60")  # bordure visible dark + light
CHECK_BORDER_WIDTH = 2


def _make_checkbox(parent, **kwargs):
    """Factory CTkCheckBox avec les valeurs de style par défaut du projet.

    Centralise la lisibilité : taille de police, bordure visible, couleurs
    actives. ``kwargs`` peut surcharger n'importe quel paramètre.
    """
    defaults = {
        "font": ctk.CTkFont(size=CHECKBOX_FONT_SIZE),
        "fg_color": CHECK_FG,
        "hover_color": CHECK_HOVER,
        "border_color": CHECK_BORDER,
        "border_width": CHECK_BORDER_WIDTH,
    }
    defaults.update(kwargs)
    return ctk.CTkCheckBox(parent, **defaults)


def _make_radio(parent, **kwargs):
    """Factory CTkRadioButton (pendant de _make_checkbox)."""
    defaults = {
        "font": ctk.CTkFont(size=CHECKBOX_FONT_SIZE),
        "fg_color": CHECK_FG,
        "hover_color": CHECK_HOVER,
        "border_color": CHECK_BORDER,
        "border_width_unchecked": CHECK_BORDER_WIDTH,
    }
    defaults.update(kwargs)
    return ctk.CTkRadioButton(parent, **defaults)


class OrganizeFrame(ctk.CTkFrame):
    """Frame d'organisation des fichiers."""

    def __init__(
        self,
        parent,
        source_var: ctk.StringVar,
        dest_var: ctk.StringVar,
        file_manager: Optional[FileManager] = None,
        status_callback: Optional[Callable] = None,
    ):
        """
        Initialise le frame d'organisation.

        Args:
            parent: Widget parent
            source_var: Variable pour le dossier source
            dest_var: Variable pour le dossier destination
            file_manager: Gestionnaire de fichiers partagé entre frames.
                Crée une instance dédiée si None.
            status_callback: Callback pour la barre de statut
        """
        super().__init__(parent, fg_color="transparent")

        self.source_var = source_var
        self.dest_var = dest_var
        self.file_manager = file_manager or FileManager()
        self.status_callback = status_callback or (lambda m, p=None: None)

        # Variables d'état
        self._cancel_requested = False
        self._operation_running = False
        # D-06 (audit 2026-05-14) : sentinel pour éviter
        # `RuntimeError: main thread is not in main loop` quand un worker
        # essaie de marshaller un callback `after(0, ...)` alors que le frame
        # vient d'être détruit (fermeture app, swap d'onglet, hot-reload…).
        self._destroyed = False
        # Référence à l'organizer en cours (pour propager cancel())
        self._current_organizer: Optional[SmartOrganizer] = None

        # Ordre des critères en mode multicouche (modifiable via l'UI quand
        # `multilayer` est ON). Le SmartOrganizer applique les critères dans
        # cet ordre — ex. ['date', 'camera'] crée
        #   YYYY / MM / YYYY_MM_DD / Canon EOS R5 / photo.jpg
        # tandis que ['camera', 'date', 'location'] crée
        #   Canon EOS R5 / YYYY / MM / YYYY_MM_DD / Paris / photo.jpg
        self._criteria_order: List[str] = ["date", "camera", "location"]
        self._criteria_rows: dict = {}  # key -> (frame, label, up_btn, down_btn)

        # Options d'organisation
        self.organize_by_date = ctk.BooleanVar(value=True)
        self.organize_by_camera = ctk.BooleanVar(value=False)
        self.organize_by_location = ctk.BooleanVar(value=False)
        self.use_geocoding = ctk.BooleanVar(value=True)
        self.max_distance = ctk.DoubleVar(value=1.0)
        # Libellé numérique affiché à côté du slider distance max
        self.max_distance_label_var = ctk.StringVar(value="1.0 km")
        self.multilayer = ctk.BooleanVar(value=False)
        self.copy_not_move = ctk.BooleanVar(value=True)
        self.date_format = ctk.StringVar(value="year/month/day")
        self.recursive = ctk.BooleanVar(value=True)
        self.include_images = ctk.BooleanVar(value=True)
        self.include_raw = ctk.BooleanVar(value=True)
        self.include_videos = ctk.BooleanVar(value=False)

        # ---- Filtres avancés (R1) ----
        self.filter_date_min = ctk.StringVar(value="")  # YYYY-MM-DD
        self.filter_date_max = ctk.StringVar(value="")
        self.filter_size_min = ctk.StringVar(value="")  # ex: "100KB"
        self.filter_size_max = ctk.StringVar(value="")
        self.filter_rating_min = ctk.IntVar(value=0)  # 0..5
        self.filter_keywords = ctk.StringVar(value="")  # CSV

        # Nouveaux filtres (refactor 2026-05-15) — persistés dans AppConfig
        _cfg_app = get_config().config
        self.filter_extensions = ctk.StringVar(value=getattr(_cfg_app, "filter_extensions", ""))
        self.filter_dim_min = ctk.StringVar(value=getattr(_cfg_app, "filter_dim_min", ""))
        self.filter_dim_max = ctk.StringVar(value=getattr(_cfg_app, "filter_dim_max", ""))
        self.filter_camera_make = ctk.StringVar(value=getattr(_cfg_app, "filter_camera_make", ""))
        self.filter_gps_required = ctk.StringVar(value=getattr(_cfg_app, "filter_gps_required", "any"))
        self.filter_orientation = ctk.StringVar(value=getattr(_cfg_app, "filter_orientation", "any"))

        # ---- Toggles avancés ----
        self.skip_if_identical = ctk.BooleanVar(value=False)  # R2
        self.keep_raw_jpeg_pairs = ctk.BooleanVar(value=False)  # R3
        self.cleanup_empty_source = ctk.BooleanVar(value=False)  # R5
        self.validate_disk_space = ctk.BooleanVar(value=True)  # R6
        # Refactor 2026-05-15 : Notifications + Index déplacés en Paramètres.
        # Les BooleanVars restent sur OrganizeFrame (pour _get_options) mais
        # leur état est persisté dans AppConfig (sync bidirectionnelle).
        self.export_index_csv = ctk.BooleanVar(value=getattr(_cfg_app, "export_index_csv", False))
        self.export_index_json = ctk.BooleanVar(value=getattr(_cfg_app, "export_index_json", False))
        self.notify_on_finish = ctk.BooleanVar(value=getattr(_cfg_app, "notify_on_finish", True))

        # Sync bidirectionnelle vers AppConfig pour toutes les vars persistées.
        # Utilise un helper de méthode pour éviter les closures multiples
        # (cf. fix bug définition après usage du refactor 2026-05-15).
        for fname in (
            "notify_on_finish",
            "export_index_csv",
            "export_index_json",
            "filter_extensions",
            "filter_dim_min",
            "filter_dim_max",
            "filter_camera_make",
            "filter_gps_required",
            "filter_orientation",
        ):
            getattr(self, fname).trace_add(
                "write",
                self._make_config_persist_cb(fname),
            )

        # ---- Bursts S1 + Incremental S5 ----
        self.detect_bursts = ctk.BooleanVar(value=False)
        # "manual" | "auto_mean" | "auto_stddev" — défaut manuel (legacy compat)
        self.burst_mode = ctk.StringVar(value="manual")
        self.burst_threshold = ctk.IntVar(value=3)  # secondes
        self.burst_min_count = ctk.IntVar(value=3)
        # Bornes du clamp en mode auto (audit 2026-05-15 — option avancée).
        # Defaults [1 s ; 600 s] = comportement historique.
        self.burst_auto_min = ctk.IntVar(value=1)
        self.burst_auto_max = ctk.IntVar(value=600)
        self.incremental_mode = ctk.BooleanVar(value=False)

        # ---- Planification E5 ----
        self.schedule_enabled = ctk.BooleanVar(value=False)
        self.schedule_time = ctk.StringVar(value="23:00")
        self.schedule_status_var = ctk.StringVar(value="Désactivée")

        # ---- Renommage Q4 ----
        self.rename_template = ctk.StringVar(value="")  # vide = pas de rename

        # ---- Presets Q3 ----
        self.preset_name = ctk.StringVar(value="(aucun)")

        self._create_ui()

        # Attacher les tooltips à tous les widgets clés (centralisé dans
        # tooltips_fr.ORGANIZE pour faciliter la maintenance des libellés).
        self._attach_tooltips()

        # Brancher le compteur de fichiers source — déclenche un scan léger
        # à chaque changement du dossier source ou des filtres.
        self.source_var.trace_add("write", lambda *_: self._refresh_file_count())
        for v in (self.recursive, self.include_images, self.include_raw, self.include_videos):
            v.trace_add("write", lambda *_: self._refresh_file_count())
        self._refresh_file_count()

        # Bandeau warning trial — synchronisation initiale après création
        # de tous les widgets (notamment self.trial_warning_banner et
        # self.organize_button qui doivent exister).
        try:
            self._refresh_trial_warning_banner()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Bandeau warning trial init failed (ignoré) : {exc}")

        # ---- Initialiser le scheduler E5 ----
        # Lazy import pour ne pas tirer la dépendance si la feature n'est
        # jamais activée (et garder le démarrage rapide).
        from core.scheduler import JobScheduler

        self._scheduler = JobScheduler(callback=self._scheduled_run_callback)

        # Restaurer l'état planifié depuis AppConfig
        cfg = get_config().config
        if getattr(cfg, "schedule_enabled", False):
            self.schedule_enabled.set(True)
            self.schedule_time.set(getattr(cfg, "schedule_time", "23:00"))
            # Auto-démarrer
            self._scheduler.configure(True, self.schedule_time.get())
        # Mettre à jour le label statut
        self._refresh_schedule_status()
        # Persister à chaque modification de l'heure
        self.schedule_time.trace_add("write", lambda *_: self._on_schedule_time_change())

    def _create_ui(self):
        """Crée l'interface utilisateur (refonte v2.3 — Variante B : tabview interne).

        Layout :
          ┌──────────────────────────────────────────────────────┐
          │ ZONE TOP (compact, sticky)  Source → Dest + Compteur │  ~90 px
          ├──────────────────────────────────────┬───────────────┤
          │ TABVIEW INTERNE — 4 onglets          │ RIGHT RAIL    │
          │   🔍 Filtrer    🗂️ Organiser          │  Preset       │  ~210 px
          │   🛠️ Traiter    🏷️ Renommer           │  📊 Analyser   │  weight=1
          │                                       │  👁 Aperçu     │
          │                                       │  ❌ Annuler    │
          │                                       │  🚀 Organiser  │
          │                                       │  ─────         │
          │                                       │  Cible: …      │
          ├──────────────────────────────────────┴───────────────┤
          │ ZONE BOTTOM (slim, sticky)    Progress bar + label    │  ~40 px
          └──────────────────────────────────────────────────────┘

        Bénéfices vs v2.2 :
          - Plus de scroll vertical dans le cas nominal (tabview = onglets)
          - Actions toujours accessibles dans le right rail (sticky)
          - Densité par onglet beaucoup plus élevée
          - Zone bottom réduite à la progress bar (libère ~120 px)
        """
        # Layout root : 3 lignes × 2 colonnes (top et bottom utilisent
        # columnspan=2, le middle a col 0 expansif et col 1 fixe à 210 px).
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0, minsize=210)
        self.rowconfigure(0, weight=0)  # top compact
        self.rowconfigure(1, weight=1)  # middle expansif
        self.rowconfigure(2, weight=0)  # bottom slim

        # ZONE TOP : Source/Destination/Compteur (compact, columnspan=2)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=PAD_M, pady=(PAD_M, 0))
        top.columnconfigure(0, weight=1)
        self._top_zone = top

        # ZONE CENTRE COL 0 : scroll + tabview interne (4 onglets)
        # Le tabview est imbriqué dans _scroll (un CTkScrollableFrame) pour
        # garantir un fallback scroll au cas où un onglet déborde verticalement
        # — usage nominal : aucun scroll nécessaire.
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=(PAD_M, PAD_S), pady=PAD_S)
        self._scroll.columnconfigure(0, weight=1)

        self._main_tabview = ctk.CTkTabview(self._scroll, anchor="nw")
        self._main_tabview.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        # Espacement icône-titre (retour testeur 2026-05-17 itération 2) :
        # « les icônes sont mal positionnées ». Utilisation de NBSP + espace
        # standard qui rend mieux sur CTkTabview que les doubles espaces
        # (qui ne sont pas affichés correctement par Tk).
        TAB_FILTER = "🔍  Filtrer"
        TAB_ORGANIZE = "🗂  Organiser"
        TAB_PROCESS = "🛠  Traiter"
        TAB_RENAME = "🏷  Renommer"
        for tab_name in (TAB_FILTER, TAB_ORGANIZE, TAB_PROCESS, TAB_RENAME):
            self._main_tabview.add(tab_name)
        self._main_tabview.set(TAB_ORGANIZE)  # onglet par défaut

        # Mapping : nom logique → frame de l'onglet (parent pour les sections)
        self._tab_filter = self._main_tabview.tab(TAB_FILTER)
        self._tab_organize = self._main_tabview.tab(TAB_ORGANIZE)
        self._tab_process = self._main_tabview.tab(TAB_PROCESS)
        self._tab_rename = self._main_tabview.tab(TAB_RENAME)

        # ZONE CENTRE COL 1 : right rail (sticky vertical 210 px)
        rail = ctk.CTkFrame(self)
        rail.grid(row=1, column=1, sticky="nsew", padx=(PAD_S, PAD_M), pady=PAD_S)
        rail.columnconfigure(0, weight=1)
        self._right_rail = rail

        # ZONE BOTTOM (slim, columnspan=2)
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
        bottom.columnconfigure(0, weight=1)
        self._bottom_zone = bottom

        # Création des sections dans leur zone respective.
        # Les _create_*_section grident désormais dans les onglets correspondants
        # (cf. _tab_filter / _tab_organize / _tab_process / _tab_rename).
        self._create_folders_section()  # zone top
        self._create_options_section()  # Organiser (gauche) + Traiter (action/types)
        self._create_advanced_section()  # Filtrer (filtres) + Traiter (comportements)
        self._create_rename_section()  # Renommer
        self._create_right_rail()  # right rail : presets + actions + Cible
        self._create_actions_section()  # zone bottom : progress bar slim

        # Layout responsive v2.2 : désormais piloté par le tabview lui-même
        # (chaque onglet gère son propre flux 1 col / 2 col selon densité).
        # Les hooks `_on_scroll_configure` / `_update_responsive_layout` sont
        # conservés en tant que no-op pour préserver l'API existante.
        self._layout_mode = "tabview"
        self._responsive_debounce_id = None

    # ------------------------------------------------------------------
    # Layout responsive — refonte v2.3 (Variante B) : no-op
    # ------------------------------------------------------------------
    # Conservés pour préserver l'API publique (référencés dans
    # `audit/RAPPORT_FINAL.md` et dans visual_audit). Le tabview interne
    # gère désormais lui-même son flux ; pas besoin de bascule manuelle.
    RESPONSIVE_BREAKPOINT = 1000  # px (gardé pour rétrocompat)

    def _on_scroll_configure(self, event):
        """No-op (refonte v2.3) : le tabview gère son propre layout."""
        return

    def _update_responsive_layout(self):
        """No-op (refonte v2.3) : remplacé par le tabview interne."""
        return

    def _create_folders_section(self):
        """Section de sélection des dossiers en zone top fixe (toujours visible).

        Compactée : titre + 1 ligne source + 1 ligne destination + 1 ligne
        compteur fichiers. Pas de scroll possible sur ce bloc → l'utilisateur
        voit immédiatement combien de fichiers sont prêts à être organisés.
        """
        parent = self._top_zone
        folders = ctk.CTkFrame(parent)
        folders.grid(row=0, column=0, sticky="ew")
        # Layout 3 colonnes :
        #   col 0 = label (largeur fixe 90)
        #   col 1 = contenu (entry, dest_row, file_count) — weight=1
        #   col 2 = bouton à droite (📂, 📋) — colonne unique pour TOUS
        # Cette uniformité (retour testeur 2026-05-17 it. 3 « aligne les
        # boutons dossier et le reste au même niveau que le bouton pour
        # afficher la liste des fichiers détectés ») assure que tous les
        # boutons icône sont alignés verticalement à la même abscisse.
        folders.columnconfigure(1, weight=1)

        # Titre (refonte v5 — retours JSON 2026-05-13)
        # Le hint « Plusieurs sources : ; » et la mention drag-and-drop ont
        # été retirés (cf. W06 retour testeur : « supprime la fonctionnalité
        # drag and drop inutile et la possibilité d'utiliser des séparateurs »).
        title_row = ctk.CTkFrame(folders, fg_color="transparent")
        title_row.grid(row=0, column=0, columnspan=3, sticky="ew", padx=PAD_M, pady=(PAD_M, PAD_S))
        ctk.CTkLabel(
            title_row,
            text="📁 Sélection des dossiers",
            font=font_section(),
        ).pack(side="left")

        # Ligne Source — un seul dossier, plus de séparateur ;
        ctk.CTkLabel(
            folders,
            text="Source :",
            font=font_label(),
            width=90,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=(PAD_M, PAD_S), pady=PAD_S)
        self.source_entry = ctk.CTkEntry(
            folders,
            textvariable=self.source_var,
            placeholder_text="Sélectionnez le dossier source à organiser…",
            height=BTN_H_STD,
        )
        self.source_entry.grid(row=1, column=1, sticky="ew", padx=PAD_S, pady=PAD_S)
        self.browse_source_btn = icon_button(
            folders,
            text="📂",
            command=self._browse_source,
        )
        self.browse_source_btn.grid(row=1, column=2, padx=(PAD_S, PAD_M), pady=PAD_S)
        # Le bouton « + Source » (multi-source) a été retiré — W08 retour
        # testeur : « supprime le bouton car inutile ».

        # Ligne Destination
        ctk.CTkLabel(
            folders,
            text="Destination :",
            font=font_label(),
            width=90,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=(PAD_M, PAD_S), pady=PAD_S)

        # Sous-frame pour entry + bouton ↗ "Ouvrir dest" qui restent
        # accessibles. Le bouton 📂 Parcourir occupe la colonne 2 (cf. layout).
        dest_row = ctk.CTkFrame(folders, fg_color="transparent")
        dest_row.grid(row=2, column=1, sticky="ew", padx=PAD_S, pady=PAD_S)
        dest_row.columnconfigure(0, weight=1)

        self.dest_entry = ctk.CTkEntry(
            dest_row,
            textvariable=self.dest_var,
            placeholder_text="Sélectionnez le dossier destination…",
            height=BTN_H_STD,
        )
        self.dest_entry.grid(row=0, column=0, sticky="ew", padx=(0, PAD_S))
        self.open_dest_btn = icon_button(
            dest_row,
            text="↗",
            command=lambda: _open_folder(self.dest_var.get()),
        )
        self.open_dest_btn.grid(row=0, column=1)

        self.browse_dest_btn = icon_button(
            folders,
            text="📂",
            command=self._browse_dest,
        )
        self.browse_dest_btn.grid(row=2, column=2, padx=(PAD_S, PAD_M), pady=PAD_S)

        # Ligne Compteur fichiers (toujours visible — fix T-030..033)
        # Refonte 2026-05-17 it. 3 : le compteur occupe col 0+1 (info avant
        # le bouton) et le bouton 📋 est placé en col 2 — aligné avec les
        # boutons 📂 ci-dessus.
        self.file_count_var = ctk.StringVar(value="Aucun dossier source sélectionné.")
        self.file_count_label = ctk.CTkLabel(
            folders,
            textvariable=self.file_count_var,
            font=font_label(),
            anchor="w",
            text_color=LABEL_MUTED,
        )
        self.file_count_label.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=PAD_M,
            pady=(0, PAD_M),
        )

        # Lot B audit 2026-05-14 (T-030..T-033) : bouton « 📋 » qui ouvre une
        # modale listant les fichiers détectés. Aligné en col 2 (refonte
        # 2026-05-17 it. 3) pour cohérence avec les 📂 ci-dessus.
        self.show_files_btn = icon_button(
            folders,
            text="📋",
            command=self._show_files_list,
        )
        self.show_files_btn.grid(
            row=3,
            column=2,
            padx=(PAD_S, PAD_M),
            pady=(0, PAD_M),
        )

        # Drag-and-drop retiré (W06) — la méthode _setup_drag_drop reste
        # définie mais n'est plus appelée pour ne pas créer de bindings.

    def _create_options_section(self):
        """Crée la section des critères + options (refonte v2.3 Variante B).

        Désormais répartie sur 2 onglets :
        - Critères (gauche) → onglet 🗂️ Organiser
        - Action / Types (droite) → onglet 🛠️ Traiter

        Les attributs ``_options_left_frame`` et ``_options_right_frame``
        sont conservés (rétrocompat) mais pointent vers les frames des
        onglets et non vers ``_scroll``.
        """
        # Frame gauche - Critères d'organisation → onglet Organiser
        self._options_left_frame = left_frame = ctk.CTkFrame(self._tab_organize)
        left_frame.pack(fill="x", padx=0, pady=PAD_S)

        ctk.CTkLabel(
            left_frame, text="🗂️ Critères d'organisation", font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Organiser par date
        _make_checkbox(left_frame, text="Par date de prise de vue", variable=self.organize_by_date).pack(
            anchor="w", padx=20, pady=3
        )

        # Format de date
        date_format_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        date_format_frame.pack(fill="x", padx=40, pady=2)

        ctk.CTkLabel(
            date_format_frame,
            text="Format :",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE),
        ).pack(side="left")
        self.date_format_menu = ctk.CTkOptionMenu(
            date_format_frame,
            variable=self.date_format,
            values=["year/month/day", "year/month", "year", "year_month_day", "year_month"],
        )
        self.date_format_menu.pack(side="left", padx=5)

        # Organiser par appareil + sous-option fusionnée Caméra (v2.2 étape 3)
        # Refonte 2026-05-15 : la ligne « Caméra : [CSV] » du panneau Filtres
        # a été déplacée ici comme sous-option de « Par appareil photo ».
        # Sémantique : si l'utilisateur veut limiter aux caméras X,Y, on
        # filtre AVANT d'organiser par appareil.
        _make_checkbox(left_frame, text="Par appareil photo", variable=self.organize_by_camera).pack(
            anchor="w", padx=20, pady=3
        )
        self._camera_options_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        cam_row = ctk.CTkFrame(self._camera_options_frame, fg_color="transparent")
        cam_row.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(
            cam_row,
            text="Limiter aux marques :",
            font=font_label(),
        ).pack(side="left")
        ctk.CTkEntry(
            cam_row,
            textvariable=self.filter_camera_make,
            placeholder_text="CSV — ex. Sony,Canon  (vide = toutes)",
            height=BTN_H_STD,
        ).pack(side="left", padx=PAD_S, fill="x", expand=True)
        # Bouton 💡 Exemples — panneau inline avec marques courantes + détectées
        # (refonte 2026-05-18 retour testeur : aide au remplissage du champ)
        self.brand_examples_btn = icon_button(
            cam_row,
            text="💡",
            command=self._show_brand_examples_panel,
        )
        self.brand_examples_btn.pack(side="left", padx=(0, PAD_S))
        # Affichage conditionnel selon organize_by_camera
        self.organize_by_camera.trace_add("write", lambda *_: self._refresh_camera_options_visibility())
        self._refresh_camera_options_visibility()

        # Organiser par localisation GPS
        # On garde une référence à la case pour positionner les sous-options
        # GPS juste en dessous via pack(after=…) — cf. W17/W18 retour testeur.
        self._gps_checkbox = _make_checkbox(left_frame, text="Par localisation GPS", variable=self.organize_by_location)
        self._gps_checkbox.pack(anchor="w", padx=20, pady=3)

        # Sous-options GPS — cachées si organize_by_location est OFF.
        # Placées juste sous la case « Par localisation GPS » via
        # pack(after=…) pour rester en contexte (W17/W18).
        self.gps_options_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        # Affichage initial déclenché plus bas via _refresh_gps_options_visibility
        gps_top = ctk.CTkFrame(self.gps_options_frame, fg_color="transparent")
        gps_top.pack(fill="x", padx=20, pady=2)
        _make_checkbox(
            gps_top,
            text="Géocodage (nom du lieu)",
            variable=self.use_geocoding,
        ).pack(side="left")
        ctk.CTkLabel(
            gps_top,
            text="(sinon : Lat_x_Lon_y brutes)",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray65"),
        ).pack(side="left", padx=8)

        # Slider distance max — pas large 1 km au glissement, ajustement
        # fin 100 m via boutons ◀ / ▶ (Lot R6 du worktree d'origine).
        gps_slider = ctk.CTkFrame(self.gps_options_frame, fg_color="transparent")
        gps_slider.pack(fill="x", padx=20, pady=(2, 6))
        ctk.CTkLabel(
            gps_slider,
            text="Distance max :",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE),
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            gps_slider,
            text="◀",
            width=28,
            command=lambda: self._step_max_distance(-self.MAX_DIST_FINE_STEP),
        ).pack(side="left", padx=(0, 2))

        self.max_distance_slider = ctk.CTkSlider(
            gps_slider,
            from_=0,
            to=50,
            number_of_steps=50,  # pas 1 km au glissement
            variable=self.max_distance,
            width=160,
            command=self._on_max_distance_change,
        )
        self.max_distance_slider.pack(side="left", padx=(0, 2))

        ctk.CTkButton(
            gps_slider,
            text="▶",
            width=28,
            command=lambda: self._step_max_distance(self.MAX_DIST_FINE_STEP),
        ).pack(side="left", padx=(2, 5))

        ctk.CTkLabel(
            gps_slider,
            textvariable=self.max_distance_label_var,
            width=64,
            anchor="w",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight="bold"),
        ).pack(side="left")

        # Sous-option fusionnée GPS (v2.2 étape 3) : la ligne « GPS : [any/
        # with/without] » du panneau Filtres devient ici une simple
        # checkbox « Inclure les photos sans GPS ». Sémantique :
        #   coché   → filter_gps_required = "any"  (toutes les photos)
        #   décoché → filter_gps_required = "with" (uniquement GPS, les
        #             non-GPS sont rejetées avant organisation)
        # Le cas « without » (uniquement les photos SANS GPS) est rare et
        # accessible via le filtre keywords / la sélection ailleurs.
        gps_include_row = ctk.CTkFrame(self.gps_options_frame, fg_color="transparent")
        gps_include_row.pack(fill="x", padx=20, pady=(2, 6))
        self.include_no_gps = ctk.BooleanVar(
            value=self.filter_gps_required.get() != "with"
        )
        _make_checkbox(
            gps_include_row,
            text="Inclure aussi les photos sans GPS (sinon : exclues du tri)",
            variable=self.include_no_gps,
        ).pack(side="left")
        # Sync vers filter_gps_required à chaque toggle
        def _sync_gps_required(*_):
            self.filter_gps_required.set("any" if self.include_no_gps.get() else "with")
        self.include_no_gps.trace_add("write", _sync_gps_required)
        # Sync au démarrage (au cas où l'utilisateur ait sauvegardé "without")
        _sync_gps_required()

        # Sync libellé initial + trace pour mise à jour live
        self._on_max_distance_change(self.max_distance.get())
        self.max_distance.trace_add(
            "write",
            lambda *_: self._on_max_distance_change(self.max_distance.get()),
        )
        # Affichage conditionnel des sous-options selon la case « Par localisation »
        self.organize_by_location.trace_add("write", lambda *_: self._refresh_gps_options_visibility())
        self._refresh_gps_options_visibility()

        # ---- Séparateur visuel + section « Organisation multicouche » -----
        # Cette option modifie significativement le comportement (combine
        # plusieurs critères en cascade). On la met clairement en évidence
        # via un séparateur, un titre dédié et un widget Switch (plus visible
        # qu'une CTkCheckBox pour les modes ON/OFF).
        ctk.CTkFrame(left_frame, height=2, fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=(12, 6))
        ctk.CTkLabel(
            left_frame,
            text="🧩 Organisation avancée",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(0, 4))

        multilayer_row = ctk.CTkFrame(left_frame, fg_color="transparent")
        multilayer_row.pack(fill="x", padx=20, pady=(0, 4))

        self.multilayer_switch = ctk.CTkSwitch(
            multilayer_row,
            text="Organisation multicouche (combine date + appareil + GPS)",
            variable=self.multilayer,
            font=ctk.CTkFont(size=CHECKBOX_FONT_SIZE, weight="bold"),
            progress_color=CHECK_FG,
            switch_width=44,
            switch_height=22,
        )
        self.multilayer_switch.pack(side="left")

        # ----- Sous-panneau « Ordre des critères » (visible si multicouche)
        # Permet de réordonner Date / Appareil / GPS via des boutons ▲ ▼.
        # L'ordre choisi détermine la hiérarchie de dossiers générée par
        # SmartOrganizer (criterion[0] = niveau le plus haut).
        self.criteria_order_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        # On le pack/oublie via _update_criteria_visibility en réaction au
        # toggle multicouche.

        ctk.CTkLabel(
            self.criteria_order_frame,
            text="Ordre des critères (du plus général au plus précis) :",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 4))

        # Conteneur des lignes — re-créé entièrement à chaque réordonnancement
        # via _render_criteria_order, ce qui garde le code simple (pas de
        # gestion de drag-and-drop, juste 6 boutons à recâbler).
        self.criteria_rows_container = ctk.CTkFrame(self.criteria_order_frame, fg_color="transparent")
        self.criteria_rows_container.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            self.criteria_order_frame,
            text=("Astuce : un critère grisé est désactivé (cocher la case correspondante au-dessus pour l'activer)."),
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray65"),
            justify="left",
            wraplength=320,
        ).pack(anchor="w", padx=10, pady=(0, 6))

        # Premier rendu + branchement du toggle
        self._render_criteria_order()
        self.multilayer.trace_add("write", lambda *_: self._update_criteria_visibility())
        # Les checkboxes des critères influencent l'aspect grisé/actif :
        # on rerend le panneau quand l'une d'elles bascule.
        for v in (self.organize_by_date, self.organize_by_camera):
            v.trace_add("write", lambda *_: self._render_criteria_order())
        self._update_criteria_visibility()

        # ----- Sous-section « 💥 Détection de rafales » comme critère
        # (retour testeur 2026-05-17 : burst visible aussi dans Organiser).
        # Toggle + sous-options miroir de ceux de l'onglet Traiter (les
        # variables `detect_bursts`, `burst_mode`, `burst_threshold`,
        # `burst_min_count` sont partagées : un seul état pour les deux UI).
        ctk.CTkFrame(left_frame, height=2, fg_color=("gray70", "gray30")).pack(
            fill="x", padx=10, pady=(12, 6)
        )
        ctk.CTkLabel(
            left_frame,
            text="💥 Détection de rafales (sous-dossier Burst_NN)",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(0, 4))

        burst_row = ctk.CTkFrame(left_frame, fg_color="transparent")
        burst_row.pack(fill="x", padx=20, pady=(0, 4))
        _make_checkbox(
            burst_row,
            text="Activer la détection de rafales (regroupe par moyenne de prise)",
            variable=self.detect_bursts,
        ).pack(anchor="w")
        ctk.CTkLabel(
            left_frame,
            text=(
                "    Photos prises à moins d'un seuil (auto = Δ moyen − σ, ou manuel "
                "en secondes/minutes) regroupées dans un sous-dossier Burst_NN/."
            ),
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray65"),
            anchor="w",
            justify="left",
            wraplength=400,
        ).pack(fill="x", padx=20, pady=(0, 4))

        # Sous-options burst (mode + seuil + min photos) — toujours visibles
        self._burst_subopts_organize = ctk.CTkFrame(left_frame, fg_color="transparent")
        self._burst_subopts_organize.pack(fill="x", padx=20, pady=(0, 6))
        self._build_burst_subopts(self._burst_subopts_organize)

        # Frame droite - Action + Types de fichiers → onglet Traiter
        # Refonte v2.3 (Variante B) : repositionnée dans l'onglet 🛠️ Traiter
        # au lieu de la colonne droite du scroll.
        self._options_right_frame = right_frame = ctk.CTkFrame(self._tab_process)
        right_frame.pack(fill="x", padx=0, pady=PAD_S)

        ctk.CTkLabel(
            right_frame, text="⚙️ Options de traitement", font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Action
        action_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            action_frame,
            text="Action :",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE),
        ).pack(side="left", padx=5)
        _make_radio(action_frame, text="Copier", variable=self.copy_not_move, value=True).pack(side="left", padx=10)
        _make_radio(action_frame, text="Déplacer", variable=self.copy_not_move, value=False).pack(side="left", padx=10)

        # Options avancées
        _make_checkbox(right_frame, text="Parcourir les sous-dossiers", variable=self.recursive).pack(
            anchor="w", padx=20, pady=3
        )

        # Types de fichiers
        ctk.CTkFrame(right_frame, height=2, fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(
            right_frame, text="📂 Types de fichiers", font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold")
        ).pack(anchor="w", padx=10, pady=(0, 4))

        _make_checkbox(right_frame, text="Images (JPG, PNG, HEIC…)", variable=self.include_images).pack(
            anchor="w", padx=20, pady=3
        )

        _make_checkbox(right_frame, text="RAW (ARW, CR2, NEF…)", variable=self.include_raw).pack(
            anchor="w", padx=20, pady=3
        )

        _make_checkbox(right_frame, text="Vidéos (MP4, MOV, AVI…)", variable=self.include_videos).pack(
            anchor="w", padx=20, pady=3
        )

    # =================================================================
    # Sections "avancées" (filtres + comportements + renommage + presets)
    # =================================================================
    def _create_advanced_section(self):
        """Section Filtres + Comportements (refonte v2.3 — Variante B).

        Désormais répartie sur 2 onglets :
        - 🔍 Filtres → onglet « 🔍 Filtrer »
        - 🛠️ Comportements → onglet « 🛠️ Traiter » (sous Action/Types)

        L'attribut ``_adv_content`` est conservé (rétrocompat) et pointe
        vers un container invisible — ``_adv_collapsed`` reste à False et
        ``_toggle_advanced_section`` est un no-op fonctionnel.
        """
        # État "déplié en permanence" (rétrocompat tests v2.2)
        self._adv_collapsed = False

        # Bouton toggle conservé (caché) — rétrocompat _attach_tooltips
        self._adv_toggle_btn = ctk.CTkButton(
            self._tab_filter,
            text="⚙️ Filtres & Comportements",
            command=self._toggle_advanced_section,
            anchor="w",
            font=font_section(),
            fg_color="transparent",
            text_color=("gray10", "#DCE4EE"),
            hover_color=("gray85", "gray25"),
            height=BTN_H_STD,
        )
        # Pas de grid() → invisible.

        # Container _adv_content (rétrocompat) — contient désormais
        # directement les filtres pour qu'ils s'affichent au plus haut
        # du panneau Filtrer (retour testeur 2026-05-17 it. 2 :
        # « le titre filtre et l'ensemble des champs soit en haut »).
        self._adv_content = ctk.CTkFrame(self._tab_filter, fg_color="transparent")
        self._adv_content.pack(fill="both", expand=True, padx=0, pady=0, anchor="n")

        # ===== Colonne gauche : filtres pré-traitement → onglet 🔍 Filtrer =====
        # ``_adv_left_frame`` est désormais enfant direct de ``_adv_content``
        # pour assurer un layout vertical propre, ancré au haut du panneau.
        self._adv_left_frame = filters = ctk.CTkFrame(self._adv_content, fg_color="transparent")
        filters.pack(fill="x", padx=0, pady=0, anchor="n")

        # Titre + bouton 💡 « Exemples de filtres » (refonte 2026-05-19) —
        # ouvre un panneau intégré avec des valeurs standards pour les filtres
        # « non personnels » (extensions, dimensions, mots-clés, orientation,
        # note). La date et la taille restent gérées par les chips inline car
        # ces deux filtres sont propres à chaque utilisateur.
        title_row = ctk.CTkFrame(filters, fg_color="transparent")
        title_row.pack(fill="x", padx=PAD_S, pady=(PAD_S, PAD_S))
        ctk.CTkLabel(
            title_row,
            text="🔍 Filtres",
            font=font_label(weight="bold"),
        ).pack(side="left")
        self.filter_examples_btn = icon_button(
            title_row,
            text="💡",
            command=self._show_filter_examples_panel,
        )
        self.filter_examples_btn.pack(side="left", padx=PAD_S)
        ctk.CTkLabel(
            title_row,
            text="Cliquer 💡 pour voir des valeurs standards (extensions, dimensions, mots-clés…).",
            font=font_hint(),
            text_color=HINT_COLOR,
            anchor="w",
        ).pack(side="left", padx=(PAD_S, 0))

        # ---- Bloc Entrées texte avec exemples cliquables sous chaque champ ----
        # Refonte v2.3 (retour testeur 2026-05-17) : chaque filtre est
        # accompagné d'une rangée de « chips » cliquables qui remplissent
        # le champ en un clic. Permet d'expérimenter rapidement sans
        # connaître la syntaxe.
        filter_specs = [
            ("Date min :",  self.filter_date_min,  "YYYY-MM-DD — ex. 2024-06-01",
             ["2024-01-01", "2024-06-01", "2025-01-01"]),
            ("Date max :",  self.filter_date_max,  "YYYY-MM-DD — vide = pas de limite",
             ["2024-12-31", "2025-06-30", "2025-12-31"]),
            ("Taille min :", self.filter_size_min, "B/KB/MB/GB — ex. 100KB",
             ["100KB", "500KB", "1MB", "5MB"]),
            ("Taille max :", self.filter_size_max, "B/KB/MB/GB — vide = pas de limite",
             ["5MB", "20MB", "50MB", "1GB"]),
            ("Extension :", self.filter_extensions, "Liste CSV — ex. jpg,raw,heic",
             ["jpg", "jpg,png", "jpg,raw", "raw,heic,dng"]),
            ("Dim. min :",  self.filter_dim_min,   "WxH — ex. 1920x1080",
             ["800x600", "1920x1080", "3840x2160"]),
            ("Dim. max :",  self.filter_dim_max,   "WxH — ex. 8000x6000",
             ["1920x1080", "4096x2160", "8000x6000"]),
        ]
        # Liste des chips créés (utile aux tests + à la lecture programmatique)
        self._filter_example_chips = []
        for label, var, placeholder, examples in filter_specs:
            row = ctk.CTkFrame(filters, fg_color="transparent")
            row.pack(fill="x", padx=PAD_S, pady=(2, 0))
            ctk.CTkLabel(row, text=label, width=86, anchor="w", font=font_label()).pack(side="left")
            ctk.CTkEntry(row, textvariable=var, placeholder_text=placeholder, height=BTN_H_STD).pack(
                side="left", padx=PAD_S, fill="x", expand=True
            )
            # Ligne d'exemples cliquables (chips compacts)
            ex_row = ctk.CTkFrame(filters, fg_color="transparent")
            ex_row.pack(fill="x", padx=(94, PAD_S), pady=(0, PAD_S))
            ctk.CTkLabel(
                ex_row, text="Exemples :", font=font_hint(),
                text_color=HINT_COLOR, anchor="w",
            ).pack(side="left", padx=(0, PAD_S))
            for ex in examples:
                chip = ctk.CTkButton(
                    ex_row,
                    text=ex,
                    command=lambda v=var, val=ex: v.set(val),
                    width=10,
                    height=22,
                    font=font_hint(),
                    fg_color=("gray85", "gray25"),
                    text_color=("gray15", "gray85"),
                    hover_color=("gray75", "gray35"),
                    corner_radius=11,
                )
                chip.pack(side="left", padx=2)
                self._filter_example_chips.append(chip)

        # Refonte v2.2 : hints inline supprimés ; le sens des valeurs est
        # explicité dans le tooltip de l'OptionMenu (cf. _attach_tooltips).

        # Note EXIF (0 = inactif)
        rating_row = ctk.CTkFrame(filters, fg_color="transparent")
        rating_row.pack(fill="x", padx=PAD_S, pady=2)
        ctk.CTkLabel(rating_row, text="Note ≥ :", width=86, anchor="w", font=font_label()).pack(side="left")
        ctk.CTkOptionMenu(
            rating_row,
            variable=self.filter_rating_min,
            values=["0", "1", "2", "3", "4", "5"],
            width=70,
            height=BTN_H_STD,
            command=lambda v: self.filter_rating_min.set(int(v)),
        ).pack(side="left", padx=PAD_S)

        # GPS filtre retiré — fusionné dans la section Critères >
        # « ☑ Par localisation GPS » qui propose désormais d'inclure ou
        # non les photos sans GPS (cf. étape 3 fusion conceptuelle).

        # Orientation (any/landscape/portrait/square)
        ori_row = ctk.CTkFrame(filters, fg_color="transparent")
        ori_row.pack(fill="x", padx=PAD_S, pady=2)
        ctk.CTkLabel(ori_row, text="Orientation :", width=86, anchor="w", font=font_label()).pack(side="left")
        ctk.CTkOptionMenu(
            ori_row,
            variable=self.filter_orientation,
            values=["any", "landscape", "portrait", "square"],
            width=120,
            height=BTN_H_STD,
        ).pack(side="left", padx=PAD_S)

        # Mots-clés (CSV)
        kw_row = ctk.CTkFrame(filters, fg_color="transparent")
        kw_row.pack(fill="x", padx=PAD_S, pady=2)
        ctk.CTkLabel(kw_row, text="Mots-clés :", width=86, anchor="w", font=font_label()).pack(side="left")
        ctk.CTkEntry(
            kw_row,
            textvariable=self.filter_keywords,
            placeholder_text="CSV — ex. vacances, mariage, été",
            height=BTN_H_STD,
        ).pack(side="left", padx=PAD_S, fill="x", expand=True)

        # ===== Comportements + bursts + incremental → onglet 🛠️ Traiter =====
        # Refonte v2.3 (Variante B) : la colonne droite « Comportements »
        # est désormais empilée sous Action/Types dans l'onglet Traiter
        # (et non plus en parallèle des filtres).
        self._adv_right_frame = behaviors = ctk.CTkFrame(self._tab_process, fg_color="transparent")
        behaviors.pack(fill="x", padx=PAD_S, pady=(PAD_M, PAD_S))

        # Séparateur visuel entre Action/Types et Comportements
        ctk.CTkFrame(self._tab_process, height=1, fg_color=SEPARATOR_COLOR).pack(
            fill="x", padx=PAD_M, pady=(0, PAD_S), before=behaviors,
        )

        ctk.CTkLabel(
            behaviors,
            text="🛠️ Comportements",
            font=font_label(weight="bold"),
        ).pack(anchor="w", padx=PAD_S, pady=(PAD_S, PAD_S))

        # Comportements regroupés par catégorie (refactor 2026-05-15).
        #
        # Refactor 2026-05-15 (suite testeur) :
        # - La section « 🔔 Notification » est DÉPLACÉE dans Paramètres.
        # - La section « 📋 Index » est DÉPLACÉE dans Paramètres.
        # - Les sous-options bursts (mode/écart/min) apparaissent désormais
        #   DIRECTEMENT sous la checkbox « Détection de rafales » (et non
        #   plus en fin de panneau Comportements après Notifications),
        #   ce qui était illisible.
        #
        # Le rendu dynamique (show/hide) des sous-options bursts est piloté
        # par une trace sur ``self.detect_bursts`` (voir _refresh_burst_subopts).
        behavior_groups = [
            (
                "📦 Conservation des doublons",
                [
                    (
                        "Skip si fichier identique déjà présent",
                        self.skip_if_identical,
                        "ex : 2 photos identiques (hash égal) → seule la 1ère est traitée",
                    ),
                    (
                        "Garder les paires RAW + JPEG ensemble",
                        self.keep_raw_jpeg_pairs,
                        "ex : IMG_001.CR2 + IMG_001.JPG → même dossier final",
                    ),
                ],
            ),
            (
                "🧹 Nettoyage / sécurité",
                [
                    (
                        "Nettoyer les dossiers source vides (Déplacer)",
                        self.cleanup_empty_source,
                        "ex : après MOVE, supprime D:/Vacances/Jour1/ s'il devient vide",
                    ),
                    (
                        "Vérifier l'espace disque avant exécution",
                        self.validate_disk_space,
                        "ex : refuse de copier 80 Go vers un disque qui en a 50",
                    ),
                ],
            ),
            (
                "🔍 Détection / mode",
                [
                    # Détection de rafales : DÉPLACÉE dans l'onglet Organiser
                    # (retour testeur 2026-05-17) — burst = critère, pas juste
                    # un comportement. Cf. _create_options_section / left_frame.
                    (
                        "Mode incrémental (skip déjà organisés)",
                        self.incremental_mode,
                        "ex : 2e exécution du même dossier → ne retraite que les nouveaux",
                    ),
                ],
            ),
        ]
        for group_title, toggles in behavior_groups:
            ctk.CTkLabel(
                behaviors,
                text=group_title,
                font=font_hint(),
                text_color=HINT_COLOR,
                anchor="w",
            ).pack(fill="x", padx=PAD_S, pady=(PAD_S, 0))
            for text, var, hint in toggles:
                _make_checkbox(behaviors, text=text, variable=var).pack(anchor="w", padx=(PAD_L, PAD_S), pady=(2, 0))
                # Note inline avec un "ex : …" sous chaque toggle.
                ctk.CTkLabel(
                    behaviors,
                    text=f"    {hint}",
                    font=font_hint(),
                    text_color=HINT_COLOR,
                    anchor="w",
                    justify="left",
                ).pack(fill="x", padx=(PAD_L, PAD_S), pady=(0, PAD_S))

        # Bursts ont été déplacés vers l'onglet Organiser (cf. _create_options_section).
        # On garde une référence vide pour rétrocompat de _refresh_burst_subopts.
        if not hasattr(self, "_burst_subopts"):
            self._burst_subopts = self._burst_subopts_organize

    def _make_config_persist_cb(self, attr_name):
        """Renvoie un callback `trace_add("write", ...)` qui persiste
        ``self.<attr_name>`` dans AppConfig dès qu'il change.

        Méthode (et pas closure dans __init__) pour éviter les problèmes
        d'ordre de définition entre les blocs de vars (refactor 2026-05-15).
        """

        def _cb(*_args):
            try:
                get_config().set(attr_name, getattr(self, attr_name).get())
            except Exception as exc:
                logger.debug(f"persist {attr_name}: {exc}")

        return _cb

    def _build_burst_subopts(self, container):
        """Construit le sous-bloc 'mode/écart/min photos' des bursts.

        Extrait dans une méthode pour pouvoir l'attacher juste sous la
        checkbox « Détection de rafales » (cf. fix bug 2026-05-15).
        """
        # Ligne 1 : choix du mode (radios)
        mode_row = ctk.CTkFrame(container, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(mode_row, text="Mode :", width=80, anchor="w", font=font_hint(), text_color=HINT_COLOR).pack(
            side="left"
        )
        # Refonte 2026-05-17 it. 2 : 3 modes au lieu de 2 (manuel, auto-mean,
        # auto-stddev). L'utilisateur choisit la stratégie de calcul auto.
        _make_radio(
            mode_row,
            text="Manuel (seuil fixe)",
            variable=self.burst_mode,
            value="manual",
            command=lambda: self._refresh_burst_mode_ui(),
        ).pack(side="left", padx=(0, PAD_M))
        _make_radio(
            mode_row,
            text="Auto moyenne (Δ < mean)",
            variable=self.burst_mode,
            value="auto_mean",
            command=lambda: self._refresh_burst_mode_ui(),
        ).pack(side="left", padx=(0, PAD_M))
        _make_radio(
            mode_row,
            text="Auto écart-type (Δ < mean − σ)",
            variable=self.burst_mode,
            value="auto_stddev",
            command=lambda: self._refresh_burst_mode_ui(),
        ).pack(side="left")

        # Ligne 2 : Écart max (visible seulement en mode manuel)
        self._burst_manual_row = ctk.CTkFrame(container, fg_color="transparent")
        self._burst_manual_row.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(
            self._burst_manual_row, text="Écart max :", width=80, anchor="w", font=font_hint(), text_color=HINT_COLOR
        ).pack(side="left")
        ctk.CTkOptionMenu(
            self._burst_manual_row,
            variable=self.burst_threshold,
            values=["1", "2", "3", "5", "10", "30", "60"],
            width=70,
            height=BTN_H_STD,
            command=lambda v: self.burst_threshold.set(int(v)),
        ).pack(side="left", padx=PAD_S)
        ctk.CTkLabel(self._burst_manual_row, text="s", font=font_hint(), text_color=HINT_COLOR).pack(side="left")

        # Ligne 2 bis : bornes auto (visibles seulement en mode auto)
        # Audit 2026-05-15 (élargissement) — expose le clamp historique
        # [1 s ; 600 s] comme option avancée. L'utilisateur peut élargir
        # (timelapse, pauses longues) ou serrer (vraies rafales rapides).
        self._burst_auto_row = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkLabel(
            self._burst_auto_row, text="Bornes auto :", width=80, anchor="w", font=font_hint(), text_color=HINT_COLOR
        ).pack(side="left")
        ctk.CTkLabel(self._burst_auto_row, text="min", font=font_hint(), text_color=HINT_COLOR).pack(
            side="left", padx=(0, 2)
        )
        ctk.CTkOptionMenu(
            self._burst_auto_row,
            variable=self.burst_auto_min,
            values=["1", "2", "3", "5", "10", "30"],
            width=60,
            height=BTN_H_STD,
            command=lambda v: self.burst_auto_min.set(int(v)),
        ).pack(side="left", padx=(0, PAD_S))
        ctk.CTkLabel(self._burst_auto_row, text="s  ·  max", font=font_hint(), text_color=HINT_COLOR).pack(
            side="left", padx=(0, 2)
        )
        ctk.CTkOptionMenu(
            self._burst_auto_row,
            variable=self.burst_auto_max,
            values=["60", "120", "300", "600", "1800", "3600"],
            width=70,
            height=BTN_H_STD,
            command=lambda v: self.burst_auto_max.set(int(v)),
        ).pack(side="left", padx=(0, PAD_S))
        ctk.CTkLabel(self._burst_auto_row, text="s", font=font_hint(), text_color=HINT_COLOR).pack(side="left")

        # Ligne 3 : Min photos par burst — visible UNIQUEMENT en mode manuel.
        # Retour testeur 2026-05-17 it. 3 : en mode auto, le calcul est
        # entièrement basé sur la stat des Δt — aucun bouton à exposer.
        self._burst_min_row = ctk.CTkFrame(container, fg_color="transparent")
        self._burst_min_row.pack(fill="x")
        ctk.CTkLabel(self._burst_min_row, text="Min photos :", width=80, anchor="w", font=font_hint(), text_color=HINT_COLOR).pack(
            side="left"
        )
        ctk.CTkOptionMenu(
            self._burst_min_row,
            variable=self.burst_min_count,
            values=["2", "3", "4", "5", "8"],
            width=60,
            height=BTN_H_STD,
            command=lambda v: self.burst_min_count.set(int(v)),
        ).pack(side="left", padx=PAD_S)
        ctk.CTkLabel(
            self._burst_min_row,
            text="par groupe",
            font=font_hint(),
            text_color=HINT_COLOR,
        ).pack(side="left")

        # Hint dédié au mode auto (affiché en remplacement quand auto)
        self._burst_auto_hint = ctk.CTkLabel(
            container,
            text=(
                "Calcul automatique sur les Δt EXIF du dossier — "
                "aucun paramètre à régler manuellement."
            ),
            font=font_hint(),
            text_color=HINT_COLOR,
            anchor="w",
            justify="left",
            wraplength=400,
        )
        # Pas packé ici — affichage piloté par _refresh_burst_mode_ui.

        # État initial (manuel par défaut)
        self._refresh_burst_mode_ui()

    def _refresh_burst_subopts(self):
        """No-op (refonte v2.3 retour testeur 2026-05-17) : les sous-options
        burst sont désormais toujours visibles dans l'onglet Organiser.
        Conservé pour rétrocompat avec d'éventuels appels externes.
        """
        return

    def _toggle_advanced_section(self):
        """Bascule le panneau Avancé (collapse/expand)."""
        if self._adv_collapsed:
            # Affiche le contenu
            self._adv_content.grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            self._adv_toggle_btn.configure(text="▼  ⚙️ Options avancées (cliquez pour replier)")
            self._adv_collapsed = False
        else:
            self._adv_content.grid_forget()
            self._adv_toggle_btn.configure(text="▶  ⚙️ Options avancées (filtres, comportements, bursts, …)")
            self._adv_collapsed = True

    def _create_schedule_section(self):
        """No-op : la section "Planification" a été déplacée dans SettingsFrame.

        Les vars (schedule_enabled, schedule_time, schedule_status_var) restent
        définies dans __init__ pour que SettingsFrame puisse y accéder via
        l'instance OrganizeFrame partagée. Cette méthode est conservée pour
        compatibilité avec d'éventuels appels externes mais ne crée plus de
        widget — le UI vit dans Paramètres > Planification.
        """
        return  # intentionnel — voir docstring

    def _create_rename_section(self):
        """Section "Renommage" — single colonne + popover exemples (v2.2).

        Audit 2026-05-15 — étape 2/5 : la liste statique de 10 exemples
        occupait ~30 % de la largeur du panneau Renommage en permanence.
        Refonte : un bouton « 📋 Exemples ▸ » à côté du champ Template
        ouvre un popover modal listant les 10 templates cliquables. Gain
        d'espace : ~250 px de largeur récupérés, layout single-column.

        Garde ``_rename_collapsed = False`` et ``_rename_toggle_btn`` pour
        rétrocompat avec ``_attach_tooltips`` (référence existante au btn).
        """
        # Container externe — refonte v2.3 (Variante B) : grid dans l'onglet Renommer
        wrapper = ctk.CTkFrame(self._tab_rename)
        wrapper.pack(fill="x", padx=0, pady=PAD_S)
        wrapper.columnconfigure(0, weight=1)

        # État "déplié en permanence" — flag conservé pour rétrocompat
        self._rename_collapsed = False

        # Bouton toggle gardé pour rétrocompat (référencé par _attach_tooltips)
        self._rename_toggle_btn = ctk.CTkButton(
            wrapper,
            text="🏷️ Renommage & Presets",
            command=self._toggle_rename_section,
            anchor="w",
            font=font_section(),
            fg_color="transparent",
            text_color=("gray10", "#DCE4EE"),
            hover_color=("gray85", "gray25"),
            height=BTN_H_STD,
        )
        # Pas de grid() → invisible.

        # Titre de section visible (statique).
        ctk.CTkLabel(
            wrapper,
            text="🏷️ Renommage & Presets",
            font=font_section(),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))

        # Content frame — single colonne (refonte v2.2)
        self._rename_content = ctk.CTkFrame(wrapper, fg_color="transparent")
        self._rename_content.columnconfigure(1, weight=1)

        # Liste des templates RENAME_TEMPLATES (chargée pour le popover et
        # pour la rétrocompat de ``self._rename_example_btns``).
        from ui.prompt_examples import RENAME_TEMPLATES
        self._rename_templates = list(RENAME_TEMPLATES)

        # Rétrocompat : conserver `_rename_example_btns` (référencé par les
        # tests UX_V4). Les boutons sont créés à la volée dans le popover ;
        # ici on alimente la liste avec des références placeholder = None
        # qui seront remplacées à chaque ouverture du popover.
        self._rename_example_btns = [(None, tpl) for tpl in self._rename_templates]

        # ===== Single colonne : édition + presets =====
        edit_box = ctk.CTkFrame(self._rename_content)
        edit_box.grid(row=0, column=0, sticky="nsew", padx=PAD_M, pady=(0, PAD_M))
        edit_box.columnconfigure(1, weight=1)

        # Template entry — refonte v2.3 (retour testeur 2026-05-17) :
        # le bouton popover « 📋 Exemples ▸ » a été supprimé au profit
        # d'une liste inline scrollable plus bas. Le bouton est conservé
        # caché pour rétrocompat (références tooltips / autres).
        ctk.CTkLabel(edit_box, text="Template :", font=font_label()).grid(
            row=0, column=0, sticky="w", padx=PAD_M, pady=(PAD_M, PAD_S)
        )
        self.rename_entry = ctk.CTkEntry(
            edit_box,
            textvariable=self.rename_template,
            placeholder_text="(vide = nom d'origine conservé)",
            height=BTN_H_STD,
            font=font_label(),
        )
        self.rename_entry.grid(row=0, column=1, sticky="ew", padx=(0, PAD_M), pady=(PAD_M, PAD_S))

        # Bouton popover caché (rétrocompat — pas grid() → invisible).
        self._rename_examples_btn = neutral_button(
            edit_box, text="📋 Exemples ▸",
            command=self._show_rename_examples_popover,
            width=140,
        )

        # Aperçu live
        self.rename_preview_var = ctk.StringVar(value="(aucun template)")
        ctk.CTkLabel(edit_box, text="Aperçu :", font=font_label()).grid(
            row=1, column=0, sticky="w", padx=PAD_M, pady=PAD_S
        )
        ctk.CTkLabel(
            edit_box,
            textvariable=self.rename_preview_var,
            font=font_hint(),
            text_color=HINT_COLOR,
            anchor="w",
            justify="left",
        ).grid(row=1, column=1, sticky="ew", padx=(0, PAD_M), pady=PAD_S)
        self.rename_template.trace_add("write", lambda *_: self._refresh_rename_preview())

        # Tokens disponibles + exemples concrets (audit 2026-05-15)
        ctk.CTkLabel(
            edit_box,
            text="Tokens : {original}, {ext}, {date:%Y%m%d}, {camera}, {counter:03d}",
            font=font_hint(),
            text_color=HINT_COLOR,
            anchor="w",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=PAD_M, pady=(PAD_S, 0))
        ctk.CTkLabel(
            edit_box,
            text=(
                "    ex : {date:%Y%m%d}_{counter:04d}{ext}    →    "
                "20260507_0001.jpg\n"
                "    ex : {date:%Y-%m-%d}_{camera}_{original}    →    "
                "2026-05-07_Sony-A7M3_IMG_0001.jpg\n"
                "    ex : {date:%Y-%m}_VAC_{counter:03d}{ext}   →    "
                "2026-05_VAC_001.jpg"
            ),
            font=font_hint(),
            text_color=HINT_COLOR,
            anchor="w",
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=PAD_M, pady=(0, PAD_M))

        # ----- Liste inline des exemples (refonte v2.3 it. 2) -----------
        # Retour testeur 2026-05-17 it. 2 : « les exemples doivent prendre
        # toute la place du panneau pour éviter de perdre de l'espace et
        # avoir une scroll bar pour rien ». Utilisation d'un Frame normal
        # (pas de scrollbar interne) qui s'étend verticalement (sticky=nsew).
        # Si l'onglet est trop court, le scroll global de la zone centre
        # prend le relais — pas de scrollbar imbriquée.
        ctk.CTkLabel(
            edit_box,
            text="📋 Exemples (cliquer pour appliquer) :",
            font=font_label(weight="bold"),
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=PAD_M, pady=(PAD_M, PAD_S))

        # Frame normal sans height fixe — prend toute la place dispo.
        examples_box = ctk.CTkFrame(
            edit_box, fg_color=("gray95", "gray18"),
        )
        examples_box.grid(
            row=5, column=0, columnspan=2, sticky="nsew",
            padx=PAD_M, pady=(0, PAD_S),
        )
        # Permet à edit_box row=5 de s'étendre verticalement
        edit_box.rowconfigure(5, weight=1)

        # On reconstruit _rename_example_btns avec les vrais boutons inline
        # (les tests UX_V4 vérifient len(self._rename_example_btns) >= 5).
        self._rename_example_btns = []
        for tpl in self._rename_templates:
            row = ctk.CTkFrame(examples_box, fg_color="transparent")
            row.pack(fill="x", padx=PAD_S, pady=4)
            btn = ctk.CTkButton(
                row,
                text=f"• {tpl.label}",
                anchor="w",
                fg_color="transparent",
                hover_color=("gray80", "gray28"),
                text_color=("gray10", "#DCE4EE"),
                command=lambda t=tpl.template: self._apply_rename_example(t),
                height=28,
                font=font_label(weight="bold"),
            )
            btn.pack(fill="x")
            self._rename_example_btns.append((btn, tpl))
            # Refonte v2.3 it. 4 (retour testeur 2026-05-18) : élargir les
            # exemples pour montrer le template regex ET son explication
            # côte à côte. wraplength est passé à une valeur très grande
            # (1600 px) — le label utilise toute la largeur dispo grâce
            # à fill="x" / anchor="w".
            template_str = getattr(tpl, "template", "") or "(vide)"
            description = getattr(tpl, "description", None) or template_str
            preview = getattr(tpl, "preview", None)

            # Ligne 1 : le template (regex) en monospace-like
            ctk.CTkLabel(
                row,
                text=f"    Template : {template_str}",
                font=font_hint(),
                text_color=("#1565C0", "#64B5F6"),  # bleu — visuel "code"
                anchor="w",
                justify="left",
                wraplength=1600,
            ).pack(fill="x", padx=(0, 0))

            # Ligne 2 : description + aperçu rendu
            sub_text = f"    → {description}"
            if preview:
                sub_text += f"   ·   ex : {preview}"
            ctk.CTkLabel(
                row,
                text=sub_text,
                font=font_hint(),
                text_color=HINT_COLOR,
                anchor="w",
                justify="left",
                wraplength=1600,
            ).pack(fill="x", padx=(0, 0))

        # Séparateur entre Exemples et Presets
        ctk.CTkFrame(edit_box, height=1, fg_color=SEPARATOR_COLOR).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=PAD_M,
            pady=(PAD_S, PAD_S),
        )

        # Ligne Presets
        ctk.CTkLabel(edit_box, text="Preset :", font=font_label()).grid(
            row=7, column=0, sticky="w", padx=PAD_M, pady=(0, PAD_M)
        )
        preset_row = ctk.CTkFrame(edit_box, fg_color="transparent")
        preset_row.grid(row=7, column=1, sticky="ew", padx=(0, PAD_M), pady=(0, PAD_M))
        self._preset_menu = ctk.CTkOptionMenu(
            preset_row,
            variable=self.preset_name,
            values=self._list_preset_names(),
            command=self._on_preset_selected,
            width=180,
            height=BTN_H_STD,
        )
        self._preset_menu.pack(side="left", padx=(0, PAD_S))
        icon_button(preset_row, text="💾", command=self._save_preset_dialog).pack(side="left", padx=(0, PAD_S))
        icon_button(preset_row, text="🗑", command=self._delete_preset).pack(side="left")

        # Toujours visible (refonte v2.2) — plus de pliage conditionnel.
        self._rename_content.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

    def _show_rename_examples_popover(self):
        """Modale flottante listant les 10 templates de renommage cliquables.

        Refonte v2.2 (étape 2/5) : remplace la liste statique permanente
        (colonne gauche du Renommage qui prenait ~30 % de la largeur).
        Cette modale s'ouvre au clic sur « 📋 Exemples ▸ », l'utilisateur
        choisit un template (clic) ou réinitialise (bouton bas), puis la
        modale se ferme automatiquement.
        """
        from ui.theme import add_logo_to_modal

        win = ctk.CTkToplevel(self)
        win.title("Exemples de renommage")
        win.geometry("520x460")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        # Logo + titre (helper centralisé)
        add_logo_to_modal(win, size=40, text="📋 Exemples de renommage")

        # Sous-titre explicatif
        ctk.CTkLabel(
            win,
            text=("Cliquez sur un exemple pour l'appliquer au champ Template. "
                  "La modale se ferme automatiquement."),
            font=font_hint(),
            text_color=HINT_COLOR,
            anchor="w",
            justify="left",
            wraplength=480,
        ).pack(fill="x", padx=PAD_L, pady=(PAD_S, PAD_M))

        # Liste scrollable des exemples cliquables (refait à chaque ouverture
        # — les références sont stockées dans _rename_example_btns pour
        # rétrocompat avec les tests).
        listbox = ctk.CTkScrollableFrame(win, fg_color="transparent")
        listbox.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_S)

        self._rename_example_btns = []
        for tpl in self._rename_templates:
            row = ctk.CTkFrame(listbox, fg_color="transparent")
            row.pack(fill="x", pady=2)
            # Label du template (Titre + description en dessous)
            btn = ctk.CTkButton(
                row,
                text=f"• {tpl.label}",
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("gray10", "#DCE4EE"),
                command=lambda t=tpl.template, w=win: (
                    self._apply_rename_example(t), w.destroy()
                ),
                height=28,
                font=font_label(),
            )
            btn.pack(fill="x")
            self._rename_example_btns.append((btn, tpl))
            # Description en sous-ligne grise pour comprendre le rendu
            description = getattr(tpl, "description", None) or getattr(tpl, "template", "")
            ctk.CTkLabel(
                row,
                text=f"    → {description}",
                font=font_hint(),
                text_color=HINT_COLOR,
                anchor="w",
                justify="left",
            ).pack(fill="x")

        # Boutons bas : Réinitialiser (gauche) + Fermer (droite)
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD_L, pady=(PAD_S, PAD_L))
        btn_row.columnconfigure(1, weight=1)

        neutral_button(
            btn_row,
            text="🔄 Réinitialiser",
            command=lambda: (self._apply_rename_example(""), win.destroy()),
            width=140,
        ).grid(row=0, column=0, sticky="w")

        neutral_button(
            btn_row,
            text="Fermer",
            command=win.destroy,
            width=100,
        ).grid(row=0, column=2, sticky="e")

        # Raccourci Echap pour fermer
        win.bind("<Escape>", lambda _e: win.destroy())

    def _rename_toggle_label(self) -> str:
        return "▶  🏷️ Renommage & Presets" if self._rename_collapsed else "▼  🏷️ Renommage & Presets"

    def _refresh_burst_mode_ui(self):
        """Affiche/cache les sous-options bursts selon le mode actif.

        Refonte 2026-05-17 it. 3 :
        - Mode manuel : Écart max + Min photos affichés (paramétrables).
        - Modes auto_mean / auto_stddev : tout est masqué — seul un hint
          indique que le calcul est entièrement automatique sur les Δt
          EXIF. L'utilisateur n'a aucun bouton à régler.
        """
        try:
            mode = self.burst_mode.get()
            is_manual = (mode == "manual")
            if is_manual:
                self._burst_manual_row.pack(fill="x", pady=(0, 2))
                self._burst_auto_row.pack_forget()
                self._burst_min_row.pack(fill="x")
                self._burst_auto_hint.pack_forget()
            else:
                self._burst_manual_row.pack_forget()
                self._burst_auto_row.pack_forget()
                self._burst_min_row.pack_forget()
                self._burst_auto_hint.pack(fill="x", pady=(PAD_S, 0))
        except AttributeError:
            # Pas encore créé (appel pendant l'init)
            pass

    def _toggle_rename_section(self):
        """Bascule le panneau Renommage et persiste l'état."""
        self._rename_collapsed = not self._rename_collapsed
        if self._rename_collapsed:
            self._rename_content.grid_forget()
        else:
            self._rename_content.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        self._rename_toggle_btn.configure(text=self._rename_toggle_label())
        # Persistance
        try:
            get_config().set("rename_collapsed", self._rename_collapsed)
        except Exception:
            pass

    def _apply_rename_example(self, template_str: str):
        """Applique un exemple de template à la zone d'édition."""
        self.rename_template.set(template_str)
        # Le trace_add appelle automatiquement _refresh_rename_preview

    def _create_right_rail(self):
        """Right rail (refonte v2.3 — Variante B) : actions + presets.

        Layout vertical sticky (210 px de large, hauteur = middle row) :
          ─────────────
          Preset ▼  💾  🗑
          ─────────────
          📊 Analyser  (height=40)
          👁 Aperçu    (height=40)
          ❌ Annuler   (height=32)
          🚀 Organiser (height=40, primary)
          ─────────────
          ▼ Cible
          • N fichiers
          • M dossiers

        Les attributs ``self.analyze_button`` / ``self.preview_button`` /
        ``self.cancel_button`` / ``self.organize_button`` sont conservés
        (les méthodes _organize_files etc. y font référence partout).
        """
        rail = self._right_rail
        rail.columnconfigure(0, weight=1)

        # ===== Section Preset (en haut du rail) =====
        ctk.CTkLabel(
            rail, text="📦 Preset", font=font_label(weight="bold"), anchor="w"
        ).pack(fill="x", padx=PAD_M, pady=(PAD_M, PAD_S))

        preset_box = ctk.CTkFrame(rail, fg_color="transparent")
        preset_box.pack(fill="x", padx=PAD_M, pady=(0, PAD_S))
        preset_box.columnconfigure(0, weight=1)

        # On crée un OptionMenu rail mais sans variable (la vraie variable
        # `self.preset_name` est créée par _create_rename_section). On
        # synchronisera l'affichage via une trace après init.
        self._rail_preset_menu = ctk.CTkOptionMenu(
            preset_box,
            variable=self.preset_name,
            values=self._list_preset_names() if hasattr(self, "_list_preset_names") else ["—"],
            command=self._on_preset_selected if hasattr(self, "_on_preset_selected") else None,
            height=BTN_H_STD,
        )
        self._rail_preset_menu.grid(row=0, column=0, sticky="ew")
        icon_button(preset_box, text="💾", command=self._save_preset_dialog).grid(
            row=0, column=1, padx=(PAD_S, 0)
        )
        icon_button(preset_box, text="🗑", command=self._delete_preset).grid(
            row=0, column=2, padx=(PAD_S, 0)
        )

        # Séparateur
        ctk.CTkFrame(rail, height=1, fg_color=SEPARATOR_COLOR).pack(
            fill="x", padx=PAD_M, pady=PAD_S,
        )

        # ===== Actions (verticales, sticky) =====
        # Refonte v2.3 (Variante B) : les 4 boutons sont empilés
        # verticalement dans le right rail au lieu de la zone bottom
        # horizontale. Cliquables sans bouger les yeux du contenu.
        actions_box = ctk.CTkFrame(rail, fg_color="transparent")
        actions_box.pack(fill="x", padx=PAD_M, pady=(0, PAD_S))
        actions_box.columnconfigure(0, weight=1)

        self.analyze_button = neutral_button(
            actions_box,
            text="📊 Analyser",
            command=self._analyze_files,
            height=BTN_H_PRIMARY,
            font=font_label(weight="bold"),
        )
        self.analyze_button.pack(fill="x", pady=(0, PAD_S))

        self.preview_button = neutral_button(
            actions_box,
            text="👁 Aperçu",
            command=self._show_dry_run_preview,
            height=BTN_H_PRIMARY,
            font=font_label(weight="bold"),
        )
        self.preview_button.pack(fill="x", pady=(0, PAD_S))

        self.cancel_button = danger_button(
            actions_box,
            text="❌ Annuler",
            command=self._cancel_operation,
            state="disabled",
        )
        self.cancel_button.pack(fill="x", pady=(0, PAD_S))

        # Bandeau warning trial (pivot 2026-05-26)
        # Affiché de manière persistante au-dessus du bouton Organiser quand
        # l'utilisateur est aux seuils 8/10 ou 9/10 SANS licence active.
        # Hors warning : grid_remove() le masque sans le détruire.
        self.trial_warning_banner = ctk.CTkLabel(
            actions_box,
            text="",
            font=font_label(weight="bold"),
            text_color=("#8a5a10", "#f3c876"),
            fg_color=("#f7e7c4", "#3a2e16"),
            corner_radius=6,
            anchor="w",
            justify="left",
            # B-11 (audit 2026-06-11) : le rail fait 210 px de large —
            # wraplength=380 tronquait le texte au lieu de le replier.
            wraplength=180,
        )
        # NB : on utilise pack(...) ailleurs dans ce conteneur — pack_forget()
        # est l'équivalent de grid_remove pour le pack manager.
        self.trial_warning_banner.pack(fill="x", pady=(0, PAD_S))
        self.trial_warning_banner.pack_forget()  # masqué tant qu'on n'est pas en warning

        self.organize_button = primary_button(
            actions_box,
            text="🚀 Organiser",
            command=self._organize_files,
        )
        self.organize_button.pack(fill="x")

        # Séparateur
        ctk.CTkFrame(rail, height=1, fg_color=SEPARATOR_COLOR).pack(
            fill="x", padx=PAD_M, pady=PAD_S,
        )

        # ===== Cible (résumé dynamique) =====
        ctk.CTkLabel(
            rail, text="🎯 Cible", font=font_label(weight="bold"), anchor="w"
        ).pack(fill="x", padx=PAD_M, pady=(0, PAD_S))

        # Variable affichant le résumé. Sera mise à jour par _refresh_file_count
        # une fois le scan terminé (cf. Variante B point « right rail Cible »).
        self._target_summary_var = ctk.StringVar(
            value="Sélectionnez une source pour voir la cible."
        )
        ctk.CTkLabel(
            rail,
            textvariable=self._target_summary_var,
            font=font_hint(),
            text_color=HINT_COLOR,
            anchor="w",
            justify="left",
            wraplength=180,
        ).pack(fill="x", padx=PAD_M, pady=(0, PAD_M))

    def _create_actions_section(self):
        """Section actions en zone bottom slim (refonte v2.3 — Variante B).

        Désormais réduite à la progress bar uniquement (~40 px). Les boutons
        d'action sont passés dans le right rail (cf. ``_create_right_rail``).
        """
        parent = self._bottom_zone
        parent.columnconfigure(0, weight=1)

        # Progress bar + pourcentage + label sur 1 ligne (slim)
        progress_row = ctk.CTkFrame(parent, fg_color="transparent")
        progress_row.grid(row=0, column=0, sticky="ew", pady=0)
        progress_row.columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            progress_row,
            height=18,
            border_width=1,
            border_color=("gray60", "gray40"),
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, PAD_S))
        self.progress_bar.set(0)

        self.progress_pct_var = ctk.StringVar(value="0 %")
        ctk.CTkLabel(
            progress_row,
            textvariable=self.progress_pct_var,
            font=font_label(weight="bold"),
            width=44,
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(0, PAD_S))

        # Label de progression (slim — collé à la même ligne)
        self.progress_label = ctk.CTkLabel(
            progress_row,
            text="Prêt",
            font=font_label(),
            anchor="w",
            text_color=LABEL_MUTED,
            width=200,
        )
        self.progress_label.grid(row=0, column=2, sticky="e")

    # ------------------------------------------------------------------
    # Ordre des critères en mode multicouche
    # ------------------------------------------------------------------
    CRITERIA_LABELS = {
        "date": ("📅", "Date"),
        "camera": ("📷", "Appareil"),
        "location": ("🌍", "Localisation"),
    }
    CRITERIA_ENABLE_VAR = {
        "date": "organize_by_date",
        "camera": "organize_by_camera",
        "location": "organize_by_location",
    }

    def _update_criteria_visibility(self):
        """Affiche le panneau d'ordre des critères (multicouche).

        Refonte v2.3 (retour testeur 2026-05-17) : toujours visible.
        L'ordre est ignoré au runtime quand ``multilayer`` est False
        (cf. core/organizer.py), mais l'utilisateur voit en permanence
        l'ordre actuel et peut le réarranger même hors mode multicouche.
        """
        self.criteria_order_frame.pack(fill="x", padx=20, pady=(0, 6))

    def _render_criteria_order(self):
        """Recrée les lignes de l'ordre des critères.

        Plus simple qu'un drag-and-drop : on détruit puis on reconstruit les
        lignes à chaque modification. Les critères inactifs (case décochée
        au-dessus) restent visibles mais grisés pour informer l'utilisateur.
        """
        # On reconstruit à blanc — pas de réutilisation de widgets
        for child in self.criteria_rows_container.winfo_children():
            child.destroy()
        self._criteria_rows.clear()

        n = len(self._criteria_order)
        for index, key in enumerate(self._criteria_order):
            emoji, label = self.CRITERIA_LABELS[key]
            enabled = bool(getattr(self, self.CRITERIA_ENABLE_VAR[key]).get())

            row = ctk.CTkFrame(
                self.criteria_rows_container,
                fg_color=("gray90", "gray20") if enabled else ("gray80", "gray15"),
                corner_radius=6,
            )
            row.pack(fill="x", pady=2)

            text_color = None if enabled else ("gray50", "gray55")
            ctk.CTkLabel(
                row,
                text=f"{index + 1}.  {emoji}  {label}",
                font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight="bold" if enabled else "normal"),
                text_color=text_color,
                anchor="w",
                width=180,
            ).pack(side="left", padx=(10, 5), pady=4)

            if not enabled:
                ctk.CTkLabel(
                    row,
                    text="(désactivé)",
                    font=ctk.CTkFont(size=11, slant="italic"),
                    text_color=("gray50", "gray55"),
                ).pack(side="left", padx=4)

            up_btn = ctk.CTkButton(
                row,
                text="▲",
                width=30,
                height=28,
                command=lambda k=key: self._move_criterion(k, -1),
                state="disabled" if index == 0 else "normal",
                fg_color=CHECK_FG,
                hover_color=CHECK_HOVER,
            )
            up_btn.pack(side="right", padx=(2, 6), pady=3)

            down_btn = ctk.CTkButton(
                row,
                text="▼",
                width=30,
                height=28,
                command=lambda k=key: self._move_criterion(k, 1),
                state="disabled" if index == n - 1 else "normal",
                fg_color=CHECK_FG,
                hover_color=CHECK_HOVER,
            )
            down_btn.pack(side="right", padx=(2, 2), pady=3)

            self._criteria_rows[key] = (row, up_btn, down_btn)

    def _move_criterion(self, key: str, delta: int):
        """Déplace un critère d'une position dans la liste (delta = ±1).

        Bornes incluses : un noop si la nouvelle position sort de la liste.
        """
        try:
            idx = self._criteria_order.index(key)
        except ValueError:
            return
        new_idx = idx + delta
        if not (0 <= new_idx < len(self._criteria_order)):
            return
        order = self._criteria_order
        order[idx], order[new_idx] = order[new_idx], order[idx]
        self._render_criteria_order()

    # ----------------------------- GPS / Localisation -----------------------------
    # Bornes et précision du slider de distance max (km)
    MAX_DIST_MIN = 0.0
    MAX_DIST_MAX = 50.0
    MAX_DIST_FINE_STEP = 0.1  # pas 100 m via les boutons ◀ / ▶
    MAX_DIST_PRECISION = 10  # 1 / 0.1 → arrondi 100 m

    def _snap_max_distance(self, value: float) -> float:
        """Arrondit la valeur à 100 m près."""
        return round(value * self.MAX_DIST_PRECISION) / self.MAX_DIST_PRECISION

    def _on_max_distance_change(self, value):
        """Met à jour le libellé numérique du slider de distance max."""
        try:
            km = float(value)
        except (TypeError, ValueError):
            km = 0.0
        km = self._snap_max_distance(km)
        self.max_distance_label_var.set(f"{km:.1f} km")

    def _step_max_distance(self, delta: float):
        """Ajuste finement la distance max via les boutons ◀ / ▶ (±100 m)."""
        try:
            current = float(self.max_distance.get())
        except (TypeError, ValueError):
            current = 0.0
        new_val = max(self.MAX_DIST_MIN, min(self.MAX_DIST_MAX, current + delta))
        new_val = self._snap_max_distance(new_val)
        self.max_distance.set(new_val)
        self._on_max_distance_change(new_val)

    def _refresh_gps_options_visibility(self):
        """Affiche les sous-options GPS sous la case correspondante.

        Refonte v2.3 (retour testeur 2026-05-17) : les sous-options sont
        désormais TOUJOURS visibles, peu importe l'état de la checkbox
        « Par localisation GPS ». L'utilisateur voit en permanence les
        paramètres disponibles (géocodage, distance max) et peut les
        configurer même si le critère n'est pas (encore) activé.
        """
        # Toujours visible — pas de pack_forget conditionnel.
        # ``after=`` reste pour positionner sous le checkbox.
        try:
            self.gps_options_frame.pack(
                fill="x",
                padx=40,
                pady=(0, 4),
                after=self._gps_checkbox,
            )
        except (tk.TclError, AttributeError):
            # Si _gps_checkbox n'est pas encore créé, pack standard.
            self.gps_options_frame.pack(fill="x", padx=40, pady=(0, 4))

    def _refresh_camera_options_visibility(self):
        """Affiche la sous-option « Limiter aux marques » sous « Par appareil ».

        Refonte v2.3 (retour testeur 2026-05-17) : toujours visible.
        L'utilisateur peut renseigner les marques même si le critère
        principal n'est pas activé — le champ est ignoré quand
        ``organize_by_camera`` est False (cf. core/organizer.py).
        """
        # Toujours visible — plus de logique conditionnelle.
        self._camera_options_frame.pack(fill="x", padx=20, pady=(0, 4))

    def _browse_source(self):
        """Ouvre le dialogue de sélection du dossier source."""
        folder = filedialog.askdirectory(title="Sélectionner le dossier source")
        if folder:
            self.source_var.set(folder)

    def _browse_dest(self):
        """Ouvre le dialogue de sélection du dossier destination."""
        folder = filedialog.askdirectory(title="Sélectionner le dossier destination")
        if folder:
            self.dest_var.set(folder)

    def _add_source_folder(self):
        """Conservé pour compatibilité (plus de bouton + dans l'IHM, cf. W08).
        Si appelé via API, ouvre juste un askdirectory et remplace.
        """
        folder = filedialog.askdirectory(title="Sélectionner le dossier source")
        if folder:
            self.source_var.set(folder)

    def _split_sources(self) -> List[str]:
        """Refonte v5 (W06) : multi-source retirée. Retourne [source] ou []."""
        raw = self.source_var.get().strip()
        return [raw] if raw else []

    def _setup_drag_drop(self):
        """Active le drag-and-drop si tkinterdnd2 est installé (Lot Q1).

        Sans tkinterdnd2 (cas par défaut sans dépendance), la méthode
        n'a aucun effet visible : l'app reste fonctionnelle, juste sans DnD.
        """
        if not DND_AVAILABLE:
            return
        try:
            from tkinterdnd2 import DND_FILES

            for entry, var in (
                (self.source_entry, self.source_var),
                (self.dest_entry, self.dest_var),
            ):
                # NB: source_entry/dest_entry sont des CTkEntry qui exposent
                # le tkinter.Entry sous-jacent via _entry. tkinterdnd2 attache
                # le drop sur le widget tkinter natif.
                tk_widget = getattr(entry, "_entry", entry)
                tk_widget.drop_target_register(DND_FILES)

                def _on_drop(event, v=var, is_source=(var is self.source_var)):
                    # event.data peut contenir plusieurs paths séparés par ' '.
                    # Sur Windows, paths avec espaces sont entourés de {}.
                    raw = event.data
                    paths = self._parse_dnd_paths(raw)
                    folders = [p for p in paths if os.path.isdir(p)]
                    if not folders:
                        return
                    if is_source and len(folders) > 1:
                        v.set(";".join(folders))
                    else:
                        v.set(folders[0])

                tk_widget.dnd_bind("<<Drop>>", _on_drop)
            logger.debug("Drag-and-drop active sur source/dest entries")
        except Exception as exc:
            logger.warning(f"Echec setup drag-and-drop : {exc}")

    @staticmethod
    def _parse_dnd_paths(raw: str) -> List[str]:
        """Parse la string DnD (paths séparés par espace, accolades autour
        des paths avec espaces sous Windows)."""
        out, buf, in_brace = [], "", False
        for c in raw:
            if c == "{":
                in_brace = True
            elif c == "}":
                in_brace = False
                if buf:
                    out.append(buf)
                    buf = ""
            elif c == " " and not in_brace:
                if buf:
                    out.append(buf)
                    buf = ""
            else:
                buf += c
        if buf:
            out.append(buf)
        return out

    # --------------------------- Renommage Q4 ---------------------------
    def _refresh_rename_preview(self):
        """Aperçu live du template de renommage."""
        tpl = self.rename_template.get().strip()
        if not tpl:
            self.rename_preview_var.set("(aucun template — nom d'origine conservé)")
            return
        try:
            sample = SmartOrganizer._apply_rename_template(
                "IMG_0001.jpg",
                tpl,
                date_taken=datetime(2026, 5, 7, 14, 30),
                make="Sony",
                model="ILCE-7M3",
                counter=42,
            )
            self.rename_preview_var.set(f"IMG_0001.jpg → {sample}")
        except Exception as exc:
            self.rename_preview_var.set(f"⚠️ Template invalide : {exc}")

    # --------------------------- Presets Q3 ---------------------------
    def _list_preset_names(self) -> List[str]:
        try:
            names = get_config().list_presets()
        except Exception as exc:
            logger.warning(f"list_presets : {exc}")
            names = []
        return ["(aucun)"] + sorted(names)

    def _on_preset_selected(self, name: str):
        if name == "(aucun)":
            return
        try:
            data = get_config().load_preset(name)
        except Exception as exc:
            messagebox.showerror("Preset", f"Chargement échoué : {exc}")
            return
        if not data:
            return
        # Appliquer chaque clé connue
        mapping = {
            "organize_by_date": self.organize_by_date,
            "organize_by_camera": self.organize_by_camera,
            "multilayer": self.multilayer,
            "copy_not_move": self.copy_not_move,
            "date_format": self.date_format,
            "recursive": self.recursive,
            "include_images": self.include_images,
            "include_raw": self.include_raw,
            "include_videos": self.include_videos,
            "filter_date_min": self.filter_date_min,
            "filter_date_max": self.filter_date_max,
            "filter_size_min": self.filter_size_min,
            "filter_size_max": self.filter_size_max,
            "filter_rating_min": self.filter_rating_min,
            "filter_keywords": self.filter_keywords,
            "skip_if_identical": self.skip_if_identical,
            "keep_raw_jpeg_pairs": self.keep_raw_jpeg_pairs,
            "cleanup_empty_source": self.cleanup_empty_source,
            "validate_disk_space": self.validate_disk_space,
            "export_index_csv": self.export_index_csv,
            "export_index_json": self.export_index_json,
            "notify_on_finish": self.notify_on_finish,
            "rename_template": self.rename_template,
        }
        for k, var in mapping.items():
            if k in data:
                try:
                    var.set(data[k])
                except Exception:
                    pass
        if "criteria_order" in data:
            order = data["criteria_order"]
            if isinstance(order, list) and all(c in self._criteria_order for c in order):
                self._criteria_order = list(order)
                self._render_criteria_order()
        logger.info(f"Preset '{name}' charge")

    def _save_preset_dialog(self):
        """Panneau inline « Sauvegarder un preset » (refonte 2026-05-18).

        Remplace l'ancienne modale CTkToplevel par un panneau intégré
        (logo + champ Nom + récap + boutons Annuler/Enregistrer). La
        validation est faite dans la callback ``_on_save`` ; en cas de
        succès, le panneau se ferme et le status bar est mis à jour.
        """
        name_var = ctk.StringVar()
        error_var = ctk.StringVar(value="")
        recap_lines = [
            f"• Organisation : date={self.organize_by_date.get()}, "
            f"camera={self.organize_by_camera.get()}, "
            f"lieu={self.organize_by_location.get()}",
            f"• Multicouche : {self.multilayer.get()}  ·  ordre={', '.join(self._criteria_order)}",
            f"• Format date : {self.date_format.get()}",
            f"• Mode : {'COPIER' if self.copy_not_move.get() else 'DÉPLACER'}",
            f"• Récursif : {self.recursive.get()}",
            f"• Types : images={self.include_images.get()}, "
            f"raw={self.include_raw.get()}, vidéos={self.include_videos.get()}",
            f"• Filtres : date [{self.filter_date_min.get() or '—'} → "
            f"{self.filter_date_max.get() or '—'}], "
            f"taille [{self.filter_size_min.get() or '—'} → "
            f"{self.filter_size_max.get() or '—'}], "
            f"note ≥ {self.filter_rating_min.get()}",
            f"• Renommage : {self.rename_template.get() or '(nom d origine)'}",
        ]

        def build(body):
            body.columnconfigure(1, weight=1)
            body.rowconfigure(3, weight=1)
            # Champ Nom
            ctk.CTkLabel(
                body, text="Nom du preset :", font=font_label(weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=PAD_L, pady=(PAD_S, PAD_S))
            name_entry = ctk.CTkEntry(
                body, textvariable=name_var, height=BTN_H_STD,
                placeholder_text="ex : vacances-ete-2026",
            )
            name_entry.grid(row=0, column=1, sticky="ew", padx=(0, PAD_L), pady=(PAD_S, PAD_S))
            name_entry.focus_set()
            # Hint
            ctk.CTkLabel(
                body,
                text="    Caractères autorisés : lettres, chiffres, tirets, soulignés. Pas d'espace.",
                font=font_hint(), text_color=HINT_COLOR, anchor="w", justify="left",
            ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=PAD_L, pady=(0, PAD_S))
            # Erreur de validation inline (visible quand error_var non vide)
            ctk.CTkLabel(
                body, textvariable=error_var,
                text_color=("#c0392b", "#e74c3c"),
                anchor="w", justify="left", font=font_hint(),
            ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=PAD_L, pady=(0, PAD_S))
            # Récap des options
            recap_frame = ctk.CTkFrame(body)
            recap_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=PAD_L, pady=PAD_S)
            ctk.CTkLabel(
                recap_frame, text="📋 Contenu du preset",
                font=font_label(weight="bold"), anchor="w",
            ).pack(fill="x", padx=PAD_M, pady=(PAD_S, 2))
            recap_box = ctk.CTkTextbox(recap_frame, height=140, font=font_hint())
            recap_box.pack(fill="both", expand=True, padx=PAD_M, pady=(0, PAD_M))
            recap_box.insert("end", "\n".join(recap_lines))
            recap_box.configure(state="disabled")

        close_holder = {}

        def _on_save():
            n = name_var.get().strip()
            if not n:
                error_var.set("⚠️ Le nom est obligatoire.")
                return
            if any(c in n for c in r' /\:*?"<>|'):
                error_var.set("⚠️ Caractères interdits dans le nom (espace, /, \\, etc).")
                return
            error_var.set("")
            data = {
                "organize_by_date": self.organize_by_date.get(),
                "organize_by_camera": self.organize_by_camera.get(),
                "multilayer": self.multilayer.get(),
                "copy_not_move": self.copy_not_move.get(),
                "date_format": self.date_format.get(),
                "recursive": self.recursive.get(),
                "include_images": self.include_images.get(),
                "include_raw": self.include_raw.get(),
                "include_videos": self.include_videos.get(),
                "criteria_order": list(self._criteria_order),
                "filter_date_min": self.filter_date_min.get(),
                "filter_date_max": self.filter_date_max.get(),
                "filter_size_min": self.filter_size_min.get(),
                "filter_size_max": self.filter_size_max.get(),
                "filter_rating_min": self.filter_rating_min.get(),
                "filter_keywords": self.filter_keywords.get(),
                "skip_if_identical": self.skip_if_identical.get(),
                "keep_raw_jpeg_pairs": self.keep_raw_jpeg_pairs.get(),
                "cleanup_empty_source": self.cleanup_empty_source.get(),
                "validate_disk_space": self.validate_disk_space.get(),
                "export_index_csv": self.export_index_csv.get(),
                "export_index_json": self.export_index_json.get(),
                "notify_on_finish": self.notify_on_finish.get(),
                "rename_template": self.rename_template.get(),
            }
            try:
                get_config().save_preset(n, data)
                self._refresh_preset_menu(select=n)
                self.status_callback(f"Preset « {n} » enregistré.", None)
                close = close_holder.get("close")
                if close:
                    close()
            except Exception as exc:
                error_var.set(f"⚠️ Sauvegarde échouée : {exc}")

        close_holder["close"] = self._show_inline_panel(
            title="💾 Sauvegarder un preset",
            builder=build,
            footer_buttons=[
                ("Annuler", "__close__"),
                ("💾 Enregistrer", _on_save),
            ],
        )

    def _delete_preset(self):
        name = self.preset_name.get()
        if name == "(aucun)":
            return
        if not messagebox.askyesno("Suppression", f"Supprimer le preset « {name} » ?"):
            return
        try:
            get_config().delete_preset(name)
        except Exception as exc:
            messagebox.showerror("Preset", f"Suppression échouée : {exc}")
            return
        self._refresh_preset_menu()

    def _refresh_preset_menu(self, select: str = "(aucun)"):
        self._preset_menu.configure(values=self._list_preset_names())
        self.preset_name.set(select)

    # ---------------------------- Scheduler E5 ----------------------------
    def _on_schedule_toggle(self):
        """Active/désactive la planification quotidienne (Lot E5).

        Persiste dans AppConfig pour restauration au prochain démarrage et
        configure le JobScheduler. Si l'heure est invalide, on neutralise.
        """
        enabled = self.schedule_enabled.get()
        time_str = self.schedule_time.get().strip()
        cfg = get_config()
        cfg.set("schedule_enabled", enabled)
        cfg.set("schedule_time", time_str)
        # Source / destination courantes mémorisées pour le run automatique.
        cfg.set("schedule_source", self.source_var.get())
        cfg.set("schedule_destination", self.dest_var.get())
        cfg.set("schedule_preset", self.preset_name.get())
        self._scheduler.configure(enabled, time_str)
        self._refresh_schedule_status()

    def _on_schedule_time_change(self):
        """Reconfigure le scheduler quand l'utilisateur modifie l'heure."""
        cfg = get_config()
        cfg.set("schedule_time", self.schedule_time.get().strip())
        if self.schedule_enabled.get():
            self._scheduler.configure(True, self.schedule_time.get())
        self._refresh_schedule_status()

    def _refresh_schedule_status(self):
        """Met à jour le label de statut "Prochaine exécution : ..."."""
        if not self.schedule_enabled.get():
            self.schedule_status_var.set("⏸ Désactivée")
            return
        nxt = self._scheduler.get_next_run()
        if nxt is None:
            self.schedule_status_var.set("⚠️ Heure invalide (utiliser HH:MM)")
        else:
            self.schedule_status_var.set(f"⏰ Prochaine exécution : {nxt.strftime('%Y-%m-%d %H:%M')}")

    def _scheduled_run_callback(self):
        """Callback appelé par le JobScheduler à l'heure planifiée.

        Doit rester thread-safe : on délègue à l'UI thread via ``after()``
        et on n'appelle pas directement les widgets ici.
        """
        logger.info("Scheduled run triggered by JobScheduler")
        # On déclenche l'organisation avec les paramètres courants.
        # Si pas de source/dest configurés, on log juste et on saute.
        try:
            self._safe_after(0, self._organize_files)
        except (tk.TclError, RuntimeError) as exc:
            logger.warning(f"Scheduled run dispatch failed: {exc}")

    def _get_options(self) -> OrganizationOptions:
        """Retourne les options d'organisation actuelles.

        Inclut les filtres pré-traitement, les comportements avancés, le
        template de renommage et les flags d'export d'index.
        """

        # Parse dates filtre
        def _parse_date(s: str) -> Optional[datetime]:
            s = (s or "").strip()
            if not s:
                return None
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        keywords = [k.strip() for k in self.filter_keywords.get().split(",") if k.strip()]

        # Nouveaux filtres (refactor 2026-05-15) — parsing CSV / WxH
        ext_list = [
            e.strip().lstrip('.').lower()
            for e in self.filter_extensions.get().split(",") if e.strip()
        ]
        cam_list = [
            c.strip() for c in self.filter_camera_make.get().split(",") if c.strip()
        ]

        def _parse_dim(s: str) -> Optional[tuple]:
            """Parse 'WxH' / 'WXH' → (w, h) ; None si vide ou invalide."""
            s = (s or "").strip().lower()
            if not s:
                return None
            for sep in ('x', '×'):
                if sep in s:
                    parts = s.split(sep, 1)
                    try:
                        return int(parts[0]), int(parts[1])
                    except (ValueError, IndexError):
                        return None
            return None

        return OrganizationOptions(
            organize_by_date=self.organize_by_date.get(),
            organize_by_camera=self.organize_by_camera.get(),
            organize_by_location=self.organize_by_location.get(),
            use_geocoding=self.use_geocoding.get(),
            max_distance_km=self._snap_max_distance(self.max_distance.get()),
            multilayer=self.multilayer.get(),
            criteria_order=list(self._criteria_order),
            copy_not_move=self.copy_not_move.get(),
            date_format=self.date_format.get(),
            # Filtres
            date_min=_parse_date(self.filter_date_min.get()),
            date_max=_parse_date(self.filter_date_max.get()),
            size_min_bytes=_parse_size_input(self.filter_size_min.get()),
            size_max_bytes=_parse_size_input(self.filter_size_max.get()) or None,
            rating_min=self.filter_rating_min.get(),
            keywords_filter=keywords,
            # Nouveaux filtres (refactor 2026-05-15)
            extensions_filter=ext_list,
            dim_min=_parse_dim(self.filter_dim_min.get()),
            dim_max=_parse_dim(self.filter_dim_max.get()),
            camera_makes_filter=cam_list,
            gps_required=self.filter_gps_required.get(),
            orientation_filter=self.filter_orientation.get(),
            # Comportements
            skip_if_identical=self.skip_if_identical.get(),
            keep_raw_jpeg_pairs=self.keep_raw_jpeg_pairs.get(),
            cleanup_empty_source=self.cleanup_empty_source.get(),
            validate_disk_space=self.validate_disk_space.get(),
            # Renommage
            rename_template=(self.rename_template.get().strip() or None),
            # Index
            export_index_csv=self.export_index_csv.get(),
            export_index_json=self.export_index_json.get(),
            # Bursts S1 + Incremental S5
            detect_bursts=self.detect_bursts.get(),
            burst_mode=self.burst_mode.get(),
            burst_threshold_seconds=self.burst_threshold.get(),
            burst_min_count=self.burst_min_count.get(),
            burst_auto_min_seconds=self.burst_auto_min.get(),
            burst_auto_max_seconds=self.burst_auto_max.get(),
            incremental_mode=self.incremental_mode.get(),
        )

    def _get_files(self) -> List[str]:
        """Récupère la liste des fichiers à traiter sur le **dossier source**.

        Refonte v5 (W06) : multi-source avec séparateur ';' retirée.
        ``_split_sources()`` reste exposé en interne pour compat tests mais
        retourne désormais juste le contenu du champ.
        """
        src = self.source_var.get().strip()
        if not src or not os.path.isdir(src):
            return []
        return self.file_manager.list_files(
            src,
            recursive=self.recursive.get(),
            include_images=self.include_images.get(),
            include_raw=self.include_raw.get(),
            include_videos=self.include_videos.get(),
        )

    def _attach_tooltips(self):
        """Attache les info-bulles à tous les widgets clés du panneau.

        Centralisé après ``_create_ui()`` pour éviter de polluer les méthodes
        de construction. Les libellés viennent de ``tooltips_fr.ORGANIZE``.
        """
        # Champs Source/Destination
        attach_tooltip(self.source_entry, TIPS["source_entry"])
        attach_tooltip(self.dest_entry, TIPS["dest_entry"])
        attach_tooltip(self.file_count_label, TIPS["file_count"])

        # Boutons icône-only Source/Destination (audit 2026-05-15)
        if hasattr(self, "browse_source_btn"):
            attach_tooltip(self.browse_source_btn, TIPS["browse_source"])
        if hasattr(self, "browse_dest_btn"):
            attach_tooltip(self.browse_dest_btn, TIPS["browse_dest"])
        if hasattr(self, "open_dest_btn"):
            attach_tooltip(self.open_dest_btn, TIPS["open_dest"])
        if hasattr(self, "show_files_btn"):
            attach_tooltip(
                self.show_files_btn,
                "Affiche la liste détaillée des fichiers détectés (jusqu'à 500) avec les filtres actuels.",
            )
        if hasattr(self, "brand_examples_btn"):
            attach_tooltip(self.brand_examples_btn, TIPS["brand_examples_btn"])
        if hasattr(self, "filter_examples_btn"):
            attach_tooltip(self.filter_examples_btn, TIPS["filter_examples_btn"])

        # Cases / radios des critères et types
        # On cherche par nom de variable plutôt que par référence directe
        # (les cases ne sont pas toutes stockées comme attributs).
        if hasattr(self, "multilayer_switch"):
            attach_tooltip(self.multilayer_switch, TIPS["multilayer"])
        if hasattr(self, "_adv_toggle_btn"):
            attach_tooltip(self._adv_toggle_btn, TIPS["advanced_toggle"])
        if hasattr(self, "_rename_toggle_btn"):
            attach_tooltip(self._rename_toggle_btn, "Replier/déplier la section Renommage et Presets.")

        # Sliders / entrées GPS
        if hasattr(self, "max_distance_slider"):
            attach_tooltip(self.max_distance_slider, TIPS["max_distance"])

        # Renommage
        if hasattr(self, "rename_entry"):
            attach_tooltip(self.rename_entry, TIPS["rename_template"])

        # Presets
        if hasattr(self, "_preset_menu"):
            attach_tooltip(self._preset_menu, TIPS["preset_menu"])

        # Boutons d'action — zone bottom
        attach_tooltip(self.analyze_button, TIPS["btn_analyze"])
        attach_tooltip(self.preview_button, TIPS["btn_preview"])
        attach_tooltip(self.organize_button, TIPS["btn_organize"])
        attach_tooltip(self.cancel_button, TIPS["btn_cancel"])

        # Filtres avancés (parcours descendants pour trouver les Entry par
        # textvariable — évite de stocker chaque widget individuellement)
        self._attach_tooltips_to_filter_entries()

    def _attach_tooltips_to_filter_entries(self):
        """Attache les tooltips aux Entry des filtres avancés via leur var."""
        var_to_tip = {
            id(self.filter_date_min): TIPS["filter_date_min"],
            id(self.filter_date_max): TIPS["filter_date_max"],
            id(self.filter_size_min): TIPS["filter_size_min"],
            id(self.filter_size_max): TIPS["filter_size_max"],
            id(self.filter_keywords): TIPS["filter_keywords"],
        }
        for child in self._iter_descendants(self):
            try:
                var_name = child.cget("textvariable")
            except Exception:
                continue
            if not var_name:
                continue
            # Résolution de la var par nom Tcl → recherche dans nos vars
            for var_id, tip in var_to_tip.items():
                # On compare via le nom Tcl interne
                try:
                    matching = next(
                        (
                            v
                            for v in (
                                self.filter_date_min,
                                self.filter_date_max,
                                self.filter_size_min,
                                self.filter_size_max,
                                self.filter_keywords,
                            )
                            if str(v) == var_name and id(v) == var_id
                        ),
                        None,
                    )
                    if matching is not None:
                        attach_tooltip(child, tip)
                        break
                except Exception:
                    continue

    @staticmethod
    def _iter_descendants(widget):
        """Yield récursivement tous les descendants Tk d'un widget."""
        for child in widget.winfo_children():
            yield child
            yield from OrganizeFrame._iter_descendants(child)

    # ------------------------------------------------------------------
    # Panneau inline (refonte 2026-05-18) — remplace les CTkToplevel
    # ------------------------------------------------------------------
    def _show_inline_panel(self, title, builder, footer_buttons=None):
        """Affiche un panneau d'information *dans* la fenêtre principale.

        Refonte 2026-05-18 — l'utilisateur ne veut plus de nouvelles fenêtres
        (Toplevel) pour Aperçu / Organisation terminée / Save preset /
        Fichiers détectés / Exemples marques. Le panneau remplace
        temporairement le tabview interne (zone centre), avec :
          • Titre du panneau (row 0)
          • Corps construit par ``builder(body)``
          • Pied avec boutons (Fermer par défaut)

        Note : le logo PhotoOrganizer n'est PAS répété ici — il est déjà
        visible dans la barre de titre de la fenêtre principale
        (cf. retour utilisateur 2026-05-18 : « le logo est déjà rappelé
        dans file explorer en haut à gauche »).

        Args:
            title: Titre affiché en haut du panneau.
            builder: Callback ``builder(body_frame)`` qui peuple le corps.
            footer_buttons: Liste de ``(label, command)``. Si ``command`` vaut
                la sentinelle ``"__close__"`` ou ``None``, le bouton ferme le
                panneau. Si ``footer_buttons`` est ``None``, un bouton
                « Fermer » seul est ajouté.

        Returns:
            La fonction ``close`` permettant de fermer le panneau par
            programme (utile pour les actions qui valident puis ferment).
        """
        # Masquer le tabview pour libérer la zone centrale
        try:
            self._main_tabview.grid_remove()
        except (tk.TclError, AttributeError):
            pass

        # Détruire un éventuel panneau encore présent
        prev = getattr(self, "_inline_panel", None)
        if prev is not None:
            try:
                prev.destroy()
            except tk.TclError:
                pass
            self._inline_panel = None

        panel = ctk.CTkFrame(self._scroll)
        panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        self._inline_panel = panel

        # Header : titre seul, sans logo (le logo est déjà dans la barre de
        # titre Windows — retour utilisateur 2026-05-18).
        ctk.CTkLabel(
            panel,
            text=title,
            font=font_section(),
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=PAD_M)

        # Body : construit par l'appelant
        body = ctk.CTkFrame(panel, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=PAD_S, pady=PAD_S)
        try:
            builder(body)
        except Exception as exc:
            logger.warning(f"_show_inline_panel builder a echoue : {exc}")
            ctk.CTkLabel(
                body,
                text=f"Erreur d'affichage : {exc}",
                text_color=("red", "red"),
            ).pack(padx=PAD_M, pady=PAD_M)

        # Footer : boutons (au moins « Fermer »)
        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))

        def _close():
            try:
                panel.destroy()
            except tk.TclError:
                pass
            self._inline_panel = None
            try:
                self._main_tabview.grid()
            except (tk.TclError, AttributeError):
                pass

        buttons = footer_buttons if footer_buttons else [("Fermer", "__close__")]
        for label, cmd in buttons:
            real_cmd = _close if cmd in (None, "__close__") else cmd
            ctk.CTkButton(
                footer,
                text=label,
                command=real_cmd,
                height=BTN_H_STD,
            ).pack(side="right", padx=PAD_S)

        return _close

    # ------------------------------------------------------------------
    # Trial + unlock — panneau d'activation inline (pivot 2026-05-26)
    # ------------------------------------------------------------------
    def _show_unlock_panel(self):
        """Affiche le panneau d'activation (limite atteinte OU activation libre).

        Utilise ``_show_inline_panel`` pour respecter la préférence projet
        "pas de Toplevel dans l'onglet Organisation".

        Composants :
        - Bandeau d'explication (limite + ID machine)
        - Entry pour coller la clé
        - Bouton "Acheter une licence (10 €)" (ouvre le navigateur)
        - Footer : boutons "Activer" et "Fermer"

        L'activation appelle ``licensing.activate_key(...)``.
        """
        try:
            state = licensing.get_state()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"licensing.get_state a échoué : {exc}")
            state = None

        # Conteneurs externes pour partager l'entry + le label de feedback
        # entre le builder (qui crée les widgets) et le footer (qui les lit).
        ui_refs = {"entry": None, "feedback": None}

        def build(body):
            body.columnconfigure(0, weight=1)

            # Message principal
            if state is not None and state.is_blocked:
                main_text = (
                    "Tu as utilisé tes 10 tris gratuits.\n"
                    "Active une licence pour continuer en illimité (10 € à vie, 1 PC)."
                )
            else:
                main_text = (
                    "Active ta licence PhotoOrganizer pour débloquer l'usage illimité."
                )
            ctk.CTkLabel(
                body,
                text=main_text,
                font=font_label(),
                anchor="w",
                justify="left",
                wraplength=720,
            ).grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_M))

            # ID machine (utile pour le support)
            mid_short = state.machine_id_short if state else "MAC-????-????"
            ctk.CTkLabel(
                body,
                text=f"🖥️  Ton ordinateur : {mid_short}",
                font=font_hint(),
                text_color=LABEL_MUTED,
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))

            # Champ pour coller la clé
            ctk.CTkLabel(
                body,
                text="Clé de licence :",
                font=font_label(),
                anchor="w",
            ).grid(row=2, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, 0))

            entry = ctk.CTkEntry(
                body,
                placeholder_text="PROG-LIFE-...-...",
                height=BTN_H_STD,
                font=font_hint(),
            )
            entry.grid(row=3, column=0, sticky="ew", padx=PAD_M, pady=PAD_S)
            ui_refs["entry"] = entry

            # Zone de feedback (succès/erreur)
            feedback = ctk.CTkLabel(
                body,
                text="",
                font=font_hint(),
                anchor="w",
                justify="left",
                wraplength=720,
            )
            feedback.grid(row=4, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            ui_refs["feedback"] = feedback

            # Bouton "Acheter" + lien "Comment ça marche ?" (séparés du footer)
            buy_row = ctk.CTkFrame(body, fg_color="transparent")
            buy_row.grid(row=5, column=0, sticky="ew", padx=PAD_M, pady=PAD_S)
            ctk.CTkLabel(
                buy_row,
                text="Pas encore de clé ?",
                font=font_hint(),
                text_color=LABEL_MUTED,
            ).pack(side="left", padx=(0, PAD_S))
            neutral_button(
                buy_row,
                text="🛒 Acheter une licence (10 €)",
                command=self._open_purchase_page,
            ).pack(side="left")

            # Lien tertiaire "Comment ça marche ?" — ouvre docs/PRO_UNLOCK.md
            # sur GitHub via le navigateur par défaut. On utilise un CTkButton
            # sans fg_color pour qu'il ressemble à un lien.
            help_row = ctk.CTkFrame(body, fg_color="transparent")
            help_row.grid(row=6, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_S))
            help_link = ctk.CTkButton(
                help_row,
                text="ℹ️  Comment ça marche ?",
                command=self._open_help_page,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("#2b5fa1", "#6ba0e0"),
                anchor="w",
                height=BTN_H_STD,
            )
            help_link.pack(side="left")

        def do_activate():
            entry = ui_refs["entry"]
            feedback = ui_refs["feedback"]
            if entry is None or feedback is None:
                return
            key = entry.get().strip()
            if not key:
                feedback.configure(text="❌ Colle la clé reçue par email.", text_color=("red", "red"))
                return
            try:
                new_state = licensing.activate_key(key)
            except Exception as exc:  # noqa: BLE001
                # B-02 (audit 2026-06-11) : on capture toutes les exceptions
                # du validator pour afficher un message localisé ; la
                # distinction des cas se fait par isinstance ci-dessous.
                from utils.license_validator import (
                    LicenseExpiredError,
                    LicenseInvalidError,
                )
                if isinstance(exc, LicenseExpiredError):
                    msg = "❌ Cette clé a expiré."
                elif isinstance(exc, LicenseInvalidError):
                    if "bound" in str(exc).lower() or "another machine" in str(exc).lower():
                        msg = "❌ Cette clé est déjà liée à un autre ordinateur."
                    else:
                        msg = "❌ Clé invalide. Vérifie qu'aucun caractère ne manque."
                else:
                    msg = f"❌ Erreur d'activation : {exc}"
                feedback.configure(text=msg, text_color=("red", "red"))
                logger.info(f"Activation refusée : {exc}")
                return

            # Succès
            feedback.configure(
                text=f"✅ Activée pour cet ordinateur ({new_state.machine_id_short}). Merci !",
                text_color=("green", "lightgreen"),
            )
            # Rafraîchir le badge global
            self._refresh_license_badge()

        self._show_inline_panel(
            title="🔓 Activer PhotoOrganizer",
            builder=build,
            footer_buttons=[
                ("Activer", do_activate),
                ("Fermer", "__close__"),
            ],
        )

    def _open_purchase_page(self):
        """Ouvre la page d'achat Lemon Squeezy dans le navigateur."""
        import webbrowser

        url = "https://photoorganizer.lemonsqueezy.com"
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Impossible d'ouvrir le navigateur : {exc}")
            messagebox.showinfo(
                "Acheter une licence",
                f"Va sur :\n{url}\n\nPour 10 € à vie sur un PC.",
            )

    def _open_help_page(self):
        """Ouvre la page d'explication du modèle trial+unlock.

        Lien GitHub direct vers ``docs/PRO_UNLOCK.md`` (page utilisateur
        courte, accessible publiquement, versionnée avec le projet).
        """
        import webbrowser

        url = "https://github.com/Kiriiaq/PhotoOrganizer/blob/main/docs/PRO_UNLOCK.md"
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Impossible d'ouvrir le navigateur : {exc}")
            messagebox.showinfo(
                "Comment ça marche ?",
                f"Va sur :\n{url}",
            )

    def _refresh_license_badge(self):
        """Demande à l'app parent de rafraîchir le badge d'état licence.

        Méthode tolérante : si l'app n'expose pas ``refresh_license_badge()``
        (ex. dans un contexte de test), on log et on continue. On rafraîchit
        AUSSI le bandeau warning local (effet de bord cohérent).
        """
        # Bandeau warning local (toujours rafraîchi, même si pas d'app parent)
        self._refresh_trial_warning_banner()

        try:
            top = self.winfo_toplevel()
        except tk.TclError:
            return
        refresher = getattr(top, "refresh_license_badge", None)
        if callable(refresher):
            try:
                refresher()
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"refresh_license_badge: {exc}")

    def _refresh_trial_warning_banner(self):
        """Affiche ou masque le bandeau jaune au-dessus du bouton Organiser.

        Visible uniquement si :
        - aucune licence active, ET
        - le compteur de tris est à 8 (avant-dernier) ou 9 (dernier).

        Sinon (essai normal, déjà bloqué, ou licence active), le bandeau est
        masqué via ``pack_forget()``.
        """
        banner = getattr(self, "trial_warning_banner", None)
        if banner is None:
            return  # widget pas encore créé (cas d'appel précoce)

        try:
            state = licensing.get_state()
        except Exception as exc:  # noqa: BLE001 — l'UI ne doit jamais crash sur la crypto
            logger.warning(f"_refresh_trial_warning_banner: get_state a échoué : {exc}")
            try:
                banner.pack_forget()
            except tk.TclError:
                pass
            return

        if state.has_valid_license or not state.should_warn:
            try:
                banner.pack_forget()
            except tk.TclError:
                pass
            return

        # Compteur dans WARNING_THRESHOLDS = (8, 9)
        if state.trial_count == licensing.TRIAL_LIMIT - 1:  # 9
            text = (
                f"⚠️  Dernier tri gratuit avant blocage  ({state.trial_remaining}/{licensing.TRIAL_LIMIT})"
            )
        else:  # 8
            text = (
                f"⚠️  Avant-dernier tri gratuit  ({state.trial_remaining}/{licensing.TRIAL_LIMIT})"
            )

        try:
            banner.configure(text=text)
            # Le label doit être réinséré DEVANT (au-dessus de) le bouton
            # Organiser. Comme tous les widgets utilisent .pack() dans
            # actions_box, on repack devant organize_button.
            banner.pack(fill="x", pady=(0, PAD_S), before=self.organize_button)
        except tk.TclError as exc:
            logger.debug(f"trial_warning_banner refresh failed: {exc}")

    def _show_files_list(self):
        """Liste les fichiers détectés (T-030..T-033) — panneau inline.

        Refonte 2026-05-18 : remplace la modale CTkToplevel par un panneau
        intégré qui remplace temporairement le tabview interne. Affiche
        jusqu'à 500 chemins ; au-delà, mention « … et N de plus ».
        """
        files = self._get_files()

        def build(body):
            body.columnconfigure(0, weight=1)
            body.rowconfigure(0, weight=1)
            if not files:
                ctk.CTkLabel(
                    body,
                    text="Aucun fichier trouvé.",
                    text_color=LABEL_MUTED,
                ).grid(row=0, column=0, padx=PAD_L, pady=PAD_M, sticky="w")
                return
            box = ctk.CTkTextbox(body, font=font_hint())
            box.grid(row=0, column=0, sticky="nsew", padx=PAD_L, pady=PAD_S)
            for i, f in enumerate(files[:500], 1):
                box.insert("end", f"{i:>4}.  {f}\n")
            if len(files) > 500:
                box.insert("end", f"\n… et {len(files) - 500} fichier(s) supplémentaire(s)")
            box.configure(state="disabled")

        self._show_inline_panel(
            title=f"📋 {len(files)} fichier(s) détecté(s) avec les filtres actuels",
            builder=build,
        )

    def _refresh_file_count(self):
        """Met à jour le compteur enrichi de fichiers détectés (v2.2 étape 4).

        Refonte 2026-05-15 : le compteur affiche désormais des stats EXIF
        agrégées sur un échantillon des fichiers détectés :
          • Plage de dates (DateTimeOriginal min/max)
          • Nombre de caméras distinctes (EXIF Make)
          • Pourcentage de photos avec GPS

        Pour les dossiers volumineux, le scan EXIF complet peut prendre
        plusieurs secondes. Stratégie :
          ≤ 200 fichiers : scan complet
          > 200          : échantillon stratifié (50 premiers + 50 milieu
                           + 50 derniers, total ~150 fichiers)

        Affichage en 2 lignes :
          📂 D:/Photos/2026 — 1247 fichier(s) détecté(s)
          📅 2024-06-01 → 2024-12-31  ·  📷 8 caméras  ·  🌍 78 % avec GPS
        """
        source = self.source_var.get().strip()
        if not source:
            self.file_count_var.set("Aucun dossier source sélectionné.")
            return
        if not os.path.isdir(source):
            self.file_count_var.set(f"Dossier introuvable : {source}")
            return

        # Affichage immédiat du « comptage en cours », puis comptage en thread
        self.file_count_var.set(f"Comptage des fichiers dans {os.path.basename(source)}…")

        def count_thread():
            # D-06 (audit 2026-05-14) : sortir immédiatement si le frame a
            # été détruit pendant que le thread démarrait.
            if getattr(self, "_destroyed", False):
                return
            try:
                files = self._get_files()
                if getattr(self, "_destroyed", False):
                    return
                count = len(files)
                shown = source if len(source) <= 70 else "…" + source[-67:]
                if count == 0:
                    msg = f"📂 {shown} — aucun fichier détecté avec les filtres actuels."
                    self._safe_after(0, lambda m=msg: self.file_count_var.set(m))
                    return

                # Ligne 1 : compteur basique (affichée immédiatement)
                line1 = f"📂 {shown} — {count} fichier(s) détecté(s)"
                self._safe_after(0, lambda m=line1: self.file_count_var.set(m))

                # Ligne 2 : stats EXIF (calculées sur échantillon)
                stats = self._compute_exif_stats(files)
                if stats is None:
                    return  # frame détruit pendant le scan
                if not stats:
                    return  # pas de stats utiles (pas d'EXIF lisibles)

                line2 = (
                    f"📅 {stats['date_range']}  ·  "
                    f"📷 {stats['cameras_text']}  ·  "
                    f"🌍 {stats['gps_pct']} % avec GPS"
                )
                msg = f"{line1}\n{line2}"
                self._safe_after(0, lambda m=msg: self.file_count_var.set(m))
            except RuntimeError:
                # Tk mainloop disparue (frame détruit pendant un get).
                return
            except (OSError, ValueError) as exc:
                err = str(exc)
                logger.warning(f"Comptage echoue: {err}")
                self._safe_after(0, lambda m=err: self.file_count_var.set(f"Erreur de comptage : {m}"))

        threading.Thread(target=count_thread, daemon=True).start()

    def _compute_exif_stats(self, files: List[str]) -> Optional[dict]:
        """Calcule date_range / cameras / gps_pct sur un échantillon.

        ≤ 200 fichiers : scan complet
        > 200          : 50 premiers + 50 milieu + 50 derniers

        Retourne dict {date_range, cameras_text, gps_pct} ou None si
        frame détruit, ou {} si pas d'EXIF lisible.
        """
        from core.metadata import extract_date, get_camera_info, get_exif_data, get_gps_coordinates

        n = len(files)
        if n <= 200:
            sample = files
        else:
            third = 50
            mid = n // 2
            sample = files[:third] + files[mid : mid + third] + files[-third:]

        dates = []
        cameras = set()
        gps_count = 0
        scanned = 0

        for fp in sample:
            if getattr(self, "_destroyed", False):
                return None
            try:
                exif = get_exif_data(fp)
                d = extract_date(fp, exif)
                if d is not None:
                    dates.append(d)
                make, model = get_camera_info(exif, fp)
                if make and make != "Unknown":
                    cameras.add(f"{make} {model}".strip())
                lat, lon = get_gps_coordinates(fp)
                if lat is not None and lon is not None:
                    gps_count += 1
                scanned += 1
            except Exception:
                continue

        if scanned == 0:
            return {}

        # Date range — affiche min → max au format YYYY-MM-DD
        if dates:
            date_range = f"{min(dates).strftime('%Y-%m-%d')} → {max(dates).strftime('%Y-%m-%d')}"
        else:
            date_range = "dates inconnues"

        # Caméras — nombre + liste tronquée si beaucoup
        if not cameras:
            cameras_text = "appareil inconnu"
        elif len(cameras) == 1:
            cameras_text = next(iter(cameras))
        else:
            cameras_text = f"{len(cameras)} caméras"

        gps_pct = int(round(gps_count / scanned * 100))

        return {
            "date_range": date_range,
            "cameras_text": cameras_text,
            "gps_pct": gps_pct,
            "scanned": scanned,
            "sampled": scanned < n,
        }

    # ------------------------------------------------------------------
    # Exemples de marques — bouton 💡 (refonte 2026-05-18)
    # ------------------------------------------------------------------
    # Marques courantes ordonnées par diffusion grand public. L'utilisateur
    # peut en cliquer une dans le panneau pour l'ajouter au champ
    # ``filter_camera_make``.
    COMMON_CAMERA_MAKES = (
        "Apple", "Canon", "DJI", "Fujifilm", "GoPro", "Huawei",
        "Leica", "Nikon", "Olympus", "Panasonic", "Pentax", "Ricoh",
        "Samsung", "Sigma", "Sony", "Xiaomi",
    )

    def _detect_camera_makes(self) -> List[str]:
        """Détecte les marques EXIF (`Make`) dans un échantillon de la source.

        Scanne au plus 50 fichiers pour rester rapide. Retourne la liste
        triée des marques uniques rencontrées. Liste vide si aucun dossier
        source ou aucun fichier EXIF lisible.
        """
        if not self.source_var.get().strip():
            return []
        try:
            files = self._get_files()
        except Exception as exc:
            logger.debug(f"_detect_camera_makes _get_files : {exc}")
            return []
        if not files:
            return []
        sample = files[:50]
        makes: set = set()
        for fp in sample:
            try:
                exif = get_exif_data(fp)
                make, _model = get_camera_info(exif, fp)
                if make and make != "Unknown":
                    makes.add(make.strip())
            except Exception:
                continue
        return sorted(makes)

    def _show_brand_examples_panel(self):
        """Panneau inline « Exemples de marques » (refonte 2026-05-18).

        Liste les marques courantes + celles détectées dans la source. Un
        clic sur une marque l'ajoute au champ « Limiter aux marques »
        (déduplication automatique).
        """
        detected = self._detect_camera_makes()
        current_var = self.filter_camera_make  # alias pratique

        def add_make(m: str):
            current = current_var.get().strip()
            existing = [x.strip() for x in current.split(",") if x.strip()]
            if m in existing:
                return
            existing.append(m)
            current_var.set(",".join(existing))

        def clear_field():
            current_var.set("")

        def build(body):
            body.columnconfigure(0, weight=1)

            ctk.CTkLabel(
                body,
                text="Cliquez sur une marque pour l'ajouter au champ « Limiter aux marques ».\n"
                     "Les marques sont ajoutées en CSV — laissez vide pour tout inclure.",
                font=font_hint(), text_color=HINT_COLOR, anchor="w", justify="left",
            ).grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_M))

            row_idx = 1

            # Section : marques détectées dans la source (si dossier choisi)
            if detected:
                ctk.CTkLabel(
                    body,
                    text=f"📷 Détectées dans la source ({len(detected)})",
                    font=font_label(weight="bold"), anchor="w",
                ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))
                row_idx += 1
                detected_frame = ctk.CTkFrame(body, fg_color="transparent")
                detected_frame.grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
                cols = 4
                for c in range(cols):
                    detected_frame.columnconfigure(c, weight=1)
                for i, m in enumerate(detected):
                    r, c = i // cols, i % cols
                    ctk.CTkButton(
                        detected_frame, text=m, height=BTN_H_STD,
                        command=lambda mm=m: add_make(mm),
                    ).grid(row=r, column=c, padx=PAD_S, pady=PAD_S, sticky="ew")
                row_idx += 1
            else:
                ctk.CTkLabel(
                    body,
                    text="(Aucune marque détectée — sélectionnez d'abord un dossier source.)",
                    font=font_hint(), text_color=HINT_COLOR, anchor="w", justify="left",
                ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
                row_idx += 1

            # Section : marques courantes (toujours visible)
            ctk.CTkLabel(
                body, text="📦 Marques courantes",
                font=font_label(weight="bold"), anchor="w",
            ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))
            row_idx += 1
            common_frame = ctk.CTkFrame(body, fg_color="transparent")
            common_frame.grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            cols = 4
            for c in range(cols):
                common_frame.columnconfigure(c, weight=1)
            for i, m in enumerate(self.COMMON_CAMERA_MAKES):
                r, c = i // cols, i % cols
                ctk.CTkButton(
                    common_frame, text=m, height=BTN_H_STD,
                    command=lambda mm=m: add_make(mm),
                ).grid(row=r, column=c, padx=PAD_S, pady=PAD_S, sticky="ew")
            row_idx += 1

            # Récap : valeur actuelle du champ
            ctk.CTkLabel(
                body, text="✏️ Champ actuel",
                font=font_label(weight="bold"), anchor="w",
            ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))
            row_idx += 1
            value_row = ctk.CTkFrame(body, fg_color="transparent")
            value_row.grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            value_row.columnconfigure(0, weight=1)
            ctk.CTkLabel(
                value_row, textvariable=current_var,
                font=font_hint(), anchor="w", justify="left", wraplength=520,
            ).grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                value_row, text="🗑 Vider", width=80, height=BTN_H_STD,
                command=clear_field,
            ).grid(row=0, column=1, padx=(PAD_S, 0))

        self._show_inline_panel(
            title="💡 Exemples de marques (cliquer pour ajouter)",
            builder=build,
        )

    # ------------------------------------------------------------------
    # Exemples de filtres — bouton 💡 onglet Filtrer (refonte 2026-05-19)
    # ------------------------------------------------------------------
    # Listes de valeurs standards pour les filtres non personnels. Les
    # constantes sont des tuples (immuables) pour rester triables et
    # testables. Date et taille sont volontairement absentes car propres
    # à chaque utilisateur.
    COMMON_KEYWORDS = (
        "animaux", "anniversaire", "architecture", "concert", "famille",
        "fête", "mariage", "montagne", "nature", "noël", "nuit", "paysage",
        "plage", "portrait", "ski", "sport", "ville", "vacances", "voyage",
    )
    COMMON_EXTENSIONS_IMAGES = (
        "jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp", "heic", "heif",
    )
    COMMON_EXTENSIONS_RAW = (
        "arw", "cr2", "cr3", "dng", "nef", "orf", "pef", "raf", "rw2", "srw",
    )
    COMMON_EXTENSIONS_VIDEOS = (
        "mp4", "mov", "avi", "mkv", "m4v", "mpg", "mpeg", "webm",
    )
    # (libellé, valeur WxH) — du plus petit au plus grand
    COMMON_DIMENSIONS = (
        ("SD (640×480)",          "640x480"),
        ("VGA (800×600)",         "800x600"),
        ("HD (1280×720)",         "1280x720"),
        ("Full HD (1920×1080)",   "1920x1080"),
        ("QHD/2K (2560×1440)",    "2560x1440"),
        ("4K UHD (3840×2160)",    "3840x2160"),
        ("6K (6144×3160)",        "6144x3160"),
        ("8K UHD (7680×4320)",    "7680x4320"),
    )
    # (libellé affiché, valeur stockée)
    COMMON_ORIENTATIONS = (
        ("Toutes",   "any"),
        ("Paysage",  "landscape"),
        ("Portrait", "portrait"),
        ("Carré",    "square"),
    )

    def _show_filter_examples_panel(self):
        """Panneau intégré « Exemples de filtres » (refonte 2026-05-19).

        Propose des valeurs standards pour les filtres non personnels :
        - Mots-clés EXIF/XMP courants (CSV cumulatif)
        - Extensions image / RAW / vidéos (CSV cumulatif)
        - Dimensions courantes (Full HD, 4K, etc.) → applicable à
          ``filter_dim_min`` ou ``filter_dim_max`` au choix
        - Orientation (toutes / paysage / portrait / carré)
        - Note minimale (0 à 5)

        La date et la taille en octets sont volontairement absentes : ce sont
        des valeurs propres à chaque utilisateur (cf. consigne 2026-05-19).
        """
        # Helpers de manipulation CSV (ajout déduplicaté / clear)
        def csv_add(var: ctk.StringVar, value: str):
            current = var.get().strip()
            existing = [x.strip() for x in current.split(",") if x.strip()]
            if value in existing:
                return
            existing.append(value)
            var.set(",".join(existing))

        def csv_clear(var: ctk.StringVar):
            var.set("")

        def build(body):
            body.columnconfigure(0, weight=1)

            ctk.CTkLabel(
                body,
                text="Cliquez une valeur pour l'ajouter au champ correspondant.\n"
                     "Les CSV s'enrichissent (déduplication automatique). 🗑 vide le champ.",
                font=font_hint(), text_color=HINT_COLOR,
                anchor="w", justify="left",
            ).grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_M))

            row_idx = 1

            # ====== Section : Mots-clés ======
            row_idx = self._build_filter_section_csv(
                body, row_idx,
                title="🏷️ Mots-clés courants",
                var=self.filter_keywords,
                items=self.COMMON_KEYWORDS,
                add_fn=csv_add, clear_fn=csv_clear,
                cols=5,
            )

            # ====== Section : Extensions images ======
            row_idx = self._build_filter_section_csv(
                body, row_idx,
                title="🖼️ Extensions — images standards",
                var=self.filter_extensions,
                items=self.COMMON_EXTENSIONS_IMAGES,
                add_fn=csv_add, clear_fn=csv_clear,
                cols=5,
            )

            # ====== Section : Extensions RAW ======
            row_idx = self._build_filter_section_csv(
                body, row_idx,
                title="📷 Extensions — RAW (formats bruts d'appareils)",
                var=self.filter_extensions,
                items=self.COMMON_EXTENSIONS_RAW,
                add_fn=csv_add, clear_fn=csv_clear,
                cols=5, show_value=False,  # même champ que ci-dessus
            )

            # ====== Section : Extensions vidéos ======
            row_idx = self._build_filter_section_csv(
                body, row_idx,
                title="🎬 Extensions — vidéos",
                var=self.filter_extensions,
                items=self.COMMON_EXTENSIONS_VIDEOS,
                add_fn=csv_add, clear_fn=csv_clear,
                cols=5, show_value=False,
            )

            # ====== Section : Dimensions ======
            ctk.CTkLabel(
                body, text="📐 Dimensions courantes",
                font=font_label(weight="bold"), anchor="w",
            ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))
            row_idx += 1
            ctk.CTkLabel(
                body,
                text="Pour chaque dimension, cliquez « min » pour la borne basse ou « max » pour la borne haute.",
                font=font_hint(), text_color=HINT_COLOR,
                anchor="w", justify="left",
            ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_S))
            row_idx += 1
            dim_frame = ctk.CTkFrame(body, fg_color="transparent")
            dim_frame.grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            dim_frame.columnconfigure(0, weight=1)
            for r, (label, value) in enumerate(self.COMMON_DIMENSIONS):
                ctk.CTkLabel(
                    dim_frame, text=label, anchor="w", font=font_hint(),
                ).grid(row=r, column=0, sticky="ew", padx=PAD_S, pady=2)
                ctk.CTkButton(
                    dim_frame, text="↧ min", width=80, height=BTN_H_STD,
                    command=lambda v=value: self.filter_dim_min.set(v),
                ).grid(row=r, column=1, padx=PAD_S, pady=2)
                ctk.CTkButton(
                    dim_frame, text="↥ max", width=80, height=BTN_H_STD,
                    command=lambda v=value: self.filter_dim_max.set(v),
                ).grid(row=r, column=2, padx=PAD_S, pady=2)
            # Récap valeurs courantes des champs Dim min/max
            dim_recap = ctk.CTkFrame(body, fg_color="transparent")
            dim_recap.grid(row=row_idx + 1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            dim_recap.columnconfigure(1, weight=1)
            ctk.CTkLabel(dim_recap, text="Dim. min :", font=font_label()).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                dim_recap, textvariable=self.filter_dim_min,
                font=font_hint(), anchor="w",
            ).grid(row=0, column=1, sticky="ew", padx=PAD_S)
            ctk.CTkButton(
                dim_recap, text="🗑", width=40, height=BTN_H_STD,
                command=lambda: self.filter_dim_min.set(""),
            ).grid(row=0, column=2)
            ctk.CTkLabel(dim_recap, text="Dim. max :", font=font_label()).grid(row=1, column=0, sticky="w", pady=(PAD_S, 0))
            ctk.CTkLabel(
                dim_recap, textvariable=self.filter_dim_max,
                font=font_hint(), anchor="w",
            ).grid(row=1, column=1, sticky="ew", padx=PAD_S, pady=(PAD_S, 0))
            ctk.CTkButton(
                dim_recap, text="🗑", width=40, height=BTN_H_STD,
                command=lambda: self.filter_dim_max.set(""),
            ).grid(row=1, column=2, pady=(PAD_S, 0))
            row_idx += 2

            # ====== Section : Orientation ======
            ctk.CTkLabel(
                body, text="📐 Orientation",
                font=font_label(weight="bold"), anchor="w",
            ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))
            row_idx += 1
            ori_frame = ctk.CTkFrame(body, fg_color="transparent")
            ori_frame.grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            for i, (label, value) in enumerate(self.COMMON_ORIENTATIONS):
                ori_frame.columnconfigure(i, weight=1)
                ctk.CTkButton(
                    ori_frame, text=label, height=BTN_H_STD,
                    command=lambda v=value: self.filter_orientation.set(v),
                ).grid(row=0, column=i, padx=PAD_S, pady=PAD_S, sticky="ew")
            ctk.CTkLabel(
                body, text="Valeur courante :", font=font_label(),
            ).grid(row=row_idx + 1, column=0, sticky="w", padx=PAD_M, pady=(0, 0))
            ctk.CTkLabel(
                body, textvariable=self.filter_orientation,
                font=font_hint(), anchor="w",
            ).grid(row=row_idx + 2, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            row_idx += 3

            # ====== Section : Note ======
            ctk.CTkLabel(
                body, text="⭐ Note minimale (0 = pas de filtre, 5 = uniquement les meilleures)",
                font=font_label(weight="bold"), anchor="w",
            ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))
            row_idx += 1
            rating_frame = ctk.CTkFrame(body, fg_color="transparent")
            rating_frame.grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            for i in range(6):
                rating_frame.columnconfigure(i, weight=1)
                ctk.CTkButton(
                    rating_frame,
                    text=("0 (toutes)" if i == 0 else "★" * i),
                    height=BTN_H_STD,
                    command=lambda n=i: self.filter_rating_min.set(n),
                ).grid(row=0, column=i, padx=PAD_S, pady=PAD_S, sticky="ew")
            row_idx += 1

        self._show_inline_panel(
            title="💡 Exemples de filtres (cliquer pour appliquer)",
            builder=build,
        )

    def _build_filter_section_csv(self, body, row_idx, *, title, var, items,
                                    add_fn, clear_fn, cols=5, show_value=True):
        """Construit une section « clic = ajout au CSV » dans le panneau filtres.

        Args:
            body: frame parent.
            row_idx: ligne grid de départ.
            title: titre de la section (avec emoji).
            var: ``ctk.StringVar`` à mettre à jour.
            items: itérable de valeurs (str) à proposer en boutons.
            add_fn: callback ``add_fn(var, value)`` qui ajoute en CSV.
            clear_fn: callback ``clear_fn(var)`` qui vide le champ.
            cols: nombre de colonnes pour la grille de boutons.
            show_value: afficher le récap « Champ actuel » sous la section.

        Returns:
            Nouvelle valeur de ``row_idx`` après la section.
        """
        ctk.CTkLabel(
            body, text=title,
            font=font_label(weight="bold"), anchor="w",
        ).grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))
        row_idx += 1
        chips = ctk.CTkFrame(body, fg_color="transparent")
        chips.grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_S))
        for c in range(cols):
            chips.columnconfigure(c, weight=1)
        for i, item in enumerate(items):
            r, c = i // cols, i % cols
            ctk.CTkButton(
                chips, text=item, height=BTN_H_STD,
                command=lambda v=var, val=item: add_fn(v, val),
            ).grid(row=r, column=c, padx=PAD_S, pady=2, sticky="ew")
        row_idx += 1
        if show_value:
            value_row = ctk.CTkFrame(body, fg_color="transparent")
            value_row.grid(row=row_idx, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            value_row.columnconfigure(1, weight=1)
            ctk.CTkLabel(
                value_row, text="Champ actuel :", font=font_label(),
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                value_row, textvariable=var,
                font=font_hint(), anchor="w", justify="left", wraplength=480,
            ).grid(row=0, column=1, sticky="ew", padx=PAD_S)
            ctk.CTkButton(
                value_row, text="🗑 Vider", width=80, height=BTN_H_STD,
                command=lambda v=var: clear_fn(v),
            ).grid(row=0, column=2)
            row_idx += 1
        return row_idx

    def _analyze_files(self):
        """Analyse les fichiers du dossier source."""
        # D-01 (audit 2026-05-14) : pas de double-lancement pendant qu'une
        # opération tourne, et message clair si annulation en cours.
        if getattr(self, "_operation_running", False):
            if getattr(self, "_cancel_requested", False):
                messagebox.showinfo(
                    "Annulation en cours",
                    "L'opération est en cours d'annulation.\nPatientez quelques secondes avant de relancer.",
                )
            else:
                logger.debug("Analyse déjà en cours, ignore clic redondant")
            return

        source = self.source_var.get()
        if not source:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier source.")
            return

        if not os.path.isdir(source):
            messagebox.showerror("Erreur", "Le dossier source n'existe pas.")
            return

        # Reset cancel flag avant de lancer une nouvelle opération
        self._cancel_requested = False

        def analyze():
            # B-03 (audit 2026-06-11) : tout le corps du worker est sous
            # try/finally — sans cela, une exception précoce (ex. dossier
            # devenu inaccessible dans _get_files) laissait
            # _operation_running=True et les boutons morts jusqu'au
            # redémarrage de l'app. Même pattern que duplicates_frame.
            self._operation_running = True
            self._set_buttons_state(False)
            try:
                files = self._get_files()
                total = len(files)

                if total == 0:
                    self._update_progress("Aucun fichier trouvé", 0)
                    return

                # Statistiques
                stats = {"total": total, "with_date": 0, "with_camera": 0, "with_gps": 0, "by_year": {}, "by_camera": {}}

                for i, file_path in enumerate(files):
                    if self._cancel_requested:
                        break

                    self._update_progress(f"Analyse de {os.path.basename(file_path)} ({i + 1}/{total})", (i + 1) / total)

                    try:
                        exif_data = get_exif_data(file_path)
                        date = extract_date(file_path, exif_data)
                        make, model = get_camera_info(exif_data, file_path)
                        gps = get_gps_coordinates(file_path)

                        if date:
                            stats["with_date"] += 1
                            year = date.year
                            stats["by_year"][year] = stats["by_year"].get(year, 0) + 1

                        if make != "Unknown":
                            stats["with_camera"] += 1
                            camera = f"{make} {model}"
                            stats["by_camera"][camera] = stats["by_camera"].get(camera, 0) + 1

                        if gps[0] is not None:
                            stats["with_gps"] += 1

                    except (OSError, ValueError) as exc:
                        logger.warning(f"Analyse echouee pour {file_path}: {exc}")

                self._show_analysis_results(stats)
            except Exception as exc:  # noqa: BLE001 — le worker ne doit jamais mourir muet
                err_msg = str(exc)
                logger.exception("Analyse échouée")
                self._update_progress(f"Erreur : {err_msg}", 0)
                self._safe_after(0, lambda m=err_msg: messagebox.showerror("Erreur", m))
            finally:
                self._operation_running = False
                self._set_buttons_state(True)

        thread = threading.Thread(target=analyze, daemon=True)
        thread.start()

    def _organize_files(self):
        """Lance l'organisation des fichiers.

        W60 (retour testeur 2026-05-13) : garde anti-double-clic + après une
        annulation l'utilisateur doit pouvoir relancer immédiatement. On
        reset explicitement les flags d'état au début de chaque lancement.

        D-01 (audit 2026-05-14) : si une annulation est en cours, le worker
        n'a pas encore fini de sortir proprement. On informe l'utilisateur
        avec un message clair plutôt qu'un no-op silencieux.
        """
        # Garde anti-double-clic / relance immédiate post-cancel
        if getattr(self, "_operation_running", False):
            if getattr(self, "_cancel_requested", False):
                # Annulation en cours mais worker pas encore sorti.
                messagebox.showinfo(
                    "Annulation en cours",
                    "L'opération est en cours d'annulation.\nPatientez quelques secondes avant de relancer.",
                )
            else:
                logger.debug("Org déjà en cours, ignore clic redondant")
            return

        # Reset PROACTIF — si l'utilisateur avait annulé puis le bouton n'a
        # pas été correctement remis (race condition), on garantit ici un
        # état propre avant de relancer.
        self._cancel_requested = False
        self._current_organizer = None

        source = self.source_var.get()
        dest = self.dest_var.get()

        if not source:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier source.")
            return
        if not dest:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier destination.")
            return
        if not os.path.isdir(source):
            messagebox.showerror("Erreur", "Le dossier source n'existe pas.")
            return

        # ----------------------------------------------------------------
        # Hook trial + unlock (pivot 2026-05-26)
        # ----------------------------------------------------------------
        # Si l'utilisateur a consommé ses 10 tris gratuits et n'a pas de
        # licence active sur ce PC, on ouvre le modal d'activation au lieu
        # de lancer le tri. Sinon, on continue normalement (et on affiche
        # un warning dans la confirmation aux seuils 8/9).
        try:
            allowed, lic_state = licensing.can_organize_now()
        except Exception as exc:  # noqa: BLE001 — un crash crypto ne doit jamais bloquer le tri en dev
            logger.warning(f"licensing.can_organize_now a échoué : {exc} — on autorise par défaut")
            allowed, lic_state = True, None

        if not allowed:
            self._show_unlock_panel()
            return

        # Confirmation
        action = "copier" if self.copy_not_move.get() else "déplacer"
        confirm_msg = f"Voulez-vous {action} les fichiers de:\n{source}\nvers:\n{dest}?"
        if lic_state is not None and lic_state.should_warn:
            if lic_state.trial_count == licensing.TRIAL_LIMIT - 1:
                confirm_msg = (
                    "⚠️ Dernier tri gratuit avant blocage.\n"
                    "Une fois ce tri terminé, une licence sera nécessaire pour continuer.\n\n"
                    + confirm_msg
                )
            else:  # seuil 8 = TRIAL_LIMIT - 2
                confirm_msg = (
                    f"⚠️ Avant-dernier tri gratuit (il en restera {lic_state.trial_remaining - 1} après).\n\n"
                    + confirm_msg
                )
        if not messagebox.askyesno("Confirmation", confirm_msg):
            return

        def organize():
            # B-03 (audit 2026-06-11) : tout le corps du worker est sous
            # try/except/finally — une exception précoce (_get_files,
            # _get_options…) laissait _operation_running=True et les
            # boutons morts jusqu'au redémarrage de l'app.
            self._operation_running = True
            self._cancel_requested = False
            self._set_buttons_state(False)
            try:
                files = self._get_files()
                total = len(files)

                if total == 0:
                    self._update_progress("Aucun fichier trouvé", 0)
                    return

                # Créer le dossier de destination
                os.makedirs(dest, exist_ok=True)

                # Organiser avec le FileManager partagé : la session et l'historique
                # seront ainsi visibles dans l'onglet Historique.
                organizer = SmartOrganizer(file_manager=self.file_manager)
                self._current_organizer = organizer
                options = self._get_options()

                def progress_callback(current, total_files, message):
                    self._update_progress(
                        f"Organisation : {current}/{total_files} — {message}",
                        current / total_files if total_files else 0.0,
                    )

                try:
                    result = organizer.organize(files, dest, options, progress_callback)
                finally:
                    self._current_organizer = None

                # ------------------------------------------------------------
                # Hook trial : incrémenter UNIQUEMENT après succès, pas après
                # annulation. Le compteur ne sert à rien si une licence est
                # active (licensing.record_successful_organize gère ce cas).
                # ------------------------------------------------------------
                # B-01 (audit 2026-06-11) : le champ s'appelle `processed` —
                # `result.success` n'existe pas et tuait le worker en silence.
                if not self._cancel_requested and result.processed > 0:
                    try:
                        licensing.record_successful_organize()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"Impossible d'enregistrer l'usage : {exc}")
                    # Rafraîchit le badge global si l'app expose cette méthode.
                    self._safe_after(0, self._refresh_license_badge)

                # Afficher les résultats
                self._safe_after(0, lambda: self._show_organization_results(result))
            except Exception as exc:  # noqa: BLE001 — le worker ne doit jamais mourir muet
                err_msg = str(exc)
                logger.exception("Organisation échouée")
                self._update_progress(f"Erreur : {err_msg}", 0)
                self._safe_after(0, lambda m=err_msg: messagebox.showerror("Erreur", m))
            finally:
                self._operation_running = False
                self._set_buttons_state(True)

        thread = threading.Thread(target=organize, daemon=True)
        thread.start()

    def _cancel_operation(self):
        """Annule l'opération en cours.

        Appelle ``cancel()`` sur le ``SmartOrganizer`` actif pour qu'il
        sorte de sa boucle d'organisation à la prochaine itération.
        Le flag local ``_cancel_requested`` reste utile pour la phase
        d'analyse et pour les conditions de boucle de scan.

        W60 (retour testeur) : on réactive immédiatement le bouton
        Organiser et on désactive Annuler — l'utilisateur ne doit pas
        rester bloqué tant que le thread n'a pas pris le signal.
        """
        self._cancel_requested = True
        if self._current_organizer is not None:
            try:
                self._current_organizer.cancel()
            except Exception as exc:
                logger.debug(f"_cancel_operation: {exc}")
        self._update_progress("Annulation en cours…", None)
        # Réactive le bouton Organiser dès la demande d'annulation, sans
        # attendre la sortie du thread worker. Sécurité : l'option
        # `_operation_running` reste True jusqu'à la fin du worker, ce qui
        # empêche un double-lancement via la garde au début de _organize_files.
        try:
            self.organize_button.configure(state="normal")
            self.analyze_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
        except Exception as exc:
            logger.debug(f"_cancel_operation buttons reset: {exc}")

    # ------------------------------------------------------------------
    # D-06 (audit 2026-05-14) : sentinel anti-RuntimeError post-destroy
    # ------------------------------------------------------------------
    def destroy(self):
        """Marque le frame comme détruit avant de libérer les ressources Tk.

        Les workers en arrière-plan utilisent ``self.after(0, ...)`` pour
        marshaller leurs callbacks sur la boucle Tk principale. Sans ce
        sentinel, un worker qui se réveille après ``destroy()`` ferait
        crasher l'app avec ``RuntimeError: main thread is not in main loop``.
        """
        self._destroyed = True
        super().destroy()

    def _safe_after(self, delay_ms: int, fn):
        """Variante de ``self.after`` no-op si le frame a été détruit."""
        if getattr(self, "_destroyed", False):
            return None
        try:
            return self.after(delay_ms, fn)
        except (tk.TclError, RuntimeError) as exc:
            # TclError : widget invalide. RuntimeError : main loop terminée.
            logger.debug(f"_safe_after: {exc}")
            return None

    def _set_buttons_state(self, enabled: bool):
        """Active/désactive les boutons."""
        state = "normal" if enabled else "disabled"
        cancel_state = "disabled" if enabled else "normal"

        self._safe_after(0, lambda: self.analyze_button.configure(state=state))
        self._safe_after(0, lambda: self.organize_button.configure(state=state))
        self._safe_after(0, lambda: self.cancel_button.configure(state=cancel_state))

    def _update_progress(self, message: str, progress: Optional[float]):
        """Met à jour la barre de progression et le label %."""

        def update():
            self.progress_label.configure(text=message)
            if progress is not None:
                self.progress_bar.set(progress)
                # Lot B audit 2026-05-14 : label numérique synchro
                try:
                    self.progress_pct_var.set(f"{int(round(progress * 100))} %")
                except tk.TclError:
                    # Widget detruit pendant l'update — no-op silencieux.
                    pass
            self.status_callback(message, progress)

        self._safe_after(0, update)

    def _show_analysis_results(self, stats: dict):
        """Affiche les résultats de l'analyse."""

        def show():
            message = f"""
Résultats de l'analyse:

Total de fichiers: {stats["total"]}
Avec date: {stats["with_date"]} ({stats["with_date"] * 100 // max(1, stats["total"])}%)
Avec appareil: {stats["with_camera"]} ({stats["with_camera"] * 100 // max(1, stats["total"])}%)
Avec GPS: {stats["with_gps"]} ({stats["with_gps"] * 100 // max(1, stats["total"])}%)

Distribution par année:
{chr(10).join(f"  {y}: {c} fichiers" for y, c in sorted(stats["by_year"].items()))}

Distribution par appareil:
{chr(10).join(f"  {c}: {n} fichiers" for c, n in sorted(stats["by_camera"].items(), key=lambda x: -x[1])[:5])}
"""
            messagebox.showinfo("Analyse terminée", message)
            self._update_progress("Analyse terminée", 1)

        self._safe_after(0, show)

    def _show_organization_results(self, result):
        """Affiche les résultats de l'organisation avec :
        - une notification système non-modale (Q5)
        - un dialog modal résumé + bouton « Ouvrir destination » (Q6).

        W60 (retour testeur) : si l'utilisateur a annulé, on saute la
        modale (qui bloquerait l'IHM avec grab_set) et on remet juste le
        status bar à « Organisation annulée ». L'utilisateur peut relancer
        immédiatement.
        """
        if self._cancel_requested:
            self._update_progress(
                f"Organisation annulée — {result.processed} traités sur {result.total}",
                0.0,
            )
            return

        summary = (
            f"Total : {result.total}  •  Traités : {result.processed}\n"
            f"Ignorés : {result.skipped}  •  Erreurs : {result.errors}"
        )
        full_message = f"Organisation terminée!\n\n{summary}"

        # Bloc stats GPS si la localisation a été appliquée
        with_gps = getattr(result, "files_with_gps", 0)
        without_gps = getattr(result, "files_without_gps", 0)
        if with_gps or without_gps:
            geocoded = getattr(result, "files_geocoded", 0)
            raw_coords = getattr(result, "files_raw_coords", 0)
            full_message += (
                f"\n\n🌍 Localisation GPS\n"
                f"  Avec GPS    : {with_gps}\n"
                f"  Sans GPS    : {without_gps}\n"
                f"  Géocodées   : {geocoded}  (nom de lieu)\n"
                f"  Coordonnées : {raw_coords}  (Lat_x_Lon_y, fallback)"
            )

        if result.error_messages:
            full_message += "\n\nErreurs:\n" + "\n".join(result.error_messages[:5])
            if len(result.error_messages) > 5:
                full_message += f"\n... et {len(result.error_messages) - 5} autres erreurs"

        # Q5 — Notification système non-modale (fond + barre des tâches)
        if self.notify_on_finish.get():
            try:
                _windows_toast("PhotoOrganizer", summary.replace("\n", " • "))
            except Exception as exc:
                logger.debug(f"toast non envoye : {exc}")

        # Modal récap avec bouton « Ouvrir destination »
        self._show_results_modal(full_message, dest=self.dest_var.get())
        self._update_progress("Organisation terminée", 1)

    def _show_results_modal(self, message: str, dest: str):
        """Panneau inline « Organisation terminée » (refonte 2026-05-18).

        Remplace l'ancienne modale CTkToplevel par un panneau intégré qui
        prend la place du tabview, avec logo + titre + récap + bouton
        « 📂 Ouvrir destination » et « Fermer ».
        """
        def build(body):
            body.columnconfigure(0, weight=1)
            body.rowconfigure(0, weight=1)
            textbox = ctk.CTkTextbox(body, height=200)
            textbox.grid(row=0, column=0, sticky="nsew", padx=PAD_M, pady=PAD_S)
            textbox.insert("end", message)
            textbox.configure(state="disabled")

        footer = []
        if dest:
            footer.append(("📂 Ouvrir destination", lambda d=dest: _open_folder(d)))
        footer.append(("Fermer", "__close__"))

        self._show_inline_panel(
            title="✅ Organisation terminée",
            builder=build,
            footer_buttons=footer,
        )

    def _show_dry_run_preview(self):
        """Q2 — Aperçu dry-run : applique les options pour les 100 premiers
        fichiers et affiche l'arborescence cible dans un panneau inline,
        **sans copier ni déplacer aucun fichier**.

        B-07 (audit 2026-06-11) : le calcul (lecture EXIF jusqu'à 100
        fichiers) tourne désormais dans un worker thread — il gelait l'UI
        plusieurs secondes sur le main thread. B-06 : le critère « lieu »
        est maintenant pris en compte (coordonnées brutes, sans appel
        réseau ; les noms de lieux sont résolus uniquement au tri réel).
        """
        if getattr(self, "_operation_running", False):
            logger.debug("Aperçu ignoré : une opération est déjà en cours")
            return

        sources = self._split_sources()
        dest = self.dest_var.get().strip()
        if not sources:
            messagebox.showerror("Aperçu", "Sélectionnez au moins un dossier source.")
            return
        if not dest:
            messagebox.showerror("Aperçu", "Sélectionnez le dossier destination.")
            return

        def compute_preview():
            # B-03/B-07 : même discipline que les autres workers — flags
            # toujours remis en place, erreurs affichées, jamais de mort muette.
            self._operation_running = True
            self._set_buttons_state(False)
            try:
                files = self._get_files()
                if not files:
                    self._update_progress("Aucun fichier détecté avec ces filtres.", 0)
                    self._safe_after(0, lambda: messagebox.showinfo(
                        "Aperçu", "Aucun fichier détecté avec ces filtres."))
                    return

                options = self._get_options()
                # On applique les filtres pré-traitement comme en réel
                organizer = SmartOrganizer(file_manager=self.file_manager)
                eligible = [f for f in files if organizer._passes_filters(f, options)]

                # Détection paires si demandé (impact visuel)
                pairs = organizer._detect_raw_jpeg_pairs(eligible) if options.keep_raw_jpeg_pairs else {}

                # Pour chaque fichier, calculer le chemin cible (sans copier)
                sample = eligible[:100]
                total_sample = len(sample)
                tree: dict = {}
                counter = 0
                location_used = False
                for idx, fp in enumerate(sample):
                    if self._cancel_requested:
                        self._update_progress("Aperçu annulé", 0)
                        return
                    counter += 1
                    self._update_progress(
                        f"Aperçu : {idx + 1}/{total_sample}",
                        (idx + 1) / total_sample,
                    )
                    try:
                        exif = get_exif_data(fp)
                        date_taken = extract_date(fp, exif)
                        make, model = get_camera_info(exif, fp)
                        path = dest
                        # Critères dans l'ordre choisi
                        if options.multilayer:
                            crits = options.criteria_order
                        elif options.organize_by_date:
                            crits = ["date"]
                        elif options.organize_by_camera:
                            crits = ["camera"]
                        elif options.organize_by_location:
                            crits = ["location"]
                        else:
                            crits = []
                        for c in crits:
                            if c == "date" and options.organize_by_date:
                                if date_taken:
                                    y, m, d = (str(date_taken.year), f"{date_taken.month:02d}", f"{date_taken.day:02d}")
                                    mapping = {
                                        "year/month/day": [y, m, f"{y}_{m}_{d}"],
                                        "year/month": [y, f"{y}_{m}"],
                                        "year": [y],
                                        "year_month_day": [f"{y}_{m}_{d}"],
                                        "year_month": [f"{y}_{m}"],
                                    }
                                    for seg in mapping.get(options.date_format, [y, m, f"{y}_{m}_{d}"]):
                                        path = os.path.join(path, seg)
                                else:
                                    path = os.path.join(path, "Sans date")
                            elif c == "camera" and options.organize_by_camera:
                                cam = (
                                    f"{make} {model}".strip()
                                    if (make != "Unknown" or model != "Unknown")
                                    else "Appareil inconnu"
                                )
                                path = os.path.join(path, cam.replace("/", "_"))
                            elif c == "location" and options.organize_by_location:
                                # B-06 : aperçu du critère lieu SANS réseau —
                                # coordonnées brutes, comme le fallback du tri réel.
                                location_used = True
                                try:
                                    lat, lon = get_gps_coordinates(fp)
                                except Exception:
                                    lat, lon = None, None
                                if lat is None or lon is None:
                                    seg = "Sans localisation GPS"
                                else:
                                    seg = f"Lat_{lat:.4f}_Lon_{lon:.4f}"
                                path = os.path.join(path, seg)

                        # Renommage
                        fname = os.path.basename(fp)
                        if options.rename_template:
                            try:
                                fname = SmartOrganizer._apply_rename_template(
                                    fname,
                                    options.rename_template,
                                    date_taken,
                                    make,
                                    model,
                                    counter,
                                )
                            except Exception:
                                pass
                    except Exception as exc:
                        logger.debug(f"preview erreur : {exc}")
                        path = os.path.join(dest, "(erreur)")
                        fname = os.path.basename(fp)

                    tree.setdefault(path, []).append(fname)

                # Header textuel + arbo cible (refonte 2026-05-18 — panneau inline)
                header_text = f"📋 {len(eligible)} fichier(s) éligible(s) sur {len(files)} détecté(s)"
                if options.keep_raw_jpeg_pairs and pairs:
                    header_text += f"  •  {len(pairs)} paire(s) RAW+JPEG détectée(s)"
                header_text += f"\n📁 Destination : {dest}"
                if len(eligible) > 100:
                    header_text += f"\n(Aperçu limité aux 100 premiers fichiers sur {len(eligible)})"
                if location_used and options.use_geocoding:
                    header_text += (
                        "\nℹ️ Lieux affichés en coordonnées brutes — les noms de "
                        "lieux seront résolus lors du tri réel."
                    )

                def show_panel():
                    def build(body):
                        body.columnconfigure(0, weight=1)
                        body.rowconfigure(1, weight=1)
                        ctk.CTkLabel(
                            body, text=header_text, justify="left", anchor="w",
                        ).grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_S))
                        textbox = ctk.CTkTextbox(body, font=ctk.CTkFont(family="Consolas", size=11))
                        textbox.grid(row=1, column=0, sticky="nsew", padx=PAD_M, pady=PAD_S)
                        for folder in sorted(tree.keys()):
                            rel = os.path.relpath(folder, dest) if dest in folder else folder
                            textbox.insert("end", f"\n📁 {rel}/  ({len(tree[folder])} fichiers)\n")
                            for f in tree[folder][:10]:
                                textbox.insert("end", f"   • {f}\n")
                            if len(tree[folder]) > 10:
                                textbox.insert("end", f"   … {len(tree[folder]) - 10} de plus\n")
                        textbox.configure(state="disabled")

                    self._show_inline_panel(
                        title="👁 Aperçu (dry-run, sans modification disque)",
                        builder=build,
                    )
                    self._update_progress("Aperçu prêt", None)

                self._safe_after(0, show_panel)
            except Exception as exc:  # noqa: BLE001 — le worker ne doit jamais mourir muet
                err_msg = str(exc)
                logger.exception("Aperçu dry-run échoué")
                self._update_progress(f"Erreur : {err_msg}", 0)
                self._safe_after(0, lambda m=err_msg: messagebox.showerror("Aperçu", m))
            finally:
                self._operation_running = False
                self._set_buttons_state(True)

        self._cancel_requested = False
        threading.Thread(target=compute_preview, daemon=True).start()
