#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module définissant l'interface graphique pour l'organisation des fichiers d'images.
"""

import os
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import logging

# Ajouter le répertoire parent au chemin Python si nécessaire
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import file_operations, metadata
from utils import file_utils, ui_utils, progress_utils
from utils.config_manager import get_config

logger = logging.getLogger(__name__)

# metadata already imported above

class FileOrganizationFrame(ttk.Frame):
    """Interface graphique pour l'organisation des fichiers d'images."""
    
    def __init__(self, parent):
        """
        Initialise le cadre d'organisation de fichiers.
        
        Args:
            parent: Widget parent (généralement un Notebook)
        """
        super().__init__(parent)
        
        # Variables pour les dossiers
        self.source_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        
        # Variables pour les options d'organisation
        self.organize_by_date_var = tk.BooleanVar(value=True)
        self.organize_by_camera_var = tk.BooleanVar(value=False)
        self.organize_by_location_var = tk.BooleanVar(value=False)
        
        # Structure de répertoires
        self.date_format_var = tk.StringVar(value="year/month/day")
        self.date_source_var = tk.StringVar(value="exif")  # Ajout de la variable manquante
        self.preserve_structure_var = tk.BooleanVar(value=True)
        
        # Variables pour les options de traitement
        self.copy_not_move_var = tk.BooleanVar(value=True)
        self.skip_existing_var = tk.BooleanVar(value=True)
        self.recursive_var = tk.BooleanVar(value=True)
        self.rename_files_var = tk.BooleanVar(value=False)
        self.auto_rename_var = tk.BooleanVar(value=True)
        
        # Variables pour l'organisation multicouche
        self.multilayer_var = tk.BooleanVar(value=False)
        
        # Variables pour l'emplacement GPS
        self.max_distance_var = tk.DoubleVar(value=1.0)
        self.use_geocoding_var = tk.BooleanVar(value=True)
        self.generate_maps_links_var = tk.BooleanVar(value=False)
        
        # Variables pour les types de fichiers
        self.include_images_var = tk.BooleanVar(value=True)
        self.include_raw_var = tk.BooleanVar(value=True)
        self.include_videos_var = tk.BooleanVar(value=False)
        
        # Gestion de l'annulation
        self.cancel_requested = False
        
        # Gestionnaire de progression
        self.progress_manager = None
        
        # Tâche en cours
        self.current_task = None
        
        # Créer l'interface utilisateur
        self.create_widgets()
    
    def update_criteria_selection(self, selected_criterion):
        """Met à jour la sélection des critères en mode non-multicouche."""
        if not self.multilayer_var.get():
            # En mode non-multicouche, désactiver les autres critères
            if selected_criterion == 'date':
                self.organize_by_camera_var.set(False)
                self.organize_by_location_var.set(False)
            elif selected_criterion == 'camera':
                self.organize_by_date_var.set(False)
                self.organize_by_location_var.set(False)
            elif selected_criterion == 'location':
                self.organize_by_date_var.set(False)
                self.organize_by_camera_var.set(False)
        # Mettre à jour la visibilité des options
        self.update_options_visibility()
    
    def create_widgets(self):
        """Crée les widgets de l'interface graphique."""
        # Utiliser un cadre principal avec remplissage automatique
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Diviser l'écran en colonnes
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Sections de l'interface
        self.create_folder_section(left_frame)
        self.create_organization_options(left_frame)
        self.create_file_options(right_frame)
        
        # Section des boutons d'action (en bas)
        self.create_action_buttons(main_frame)
    
    def create_folder_section(self, parent):
        """
        Crée la section pour sélectionner les dossiers source et destination.
        
        Args:
            parent: Widget parent
        """
        folder_section = ui_utils.create_settings_section(parent, "Sélection des dossiers")
        
        # Dossier source
        source_frame = ui_utils.create_folder_selection(
            folder_section,
            "Dossier source:",
            self.source_var
        )
        source_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Dossier destination
        dest_frame = ui_utils.create_folder_selection(
            folder_section,
            "Dossier destination:",
            self.destination_var
        )
        dest_frame.pack(fill=tk.X, padx=5, pady=5)
    
    def create_organization_options(self, parent):
        """
        Crée la section pour les options d'organisation.
        
        Args:
            parent: Widget parent
        """
        org_section = ui_utils.create_settings_section(parent, "Méthode d'organisation")
        
        # Option pour préserver la structure des dossiers
        preserve_check = ttk.Checkbutton(
            org_section,
            text="Préserver la structure des sous-dossiers",
            variable=self.preserve_structure_var
        )
        preserve_check.pack(anchor=tk.W, padx=10, pady=(5, 5))
        
        # Organisation multicouche (déplacée juste après "Préserver la structure")
        self.multilayer_var = tk.BooleanVar(value=False)
        multilayer_check = ttk.Checkbutton(
            org_section,
            text="Organisation multicouche (combinaison des critères)",
            variable=self.multilayer_var,
            command=self.update_options_visibility
        )
        multilayer_check.pack(anchor=tk.W, padx=10, pady=(0, 10))
        
        # Options d'organisation
        criteria_frame = ttk.Frame(org_section)
        criteria_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Critères d'organisation disponibles
        ttk.Label(
            criteria_frame,
            text="Critères disponibles:"
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # Option pour organiser par date
        date_check = ttk.Checkbutton(
            criteria_frame,
            text="Organiser par date",
            variable=self.organize_by_date_var,
            command=lambda: self.update_criteria_selection('date')
        )
        date_check.pack(anchor=tk.W, padx=20, pady=2)
        
        # Toujours afficher la source de la date sous la case à cocher
        self.date_source_frame = ttk.Frame(criteria_frame)  # Stocker la référence
        self.date_source_frame.pack(anchor=tk.W, padx=40, pady=2)
        
        ttk.Label(
            self.date_source_frame,
            text="Source de la date:"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            self.date_source_frame,
            text="EXIF",
            variable=self.date_source_var,
            value="exif"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            self.date_source_frame,
            text="Nom de fichier",
            variable=self.date_source_var,
            value="filename"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            self.date_source_frame,
            text="Date de modification",
            variable=self.date_source_var,
            value="modification"
        ).pack(side=tk.LEFT, padx=5)
        
        # Option pour organiser par appareil photo
        camera_check = ttk.Checkbutton(
            criteria_frame,
            text="Organiser par appareil photo",
            variable=self.organize_by_camera_var,
            command=lambda: self.update_criteria_selection('camera')
        )
        camera_check.pack(anchor=tk.W, padx=20, pady=2)
        
        # Option pour organiser par emplacement (intégrant la fonctionnalité GPS)
        location_check = ttk.Checkbutton(
            criteria_frame,
            text="Organiser par emplacement géographique",
            variable=self.organize_by_location_var,
            command=lambda: self.update_criteria_selection('location')
        )
        location_check.pack(anchor=tk.W, padx=20, pady=2)
        
        # Frame pour l'ordre des critères
        self.criteria_order_frame = ttk.LabelFrame(org_section, text="Ordre des critères")
        
        # Créer une liste de variables pour l'ordre
        self.criteria_order = []
        self.criteria_labels = []
        
        # Boutons haut/bas pour réorganiser
        for i, criteria in enumerate(["Date", "Appareil photo", "Emplacement"]):
            criteria_row = ttk.Frame(self.criteria_order_frame)
            criteria_row.pack(fill=tk.X, padx=5, pady=2)
            
            # Label avec numéro d'ordre et nom du critère
            order_label = ttk.Label(criteria_row, text=f"{i+1}. {criteria}", width=20)
            order_label.pack(side=tk.LEFT, padx=5)
            self.criteria_labels.append(order_label)
            
            # Boutons pour réorganiser
            if i > 0:  # Pas de bouton "monter" pour le premier
                up_button = ttk.Button(
                    criteria_row, 
                    text="↑", 
                    width=2,
                    command=lambda idx=i: self.move_criteria_up(idx)
                )
                up_button.pack(side=tk.LEFT, padx=2)
            
            if i < 2:  # Pas de bouton "descendre" pour le dernier
                down_button = ttk.Button(
                    criteria_row, 
                    text="↓", 
                    width=2,
                    command=lambda idx=i: self.move_criteria_down(idx)
                )
                down_button.pack(side=tk.LEFT, padx=2)
        
        # Paramètres spécifiques à l'appareil photo
        self.camera_options_frame = ttk.LabelFrame(org_section, text="Options d'appareil photo")
        ttk.Label(
            self.camera_options_frame,
            text="Format: Marque/Modèle"
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        # Paramètres spécifiques à l'emplacement (intégrant les options GPS)
        self.location_options_frame = ttk.LabelFrame(org_section, text="Options d'emplacement")
        
        ttk.Label(
            self.location_options_frame,
            text="Format: Pays/Ville/Lieu (si disponible)"
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        # Initialiser le frame des options GPS
        self.gps_options_frame = ttk.Frame(self.location_options_frame)
        
        # Distance maximale pour le regroupement
        distance_frame = ttk.Frame(self.gps_options_frame)
        distance_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(
            distance_frame,
            text="Distance maximale entre images (km):"
        ).pack(side=tk.LEFT, padx=5)
        
        self.max_distance_var = tk.DoubleVar(value=1.0)
        distance_spinbox = ttk.Spinbox(
            distance_frame,
            from_=0.1,
            to=50.0,
            increment=0.1,
            textvariable=self.max_distance_var,
            width=5
        )
        distance_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Géocodage
        self.use_geocoding_var = tk.BooleanVar(value=True)
        geocoding_check = ttk.Checkbutton(
            self.gps_options_frame,
            text="Utiliser le géocodage inverse pour les noms de lieux",
            variable=self.use_geocoding_var
        )
        geocoding_check.pack(anchor=tk.W, padx=5, pady=2)
        
        # Liens Google Maps
        self.generate_maps_links_var = tk.BooleanVar(value=False)
        maps_links_check = ttk.Checkbutton(
            self.gps_options_frame,
            text="Générer un fichier texte avec les liens Google Maps dans chaque dossier",
            variable=self.generate_maps_links_var
        )
        maps_links_check.pack(anchor=tk.W, padx=5, pady=2)
    
    def update_options_visibility(self):
        """Updates option visibility based on selections."""
        # Visibilité de l'organisation multicouche
        if self.multilayer_var.get():
            self.criteria_order_frame.pack(fill=tk.X, padx=10, pady=5)
            # Masquer les critères non sélectionnés dans l'ordre des critères
            for i, label in enumerate(self.criteria_labels):
                criteria_text = label['text']
                if criteria_text == "Date" and not self.organize_by_date_var.get():
                    label.pack_forget()
                elif criteria_text == "Appareil photo" and not self.organize_by_camera_var.get():
                    label.pack_forget()
                elif criteria_text == "Emplacement" and not self.organize_by_location_var.get():
                    label.pack_forget()
                else:
                    label.pack(side=tk.LEFT, padx=5)
        else:
            self.criteria_order_frame.pack_forget()
        
        # Visibilité des options d'appareil photo
        if self.organize_by_camera_var.get():
            self.camera_options_frame.pack(fill=tk.X, padx=10, pady=5)
        else:
            self.camera_options_frame.pack_forget()
        
        # Visibilité des options d'emplacement
        if self.organize_by_location_var.get():
            self.location_options_frame.pack(fill=tk.X, padx=10, pady=5)
            self.gps_options_frame.pack(fill=tk.X, padx=5, pady=5)
        else:
            self.location_options_frame.pack_forget()
            self.gps_options_frame.pack_forget()
            
        # Visibilité des options de source de date
        if self.organize_by_date_var.get():
            self.date_source_frame.pack(anchor=tk.W, padx=40, pady=2)
        else:
            self.date_source_frame.pack_forget()

    def move_criteria_up(self, index):
        """Déplace un critère vers le haut dans l'ordre."""
        if index > 0:
            # Extraire le numéro et le texte du critère
            current_text = self.criteria_labels[index]['text']
            prev_text = self.criteria_labels[index-1]['text']
            
            # Échanger les textes en conservant les numéros
            current_num = current_text.split('.')[0]
            prev_num = prev_text.split('.')[0]
            
            current_criteria = current_text.split('. ')[1]
            prev_criteria = prev_text.split('. ')[1]
            
            self.criteria_labels[index-1]['text'] = f"{prev_num}. {current_criteria}"
            self.criteria_labels[index]['text'] = f"{current_num}. {prev_criteria}"

    def move_criteria_down(self, index):
        """Déplace un critère vers le bas dans l'ordre."""
        if index < len(self.criteria_labels)-1:
            # Extraire le numéro et le texte du critère
            current_text = self.criteria_labels[index]['text']
            next_text = self.criteria_labels[index+1]['text']
            
            # Échanger les textes en conservant les numéros
            current_num = current_text.split('.')[0]
            next_num = next_text.split('.')[0]
            
            current_criteria = current_text.split('. ')[1]
            next_criteria = next_text.split('. ')[1]
            
            self.criteria_labels[index+1]['text'] = f"{next_num}. {current_criteria}"
            self.criteria_labels[index]['text'] = f"{current_num}. {next_criteria}"
    
    def create_file_options(self, parent):
        """
        Crée la section pour les options de traitement des fichiers.
        
        Args:
            parent: Widget parent
        """
        file_options_section = ui_utils.create_settings_section(parent, "Options de traitement")
        
        # Option pour copier ou déplacer
        copy_move_frame = ttk.Frame(file_options_section)
        copy_move_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(
            copy_move_frame,
            text="Action:"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            copy_move_frame,
            text="Copier",
            variable=self.copy_not_move_var,
            value=True
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            copy_move_frame,
            text="Déplacer",
            variable=self.copy_not_move_var,
            value=False
        ).pack(side=tk.LEFT, padx=10)
        
        # Traitement des conflits
        conflict_frame = ttk.LabelFrame(file_options_section, text="Traitement des conflits")
        conflict_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Option pour ignorer les fichiers existants
        skip_check = ttk.Checkbutton(
            conflict_frame,
            text="Ignorer les fichiers existants",
            variable=self.skip_existing_var
        )
        skip_check.pack(anchor=tk.W, padx=10, pady=2)
        
        # Option pour renommer automatiquement
        self.auto_rename_var = tk.BooleanVar(value=True)
        auto_rename_check = ttk.Checkbutton(
            conflict_frame,
            text="Renommer automatiquement en cas de conflit",
            variable=self.auto_rename_var
        )
        auto_rename_check.pack(anchor=tk.W, padx=10, pady=2)
        
        # Options avancées
        advanced_frame = ttk.LabelFrame(file_options_section, text="Options avancées")
        advanced_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Option pour parcourir les sous-dossiers
        recursive_check = ttk.Checkbutton(
            advanced_frame,
            text="Parcourir les sous-dossiers",
            variable=self.recursive_var
        )
        recursive_check.pack(anchor=tk.W, padx=10, pady=2)
        
        # Option pour renommer les fichiers
        rename_check = ttk.Checkbutton(
            advanced_frame,
            text="Renommer les fichiers avec la date de prise de vue",
            variable=self.rename_files_var
        )
        rename_check.pack(anchor=tk.W, padx=10, pady=2)
        
        # Types de fichiers
        files_frame = ttk.LabelFrame(file_options_section, text="Types de fichiers")
        files_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.include_images_var = tk.BooleanVar(value=True)
        include_images_check = ttk.Checkbutton(
            files_frame,
            text="Images (.jpg, .png, etc.)",
            variable=self.include_images_var
        )
        include_images_check.pack(anchor=tk.W, padx=10, pady=2)
        
        self.include_raw_var = tk.BooleanVar(value=True)
        include_raw_check = ttk.Checkbutton(
            files_frame,
            text="RAW (.raw, .arw, .cr2, .nef, .dng, etc.)",
            variable=self.include_raw_var
        )
        include_raw_check.pack(anchor=tk.W, padx=10, pady=2)
        
        self.include_videos_var = tk.BooleanVar(value=False)
        include_videos_check = ttk.Checkbutton(
            files_frame,
            text="Vidéos (.mp4, .mov, .avi, etc.)",
            variable=self.include_videos_var
        )
        include_videos_check.pack(anchor=tk.W, padx=10, pady=2)

    def create_action_buttons(self, parent):
        """
        Crée les boutons d'action.

        Args:
            parent: Widget parent
        """
        # Frame pour les boutons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Bouton Analyser (stocker la référence)
        self.analyze_button = ttk.Button(
            button_frame,
            text="Analyser les fichiers",
            command=self.analyze_files
        )
        self.analyze_button.pack(fill=tk.X, pady=2)

        # Bouton Organiser (stocker la référence)
        self.organize_button = ttk.Button(
            button_frame,
            text="Organiser les fichiers",
            command=self.organize_files
        )
        self.organize_button.pack(fill=tk.X, pady=2)

        # Bouton Annuler avec style distinct
        self.cancel_button = ttk.Button(
            button_frame,
            text="Annuler l'opération",
            command=self.cancel_operation,
            state=tk.DISABLED,
            style="Cancel.TButton"  # Style personnalisé pour le bouton d'annulation
        )
        self.cancel_button.pack(fill=tk.X, pady=2)

        # Créer un style personnalisé pour le bouton d'annulation
        style = ttk.Style()
        style.configure(
            "Cancel.TButton",
            foreground="red",
            font=("Helvetica", 10, "bold")
        )

        # Barre de progression
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=2)

        # Label de statut
        self.status_var = tk.StringVar(value="Prêt")
        status_label = ttk.Label(
            progress_frame,
            textvariable=self.status_var,
            font=("Helvetica", 9)
        )
        status_label.pack(fill=tk.X, pady=2)

        # Initialiser le gestionnaire de progression
        self.progress_manager = progress_utils.ProgressManager(
            self.progress_bar,
            self.status_var
        )

    def analyze_files(self):
        """
        Analyse les fichiers dans le dossier source et affiche les statistiques.
        """
        # Vérifier le dossier source
        source = self.source_var.get()

        if not source or not os.path.isdir(source):
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier source valide.")
            return

        # Récupérer les options sélectionnées
        recursive = self.recursive_var.get()
        include_images = self.include_images_var.get()
        include_raw = self.include_raw_var.get()
        include_videos = self.include_videos_var.get()

        # Vérifier qu'au moins un type de fichier est sélectionné
        if not (include_images or include_raw or include_videos):
            messagebox.showerror("Erreur", "Veuillez sélectionner au moins un type de fichier à traiter.")
            return

        # Réinitialiser la barre de progression
        self.progress_manager.reset()

        # Désactiver les boutons d'action et activer le bouton Annuler
        self.analyze_button.configure(state=tk.DISABLED)
        self.organize_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.cancel_requested = False
        
        # Définir la tâche d'analyse
        def analysis_task(progress_mgr):
            # Vérifier si l'opération a été annulée
            if self.cancel_requested:
                return None

            # Déterminer les extensions à traiter
            extensions = []
            if include_images:
                extensions.extend(['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp',
                                '.heic', '.heif', '.svg', '.psd', '.jfif', '.jp2', '.avif'])
            if include_raw:
                extensions.extend(['.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng', '.3fr',
                                '.raf', '.pef', '.srw', '.sr2', '.x3f', '.mef', '.iiq', '.rwl'])
            if include_videos:
                extensions.extend(['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.3gp',
                                '.m4v', '.mpg', '.mpeg', '.mts', '.ts', '.vob'])

            # Trouver tous les fichiers correspondants
            media_files = file_utils.get_files_by_extension(source, extensions, recursive)
            
            # Configurer le suivi de la progression
            progress_mgr.max_value = len(media_files)
            
            # Initialiser les conteneurs de statistiques
            file_types = {ext: 0 for ext in extensions}
            date_stats = {
                'with_exif_date': 0,
                'with_filename_date': 0,
                'no_date': 0,
                'by_year': {},
                'by_month': {}
            }
            camera_stats = {}
            gps_stats = {
                'with_gps': 0,
                'without_gps': 0,
                'locations': {}
            }
            
            # Traiter chaque fichier
            for i, file_path in enumerate(media_files):
                # Vérifier si l'opération a été annulée
                if self.cancel_requested:
                    return None
                
                # Mettre à jour la progression
                progress_mgr.update(
                    i,
                    f"Analyse de {os.path.basename(file_path)} ({i+1}/{len(media_files)})"
                )
                
                # Compter par extension
                ext = os.path.splitext(file_path)[1].lower()
                if ext in file_types:
                    file_types[ext] += 1
                
                try:
                    # Extraire les métadonnées EXIF
                    exif_data = metadata.get_exif_data(file_path)
                    
                    # Traiter les informations de date
                    date_taken = None

                    # Essayer d'abord la date EXIF
                    exif_date = metadata.extract_image_date(file_path)
                    if exif_date:
                        date_taken = exif_date
                        date_stats['with_exif_date'] += 1
                        
                        # Enregistrer les statistiques par année et mois
                        year = date_taken.year
                        month = f"{year}-{date_taken.month:02d}"
                        
                        date_stats['by_year'][year] = date_stats['by_year'].get(year, 0) + 1
                        date_stats['by_month'][month] = date_stats['by_month'].get(month, 0) + 1
                    else:
                        # Essayer la date dans le nom de fichier
                        filename = os.path.basename(file_path)
                        date_from_filename = metadata.extract_image_date(filename, fallback_to_file_date=False)
                        
                        if date_from_filename:
                            date_taken = date_from_filename
                            date_stats['with_filename_date'] += 1
                            
                            # Enregistrer les statistiques par année et mois
                            year = date_taken.year
                            month = f"{year}-{date_taken.month:02d}"
                            
                            date_stats['by_year'][year] = date_stats['by_year'].get(year, 0) + 1
                            date_stats['by_month'][month] = date_stats['by_month'].get(month, 0) + 1
                        else:
                            date_stats['no_date'] += 1
                    
                    # Traiter les informations sur l'appareil photo
                    if exif_data:
                        make, model = metadata.get_camera_info(exif_data)
                        camera_key = f"{make} {model}".strip()
                        if camera_key != "Unknown Unknown":
                            camera_stats[camera_key] = camera_stats.get(camera_key, 0) + 1
                    
                    # Traiter les informations GPS
                    coords = metadata.get_image_gps_coordinates(file_path)
                    if coords[0] is not None and coords[1] is not None:
                        gps_stats['with_gps'] += 1
                        
                        # Regrouper par localisation approximative (arrondie à 2 décimales)
                        rounded_lat = round(coords[0], 2)
                        rounded_lon = round(coords[1], 2)
                        location_key = f"{rounded_lat},{rounded_lon}"
                        
                        if location_key not in gps_stats['locations']:
                            gps_stats['locations'][location_key] = 1
                        else:
                            gps_stats['locations'][location_key] += 1
                    else:
                        gps_stats['without_gps'] += 1
                        
                except Exception as e:
                    print(f"Erreur lors de l'analyse de {file_path}: {e}")
                    date_stats['no_date'] += 1
                    gps_stats['without_gps'] += 1
            
            # Retourner les résultats de l'analyse
            results = {
                'total_files': len(media_files),
                'file_types': file_types,
                'date_stats': date_stats,
                'camera_stats': camera_stats,
                'gps_stats': gps_stats
            }
            return results

        # Définir la fonction pour afficher les résultats
        def show_analysis_results(results):
            # Réactiver les boutons d'action et désactiver le bouton Annuler
            self.analyze_button.configure(state=tk.NORMAL)
            self.organize_button.configure(state=tk.NORMAL)
            self.cancel_button.configure(state=tk.DISABLED)

            if results is None:
                messagebox.showinfo("Annulation", "L'analyse a été annulée.")
                return

            # Vérifier si des fichiers ont été trouvés
            if results['total_files'] == 0:
                messagebox.showinfo("Aucun fichier", "Aucun fichier correspondant aux critères n'a été trouvé dans le dossier sélectionné.")
                return

            # Créer une fenêtre modale
            result_window = tk.Toplevel(self)
            result_window.title("Résultats de l'analyse")
            result_window.geometry("800x700")
            result_window.transient(self.winfo_toplevel())
            result_window.grab_set()
            
            # Centrer la fenêtre
            result_window.update_idletasks()
            width = result_window.winfo_width()
            height = result_window.winfo_height()
            x = (result_window.winfo_screenwidth() // 2) - (width // 2)
            y = (result_window.winfo_screenheight() // 2) - (height // 2)
            result_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Créer un cadre défilant
            main_frame = ui_utils.ScrollableFrame(result_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # ===== SECTION TITRE =====
            title_label = ttk.Label(
                main_frame.scrollable_frame,
                text="📊 Résultats de l'analyse",
                font=("Helvetica", 16, "bold")
            )
            title_label.pack(anchor=tk.W, pady=(5, 15))

            # Séparateur
            ttk.Separator(main_frame.scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=5)

            # ===== SECTION STATISTIQUES GÉNÉRALES =====
            ttk.Label(
                main_frame.scrollable_frame,
                text=f"📁 Nombre total de fichiers analysés : {results['total_files']}",
                font=("Helvetica", 12, "bold")
            ).pack(anchor=tk.W, pady=(10, 5))
            
            # Séparateur
            ttk.Separator(main_frame.scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)

            # ===== SECTION TYPES DE FICHIERS =====
            ttk.Label(
                main_frame.scrollable_frame,
                text="📷 Types de fichiers",
                font=("Helvetica", 13, "bold")
            ).pack(anchor=tk.W, pady=(10, 5))
            
            # Trier les types de fichiers par nombre
            sorted_types = [(ext, count) for ext, count in results['file_types'].items() if count > 0]
            sorted_types.sort(key=lambda x: x[1], reverse=True)
            
            # Regrouper les types de fichiers par catégorie
            image_files = sum(count for ext, count in sorted_types if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif', '.svg', '.psd', '.jfif', '.jp2', '.avif'])
            raw_files = sum(count for ext, count in sorted_types if ext in ['.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng', '.3fr', '.raf', '.pef', '.srw', '.sr2', '.x3f', '.mef', '.iiq', '.rwl'])
            video_files = sum(count for ext, count in sorted_types if ext in ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.3gp', '.m4v', '.mpg', '.mpeg', '.mts', '.ts', '.vob'])
            
            # Afficher les résumés par catégorie
            if image_files > 0:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text=f"Fichiers image : {image_files} ({image_files/results['total_files']*100:.1f}%)"
                ).pack(anchor=tk.W, padx=20)
            
            if raw_files > 0:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text=f"Fichiers RAW : {raw_files} ({raw_files/results['total_files']*100:.1f}%)"
                ).pack(anchor=tk.W, padx=20)
                
            if video_files > 0:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text=f"Fichiers vidéo : {video_files} ({video_files/results['total_files']*100:.1f}%)"
                ).pack(anchor=tk.W, padx=20)
            
            # Top 10 des extensions de fichiers
            ttk.Label(
                main_frame.scrollable_frame,
                text="Extensions de fichiers les plus courantes :"
            ).pack(anchor=tk.W, padx=20, pady=(10, 0))
            
            for ext, count in sorted_types[:10]:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text=f"{ext} : {count} fichiers ({count/results['total_files']*100:.1f}%)"
                ).pack(anchor=tk.W, padx=40)
            
            # Séparateur
            ttk.Separator(main_frame.scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)

            # ===== SECTION INFORMATIONS DE DATE =====
            ttk.Label(
                main_frame.scrollable_frame,
                text="📅 Informations de date",
                font=("Helvetica", 13, "bold")
            ).pack(anchor=tk.W, pady=(10, 5))
            
            date_stats = results['date_stats']
            
            # Statistiques de disponibilité des dates
            ttk.Label(
                main_frame.scrollable_frame,
                text=f"Fichiers avec date EXIF : {date_stats['with_exif_date']} ({date_stats['with_exif_date']/results['total_files']*100:.1f}%)"
            ).pack(anchor=tk.W, padx=20)
            
            ttk.Label(
                main_frame.scrollable_frame,
                text=f"Fichiers avec date dans le nom : {date_stats['with_filename_date']} ({date_stats['with_filename_date']/results['total_files']*100:.1f}%)"
            ).pack(anchor=tk.W, padx=20)
            
            ttk.Label(
                main_frame.scrollable_frame,
                text=f"Fichiers sans date : {date_stats['no_date']} ({date_stats['no_date']/results['total_files']*100:.1f}%)"
            ).pack(anchor=tk.W, padx=20)
            
            # Distribution par année (si disponible)
            if date_stats['by_year']:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="Distribution par année :"
                ).pack(anchor=tk.W, padx=20, pady=(10, 0))
                
                for year, count in sorted(date_stats['by_year'].items()):
                    ttk.Label(
                        main_frame.scrollable_frame,
                        text=f"{year} : {count} fichiers ({count/results['total_files']*100:.1f}%)"
                    ).pack(anchor=tk.W, padx=40)
            
            # ===== SECTION INFORMATIONS APPAREIL PHOTO =====
            if results['camera_stats']:
                # Séparateur
                ttk.Separator(main_frame.scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)

                ttk.Label(
                    main_frame.scrollable_frame,
                    text="📸 Informations appareil photo",
                    font=("Helvetica", 13, "bold")
                ).pack(anchor=tk.W, pady=(10, 5))
                
                for camera, count in sorted(results['camera_stats'].items(), key=lambda x: x[1], reverse=True):
                    ttk.Label(
                        main_frame.scrollable_frame,
                        text=f"{camera} : {count} fichiers ({count/results['total_files']*100:.1f}%)"
                    ).pack(anchor=tk.W, padx=20)
            
            # Séparateur
            ttk.Separator(main_frame.scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)

            # ===== SECTION INFORMATIONS GPS =====
            ttk.Label(
                main_frame.scrollable_frame,
                text="🌍 Informations GPS",
                font=("Helvetica", 13, "bold")
            ).pack(anchor=tk.W, pady=(10, 5))
            
            gps_stats = results['gps_stats']
            ttk.Label(
                main_frame.scrollable_frame,
                text=f"Fichiers avec coordonnées GPS : {gps_stats['with_gps']} ({gps_stats['with_gps']/results['total_files']*100:.1f}%)"
            ).pack(anchor=tk.W, padx=20)
            
            ttk.Label(
                main_frame.scrollable_frame,
                text=f"Fichiers sans coordonnées GPS : {gps_stats['without_gps']} ({gps_stats['without_gps']/results['total_files']*100:.1f}%)"
            ).pack(anchor=tk.W, padx=20)
            
            # Regroupements de localisation
            locations_count = len(gps_stats['locations'])
            if locations_count > 0:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text=f"Regroupements de localisation distincts identifiés : {locations_count}"
                ).pack(anchor=tk.W, padx=20)
                
                # Localisations principales
                if locations_count > 1:
                    ttk.Label(
                        main_frame.scrollable_frame,
                        text="Localisations les plus fréquentes :"
                    ).pack(anchor=tk.W, padx=20, pady=(10, 0))
                    
                    # Afficher les 5 localisations principales
                    for location, count in sorted(gps_stats['locations'].items(), key=lambda x: x[1], reverse=True)[:5]:
                        lat, lon = location.split(',')
                        ttk.Label(
                            main_frame.scrollable_frame,
                            text=f"Localisation ({lat}, {lon}) : {count} fichiers ({count/results['total_files']*100:.1f}%)"
                        ).pack(anchor=tk.W, padx=40)
            
            # Séparateur
            ttk.Separator(main_frame.scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)

            # ===== SECTION RECOMMANDATIONS =====
            ttk.Label(
                main_frame.scrollable_frame,
                text="💡 Recommandations d'organisation",
                font=("Helvetica", 13, "bold")
            ).pack(anchor=tk.W, pady=(10, 10))
            
            # Recommandation d'organisation par date
            has_dates = date_stats['with_exif_date'] + date_stats['with_filename_date']
            date_percentage = has_dates / results['total_files'] * 100 if results['total_files'] > 0 else 0
            
            if date_percentage > 70:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="✓ Organisation par date fortement recommandée"
                ).pack(anchor=tk.W, padx=20)
            elif date_percentage > 40:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="✓ Organisation par date recommandée"
                ).pack(anchor=tk.W, padx=20)
            else:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="✗ Organisation par date non recommandée (informations de date insuffisantes)"
                ).pack(anchor=tk.W, padx=20)
            
            # Recommandation d'organisation par appareil photo
            camera_count = sum(results['camera_stats'].values())
            camera_percentage = camera_count / results['total_files'] * 100 if results['total_files'] > 0 else 0
            
            if camera_percentage > 50 and len(results['camera_stats']) > 1:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="✓ Organisation par appareil photo recommandée"
                ).pack(anchor=tk.W, padx=20)
            else:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="✗ Organisation par appareil photo non recommandée (informations d'appareil insuffisantes)"
                ).pack(anchor=tk.W, padx=20)
            
            # Recommandation d'organisation par GPS
            gps_percentage = gps_stats['with_gps'] / results['total_files'] * 100 if results['total_files'] > 0 else 0
            
            if gps_percentage > 60:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="✓ Organisation par localisation fortement recommandée"
                ).pack(anchor=tk.W, padx=20)
            elif gps_percentage > 30:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="✓ Organisation par localisation recommandée"
                ).pack(anchor=tk.W, padx=20)
            else:
                ttk.Label(
                    main_frame.scrollable_frame,
                    text="✗ Organisation par localisation non recommandée (informations GPS insuffisantes)"
                ).pack(anchor=tk.W, padx=20)
            
            # ===== BOUTON FERMER =====
            ttk.Button(
                result_window,
                text="Fermer",
                command=result_window.destroy
            ).pack(pady=10)
        
        # Exécuter la tâche d'analyse dans un thread séparé
        self.current_task = progress_utils.ThreadedTask(
            analysis_task,
            self.progress_manager,
            show_analysis_results
        )
        self.current_task.start()

    def organize_files(self):
        """
        Organise les fichiers selon les critères sélectionnés.
        """
        print("DEBUG: Début de la fonction organize_files")

        # Vérifier le dossier source
        if not self.source_var.get():
            print("DEBUG: Erreur - Dossier source non sélectionné")
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier source valide.")
            return

        source_dir = self.source_var.get()
        if not os.path.isdir(source_dir):
            messagebox.showerror("Erreur", "Le dossier source sélectionné n'existe pas.")
            return

        # Vérifier le dossier de destination
        target_dir = self.destination_var.get()
        if not target_dir:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier de destination.")
            return

        if not os.path.isdir(target_dir):
            # Demander si on veut créer le dossier
            response = messagebox.askyesno(
                "Dossier inexistant",
                f"Le dossier de destination n'existe pas:\n{target_dir}\n\nVoulez-vous le créer?"
            )
            if not response:
                return

        print(f"DEBUG: Dossier source: {source_dir}")
        print(f"DEBUG: Dossier destination: {target_dir}")

        # Désactiver les boutons d'action et activer le bouton Annuler
        self.analyze_button.configure(state=tk.DISABLED)
        self.organize_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.cancel_requested = False
        
        try:
            print("DEBUG: Récupération des fichiers par extension")
            # Obtenir tous les fichiers avec leurs extensions
            files = self.get_files_by_extension()
            
            if not files:
                print("DEBUG: Aucun fichier trouvé")
                messagebox.showinfo("Information", "Aucun fichier trouvé dans le dossier source")
                return
            
            print(f"DEBUG: Nombre de fichiers trouvés: {len(files)}")
            
            # Créer le dossier de destination s'il n'existe pas
            os.makedirs(target_dir, exist_ok=True)
            print("DEBUG: Dossier de destination créé/vérifié")
            
            # Préparer les options d'organisation
            organization_options = {
                'organize_by_date': self.organize_by_date_var.get(),
                'organize_by_camera': self.organize_by_camera_var.get(),
                'organize_by_location': self.organize_by_location_var.get(),
                'multilayer': self.multilayer_var.get(),
                'copy_not_move': self.copy_not_move_var.get(),
                'date_format': self.date_format_var.get(),
                'max_distance_km': self.max_distance_var.get(),
                'no_date_handling': 'separate_folder',
                'no_camera_handling': 'separate_folder',
                'no_location_handling': 'separate_folder'
            }
            print("DEBUG: Options d'organisation:", organization_options)
            
            # Si l'organisation multicouche est activée, déterminer l'ordre des critères
            if self.multilayer_var.get():
                print("DEBUG: Organisation multicouche activée")
                criteria_order = []
                for label in self.criteria_labels:
                    if label.winfo_viewable():  # Vérifier si le label est visible
                        criteria_text = label['text']
                        criterion = criteria_text.split('. ')[1].lower()
                        if criterion == "date" and self.organize_by_date_var.get():
                            criteria_order.append('date')
                        elif criterion == "appareil photo" and self.organize_by_camera_var.get():
                            criteria_order.append('camera')
                        elif criterion == "emplacement" and self.organize_by_location_var.get():
                            criteria_order.append('location')
                organization_options['criteria_order'] = criteria_order
                print(f"DEBUG: Ordre des critères: {criteria_order}")
            
            # Réinitialiser la barre de progression
            self.progress_manager.reset()

            # Définir la tâche d'organisation
            def organization_task(progress_mgr):
                print("DEBUG: Début de la tâche d'organisation")
                if self.cancel_requested:
                    print("DEBUG: Annulation demandée")
                    return None
                
                # Convertir la liste de fichiers en liste de chemins
                file_paths = [file_info['file_path'] for file_info in files]
                print(f"DEBUG: Nombre de fichiers à traiter: {len(file_paths)}")
                
                # Créer l'adaptateur de progression
                def progress_adapter(percent):  # Modifié pour n'accepter qu'un seul paramètre
                    if progress_mgr:
                        # Calculer l'index du fichier actuel basé sur le pourcentage
                        current_file_index = int((percent / 100) * len(file_paths))
                        # Créer un message de statut
                        status_message = f"Traitement des fichiers ({int(percent)}%)"
                        # Mettre à jour le gestionnaire de progression
                        progress_mgr.update(current_file_index, status_message)
                
                # Exécuter l'organisation
                print("DEBUG: Appel de run_smart_organization")
                result = file_operations.run_smart_organization(
                    file_paths,
                    target_dir,
                    organization_options,
                    progress_callback=progress_adapter
                )
                print("DEBUG: Fin de run_smart_organization")
                return result
            
            # Définir la fonction pour afficher les résultats
            def show_organization_results(results):
                print("DEBUG: Affichage des résultats")
                # Réactiver les boutons d'action et désactiver le bouton Annuler
                self.analyze_button.configure(state=tk.NORMAL)
                self.organize_button.configure(state=tk.NORMAL)
                self.cancel_button.configure(state=tk.DISABLED)

                if results is None:
                    print("DEBUG: Résultats annulés")
                    messagebox.showinfo("Annulation", "L'organisation a été annulée.")
                    return
                
                print("DEBUG: Préparation du message de résultats")
                # Create a message with the results
                message = f"Organisation terminée!\n\n"
                
                if isinstance(results, dict):
                    print("DEBUG: Traitement des résultats sous forme de dictionnaire")
                    # Handle dictionary result
                    message += f"Total des fichiers : {results.get('total', 0)}\n"
                    message += f"Fichiers traités : {results.get('processed', 0)}\n"
                    message += f"Fichiers ignorés : {results.get('skipped', 0)}\n"
                    message += f"Erreurs : {results.get('errors', 0)}\n"
                    
                    if results.get('results'):
                        message += "\nDétails par critère :\n"
                        for criterion, stats in results['results'].items():
                            message += f"\n{criterion.capitalize()} :\n"
                            
                            # Check if stats is a dictionary and process accordingly
                            if isinstance(stats, dict):
                                message += f"  - Traités : {stats.get('processed', 0)}\n"
                                message += f"  - Ignorés : {stats.get('skipped', 0)}\n"
                                message += f"  - Erreurs : {stats.get('errors', 0)}\n"
                            else:
                                # Handle list or other types
                                message += f"  - Informations : {stats}\n"
                else:
                    print("DEBUG: Traitement des résultats sous forme de liste")
                    # Handle list or other result types
                    message += f"Nombre de fichiers traités : {len(results) if isinstance(results, list) else 1}\n"
                
                print("DEBUG: Affichage de la boîte de dialogue des résultats")
                messagebox.showinfo("Rapport d'organisation", message)
            
            print("DEBUG: Démarrage de la tâche d'organisation")
            # Exécuter la tâche d'organisation dans un thread séparé
            self.current_task = progress_utils.ThreadedTask(
                organization_task,
                self.progress_manager,
                show_organization_results
            )
            self.current_task.start()
            
        except Exception as e:
            print(f"DEBUG: Erreur lors de l'organisation: {str(e)}")
            # Réactiver les boutons en cas d'erreur
            self.analyze_button.configure(state=tk.NORMAL)
            self.organize_button.configure(state=tk.NORMAL)
            self.cancel_button.configure(state=tk.DISABLED)
            messagebox.showerror("Erreur", f"Une erreur est survenue: {str(e)}")
            # Réinitialiser la progression
            if self.progress_manager:
                self.progress_manager.reset()
            print("DEBUG: Fin de la fonction organize_files")

    def has_running_tasks(self):
        """Vérifie si des tâches sont en cours d'exécution."""
        return self.current_task is not None and self.current_task.is_running()

    def bind_source_var(self, var):
        """
        Lie une variable externe à la variable de dossier source.
        
        Args:
            var (tk.StringVar): Variable à lier
        """
        # Liaison bidirectionnelle
        self.source_var.trace_add(
            "write",
            lambda name, index, mode, sv=self.source_var, v=var: v.set(sv.get())
        )
        var.trace_add(
            "write",
            lambda name, index, mode, sv=var, v=self.source_var: v.set(sv.get())
        )

    def bind_dest_var(self, var):
        """
        Lie une variable externe à la variable de dossier destination.
        
        Args:
            var (tk.StringVar): Variable à lier
        """
        # Liaison bidirectionnelle
        self.destination_var.trace_add(
            "write",
            lambda name, index, mode, sv=self.destination_var, v=var: v.set(sv.get())
        )
        var.trace_add(
            "write",
            lambda name, index, mode, sv=var, v=self.destination_var: v.set(sv.get())
        )

    def set_progress_manager(self, progress_manager):
        """
        Définit le gestionnaire de progression à utiliser.
        
        Args:
            progress_manager (progress_utils.ProgressManager): Gestionnaire de progression
        """
        self.progress_manager = progress_manager

    def cancel_operation(self):
        """Annule l'opération en cours."""
        if self.current_task and self.current_task.is_running():
            self.cancel_requested = True
            self.current_task.cancel()
            # Réactiver les boutons d'action et désactiver le bouton Annuler
            self.analyze_button.configure(state=tk.NORMAL)
            self.organize_button.configure(state=tk.NORMAL)
            self.cancel_button.configure(state=tk.DISABLED)
            # Réinitialiser la barre de progression
            if self.progress_manager:
                self.progress_manager.reset()
            messagebox.showinfo("Annulation", "L'opération en cours a été annulée.")

    def get_allowed_extensions(self):
        """
        Retourne la liste des extensions de fichiers autorisées en fonction des options sélectionnées.
        
        Returns:
            list: Liste des extensions autorisées
        """
        extensions = []
        
        if self.include_images_var.get():
            extensions.extend([
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', 
                '.webp', '.heic', '.heif', '.svg', '.psd', '.jfif', '.jp2', '.avif'
            ])
            
        if self.include_raw_var.get():
            extensions.extend([
                '.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng', 
                '.3fr', '.raf', '.pef', '.srw', '.sr2', '.x3f', '.mef', '.iiq', '.rwl'
            ])
            
        if self.include_videos_var.get():
            extensions.extend([
                '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', 
                '.3gp', '.m4v', '.mpg', '.mpeg', '.mts', '.ts', '.vob'
            ])
            
        return extensions

    def get_files_by_extension(self):
        """
        Récupère tous les fichiers avec leurs extensions autorisées.
        
        Returns:
            list: Liste des fichiers avec leurs informations
        """
        print("DEBUG: Début de get_files_by_extension")
        source_dir = self.source_var.get()
        print(f"DEBUG: Dossier source: {source_dir}")
        
        extensions = self.get_allowed_extensions()
        print(f"DEBUG: Extensions autorisées: {extensions}")
        
        files = []
        print("DEBUG: Début de la recherche des fichiers")
        for root, dirs, filenames in os.walk(source_dir):
            print(f"DEBUG: Exploration du dossier: {root}")
            print(f"DEBUG: Sous-dossiers trouvés: {dirs}")
            print(f"DEBUG: Fichiers trouvés: {len(filenames)}")
            
            for filename in filenames:
                if any(filename.lower().endswith(ext.lower()) for ext in extensions):
                    file_path = os.path.join(root, filename)
                    print(f"DEBUG: Fichier correspondant trouvé: {file_path}")
                    files.append({
                        'file_path': file_path,
                        'filename': filename,
                        'mtime': os.path.getmtime(file_path)
                    })
        
        # Trier les fichiers par date de modification
        files.sort(key=lambda x: x['mtime'])
        print(f"DEBUG: Nombre total de fichiers trouvés: {len(files)}")
        print("DEBUG: Fin de get_files_by_extension")
        return files

    def get_location_name(self, latitude, longitude):
        """
        Obtient le nom de la localisation à partir des coordonnées GPS.

        Args:
            latitude (float): Latitude
            longitude (float): Longitude

        Returns:
            str: Nom de la localisation formaté
        """
        if not self.use_geocoding_var.get():
            return f"Lat{latitude:.4f}_Lon{longitude:.4f}"

        try:
            # Get API key from config
            config = get_config()
            api_key = config.get_api_key('positionstack')

            if not api_key:
                logger.warning("Positionstack API key not configured. Using coordinates only.")
                return f"Lat{latitude:.4f}_Lon{longitude:.4f}"

            # Import requests only when needed
            import requests

            url = f"http://api.positionstack.com/v1/reverse?access_key={api_key}&limit=1&query={latitude},{longitude}"

            response = requests.get(url, timeout=5)
            data = response.json()

            if "data" in data and data["data"]:
                location_info = data["data"][0]
                address_component = location_info.get('label', '')

                # Nettoyer et formater le nom de la localisation
                location_name = address_component.replace(', ', ' - ')
                location_name = re.sub(r'[<>:"/\\|?*]', '_', location_name)
                location_name = location_name[:80]  # Limiter la longueur

                return location_name

        except Exception as e:
            logger.error(f"Erreur lors du géocodage inverse: {e}")

        # En cas d'erreur, retourner les coordonnées
        return f"Lat{latitude:.4f}_Lon{longitude:.4f}"

