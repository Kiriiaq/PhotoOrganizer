# -*- coding: utf-8 -*-
"""
Design system PhotoOrganizer — constantes UI et factories.

Centralise les valeurs cosmétiques pour assurer une cohérence visuelle
entre les 4 panneaux principaux. Toutes les frames doivent importer ce
module au lieu de hard-coder leurs paddings/couleurs/hauteurs.

Convention couleurs : palette Material Design (tons 800/900) pour assurer
un contraste WCAG AA en thèmes clair et sombre.
"""

from typing import Callable, Optional

import customtkinter as ctk

# ---------------------------------------------------------------------------
# Espacements (unité = pixels)
# ---------------------------------------------------------------------------
PAD_S = 4    # entre widgets d'un même groupe (icône + label, label + entry)
PAD_M = 8    # entre éléments d'un groupe (boutons consécutifs)
PAD_L = 16   # entre groupes logiques (sections d'un panneau)
PAD_XL = 24  # marge externe panneau racine

# ---------------------------------------------------------------------------
# Boutons : hauteur, largeur min
# ---------------------------------------------------------------------------
BTN_H_STD     = 32   # boutons standards (analyser, parcourir, refresh, …)
BTN_H_PRIMARY = 40   # actions principales (Organiser, Rechercher)
BTN_W_MIN     = 100  # largeur minimale par défaut
BTN_W_ICON    = 40   # boutons icône-only carrés

# ---------------------------------------------------------------------------
# Couleurs sémantiques (tuple light, dark)
# ---------------------------------------------------------------------------
# Material Design — verts/rouges/oranges 800/900
COLOR_PRIMARY        = ("#2E7D32", "#1B5E20")  # validation, exécution
COLOR_PRIMARY_HOVER  = ("#1B5E20", "#0F3F0F")
COLOR_DANGER         = ("#C62828", "#8E0000")  # suppression, annulation destructive
COLOR_DANGER_HOVER   = ("#8E0000", "#5C0000")
COLOR_WARNING        = ("#EF6C00", "#B53D00")  # simulation, rollback partiel
COLOR_WARNING_HOVER  = ("#B53D00", "#7A2A00")
COLOR_INFO           = ("#1565C0", "#0D47A1")  # navigation, action neutre
COLOR_INFO_HOVER     = ("#0D47A1", "#063171")
COLOR_DISABLED       = "#9E9E9E"

# Couleurs de fond (cohérence avec app.py existant)
BG_ROOT  = ("#dcdcdc", "#1a1a1a")
BG_FRAME = ("#e8e8e8", "#222222")
BG_INNER = ("#f0f0f0", "#2a2a2a")

# Bordures et accents pour widgets compacts (separator, hint texts)
SEPARATOR_COLOR = ("gray70", "gray30")
HINT_COLOR      = ("gray45", "gray65")
LABEL_MUTED     = ("gray30", "gray70")

# Couleurs spécifiques checkbox / radio (cohérent avec theme blue CTk)
CHECK_FG     = ("#1f6aa5", "#1f6aa5")
CHECK_HOVER  = ("#144870", "#144870")
CHECK_BORDER = ("gray40", "gray60")

# ---------------------------------------------------------------------------
# Polices
# ---------------------------------------------------------------------------
FONT_TITLE_SIZE   = 18  # titres de panneaux (📁 Sélection des dossiers)
FONT_SECTION_SIZE = 14  # titres de sous-sections (Critères, Options, …)
FONT_LABEL_SIZE   = 13  # texte courant des labels et des cases à cocher
FONT_HINT_SIZE    = 11  # textes secondaires en gris (descriptions)
FONT_MONO         = "Consolas"


def font_title() -> ctk.CTkFont:
    return ctk.CTkFont(size=FONT_TITLE_SIZE, weight="bold")


def font_section() -> ctk.CTkFont:
    return ctk.CTkFont(size=FONT_SECTION_SIZE, weight="bold")


