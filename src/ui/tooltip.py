# -*- coding: utf-8 -*-
"""
Widget Tooltip réutilisable pour CustomTkinter.

Implémentation maison sans dépendance externe (`CTkToolTip` est dispo
mais ajoute du poids et a des bugs avec les frames scrollables). Cette
version utilise un ``ctk.CTkToplevel`` overrideredirect, géré
intégralement via les bindings Tk natifs.

Usage minimal :
    from ui.tooltip import attach_tooltip
    attach_tooltip(my_button, "Lance le scan des doublons.")

Le delay par défaut (600ms) suit la convention OS Windows / GNOME.
La tooltip se positionne sous le curseur, avec décalage anti-dépassement
écran. Elle se ferme automatiquement quand la souris quitte le widget.
"""

import weakref
from typing import Optional, Union

import customtkinter as ctk

# Registre faible des widgets ayant un tooltip — utile aux tests pour
# vérifier qu'un tooltip a été attaché sans avoir à inspecter Tcl bindings
# (les CTk* surchargent bind() et le routent vers des sous-widgets).
_TOOLTIP_REGISTRY: "weakref.WeakSet" = weakref.WeakSet()


def has_tooltip(widget) -> bool:
    """Renvoie True si un tooltip a été attaché à ce widget via attach_tooltip."""
    return widget in _TOOLTIP_REGISTRY

# Couleurs et police par défaut — délibérément discrètes (gris foncé sur
# fond beige clair) pour ne pas distraire de l'IHM principale.
_BG_COLOR    = ("#FFF3D0", "#3a3a3a")
_FG_COLOR    = ("gray10", "#DCE4EE")
_BORDER_COLOR = ("gray60", "gray35")
_FONT_SIZE    = 11
_DELAY_MS     = 600     # délai avant affichage
_WRAP_LENGTH  = 320     # px — wrap automatique au-delà
_MAX_TEXT_LEN = 400     # texte tronqué au-delà (sécurité anti-mégatooltip)


class Tooltip:
    """Tooltip flottante attachable à n'importe quel widget Tk/CTk.

    Cycle de vie :
        Enter → schedule (after _delay) → show
        Leave / ButtonPress → unschedule + hide
    """

    def __init__(
        self,
        widget,
        text: str,
        delay: int = _DELAY_MS,
        wraplength: int = _WRAP_LENGTH,
    ):
        self.widget = widget
        self.text = self._truncate(text)
        self.delay = max(100, delay)
        self.wraplength = wraplength

        self._after_id: Optional[str] = None
        self._toplevel: Optional[ctk.CTkToplevel] = None

        # Bindings standards
        widget.bind("<Enter>",         self._on_enter, add="+")
        widget.bind("<Leave>",         self._on_leave, add="+")
        widget.bind("<ButtonPress>",   self._on_leave, add="+")
        # Si le widget est détruit, garde-fou
        widget.bind("<Destroy>",       self._on_destroy, add="+")

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _truncate(text: str) -> str:
        """Limite la taille du tooltip pour éviter les fenêtres énormes."""
        if not text:
            return ""
        text = str(text).strip()
        if len(text) > _MAX_TEXT_LEN:
            text = text[: _MAX_TEXT_LEN - 1] + "…"
        return text

    def update_text(self, text: str):
        """Permet de mettre à jour dynamiquement le texte du tooltip."""
        self.text = self._truncate(text)
        if self._toplevel is not None:
            for child in self._toplevel.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    child.configure(text=self.text)

    # ---------------------------------------------------------------- events
    def _on_enter(self, _event=None):
        self._unschedule()
        if not self.text:
            return
        try:
            self._after_id = self.widget.after(self.delay, self._show)
        except Exception:
            self._after_id = None

    def _on_leave(self, _event=None):
        self._unschedule()
        self._hide()

    def _on_destroy(self, _event=None):
        self._unschedule()
        self._hide()

    def _unschedule(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    # ---------------------------------------------------------------- show/hide
    def _show(self):
        if self._toplevel is not None:
            return
        if not self.text:
            return
        try:
            tl = ctk.CTkToplevel(self.widget)
            tl.overrideredirect(True)        # pas de barre de titre
            tl.attributes("-topmost", True)
            tl.configure(fg_color=_BG_COLOR)

            label = ctk.CTkLabel(
                tl, text=self.text,
                font=ctk.CTkFont(size=_FONT_SIZE),
                text_color=_FG_COLOR,
                fg_color=_BG_COLOR,
                wraplength=self.wraplength,
                justify="left",
                padx=8, pady=4,
            )
            label.pack()

            # Positionnement sous le curseur, avec clamp aux bords écran
            x, y = self._calc_position(tl)
            tl.geometry(f"+{x}+{y}")
            self._toplevel = tl
        except Exception:
            # Toplevel peut échouer si parent détruit pendant la frame
            self._toplevel = None

    def _calc_position(self, tl):
        """Position de la tooltip : sous le curseur, avec clamp."""
        x = self.widget.winfo_pointerx() + 12
        y = self.widget.winfo_pointery() + 18
        # Clamp pour ne pas sortir de l'écran
        try:
            tl.update_idletasks()
            screen_w = tl.winfo_screenwidth()
            screen_h = tl.winfo_screenheight()
            tip_w = tl.winfo_reqwidth()
            tip_h = tl.winfo_reqheight()
            if x + tip_w > screen_w:
                x = screen_w - tip_w - 4
            if y + tip_h > screen_h:
                y = self.widget.winfo_pointery() - tip_h - 8
        except Exception:
            pass
        return x, y

    def _hide(self):
        if self._toplevel is not None:
            try:
                self._toplevel.destroy()
            except Exception:
                pass
            self._toplevel = None


def attach_tooltip(widget, text: Union[str, None]) -> Optional[Tooltip]:
    """Attache un tooltip à ``widget``. ``text=None``/vide → no-op.

    Retourne l'instance Tooltip pour pouvoir la mettre à jour ensuite via
    ``tooltip.update_text(...)``.
    """
    if not text:
        return None
    tip = Tooltip(widget, text)
    try:
        _TOOLTIP_REGISTRY.add(widget)
    except TypeError:
        # Certains widgets non-hashables / déjà détruits — best-effort
        pass
    return tip
