"""
Application principale PhotoOrganizer.
Interface moderne avec CustomTkinter.
"""

import logging
import os
import sys
import tkinter as tk
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

# Configuration du chemin
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.metadata.gps_processor import get_processor as get_gps_processor
from core.operations.file_manager import FileManager
from utils.cache import init_cache
from utils.config import get_config

from .frames.duplicates_frame import DuplicatesFrame
from .frames.history_frame import HistoryFrame
from .frames.organize_frame import OrganizeFrame
from .frames.settings_frame import SettingsFrame

logger = logging.getLogger(__name__)


class PhotoOrganizerApp(ctk.CTk):
    """Application principale PhotoOrganizer."""

    APP_NAME = "PhotoOrganizer"
    APP_VERSION = "2.0.0"

    def __init__(self):
        """Initialise l'application."""
        super().__init__()

        # Activation du drag-and-drop (tkinterdnd2) sur la racine Tk.
        # Comme on hérite de ctk.CTk (et non de TkinterDnD.Tk()), on doit
        # charger le package Tcl `tkdnd` à la main puis brancher le mixin
        # `DnDWrapper` sur notre classe pour que les widgets enfants
        # héritent de drop_target_register/dnd_bind. Si tkinterdnd2 n'est
        # pas installé OU si le chargement échoue, on continue sans DnD.
        self._enable_tk_dnd()

        # Configuration
        self.config_manager = get_config()
        config = self.config_manager.config

        # Initialiser les singletons depuis AppConfig
        init_cache(
            ttl_hours=config.cache_ttl_hours,
            max_size_mb=config.max_cache_size_mb,
        )
        get_gps_processor().geocoding_enabled = config.geocoding_enabled

        # Configuration de l'apparence
        ctk.set_appearance_mode(config.theme)
        ctk.set_default_color_theme("blue")
        # Adoucir le thème clair : par défaut CTk light est très blanc,
        # ce qui crée des frames quasi invisibles entre eux. On force un
        # gris pâle (gray86) sur le fond root et un gris ardoise pour les
        # frames internes (gray92). Le thème dark conserve ses valeurs.
        # NB : ces couleurs sont appliquées en (light, dark) — CTk choisit
        # automatiquement selon le mode actif.
        self._LIGHT_BG_ROOT  = ("#dcdcdc", "#1a1a1a")   # fond fenêtre
        self._LIGHT_BG_FRAME = ("#e8e8e8", "#242424")   # frames principaux
        self._LIGHT_BG_INNER = ("#f0f0f0", "#2b2b2b")   # zones internes
        self.configure(fg_color=self._LIGHT_BG_ROOT)

        # Configuration de la fenêtre
        self.title(f"{self.APP_NAME} v{self.APP_VERSION}")
        self.geometry(f"{config.window_width}x{config.window_height}")
        # Refonte UI v3 : minsize relevé à 800×550 pour garantir le
        # layout 3-zones de l'onglet Organisation (top fixe / centre /
        # bottom fixe). En dessous, l'IHM devient inutilisable car les
        # 3 zones se chevauchent.
        self.minsize(800, 550)

        # Position de la fenêtre
        if config.window_x is not None and config.window_y is not None:
            self.geometry(f"+{config.window_x}+{config.window_y}")

        # Icône (si disponible) — cherche resources/icons puis fallback assets/
        self._install_icon()

        # Variables partagées
        self.source_folder = ctk.StringVar()
        self.dest_folder = ctk.StringVar()

        # FileManager partagé — sans cela l'onglet Historique n'a rien à
        # afficher (chaque frame instanciait son propre gestionnaire).
        self.file_manager = FileManager()

        # Créer l'interface
        self._create_ui()

        # Raccourcis clavier de navigation entre onglets (Ctrl+1..Ctrl+4)
        self._install_shortcuts()

        # Événements de fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Restaurer les derniers dossiers utilisés
        if config.recent_sources:
            self.source_folder.set(config.recent_sources[0])
        if config.recent_destinations:
            self.dest_folder.set(config.recent_destinations[0])

    def _create_ui(self):
        """Crée l'interface utilisateur.

        Layout :
        - Header non-scrollable (titre + boutons thème/aide)
        - Tabview central, ses onglets sont eux-mêmes scrollables si besoin
        - Status bar toujours visible en bas

        Pour que l'IHM reste utilisable lorsque la fenêtre est réduite, on
        utilise une grille avec poids et le tabview prend toute la place
        verticale disponible. Les frames de chaque onglet hébergent leurs
        propres CTkScrollableFrame.
        """
        # Grille root pour répartition propre header / contenu / status
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Frame principal (un seul container plein-écran)
        self.main_frame = ctk.CTkFrame(self, fg_color=self._LIGHT_BG_FRAME)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 4))
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header (row 0)
        self._create_header()

        # Navigation onglets (row 1, expansible)
        self._create_navigation()

        # Barre de statut (row 2)
        self._create_status_bar()

    def _create_header(self):
        """En-tête de l'application — refonte UI v3.

        Titre 18pt + boutons icône-only carrés 32×40 (cohérent avec le
        design system). Conserve la disposition titre-gauche / icônes-droite.
        """
        from ui.theme import (
            BTN_H_STD,
            BTN_W_ICON,
            PAD_M,
            PAD_S,
            font_title,
        )

        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_M, PAD_S))

        # Titre (taille design system, plus discret que 24pt)
        title_label = ctk.CTkLabel(
            header_frame,
            text=f"📷 {self.APP_NAME}",
            font=font_title(),
        )
        title_label.pack(side="left")

        # Boutons icône-only à droite, hauteur normalisée 32
        self.theme_button = ctk.CTkButton(
            header_frame,
            text="🌙" if ctk.get_appearance_mode() == "Light" else "☀️",
            width=BTN_W_ICON, height=BTN_H_STD,
            command=self._toggle_theme,
        )
        self.theme_button.pack(side="right", padx=PAD_S)

        help_button = ctk.CTkButton(
            header_frame,
            text="❓",
            width=BTN_W_ICON, height=BTN_H_STD,
            command=self._show_about,
        )
        help_button.pack(side="right", padx=PAD_S)

    def _create_navigation(self):
        """Crée la navigation par onglets."""
        # Tabview en grille pour qu'il prenne toute la place verticale
        # disponible. Les frames internes utilisent eux-mêmes des grids/packs
        # avec sticky/expand pour rester accessibles en petite fenêtre.
        self.tabview = ctk.CTkTabview(
            self.main_frame, fg_color=self._LIGHT_BG_INNER
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

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
            file_manager=self.file_manager,
            status_callback=self._update_status
        )
        self.organize_frame.pack(fill="both", expand=True)

        # Frame Doublons (FileManager partagé pour que les MOVE soient
        # historisés et qu'un rollback soit possible depuis l'Historique)
        self.duplicates_frame = DuplicatesFrame(
            self.tabview.tab("🔍 Doublons"),
            source_var=self.source_folder,
            file_manager=self.file_manager,
            status_callback=self._update_status,
            navigate_callback=lambda tab_name: self.tabview.set(tab_name),
        )
        self.duplicates_frame.pack(fill="both", expand=True)

        # Frame Historique (partage le même FileManager qu'Organize)
        self.history_frame = HistoryFrame(
            self.tabview.tab("📜 Historique"),
            file_manager=self.file_manager,
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

        # Rafraîchir l'historique au changement d'onglet
        self.tabview.configure(command=self._on_tab_changed)

    def _create_status_bar(self):
        """Crée la barre de statut."""
        self.status_frame = ctk.CTkFrame(self.main_frame, height=30)
        self.status_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.status_frame.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Prêt",
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10, fill="x", expand=True)

        # Lot B (audit 2026-05-14, T-036) : progress bar TOUJOURS visible
        # dans la status bar, dès l'init à 0 %. L'utilisateur sait où la
        # trouver et n'est plus surpris par son apparition soudaine.
        self.progress_bar = ctk.CTkProgressBar(
            self.status_frame, width=200, height=16,
            border_width=1, border_color=("gray60", "gray40"),
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", padx=10)

    def _update_status(self, message: str, progress: Optional[float] = None):
        """
        Met à jour la barre de statut.

        Args:
            message: Message à afficher
            progress: Progression (0-1) ou None pour remettre la barre à 0
        """
        self.status_label.configure(text=message)
        # Progress bar toujours visible. None → reset à 0 (idle visible).
        self.progress_bar.set(progress if progress is not None else 0)

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

    def _on_tab_changed(self):
        """Callback de changement d'onglet : rafraîchit l'historique."""
        try:
            if self.tabview.get() == "📜 Historique":
                self.history_frame.refresh()
        except (tk.TclError, AttributeError) as exc:
            # D-04 (audit 2026-05-14) : TclError si widget détruit, AttributeError
            # si history_frame pas encore monté (timing init).
            logger.debug(f"_on_tab_changed: {exc}")

    # ------------------------------------------------------------------
    # Raccourcis clavier (T-016..T-019 : navigation entre onglets)
    # ------------------------------------------------------------------
    TAB_NAMES = (
        "📁 Organisation",
        "🔍 Doublons",
        "📜 Historique",
        "⚙️ Paramètres",
    )

    def _install_shortcuts(self):
        """Installe les raccourcis clavier globaux (Lot A audit 2026-05-14).

        Stratégie de robustesse :
        - ``bind_all("<Control-Key-N>")`` pour la navigation entre onglets,
          MAIS certains widgets (CTkEntry/Textbox) peuvent consommer la
          touche avant qu'elle ne remonte au niveau ``all`` ;
        - on **double les bindings** avec ``<Alt-Key-N>`` qui n'est jamais
          consommé par les Entry — fallback garanti même focus dans un champ ;
        - ``<Control-Key-5>`` (T-020) : pas de 5e onglet → câblé sur
          « focus champ Source de l'onglet courant » (action utile sinon perdue) ;
        - ``<Escape>`` (T-023) : annulation contextuelle de l'opération en
          cours sur l'onglet actif. No-op si aucune op en cours.
        - ``F1`` = aide.
        """
        for i, name in enumerate(self.TAB_NAMES, start=1):
            self.bind_all(
                f"<Control-Key-{i}>",
                lambda _e, n=name: self._select_tab(n),
            )
            # Doublon Alt+N pour résilience face aux widgets qui consomment Ctrl+N
            self.bind_all(
                f"<Alt-Key-{i}>",
                lambda _e, n=name: self._select_tab(n),
            )

        # Ctrl+5 : focus champ source du panneau Organisation
        self.bind_all("<Control-Key-5>", lambda _e: self._focus_source_entry())
        # Escape : annulation contextuelle (cf. _cancel_active_op)
        self.bind_all("<Escape>", lambda _e: self._cancel_active_op())
        # F1 : aide
        self.bind_all("<F1>", lambda _e: self._show_about())

    def _focus_source_entry(self):
        """Met le focus sur le champ Source du panneau Organisation."""
        try:
            self.tabview.set("📁 Organisation")
            self.organize_frame.source_entry.focus_set()
        except (tk.TclError, AttributeError) as exc:
            # D-04 (audit 2026-05-14) : si l'onglet/widget est détruit ou pas
            # encore prêt, on log et on continue.
            logger.debug(f"_focus_source_entry: {exc}")

    def _cancel_active_op(self):
        """Annule l'opération en cours sur l'onglet actif (Escape — T-023).

        Aiguillage simple :
        - 📁 Organisation → ``organize_frame._cancel_operation()``
        - 🔍 Doublons     → ``duplicates_frame._cancel_operation()``
        Autres onglets : no-op silencieux.
        Si aucune op n'est en cours, ``_cancel_operation`` est idempotent
        (positionne juste le flag et désactive le bouton).
        """
        try:
            active = self.tabview.get()
            if active == "📁 Organisation":
                if getattr(self.organize_frame, "_operation_running", False):
                    self.organize_frame._cancel_operation()
            elif active == "🔍 Doublons":
                if getattr(self.duplicates_frame, "_operation_running", False):
                    self.duplicates_frame._cancel_operation()
        except (tk.TclError, AttributeError) as exc:
            # D-04 (audit 2026-05-14) : tabview détruit ou frame absent.
            logger.debug(f"_cancel_active_op: {exc}")

    def _select_tab(self, tab_name: str):
        """Sélectionne un onglet par son nom."""
        try:
            self.tabview.set(tab_name)
            self._on_tab_changed()
        except (tk.TclError, AttributeError) as exc:
            # D-04 (audit 2026-05-14) : nom inconnu ou widget détruit.
            logger.warning(f"Impossible de selectionner l'onglet {tab_name}: {exc}")

    # ------------------------------------------------------------------
    # Icône Windows / Linux
    # ------------------------------------------------------------------
    def _enable_tk_dnd(self):
        """Active le drag-and-drop via tkinterdnd2 sur la racine Tk.

        Comme on hérite de ``ctk.CTk`` (et non de ``TkinterDnD.Tk()``), il
        faut charger le package Tcl ``tkdnd`` à la main puis brancher le
        mixin ``DnDWrapper`` sur notre classe pour que les widgets enfants
        héritent de ``drop_target_register`` / ``dnd_bind``.

        Implémentation : on délègue à ``TkinterDnD._require(self)`` qui
        sélectionne proprement la sous-archi (win-x64, linux-arm64, …) en
        fonction de la plateforme. Échec gracieux si tkinterdnd2 absent.
        """
        try:
            import tkinterdnd2
            from tkinterdnd2 import TkinterDnD
        except ImportError:
            logger.debug("tkinterdnd2 absent — DnD desactive")
            return

        # En mode EXE PyInstaller, tkinterdnd2.__file__ pointe vers le
        # dossier d'extraction _MEIPASS, donc `tkdnd/` y est présent
        # (cf. --add-data dans build.py). Rien de spécial à faire ici.
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            # Brancher les méthodes DnDWrapper sur la classe Tk pour que
            # tous les widgets enfants héritent de drop_target_register /
            # dnd_bind sans modifier individuellement chaque widget.
            wrapper = TkinterDnD.DnDWrapper
            for name in dir(wrapper):
                if name.startswith('_'):
                    continue
                method = getattr(wrapper, name)
                if callable(method):
                    setattr(type(self), name, method)
            logger.info(f"Drag-and-drop active (tkdnd {self.TkdndVersion})")
        except Exception as exc:
            logger.warning(f"DnD non active : {exc}")

    def _install_icon(self):
        """Charge l'icône de l'application (titre, barre des tâches Windows).

        L'icône est cherchée dans plusieurs emplacements :
          1. ``assets/icons/icon.ico`` (chemin officiel actuel)
          2. ``resources/icons/icon.ico`` (compat ancienne arborescence)
          3. ``src/ui/assets/icon.ico`` (fallback embarqué)

        Lorsqu'on tourne depuis l'EXE PyInstaller, ``sys._MEIPASS`` pointe
        sur le dossier temporaire d'extraction où ``assets/`` a été embarqué
        par ``--add-data``. On le scrute en plus de la racine projet.

        Sous Windows on définit ``AppUserModelID`` pour que la barre des
        tâches affiche bien l'icône (sinon l'exe Python générique apparaît).
        """
        here = os.path.dirname(__file__)                # …/src/ui
        project_root = os.path.abspath(os.path.join(here, '..', '..'))

        # Bases possibles : projet (mode dev) + extraction PyInstaller
        bases = [project_root, here]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bases.insert(0, meipass)

        rel_ico = [
            os.path.join('assets', 'icons', 'icon.ico'),
            os.path.join('resources', 'icons', 'icon.ico'),
            os.path.join('assets', 'icon.ico'),
        ]
        rel_png = [
            os.path.join('assets', 'icons', 'icon.png'),
            os.path.join('resources', 'icons', 'icon.png'),
            os.path.join('assets', 'icon.png'),
        ]

        ico_candidates = [os.path.join(b, r) for b in bases for r in rel_ico]
        png_candidates = [os.path.join(b, r) for b in bases for r in rel_png]

        ico_path = next((p for p in ico_candidates if os.path.exists(p)), None)
        png_path = next((p for p in png_candidates if os.path.exists(p)), None)

        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    f"PhotoOrganizer.App.{self.APP_VERSION}"
                )
            except (OSError, AttributeError) as exc:
                # D-04 (audit 2026-05-14) : OSError si Win32 API rejette,
                # AttributeError si ctypes.windll indisponible (Wine, sandbox).
                logger.debug(f"AppUserModelID non applique: {exc}")

        applied = False
        if ico_path:
            try:
                # `default=` propage l'icône à toutes les Toplevel ouvertes
                # ensuite (messagebox, dialogs, etc.).
                self.iconbitmap(default=ico_path)
                self.iconbitmap(ico_path)
                logger.info(f"Icone chargee: {ico_path}")
                applied = True
            except (tk.TclError, OSError) as exc:
                # D-04 (audit 2026-05-14) : TclError = format invalide,
                # OSError = fichier illisible/manquant à l'instant T.
                logger.warning(f"iconbitmap a echoue ({ico_path}): {exc}")

        # iconphoto en complément du .ico : améliore le rendu sur certains
        # gestionnaires de fenêtres et reste utile en fallback Linux/macOS.
        if png_path:
            try:
                from tkinter import PhotoImage
                self._icon_photo = PhotoImage(file=png_path)
                self.iconphoto(True, self._icon_photo)
                if not applied:
                    logger.info(f"Icone PNG chargee: {png_path}")
                applied = True
            except (tk.TclError, OSError) as exc:
                # D-04 (audit 2026-05-14) : idem ci-dessus pour le PNG.
                logger.warning(f"iconphoto a echoue ({png_path}): {exc}")

        if not applied:
            logger.warning(
                "Aucune icone trouvee — chemins testes : %s",
                " ; ".join(ico_candidates + png_candidates),
            )

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


# D-03 (audit 2026-05-14) : la fonction main() locale a été supprimée car
# dupliquée avec src/main.py. Le point d'entrée officiel est `main.py` à la
# racine du projet, qui délègue à `src.main.main`. Si on lance directement
# `python src/ui/app.py` (cas de debug rare), on délègue au vrai entry point.
if __name__ == "__main__":
    from main import main as _entry  # noqa: E402  (root main.py)
    _entry()
