#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module contenant la classe principale de l'interface graphique de PhotoManager.
Ce fichier définit l'application qui intègre tous les onglets de fonctionnalité.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser

# Importer les modules du projet
# Ajouter le répertoire parent au chemin Python si nécessaire
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import file_operations, format_conversion, metadata
from utils import file_utils, ui_utils, progress_utils
from gui.frames import file_organization_frame


class PhotoManagerApp:
    """Classe principale pour l'application de gestion de photos."""
    
    def __init__(self, root):
        """
        Initialise l'application.
        
        Args:
            root (tk.Tk): Fenêtre principale Tkinter
        """
        self.root = root
        self.root.title("PhotoManager")
        self.root.geometry("950x700")
        self.root.minsize(800, 600)
        
        # Configurer l'icône de l'application si disponible
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass  # Ignorer si l'icône n'est pas disponible
        
        # Variables pour les répertoires souvent utilisés
        self.last_source_dir = tk.StringVar(value=os.path.expanduser("~"))
        self.last_dest_dir = tk.StringVar(value=os.path.expanduser("~"))
        
        # Créer les éléments d'interface utilisateur
        self.create_menu()
        self.create_widgets()
        
        # Configurer le gestionnaire d'événements pour le redimensionnement de la fenêtre
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Configurer la gestion de la fermeture de l'application
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_menu(self):
        """Crée la barre de menu de l'application."""
        menu_bar = tk.Menu(self.root)
        
        # Menu Fichier
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Ouvrir le dossier source...", command=self.browse_source_folder)
        file_menu.add_command(label="Ouvrir le dossier destination...", command=self.browse_dest_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.on_closing)
        menu_bar.add_cascade(label="Fichier", menu=file_menu)
        
        # Menu Outils
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        tools_menu.add_command(label="Préférences...", command=self.show_preferences)
        tools_menu.add_command(label="Vérifier les formats supportés", command=self.check_supported_formats)
        menu_bar.add_cascade(label="Outils", menu=tools_menu)
        
        # Menu Aide
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Documentation", command=lambda: webbrowser.open("https://github.com/votrenom/photomanager/wiki"))
        help_menu.add_command(label="À propos", command=self.show_about_dialog)
        menu_bar.add_cascade(label="Aide", menu=help_menu)
        
        self.root.config(menu=menu_bar)
    
    def create_widgets(self):
        """Crée les widgets principaux de l'interface utilisateur."""
        # Appliquer un style personnalisé
        self.configure_styles()
        
        # Cadre principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglets principaux
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Créer et ajouter les onglets de fonctionnalité
        self.create_tabs()
        
        # Barre de progression et statut
        self.create_status_bar()
    
    def configure_styles(self):
        """Configure les styles pour l'interface utilisateur."""
        style = ttk.Style()
        
        # Utiliser un thème moderne s'il est disponible
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        
        # Configurer les styles personnalisés
        style.configure("TFrame", background="#f5f5f5")
        style.configure("TNotebook", background="#f5f5f5")
        style.configure("TNotebook.Tab", padding=[10, 2], font=('Helvetica', 10))
        style.configure("TButton", font=('Helvetica', 10))
        style.configure("TLabel", font=('Helvetica', 10), background="#f5f5f5")
        style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))
        style.configure("Subheader.TLabel", font=('Helvetica', 11, 'italic'))
    
    def create_tabs(self):
        """Crée et ajoute les onglets de fonctionnalité au notebook."""
        # Onglet Organisation des fichiers
        self.file_org_frame = file_organization_frame.FileOrganizationFrame(self.notebook)
        self.notebook.add(self.file_org_frame, text="Organisation")
        
        
        # Partager les variables de dossier entre les onglets
        self.file_org_frame.bind_source_var(self.last_source_dir)
        self.file_org_frame.bind_dest_var(self.last_dest_dir)
        
    
    def create_status_bar(self):
        """Crée la barre de statut et de progression en bas de l'application."""
        # Cadre pour la barre de statut
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Barre de progression
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            status_frame, 
            variable=self.progress_var, 
            mode='determinate', 
            length=200
        )
        self.progress_bar.pack(side=tk.LEFT, padx=(5, 10), fill=tk.X, expand=True)
        
        # Message de statut
        self.status_var = tk.StringVar(value="Prêt")
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var, 
            anchor=tk.W,
            width=40
        )
        status_label.pack(side=tk.RIGHT, padx=5)
        
        # Créer un gestionnaire de progression partagé pour les onglets
        self.progress_manager = progress_utils.ProgressManager(
            self.progress_bar,
            self.status_var
        )
        
        # Partager le gestionnaire de progression avec les onglets
        self.file_org_frame.set_progress_manager(self.progress_manager)

    def browse_source_folder(self):
        """Ouvre une boîte de dialogue pour sélectionner le dossier source."""
        folder = filedialog.askdirectory(
            title="Sélectionner le dossier source",
            initialdir=self.last_source_dir.get()
        )
        if folder:
            self.last_source_dir.set(folder)
    
    def browse_dest_folder(self):
        """Ouvre une boîte de dialogue pour sélectionner le dossier destination."""
        folder = filedialog.askdirectory(
            title="Sélectionner le dossier destination",
            initialdir=self.last_dest_dir.get()
        )
        if folder:
            self.last_dest_dir.set(folder)
    
    def show_preferences(self):
        """Affiche la boîte de dialogue des préférences."""
        # Créer une fenêtre modale des préférences
        prefs_window = tk.Toplevel(self.root)
        prefs_window.title("Préférences")
        prefs_window.geometry("500x400")
        prefs_window.transient(self.root)
        prefs_window.grab_set()
        
        # Centrer la fenêtre des préférences par rapport à la fenêtre principale
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        prefs_window.geometry(f"+{x}+{y}")
        
        # Créer un notebook pour les préférences
        prefs_notebook = ttk.Notebook(prefs_window)
        prefs_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Onglet général
        general_frame = ttk.Frame(prefs_notebook)
        prefs_notebook.add(general_frame, text="Général")
        
        # Onglet des extensions
        extensions_frame = ttk.Frame(prefs_notebook)
        prefs_notebook.add(extensions_frame, text="Extensions")
        
        # Ajouter des options dans l'onglet général
        ttk.Label(
            general_frame, 
            text="Paramètres généraux", 
            style="Header.TLabel"
        ).pack(anchor=tk.W, padx=10, pady=10)
        
        # Option pour le comportement par défaut (copier ou déplacer)
        default_action_frame = ttk.Frame(general_frame)
        default_action_frame.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(
            default_action_frame, 
            text="Action par défaut:"
        ).pack(side=tk.LEFT, padx=5)
        
        default_action_var = tk.StringVar(value="copy")
        ttk.Radiobutton(
            default_action_frame, 
            text="Copier", 
            value="copy", 
            variable=default_action_var
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            default_action_frame, 
            text="Déplacer", 
            value="move", 
            variable=default_action_var
        ).pack(side=tk.LEFT, padx=10)
        
        # Boutons de confirmation
        button_frame = ttk.Frame(prefs_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            button_frame, 
            text="Annuler", 
            command=prefs_window.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Enregistrer", 
            command=lambda: self.save_preferences(prefs_window, default_action_var)
        ).pack(side=tk.RIGHT, padx=5)
    
    def save_preferences(self, window, default_action_var):
        """
        Enregistre les préférences et ferme la fenêtre.

        Args:
            window (tk.Toplevel): Fenêtre des préférences
            default_action_var (tk.StringVar): Variable pour l'action par défaut
        """
        from utils.config_manager import get_config

        # Save preferences using config manager
        config = get_config()
        config.set('preferences.default_action', default_action_var.get())
        config.save()

        # Fermer la fenêtre
        window.destroy()
    
    def check_supported_formats(self):
        """Vérifie et affiche les formats supportés par le système."""
        # Créer un convertisseur de formats
        converter = format_conversion.FormatConverter()
        formats_info = converter.get_supported_formats_info()
        
        # Créer une fenêtre modale pour afficher les résultats
        formats_window = tk.Toplevel(self.root)
        formats_window.title("Formats supportés")
        formats_window.geometry("500x400")
        formats_window.transient(self.root)
        formats_window.grab_set()
        
        # Centrer la fenêtre
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        formats_window.geometry(f"+{x}+{y}")
        
        # Titre
        ttk.Label(
            formats_window, 
            text="Formats supportés sur ce système", 
            style="Header.TLabel"
        ).pack(anchor=tk.W, padx=10, pady=10)
        
        # Créer un cadre pour les informations
        info_frame = ttk.Frame(formats_window)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Afficher les informations sur les formats
        row = 0
        for format_name, info in formats_info.items():
            ttk.Label(
                info_frame, 
                text=f"Format {format_name.upper()}:", 
                style="Subheader.TLabel"
            ).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            row += 1
            
            status = "Supporté" if info.get('supported', False) else "Non supporté"
            ttk.Label(
                info_frame, 
                text=f"État: {status}"
            ).grid(row=row, column=0, sticky=tk.W, padx=20)
            row += 1
            
            if info.get('supported', False):
                if info.get('library'):
                    ttk.Label(
                        info_frame, 
                        text=f"Bibliothèque: {info['library']}"
                    ).grid(row=row, column=0, sticky=tk.W, padx=20)
                    row += 1
                elif info.get('command'):
                    ttk.Label(
                        info_frame, 
                        text=f"Commande: {info['command']}"
                    ).grid(row=row, column=0, sticky=tk.W, padx=20)
                    row += 1
            
            # Ajouter un séparateur
            ttk.Separator(info_frame, orient=tk.HORIZONTAL).grid(
                row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=10
            )
            row += 1
        
        # Bouton pour fermer la fenêtre
        ttk.Button(
            formats_window, 
            text="Fermer", 
            command=formats_window.destroy
        ).pack(pady=10)
    
    def show_about_dialog(self):
        """Affiche la boîte de dialogue À propos."""
        # Créer une fenêtre modale
        about_window = tk.Toplevel(self.root)
        about_window.title("À propos de PhotoManager")
        about_window.geometry("400x300")
        about_window.transient(self.root)
        about_window.grab_set()
        
        # Centrer la fenêtre
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 300) // 2
        about_window.geometry(f"+{x}+{y}")
        
        # Titre
        ttk.Label(
            about_window, 
            text="PhotoManager", 
            font=("Helvetica", 16, "bold")
        ).pack(pady=(20, 5))
        
        # Version
        ttk.Label(
            about_window, 
            text="Version 1.0.0"
        ).pack(pady=(0, 10))
        
        # Description
        ttk.Label(
            about_window, 
            text="Application de gestion et d'analyse d'images",
            wraplength=350
        ).pack(padx=20, pady=5)
        
        # Copyright
        ttk.Label(
            about_window, 
            text="© 2025 Votre Nom"
        ).pack(pady=5)
        
        # Lien vers le site web
        link_label = ttk.Label(
            about_window,
            text="https://github.com/votrenom/photomanager",
            foreground="blue",
            cursor="hand2"
        )
        link_label.pack(pady=5)
        link_label.bind(
            "<Button-1>", 
            lambda e: webbrowser.open("https://github.com/votrenom/photomanager")
        )
        
        # Bouton pour fermer la fenêtre
        ttk.Button(
            about_window, 
            text="Fermer", 
            command=about_window.destroy
        ).pack(pady=20)
    
    def on_window_resize(self, event):
        """
        Gestionnaire d'événements pour le redimensionnement de la fenêtre.

        Args:
            event: Événement de redimensionnement
        """
        from utils.config_manager import get_config

        # Ne faire quelque chose que si l'événement concerne la fenêtre principale
        if event.widget == self.root:
            # Save window size to config
            config = get_config()
            config.set('preferences.window_width', event.width)
            config.set('preferences.window_height', event.height)
            # Don't save immediately on every resize to avoid I/O overhead
            # Will be saved on close
    
    def on_closing(self):
        """Gestionnaire pour la fermeture de l'application."""
        # Vérifier s'il y a des tâches en cours
        has_running_tasks = (
            getattr(self.file_org_frame, 'has_running_tasks', lambda: False)() 
        )
        
        if has_running_tasks:
            # Demander confirmation avant de quitter
            if not messagebox.askyesno(
                "Tâches en cours",
                "Des tâches sont encore en cours d'exécution. Êtes-vous sûr de vouloir quitter ?"
            ):
                return

        # Save preferences and window settings
        from utils.config_manager import get_config
        config = get_config()
        config.save()

        # Fermer l'application
        self.root.destroy()


def main():
    """Fonction principale pour lancer l'application."""
    root = tk.Tk()
    app = PhotoManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()