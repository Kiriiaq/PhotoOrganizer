#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module principal pour l'application PhotoManager.
Point d'entrée pour démarrer l'application de gestion d'images.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
import logging
from pathlib import Path

# Configuration du logging
def setup_logging():
    """Configure le système de journalisation."""
    log_dir = Path.home() / ".photomanager" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "photomanager.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Réduire le niveau de verbosité des logs des bibliothèques tierces
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    
    return logging.getLogger("photomanager")

def check_dependencies():
    """
    Vérifie que toutes les dépendances requises sont installées.
    
    Returns:
        bool: True si toutes les dépendances sont présentes, False sinon
    """
    # Mapping des noms de packages pip vers les noms de modules à importer
    module_mapping = {
        "PIL": "PIL",
        "opencv-python": "cv2",
        "tkinter": "tkinter"
    }
    
    missing_modules = []
    
    for package, module in module_mapping.items():
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(package)
    
    if missing_modules:
        print("Les modules suivants sont requis mais n'ont pas été trouvés :")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nVeuillez les installer avec :")
        print(f"pip install {' '.join(missing_modules)}")
        return False
    
    return True

def main():
    """Fonction principale qui initialise et démarre l'application."""
    # Configurer le logging
    logger = setup_logging()
    logger.info("Démarrage de l'application PhotoManager")
    
    # Vérifier les dépendances
    if not check_dependencies():
        logger.error("Des dépendances sont manquantes. L'application va se terminer.")
        sys.exit(1)
    
    # Créer la fenêtre principale Tkinter
    root = tk.Tk()

    try:
        # Add project root to path if needed
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # Importer l'application après avoir vérifié les dépendances
        from gui.app import PhotoManagerApp

        # Initialiser l'application
        app = PhotoManagerApp(root)
        
        # Configuration générale de la fenêtre
        root.title("PhotoManager")
        root.geometry("1450x800")
        root.minsize(800, 600)
        
        # Configurer l'icône si disponible
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        
        # Démarrer la boucle principale
        logger.info("Interface utilisateur initialisée. Démarrage de la boucle d'événements.")
        root.mainloop()
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'initialisation de l'application: {e}")
        # Afficher une boîte de dialogue d'erreur
        messagebox.showerror(  # Use messagebox directly, not tk.messagebox
            "Erreur de démarrage",
            f"Une erreur s'est produite lors du démarrage de l'application:\n\n{str(e)}\n\n"
            "Veuillez consulter le fichier journal pour plus de détails."
        )
        sys.exit(1)
    
    logger.info("Fermeture de l'application PhotoManager")

if __name__ == "__main__":
    main()