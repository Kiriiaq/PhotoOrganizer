"""
Frame d'organisation des fichiers.
Interface principale pour organiser les photos et vidéos.
"""

import os
import threading
from typing import Optional, Callable, List

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.operations import FileManager, SmartOrganizer, OrganizationOptions
from core.metadata import get_exif_data, extract_date, get_camera_info, get_gps_coordinates


class OrganizeFrame(ctk.CTkFrame):
    """Frame d'organisation des fichiers."""

    def __init__(
        self,
        parent,
        source_var: ctk.StringVar,
        dest_var: ctk.StringVar,
        status_callback: Optional[Callable] = None
    ):
        """
        Initialise le frame d'organisation.

        Args:
            parent: Widget parent
            source_var: Variable pour le dossier source
            dest_var: Variable pour le dossier destination
            status_callback: Callback pour la barre de statut
        """
        super().__init__(parent, fg_color="transparent")

        self.source_var = source_var
        self.dest_var = dest_var
        self.status_callback = status_callback or (lambda m, p=None: None)

        # Variables d'état
        self._cancel_requested = False
        self._operation_running = False

        # Options d'organisation
        self.organize_by_date = ctk.BooleanVar(value=True)
        self.organize_by_camera = ctk.BooleanVar(value=False)
        self.organize_by_location = ctk.BooleanVar(value=False)
        self.multilayer = ctk.BooleanVar(value=False)
        self.copy_not_move = ctk.BooleanVar(value=True)
        self.date_format = ctk.StringVar(value="year/month/day")
        self.recursive = ctk.BooleanVar(value=True)
        self.include_images = ctk.BooleanVar(value=True)
        self.include_raw = ctk.BooleanVar(value=True)
        self.include_videos = ctk.BooleanVar(value=False)
        self.use_geocoding = ctk.BooleanVar(value=True)
        self.max_distance = ctk.DoubleVar(value=1.0)

        self._create_ui()

    def _create_ui(self):
        """Crée l'interface utilisateur."""
        # Grille principale
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        # Section dossiers
        self._create_folders_section()

        # Section options (gauche et droite)
        self._create_options_section()

        # Section actions
        self._create_actions_section()

    def _create_folders_section(self):
        """Crée la section de sélection des dossiers."""
        folders_frame = ctk.CTkFrame(self)
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
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        ctk.CTkLabel(
            left_frame,
            text="🗂️ Critères d'organisation",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Organiser par date
        ctk.CTkCheckBox(
            left_frame,
            text="Par date de prise de vue",
            variable=self.organize_by_date
        ).pack(anchor="w", padx=20, pady=2)

        # Format de date
        date_format_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        date_format_frame.pack(fill="x", padx=40, pady=2)

        ctk.CTkLabel(date_format_frame, text="Format:").pack(side="left")
        self.date_format_menu = ctk.CTkOptionMenu(
            date_format_frame,
            variable=self.date_format,
            values=["year/month/day", "year/month", "year", "year_month_day", "year_month"]
        )
        self.date_format_menu.pack(side="left", padx=5)

        # Organiser par appareil
        ctk.CTkCheckBox(
            left_frame,
            text="Par appareil photo",
            variable=self.organize_by_camera
        ).pack(anchor="w", padx=20, pady=2)

        # Organiser par localisation
        ctk.CTkCheckBox(
            left_frame,
            text="Par localisation GPS",
            variable=self.organize_by_location
        ).pack(anchor="w", padx=20, pady=2)

        # Options GPS
        gps_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        gps_frame.pack(fill="x", padx=40, pady=2)

        ctk.CTkCheckBox(
            gps_frame,
            text="Géocodage",
            variable=self.use_geocoding
        ).pack(side="left")

        ctk.CTkLabel(gps_frame, text="Distance max (km):").pack(side="left", padx=(10, 5))
        ctk.CTkEntry(
            gps_frame,
            textvariable=self.max_distance,
            width=50
        ).pack(side="left")

        # Mode multicouche
        ctk.CTkCheckBox(
            left_frame,
            text="Organisation multicouche",
            variable=self.multilayer
        ).pack(anchor="w", padx=20, pady=(10, 5))

        # Frame droite - Options de traitement
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)

        ctk.CTkLabel(
            right_frame,
            text="⚙️ Options de traitement",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Action
        action_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(action_frame, text="Action:").pack(side="left", padx=5)
        ctk.CTkRadioButton(
            action_frame,
            text="Copier",
            variable=self.copy_not_move,
            value=True
        ).pack(side="left", padx=10)
        ctk.CTkRadioButton(
            action_frame,
            text="Déplacer",
            variable=self.copy_not_move,
            value=False
        ).pack(side="left", padx=10)

        # Options avancées
        ctk.CTkCheckBox(
            right_frame,
            text="Parcourir les sous-dossiers",
            variable=self.recursive
        ).pack(anchor="w", padx=20, pady=2)

        # Types de fichiers
        ctk.CTkLabel(
            right_frame,
            text="Types de fichiers:",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkCheckBox(
            right_frame,
            text="Images (JPG, PNG, HEIC...)",
            variable=self.include_images
        ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkCheckBox(
            right_frame,
            text="RAW (ARW, CR2, NEF...)",
            variable=self.include_raw
        ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkCheckBox(
            right_frame,
            text="Vidéos (MP4, MOV, AVI...)",
            variable=self.include_videos
        ).pack(anchor="w", padx=20, pady=2)

    def _create_actions_section(self):
        """Crée la section des boutons d'action."""
        actions_frame = ctk.CTkFrame(self)
        actions_frame.grid(row=2, column=0, columnspan=2, sticky="sew", padx=10, pady=10)

        # Barre de progression
        self.progress_bar = ctk.CTkProgressBar(actions_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=(10, 5))
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
        """Retourne les options d'organisation actuelles."""
        return OrganizationOptions(
            organize_by_date=self.organize_by_date.get(),
            organize_by_camera=self.organize_by_camera.get(),
            organize_by_location=self.organize_by_location.get(),
            multilayer=self.multilayer.get(),
            copy_not_move=self.copy_not_move.get(),
            date_format=self.date_format.get(),
            max_distance_km=self.max_distance.get(),
            use_geocoding=self.use_geocoding.get()
        )

    def _get_files(self) -> List[str]:
        """Récupère la liste des fichiers à traiter."""
        source = self.source_var.get()
        if not source or not os.path.isdir(source):
            return []

        file_manager = FileManager()
        return file_manager.list_files(
            source,
            recursive=self.recursive.get(),
            include_images=self.include_images.get(),
            include_raw=self.include_raw.get(),
            include_videos=self.include_videos.get()
        )

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

                except Exception:
                    pass

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

            # Organiser
            organizer = SmartOrganizer()
            options = self._get_options()

            def progress_callback(current, total_files, message):
                self._update_progress(
                    f"{message} ({current}/{total_files})",
                    current / total_files
                )

            result = organizer.organize(files, dest, options, progress_callback)

            self._operation_running = False
            self._set_buttons_state(True)

            # Afficher les résultats
            self.after(0, lambda: self._show_organization_results(result))

        thread = threading.Thread(target=organize, daemon=True)
        thread.start()

    def _cancel_operation(self):
        """Annule l'opération en cours."""
        self._cancel_requested = True
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
            message += f"\nErreurs:\n" + "\n".join(result.error_messages[:5])
            if len(result.error_messages) > 5:
                message += f"\n... et {len(result.error_messages) - 5} autres erreurs"

        messagebox.showinfo("Organisation terminée", message)
        self._update_progress("Organisation terminée", 1)
