"""
Frame d'organisation des fichiers.
Interface principale pour organiser les photos et vidéos.
"""

import logging
import os
import subprocess
import sys
import threading
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Callable, List, Optional

import customtkinter as ctk

from core.metadata import extract_date, get_camera_info, get_exif_data, get_gps_coordinates
from core.operations import FileManager, OrganizationOptions, SmartOrganizer
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
        """Crée l'interface utilisateur.

        Toute la zone scrolle quand la fenêtre est réduite : on enveloppe
        les sections dans un ``CTkScrollableFrame`` qui prend toute la place
        disponible. Les `_create_*_section` continuent de placer leurs
        widgets en grille — la grille s'applique désormais sur l'intérieur
        scrollable.
        """
        # Layout root du frame OrganizeFrame
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=0, column=0, sticky="nsew")

        # Grille interne du scrollable
        self._scroll.columnconfigure(0, weight=1, minsize=300)
        self._scroll.columnconfigure(1, weight=1, minsize=300)
        # row=2 = section actions (boutons + progression) — doit s'étirer
        # mais sans absorber tout le scroll si l'utilisateur a peu d'espace.
        self._scroll.rowconfigure(2, weight=0)

        # Sections (parent commun = self._scroll)
        self._create_folders_section()      # row=0
        self._create_options_section()      # row=1 (critères + types)
        self._create_advanced_section()     # row=2 (filtres + comportements)
        # row=3 réservé bursts/incremental (intégrés dans advanced ci-dessus)
        self._create_schedule_section()     # row=4 (planification quotidienne)
        self._create_rename_section()       # row=5 (template + presets)
        self._create_actions_section()      # row=6 (boutons + progression)

    def _create_folders_section(self):
        """Crée la section de sélection des dossiers."""
        folders_frame = ctk.CTkFrame(self._scroll)
        folders_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        # Titre
        title_row = ctk.CTkFrame(folders_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(
            title_row,
            text="📁 Sélection des dossiers",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        # Hint sur les sources multiples + drag-and-drop
        hint = "💡 Plusieurs sources : séparer par ;"
        if DND_AVAILABLE:
            hint += "  •  Glisser-déposer un dossier supporté"
        ctk.CTkLabel(
            title_row, text=hint,
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray65"),
        ).pack(side="right")

        # Dossier source — accepte plusieurs chemins séparés par ';'
        source_frame = ctk.CTkFrame(folders_frame, fg_color="transparent")
        source_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(source_frame, text="Source(s) :", width=80).pack(side="left")
        self.source_entry = ctk.CTkEntry(
            source_frame,
            textvariable=self.source_var,
            placeholder_text="Sélectionnez le(s) dossier(s) source — séparés par ;"
        )
        self.source_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            source_frame,
            text="📂", width=40,
            command=self._browse_source
        ).pack(side="left")
        ctk.CTkButton(
            source_frame,
            text="+", width=40,
            command=self._add_source_folder,
        ).pack(side="left", padx=(2, 0))

        # Dossier destination
        dest_frame = ctk.CTkFrame(folders_frame, fg_color="transparent")
        dest_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(dest_frame, text="Destination :", width=80).pack(side="left")
        self.dest_entry = ctk.CTkEntry(
            dest_frame,
            textvariable=self.dest_var,
            placeholder_text="Sélectionnez le dossier destination..."
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            dest_frame, text="📂", width=40,
            command=self._browse_dest
        ).pack(side="left")
        ctk.CTkButton(
            dest_frame, text="📂 Ouvrir",
            width=90,
            command=lambda: _open_folder(self.dest_var.get()),
        ).pack(side="left", padx=(2, 0))

        # Activer le drag-and-drop si la lib est disponible
        self._setup_drag_drop()

    def _create_options_section(self):
        """Crée la section des options."""
        # Frame gauche - Critères d'organisation
        left_frame = ctk.CTkFrame(self._scroll)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

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
        _make_checkbox(
            left_frame,
            text="Par localisation GPS",
            variable=self.organize_by_location
        ).pack(anchor="w", padx=20, pady=3)

        # Sous-options GPS — cachées si organize_by_location est OFF
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
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)

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
        """Crée la section "Avancé" sur 2 colonnes (filtres + comportements)."""
        # Colonne gauche : filtres pré-traitement (R1)
        filters_frame = ctk.CTkFrame(self._scroll)
        filters_frame.grid(row=2, column=0, sticky="nsew", padx=(10, 5), pady=5)

        ctk.CTkLabel(
            filters_frame,
            text="🔍 Filtres pré-traitement",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Période de prise de vue
        date_row = ctk.CTkFrame(filters_frame, fg_color="transparent")
        date_row.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(date_row, text="Date min :", width=90, anchor="w").pack(side="left")
        ctk.CTkEntry(date_row, textvariable=self.filter_date_min,
                     placeholder_text="YYYY-MM-DD", width=120).pack(side="left", padx=2)

        date_row2 = ctk.CTkFrame(filters_frame, fg_color="transparent")
        date_row2.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(date_row2, text="Date max :", width=90, anchor="w").pack(side="left")
        ctk.CTkEntry(date_row2, textvariable=self.filter_date_max,
                     placeholder_text="YYYY-MM-DD", width=120).pack(side="left", padx=2)

        # Taille
        size_row = ctk.CTkFrame(filters_frame, fg_color="transparent")
        size_row.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(size_row, text="Taille min :", width=90, anchor="w").pack(side="left")
        ctk.CTkEntry(size_row, textvariable=self.filter_size_min,
                     placeholder_text="ex. 100KB", width=120).pack(side="left", padx=2)

        size_row2 = ctk.CTkFrame(filters_frame, fg_color="transparent")
        size_row2.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(size_row2, text="Taille max :", width=90, anchor="w").pack(side="left")
        ctk.CTkEntry(size_row2, textvariable=self.filter_size_max,
                     placeholder_text="ex. 50MB", width=120).pack(side="left", padx=2)

        # Note EXIF
        rating_row = ctk.CTkFrame(filters_frame, fg_color="transparent")
        rating_row.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(rating_row, text="Note ≥ :", width=90, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(
            rating_row, variable=self.filter_rating_min,
            values=["0", "1", "2", "3", "4", "5"],
            width=70,
            command=lambda v: self.filter_rating_min.set(int(v)),
        ).pack(side="left", padx=2)
        ctk.CTkLabel(
            rating_row, text="(0 = pas de filtre)",
            font=ctk.CTkFont(size=11), text_color=("gray45", "gray65"),
        ).pack(side="left", padx=8)

        # Mots-clés
        kw_row = ctk.CTkFrame(filters_frame, fg_color="transparent")
        kw_row.pack(fill="x", padx=20, pady=(2, 10))
        ctk.CTkLabel(kw_row, text="Mots-clés :", width=90, anchor="w").pack(side="left")
        ctk.CTkEntry(kw_row, textvariable=self.filter_keywords,
                     placeholder_text="separés par , (vacances, mariage, …)",
                     ).pack(side="left", padx=2, fill="x", expand=True)

        # Colonne droite : comportements + index
        behaviors_frame = ctk.CTkFrame(self._scroll)
        behaviors_frame.grid(row=2, column=1, sticky="nsew", padx=(5, 10), pady=5)

        ctk.CTkLabel(
            behaviors_frame,
            text="🛠️ Comportements avancés",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        _make_checkbox(behaviors_frame,
            text="Skip si fichier identique déjà présent",
            variable=self.skip_if_identical,
        ).pack(anchor="w", padx=20, pady=3)

        _make_checkbox(behaviors_frame,
            text="Garder les paires RAW + JPEG ensemble",
            variable=self.keep_raw_jpeg_pairs,
        ).pack(anchor="w", padx=20, pady=3)

        _make_checkbox(behaviors_frame,
            text="Nettoyer les dossiers source vides (mode Déplacer)",
            variable=self.cleanup_empty_source,
        ).pack(anchor="w", padx=20, pady=3)

        _make_checkbox(behaviors_frame,
            text="Vérifier l'espace disque avant exécution",
            variable=self.validate_disk_space,
        ).pack(anchor="w", padx=20, pady=3)

        _make_checkbox(behaviors_frame,
            text="Notification système à la fin",
            variable=self.notify_on_finish,
        ).pack(anchor="w", padx=20, pady=3)

        # Index export
        ctk.CTkFrame(behaviors_frame, height=2,
                     fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            behaviors_frame, text="📋 Index post-organisation",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(0, 4))
        idx_row = ctk.CTkFrame(behaviors_frame, fg_color="transparent")
        idx_row.pack(fill="x", padx=20, pady=(0, 8))
        _make_checkbox(idx_row, text="CSV", variable=self.export_index_csv).pack(side="left", padx=(0, 12))
        _make_checkbox(idx_row, text="JSON", variable=self.export_index_json).pack(side="left")

        # ---- Bursts S1 ----
        ctk.CTkFrame(behaviors_frame, height=2,
                     fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            behaviors_frame, text="📸 Détection de rafales (bursts)",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(0, 4))
        _make_checkbox(behaviors_frame,
            text="Regrouper les photos prises en rafale dans Burst_NN/",
            variable=self.detect_bursts,
        ).pack(anchor="w", padx=20, pady=3)

        burst_row = ctk.CTkFrame(behaviors_frame, fg_color="transparent")
        burst_row.pack(fill="x", padx=40, pady=(0, 4))
        ctk.CTkLabel(burst_row, text="Écart max :", width=100, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(
            burst_row, variable=self.burst_threshold,
            values=["1", "2", "3", "5", "10"], width=70,
            command=lambda v: self.burst_threshold.set(int(v)),
        ).pack(side="left", padx=2)
        ctk.CTkLabel(burst_row, text="s",
                     font=ctk.CTkFont(size=11),
                     text_color=("gray45", "gray65")).pack(side="left", padx=(2, 12))
        ctk.CTkLabel(burst_row, text="Min photos :", width=90, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(
            burst_row, variable=self.burst_min_count,
            values=["2", "3", "4", "5", "8"], width=70,
            command=lambda v: self.burst_min_count.set(int(v)),
        ).pack(side="left", padx=2)

        # ---- Incremental S5 ----
        ctk.CTkFrame(behaviors_frame, height=2,
                     fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            behaviors_frame, text="⚡ Mode incrémental",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(0, 4))
        _make_checkbox(behaviors_frame,
            text="Skip les fichiers déjà organisés (cache hash partiel)",
            variable=self.incremental_mode,
        ).pack(anchor="w", padx=20, pady=3)
        ctk.CTkLabel(
            behaviors_frame,
            text="    L'index est persisté dans <destination>/.photoorganizer_index.json",
            font=ctk.CTkFont(size=11), text_color=("gray45", "gray65"),
        ).pack(anchor="w", padx=20, pady=(0, 8))

    def _create_schedule_section(self):
        """Section "Planification automatique" (Lot E5)."""
        sched_frame = ctk.CTkFrame(self._scroll)
        sched_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(
            sched_frame,
            text="📅 Planification automatique quotidienne",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            sched_frame,
            text="Tant que l'application est ouverte, organise automatiquement à l'heure indiquée.",
            font=ctk.CTkFont(size=11), text_color=("gray45", "gray65"),
        ).pack(anchor="w", padx=10, pady=(0, 6))

        row = ctk.CTkFrame(sched_frame, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=4)

        self.schedule_switch = ctk.CTkSwitch(
            row,
            text="Activer la planification quotidienne",
            variable=self.schedule_enabled,
            command=self._on_schedule_toggle,
            font=ctk.CTkFont(size=CHECKBOX_FONT_SIZE),
            progress_color=CHECK_FG,
        )
        self.schedule_switch.pack(side="left")

        ctk.CTkLabel(row, text="Heure :",
                     font=ctk.CTkFont(size=LABEL_FONT_SIZE)).pack(side="left", padx=(20, 4))
        ctk.CTkEntry(row, textvariable=self.schedule_time,
                     placeholder_text="HH:MM", width=80).pack(side="left", padx=2)

        ctk.CTkLabel(
            sched_frame, textvariable=self.schedule_status_var,
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70"),
        ).pack(anchor="w", padx=20, pady=(2, 10))

    def _create_rename_section(self):
        """Crée la section "Renommage par template" + Presets."""
        rename_frame = ctk.CTkFrame(self._scroll)
        rename_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        # --- Renommage Q4 ---
        ctk.CTkLabel(
            rename_frame,
            text="🏷️ Renommage par template (optionnel)",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        tpl_row = ctk.CTkFrame(rename_frame, fg_color="transparent")
        tpl_row.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(tpl_row, text="Template :", width=90, anchor="w").pack(side="left")
        ctk.CTkEntry(
            tpl_row, textvariable=self.rename_template,
            placeholder_text="ex. {date:%Y%m%d}_{counter:04d}_{original}",
        ).pack(side="left", fill="x", expand=True, padx=2)

        # Aperçu live
        self.rename_preview_var = ctk.StringVar(value="(aucun template)")
        preview_row = ctk.CTkFrame(rename_frame, fg_color="transparent")
        preview_row.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(preview_row, text="Aperçu :", width=90, anchor="w").pack(side="left")
        ctk.CTkLabel(preview_row, textvariable=self.rename_preview_var,
                     text_color=("gray30", "gray70")).pack(side="left", padx=2)
        self.rename_template.trace_add("write", lambda *_: self._refresh_rename_preview())

        ctk.CTkLabel(
            rename_frame,
            text="Tokens : {original}, {ext}, {date:%Y%m%d}, {camera}, {counter:03d}",
            font=ctk.CTkFont(size=11), text_color=("gray45", "gray65"),
        ).pack(anchor="w", padx=20, pady=(2, 8))

        # --- Presets Q3 ---
        ctk.CTkFrame(rename_frame, height=2,
                     fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=(4, 6))
        ctk.CTkLabel(
            rename_frame,
            text="💾 Presets de configuration",
            font=ctk.CTkFont(size=SECTION_TITLE_SIZE, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(0, 4))

        preset_row = ctk.CTkFrame(rename_frame, fg_color="transparent")
        preset_row.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(preset_row, text="Preset :", width=90, anchor="w").pack(side="left")
        self._preset_menu = ctk.CTkOptionMenu(
            preset_row,
            variable=self.preset_name,
            values=self._list_preset_names(),
            command=self._on_preset_selected,
            width=160,
        )
        self._preset_menu.pack(side="left", padx=2)
        ctk.CTkButton(preset_row, text="💾 Sauver…", width=100,
                      command=self._save_preset_dialog).pack(side="left", padx=4)
        ctk.CTkButton(preset_row, text="🗑 Suppr.", width=80,
                      command=self._delete_preset).pack(side="left", padx=2)

    def _create_actions_section(self):
        """Crée la section des boutons d'action."""
        actions_frame = ctk.CTkFrame(self._scroll)
        actions_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        # Compteur de fichiers détectés (T-030..T-033 : visible dès la
        # sélection du dossier source). Mis à jour par `_refresh_file_count`.
        self.file_count_var = ctk.StringVar(value="Aucun dossier source sélectionné.")
        self.file_count_label = ctk.CTkLabel(
            actions_frame,
            textvariable=self.file_count_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.file_count_label.pack(fill="x", padx=10, pady=(10, 2))

        # Barre de progression — visible dès l'init, état initial 0%
        self.progress_bar = ctk.CTkProgressBar(actions_frame, height=14)
        self.progress_bar.pack(fill="x", padx=10, pady=(2, 5))
        self.progress_bar.set(0)

        # Label de progression
        self.progress_label = ctk.CTkLabel(actions_frame, text="Prêt")
        self.progress_label.pack(padx=10, pady=5)

        # Boutons
        buttons_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=10, pady=10)

        self.analyze_button = ctk.CTkButton(
            buttons_frame,
            text="📊 Analyser",
            command=self._analyze_files
        )
        self.analyze_button.pack(side="left", padx=5, expand=True, fill="x")

        # Aperçu dry-run (Q2) — affiche l'arborescence finale sans rien copier
        self.preview_button = ctk.CTkButton(
            buttons_frame,
            text="👁 Aperçu",
            command=self._show_dry_run_preview,
        )
        self.preview_button.pack(side="left", padx=5, expand=True, fill="x")

        self.organize_button = ctk.CTkButton(
            buttons_frame,
            text="🚀 Organiser",
            command=self._organize_files,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.organize_button.pack(side="left", padx=5, expand=True, fill="x")

        self.cancel_button = ctk.CTkButton(
            buttons_frame,
            text="❌ Annuler",
            command=self._cancel_operation,
            state="disabled",
            fg_color="red",
            hover_color="darkred"
        )
        self.cancel_button.pack(side="left", padx=5, expand=True, fill="x")

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
        """Affiche/masque les sous-options GPS selon la case « Par localisation »."""
        if self.organize_by_location.get():
            # Re-pack juste après la case correspondante (on l'insère dans
            # l'ordre naturel — ici, avant la section Avancée).
            self.gps_options_frame.pack(fill="x", padx=20, pady=(0, 4))
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
        """Ajoute un dossier source supplémentaire (séparateur ;) — Lot R4."""
        folder = filedialog.askdirectory(title="Ajouter un dossier source")
        if not folder:
            return
        current = self.source_var.get().strip()
        if current:
            # Éviter les doublons
            existing = {p.strip() for p in current.split(';') if p.strip()}
            if folder not in existing:
                self.source_var.set(f"{current};{folder}")
        else:
            self.source_var.set(folder)

    def _split_sources(self) -> List[str]:
        """Découpe le source_var en liste de chemins (R4)."""
        raw = self.source_var.get().strip()
        if not raw:
            return []
        return [p.strip() for p in raw.split(';') if p.strip()]

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
        # Petit dialog inline via simpledialog — léger et natif tkinter
        from tkinter import simpledialog
        name = simpledialog.askstring(
            "Sauvegarder le preset", "Nom du preset :",
            parent=self.winfo_toplevel(),
        )
        if not name:
            return
        name = name.strip()
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
            self.after(0, self._organize_files)
        except Exception as exc:
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
            burst_threshold_seconds=self.burst_threshold.get(),
            burst_min_count=self.burst_min_count.get(),
            incremental_mode=self.incremental_mode.get(),
        )

    def _get_files(self) -> List[str]:
        """Récupère la liste des fichiers à traiter sur **toutes les sources**.

        R4 : prend en charge plusieurs sources séparées par ';' dans le champ.
        Les chemins inexistants sont ignorés silencieusement (logs debug).
        Les doublons inter-sources sont dédupliqués pour ne pas traiter
        deux fois le même chemin physique.
        """
        sources = self._split_sources()
        if not sources:
            return []

        all_files: List[str] = []
        seen: set = set()
        for src in sources:
            if not os.path.isdir(src):
                logger.debug(f"Source ignoree (inexistante) : {src}")
                continue
            files = self.file_manager.list_files(
                src,
                recursive=self.recursive.get(),
                include_images=self.include_images.get(),
                include_raw=self.include_raw.get(),
                include_videos=self.include_videos.get(),
            )
            for f in files:
                norm = os.path.normcase(os.path.abspath(f))
                if norm in seen:
                    continue
                seen.add(norm)
                all_files.append(f)
        return all_files

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
            try:
                files = self._get_files()
                count = len(files)
                shown = source if len(source) <= 70 else "…" + source[-67:]
                if count == 0:
                    msg = f"📂 {shown} — aucun fichier détecté avec les filtres actuels."
                else:
                    msg = f"📂 {shown} — {count} fichier(s) prêt(s) à être organisé(s)."
                self.after(0, lambda m=msg: self.file_count_var.set(m))
            except Exception as exc:
                err = str(exc)
                logger.warning(f"Comptage echoue: {err}")
                self.after(
                    0, lambda m=err: self.file_count_var.set(f"Erreur de comptage : {m}")
                )

        threading.Thread(target=count_thread, daemon=True).start()

    def _analyze_files(self):
        """Analyse les fichiers du dossier source."""
        source = self.source_var.get()
        if not source:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier source.")
            return

        if not os.path.isdir(source):
            messagebox.showerror("Erreur", "Le dossier source n'existe pas.")
            return

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
        """Lance l'organisation des fichiers."""
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
            self.after(0, lambda: self._show_organization_results(result))

        thread = threading.Thread(target=organize, daemon=True)
        thread.start()

    def _cancel_operation(self):
        """Annule l'opération en cours.

        Appelle ``cancel()`` sur le ``SmartOrganizer`` actif pour qu'il
        sorte de sa boucle d'organisation à la prochaine itération.
        Le flag local ``_cancel_requested`` reste utile pour la phase
        d'analyse et pour les conditions de boucle de scan.
        """
        self._cancel_requested = True
        if self._current_organizer is not None:
            try:
                self._current_organizer.cancel()
            except Exception as exc:
                logger.debug(f"_cancel_operation: {exc}")
        self._update_progress("Annulation en cours...", None)

    def _set_buttons_state(self, enabled: bool):
        """Active/désactive les boutons."""
        state = "normal" if enabled else "disabled"
        cancel_state = "disabled" if enabled else "normal"

        self.after(0, lambda: self.analyze_button.configure(state=state))
        self.after(0, lambda: self.organize_button.configure(state=state))
        self.after(0, lambda: self.cancel_button.configure(state=cancel_state))

    def _update_progress(self, message: str, progress: Optional[float]):
        """Met à jour la barre de progression."""
        def update():
            self.progress_label.configure(text=message)
            if progress is not None:
                self.progress_bar.set(progress)
            self.status_callback(message, progress)

        self.after(0, update)

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

        self.after(0, show)

    def _show_organization_results(self, result):
        """Affiche les résultats de l'organisation avec :
        - une notification système non-modale (Q5)
        - un dialog modal résumé + bouton « Ouvrir destination » (Q6).
        """
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
        """
        win = ctk.CTkToplevel(self)
        win.title("Organisation terminée")
        win.geometry("520x320")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        ctk.CTkLabel(
            win, text="✅ Organisation terminée",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=12, pady=(12, 6), anchor="w")

        textbox = ctk.CTkTextbox(win, height=180)
        textbox.pack(fill="both", expand=True, padx=12, pady=4)
        textbox.insert("end", message)
        textbox.configure(state="disabled")

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
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

        # Modale d'affichage
        win = ctk.CTkToplevel(self)
        win.title("Aperçu dry-run (sans modification disque)")
        win.geometry("760x540")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        header_text = (
            f"📋 {len(eligible)} fichier(s) éligible(s) sur {len(files)} détecté(s)"
        )
        if options.keep_raw_jpeg_pairs and pairs:
            header_text += f"  •  {len(pairs)} paire(s) RAW+JPEG détectée(s)"
        header_text += f"\n📁 Destination : {dest}"
        if len(eligible) > 100:
            header_text += f"\n(Aperçu limité aux 100 premiers fichiers sur {len(eligible)})"
        ctk.CTkLabel(win, text=header_text, justify="left", anchor="w").pack(
            fill="x", padx=12, pady=(12, 4)
        )

        textbox = ctk.CTkTextbox(win, font=ctk.CTkFont(family="Consolas", size=11))
        textbox.pack(fill="both", expand=True, padx=12, pady=4)
        for folder in sorted(tree.keys()):
            rel = os.path.relpath(folder, dest) if dest in folder else folder
            textbox.insert("end", f"\n📁 {rel}/  ({len(tree[folder])} fichiers)\n")
            for f in tree[folder][:10]:
                textbox.insert("end", f"   • {f}\n")
            if len(tree[folder]) > 10:
                textbox.insert("end", f"   … {len(tree[folder]) - 10} de plus\n")
        textbox.configure(state="disabled")

        ctk.CTkButton(win, text="Fermer", command=win.destroy).pack(
            padx=12, pady=(4, 12)
        )
