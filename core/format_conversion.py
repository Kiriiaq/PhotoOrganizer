#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module pour la conversion entre différents formats d'image.
Ce module gère la conversion HEIC, RAW, et d'autres formats spécialisés.
"""

import os
import subprocess
from PIL import Image
import tempfile

class FormatConverter:
    """Classe pour la conversion entre différents formats d'image."""
    
    def __init__(self):
        """Initialise le convertisseur de formats."""
        self.supported_formats = self._detect_supported_formats()
    
    def _detect_supported_formats(self):
        """
        Détecte les formats supportés sur le système.
        
        Returns:
            dict: Dictionnaire des formats supportés et des commandes/bibliothèques associées
        """
        formats = {
            'heic': {
                'supported': False,
                'command': None,
                'library': None
            },
            'raw': {
                'supported': False,
                'command': None,
                'library': None
            }
        }
        
        # Vérifier le support HEIC
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            formats['heic']['supported'] = True
            formats['heic']['library'] = 'pillow_heif'
        except ImportError:
            # Vérifier si libheif est installé
            try:
                result = subprocess.run(['which', 'heif-convert'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    formats['heic']['supported'] = True
                    formats['heic']['command'] = 'heif-convert'
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
        
        # Vérifier le support RAW
        try:
            import rawpy
            formats['raw']['supported'] = True
            formats['raw']['library'] = 'rawpy'
        except ImportError:
            # Vérifier si dcraw est installé
            try:
                result = subprocess.run(['which', 'dcraw'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    formats['raw']['supported'] = True
                    formats['raw']['command'] = 'dcraw'
            except (subprocess.SubprocessError, FileNotFoundError):
                # Vérifier si darktable-cli est installé
                try:
                    result = subprocess.run(['which', 'darktable-cli'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if result.returncode == 0:
                        formats['raw']['supported'] = True
                        formats['raw']['command'] = 'darktable-cli'
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass
        
        return formats
    
    def is_format_supported(self, format_name):
        """
        Vérifie si un format est supporté.
        
        Args:
            format_name (str): Nom du format à vérifier
        
        Returns:
            bool: True si le format est supporté, False sinon
        """
        format_name = format_name.lower()
        return format_name in self.supported_formats and self.supported_formats[format_name]['supported']
    
    def get_supported_formats_info(self):
        """
        Retourne des informations sur les formats supportés.
        
        Returns:
            dict: Informations sur les formats supportés
        """
        return self.supported_formats
    
    def convert_heic_to_jpeg(self, source_path, dest_path=None, quality=95):
        """
        Convertit un fichier HEIC en JPEG.
        
        Args:
            source_path (str): Chemin du fichier HEIC source
            dest_path (str): Chemin du fichier JPEG de destination. Si None, utilise le même nom avec extension .jpg
            quality (int): Qualité JPEG (1-100)
        
        Returns:
            str: Chemin du fichier JPEG créé ou None en cas d'erreur
        """
        if not self.is_format_supported('heic'):
            print("Le format HEIC n'est pas supporté sur ce système")
            return None
        
        # Si aucun chemin de destination n'est spécifié, utiliser le même nom avec extension .jpg
        if dest_path is None:
            dest_path = os.path.splitext(source_path)[0] + '.jpg'
        
        # Créer le répertoire de destination si nécessaire
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        
        try:
            # Utiliser la bibliothèque Python si disponible
            if self.supported_formats['heic']['library'] == 'pillow_heif':
                with Image.open(source_path) as img:
                    img.convert('RGB').save(dest_path, 'JPEG', quality=quality)
                return dest_path
            
            # Utiliser la commande système si disponible
            elif self.supported_formats['heic']['command'] == 'heif-convert':
                command = [
                    'heif-convert',
                    '-q', str(quality),
                    source_path,
                    dest_path
                ]
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    return dest_path
                else:
                    print(f"Erreur lors de la conversion HEIC->JPEG: {result.stderr.decode()}")
                    return None
            
            else:
                print("Aucune méthode de conversion HEIC n'est disponible")
                return None
        
        except Exception as e:
            print(f"Erreur lors de la conversion HEIC->JPEG: {e}")
            return None
    
    def convert_raw_to_jpeg(self, source_path, dest_path=None, quality=95):
        """
        Convertit un fichier RAW en JPEG.
        
        Args:
            source_path (str): Chemin du fichier RAW source
            dest_path (str): Chemin du fichier JPEG de destination. Si None, utilise le même nom avec extension .jpg
            quality (int): Qualité JPEG (1-100)
        
        Returns:
            str: Chemin du fichier JPEG créé ou None en cas d'erreur
        """
        if not self.is_format_supported('raw'):
            print("Le format RAW n'est pas supporté sur ce système")
            return None
        
        # Si aucun chemin de destination n'est spécifié, utiliser le même nom avec extension .jpg
        if dest_path is None:
            dest_path = os.path.splitext(source_path)[0] + '.jpg'
        
        # Créer le répertoire de destination si nécessaire
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        
        try:
            # Utiliser la bibliothèque Python si disponible
            if self.supported_formats['raw']['library'] == 'rawpy':
                import rawpy
                import imageio
                
                with rawpy.imread(source_path) as raw:
                    rgb = raw.postprocess()
                    imageio.imsave(dest_path, rgb, quality=quality/100)
                return dest_path
            
            # Utiliser dcraw si disponible
            elif self.supported_formats['raw']['command'] == 'dcraw':
                # Créer un fichier temporaire pour la sortie PPM
                with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    # Utiliser dcraw pour convertir RAW en PPM
                    command1 = [
                        'dcraw',
                        '-c',           # Sortie sur stdout
                        '-w',           # Utiliser la balance des blancs de l'appareil
                        '-H', '0',      # Pas d'highlight recovery
                        '-o', '1',      # Espace colorimétrique sRGB
                        '-q', '3',      # Interpolation de haute qualité
                        source_path
                    ]
                    
                    with open(tmp_path, 'wb') as f:
                        result = subprocess.run(command1, stdout=f, stderr=subprocess.PIPE)
                    
                    if result.returncode != 0:
                        print(f"Erreur lors de la conversion RAW->PPM: {result.stderr.decode()}")
                        return None
                    
                    # Convertir PPM en JPEG
                    img = Image.open(tmp_path)
                    img.save(dest_path, 'JPEG', quality=quality)
                    
                    return dest_path
                
                finally:
                    # Nettoyer le fichier temporaire
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            
            # Utiliser darktable-cli si disponible
            elif self.supported_formats['raw']['command'] == 'darktable-cli':
                command = [
                    'darktable-cli',
                    source_path,
                    dest_path,
                    '--width', '0',
                    '--height', '0',
                    '--hq', 'true',
                    '--core',
                    '--conf', f'plugins/imageio/format/jpeg/quality={quality}'
                ]
                
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    return dest_path
                else:
                    print(f"Erreur lors de la conversion RAW->JPEG: {result.stderr.decode()}")
                    return None
            
            else:
                print("Aucune méthode de conversion RAW n'est disponible")
                return None
        
        except Exception as e:
            print(f"Erreur lors de la conversion RAW->JPEG: {e}")
            return None
    
def is_heic_file(file_path):
    """
    Vérifie si un fichier est au format HEIC.
    
    Args:
        file_path (str): Chemin du fichier
    
    Returns:
        bool: True si le fichier est au format HEIC, False sinon
    """
    return os.path.splitext(file_path)[1].lower() in ['.heic', '.heif']

def is_raw_file(file_path):
    """
    Vérifie si un fichier est au format RAW.
    
    Args:
        file_path (str): Chemin du fichier
    
    Returns:
        bool: True si le fichier est au format RAW, False sinon
    """
    raw_extensions = ['.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng']
    return os.path.splitext(file_path)[1].lower() in raw_extensions
