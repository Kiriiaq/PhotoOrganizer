"""
Frame des paramètres.
Configuration de l'application.
"""

from tkinter import messagebox
from typing import Callable, Optional

import customtkinter as ctk

from ui.theme import (
    BTN_H_STD,
    CHECK_FG,
    HINT_COLOR,
    LABEL_MUTED,
    PAD_L,
    PAD_M,
    PAD_S,
    font_hint,
    font_label,
    font_section,
    make_checkbox,
    make_radio,
    neutral_button,
    primary_button,
    warning_button,
)
from utils.cache import get_cache
from utils.config import ConfigManager
from utils.logger import get_log_dir, set_log_level

# Aliases retro-compat avec l'ancien nommage local
_make_checkbox = make_checkbox
_make_radio = make_radio

from ui.tooltip import attach_tooltip
from ui.tooltips_fr import SETTINGS as TIPS


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
        self._attach_tooltips()

    def _attach_tooltips(self):
        """Attache les info-bulles aux widgets clés du panneau Paramètres."""
        if hasattr(self, "schedule_switch"):
            attach_tooltip(self.schedule_switch, TIPS["schedule_enabled"])

    def _create_ui(self):
        """Refonte UI v5 (retours testeur 2026-05-13).

        Sections retirées suite aux retours :
          - Apparence (W102) : redondant avec le bouton thème du header.
          - Comportement par défaut (W103-W104) : déjà accessible dans Organize.
          - Performance / Cache (W105-W107) : jugé inutile par le testeur.
          - Auto-save planning Heure (W117) : inutile.

        Sections conservées :
          - Planification automatique (depuis Organize)
          - API & Services (géocodage + clé)
          - Logs & Données (niveau log + dossiers récents)
        """
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # ZONE 1 : sections scrollables
        scrollable = ctk.CTkScrollableFrame(self)
        scrollable.grid(row=0, column=0, sticky="nsew", padx=PAD_M, pady=(PAD_M, PAD_S))

        # Sections W102 (Apparence), W103-W104 (Comportement défaut),
        # W105-W107 (Performance/Cache) retirées suite aux retours testeur.
        self._create_schedule_section(scrollable)   # Planification
        self._create_api_section(scrollable)        # API & Services
        self._create_data_section(scrollable)       # Logs & Données

        # ZONE 2 : boutons sticky bottom (toujours visibles)
        self._create_buttons_sticky()

    def _create_schedule_section(self, parent):
        """Section "Planification automatique" — déplacée depuis OrganizeFrame.

        L'UI ici met juste à jour les vars de l'organize_frame ; le scheduler
        est hébergé là-bas (via JobScheduler). On accède via la fenêtre racine
        (`winfo_toplevel().organize_frame`) pour rester découplé.
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=PAD_M)

        ctk.CTkLabel(
            section, text="📅 Planification automatique quotidienne",
            font=font_section(),
        ).pack(anchor="w", padx=PAD_M, pady=(PAD_M, PAD_S))

        ctk.CTkLabel(
            section,
            text="Tant que l'application est ouverte, organise automatiquement à l'heure indiquée.",
            font=font_hint(), text_color=HINT_COLOR,
        ).pack(anchor="w", padx=PAD_M, pady=(0, PAD_S))

        # Référence à l'OrganizeFrame parent (créé avant SettingsFrame dans app.py)
        # On accède aux vars via une méthode helper pour graceful degradation.
        org_frame = self._get_organize_frame()
        if org_frame is None:
            ctk.CTkLabel(
                section,
                text="⚠️ OrganizeFrame indisponible — planification désactivée.",
                text_color=LABEL_MUTED,
            ).pack(anchor="w", padx=PAD_M, pady=(0, PAD_M))
            return

        # Toggle + heure
        row = ctk.CTkFrame(section, fg_color="transparent")
        row.pack(fill="x", padx=PAD_M, pady=PAD_S)

        self.schedule_switch = ctk.CTkSwitch(
            row,
            text="Activer la planification quotidienne",
            variable=org_frame.schedule_enabled,
            command=org_frame._on_schedule_toggle,
            font=font_label(),
            progress_color=CHECK_FG,
        )
        self.schedule_switch.pack(side="left")

        ctk.CTkLabel(row, text="Heure :",
                     font=font_label()).pack(side="left", padx=(PAD_L, PAD_S))
        ctk.CTkEntry(row, textvariable=org_frame.schedule_time,
                     placeholder_text="HH:MM",
                     width=80, height=BTN_H_STD).pack(side="left")

        # Statut "Prochaine exécution : ..."
        ctk.CTkLabel(
            section, textvariable=org_frame.schedule_status_var,
            font=font_label(), text_color=LABEL_MUTED, anchor="w",
        ).pack(anchor="w", padx=PAD_M, pady=(0, PAD_M))

    def _get_organize_frame(self):
        """Retourne l'OrganizeFrame parent ou None s'il n'est pas accessible."""
        try:
            return self.winfo_toplevel().organize_frame
        except AttributeError:
            return None

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

        # Niveau de log — audit 2026-05-15 : appliqué à chaud (plus besoin
        # de relancer l'app pour voir l'effet), accolé à un bouton « Voir
        # les logs » qui ouvre le dossier de logs dans l'explorateur.
        log_frame = ctk.CTkFrame(section, fg_color="transparent")
        log_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(log_frame, text="Niveau de log :").pack(side="left", padx=5)
        ctk.CTkOptionMenu(
            log_frame,
            variable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            command=lambda v: set_log_level(v),
        ).pack(side="left", padx=5)
        ctk.CTkLabel(
            log_frame, text="(appliqué immédiatement)",
            font=font_hint(), text_color=HINT_COLOR,
        ).pack(side="left", padx=PAD_S)

        neutral_button(
            log_frame, text="📂 Voir les logs",
            command=self._open_log_dir, width=140,
        ).pack(side="right", padx=PAD_S)

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

    def _create_buttons_sticky(self):
        """Boutons sauvegarde / réinitialiser sticky bottom (toujours visibles)."""
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
        buttons_frame.columnconfigure(1, weight=1)  # spacer

        # Réinitialiser à gauche (warning, secondaire)
        warning_button(
            buttons_frame, text="🔄 Réinitialiser",
            command=self._reset_settings,
        ).grid(row=0, column=0, sticky="w")

        # Sauvegarder à droite (primary, action principale)
        primary_button(
            buttons_frame, text="💾 Sauvegarder",
            command=self._save_settings,
        ).grid(row=0, column=2, sticky="e")

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

    def _open_log_dir(self):
        """Ouvre le dossier des logs dans l'explorateur (audit 2026-05-15).

        Plateforme :
        - Windows : ``os.startfile``
        - macOS   : ``open <path>`` via subprocess
        - Linux   : ``xdg-open <path>`` via subprocess
        """
        import os
        import subprocess
        import sys

        log_dir = get_log_dir()
        try:
            if sys.platform == "win32":
                os.startfile(str(log_dir))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_dir)])  # noqa: S603
            else:
                subprocess.Popen(["xdg-open", str(log_dir)])  # noqa: S603
        except OSError as exc:
            messagebox.showerror(
                "Logs",
                f"Impossible d'ouvrir le dossier de logs :\n{log_dir}\n\n{exc}",
            )

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
