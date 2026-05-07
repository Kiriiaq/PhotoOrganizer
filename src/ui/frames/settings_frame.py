"""
Frame des paramètres.
Configuration de l'application.
"""

from typing import Optional, Callable

import customtkinter as ctk
from tkinter import messagebox

from utils.config import ConfigManager
from utils.cache import get_cache

# Style cohérent avec OrganizeFrame (cf. organize_frame.py pour la rationale).
_FONT_SIZE = 13
_FG = ("#1f6aa5", "#1f6aa5")
_HOVER = ("#144870", "#144870")
_BORDER = ("gray40", "gray60")


def _make_checkbox(parent, **kwargs):
    defaults = {
        "font": ctk.CTkFont(size=_FONT_SIZE),
        "fg_color": _FG, "hover_color": _HOVER,
        "border_color": _BORDER, "border_width": 2,
    }
    defaults.update(kwargs)
    return ctk.CTkCheckBox(parent, **defaults)


def _make_radio(parent, **kwargs):
    defaults = {
        "font": ctk.CTkFont(size=_FONT_SIZE),
        "fg_color": _FG, "hover_color": _HOVER,
        "border_color": _BORDER, "border_width_unchecked": 2,
    }
    defaults.update(kwargs)
    return ctk.CTkRadioButton(parent, **defaults)


