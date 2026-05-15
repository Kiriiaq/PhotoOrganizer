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
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
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
            title=title, message=message,
            app_name='PhotoOrganizer', timeout=5,
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
        win.attributes('-topmost', True)
        ctk.CTkLabel(
            win, text=title, font=ctk.CTkFont(size=14, weight='bold'),
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
    text = text.strip().upper().replace(' ', '')
    units = {'B': 1, 'KB': 1024, 'K': 1024,
             'MB': 1024 ** 2, 'M': 1024 ** 2,
             'GB': 1024 ** 3, 'G': 1024 ** 3}
    for unit, mult in units.items():
        if text.endswith(unit):
            try:
                return int(float(text[:-len(unit)]) * mult)
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
CHECK_FG = ("#1f6aa5", "#1f6aa5")          # bleu cohérent avec color_theme=blue
CHECK_HOVER = ("#144870", "#144870")
CHECK_BORDER = ("gray40", "gray60")        # bordure visible dark + light
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
        status_callback: Optional[Callable] = None
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
        self._criteria_order: List[str] = ['date', 'camera', 'location']
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
        self.filter_rating_min = ctk.IntVar(value=0)    # 0..5
        self.filter_keywords = ctk.StringVar(value="")  # CSV

        # ---- Toggles avancés ----
        self.skip_if_identical = ctk.BooleanVar(value=False)   # R2
        self.keep_raw_jpeg_pairs = ctk.BooleanVar(value=False) # R3
        self.cleanup_empty_source = ctk.BooleanVar(value=False)# R5
        self.validate_disk_space = ctk.BooleanVar(value=True)  # R6
        self.export_index_csv = ctk.BooleanVar(value=False)    # R7
        self.export_index_json = ctk.BooleanVar(value=False)
        self.notify_on_finish = ctk.BooleanVar(value=True)     # Q5

        # ---- Bursts S1 + Incremental S5 ----
        self.detect_bursts = ctk.BooleanVar(value=False)
        self.burst_mode = ctk.StringVar(value="manual")  # "manual" | "auto"
        self.burst_threshold = ctk.IntVar(value=3)             # secondes
        self.burst_min_count = ctk.IntVar(value=3)
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

        # ---- Initialiser le scheduler E5 ----
        # Lazy import pour ne pas tirer la dépendance si la feature n'est
        # jamais activée (et garder le démarrage rapide).
        from core.scheduler import JobScheduler
        self._scheduler = JobScheduler(callback=self._scheduled_run_callback)

        # Restaurer l'état planifié depuis AppConfig
        cfg = get_config().config
        if getattr(cfg, 'schedule_enabled', False):
            self.schedule_enabled.set(True)
            self.schedule_time.set(getattr(cfg, 'schedule_time', '23:00'))
            # Auto-démarrer
            self._scheduler.configure(True, self.schedule_time.get())
        # Mettre à jour le label statut
        self._refresh_schedule_status()
        # Persister à chaque modification de l'heure
        self.schedule_time.trace_add("write", lambda *_: self._on_schedule_time_change())

    def _create_ui(self):
        """Crée l'interface utilisateur en 3 zones (refonte UI v3).

        Layout :
          ┌──────────────────────────────────────────────────────┐
          │ ZONE TOP (fixe)        Sources / Dest / Compteur     │  ~110 px
          ├──────────────────────────────────────────────────────┤
          │ ZONE CENTRE (scroll si nécessaire) 2 colonnes         │  weight=1
          │   • Critères d'organisation  | Action + Types         │
          │   • [▼ Avancé] (collapsible) — filtres + comportements│
          │   • Renommage (1 ligne template + presets)            │
          ├──────────────────────────────────────────────────────┤
          │ ZONE BOTTOM (fixe)     Progression + boutons d'action │  ~80 px
          └──────────────────────────────────────────────────────┘

        Bénéfices vs v2 :
          - Compteur fichiers et boutons toujours visibles
          - Action principale "Organiser" à droite (convention desktop)
          - Section Planification déplacée vers Paramètres (config persistante)
        """
        # Layout root du frame OrganizeFrame : 3 lignes (top fixe / centre
        # scrollable / bottom fixe). Seule la ligne du milieu prend du poids.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # top fixe
        self.rowconfigure(1, weight=1)  # centre scrollable expansif
        self.rowconfigure(2, weight=0)  # bottom fixe

        # ZONE TOP : Sources / Destination / Compteur fichiers (sticky)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_M, 0))
        top.columnconfigure(0, weight=1)
        self._top_zone = top

        # ZONE CENTRE : scrollable avec les options
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=PAD_M, pady=PAD_S)
        self._scroll.columnconfigure(0, weight=1, minsize=280)
        self._scroll.columnconfigure(1, weight=1, minsize=280)

        # ZONE BOTTOM : compteur + progress + boutons (sticky bottom)
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
        bottom.columnconfigure(0, weight=1)
        self._bottom_zone = bottom

        # Création des sections dans leur zone respective
        self._create_folders_section()       # zone top
        self._create_options_section()       # scroll row=0 (critères + types)
        self._create_advanced_section()      # scroll row=1 (collapsible)
        self._create_rename_section()        # scroll row=2 (1 ligne)
        self._create_actions_section()       # zone bottom

        # Section Planification déplacée vers SettingsFrame — l'attribut
        # `schedule_status_var` reste utilisé par le scheduler.

    def _create_folders_section(self):
        """Section de sélection des dossiers en zone top fixe (toujours visible).

        Compactée : titre + 1 ligne source + 1 ligne destination + 1 ligne
        compteur fichiers. Pas de scroll possible sur ce bloc → l'utilisateur
        voit immédiatement combien de fichiers sont prêts à être organisés.
        """
        parent = self._top_zone
        folders = ctk.CTkFrame(parent)
        folders.grid(row=0, column=0, sticky="ew")
        folders.columnconfigure(1, weight=1)

        # Titre (refonte v5 — retours JSON 2026-05-13)
        # Le hint « Plusieurs sources : ; » et la mention drag-and-drop ont
        # été retirés (cf. W06 retour testeur : « supprime la fonctionnalité
        # drag and drop inutile et la possibilité d'utiliser des séparateurs »).
        title_row = ctk.CTkFrame(folders, fg_color="transparent")
        title_row.grid(row=0, column=0, columnspan=3, sticky="ew", padx=PAD_M, pady=(PAD_M, PAD_S))
        ctk.CTkLabel(
            title_row, text="📁 Sélection des dossiers",
            font=font_section(),
        ).pack(side="left")

        # Ligne Source — un seul dossier, plus de séparateur ;
        ctk.CTkLabel(folders, text="Source :",
                     font=font_label(), width=90, anchor="w",
                     ).grid(row=1, column=0, sticky="w", padx=(PAD_M, PAD_S), pady=PAD_S)
        self.source_entry = ctk.CTkEntry(
            folders,
            textvariable=self.source_var,
            placeholder_text="Sélectionnez le dossier source à organiser…",
            height=BTN_H_STD,
        )
        self.source_entry.grid(row=1, column=1, sticky="ew", padx=PAD_S, pady=PAD_S)
        self.browse_source_btn = icon_button(
            folders, text="📂", command=self._browse_source,
        )
        self.browse_source_btn.grid(row=1, column=2, padx=(PAD_S, PAD_M), pady=PAD_S)
        # Le bouton « + Source » (multi-source) a été retiré — W08 retour
        # testeur : « supprime le bouton car inutile ».

        # Ligne Destination
        ctk.CTkLabel(folders, text="Destination :",
                     font=font_label(), width=90, anchor="w",
                     ).grid(row=2, column=0, sticky="w", padx=(PAD_M, PAD_S), pady=PAD_S)

        # Sous-frame pour entry + bouton ↗ "Ouvrir dest" qui restent
        # accessibles. Le bouton 📂 Parcourir occupe la colonne 2.
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
            dest_row, text="↗",
            command=lambda: _open_folder(self.dest_var.get()),
        )
        self.open_dest_btn.grid(row=0, column=1)

        self.browse_dest_btn = icon_button(
            folders, text="📂", command=self._browse_dest,
        )
        self.browse_dest_btn.grid(row=2, column=2, padx=(PAD_S, PAD_M), pady=PAD_S)

        # Ligne Compteur fichiers (toujours visible — fix T-030..033)
        self.file_count_var = ctk.StringVar(value="Aucun dossier source sélectionné.")
        self.file_count_label = ctk.CTkLabel(
            folders,
            textvariable=self.file_count_var,
            font=font_label(),
            anchor="w",
            text_color=LABEL_MUTED,
        )
        self.file_count_label.grid(
            row=3, column=0, columnspan=3,
            sticky="ew", padx=PAD_M, pady=(0, PAD_M),
        )

        # Lot B audit 2026-05-14 (T-030..T-033) : bouton « 📋 » qui ouvre une
        # modale listant les fichiers détectés. Réponse au retour testeur
        # "je ne vois pas le titre/chemin des fichiers sélectionnés".
        self.show_files_btn = icon_button(
            folders, text="📋",
            command=self._show_files_list,
        )
        self.show_files_btn.grid(
            row=3, column=3, padx=(0, PAD_M), pady=(0, PAD_M),
        )

        # Drag-and-drop retiré (W06) — la méthode _setup_drag_drop reste
        # définie mais n'est plus appelée pour ne pas créer de bindings.

    def _create_options_section(self):
        """Crée la section des options dans le scroll central (row=0)."""
        # Frame gauche - Critères d'organisation
        left_frame = ctk.CTkFrame(self._scroll)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S), pady=PAD_S)

        ctk.CTkLabel(
            left_frame,
            text="🗂️ Critères d'organisation",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Organiser par date
        _make_checkbox(
            left_frame,
            text="Par date de prise de vue",
            variable=self.organize_by_date
        ).pack(anchor="w", padx=20, pady=3)

        # Format de date
        date_format_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        date_format_frame.pack(fill="x", padx=40, pady=2)

        ctk.CTkLabel(
            date_format_frame, text="Format :",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE),
        ).pack(side="left")
        self.date_format_menu = ctk.CTkOptionMenu(
            date_format_frame,
            variable=self.date_format,
            values=["year/month/day", "year/month", "year", "year_month_day", "year_month"]
        )
        self.date_format_menu.pack(side="left", padx=5)

        # Organiser par appareil
        _make_checkbox(
            left_frame,
            text="Par appareil photo",
            variable=self.organize_by_camera
        ).pack(anchor="w", padx=20, pady=3)

        # Organiser par localisation GPS
        # On garde une référence à la case pour positionner les sous-options
        # GPS juste en dessous via pack(after=…) — cf. W17/W18 retour testeur.
        self._gps_checkbox = _make_checkbox(
            left_frame,
            text="Par localisation GPS",
            variable=self.organize_by_location
        )
        self._gps_checkbox.pack(anchor="w", padx=20, pady=3)

        # Sous-options GPS — cachées si organize_by_location est OFF.
        # Placées juste sous la case « Par localisation GPS » via
        # pack(after=…) pour rester en contexte (W17/W18).
        self.gps_options_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        # Affichage initial déclenché plus bas via _refresh_gps_options_visibility
        gps_top = ctk.CTkFrame(self.gps_options_frame, fg_color="transparent")
        gps_top.pack(fill="x", padx=20, pady=2)
        _make_checkbox(
            gps_top, text="Géocodage (nom du lieu)",
            variable=self.use_geocoding,
        ).pack(side="left")
        ctk.CTkLabel(
            gps_top,
            text="(sinon : Lat_x_Lon_y brutes)",
            font=ctk.CTkFont(size=11), text_color=("gray45", "gray65"),
        ).pack(side="left", padx=8)

        # Slider distance max — pas large 1 km au glissement, ajustement
        # fin 100 m via boutons ◀ / ▶ (Lot R6 du worktree d'origine).
        gps_slider = ctk.CTkFrame(self.gps_options_frame, fg_color="transparent")
        gps_slider.pack(fill="x", padx=20, pady=(2, 6))
        ctk.CTkLabel(
            gps_slider, text="Distance max :",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE),
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            gps_slider, text="◀", width=28,
            command=lambda: self._step_max_distance(-self.MAX_DIST_FINE_STEP),
        ).pack(side="left", padx=(0, 2))

        self.max_distance_slider = ctk.CTkSlider(
            gps_slider, from_=0, to=50,
            number_of_steps=50,                 # pas 1 km au glissement
            variable=self.max_distance, width=160,
            command=self._on_max_distance_change,
        )
        self.max_distance_slider.pack(side="left", padx=(0, 2))

        ctk.CTkButton(
            gps_slider, text="▶", width=28,
            command=lambda: self._step_max_distance(self.MAX_DIST_FINE_STEP),
        ).pack(side="left", padx=(2, 5))

        ctk.CTkLabel(
            gps_slider, textvariable=self.max_distance_label_var,
            width=64, anchor="w",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight="bold"),
        ).pack(side="left")

        # Sync libellé initial + trace pour mise à jour live
        self._on_max_distance_change(self.max_distance.get())
        self.max_distance.trace_add(
            "write",
            lambda *_: self._on_max_distance_change(self.max_distance.get()),
        )
        # Affichage conditionnel des sous-options selon la case « Par localisation »
        self.organize_by_location.trace_add(
            "write", lambda *_: self._refresh_gps_options_visibility()
        )
        self._refresh_gps_options_visibility()

        # ---- Séparateur visuel + section « Organisation multicouche » -----
        # Cette option modifie significativement le comportement (combine
        # plusieurs critères en cascade). On la met clairement en évidence
        # via un séparateur, un titre dédié et un widget Switch (plus visible
        # qu'une CTkCheckBox pour les modes ON/OFF).
        ctk.CTkFrame(left_frame, height=2, fg_color=("gray70", "gray30")).pack(
            fill="x", padx=10, pady=(12, 6)
        )
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
        self.criteria_rows_container = ctk.CTkFrame(
            self.criteria_order_frame, fg_color="transparent"
        )
        self.criteria_rows_container.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            self.criteria_order_frame,
            text=(
                "Astuce : un critère grisé est désactivé (cocher la case "
                "correspondante au-dessus pour l'activer)."
            ),
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray65"),
            justify="left",
            wraplength=320,
        ).pack(anchor="w", padx=10, pady=(0, 6))

        # Premier rendu + branchement du toggle
        self._render_criteria_order()
        self.multilayer.trace_add(
            "write", lambda *_: self._update_criteria_visibility()
        )
        # Les checkboxes des critères influencent l'aspect grisé/actif :
        # on rerend le panneau quand l'une d'elles bascule.
        for v in (self.organize_by_date, self.organize_by_camera):
            v.trace_add("write", lambda *_: self._render_criteria_order())
        self._update_criteria_visibility()

        # Frame droite - Options de traitement
        right_frame = ctk.CTkFrame(self._scroll)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(PAD_S, 0), pady=PAD_S)

        ctk.CTkLabel(
            right_frame,
            text="⚙️ Options de traitement",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Action
        action_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            action_frame, text="Action :",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE),
        ).pack(side="left", padx=5)
        _make_radio(
            action_frame,
            text="Copier",
            variable=self.copy_not_move,
            value=True
        ).pack(side="left", padx=10)
        _make_radio(
            action_frame,
            text="Déplacer",
            variable=self.copy_not_move,
            value=False
        ).pack(side="left", padx=10)

        # Options avancées
        _make_checkbox(
            right_frame,
            text="Parcourir les sous-dossiers",
            variable=self.recursive
        ).pack(anchor="w", padx=20, pady=3)

        # Types de fichiers
        ctk.CTkFrame(right_frame, height=2, fg_color=("gray70", "gray30")).pack(
            fill="x", padx=10, pady=(10, 4)
        )
        ctk.CTkLabel(
            right_frame,
            text="📂 Types de fichiers",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold")
        ).pack(anchor="w", padx=10, pady=(0, 4))

        _make_checkbox(
            right_frame,
            text="Images (JPG, PNG, HEIC…)",
            variable=self.include_images
        ).pack(anchor="w", padx=20, pady=3)

        _make_checkbox(
            right_frame,
            text="RAW (ARW, CR2, NEF…)",
            variable=self.include_raw
        ).pack(anchor="w", padx=20, pady=3)

        _make_checkbox(
            right_frame,
            text="Vidéos (MP4, MOV, AVI…)",
            variable=self.include_videos
        ).pack(anchor="w", padx=20, pady=3)

    # =================================================================
    # Sections "avancées" (filtres + comportements + renommage + presets)
    # =================================================================
    def _create_advanced_section(self):
        """Section "Avancé" repliable (collapsed par défaut).

        Regroupe en un seul panneau toutes les options secondaires :
        filtres pré-traitement (R1), comportements (R2-R7), bursts (S1),
        index, mode incrémental (S5).

        Le toggle texte ▶/▼ permet d'afficher/masquer le contenu — par
        défaut masqué pour ne pas encombrer l'IHM ; les options gardent
        leurs valeurs courantes même quand le panneau est replié.
        """
        # Container externe : occupe les 2 colonnes du scroll
        wrapper = ctk.CTkFrame(self._scroll)
        wrapper.grid(row=1, column=0, columnspan=2, sticky="ew",
                     padx=PAD_S, pady=PAD_S)
        wrapper.columnconfigure(0, weight=1)

        # En-tête cliquable : titre + flèche, occupe toute la largeur
        self._adv_collapsed = True  # état initial
        self._adv_toggle_btn = ctk.CTkButton(
            wrapper, text="▶  ⚙️ Options avancées (filtres, comportements, bursts, …)",
            command=self._toggle_advanced_section,
            anchor="w",
            font=font_section(),
            fg_color="transparent",
            text_color=("gray10", "#DCE4EE"),
            hover_color=("gray85", "gray25"),
            height=BTN_H_STD,
        )
        self._adv_toggle_btn.grid(row=0, column=0, sticky="ew",
                                  padx=PAD_M, pady=PAD_S)

        # Container interne (caché par défaut) — 2 colonnes (filtres / comportements)
        self._adv_content = ctk.CTkFrame(wrapper, fg_color="transparent")
        # Pas de grid() ici → le panneau démarre invisible
        self._adv_content.columnconfigure(0, weight=1, uniform="adv")
        self._adv_content.columnconfigure(1, weight=1, uniform="adv")

        # ===== Colonne gauche : filtres pré-traitement =====
        filters = ctk.CTkFrame(self._adv_content, fg_color="transparent")
        filters.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S), pady=0)

        ctk.CTkLabel(filters, text="🔍 Filtres",
                     font=font_label(weight="bold"),
                     ).pack(anchor="w", padx=PAD_S, pady=(PAD_S, PAD_S))

        # W30-W35 (retour testeur 2026-05-13) : placeholders enrichis avec
        # un exemple concret et le format attendu, plus une ligne grise
        # sous chaque champ qui rappelle le format en clair.
        for label, var, placeholder, hint in [
            ("Date min :",   self.filter_date_min,  "ex. 2024-06-01",
             "Format YYYY-MM-DD  ·  ex. 2024-06-01"),
            ("Date max :",   self.filter_date_max,  "ex. 2024-12-31",
             "Format YYYY-MM-DD  ·  laisser vide = pas de limite"),
            ("Taille min :", self.filter_size_min,  "ex. 100KB",
             "Unités acceptées : B, KB, MB, GB  ·  ex. 100KB, 5MB"),
            ("Taille max :", self.filter_size_max,  "ex. 50MB",
             "Unités acceptées : B, KB, MB, GB  ·  vide = pas de limite"),
        ]:
            row = ctk.CTkFrame(filters, fg_color="transparent")
            row.pack(fill="x", padx=PAD_S, pady=(2, 0))
            ctk.CTkLabel(row, text=label, width=86, anchor="w",
                         font=font_label()).pack(side="left")
            ctk.CTkEntry(row, textvariable=var, placeholder_text=placeholder,
                         height=BTN_H_STD).pack(side="left", padx=PAD_S, fill="x", expand=True)
            # Hint format en italique gris sous le champ
            ctk.CTkLabel(filters, text=f"    {hint}",
                         font=font_hint(), text_color=HINT_COLOR, anchor="w",
                         ).pack(fill="x", padx=PAD_S, pady=(0, 2))

        # Note EXIF
        rating_row = ctk.CTkFrame(filters, fg_color="transparent")
        rating_row.pack(fill="x", padx=PAD_S, pady=2)
        ctk.CTkLabel(rating_row, text="Note ≥ :", width=86, anchor="w",
                     font=font_label()).pack(side="left")
        ctk.CTkOptionMenu(
            rating_row, variable=self.filter_rating_min,
            values=["0", "1", "2", "3", "4", "5"], width=70, height=BTN_H_STD,
            command=lambda v: self.filter_rating_min.set(int(v)),
        ).pack(side="left", padx=PAD_S)
        ctk.CTkLabel(rating_row, text="(0 = inactif)",
                     font=font_hint(), text_color=HINT_COLOR).pack(side="left")

        # Mots-clés — W35 : placeholder + hint format
        kw_row = ctk.CTkFrame(filters, fg_color="transparent")
        kw_row.pack(fill="x", padx=PAD_S, pady=(2, 0))
        ctk.CTkLabel(kw_row, text="Mots-clés :", width=86, anchor="w",
                     font=font_label()).pack(side="left")
        ctk.CTkEntry(kw_row, textvariable=self.filter_keywords,
                     placeholder_text="ex. vacances, mariage, été",
                     height=BTN_H_STD,
                     ).pack(side="left", padx=PAD_S, fill="x", expand=True)
        ctk.CTkLabel(
            filters,
            text="    Séparateur : virgule  ·  match si AU MOINS UN mot-clé EXIF correspond",
            font=font_hint(), text_color=HINT_COLOR, anchor="w",
        ).pack(fill="x", padx=PAD_S, pady=(0, PAD_S))

        # ===== Colonne droite : comportements + bursts + incremental + index =====
        behaviors = ctk.CTkFrame(self._adv_content, fg_color="transparent")
        behaviors.grid(row=0, column=1, sticky="nsew", padx=(PAD_S, 0), pady=0)

        ctk.CTkLabel(behaviors, text="🛠️ Comportements",
                     font=font_label(weight="bold"),
                     ).pack(anchor="w", padx=PAD_S, pady=(PAD_S, PAD_S))

        # Comportements regroupés par catégorie (audit 2026-05-15) — au lieu
        # d'une longue liste à plat, on présente 4 sous-groupes lisibles.
        # Chaque sous-groupe a un sous-titre gris et 1-3 toggles indentés.
        behavior_groups = [
            ("📦 Conservation des doublons", [
                ("Skip si fichier identique déjà présent",
                 self.skip_if_identical,
                 "ex : 2 photos identiques (hash égal) → seule la 1ère est traitée"),
                ("Garder les paires RAW + JPEG ensemble",
                 self.keep_raw_jpeg_pairs,
                 "ex : IMG_001.CR2 + IMG_001.JPG → même dossier final"),
            ]),
            ("🧹 Nettoyage / sécurité", [
                ("Nettoyer les dossiers source vides (Déplacer)",
                 self.cleanup_empty_source,
                 "ex : après MOVE, supprime D:/Vacances/Jour1/ s'il devient vide"),
                ("Vérifier l'espace disque avant exécution",
                 self.validate_disk_space,
                 "ex : refuse de copier 80 Go vers un disque qui en a 50"),
            ]),
            ("🔍 Détection / mode", [
                ("Détection de rafales → sous-dossier Burst_NN/",
                 self.detect_bursts,
                 "ex : 5 photos prises en 2 s → Burst_01/"),
                ("Mode incrémental (skip déjà organisés)",
                 self.incremental_mode,
                 "ex : 2e exécution du même dossier → ne retraite que les nouveaux"),
            ]),
            ("🔔 Notification", [
                ("Notification système à la fin",
                 self.notify_on_finish,
                 "ex : toast Windows « 1245 fichiers traités » à la fin"),
            ]),
        ]
        for group_title, toggles in behavior_groups:
            ctk.CTkLabel(
                behaviors, text=group_title,
                font=font_hint(), text_color=HINT_COLOR,
                anchor="w",
            ).pack(fill="x", padx=PAD_S, pady=(PAD_S, 0))
            for text, var, hint in toggles:
                _make_checkbox(behaviors, text=text, variable=var
                               ).pack(anchor="w", padx=(PAD_L, PAD_S), pady=(2, 0))
                # Note inline avec un "ex : …" sous chaque toggle.
                ctk.CTkLabel(
                    behaviors, text=f"    {hint}",
                    font=font_hint(), text_color=HINT_COLOR,
                    anchor="w", justify="left",
                ).pack(fill="x", padx=(PAD_L, PAD_S), pady=(0, PAD_S))

        # Sous-options bursts inline — mode manuel / auto (audit 2026-05-15).
        # En mode manuel : seuil temporel choisi par l'utilisateur.
        # En mode auto : seuil = mean - stddev des deltas du dossier final.
        burst_sub = ctk.CTkFrame(behaviors, fg_color="transparent")
        burst_sub.pack(fill="x", padx=(28, PAD_S), pady=(0, PAD_S))

        # Ligne 1 : choix du mode (radios)
        mode_row = ctk.CTkFrame(burst_sub, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(mode_row, text="Mode :", width=80, anchor="w",
                     font=font_hint(), text_color=HINT_COLOR).pack(side="left")
        _make_radio(
            mode_row, text="Manuel (seuil fixe)",
            variable=self.burst_mode, value="manual",
            command=lambda: self._refresh_burst_mode_ui(),
        ).pack(side="left", padx=(0, PAD_M))
        _make_radio(
            mode_row, text="Auto (Δ moyen − σ)",
            variable=self.burst_mode, value="auto",
            command=lambda: self._refresh_burst_mode_ui(),
        ).pack(side="left")

        # Ligne 2 : Écart max (visible seulement en mode manuel)
        self._burst_manual_row = ctk.CTkFrame(burst_sub, fg_color="transparent")
        self._burst_manual_row.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(self._burst_manual_row, text="Écart max :", width=80, anchor="w",
                     font=font_hint(), text_color=HINT_COLOR).pack(side="left")
        ctk.CTkOptionMenu(
            self._burst_manual_row, variable=self.burst_threshold,
            values=["1", "2", "3", "5", "10", "30", "60"],
            width=70, height=BTN_H_STD,
            command=lambda v: self.burst_threshold.set(int(v)),
        ).pack(side="left", padx=PAD_S)
        ctk.CTkLabel(self._burst_manual_row, text="s",
                     font=font_hint(), text_color=HINT_COLOR).pack(side="left")

        # Ligne 3 : Min photos par burst (visible dans les 2 modes)
        min_row = ctk.CTkFrame(burst_sub, fg_color="transparent")
        min_row.pack(fill="x")
        ctk.CTkLabel(min_row, text="Min photos :", width=80, anchor="w",
                     font=font_hint(), text_color=HINT_COLOR).pack(side="left")
        ctk.CTkOptionMenu(
            min_row, variable=self.burst_min_count,
            values=["2", "3", "4", "5", "8"], width=60, height=BTN_H_STD,
            command=lambda v: self.burst_min_count.set(int(v)),
        ).pack(side="left", padx=PAD_S)
        ctk.CTkLabel(
            min_row, text="par groupe",
            font=font_hint(), text_color=HINT_COLOR,
        ).pack(side="left")

        # État initial (manuel par défaut)
        self._refresh_burst_mode_ui()

        # Index export — séparateur + 2 cases compactes en bas
        ctk.CTkFrame(behaviors, height=1, fg_color=SEPARATOR_COLOR).pack(
            fill="x", padx=PAD_M, pady=(PAD_S, PAD_S)
        )
        idx_row = ctk.CTkFrame(behaviors, fg_color="transparent")
        idx_row.pack(fill="x", padx=PAD_M, pady=(0, PAD_S))
        ctk.CTkLabel(idx_row, text="📋 Index :",
                     font=font_label()).pack(side="left", padx=(0, PAD_S))
        _make_checkbox(idx_row, text="CSV",
                       variable=self.export_index_csv).pack(side="left", padx=(0, PAD_M))
        _make_checkbox(idx_row, text="JSON",
                       variable=self.export_index_json).pack(side="left")

    def _toggle_advanced_section(self):
        """Bascule le panneau Avancé (collapse/expand)."""
        if self._adv_collapsed:
            # Affiche le contenu
            self._adv_content.grid(row=1, column=0, sticky="ew",
                                   padx=PAD_M, pady=(0, PAD_M))
            self._adv_toggle_btn.configure(
                text="▼  ⚙️ Options avancées (cliquez pour replier)"
            )
            self._adv_collapsed = False
        else:
            self._adv_content.grid_forget()
            self._adv_toggle_btn.configure(
                text="▶  ⚙️ Options avancées (filtres, comportements, bursts, …)"
            )
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
        """Section "Renommage" repliable avec layout 2 colonnes.

        Layout :
          ▼ 🏷️ Renommage & Presets   ← bouton de pliage / dépliage
          ┌────────────────────────┬──────────────────────────────────┐
          │ Exemples (cliquables)   │ Template [_____________________]│
          │  • Garder nom origine   │ Aperçu :                         │
          │  • Date YYYYMMDD        │   IMG_0001.jpg → 20260507_…      │
          │  • Date + compteur      │                                  │
          │  • …                    │ Tokens : {original}, {ext}, …    │
          │                         │                                  │
          │  [Réinitialiser]        │ Preset : […▼] [💾] [🗑]           │
          └────────────────────────┴──────────────────────────────────┘

        L'état (replié/déplié) est persisté dans AppConfig.rename_collapsed.
        """
        # Container externe — wrapper qui contient le toggle + le contenu
        wrapper = ctk.CTkFrame(self._scroll)
        wrapper.grid(row=2, column=0, columnspan=2, sticky="ew",
                     padx=PAD_S, pady=(PAD_S, 0))
        wrapper.columnconfigure(0, weight=1)

        # En-tête cliquable — toggle ▼ / ▶
        self._rename_collapsed = bool(
            getattr(get_config().config, 'rename_collapsed', False)
        )
        self._rename_toggle_btn = ctk.CTkButton(
            wrapper,
            text=self._rename_toggle_label(),
            command=self._toggle_rename_section,
            anchor="w",
            font=font_section(),
            fg_color="transparent",
            text_color=("gray10", "#DCE4EE"),
            hover_color=("gray85", "gray25"),
            height=BTN_H_STD,
        )
        self._rename_toggle_btn.grid(row=0, column=0, sticky="ew",
                                     padx=PAD_M, pady=PAD_S)

        # Content frame (2 colonnes) — affiché ou caché selon état
        self._rename_content = ctk.CTkFrame(wrapper, fg_color="transparent")
        self._rename_content.columnconfigure(0, weight=1, uniform="rn")
        self._rename_content.columnconfigure(1, weight=2, uniform="rn")

        # ===== Colonne gauche : exemples cliquables =====
        examples_box = ctk.CTkFrame(self._rename_content)
        examples_box.grid(row=0, column=0, sticky="nsew",
                          padx=(PAD_M, PAD_S), pady=(0, PAD_M))

        ctk.CTkLabel(
            examples_box, text="📋 Exemples cliquables",
            font=font_label(weight="bold"),
        ).pack(anchor="w", padx=PAD_S, pady=(PAD_S, PAD_S))

        # Scrollable list (les 10 exemples, ~28 px par ligne)
        from ui.prompt_examples import RENAME_TEMPLATES
        examples_scroll = ctk.CTkScrollableFrame(
            examples_box, height=180, fg_color="transparent",
        )
        examples_scroll.pack(fill="both", expand=True, padx=PAD_S, pady=(0, PAD_S))

        self._rename_example_btns = []
        for tpl in RENAME_TEMPLATES:
            row = ctk.CTkFrame(examples_scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)
            btn = ctk.CTkButton(
                row, text=f"• {tpl.label}",
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("gray10", "#DCE4EE"),
                command=lambda t=tpl.template: self._apply_rename_example(t),
                height=24, font=font_label(),
            )
            btn.pack(fill="x")
            self._rename_example_btns.append((btn, tpl))

        # Bouton Réinitialiser
        ctk.CTkButton(
            examples_box, text="🔄 Réinitialiser",
            command=lambda: self._apply_rename_example(""),
            height=BTN_H_STD,
            font=font_label(),
        ).pack(fill="x", padx=PAD_S, pady=(PAD_S, PAD_S))

        # ===== Colonne droite : zone d'édition + presets =====
        edit_box = ctk.CTkFrame(self._rename_content)
        edit_box.grid(row=0, column=1, sticky="nsew",
                      padx=(0, PAD_M), pady=(0, PAD_M))
        edit_box.columnconfigure(1, weight=1)

        # Template entry (la "textbox" demandée par le prompt)
        ctk.CTkLabel(edit_box, text="Template :",
                     font=font_label()).grid(row=0, column=0, sticky="w",
                                             padx=PAD_M, pady=(PAD_M, PAD_S))
        self.rename_entry = ctk.CTkEntry(
            edit_box, textvariable=self.rename_template,
            placeholder_text="(vide = nom d'origine conservé)",
            height=BTN_H_STD, font=font_label(),
        )
        self.rename_entry.grid(row=0, column=1, sticky="ew",
                               padx=(0, PAD_M), pady=(PAD_M, PAD_S))

        # Aperçu live
        self.rename_preview_var = ctk.StringVar(value="(aucun template)")
        ctk.CTkLabel(edit_box, text="Aperçu :",
                     font=font_label()).grid(row=1, column=0, sticky="w",
                                             padx=PAD_M, pady=PAD_S)
        ctk.CTkLabel(
            edit_box, textvariable=self.rename_preview_var,
            font=font_hint(), text_color=HINT_COLOR, anchor="w", justify="left",
        ).grid(row=1, column=1, sticky="ew", padx=(0, PAD_M), pady=PAD_S)
        self.rename_template.trace_add(
            "write", lambda *_: self._refresh_rename_preview()
        )

        # Tokens disponibles + exemples concrets (audit 2026-05-15)
        ctk.CTkLabel(
            edit_box,
            text="Tokens : {original}, {ext}, {date:%Y%m%d}, {camera}, {counter:03d}",
            font=font_hint(), text_color=HINT_COLOR, anchor="w",
        ).grid(row=2, column=0, columnspan=2, sticky="ew",
               padx=PAD_M, pady=(PAD_S, 0))
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
            font=font_hint(), text_color=HINT_COLOR,
            anchor="w", justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="ew",
               padx=PAD_M, pady=(0, PAD_M))

        # Séparateur entre Renommage et Presets
        ctk.CTkFrame(edit_box, height=1, fg_color=SEPARATOR_COLOR).grid(
            row=4, column=0, columnspan=2, sticky="ew",
            padx=PAD_M, pady=(0, PAD_S),
        )

        # Ligne Presets
        ctk.CTkLabel(edit_box, text="Preset :",
                     font=font_label()).grid(row=5, column=0, sticky="w",
                                             padx=PAD_M, pady=(0, PAD_M))
        preset_row = ctk.CTkFrame(edit_box, fg_color="transparent")
        preset_row.grid(row=5, column=1, sticky="ew",
                        padx=(0, PAD_M), pady=(0, PAD_M))
        self._preset_menu = ctk.CTkOptionMenu(
            preset_row, variable=self.preset_name,
            values=self._list_preset_names(),
            command=self._on_preset_selected,
            width=180, height=BTN_H_STD,
        )
        self._preset_menu.pack(side="left", padx=(0, PAD_S))
        icon_button(preset_row, text="💾",
                    command=self._save_preset_dialog).pack(side="left", padx=(0, PAD_S))
        icon_button(preset_row, text="🗑",
                    command=self._delete_preset).pack(side="left")

        # État initial
        if not self._rename_collapsed:
            self._rename_content.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

    def _rename_toggle_label(self) -> str:
        return "▶  🏷️ Renommage & Presets" if self._rename_collapsed \
               else "▼  🏷️ Renommage & Presets"

    def _refresh_burst_mode_ui(self):
        """Affiche/cache la ligne Écart max selon le mode burst.

        Mode manuel → ligne visible (l'utilisateur règle le seuil)
        Mode auto   → ligne cachée (le seuil est calculé à l'exécution)
        """
        try:
            if self.burst_mode.get() == "manual":
                self._burst_manual_row.pack(fill="x", pady=(0, 2))
                # Réordonner avant la ligne min — repack après le pack_forget
                # du min n'est pas nécessaire ici car min_row n'est pas masquée.
            else:
                self._burst_manual_row.pack_forget()
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
            get_config().set('rename_collapsed', self._rename_collapsed)
        except Exception:
            pass

    def _apply_rename_example(self, template_str: str):
        """Applique un exemple de template à la zone d'édition."""
        self.rename_template.set(template_str)
        # Le trace_add appelle automatiquement _refresh_rename_preview

    def _create_actions_section(self):
        """Section actions en zone bottom fixe (toujours visible).

        Layout :
          ProgressBar (row 0)
          Label progression (row 1)
          [📊 Analyser] [👁 Aperçu]   <-spacer->   [❌ Annuler] [🚀 Organiser]
                                                              (action principale à droite)

        Le compteur fichiers est en zone TOP (sous Source/Destination), pas
        ici — l'utilisateur le voit avant même de regarder les boutons.
        """
        parent = self._bottom_zone
        parent.columnconfigure(0, weight=1)

        # Lot B (audit 2026-05-14, T-036) : progress bar plus visible.
        # height 14 → 20 ; ajout d'une bordure matérialisant la track à 0 % ;
        # label numérique « 0 % » toujours présent à droite pour qu'on
        # repère immédiatement où est l'indicateur.
        progress_row = ctk.CTkFrame(parent, fg_color="transparent")
        progress_row.grid(row=0, column=0, sticky="ew", pady=(0, PAD_S))
        progress_row.columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            progress_row, height=20,
            border_width=1, border_color=("gray60", "gray40"),
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, PAD_S))
        self.progress_bar.set(0)

        self.progress_pct_var = ctk.StringVar(value="0 %")
        ctk.CTkLabel(
            progress_row, textvariable=self.progress_pct_var,
            font=font_label(weight="bold"), width=44, anchor="e",
        ).grid(row=0, column=1, sticky="e")

        # Label de progression
        self.progress_label = ctk.CTkLabel(
            parent, text="Prêt",
            font=font_label(), anchor="w",
            text_color=LABEL_MUTED,
        )
        self.progress_label.grid(row=1, column=0, sticky="ew", pady=(0, PAD_S))

        # Rangée de boutons : actions secondaires à gauche, principales à droite
        buttons = ctk.CTkFrame(parent, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew")
        # 4 colonnes : 2 boutons gauche, expanding spacer, 2 boutons droite
        buttons.columnconfigure(2, weight=1)

        # GAUCHE : actions secondaires (analyse, preview)
        self.analyze_button = neutral_button(
            buttons, text="📊 Analyser", command=self._analyze_files,
        )
        self.analyze_button.grid(row=0, column=0, padx=(0, PAD_S), sticky="w")

        self.preview_button = neutral_button(
            buttons, text="👁 Aperçu", command=self._show_dry_run_preview,
        )
        self.preview_button.grid(row=0, column=1, padx=(0, PAD_S), sticky="w")

        # DROITE : annuler (destructif) + action principale
        self.cancel_button = danger_button(
            buttons, text="❌ Annuler",
            command=self._cancel_operation, state="disabled",
        )
        self.cancel_button.grid(row=0, column=3, padx=(0, PAD_S), sticky="e")

        self.organize_button = primary_button(
            buttons, text="🚀 Organiser", command=self._organize_files,
        )
        self.organize_button.grid(row=0, column=4, sticky="e")

    # ------------------------------------------------------------------
    # Ordre des critères en mode multicouche
    # ------------------------------------------------------------------
    CRITERIA_LABELS = {
        'date':     ('📅', 'Date'),
        'camera':   ('📷', 'Appareil'),
        'location': ('🌍', 'Localisation'),
    }
    CRITERIA_ENABLE_VAR = {
        'date':     'organize_by_date',
        'camera':   'organize_by_camera',
        'location': 'organize_by_location',
    }

    def _update_criteria_visibility(self):
        """Affiche/masque le panneau d'ordre selon le toggle multicouche."""
        if self.multilayer.get():
            self.criteria_order_frame.pack(fill="x", padx=20, pady=(0, 6))
        else:
            self.criteria_order_frame.pack_forget()

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
                font=ctk.CTkFont(size=LABEL_FONT_SIZE,
                                 weight="bold" if enabled else "normal"),
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
                row, text="▲", width=30, height=28,
                command=lambda k=key: self._move_criterion(k, -1),
                state="disabled" if index == 0 else "normal",
                fg_color=CHECK_FG, hover_color=CHECK_HOVER,
            )
            up_btn.pack(side="right", padx=(2, 6), pady=3)

            down_btn = ctk.CTkButton(
                row, text="▼", width=30, height=28,
                command=lambda k=key: self._move_criterion(k, 1),
                state="disabled" if index == n - 1 else "normal",
                fg_color=CHECK_FG, hover_color=CHECK_HOVER,
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
    MAX_DIST_FINE_STEP = 0.1   # pas 100 m via les boutons ◀ / ▶
    MAX_DIST_PRECISION = 10    # 1 / 0.1 → arrondi 100 m

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
        """Affiche/masque les sous-options GPS sous la case correspondante.

        Refonte W17/W18 : pack(after=self._gps_checkbox) pour que les
        sous-options apparaissent DIRECTEMENT sous « Par localisation GPS »
        et non en bas du panneau (après Organisation avancée).
        """
        if self.organize_by_location.get():
            self.gps_options_frame.pack(
                fill="x", padx=40, pady=(0, 4),
                after=self._gps_checkbox,
            )
        else:
            self.gps_options_frame.pack_forget()

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
                        v.set(';'.join(folders))
                    else:
                        v.set(folders[0])

                tk_widget.dnd_bind('<<Drop>>', _on_drop)
            logger.debug("Drag-and-drop active sur source/dest entries")
        except Exception as exc:
            logger.warning(f"Echec setup drag-and-drop : {exc}")

    @staticmethod
    def _parse_dnd_paths(raw: str) -> List[str]:
        """Parse la string DnD (paths séparés par espace, accolades autour
        des paths avec espaces sous Windows)."""
        out, buf, in_brace = [], "", False
        for c in raw:
            if c == '{':
                in_brace = True
            elif c == '}':
                in_brace = False
                if buf:
                    out.append(buf)
                    buf = ""
            elif c == ' ' and not in_brace:
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
                "IMG_0001.jpg", tpl,
                date_taken=datetime(2026, 5, 7, 14, 30),
                make="Sony", model="ILCE-7M3",
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
            'organize_by_date': self.organize_by_date,
            'organize_by_camera': self.organize_by_camera,
            'multilayer': self.multilayer,
            'copy_not_move': self.copy_not_move,
            'date_format': self.date_format,
            'recursive': self.recursive,
            'include_images': self.include_images,
            'include_raw': self.include_raw,
            'include_videos': self.include_videos,
            'filter_date_min': self.filter_date_min,
            'filter_date_max': self.filter_date_max,
            'filter_size_min': self.filter_size_min,
            'filter_size_max': self.filter_size_max,
            'filter_rating_min': self.filter_rating_min,
            'filter_keywords': self.filter_keywords,
            'skip_if_identical': self.skip_if_identical,
            'keep_raw_jpeg_pairs': self.keep_raw_jpeg_pairs,
            'cleanup_empty_source': self.cleanup_empty_source,
            'validate_disk_space': self.validate_disk_space,
            'export_index_csv': self.export_index_csv,
            'export_index_json': self.export_index_json,
            'notify_on_finish': self.notify_on_finish,
            'rename_template': self.rename_template,
        }
        for k, var in mapping.items():
            if k in data:
                try:
                    var.set(data[k])
                except Exception:
                    pass
        if 'criteria_order' in data:
            order = data['criteria_order']
            if isinstance(order, list) and all(c in self._criteria_order for c in order):
                self._criteria_order = list(order)
                self._render_criteria_order()
        logger.info(f"Preset '{name}' charge")

    def _save_preset_dialog(self):
        """Modale de sauvegarde de preset (audit 2026-05-15).

        Remplace l'ancien ``simpledialog.askstring`` (trop petit, illisible)
        par une vraie modale 520×360 avec :
        - Logo PhotoOrganizer en haut-gauche
        - Champ Nom (entry)
        - Récap synthétique de ce qui sera sauvegardé (label scrollable)
        - Boutons Annuler / Enregistrer
        """
        from ui.theme import BTN_H_PRIMARY, add_logo_to_modal

        win = ctk.CTkToplevel(self)
        win.title("Sauvegarder un preset")
        win.geometry("520x360")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.columnconfigure(1, weight=1)
        win.rowconfigure(3, weight=1)

        # Logo + titre (row 0)
        add_logo_to_modal(win, size=40, text="Sauvegarder un preset")

        # Champ Nom (row 1)
        ctk.CTkLabel(
            win, text="Nom du preset :",
            font=font_label(weight="bold"),
        ).grid(row=1, column=0, sticky="w", padx=PAD_L, pady=(PAD_M, PAD_S))
        name_var = ctk.StringVar()
        name_entry = ctk.CTkEntry(
            win, textvariable=name_var, height=BTN_H_STD,
            placeholder_text="ex : vacances-ete-2026",
        )
        name_entry.grid(row=1, column=1, sticky="ew",
                        padx=(0, PAD_L), pady=(PAD_M, PAD_S))
        name_entry.focus_set()

        # Hint nom (row 2)
        ctk.CTkLabel(
            win,
            text="    Caractères autorisés : lettres, chiffres, tirets, "
                 "soulignés. Pas d'espace.",
            font=font_hint(), text_color=HINT_COLOR,
            anchor="w", justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="ew",
               padx=PAD_L, pady=(0, PAD_S))

        # Récap des options sauvegardées (row 3, expand)
        recap_frame = ctk.CTkFrame(win)
        recap_frame.grid(row=3, column=0, columnspan=2, sticky="nsew",
                         padx=PAD_L, pady=PAD_S)
        ctk.CTkLabel(
            recap_frame, text="📋 Contenu du preset",
            font=font_label(weight="bold"), anchor="w",
        ).pack(fill="x", padx=PAD_M, pady=(PAD_S, 2))
        recap_box = ctk.CTkTextbox(recap_frame, height=140, font=font_hint())
        recap_box.pack(fill="both", expand=True, padx=PAD_M, pady=(0, PAD_M))
        # Construction du récap textuel
        recap_lines = [
            f"• Organisation : date={self.organize_by_date.get()}, "
            f"camera={self.organize_by_camera.get()}, "
            f"lieu={self.organize_by_location.get()}",
            f"• Multicouche : {self.multilayer.get()}  ·  "
            f"ordre={', '.join(self._criteria_order)}",
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
        recap_box.insert("end", "\n".join(recap_lines))
        recap_box.configure(state="disabled")

        # Boutons (row 4)
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.grid(row=4, column=0, columnspan=2, sticky="ew",
                     padx=PAD_L, pady=(0, PAD_L))
        btn_row.columnconfigure(1, weight=1)

        result = {"name": None}

        def _on_save():
            n = name_var.get().strip()
            if not n:
                messagebox.showerror(
                    "Preset", "Le nom est obligatoire.", parent=win,
                )
                return
            if any(c in n for c in r' /\:*?"<>|'):
                messagebox.showerror(
                    "Preset",
                    "Caractères interdits dans le nom (espace, /, \\, etc).",
                    parent=win,
                )
                return
            result["name"] = n
            win.destroy()

        ctk.CTkButton(
            btn_row, text="Annuler",
            command=win.destroy, height=BTN_H_STD,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            btn_row, text="💾 Enregistrer",
            command=_on_save, height=BTN_H_PRIMARY,
            font=font_label(weight="bold"),
        ).grid(row=0, column=2, sticky="e")

        # Raccourci Enter = enregistrer, Echap = annuler
        win.bind("<Return>", lambda _e: _on_save())
        win.bind("<Escape>", lambda _e: win.destroy())

        win.wait_window()

        name = result["name"]
        if not name:
            return
        data = {
            'organize_by_date': self.organize_by_date.get(),
            'organize_by_camera': self.organize_by_camera.get(),
            'multilayer': self.multilayer.get(),
            'copy_not_move': self.copy_not_move.get(),
            'date_format': self.date_format.get(),
            'recursive': self.recursive.get(),
            'include_images': self.include_images.get(),
            'include_raw': self.include_raw.get(),
            'include_videos': self.include_videos.get(),
            'criteria_order': list(self._criteria_order),
            'filter_date_min': self.filter_date_min.get(),
            'filter_date_max': self.filter_date_max.get(),
            'filter_size_min': self.filter_size_min.get(),
            'filter_size_max': self.filter_size_max.get(),
            'filter_rating_min': self.filter_rating_min.get(),
            'filter_keywords': self.filter_keywords.get(),
            'skip_if_identical': self.skip_if_identical.get(),
            'keep_raw_jpeg_pairs': self.keep_raw_jpeg_pairs.get(),
            'cleanup_empty_source': self.cleanup_empty_source.get(),
            'validate_disk_space': self.validate_disk_space.get(),
            'export_index_csv': self.export_index_csv.get(),
            'export_index_json': self.export_index_json.get(),
            'notify_on_finish': self.notify_on_finish.get(),
            'rename_template': self.rename_template.get(),
        }
        try:
            get_config().save_preset(name, data)
            self._refresh_preset_menu(select=name)
            messagebox.showinfo("Preset", f"Preset '{name}' enregistré.")
        except Exception as exc:
            messagebox.showerror("Preset", f"Sauvegarde échouée : {exc}")

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
        cfg.set('schedule_enabled', enabled)
        cfg.set('schedule_time', time_str)
        # Source / destination courantes mémorisées pour le run automatique.
        cfg.set('schedule_source', self.source_var.get())
        cfg.set('schedule_destination', self.dest_var.get())
        cfg.set('schedule_preset', self.preset_name.get())
        self._scheduler.configure(enabled, time_str)
        self._refresh_schedule_status()

    def _on_schedule_time_change(self):
        """Reconfigure le scheduler quand l'utilisateur modifie l'heure."""
        cfg = get_config()
        cfg.set('schedule_time', self.schedule_time.get().strip())
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
            self.schedule_status_var.set(
                f"⏰ Prochaine exécution : {nxt.strftime('%Y-%m-%d %H:%M')}"
            )

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
            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y'):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        keywords = [k.strip() for k in self.filter_keywords.get().split(',') if k.strip()]

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
                "Affiche la liste détaillée des fichiers détectés "
                "(jusqu'à 500) avec les filtres actuels.",
            )

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
        attach_tooltip(self.analyze_button,  TIPS["btn_analyze"])
        attach_tooltip(self.preview_button,  TIPS["btn_preview"])
        attach_tooltip(self.organize_button, TIPS["btn_organize"])
        attach_tooltip(self.cancel_button,   TIPS["btn_cancel"])

        # Filtres avancés (parcours descendants pour trouver les Entry par
        # textvariable — évite de stocker chaque widget individuellement)
        self._attach_tooltips_to_filter_entries()

    def _attach_tooltips_to_filter_entries(self):
        """Attache les tooltips aux Entry des filtres avancés via leur var."""
        var_to_tip = {
            id(self.filter_date_min):   TIPS["filter_date_min"],
            id(self.filter_date_max):   TIPS["filter_date_max"],
            id(self.filter_size_min):   TIPS["filter_size_min"],
            id(self.filter_size_max):   TIPS["filter_size_max"],
            id(self.filter_keywords):   TIPS["filter_keywords"],
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
                        (v for v in (
                            self.filter_date_min, self.filter_date_max,
                            self.filter_size_min, self.filter_size_max,
                            self.filter_keywords,
                        ) if str(v) == var_name and id(v) == var_id),
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

    def _show_files_list(self):
        """Modal listant les fichiers détectés dans la source (T-030..T-033).

        Affiche jusqu'à 500 chemins triés. Permet à l'utilisateur de vérifier
        VISUELLEMENT quels fichiers seront traités. Si > 500, affiche un
        message « ... et N de plus » pour rester réactif.

        Logo PhotoOrganizer en haut-gauche (audit 2026-05-15).
        """
        from ui.theme import add_logo_to_modal

        files = self._get_files()
        win = ctk.CTkToplevel(self)
        win.title("Fichiers détectés")
        win.geometry("700x540")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        # Logo haut-gauche
        add_logo_to_modal(
            win, size=40,
            text=f"📋 {len(files)} fichier(s) détecté(s) avec les filtres actuels",
        )

        # Container pour le reste
        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True)

        if not files:
            ctk.CTkLabel(
                body, text="Aucun fichier trouvé.",
                text_color=LABEL_MUTED,
            ).pack(padx=PAD_L, pady=PAD_M)
        else:
            box = ctk.CTkTextbox(body, font=font_hint())
            box.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_S)
            for i, f in enumerate(files[:500], 1):
                box.insert("end", f"{i:>4}.  {f}\n")
            if len(files) > 500:
                box.insert("end", f"\n… et {len(files) - 500} fichier(s) supplémentaire(s)")
            box.configure(state="disabled")

        ctk.CTkButton(
            body, text="Fermer", command=win.destroy,
            height=BTN_H_STD,
        ).pack(pady=PAD_M)

    def _refresh_file_count(self):
        """Met à jour le compteur de fichiers détectés sous les boutons.

        Affiche un état clair même quand aucun dossier n'est sélectionné
        (T-030..T-033). Limite intentionnellement le scan : utilise les
        mêmes filtres que `_get_files`. Pour les dossiers volumineux le
        comptage peut prendre quelques secondes — on l'execute en tâche
        de fond pour ne pas geler l'UI.
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
            # été détruit pendant que le thread démarrait — évite le
            # `RuntimeError: main thread is not in main loop` lors de
            # l'accès aux StringVar via `_get_files()`.
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
                else:
                    msg = f"📂 {shown} — {count} fichier(s) prêt(s) à être organisé(s)."
                self._safe_after(0, lambda m=msg: self.file_count_var.set(m))
            except RuntimeError:
                # Tk mainloop disparue (frame détruit pendant un get).
                return
            except (OSError, ValueError) as exc:
                err = str(exc)
                logger.warning(f"Comptage echoue: {err}")
                self._safe_after(
                    0, lambda m=err: self.file_count_var.set(f"Erreur de comptage : {m}")
                )

        threading.Thread(target=count_thread, daemon=True).start()

    def _analyze_files(self):
        """Analyse les fichiers du dossier source."""
        # D-01 (audit 2026-05-14) : pas de double-lancement pendant qu'une
        # opération tourne, et message clair si annulation en cours.
        if getattr(self, "_operation_running", False):
            if getattr(self, "_cancel_requested", False):
                messagebox.showinfo(
                    "Annulation en cours",
                    "L'opération est en cours d'annulation.\n"
                    "Patientez quelques secondes avant de relancer.",
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
            self._operation_running = True
            self._set_buttons_state(False)

            files = self._get_files()
            total = len(files)

            if total == 0:
                self._update_progress("Aucun fichier trouvé", 0)
                self._operation_running = False
                self._set_buttons_state(True)
                return

            # Statistiques
            stats = {
                'total': total,
                'with_date': 0,
                'with_camera': 0,
                'with_gps': 0,
                'by_year': {},
                'by_camera': {}
            }

            for i, file_path in enumerate(files):
                if self._cancel_requested:
                    break

                self._update_progress(
                    f"Analyse de {os.path.basename(file_path)} ({i+1}/{total})",
                    (i + 1) / total
                )

                try:
                    exif_data = get_exif_data(file_path)
                    date = extract_date(file_path, exif_data)
                    make, model = get_camera_info(exif_data, file_path)
                    gps = get_gps_coordinates(file_path)

                    if date:
                        stats['with_date'] += 1
                        year = date.year
                        stats['by_year'][year] = stats['by_year'].get(year, 0) + 1

                    if make != 'Unknown':
                        stats['with_camera'] += 1
                        camera = f"{make} {model}"
                        stats['by_camera'][camera] = stats['by_camera'].get(camera, 0) + 1

                    if gps[0] is not None:
                        stats['with_gps'] += 1

                except (OSError, ValueError) as exc:
                    logger.warning(f"Analyse echouee pour {file_path}: {exc}")

            self._operation_running = False
            self._set_buttons_state(True)
            self._show_analysis_results(stats)

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
                    "L'opération est en cours d'annulation.\n"
                    "Patientez quelques secondes avant de relancer.",
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

        # Confirmation
        action = "copier" if self.copy_not_move.get() else "déplacer"
        if not messagebox.askyesno(
            "Confirmation",
            f"Voulez-vous {action} les fichiers de:\n{source}\nvers:\n{dest}?"
        ):
            return

        def organize():
            self._operation_running = True
            self._cancel_requested = False
            self._set_buttons_state(False)

            files = self._get_files()
            total = len(files)

            if total == 0:
                self._update_progress("Aucun fichier trouvé", 0)
                self._operation_running = False
                self._set_buttons_state(True)
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
                self._operation_running = False
                self._set_buttons_state(True)

            # Afficher les résultats
            self._safe_after(0, lambda: self._show_organization_results(result))

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

Total de fichiers: {stats['total']}
Avec date: {stats['with_date']} ({stats['with_date']*100//max(1,stats['total'])}%)
Avec appareil: {stats['with_camera']} ({stats['with_camera']*100//max(1,stats['total'])}%)
Avec GPS: {stats['with_gps']} ({stats['with_gps']*100//max(1,stats['total'])}%)

Distribution par année:
{chr(10).join(f'  {y}: {c} fichiers' for y, c in sorted(stats['by_year'].items()))}

Distribution par appareil:
{chr(10).join(f'  {c}: {n} fichiers' for c, n in sorted(stats['by_camera'].items(), key=lambda x: -x[1])[:5])}
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
        with_gps = getattr(result, 'files_with_gps', 0)
        without_gps = getattr(result, 'files_without_gps', 0)
        if with_gps or without_gps:
            geocoded = getattr(result, 'files_geocoded', 0)
            raw_coords = getattr(result, 'files_raw_coords', 0)
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
                full_message += (
                    f"\n... et {len(result.error_messages) - 5} autres erreurs"
                )

        # Q5 — Notification système non-modale (fond + barre des tâches)
        if self.notify_on_finish.get():
            try:
                _windows_toast("PhotoOrganizer", summary.replace('\n', ' • '))
            except Exception as exc:
                logger.debug(f"toast non envoye : {exc}")

        # Modal récap avec bouton « Ouvrir destination »
        self._show_results_modal(full_message, dest=self.dest_var.get())
        self._update_progress("Organisation terminée", 1)

    def _show_results_modal(self, message: str, dest: str):
        """Modal résumé custom (au lieu de messagebox basique) avec un
        bouton « 📂 Ouvrir destination » qui ouvre l'explorateur natif.

        Logo PhotoOrganizer en haut-gauche (audit 2026-05-15).
        """
        from ui.theme import add_logo_to_modal

        win = ctk.CTkToplevel(self)
        win.title("Organisation terminée")
        win.geometry("520x360")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        # Logo haut-gauche (audit 2026-05-15)
        add_logo_to_modal(win, size=40, text="✅ Organisation terminée")

        # Container pour le reste (sous le logo)
        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True)

        textbox = ctk.CTkTextbox(body, height=180)
        textbox.pack(fill="both", expand=True, padx=12, pady=4)
        textbox.insert("end", message)
        textbox.configure(state="disabled")

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(4, 12))

        if dest:
            ctk.CTkButton(
                btn_row, text="📂 Ouvrir destination",
                command=lambda: _open_folder(dest),
            ).pack(side="left", padx=4, expand=True, fill="x")
        ctk.CTkButton(btn_row, text="Fermer", command=win.destroy).pack(
            side="left", padx=4, expand=True, fill="x"
        )

    def _show_dry_run_preview(self):
        """Q2 — Aperçu dry-run : applique les options pour les 100 premiers
        fichiers et affiche l'arborescence cible dans une modale, **sans
        copier ni déplacer aucun fichier**.
        """
        sources = self._split_sources()
        dest = self.dest_var.get().strip()
        if not sources:
            messagebox.showerror("Aperçu", "Sélectionnez au moins un dossier source.")
            return
        if not dest:
            messagebox.showerror("Aperçu", "Sélectionnez le dossier destination.")
            return

        files = self._get_files()
        if not files:
            messagebox.showinfo("Aperçu", "Aucun fichier détecté avec ces filtres.")
            return

        options = self._get_options()
        # On applique les filtres pré-traitement comme en réel
        organizer = SmartOrganizer(file_manager=self.file_manager)
        eligible = [f for f in files if organizer._passes_filters(f, options)]

        # Détection paires si demandé (impact visuel)
        pairs = (
            organizer._detect_raw_jpeg_pairs(eligible)
            if options.keep_raw_jpeg_pairs else {}
        )

        # Pour chaque fichier, calculer le chemin cible (sans copier)
        sample = eligible[:100]
        tree: dict = {}
        counter = 0
        for fp in sample:
            counter += 1
            try:
                exif = get_exif_data(fp)
                date_taken = extract_date(fp, exif)
                make, model = get_camera_info(exif, fp)
                path = dest
                # Critères dans l'ordre choisi
                if options.multilayer:
                    crits = options.criteria_order
                elif options.organize_by_date:
                    crits = ['date']
                elif options.organize_by_camera:
                    crits = ['camera']
                else:
                    crits = []
                for c in crits:
                    if c == 'date' and options.organize_by_date:
                        if date_taken:
                            y, m, d = (str(date_taken.year),
                                       f"{date_taken.month:02d}",
                                       f"{date_taken.day:02d}")
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
                    elif c == 'camera' and options.organize_by_camera:
                        cam = (f"{make} {model}".strip()
                               if (make != 'Unknown' or model != 'Unknown')
                               else "Appareil inconnu")
                        path = os.path.join(path, cam.replace('/', '_'))

                # Renommage
                fname = os.path.basename(fp)
                if options.rename_template:
                    try:
                        fname = SmartOrganizer._apply_rename_template(
                            fname, options.rename_template,
                            date_taken, make, model, counter,
                        )
                    except Exception:
                        pass
            except Exception as exc:
                logger.debug(f"preview erreur : {exc}")
                path = os.path.join(dest, "(erreur)")
                fname = os.path.basename(fp)

            tree.setdefault(path, []).append(fname)

        # Modale d'affichage — logo haut-gauche (audit 2026-05-15)
        from ui.theme import add_logo_to_modal

        win = ctk.CTkToplevel(self)
        win.title("Aperçu dry-run (sans modification disque)")
        win.geometry("760x580")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        add_logo_to_modal(win, size=40, text="Aperçu (dry-run)")

        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True)

        header_text = (
            f"📋 {len(eligible)} fichier(s) éligible(s) sur {len(files)} détecté(s)"
        )
        if options.keep_raw_jpeg_pairs and pairs:
            header_text += f"  •  {len(pairs)} paire(s) RAW+JPEG détectée(s)"
        header_text += f"\n📁 Destination : {dest}"
        if len(eligible) > 100:
            header_text += f"\n(Aperçu limité aux 100 premiers fichiers sur {len(eligible)})"
        ctk.CTkLabel(body, text=header_text, justify="left", anchor="w").pack(
            fill="x", padx=12, pady=(12, 4)
        )

        textbox = ctk.CTkTextbox(body, font=ctk.CTkFont(family="Consolas", size=11))
        textbox.pack(fill="both", expand=True, padx=12, pady=4)
        for folder in sorted(tree.keys()):
            rel = os.path.relpath(folder, dest) if dest in folder else folder
            textbox.insert("end", f"\n📁 {rel}/  ({len(tree[folder])} fichiers)\n")
            for f in tree[folder][:10]:
                textbox.insert("end", f"   • {f}\n")
            if len(tree[folder]) > 10:
                textbox.insert("end", f"   … {len(tree[folder]) - 10} de plus\n")
        textbox.configure(state="disabled")

        ctk.CTkButton(body, text="Fermer", command=win.destroy).pack(
            padx=12, pady=(4, 12)
        )
