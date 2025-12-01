#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modules d'utilitaires pour la gestion d'images.
"""

# utils/file_utils.py
"""Utilitaires pour les opérations sur les fichiers."""

import re
import unicodedata
from datetime import datetime

import os
from typing import Optional
from pathlib import Path

def normalize_path(path: Optional[str]) -> Optional[str]:
    """
    Normalise un chemin de fichier pour éviter les problèmes de séparateurs mixtes.
    
    Args:
        path: Chemin à normaliser
        
    Returns:
        Chemin normalisé ou None si le chemin d'entrée est None
    """
    return os.path.normpath(path) if path else path

def ensure_dir_exists(directory: str) -> str:
    """
    S'assure qu'un répertoire existe, le crée si nécessaire.
    
    Args:
        directory: Chemin du répertoire à vérifier/créer
        
    Returns:
        Le chemin normalisé du répertoire
    """
    directory = normalize_path(directory)
    os.makedirs(directory, exist_ok=True)
    return directory

def get_file_info(file_path):
    """
    Récupère les informations de base d'un fichier.
    
    Args:
        file_path (str): Chemin du fichier
    
    Returns:
        dict: Informations du fichier
    """
    if not os.path.exists(file_path):
        return None
    
    stat_info = os.stat(file_path)
    
    return {
        'path': file_path,
        'name': os.path.basename(file_path),
        'size': stat_info.st_size,
        'created': datetime.fromtimestamp(stat_info.st_ctime),
        'modified': datetime.fromtimestamp(stat_info.st_mtime),
        'accessed': datetime.fromtimestamp(stat_info.st_atime),
        'extension': os.path.splitext(file_path)[1].lower()
    }

def normalize_filename(filename):
    """
    Normalise un nom de fichier (supprime les caractères spéciaux, accents, etc.).
    
    Args:
        filename (str): Nom de fichier à normaliser
    
    Returns:
        str: Nom de fichier normalisé
    """
    # Supprimer l'extension
    base, ext = os.path.splitext(filename)
    
    # Remplacer les caractères spéciaux par des underscores
    base = re.sub(r'[^\w\s-]', '_', unicodedata.normalize('NFKD', base).encode('ASCII', 'ignore').decode('ASCII'))
    
    # Remplacer les espaces par des underscores
    base = re.sub(r'[\s]+', '_', base)
    
    # Supprimer les underscores en début et fin
    base = base.strip('_')
    
    # Remettre l'extension
    return base + ext

def get_files_by_extension(directory, extensions, recursive=True):
    """
    Récupère tous les fichiers d'un répertoire ayant une extension spécifique.
    
    Args:
        directory (str): Répertoire à explorer
        extensions (list): Liste des extensions à rechercher (ex: ['.jpg', '.png'])
        recursive (bool): Parcourir les sous-répertoires
    
    Returns:
        list: Liste des chemins des fichiers correspondants
    """
    files = []
    
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if any(filename.lower().endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, filename))
    else:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath) and any(filename.lower().endswith(ext) for ext in extensions):
                files.append(filepath)
    
    return files