class SettingsFrame(ctk.CTkFrame):
    """Frame des paramètres de l'application."""

    def __init__(
        self,
        parent,
        config_manager: ConfigManager,
        on_theme_change: Optional[Callable] = None
    ):
        """
        Initialise le frame des paramètres.

        Args:
            parent: Widget parent
            config_manager: Gestionnaire de configuration
            on_theme_change: Callback lors du changement de thème
        """
        super().__init__(parent, fg_color="transparent")

        self.config_manager = config_manager
        self.on_theme_change = on_theme_change or (lambda t: None)
        self.config = config_manager.config

        # Variables liées aux paramètres
        self.theme_var = ctk.StringVar(value=self.config.theme)
        self.default_action_var = ctk.StringVar(value=self.config.default_action)
        self.recursive_var = ctk.BooleanVar(value=self.config.default_recursive)
        self.cache_enabled_var = ctk.BooleanVar(value=self.config.cache_enabled)
        self.geocoding_var = ctk.BooleanVar(value=self.config.geocoding_enabled)
        self.log_level_var = ctk.StringVar(value=self.config.log_level)
        self.api_key_var = ctk.StringVar(value=self.config.positionstack_api_key)

        self._create_ui()

    def _create_ui(self):
        """Crée l'interface utilisateur."""
        # Scrollable frame pour toutes les options
        scrollable = ctk.CTkScrollableFrame(self)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)

        # Section Apparence
        self._create_appearance_section(scrollable)

        # Section Comportement par défaut
        self._create_defaults_section(scrollable)

        # Section Performance
        self._create_performance_section(scrollable)

        # Section API
        self._create_api_section(scrollable)

        # Section Données
        self._create_data_section(scrollable)

        # Boutons
        self._create_buttons(scrollable)

    def _create_appearance_section(self, parent):
        """Crée la section Apparence."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            section,
            text="🎨 Apparence",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Thème
        theme_frame = ctk.CTkFrame(section, fg_color="transparent")
        theme_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(theme_frame, text="Thème:").pack(side="left", padx=5)
        _make_radio(
            theme_frame,
            text="Sombre",
            variable=self.theme_var,
            value="dark",
            command=self._on_theme_change
        ).pack(side="left", padx=10)
        _make_radio(
            theme_frame,
            text="Clair",
            variable=self.theme_var,
            value="light",
            command=self._on_theme_change
        ).pack(side="left", padx=10)
        _make_radio(
            theme_frame,
            text="Système",
            variable=self.theme_var,
            value="system",
            command=self._on_theme_change
        ).pack(side="left", padx=10)

    def _create_defaults_section(self, parent):
        """Crée la section Comportement par défaut."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            section,
            text="⚙️ Comportement par défaut",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Action par défaut
        action_frame = ctk.CTkFrame(section, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(action_frame, text="Action par défaut:").pack(side="left", padx=5)
        _make_radio(
            action_frame,
            text="Copier",
            variable=self.default_action_var,
            value="copy"
        ).pack(side="left", padx=10)
        _make_radio(
            action_frame,
            text="Déplacer",
            variable=self.default_action_var,
            value="move"
        ).pack(side="left", padx=10)

        # Récursif par défaut
        _make_checkbox(
            section,
            text="Parcourir les sous-dossiers par défaut",
            variable=self.recursive_var
        ).pack(anchor="w", padx=20, pady=5)

    def _create_performance_section(self, parent):
        """Crée la section Performance."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            section,
            text="⚡ Performance",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Cache
        _make_checkbox(
            section,
            text="Activer le cache des métadonnées",
            variable=self.cache_enabled_var
        ).pack(anchor="w", padx=20, pady=5)

        # Statistiques du cache
        cache = get_cache()
        stats = cache.get_stats()

        stats_label = ctk.CTkLabel(
            section,
            text=f"Cache: {stats['memory_entries']} entrées en mémoire, "
                 f"{stats['disk_size_formatted']} sur disque, "
                 f"Taux de succès: {stats['hit_rate']}",
            text_color="gray"
        )
        stats_label.pack(anchor="w", padx=40, pady=5)

        # Bouton vider le cache
        ctk.CTkButton(
            section,
            text="🗑️ Vider le cache",
            command=self._clear_cache,
            width=150
        ).pack(anchor="w", padx=40, pady=5)

    def _create_api_section(self, parent):
        """Crée la section API."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            section,
            text="🔑 API & Services",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Géocodage
        _make_checkbox(
            section,
            text="Activer le géocodage inverse (noms de lieux)",
            variable=self.geocoding_var
        ).pack(anchor="w", padx=20, pady=5)

        # Clé API PositionStack
        api_frame = ctk.CTkFrame(section, fg_color="transparent")
        api_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(api_frame, text="Clé API PositionStack:").pack(side="left", padx=5)
        ctk.CTkEntry(
            api_frame,
            textvariable=self.api_key_var,
            width=300,
            show="*",
            placeholder_text="Optionnel - pour géocodage avancé"
        ).pack(side="left", padx=5)

        info_label = ctk.CTkLabel(
            section,
            text="💡 Sans clé API, le géocodage utilise OpenStreetMap (gratuit mais limité).",
            text_color="gray"
        )
        info_label.pack(anchor="w", padx=20, pady=5)

    def _create_data_section(self, parent):
        """Crée la section Données."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            section,
            text="📊 Logs & Données",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Niveau de log
        log_frame = ctk.CTkFrame(section, fg_color="transparent")
        log_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(log_frame, text="Niveau de log:").pack(side="left", padx=5)
        ctk.CTkOptionMenu(
            log_frame,
            variable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"]
        ).pack(side="left", padx=5)

        # Dossiers récents
        recent_frame = ctk.CTkFrame(section, fg_color="transparent")
        recent_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            recent_frame,
            text=f"Dossiers récents: {len(self.config.recent_sources)} sources, "
                 f"{len(self.config.recent_destinations)} destinations"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            recent_frame,
            text="Effacer",
            command=self._clear_recent,
            width=80
        ).pack(side="left", padx=10)

    def _create_buttons(self, parent):
        """Crée les boutons de sauvegarde."""
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            buttons_frame,
            text="💾 Sauvegarder",
            command=self._save_settings,
            fg_color="green",
            hover_color="darkgreen"
        ).pack(side="left", padx=5, expand=True, fill="x")

        ctk.CTkButton(
            buttons_frame,
            text="🔄 Réinitialiser",
            command=self._reset_settings,
            fg_color="orange",
            hover_color="darkorange"
        ).pack(side="left", padx=5, expand=True, fill="x")

    def _on_theme_change(self):
        """Gère le changement de thème."""
        theme = self.theme_var.get()
        self.on_theme_change(theme)

    def _save_settings(self):
        """Sauvegarde les paramètres."""
        self.config_manager.set('theme', self.theme_var.get())
        self.config_manager.set('default_action', self.default_action_var.get())
        self.config_manager.set('default_recursive', self.recursive_var.get())
        self.config_manager.set('cache_enabled', self.cache_enabled_var.get())
        self.config_manager.set('geocoding_enabled', self.geocoding_var.get())
        self.config_manager.set('log_level', self.log_level_var.get())
        self.config_manager.set('positionstack_api_key', self.api_key_var.get())

        messagebox.showinfo("Succès", "Les paramètres ont été sauvegardés.")

    def _reset_settings(self):
        """Réinitialise les paramètres par défaut."""
        if not messagebox.askyesno(
            "Confirmation",
            "Voulez-vous réinitialiser tous les paramètres aux valeurs par défaut?"
        ):
            return

        self.config_manager.reset_to_defaults()

        # Mettre à jour les variables
        self.theme_var.set(self.config_manager.config.theme)
        self.default_action_var.set(self.config_manager.config.default_action)
        self.recursive_var.set(self.config_manager.config.default_recursive)
        self.cache_enabled_var.set(self.config_manager.config.cache_enabled)
        self.geocoding_var.set(self.config_manager.config.geocoding_enabled)
        self.log_level_var.set(self.config_manager.config.log_level)
        self.api_key_var.set(self.config_manager.config.positionstack_api_key)

        messagebox.showinfo("Succès", "Les paramètres ont été réinitialisés.")

    def _clear_cache(self):
        """Vide le cache des métadonnées."""
        if not messagebox.askyesno(
            "Confirmation",
            "Voulez-vous vider le cache des métadonnées?"
        ):
            return

        cache = get_cache()
        cache.clear()

        messagebox.showinfo("Succès", "Le cache a été vidé.")

    def _clear_recent(self):
        """Efface les dossiers récents."""
        if not messagebox.askyesno(
            "Confirmation",
            "Voulez-vous effacer l'historique des dossiers récents?"
        ):
            return

        self.config_manager.config.recent_sources.clear()
        self.config_manager.config.recent_destinations.clear()
        self.config_manager.save()

        messagebox.showinfo("Succès", "L'historique des dossiers récents a été effacé.")
