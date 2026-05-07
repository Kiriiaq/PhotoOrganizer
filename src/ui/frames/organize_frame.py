"""
Frame d'organisation des fichiers.
Interface principale pour organiser les photos et vidéos.
"""

import os
import logging
import threading
from typing import Optional, Callable, List

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.operations import FileManager, SmartOrganizer, OrganizationOptions
from core.metadata import get_exif_data, extract_date, get_camera_info, get_gps_coordinates

logger = logging.getLogger(__name__)


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
        # tandis que ['camera', 'date'] crée
        #   Canon EOS R5 / YYYY / MM / YYYY_MM_DD / photo.jpg
        # NB : la fonctionnalité GPS / localisation a été retirée de l'IHM.
        self._criteria_order: List[str] = ['date', 'camera']
        self._criteria_rows: dict = {}  # key -> (frame, label, up_btn, down_btn)

        # Options d'organisation
        self.organize_by_date = ctk.BooleanVar(value=True)
        self.organize_by_camera = ctk.BooleanVar(value=False)
        # GPS retiré de l'IHM : on conserve une variable interne à False pour
        # rester compatible avec OrganizationOptions, mais aucune commande UI
        # ne peut plus l'activer.
        self.organize_by_location = ctk.BooleanVar(value=False)
        self.multilayer = ctk.BooleanVar(value=False)
        self.copy_not_move = ctk.BooleanVar(value=True)
        self.date_format = ctk.StringVar(value="year/month/day")
        self.recursive = ctk.BooleanVar(value=True)
        self.include_images = ctk.BooleanVar(value=True)
        self.include_raw = ctk.BooleanVar(value=True)
        self.include_videos = ctk.BooleanVar(value=False)

        self._create_ui()

        # Brancher le compteur de fichiers source — déclenche un scan léger
        # à chaque changement du dossier source ou des filtres.
        self.source_var.trace_add("write", lambda *_: self._refresh_file_count())
        for v in (self.recursive, self.include_images, self.include_raw, self.include_videos):
            v.trace_add("write", lambda *_: self._refresh_file_count())
        self._refresh_file_count()

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
        self._create_folders_section()
        self._create_options_section()
        self._create_actions_section()

    def _create_folders_section(self):
        """Crée la section de sélection des dossiers."""
        folders_frame = ctk.CTkFrame(self._scroll)
        folders_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        # Titre
        title = ctk.CTkLabel(
            folders_frame,
            text="📁 Sélection des dossiers",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.pack(anchor="w", padx=10, pady=(10, 5))

        # Dossier source
        source_frame = ctk.CTkFrame(folders_frame, fg_color="transparent")
        source_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(source_frame, text="Source:", width=80).pack(side="left")
        self.source_entry = ctk.CTkEntry(
            source_frame,
            textvariable=self.source_var,
            placeholder_text="Sélectionnez le dossier source..."
        )
        self.source_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            source_frame,
            text="📂",
            width=40,
            command=self._browse_source
        ).pack(side="left")

        # Dossier destination
        dest_frame = ctk.CTkFrame(folders_frame, fg_color="transparent")
        dest_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(dest_frame, text="Destination:", width=80).pack(side="left")
        self.dest_entry = ctk.CTkEntry(
            dest_frame,
            textvariable=self.dest_var,
            placeholder_text="Sélectionnez le dossier destination..."
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            dest_frame,
            text="📂",
            width=40,
            command=self._browse_dest
        ).pack(side="left")

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

        # NB : la fonctionnalité GPS / localisation a été retirée de l'IHM
        # (jugée hors-scope pour la version courante). Le code core
        # (`gps_processor`) reste en place pour ne pas régresser les tests
        # mais aucun widget ne l'expose à l'utilisateur.

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
            text="Organisation multicouche (combine date + appareil)",
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

    def _create_actions_section(self):
        """Crée la section des boutons d'action."""
        actions_frame = ctk.CTkFrame(self._scroll)
        actions_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

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
    }
    CRITERIA_ENABLE_VAR = {
        'date':     'organize_by_date',
        'camera':   'organize_by_camera',
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

    def _get_options(self) -> OrganizationOptions:
        """Retourne les options d'organisation actuelles.

        ``criteria_order`` est remonté tel qu'affiché (incluant les critères
        désactivés). Le SmartOrganizer ignore de toute façon ceux dont la
        case correspondante n'est pas cochée — le maintien dans la liste
        permet à l'utilisateur de les réactiver sans perdre son ordre.

        La fonctionnalité GPS étant retirée de l'IHM, ``organize_by_location``
        est forcé à False et ``max_distance_km``/``use_geocoding`` reprennent
        les valeurs par défaut du dataclass.
        """
        return OrganizationOptions(
            organize_by_date=self.organize_by_date.get(),
            organize_by_camera=self.organize_by_camera.get(),
            organize_by_location=False,
            multilayer=self.multilayer.get(),
            criteria_order=list(self._criteria_order),
            copy_not_move=self.copy_not_move.get(),
            date_format=self.date_format.get(),
        )

    def _get_files(self) -> List[str]:
        """Récupère la liste des fichiers à traiter (synchrone)."""
        source = self.source_var.get()
        if not source or not os.path.isdir(source):
            return []

        return self.file_manager.list_files(
            source,
            recursive=self.recursive.get(),
            include_images=self.include_images.get(),
            include_raw=self.include_raw.get(),
            include_videos=self.include_videos.get()
        )

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
        """Affiche les résultats de l'organisation."""
        message = f"""
Organisation terminée!

Total: {result.total}
Traités: {result.processed}
Ignorés: {result.skipped}
Erreurs: {result.errors}
"""
        if result.error_messages:
            message += "\nErreurs:\n" + "\n".join(result.error_messages[:5])
            if len(result.error_messages) > 5:
                message += f"\n... et {len(result.error_messages) - 5} autres erreurs"

        messagebox.showinfo("Organisation terminée", message)
        self._update_progress("Organisation terminée", 1)
