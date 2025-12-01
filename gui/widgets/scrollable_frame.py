#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module définissant un widget de cadre défilable (ScrollableFrame).
"""

import tkinter as tk
from tkinter import ttk

class ScrollableFrame(ttk.Frame):
    """
    Un widget de cadre avec des barres de défilement intégrées.
    
    Ce widget permet d'afficher du contenu qui peut être plus grand que l'espace disponible,
    en ajoutant automatiquement des barres de défilement verticales et horizontales si nécessaire.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialise le cadre défilable.
        
        Args:
            parent: Widget parent
            **kwargs: Arguments supplémentaires pour ttk.Frame
        """
        super().__init__(parent, **kwargs)
        
        # Créer un canevas et l'attacher à cette frame
        self.canvas = tk.Canvas(self)
        
        # Créer les barres de défilement
        self.vertical_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.horizontal_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        
        # Configurer le canevas pour utiliser les barres de défilement
        self.canvas.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set
        )
        
        # Placer les widgets avec le gestionnaire d'agencement grid
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.vertical_scrollbar.grid(row=0, column=1, sticky='ns')
        self.horizontal_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configurer la grille pour s'étendre
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Créer le cadre interne pour le contenu
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Ajouter le cadre interne au canevas
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor='nw'
        )
        
        # Configurer les événements pour mettre à jour la zone de défilement
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self._update_scrollregion()
        )
        
        # Configurer le canevas pour s'adapter à la largeur
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Configurer le défilement par molette de souris
        self._bind_mousewheel()
    
    def _update_scrollregion(self):
        """Met à jour la région de défilement du canevas."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """
        Redimensionne la fenêtre interne pour correspondre à la largeur du canevas.
        
        Args:
            event: Événement de configuration
        """
        # Mettre à jour la largeur de la fenêtre pour qu'elle corresponde à la largeur du canevas
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _bind_mousewheel(self):
        """Attache les événements de la molette de souris au canevas."""
        # Use bind() instead of bind_all() to avoid affecting other widgets
        # Défilement vertical
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_windows)  # Windows
        self.canvas.bind("<Button-4>", self._on_mousewheel_linux)  # Linux (haut)
        self.canvas.bind("<Button-5>", self._on_mousewheel_linux)  # Linux (bas)

        # Défilement horizontal (avec Shift)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel_windows)  # Windows
        self.canvas.bind("<Shift-Button-4>", self._on_shift_mousewheel_linux)  # Linux (gauche)
        self.canvas.bind("<Shift-Button-5>", self._on_shift_mousewheel_linux)  # Linux (droite)
    
    def _on_mousewheel_windows(self, event):
        """
        Gère le défilement vertical avec la molette de souris sous Windows.
        
        Args:
            event: Événement de la molette de souris
        """
        if self._is_mouse_over_canvas():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_mousewheel_linux(self, event):
        """
        Gère le défilement vertical avec la molette de souris sous Linux.
        
        Args:
            event: Événement de la molette de souris
        """
        if self._is_mouse_over_canvas():
            if event.num == 4:  # Défilement vers le haut
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Défilement vers le bas
                self.canvas.yview_scroll(1, "units")
    
    def _on_shift_mousewheel_windows(self, event):
        """
        Gère le défilement horizontal avec Shift + molette de souris sous Windows.
        
        Args:
            event: Événement de la molette de souris
        """
        if self._is_mouse_over_canvas():
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_shift_mousewheel_linux(self, event):
        """
        Gère le défilement horizontal avec Shift + molette de souris sous Linux.
        
        Args:
            event: Événement de la molette de souris
        """
        if self._is_mouse_over_canvas():
            if event.num == 4:  # Défilement vers la gauche
                self.canvas.xview_scroll(-1, "units")
            elif event.num == 5:  # Défilement vers la droite
                self.canvas.xview_scroll(1, "units")
    
    def _is_mouse_over_canvas(self):
        """
        Vérifie si le curseur de la souris est au-dessus du canevas.
        
        Returns:
            bool: True si le curseur est au-dessus du canevas, False sinon
        """
        try:
            x, y = self.canvas.winfo_pointerxy()
            widget_under_pointer = self.canvas.winfo_containing(x, y)
            return (widget_under_pointer == self.canvas or 
                   widget_under_pointer is not None and 
                   self.scrollable_frame in widget_under_pointer.winfo_ancestors())
        except:
            return False
    
    def update_scrollregion(self):
        """Met à jour la région de défilement du canevas."""
        self._update_scrollregion()