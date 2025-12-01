#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utilitaires pour l'interface utilisateur."""

import os
import tkinter as tk
from tkinter import ttk, filedialog

def create_folder_selection(parent, title, var, command=None):
    """
    Crée un champ de sélection de dossier avec un bouton de navigation.
    
    Args:
        parent: Widget parent
        title (str): Titre du champ
        var (tk.StringVar): Variable pour stocker le chemin du dossier
        command (callable): Fonction à appeler après la sélection
    
    Returns:
        ttk.Frame: Frame contenant les widgets
    """
    frame = ttk.Frame(parent)
    
    # Étiquette
    label = ttk.Label(frame, text=title, width=15)
    label.pack(side=tk.LEFT, padx=5, pady=5)
    
    # Champ de texte
    entry = ttk.Entry(frame, textvariable=var, width=40)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
    
    # Bouton de navigation
    def browse_folder():
        folder = filedialog.askdirectory(title=f"Sélectionner {title}")
        if folder:
            # Normalisation du chemin
            folder = os.path.normpath(folder)
            var.set(folder)
            if command:
                command(folder)
    
    button = ttk.Button(frame, text="Parcourir", command=browse_folder)
    button.pack(side=tk.LEFT, padx=5, pady=5)
    
    return frame



def create_settings_section(parent, title):
    """
    Crée une section encadrée avec un titre.
    
    Args:
        parent: Widget parent
        title (str): Titre de la section
    
    Returns:
        ttk.LabelFrame: Cadre contenant la section
    """
    section = ttk.LabelFrame(parent, text=title)
    section.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    return section

class ScrollableFrame(ttk.Frame):
    """
    Frame défilable pour afficher du contenu qui dépasse la taille de la fenêtre.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Créer un canvas
        self.canvas = tk.Canvas(self, borderwidth=0, background="#ffffff")

        # Créer un scrollbar vertical
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        # Frame qui contiendra le contenu défilable
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configurer le scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Créer une fenêtre dans le canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Empaqueter les widgets
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Lier la molette de la souris
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Gère le défilement avec la molette de la souris."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")