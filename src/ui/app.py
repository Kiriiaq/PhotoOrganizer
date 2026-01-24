"""
Application principale PhotoOrganizer.
Interface moderne avec CustomTkinter.
"""

import os
import sys
import logging
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox

# Configuration du chemin
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import get_config
from utils.logger import setup_logging

from .frames.organize_frame import OrganizeFrame
from .frames.duplicates_frame import DuplicatesFrame
from .frames.history_frame import HistoryFrame
from .frames.settings_frame import SettingsFrame

logger = logging.getLogger(__name__)


class PhotoOrganizerApp(ctk.CTk):
    """Application principale PhotoOrganizer."""

    APP_NAME = "PhotoOrganizer"
    APP_VERSION = "2.0.0"

    def __init__(self):
        """Initialise l'application."""
        super().__init__()

        # Configuration
        self.config_manager = get_config()
        config = self.config_manager.config

        # Configuration de l'apparence
        ctk.set_appearance_mode(config.theme)
        ctk.set_default_color_theme("blue")

        # Configuration de la fenêtre
        self.title(f"{self.APP_NAME} v{self.APP_VERSION}")
        self.geometry(f"{config.window_width}x{config.window_height}")
        self.minsize(900, 600)

        # Position de la fenêtre
        if config.window_x is not None and config.window_y is not None:
            self.geometry(f"+{config.window_x}+{config.window_y}")

        # Icône (si disponible)
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Variables partagées
        self.source_folder = ctk.StringVar()
        self.dest_folder = ctk.StringVar()

        # Créer l'interface
        self._create_ui()

        # Événements de fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Restaurer les derniers dossiers utilisés
        if config.recent_sources:
            self.source_folder.set(config.recent_sources[0])
        if config.recent_destinations:
            self.dest_folder.set(config.recent_destinations[0])

    def _create_ui(self):
        """Crée l'interface utilisateur."""
        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Header avec titre et thème
        self._create_header()

        # Navigation par onglets
        self._create_navigation()

        # Barre de statut
        self._create_status_bar()

    def _create_header(self):
        """Crée l'en-tête de l'application."""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        # Titre
        title_label = ctk.CTkLabel(
            header_frame,
            text=f"📷 {self.APP_NAME}",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left")

        # Bouton de thème
        self.theme_button = ctk.CTkButton(
            header_frame,
            text="🌙" if ctk.get_appearance_mode() == "Light" else "☀️",
            width=40,
            command=self._toggle_theme
        )
        self.theme_button.pack(side="right", padx=5)

        # Bouton d'aide
        help_button = ctk.CTkButton(
            header_frame,
            text="❓",
            width=40,
            command=self._show_about
        )
        help_button.pack(side="right", padx=5)

    def _create_navigation(self):
        """Crée la navigation par onglets."""
        # Tabview
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Onglets
        self.tabview.add("📁 Organisation")
        self.tabview.add("🔍 Doublons")
        self.tabview.add("📜 Historique")
        self.tabview.add("⚙️ Paramètres")

        # Frame Organisation
        self.organize_frame = OrganizeFrame(
            self.tabview.tab("📁 Organisation"),
            source_var=self.source_folder,
            dest_var=self.dest_folder,
            status_callback=self._update_status
        )
        self.organize_frame.pack(fill="both", expand=True)

        # Frame Doublons
        self.duplicates_frame = DuplicatesFrame(
            self.tabview.tab("🔍 Doublons"),
            source_var=self.source_folder,
            status_callback=self._update_status
        )
        self.duplicates_frame.pack(fill="both", expand=True)

        # Frame Historique
        self.history_frame = HistoryFrame(
            self.tabview.tab("📜 Historique"),
            status_callback=self._update_status
        )
        self.history_frame.pack(fill="both", expand=True)

        # Frame Paramètres
        self.settings_frame = SettingsFrame(
            self.tabview.tab("⚙️ Paramètres"),
            config_manager=self.config_manager,
            on_theme_change=self._apply_theme
        )
        self.settings_frame.pack(fill="both", expand=True)

    def _create_status_bar(self):
        """Crée la barre de statut."""
        self.status_frame = ctk.CTkFrame(self.main_frame, height=30)
        self.status_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.status_frame.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Prêt",
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10, fill="x", expand=True)

        # Progress bar (cachée par défaut)
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=200)
        self.progress_bar.set(0)

    def _update_status(self, message: str, progress: Optional[float] = None):
        """
        Met à jour la barre de statut.

        Args:
            message: Message à afficher
            progress: Progression (0-1) ou None pour cacher la barre
        """
        self.status_label.configure(text=message)

        if progress is not None:
            if not self.progress_bar.winfo_ismapped():
                self.progress_bar.pack(side="right", padx=10)
            self.progress_bar.set(progress)
        else:
            if self.progress_bar.winfo_ismapped():
                self.progress_bar.pack_forget()

        self.update_idletasks()

    def _toggle_theme(self):
        """Bascule entre thème clair et sombre."""
        current = ctk.get_appearance_mode()
        new_theme = "Light" if current == "Dark" else "Dark"
        self._apply_theme(new_theme.lower())

    def _apply_theme(self, theme: str):
        """Applique un thème."""
        ctk.set_appearance_mode(theme)
        self.config_manager.set('theme', theme)

        # Mettre à jour l'icône du bouton
        self.theme_button.configure(
            text="🌙" if theme == "light" else "☀️"
        )

    def _show_about(self):
        """Affiche la fenêtre À propos."""
        about_text = f"""
{self.APP_NAME} v{self.APP_VERSION}

Organiseur intelligent de photos et vidéos.

Fonctionnalités:
• Organisation par date, appareil, localisation
• Détection des doublons
• Extraction des métadonnées EXIF/GPS
• Géocodage inverse
• Annulation des opérations

Formats supportés:
• Images: JPG, PNG, HEIC, RAW, etc.
• Vidéos: MP4, MOV, AVI, etc.

© 2024-2026 PhotoOrganizer Team
Licence MIT
"""
        messagebox.showinfo("À propos", about_text)

    def _on_closing(self):
        """Gère la fermeture de l'application."""
        # Sauvegarder la position et la taille de la fenêtre
        self.config_manager.set('window_width', self.winfo_width())
        self.config_manager.set('window_height', self.winfo_height())
        self.config_manager.set('window_x', self.winfo_x())
        self.config_manager.set('window_y', self.winfo_y())

        # Sauvegarder les dossiers récents
        if self.source_folder.get():
            self.config_manager.add_recent_source(self.source_folder.get())
        if self.dest_folder.get():
            self.config_manager.add_recent_destination(self.dest_folder.get())

        self.destroy()


def main():
    """Point d'entrée principal."""
    # Configuration du logging
    setup_logging(level="INFO")
    logger.info("Démarrage de PhotoOrganizer")

    # Lancer l'application
    app = PhotoOrganizerApp()
    app.mainloop()

    logger.info("Fermeture de PhotoOrganizer")


if __name__ == "__main__":
    main()
