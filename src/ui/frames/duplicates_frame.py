# -*- coding: utf-8 -*-
"""
Frame avancé de détection et gestion des doublons.
Intègre toutes les fonctionnalités du DuplicateManager dans l'IHM.
"""

import os
import sys
import threading
from pathlib import Path
from typing import Optional, Callable, List
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Ensure src is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.duplicate_config import (
    DuplicateManagerConfig,
    FolderFilter,
    ExtensionFilter,
    ConservationPolicy,
    HashingConfig,
    PerformanceConfig,
    ExecutionMode,
    ConservationCriterion,
    HashAlgorithm,
    FileAction,
    FileDecision,
    DuplicateGroupDecision,
    ExecutionResult,
    load_config_from_yaml,
    save_config_to_yaml,
)
from src.core.operations.duplicate_manager import DuplicateManager
from src.core.operations.duplicate_finder import DuplicateFinder, DuplicateResult
from src.reports.duplicate_reporter import DuplicateReporter


class DuplicatesFrame(ctk.CTkFrame):
    """Frame avancé de détection et gestion des doublons."""

    def __init__(
        self,
        parent,
        source_var: ctk.StringVar,
        status_callback: Optional[Callable] = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.source_var = source_var
        self.status_callback = status_callback or (lambda m, p=None: None)

        self._cancel_requested = False
        self._operation_running = False
        self._duplicate_result: Optional[DuplicateResult] = None
        self._analysis_result: Optional[ExecutionResult] = None
        self._manager: Optional[DuplicateManager] = None

        # ========== Variables de configuration ==========

        # Mode d'exécution
        self.execution_mode = ctk.StringVar(value="DRY_RUN")

        # Dossier destination (pour mode MOVE)
        self.move_destination = ctk.StringVar()

        # Hashing
        self.algorithm = ctk.StringVar(value="sha256")
        self.quick_mode = ctk.BooleanVar(value=True)
        self.use_cache = ctk.BooleanVar(value=True)
        self.chunk_size = ctk.IntVar(value=4)

        # Scan
        self.recursive = ctk.BooleanVar(value=True)

        # Filtres fichiers
        self.include_images = ctk.BooleanVar(value=True)
        self.include_raw = ctk.BooleanVar(value=True)
        self.include_videos = ctk.BooleanVar(value=False)
        self.min_size_str = ctk.StringVar(value="0")
        self.max_size_str = ctk.StringVar(value="")

        # Conservation
        self.use_priority_folder = ctk.BooleanVar(value=True)
        self.use_preferred_ext = ctk.BooleanVar(value=True)
        self.date_criterion = ctk.StringVar(value="oldest")  # oldest/newest/none
        self.path_criterion = ctk.StringVar(value="shortest")  # shortest/longest/none
        self.priority_dirs_str = ctk.StringVar(value="")

        # Performance
        self.workers = ctk.IntVar(value=0)
        self.verify_before_delete = ctk.BooleanVar(value=False)

        # Rapports
        self.generate_csv = ctk.BooleanVar(value=False)
        self.generate_json = ctk.BooleanVar(value=False)
        self.generate_txt = ctk.BooleanVar(value=True)
        self.report_output_dir = ctk.StringVar(value="")

        self._create_ui()

    def _create_ui(self):
        """Crée l'interface utilisateur principale."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # === Section haute : dossier + mode ===
        self._create_header_section()

        # === Section centrale : onglets options + résultats ===
        self._create_main_section()

        # === Section basse : progression + actions ===
        self._create_actions_section()

    # =========================================================================
    # HEADER SECTION
    # =========================================================================

    def _create_header_section(self):
        """Section en-tête avec dossier source et mode d'exécution."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        # Titre
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            title_frame,
            text="Gestion avancee des doublons",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        # Boutons config YAML
        config_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        config_frame.pack(side="right")

        ctk.CTkButton(
            config_frame, text="Charger config", width=110,
            command=self._load_config_file
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            config_frame, text="Sauver config", width=110,
            command=self._save_config_file
        ).pack(side="left", padx=2)

        # Dossier source
        folder_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        folder_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(folder_frame, text="Dossier source:", width=100).pack(side="left")
        ctk.CTkEntry(
            folder_frame,
            textvariable=self.source_var,
            placeholder_text="Selectionnez un dossier a analyser..."
        ).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            folder_frame, text="Parcourir", width=80,
            command=self._browse_source
        ).pack(side="left")

        # Mode d'exécution + destination move
        mode_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        mode_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(mode_frame, text="Mode:", width=100).pack(side="left")

        modes = [
            ("Simulation", "DRY_RUN"),
            ("Supprimer", "DELETE"),
            ("Deplacer", "MOVE"),
            ("Corbeille", "TRASH"),
        ]
        for text, value in modes:
            ctk.CTkRadioButton(
                mode_frame, text=text, variable=self.execution_mode, value=value,
                command=self._on_mode_change
            ).pack(side="left", padx=8)

        # Destination (visible seulement en mode MOVE)
        self.dest_frame = ctk.CTkFrame(header_frame, fg_color="transparent")

        ctk.CTkLabel(self.dest_frame, text="Destination:", width=100).pack(side="left")
        ctk.CTkEntry(
            self.dest_frame,
            textvariable=self.move_destination,
            placeholder_text="Dossier de destination pour les doublons..."
        ).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            self.dest_frame, text="Parcourir", width=80,
            command=self._browse_destination
        ).pack(side="left")

    # =========================================================================
    # MAIN SECTION (Tabs: Options + Résultats)
    # =========================================================================

    def _create_main_section(self):
        """Section principale avec onglets."""
        self.main_tabview = ctk.CTkTabview(self)
        self.main_tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Onglets
        self.main_tabview.add("Options")
        self.main_tabview.add("Resultats")
        self.main_tabview.add("Details")

        self._create_options_tab()
        self._create_results_tab()
        self._create_details_tab()

    def _create_options_tab(self):
        """Onglet des options de scan."""
        tab = self.main_tabview.tab("Options")
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)

        # Colonne gauche : Hash + Filtres
        left_frame = ctk.CTkFrame(tab)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        self._create_hash_options(left_frame)
        self._create_filter_options(left_frame)

        # Colonne droite : Conservation + Performance + Rapports
        right_frame = ctk.CTkFrame(tab)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)

        self._create_conservation_options(right_frame)
        self._create_performance_options(right_frame)
        self._create_report_options(right_frame)

    def _create_hash_options(self, parent):
        """Options de hashing."""
        group = ctk.CTkFrame(parent)
        group.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            group, text="Algorithme de hash",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        row1 = ctk.CTkFrame(group, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row1, text="Algorithme:").pack(side="left")

        algorithms = ["sha256", "sha1", "md5"]
        if DuplicateFinder.is_algorithm_available("blake3"):
            algorithms.append("blake3")

        ctk.CTkOptionMenu(
            row1, variable=self.algorithm, values=algorithms, width=120
        ).pack(side="left", padx=10)

        ctk.CTkLabel(row1, text="Chunks (MB):").pack(side="left", padx=(10, 0))
        ctk.CTkOptionMenu(
            row1, variable=self.chunk_size,
            values=["1", "2", "4", "8", "16"], width=70,
            command=lambda v: self.chunk_size.set(int(v))
        ).pack(side="left", padx=5)

        row2 = ctk.CTkFrame(group, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(2, 10))

        ctk.CTkCheckBox(
            row2, text="Mode rapide (hash partiel)", variable=self.quick_mode
        ).pack(side="left", padx=(0, 15))

        ctk.CTkCheckBox(
            row2, text="Cache de hash", variable=self.use_cache
        ).pack(side="left")

    def _create_filter_options(self, parent):
        """Options de filtrage des fichiers."""
        group = ctk.CTkFrame(parent)
        group.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            group, text="Filtres de fichiers",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Types de fichiers
        types_row = ctk.CTkFrame(group, fg_color="transparent")
        types_row.pack(fill="x", padx=10, pady=2)

        ctk.CTkCheckBox(
            types_row, text="Images", variable=self.include_images
        ).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(
            types_row, text="RAW", variable=self.include_raw
        ).pack(side="left", padx=10)
        ctk.CTkCheckBox(
            types_row, text="Videos", variable=self.include_videos
        ).pack(side="left", padx=10)
        ctk.CTkCheckBox(
            types_row, text="Recursif", variable=self.recursive
        ).pack(side="left", padx=10)

        # Taille min/max
        size_row = ctk.CTkFrame(group, fg_color="transparent")
        size_row.pack(fill="x", padx=10, pady=(2, 10))

        ctk.CTkLabel(size_row, text="Taille min:").pack(side="left")
        ctk.CTkEntry(
            size_row, textvariable=self.min_size_str,
            placeholder_text="ex: 1KB", width=80
        ).pack(side="left", padx=5)

        ctk.CTkLabel(size_row, text="Taille max:").pack(side="left", padx=(15, 0))
        ctk.CTkEntry(
            size_row, textvariable=self.max_size_str,
            placeholder_text="ex: 100MB", width=80
        ).pack(side="left", padx=5)

    def _create_conservation_options(self, parent):
        """Options de conservation (quel fichier garder)."""
        group = ctk.CTkFrame(parent)
        group.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            group, text="Regles de conservation",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            group, text="(Ordre de priorite pour choisir quel fichier garder)",
            font=ctk.CTkFont(size=11), text_color="gray"
        ).pack(anchor="w", padx=10, pady=(0, 5))

        # Critères
        criteria_frame = ctk.CTkFrame(group, fg_color="transparent")
        criteria_frame.pack(fill="x", padx=10, pady=2)

        ctk.CTkCheckBox(
            criteria_frame, text="1. Dossier prioritaire",
            variable=self.use_priority_folder
        ).pack(anchor="w", pady=1)

        ctk.CTkCheckBox(
            criteria_frame, text="2. Extension preferee (.raw > .tiff > .jpg)",
            variable=self.use_preferred_ext
        ).pack(anchor="w", pady=1)

        # Date
        date_frame = ctk.CTkFrame(criteria_frame, fg_color="transparent")
        date_frame.pack(anchor="w", pady=1, fill="x")

        ctk.CTkLabel(date_frame, text="3. Date:").pack(side="left")
        ctk.CTkRadioButton(
            date_frame, text="Plus ancien", variable=self.date_criterion, value="oldest"
        ).pack(side="left", padx=8)
        ctk.CTkRadioButton(
            date_frame, text="Plus recent", variable=self.date_criterion, value="newest"
        ).pack(side="left", padx=8)
        ctk.CTkRadioButton(
            date_frame, text="Ignorer", variable=self.date_criterion, value="none"
        ).pack(side="left", padx=8)

        # Path
        path_frame = ctk.CTkFrame(criteria_frame, fg_color="transparent")
        path_frame.pack(anchor="w", pady=1, fill="x")

        ctk.CTkLabel(path_frame, text="4. Chemin:").pack(side="left")
        ctk.CTkRadioButton(
            path_frame, text="Plus court", variable=self.path_criterion, value="shortest"
        ).pack(side="left", padx=8)
        ctk.CTkRadioButton(
            path_frame, text="Plus long", variable=self.path_criterion, value="longest"
        ).pack(side="left", padx=8)
        ctk.CTkRadioButton(
            path_frame, text="Ignorer", variable=self.path_criterion, value="none"
        ).pack(side="left", padx=8)

        # Dossiers prioritaires
        prio_frame = ctk.CTkFrame(group, fg_color="transparent")
        prio_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(prio_frame, text="Dossiers prioritaires:").pack(anchor="w")
        prio_input_frame = ctk.CTkFrame(prio_frame, fg_color="transparent")
        prio_input_frame.pack(fill="x", pady=2)

        ctk.CTkEntry(
            prio_input_frame,
            textvariable=self.priority_dirs_str,
            placeholder_text="Chemins separes par ;"
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(
            prio_input_frame, text="+", width=30,
            command=self._add_priority_dir
        ).pack(side="left")

    def _create_performance_options(self, parent):
        """Options de performance et sécurité."""
        group = ctk.CTkFrame(parent)
        group.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            group, text="Performance & Securite",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        row1 = ctk.CTkFrame(group, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(2, 10))

        ctk.CTkLabel(row1, text="Workers:").pack(side="left")
        ctk.CTkOptionMenu(
            row1, variable=self.workers,
            values=["0 (auto)", "1", "2", "4", "8"],
            width=100,
            command=lambda v: self.workers.set(int(v.split()[0]))
        ).pack(side="left", padx=10)

        ctk.CTkCheckBox(
            row1, text="Verifier hash avant suppression",
            variable=self.verify_before_delete
        ).pack(side="left", padx=(20, 0))

    def _create_report_options(self, parent):
        """Options de génération de rapports."""
        group = ctk.CTkFrame(parent)
        group.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            group, text="Rapports",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        row1 = ctk.CTkFrame(group, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=2)

        ctk.CTkCheckBox(
            row1, text="CSV", variable=self.generate_csv
        ).pack(side="left", padx=(0, 15))
        ctk.CTkCheckBox(
            row1, text="JSON", variable=self.generate_json
        ).pack(side="left", padx=15)
        ctk.CTkCheckBox(
            row1, text="TXT", variable=self.generate_txt
        ).pack(side="left", padx=15)

        row2 = ctk.CTkFrame(group, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(2, 10))

        ctk.CTkLabel(row2, text="Dossier rapports:").pack(side="left")
        ctk.CTkEntry(
            row2, textvariable=self.report_output_dir,
            placeholder_text="(meme dossier que source)", width=200
        ).pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(
            row2, text="...", width=30,
            command=self._browse_report_dir
        ).pack(side="left")

    # =========================================================================
    # RESULTS TAB
    # =========================================================================

    def _create_results_tab(self):
        """Onglet des résultats (résumé + liste groupes)."""
        tab = self.main_tabview.tab("Resultats")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        # Résumé en haut
        summary_frame = ctk.CTkFrame(tab)
        summary_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.summary_label = ctk.CTkLabel(
            summary_frame,
            text="Lancez une recherche pour voir les resultats.",
            justify="left",
            anchor="w"
        )
        self.summary_label.pack(fill="x", padx=10, pady=10)

        # Liste des groupes
        self.results_textbox = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=12))
        self.results_textbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    # =========================================================================
    # DETAILS TAB
    # =========================================================================

    def _create_details_tab(self):
        """Onglet détails avec décisions par groupe."""
        tab = self.main_tabview.tab("Details")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        self.details_textbox = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.details_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.details_textbox.insert("end", "Les details apparaitront apres l'analyse.")

    # =========================================================================
    # ACTIONS SECTION
    # =========================================================================

    def _create_actions_section(self):
        """Section d'actions en bas."""
        actions_frame = ctk.CTkFrame(self)
        actions_frame.grid(row=2, column=0, sticky="sew", padx=10, pady=(5, 10))

        # Progression
        progress_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", side="top")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(progress_frame, text="Pret")
        self.progress_label.pack(pady=3)

        # Boutons
        buttons_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.search_button = ctk.CTkButton(
            buttons_frame,
            text="Rechercher les doublons",
            command=self._start_scan,
            font=ctk.CTkFont(weight="bold"),
            height=36
        )
        self.search_button.pack(side="left", padx=5, expand=True, fill="x")

        self.execute_button = ctk.CTkButton(
            buttons_frame,
            text="Simuler les actions",
            command=self._execute_actions,
            state="disabled",
            fg_color="#28a745",
            hover_color="#218838",
            height=36
        )
        self.execute_button.pack(side="left", padx=5, expand=True, fill="x")

        self.cancel_button = ctk.CTkButton(
            buttons_frame,
            text="Annuler",
            command=self._cancel_operation,
            state="disabled",
            fg_color="#dc3545",
            hover_color="#c82333",
            height=36
        )
        self.cancel_button.pack(side="left", padx=5, expand=True, fill="x")

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _on_mode_change(self):
        """Gère le changement de mode d'exécution."""
        mode = self.execution_mode.get()
        if mode == "MOVE":
            self.dest_frame.pack(fill="x", padx=10, pady=(0, 10))
        else:
            self.dest_frame.pack_forget()

        # Met à jour le texte du bouton d'exécution
        mode_labels = {
            "DRY_RUN": "Simuler les actions",
            "DELETE": "Supprimer les doublons",
            "MOVE": "Deplacer les doublons",
            "TRASH": "Envoyer a la corbeille",
        }
        self.execute_button.configure(text=mode_labels.get(mode, "Executer"))

        # Couleur du bouton selon dangerosité
        if mode == "DELETE":
            self.execute_button.configure(fg_color="#dc3545", hover_color="#c82333")
        elif mode == "TRASH":
            self.execute_button.configure(fg_color="#fd7e14", hover_color="#e36209")
        elif mode == "MOVE":
            self.execute_button.configure(fg_color="#007bff", hover_color="#0056b3")
        else:
            self.execute_button.configure(fg_color="#28a745", hover_color="#218838")

    def _browse_source(self):
        """Dialogue de sélection du dossier source."""
        folder = filedialog.askdirectory(title="Selectionnez le dossier a analyser")
        if folder:
            self.source_var.set(folder)

    def _browse_destination(self):
        """Dialogue de sélection du dossier destination."""
        folder = filedialog.askdirectory(title="Selectionnez le dossier destination")
        if folder:
            self.move_destination.set(folder)

    def _browse_report_dir(self):
        """Dialogue de sélection du dossier de rapports."""
        folder = filedialog.askdirectory(title="Dossier pour les rapports")
        if folder:
            self.report_output_dir.set(folder)

    def _add_priority_dir(self):
        """Ajoute un dossier prioritaire."""
        folder = filedialog.askdirectory(title="Ajouter un dossier prioritaire")
        if folder:
            current = self.priority_dirs_str.get()
            if current:
                self.priority_dirs_str.set(f"{current};{folder}")
            else:
                self.priority_dirs_str.set(folder)

    def _load_config_file(self):
        """Charge la configuration depuis un fichier YAML."""
        file_path = filedialog.askopenfilename(
            title="Charger la configuration",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            config = load_config_from_yaml(file_path)
            self._apply_config_to_ui(config)
            messagebox.showinfo("Succes", f"Configuration chargee:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de chargement:\n{e}")

    def _save_config_file(self):
        """Sauvegarde la configuration dans un fichier YAML."""
        file_path = filedialog.asksaveasfilename(
            title="Sauvegarder la configuration",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            config = self._build_config()
            save_config_to_yaml(config, file_path)
            messagebox.showinfo("Succes", f"Configuration sauvegardee:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de sauvegarde:\n{e}")

    def _apply_config_to_ui(self, config: DuplicateManagerConfig):
        """Applique une configuration aux variables de l'UI."""
        if config.source_directories:
            self.source_var.set(config.source_directories[0])

        self.execution_mode.set(config.execution_mode.name)
        self._on_mode_change()

        if config.move_destination:
            self.move_destination.set(config.move_destination)

        self.algorithm.set(config.hashing.algorithm.value)
        self.quick_mode.set(config.hashing.use_quick_mode)
        self.use_cache.set(config.hashing.use_cache)
        self.chunk_size.set(config.hashing.chunk_size_mb)

        self.recursive.set(config.recursive)
        self.min_size_str.set(str(config.min_file_size) if config.min_file_size else "0")
        self.max_size_str.set(str(config.max_file_size) if config.max_file_size else "")

        if config.folders.priority:
            self.priority_dirs_str.set(";".join(config.folders.priority))

        self.verify_before_delete.set(config.verify_before_delete)
        self.workers.set(config.performance.max_workers)

        self.generate_csv.set(config.generate_csv)
        self.generate_json.set(config.generate_json)
        self.generate_txt.set(config.generate_txt)
        if config.report_output_dir:
            self.report_output_dir.set(config.report_output_dir)

        # Conservation
        has_priority = ConservationCriterion.PRIORITY_FOLDER in config.conservation.criteria_order
        has_ext = ConservationCriterion.PREFERRED_EXTENSION in config.conservation.criteria_order
        self.use_priority_folder.set(has_priority)
        self.use_preferred_ext.set(has_ext)

        if ConservationCriterion.OLDEST_DATE in config.conservation.criteria_order:
            self.date_criterion.set("oldest")
        elif ConservationCriterion.NEWEST_DATE in config.conservation.criteria_order:
            self.date_criterion.set("newest")
        else:
            self.date_criterion.set("none")

        if ConservationCriterion.SHORTEST_PATH in config.conservation.criteria_order:
            self.path_criterion.set("shortest")
        elif ConservationCriterion.LONGEST_PATH in config.conservation.criteria_order:
            self.path_criterion.set("longest")
        else:
            self.path_criterion.set("none")

    # =========================================================================
    # CONFIG BUILDING
    # =========================================================================

    def _parse_size(self, size_str: str) -> int:
        """Parse une chaîne de taille en octets."""
        if not size_str or not size_str.strip():
            return 0

        size_str = size_str.strip().upper()
        units = {
            'B': 1, 'KB': 1024, 'K': 1024,
            'MB': 1024**2, 'M': 1024**2,
            'GB': 1024**3, 'G': 1024**3,
        }

        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                number = size_str[:-len(unit)].strip()
                return int(float(number) * multiplier)

        try:
            return int(size_str)
        except ValueError:
            return 0

    def _get_extensions_for_types(self) -> List[str]:
        """Retourne les extensions basées sur les types sélectionnés."""
        extensions = []
        if self.include_images.get():
            extensions.extend(['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
                             '.webp', '.heic', '.heif', '.avif'])
        if self.include_raw.get():
            extensions.extend(['.raw', '.arw', '.cr2', '.cr3', '.nef', '.dng',
                             '.orf', '.rw2', '.raf', '.pef', '.srw'])
        if self.include_videos.get():
            extensions.extend(['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.webm',
                             '.m4v', '.flv', '.3gp'])
        return extensions

    def _build_config(self) -> DuplicateManagerConfig:
        """Construit la configuration depuis les variables UI."""
        config = DuplicateManagerConfig()

        # Source
        source = self.source_var.get().strip()
        if source:
            config.source_directories = [source]

        config.recursive = self.recursive.get()

        # Mode
        config.execution_mode = ExecutionMode[self.execution_mode.get()]
        if config.execution_mode == ExecutionMode.MOVE:
            config.move_destination = self.move_destination.get().strip() or None

        # Hash
        config.hashing = HashingConfig(
            algorithm=HashAlgorithm(self.algorithm.get()),
            chunk_size_mb=self.chunk_size.get(),
            use_quick_mode=self.quick_mode.get(),
            use_cache=self.use_cache.get()
        )

        # Filtres
        extensions = self._get_extensions_for_types()
        if extensions:
            config.extensions.include = extensions

        config.min_file_size = self._parse_size(self.min_size_str.get())
        max_size_str = self.max_size_str.get().strip()
        config.max_file_size = self._parse_size(max_size_str) if max_size_str else None

        # Conservation
        criteria = []
        if self.use_priority_folder.get():
            criteria.append(ConservationCriterion.PRIORITY_FOLDER)
        if self.use_preferred_ext.get():
            criteria.append(ConservationCriterion.PREFERRED_EXTENSION)

        date_crit = self.date_criterion.get()
        if date_crit == "oldest":
            criteria.append(ConservationCriterion.OLDEST_DATE)
        elif date_crit == "newest":
            criteria.append(ConservationCriterion.NEWEST_DATE)

        path_crit = self.path_criterion.get()
        if path_crit == "shortest":
            criteria.append(ConservationCriterion.SHORTEST_PATH)
        elif path_crit == "longest":
            criteria.append(ConservationCriterion.LONGEST_PATH)

        config.conservation = ConservationPolicy(criteria_order=criteria)

        # Dossiers prioritaires
        priority_str = self.priority_dirs_str.get().strip()
        if priority_str:
            config.folders.priority = [d.strip() for d in priority_str.split(";") if d.strip()]

        # Performance
        config.performance = PerformanceConfig(
            max_workers=self.workers.get(),
            show_progress=True
        )
        config.verify_before_delete = self.verify_before_delete.get()

        # Rapports
        config.generate_csv = self.generate_csv.get()
        config.generate_json = self.generate_json.get()
        config.generate_txt = self.generate_txt.get()
        report_dir = self.report_output_dir.get().strip()
        config.report_output_dir = report_dir if report_dir else None

        return config

    # =========================================================================
    # SCAN & ANALYSIS
    # =========================================================================

    def _start_scan(self):
        """Lance le scan et l'analyse des doublons."""
        source = self.source_var.get().strip()
        if not source:
            messagebox.showerror("Erreur", "Veuillez selectionner un dossier source.")
            return
        if not os.path.isdir(source):
            messagebox.showerror("Erreur", f"Le dossier n'existe pas:\n{source}")
            return

        # Validation mode MOVE
        if self.execution_mode.get() == "MOVE" and not self.move_destination.get().strip():
            messagebox.showerror("Erreur", "Veuillez specifier un dossier de destination.")
            return

        config = self._build_config()
        errors = config.validate()
        if errors:
            messagebox.showerror("Erreur de configuration", "\n".join(errors))
            return

        # Réinitialiser l'UI
        self._reset_results()
        self._set_running(True)

        def scan_thread():
            try:
                self._manager = DuplicateManager(config)

                # Phase 1: Scan
                self._update_progress("Scan des fichiers...", 0)
                all_files, dup_result = self._manager.scan(self._progress_callback)

                if self._cancel_requested:
                    self._update_progress("Annule.", 0)
                    self._set_running(False)
                    return

                self._duplicate_result = dup_result

                if not dup_result.duplicate_groups:
                    self.after(0, lambda: self._show_no_duplicates(dup_result))
                    self._set_running(False)
                    return

                # Phase 2: Analyze
                self._update_progress("Analyse des groupes...", 0.5)
                analysis = self._manager.analyze(dup_result, self._progress_callback)
                self._analysis_result = analysis

                # Afficher les résultats
                self.after(0, lambda: self._display_analysis(dup_result, analysis))

                self._update_progress(
                    f"Termine: {analysis.duplicate_groups} groupes, "
                    f"{analysis.total_duplicates} doublons",
                    1.0
                )

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erreur", str(e)))
                self._update_progress(f"Erreur: {e}", 0)

            finally:
                self._set_running(False)

        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()

    def _execute_actions(self):
        """Exécute les actions planifiées (suppression/déplacement/corbeille)."""
        if not self._analysis_result or not self._manager:
            return

        mode = self.execution_mode.get()

        # Confirmation
        if mode == "DRY_RUN":
            # En mode simulation, on génère juste les rapports
            self._generate_reports()
            messagebox.showinfo(
                "Simulation",
                "Mode simulation : aucun fichier modifie.\n"
                "Les rapports ont ete generes."
            )
            return

        total = self._analysis_result.total_duplicates
        space = self._format_size(self._analysis_result.space_recovered)

        mode_messages = {
            "DELETE": f"Supprimer definitivement {total} fichiers?\n"
                      f"Espace a recuperer: {space}\n\n"
                      "ATTENTION: Cette action est irreversible!",
            "MOVE": f"Deplacer {total} fichiers vers:\n"
                    f"{self.move_destination.get()}\n\n"
                    f"Espace libere: {space}",
            "TRASH": f"Envoyer {total} fichiers a la corbeille?\n"
                     f"Espace a recuperer: {space}",
        }

        message = mode_messages.get(mode, f"Traiter {total} fichiers?")

        if not messagebox.askyesno("Confirmation", message):
            return

        self._set_running(True)

        def execute_thread():
            try:
                result = self._manager.execute(
                    self._analysis_result,
                    self._progress_callback
                )
                self._analysis_result = result

                # Générer les rapports après exécution
                self._generate_reports()

                # Afficher le résultat
                self.after(0, lambda: self._show_execution_result(result))
                self._update_progress("Execution terminee.", 1.0)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erreur", str(e)))

            finally:
                self._set_running(False)

        thread = threading.Thread(target=execute_thread, daemon=True)
        thread.start()

    def _generate_reports(self):
        """Génère les rapports configurés."""
        if not self._analysis_result:
            return

        has_reports = (self.generate_csv.get() or self.generate_json.get()
                      or self.generate_txt.get())
        if not has_reports:
            return

        output_dir = self.report_output_dir.get().strip()
        if not output_dir:
            output_dir = self.source_var.get().strip() or os.getcwd()

        try:
            reporter = DuplicateReporter(self._analysis_result, output_dir)
            generated = []

            if self.generate_csv.get():
                path = reporter.generate_csv()
                generated.append(f"CSV: {path}")

            if self.generate_json.get():
                path = reporter.generate_json()
                generated.append(f"JSON: {path}")

            if self.generate_txt.get():
                path = reporter.generate_txt()
                generated.append(f"TXT: {path}")

            if generated:
                self._update_progress(f"Rapports generes dans: {output_dir}", None)

        except Exception as e:
            self.after(0, lambda: messagebox.showwarning(
                "Rapports", f"Erreur lors de la generation des rapports:\n{e}"
            ))

    # =========================================================================
    # DISPLAY METHODS
    # =========================================================================

    def _reset_results(self):
        """Réinitialise l'affichage des résultats."""
        self.summary_label.configure(text="Recherche en cours...")
        self.results_textbox.delete("1.0", "end")
        self.details_textbox.delete("1.0", "end")
        self._analysis_result = None
        self._duplicate_result = None
        self.execute_button.configure(state="disabled")

    def _show_no_duplicates(self, result: DuplicateResult):
        """Affiche le message quand aucun doublon n'est trouvé."""
        summary = (
            f"Fichiers analyses: {result.total_files}\n"
            f"Temps de scan: {result.scan_time:.1f}s\n\n"
            "Aucun doublon trouve."
        )
        self.summary_label.configure(text=summary)
        self.results_textbox.delete("1.0", "end")
        self.results_textbox.insert("end", "Aucun doublon detecte dans ce dossier.")
        self._update_progress("Aucun doublon trouve.", 1.0)

    def _display_analysis(self, dup_result: DuplicateResult, analysis: ExecutionResult):
        """Affiche les résultats d'analyse complets."""
        mode = self.execution_mode.get()

        # Résumé
        summary = (
            f"Fichiers analyses: {dup_result.total_files:,}  |  "
            f"Groupes: {analysis.duplicate_groups:,}  |  "
            f"Doublons: {analysis.total_duplicates:,}\n"
            f"Espace en doublons: {self._format_size(analysis.space_duplicates)}  |  "
            f"Temps: {dup_result.scan_time:.1f}s  |  "
            f"Mode: {mode}"
        )
        self.summary_label.configure(text=summary)

        # Activer le bouton d'exécution
        self.execute_button.configure(state="normal")

        # Affichage des groupes (onglet Résultats)
        self._display_groups_list(analysis)

        # Affichage des détails (onglet Détails)
        self._display_group_details(analysis)

        # Passer à l'onglet résultats
        self.main_tabview.set("Resultats")

    def _display_groups_list(self, analysis: ExecutionResult):
        """Affiche la liste des groupes dans l'onglet Résultats."""
        self.results_textbox.delete("1.0", "end")

        mode = self.execution_mode.get()
        mode_label = {"DRY_RUN": "SIMULATION", "DELETE": "SUPPRESSION",
                     "MOVE": "DEPLACEMENT", "TRASH": "CORBEILLE"}.get(mode, mode)

        self.results_textbox.insert("end", f"{'=' * 65}\n")
        self.results_textbox.insert("end", f"  ANALYSE DES DOUBLONS - MODE {mode_label}\n")
        self.results_textbox.insert("end", f"{'=' * 65}\n\n")

        self.results_textbox.insert("end",
            f"  Groupes: {analysis.duplicate_groups}  |  "
            f"A traiter: {analysis.total_duplicates}  |  "
            f"Espace: {self._format_size(analysis.space_duplicates)}\n\n"
        )

        for group in analysis.group_decisions:
            self.results_textbox.insert("end", f"{'-' * 65}\n")
            self.results_textbox.insert("end",
                f"GROUPE #{group.group_id}  "
                f"({group.files_count} fichiers, "
                f"{self._format_size(group.file_size)} chacun)\n"
            )

            for decision in group.decisions:
                if decision.action == FileAction.KEEP:
                    tag = "[GARDER] "
                elif decision.action == FileAction.DELETE:
                    tag = "[SUPPR.] "
                elif decision.action == FileAction.MOVE:
                    tag = "[DEPL.]  "
                elif decision.action == FileAction.TRASH:
                    tag = "[CORB.]  "
                else:
                    tag = "[?]      "

                self.results_textbox.insert("end", f"  {tag}{decision.file_path}\n")
                self.results_textbox.insert("end", f"           Raison: {decision.reason}\n")

            self.results_textbox.insert("end", "\n")

    def _display_group_details(self, analysis: ExecutionResult):
        """Affiche les détails dans l'onglet Détails."""
        self.details_textbox.delete("1.0", "end")

        self.details_textbox.insert("end", f"{'=' * 65}\n")
        self.details_textbox.insert("end", "  DETAILS DES DECISIONS\n")
        self.details_textbox.insert("end", f"{'=' * 65}\n\n")

        for group in analysis.group_decisions:
            self.details_textbox.insert("end", f"GROUPE #{group.group_id}\n")
            self.details_textbox.insert("end", f"  Hash: {group.hash_value}\n")
            self.details_textbox.insert("end", f"  Taille: {self._format_size(group.file_size)}\n")
            self.details_textbox.insert("end",
                f"  Espace recuperable: {self._format_size(group.space_recoverable)}\n\n"
            )

            for decision in group.decisions:
                action_str = decision.action.value.upper()
                self.details_textbox.insert("end", f"  [{action_str:6}] {decision.file_path}\n")
                self.details_textbox.insert("end", f"           Raison: {decision.reason}\n")

                if decision.target_path:
                    self.details_textbox.insert("end", f"           Dest:   {decision.target_path}\n")

                if decision.creation_time:
                    self.details_textbox.insert("end",
                        f"           Cree:   {decision.creation_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                if decision.modification_time:
                    self.details_textbox.insert("end",
                        f"           Modif:  {decision.modification_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )

                self.details_textbox.insert("end", "\n")

            self.details_textbox.insert("end", f"{'-' * 65}\n\n")

        # Erreurs
        if analysis.errors:
            self.details_textbox.insert("end", f"\n{'=' * 65}\n")
            self.details_textbox.insert("end", "  ERREURS\n")
            self.details_textbox.insert("end", f"{'=' * 65}\n\n")
            for error in analysis.errors:
                self.details_textbox.insert("end", f"  - {error}\n")

    def _show_execution_result(self, result: ExecutionResult):
        """Affiche le résultat de l'exécution."""
        mode = self.execution_mode.get()

        message = (
            f"Execution terminee ({mode})\n\n"
            f"Fichiers gardes:       {result.files_kept}\n"
            f"Fichiers supprimes:    {result.files_deleted}\n"
            f"Fichiers deplaces:     {result.files_moved}\n"
            f"Fichiers en corbeille: {result.files_trashed}\n"
            f"Erreurs:               {result.files_errored}\n\n"
            f"Espace recupere: {self._format_size(result.space_recovered)}"
        )

        if result.errors:
            message += f"\n\n{len(result.errors)} erreur(s) survenue(s)."

        report_note = ""
        if self.generate_csv.get() or self.generate_json.get() or self.generate_txt.get():
            report_note = "\n\nLes rapports ont ete generes."

        messagebox.showinfo("Execution terminee", message + report_note)

        # Mettre à jour l'affichage
        self.summary_label.configure(text=message.split('\n\n')[0])
        self._display_groups_list(result)
        self._display_group_details(result)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _progress_callback(self, current: int, total: int, message: str):
        """Callback de progression thread-safe."""
        if self._cancel_requested:
            if self._manager:
                self._manager.cancel()
            return

        if total > 0:
            progress = current / total
        else:
            progress = 0

        self._update_progress(f"{message} ({current}/{total})", progress)

    def _update_progress(self, message: str, progress: Optional[float]):
        """Met à jour la barre de progression de manière thread-safe."""
        def update():
            self.progress_label.configure(text=message)
            if progress is not None:
                self.progress_bar.set(max(0, min(1, progress)))
            self.status_callback(message, progress)

        self.after(0, update)

    def _set_running(self, running: bool):
        """Bascule l'état des boutons selon l'opération en cours."""
        self._operation_running = running

        def update():
            if running:
                self.search_button.configure(state="disabled")
                self.execute_button.configure(state="disabled")
                self.cancel_button.configure(state="normal")
            else:
                self.search_button.configure(state="normal")
                self.cancel_button.configure(state="disabled")
                # execute_button sera activé par _display_analysis si résultats

        self.after(0, update)

    def _cancel_operation(self):
        """Annule l'opération en cours."""
        self._cancel_requested = True
        if self._manager:
            self._manager.cancel()
        self._update_progress("Annulation en cours...", None)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Formate une taille en format lisible."""
        if size_bytes == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"