def font_label(weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(size=FONT_LABEL_SIZE, weight=weight)


def font_hint() -> ctk.CTkFont:
    return ctk.CTkFont(size=FONT_HINT_SIZE)


def font_mono(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_MONO, size=size)


# ---------------------------------------------------------------------------
# Factories — créent des widgets pré-configurés selon le design system
# ---------------------------------------------------------------------------
def primary_button(
    parent,
    text: str,
    command: Optional[Callable] = None,
    **kw,
) -> ctk.CTkButton:
    """Bouton d'action principale (validation, exécution).

    Hauteur 40, gras, couleur verte sémantique.
    """
    defaults = dict(
        text=text,
        command=command,
        height=BTN_H_PRIMARY,
        fg_color=COLOR_PRIMARY,
        hover_color=COLOR_PRIMARY_HOVER,
        font=font_label(weight="bold"),
    )
    defaults.update(kw)
    return ctk.CTkButton(parent, **defaults)


def danger_button(
    parent,
    text: str,
    command: Optional[Callable] = None,
    **kw,
) -> ctk.CTkButton:
    """Bouton destructeur (suppression, annulation, effacer).

    Hauteur 32, couleur rouge sémantique.
    """
    defaults = dict(
        text=text,
        command=command,
        height=BTN_H_STD,
        fg_color=COLOR_DANGER,
        hover_color=COLOR_DANGER_HOVER,
        font=font_label(),
    )
    defaults.update(kw)
    return ctk.CTkButton(parent, **defaults)


def warning_button(
    parent,
    text: str,
    command: Optional[Callable] = None,
    **kw,
) -> ctk.CTkButton:
    """Bouton attention (simulation, rollback total, réinitialiser).

    Hauteur 32, couleur orange sémantique.
    """
    defaults = dict(
        text=text,
        command=command,
        height=BTN_H_STD,
        fg_color=COLOR_WARNING,
        hover_color=COLOR_WARNING_HOVER,
        font=font_label(),
    )
    defaults.update(kw)
    return ctk.CTkButton(parent, **defaults)


def neutral_button(
    parent,
    text: str,
    command: Optional[Callable] = None,
    **kw,
) -> ctk.CTkButton:
    """Bouton neutre / navigation (parcourir, ouvrir, refresh).

    Hauteur 32, couleur thème CTk par défaut (bleu).
    """
    defaults = dict(
        text=text,
        command=command,
        height=BTN_H_STD,
        font=font_label(),
    )
    defaults.update(kw)
    return ctk.CTkButton(parent, **defaults)


def icon_button(
    parent,
    text: str,
    command: Optional[Callable] = None,
    **kw,
) -> ctk.CTkButton:
    """Petit bouton icône-only carré 40×32.

    Pour 📂, 🔄, ⚙️, ☀️, 🌙, ❓ etc.
    """
    defaults = dict(
        text=text,
        command=command,
        height=BTN_H_STD,
        width=BTN_W_ICON,
        font=font_label(),
    )
    defaults.update(kw)
    return ctk.CTkButton(parent, **defaults)


def make_checkbox(parent, **kw) -> ctk.CTkCheckBox:
    """CTkCheckBox avec style design system (bordure 2px, font 13)."""
    defaults = dict(
        font=font_label(),
        fg_color=CHECK_FG,
        hover_color=CHECK_HOVER,
        border_color=CHECK_BORDER,
        border_width=2,
    )
    defaults.update(kw)
    return ctk.CTkCheckBox(parent, **defaults)


def make_radio(parent, **kw) -> ctk.CTkRadioButton:
    """CTkRadioButton style design system (pendant de make_checkbox)."""
    defaults = dict(
        font=font_label(),
        fg_color=CHECK_FG,
        hover_color=CHECK_HOVER,
        border_color=CHECK_BORDER,
        border_width_unchecked=2,
    )
    defaults.update(kw)
    return ctk.CTkRadioButton(parent, **defaults)


def section_separator(parent) -> ctk.CTkFrame:
    """Trait fin gris pour séparer 2 sections logiques d'un panneau."""
    return ctk.CTkFrame(parent, height=2, fg_color=SEPARATOR_COLOR)


# =============================================================================
# Logo de marque pour les modales (audit 2026-05-15)
# =============================================================================
#
# Demande testeur : « Afficher le logo PhotoOrganizer en haut à gauche sur
# toutes les fenêtres (popup clipboard/fichiers détectés, fenêtres
# secondaires, etc.) ».
#
# Ce helper centralise le chargement de l'icône .png (resize 40×40) et la
# pose dans une modale. No-op silencieux si l'image n'est pas trouvée ou
# si Pillow n'est pas dispo — la modale reste fonctionnelle.

import logging as _logging
import os as _os
import sys as _sys
from typing import Optional

_logo_logger = _logging.getLogger(__name__)
_LOGO_CACHE: dict = {}  # taille -> CTkImage (évite de relire/resize 10× par session)


def _find_logo_path() -> Optional[str]:
    """Cherche le PNG du logo dans les emplacements connus (dev + PyInstaller)."""
    here = _os.path.dirname(_os.path.abspath(__file__))
    project_root = _os.path.abspath(_os.path.join(here, '..', '..'))
    bases = [project_root, here]
    meipass = getattr(_sys, '_MEIPASS', None)
    if meipass:
        bases.insert(0, meipass)
    candidates_rel = [
        _os.path.join('assets', 'icons', 'icon.png'),
        _os.path.join('resources', 'icons', 'icon.png'),
        _os.path.join('assets', 'icon.png'),
    ]
    for base in bases:
        for rel in candidates_rel:
            p = _os.path.join(base, rel)
            if _os.path.exists(p):
                return p
    return None


def add_logo_to_modal(
    modal,
    size: int = 40,
    text: Optional[str] = None,
) -> Optional[ctk.CTkLabel]:
    """Ajoute le logo PhotoOrganizer en haut-gauche d'une modale.

    Args:
        modal: ``ctk.CTkToplevel`` cible. Le helper utilise grid(row=0,
            column=0, sticky="nw", padx=PAD_M, pady=PAD_M) — pense à
            décaler tes widgets existants en column>=1 ou à les wrapper.
            Si tu as besoin d'un pack(), passe un sous-frame ici.
        size: Taille en pixels (40 par défaut, recommandé pour modales).
        text: Texte optionnel à coller à droite du logo (titre court).

    Returns:
        Le ``CTkLabel`` créé, ou ``None`` si le logo est introuvable ou
        si l'opération échoue (l'appelant peut continuer sans souci).
    """
    try:
        from PIL import Image
    except ImportError:
        _logo_logger.debug("Pillow absent — logo modale skip")
        return None

    cache_key = size
    if cache_key in _LOGO_CACHE:
        ctk_image = _LOGO_CACHE[cache_key]
    else:
        path = _find_logo_path()
        if not path:
            _logo_logger.debug("Logo PNG introuvable — modales sans logo")
            return None
        try:
            pil_img = Image.open(path).resize((size, size), Image.LANCZOS)
            ctk_image = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=(size, size),
            )
            _LOGO_CACHE[cache_key] = ctk_image
        except (OSError, ValueError) as exc:
            _logo_logger.warning(f"Logo load failed ({path}): {exc}")
            return None

    try:
        label = ctk.CTkLabel(
            modal, image=ctk_image,
            text=f" {text}" if text else "",
            compound="left", anchor="w",
            font=font_label(weight="bold"),
        )
        label.grid(row=0, column=0, sticky="nw", padx=PAD_M, pady=PAD_M)
        return label
    except Exception as exc:
        _logo_logger.debug(f"Logo placement failed : {exc}")
        return None
