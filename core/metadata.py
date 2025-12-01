#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module pour l'extraction et le traitement des métadonnées d'images.

Ce module fournit des fonctions pour extraire et traiter les métadonnées à partir de différents
formats d'images, y compris JPEG, HEIC/HEIF, et formats RAW. Il permet d'extraire des informations
telles que la date de prise de vue, les coordonnées GPS, les informations sur l'appareil photo,
et les dimensions de l'image.
"""

import math
import os
import re
import json
import subprocess
import platform
import sys
from datetime import datetime
from typing import Dict, Tuple, Optional, Any, List
from PIL import Image, ExifTags
import exifread

# Add project root to path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import configuration (charge automatiquement .env)
try:
    import config
except ImportError:
    pass

# Import from utils
from utils.file_utils import ensure_dir_exists, normalize_path

# Configuration du logging
def setup_logging(log_file="metadata_processing.log"):
    """
    Configure la journalisation des messages dans un fichier.
    
    Args:
        log_file: Nom du fichier de log
    """
    # Créer le dossier logs s'il n'existe pas
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    ensure_dir_exists(log_dir)
    
    # Chemin complet du fichier de log
    log_path = os.path.join(log_dir, log_file)
    
    # Ouvrir le fichier en mode append
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"Session de log démarrée le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*50}\n")
    
    return log_path

def log_message(message: str, log_file: str = "metadata_processing.log"):
    """
    Écrit un message dans le fichier de log.
    
    Args:
        message: Message à logger
        log_file: Nom du fichier de log
    """
    # Créer le dossier logs s'il n'existe pas
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    ensure_dir_exists(log_dir)
    
    # Chemin complet du fichier de log
    log_path = os.path.join(log_dir, log_file)
    
    # Écrire le message avec un timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")
    
    # Afficher aussi dans la console
    print(message)

# ============================================================================
# CONSTANTES ET CONFIGURATION
# ============================================================================

# Extensions de fichiers reconnues
IMAGE_EXTENSIONS = {
    'standard': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.psd', '.jfif', '.jp2', '.avif'],
    'heic': ['.heic', '.heif'],
    'raw': ['.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng', '.3fr', '.raf', '.pef', '.srw', '.sr2', '.x3f', '.mef', '.iiq', '.rwl'],
    'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.3gp', '.m4v', '.mpg', '.mpeg', '.mts', '.ts', '.vob']
}

# Formats de date EXIF reconnus
EXIF_DATE_FORMATS = ['%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']

# Champs de date EXIF à rechercher par ordre de priorité
DATE_FIELDS = ['DateTimeOriginal', 'DateTime', 'DateTimeDigitized']

# Système d'exploitation actuel
SYSTEM = platform.system()


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def _create_basic_metadata(file_path: str) -> Dict[str, Any]:
    """
    Crée un dictionnaire de métadonnées de base à partir des attributs du fichier.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        Dictionnaire contenant les attributs de base du fichier
    """
    try:
        return {
            'FileName': os.path.basename(file_path),
            'FileSize': os.path.getsize(file_path),
            'FileDateTime': os.path.getmtime(file_path),
            'Directory': os.path.dirname(file_path),
            'FileModifyDate': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y:%m:%d %H:%M:%S")
        }
    except Exception as e:
        print(f"Erreur lors de la création des métadonnées de base pour {file_path}: {e}")
        return {'FileName': os.path.basename(file_path)}


# ============================================================================
# EXTRACTION WINDOWS-SPÉCIFIQUE AVEC WMIC
# ============================================================================

def get_windows_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Utilise WMIC sous Windows pour extraire les métadonnées du fichier.
    
    Args:
        file_path: Chemin vers le fichier
        
    Returns:
        Dictionnaire contenant les métadonnées du fichier ou un dictionnaire vide si l'extraction échoue
    """
    if SYSTEM != 'Windows':
        return {}
        
    try:
        # Préparer le chemin pour la commande WMIC
        safe_path = file_path.replace('/', '\\')
        safe_path = safe_path.replace('\\', '\\\\')
        
        # Exécuter la commande WMIC
        cmd = f'cmd.exe /c wmic datafile "{safe_path}" list full'
        output = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        ).communicate()[0]
        
        # Décoder la sortie
        output_utf = output.decode('utf-8', errors='ignore')
        
        # Analyser la sortie
        metadata = {}
        for line in output_utf.splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                metadata[key.strip()] = value.strip()
        
        # Convertir les dates de création et de modification en objet datetime
        if 'CreationDate' in metadata:
            creation_date = parse_windows_wmic_date(metadata['CreationDate'])
            if creation_date:
                metadata['CreationDateTime'] = creation_date
                
        if 'LastModified' in metadata:
            last_modified = parse_windows_wmic_date(metadata['LastModified'])
            if last_modified:
                metadata['LastModifiedDateTime'] = last_modified
        
        return metadata
    except Exception as e:
        print(f"Erreur lors de l'extraction des métadonnées WMIC de {file_path}: {e}")
        return {}

def get_windows_photo_dates(file_path: str) -> List[datetime]:
    """
    Extrait toutes les dates d'un fichier photo sous Windows en utilisant WMIC.
    
    Args:
        file_path: Chemin vers le fichier photo
        
    Returns:
        Liste de dates triées extraites du fichier
    """
    if SYSTEM != 'Windows':
        return []
        
    try:
        # Préparer le chemin pour la commande WMIC
        safe_path = file_path.replace('/', '\\')
        safe_path = safe_path.replace('\\', '\\\\')
        
        # Exécuter la commande WMIC
        cmd = f'cmd.exe /c wmic datafile "{safe_path}" list full'
        output = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        ).communicate()[0]
        
        # Décoder la sortie
        output_utf = output.decode('utf-8', errors='ignore')
        
        # Rechercher toutes les dates dans la sortie
        dates = []
        date_pattern = re.compile(r'(20\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)\.(\d*)')
        
        for match in date_pattern.finditer(output_utf):
            try:
                date = datetime(
                    year=int(match.group(1)),
                    month=int(match.group(2)),
                    day=int(match.group(3)),
                    hour=int(match.group(4)),
                    minute=int(match.group(5)),
                    second=int(match.group(6)),
                    microsecond=int(match.group(7)) if match.group(7) else 0,
                )
                dates.append(date)
            except (ValueError, IndexError):
                pass
        
        return sorted(dates)
    except Exception as e:
        print(f"Erreur lors de l'extraction des dates WMIC de {file_path}: {e}")
        return []

def parse_windows_wmic_date(date_str: str) -> Optional[datetime]:
    """
    Analyse une chaîne de date au format WMIC et la convertit en objet datetime.
    
    Args:
        date_str: Chaîne de date au format WMIC (ex: "20230817080632.333836+120")
        
    Returns:
        Objet datetime ou None si l'analyse échoue
    """
    try:
        # Format typique: AAAAMMJJHHMMSS.microseconds+timezone
        match = re.match(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.(\d+)(?:\+\d+)?', date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            second = int(match.group(6))
            microsecond = int(match.group(7)[:6].ljust(6, '0')) if match.group(7) else 0
            
            return datetime(year, month, day, hour, minute, second, microsecond)
    except (ValueError, IndexError):
        pass
    
    return None


# ============================================================================
# EXTRACTION DES MÉTADONNÉES
# ============================================================================

def get_heif_exif_data(file_path: str) -> Dict[str, Any]:
    """
    Extrait les données EXIF des fichiers HEIC/HEIF avec gestion des alternatives.
    
    Args:
        file_path: Chemin vers le fichier HEIC/HEIF
        
    Returns:
        Dictionnaire contenant les données EXIF
    """
    # Initialiser le fichier de log spécifique pour HEIC/HEIF
    log_file = "heic_heif_processing.log"
    log_path = setup_logging(log_file)
    log_message(f"\n=== DÉBUT GET_HEIF_EXIF_DATA pour: {file_path} ===", log_file)
    
    # Vérifier que file_path est bien une chaîne de caractères
    if not isinstance(file_path, (str, bytes, os.PathLike)):
        log_message(f"ERREUR: Type de chemin de fichier invalide: {type(file_path)}", log_file)
        return {}
    
    # Normaliser le chemin du fichier
    file_path = str(file_path)
    log_message(f"Chemin normalisé: {file_path}", log_file)
    
    # Vérifier que le fichier existe
    if not os.path.exists(file_path):
        log_message(f"ERREUR: Le fichier n'existe pas: {file_path}", log_file)
        return {}
    
    exif_data = {}
    
    # Méthode 1: Utiliser pillow_heif (recommandé pour Windows)
    try:
        log_message("Tentative d'extraction avec pillow_heif...", log_file)
        from pillow_heif import register_heif_opener
        register_heif_opener()
        
        with Image.open(file_path) as img:
            # Extraire les données EXIF via getexif()
            if hasattr(img, 'getexif') and callable(getattr(img, 'getexif')):
                exif = img.getexif()
                if exif:
                    log_message("Données EXIF trouvées avec pillow_heif", log_file)
                    # Récupérer les données standard
                    for tag, value in exif.items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        exif_data[tag_name] = value
                        log_message(f"Tag EXIF extrait: {tag_name} = {value}", log_file)
                    
                    # Récupérer spécifiquement les données GPS
                    if hasattr(exif, 'get_ifd') and callable(getattr(exif, 'get_ifd')):
                        gps_ifd = exif.get_ifd(0x8825)
                        if gps_ifd:
                            exif_data['GPSInfo'] = gps_ifd
                            log_message("Données GPS trouvées dans les métadonnées", log_file)
            
            # Ajouter les dimensions de l'image
            exif_data['ImageWidth'] = img.width
            exif_data['ImageHeight'] = img.height
            log_message(f"Dimensions de l'image: {img.width}x{img.height}", log_file)
            
            log_message("Extraction réussie avec pillow_heif", log_file)
            return exif_data
    except ImportError:
        log_message("AVERTISSEMENT: pillow_heif n'est pas installé. Essai des méthodes alternatives.", log_file)
    except Exception as e:
        log_message(f"ERREUR avec pillow_heif: {str(e)}", log_file)
    
    # Méthode 2: Utiliser ExifTool (solution externe)
    try:
        log_message("Tentative d'extraction avec ExifTool...", log_file)
        import subprocess
        import json
        
        # Vérifier si ExifTool est disponible
        try:
            subprocess.run(['exiftool', '-ver'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            log_message("ExifTool est disponible", log_file)
        except (subprocess.SubprocessError, FileNotFoundError):
            log_message("AVERTISSEMENT: ExifTool n'est pas disponible.", log_file)
            return exif_data
        
        # Extraire les métadonnées avec ExifTool
        result = subprocess.run(
            ['exiftool', '-j', '-g', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                if data and isinstance(data, list) and data[0]:
                    log_message("Données EXIF trouvées avec ExifTool", log_file)
                    # Extraire les informations EXIF
                    exif_section = data[0].get('EXIF', {})
                    for key, value in exif_section.items():
                        exif_data[key.replace(' ', '')] = value
                        log_message(f"Tag EXIF extrait: {key} = {value}", log_file)
                    
                    # Extraire les informations GPS
                    gps_section = data[0].get('GPS', {})
                    if gps_section:
                        exif_data['GPSInfo'] = gps_section
                        log_message("Données GPS trouvées dans les métadonnées", log_file)
                    
                    # Extraire les dimensions
                    if 'File' in data[0]:
                        if 'ImageWidth' in data[0]['File']:
                            exif_data['ImageWidth'] = data[0]['File']['ImageWidth']
                        if 'ImageHeight' in data[0]['File']:
                            exif_data['ImageHeight'] = data[0]['File']['ImageHeight']
                        log_message(f"Dimensions de l'image: {exif_data.get('ImageWidth')}x{exif_data.get('ImageHeight')}", log_file)
                    
                    log_message("Extraction réussie avec ExifTool", log_file)
                    return exif_data
            except json.JSONDecodeError:
                log_message("ERREUR: Impossible de décoder la sortie JSON d'ExifTool", log_file)
    except Exception as e:
        log_message(f"ERREUR avec ExifTool: {str(e)}", log_file)
    
    # Méthode 3: Extraction des données EXIF de base à partir du fichier
    log_message("Tentative d'extraction des métadonnées de base...", log_file)
    basic_exif = _create_basic_metadata(file_path)
    
    # Essayer d'extraire la date du nom de fichier
    filename = os.path.basename(file_path)
    date_from_filename = extract_image_date(filename, fallback_to_file_date=False)
    if date_from_filename:
        basic_exif['DateTimeOriginal'] = date_from_filename.strftime("%Y:%m:%d %H:%M:%S")
        log_message(f"Date extraite du nom de fichier: {date_from_filename}", log_file)
    
    log_message("=== FIN GET_HEIF_EXIF_DATA ===", log_file)
    return basic_exif

def _try_exiftool(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Tente d'extraire les métadonnées avec ExifTool.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        Dictionnaire contenant les métadonnées ou None si l'extraction échoue
    """
    try:
        # Essayer d'abord la méthode PyExifTool si disponible
        try:
            import exiftool 
            
            # Vérifier si le chemin ExifTool est défini
            exiftool_path = os.environ.get('EXIFTOOL_PATH')
            if exiftool_path and os.path.exists(exiftool_path):
                with exiftool.ExifToolHelper(executable=exiftool_path) as et:
                    metadata_list = et.get_metadata([file_path])
                    if metadata_list and len(metadata_list) > 0:
                        return metadata_list[0]
            else:
                # Essayer sans chemin spécifique
                with exiftool.ExifToolHelper() as et:
                    metadata_list = et.get_metadata([file_path])
                    if metadata_list and len(metadata_list) > 0:
                        return metadata_list[0]
        except (ImportError, Exception):
            pass
        
        # Méthode alternative: appeler directement ExifTool via subprocess
        try:
            # Chercher ExifTool (ordre de priorité)
            exiftool_exe = None
            try:
                from config import check_exiftool
                exiftool_exe = check_exiftool()
            except:
                pass

            # Si pas trouvé via config, essayer directement
            if not exiftool_exe:
                exiftool_exe = 'exiftool'

            # Vérifier si ExifTool est disponible
            result = subprocess.run(
                [exiftool_exe, '-ver'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if result.returncode == 0:
                # Exécuter ExifTool pour extraire les métadonnées
                result = subprocess.run(
                    [exiftool_exe, '-j', '-charset', 'UTF8', file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                if result.returncode == 0 and result.stdout:
                    try:
                        data = json.loads(result.stdout)
                        if data and isinstance(data, list) and data[0]:
                            # Convertir les clés ExifTool en format standard
                            return {k.replace(' ', ''): v for k, v in data[0].items()}
                    except json.JSONDecodeError:
                        pass
        except (FileNotFoundError, Exception):
            pass
            
    except Exception as e:
        print(f"Erreur lors de l'utilisation d'ExifTool: {e}")
    
    return None


def read_exif_with_exifread(image_path: str) -> Dict[str, Any]:
    """
    Lit les données EXIF avec la bibliothèque exifread.
    
    Args:
        image_path: Chemin de l'image
        
    Returns:
        Dictionnaire contenant les tags EXIF
    """
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
        # Convertir les objets IfdTag en valeurs utilisables
        result = {}
        for tag, value in tags.items():
            key = tag.split(' ', 1)[-1] if ' ' in tag else tag
            result[key] = str(value)
            
        return result
    except Exception as e:
        print(f"Erreur lors de la lecture des données EXIF avec exifread: {e}")
        return {}


def get_exif_data(file_path: str) -> Dict[str, Any]:
    """
    Extrait les métadonnées des fichiers image et vidéo, prenant en charge divers formats.
    
    Args:
        file_path: Chemin vers le fichier
        
    Returns:
        Dictionnaire contenant les données EXIF ou métadonnées de base si l'extraction échoue
    """
    log_message(f"\n=== Début de l'extraction des métadonnées pour: {file_path} ===")
    
    # Vérification stricte du type de file_path
    if not isinstance(file_path, (str, bytes, os.PathLike)):
        log_message(f"ERREUR: Type de chemin de fichier invalide dans get_exif_data: {type(file_path)}")
        log_message(f"Valeur reçue: {file_path}")
        return {}
    
    # Normaliser le chemin et vérifier l'existence du fichier
    file_path = normalize_path(file_path)
    if not os.path.exists(file_path):
        log_message(f"Le fichier n'existe pas: {file_path}")
        return {}
    
    # Déterminer le type de fichier par extension
    ext = os.path.splitext(file_path)[1].lower()
    log_message(f"Extension du fichier: {ext}")
    
    # TRAITEMENT SPÉCIFIQUE POUR LES FICHIERS JPG/JPEG
    if ext.lower() in ['.jpg', '.jpeg', '.jfif', '.jpe']:
        log_message("Traitement d'un fichier JPEG avec méthode optimisée")
        try:
            # Méthode 1: Extraction rapide avec exifread (optimisée pour les JPG)
            log_message("Tentative d'extraction avec exifread...")
            with open(file_path, 'rb') as file:
                # Extraire toutes les métadonnées EXIF sans limitation
                tags = exifread.process_file(file, details=False)
                
                if tags:
                    log_message(f"Nombre de tags EXIF trouvés: {len(tags)}")
                    # Convertir les objets IfdTag en un dictionnaire utilisable
                    exif_data = {}
                    
                    for tag, value in tags.items():
                        # Nettoyer les noms de tags (retirer les préfixes EXIF, Image, etc.)
                        cleaned_tag = tag.split(' ', 1)[-1] if ' ' in tag else tag
                        # Convertir les valeurs en chaînes lisibles
                        exif_data[cleaned_tag] = str(value)
                    
                    # Afficher les données EXIF importantes
                    log_message("\nDonnées EXIF importantes:")
                    important_tags = [
                        'Make', 'Model', 'DateTimeOriginal', 'DateTime', 'DateTimeDigitized',
                        'ExposureTime', 'FNumber', 'ISOSpeedRatings', 'FocalLength',
                        'ExposureProgram', 'MeteringMode', 'Flash', 'WhiteBalance',
                        'GPSLatitude', 'GPSLongitude', 'GPSAltitude'
                    ]
                    
                    for tag in important_tags:
                        if tag in exif_data:
                            log_message(f"  {tag}: {exif_data[tag]}")
                    
                    # Vérifier si la date de prise est présente (souvent clé importante)
                    if 'DateTime' in exif_data:
                        log_message(f"Date de prise trouvée: {exif_data['DateTimeOriginal']}")
                    
                    # Ajouter des métadonnées de base
                    basic_meta = _create_basic_metadata(file_path)
                    for key, value in basic_meta.items():
                        if key not in exif_data:
                            exif_data[key] = value
                    
                    log_message("\nMétadonnées complètes:")
                    log_message(json.dumps(exif_data, indent=2, ensure_ascii=False))
                    
                    log_message("Métadonnées JPEG extraites avec succès via méthode optimisée")
                    return exif_data
            
            # Méthode 2: Extraction via Pillow si exifread échoue
            log_message("Tentative d'extraction via Pillow...")
            with Image.open(file_path) as img:
                if hasattr(img, '_getexif') and callable(getattr(img, '_getexif')):
                    exif = img._getexif()
                    if exif:
                        log_message(f"Nombre de tags EXIF trouvés via Pillow: {len(exif)}")
                        exif_data = {}
                        for tag, value in exif.items():
                            tag_name = ExifTags.TAGS.get(tag, tag)
                            
                            # Traitement des valeurs binaires
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8')
                                except UnicodeDecodeError:
                                    try:
                                        value = value.decode('latin-1')
                                    except:
                                        pass
                            
                            exif_data[tag_name] = value
                        
                        # Traitement spécifique pour les données GPS
                        if 0x8825 in exif:
                            log_message("Données GPS trouvées dans les métadonnées")
                            gps_info = exif.get(0x8825, {})
                            if gps_info:
                                gps_data = {}
                                for gps_tag, gps_value in gps_info.items():
                                    gps_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                                    gps_data[gps_tag_name] = gps_value
                                exif_data['GPSInfo'] = gps_data
                        
                        log_message("Métadonnées JPEG extraites avec succès via Pillow")
                        return exif_data
        
            # Méthode 3: ExifTool (option avancée si les autres méthodes échouent)
            log_message("Tentative d'extraction via ExifTool...")
            exiftool_data = _try_exiftool(file_path)
            if exiftool_data:
                log_message("Métadonnées JPEG extraites avec succès via ExifTool")
                return exiftool_data
        except Exception as e:
            log_message(f"Erreur lors de l'extraction JPEG: {e}")
        
        # Si toutes les méthodes échouent, utiliser les métadonnées de base
        log_message("Utilisation des métadonnées de base pour JPEG")
        return _create_basic_metadata(file_path)
    
    # NOUVELLE LOGIQUE: Traitement spécifique pour les fichiers vidéo
    if ext in IMAGE_EXTENSIONS['video']:
        log_message("Traitement d'un fichier vidéo")
        # Créer des métadonnées de base pour le fichier vidéo
        video_metadata = _create_basic_metadata(file_path)
        log_message(f"Métadonnées de base extraites: {json.dumps(video_metadata, indent=2, ensure_ascii=False)}")
        
        # Détection spécifique pour les fichiers Google Pixel
        filename = os.path.basename(file_path)
        if filename.startswith('PXL_'):
            log_message("Fichier vidéo détecté comme provenant d'un Google Pixel")
            video_metadata['Make'] = 'Google'
            video_metadata['Model'] = 'Pixel'
            video_metadata['CameraType'] = 'Google Pixel'
            log_message(f"Métadonnées Google Pixel ajoutées: {json.dumps({'Make': 'Google', 'Model': 'Pixel', 'CameraType': 'Google Pixel'}, indent=2, ensure_ascii=False)}")
        
        # Essayer d'extraire la date du nom de fichier
        date_from_filename = extract_image_date(filename, fallback_to_file_date=False)
        
        if date_from_filename:
            video_metadata['DateTimeOriginal'] = date_from_filename.strftime("%Y:%m:%d %H:%M:%S")
            video_metadata['FileSourceFromName'] = True
            log_message(f"Date extraite du nom de fichier: {date_from_filename}")
        
        # Ajouter des informations vidéo génériques
        video_metadata['MediaType'] = 'Video'
        
        # Si sous Windows, essayer d'extraire des métadonnées Windows supplémentaires
        if SYSTEM == 'Windows':
            try:
                wmic_data = get_windows_file_metadata(file_path)
                if wmic_data:
                    for key, value in wmic_data.items():
                        video_metadata[key] = value
                    log_message("Métadonnées Windows extraites avec succès")
                    log_message(f"Métadonnées Windows: {json.dumps(wmic_data, indent=2, ensure_ascii=False)}")
                
                # Essayer d'obtenir les dates Windows
                windows_dates = get_windows_photo_dates(file_path)
                if windows_dates and not date_from_filename:
                    video_metadata['DateTimeOriginal'] = windows_dates[0].strftime("%Y:%m:%d %H:%M:%S")
                    log_message(f"Date extraite des métadonnées Windows: {windows_dates[0]}")
            except Exception as e:
                log_message(f"Erreur lors de l'extraction des métadonnées Windows pour {file_path}: {e}")
        
        log_message("=== Fin de l'extraction des métadonnées vidéo ===")
        log_message(f"Métadonnées finales extraites: {json.dumps(video_metadata, indent=2, ensure_ascii=False)}\n")
        return video_metadata
    
    # Traitement spécifique pour les fichiers HEIC/HEIF
    elif ext in IMAGE_EXTENSIONS['heic']:
        log_message("Traitement d'un fichier HEIC/HEIF")
        return get_heif_exif_data(file_path)
    
    # Traitement spécifique pour les fichiers RAW
    elif ext in IMAGE_EXTENSIONS['raw']:
        log_message("Traitement d'un fichier RAW")
        try:
            # Utiliser exifread pour les fichiers RAW
            log_message("Tentative d'extraction avec exifread...")
            exif_data = read_exif_with_exifread(file_path)
            if exif_data:
                log_message("Métadonnées extraites avec succès via exifread")
                return exif_data
            
            # Si exifread échoue, essayer ExifTool
            log_message("Tentative d'extraction avec ExifTool...")
            exiftool_data = _try_exiftool(file_path)
            if exiftool_data:
                log_message("Métadonnées extraites avec succès via ExifTool")
                return exiftool_data
            
            # Si sous Windows, essayer WMIC
            if SYSTEM == 'Windows':
                log_message("Tentative d'extraction avec WMIC...")
                wmic_data = get_windows_file_metadata(file_path)
                if wmic_data:
                    log_message("Métadonnées extraites avec succès via WMIC")
                    return wmic_data
                    
        except Exception as e:
            log_message(f"Erreur lors de l'extraction des métadonnées RAW: {e}")
        
        # Retourner des métadonnées de base si l'extraction échoue
        log_message("Utilisation des métadonnées de base pour le fichier RAW")
        return _create_basic_metadata(file_path)
    
    # Traitement pour les formats standard
    else:
        log_message("Traitement d'un fichier image standard")
        try:
            with Image.open(file_path) as img:
                log_message(f"Format de l'image: {img.format}")
                # Méthode principale: _getexif()
                if hasattr(img, '_getexif'):
                    log_message("Tentative d'extraction via _getexif()...")
                    exif_data = img._getexif()
                    if exif_data:
                        log_message("Métadonnées EXIF trouvées via _getexif()")
                        return {
                            ExifTags.TAGS.get(tag, tag): str(value) if isinstance(value, bytes) else value
                            for tag, value in exif_data.items()
                        }
                
                # Extraire des informations de base
                log_message("Extraction des informations de base de l'image...")
                basic_info = {
                    'ImageWidth': img.width,
                    'ImageHeight': img.height,
                    'Format': img.format
                }
                log_message(f"Dimensions: {img.width}x{img.height}")
                
                # Inclure les données img.info
                if hasattr(img, 'info'):
                    for key, value in img.info.items():
                        if not isinstance(value, bytes):
                            basic_info[key] = value
                    log_message("Informations supplémentaires extraites de img.info")
                
                if basic_info:
                    return basic_info
            
            # Si Pillow échoue, essayer exifread
            log_message("Tentative d'extraction avec exifread...")
            exif_data = read_exif_with_exifread(file_path)
            if exif_data:
                log_message("Métadonnées extraites avec succès via exifread")
                return exif_data
                
            # Si exifread échoue, essayer ExifTool
            log_message("Tentative d'extraction avec ExifTool...")
            exiftool_data = _try_exiftool(file_path)
            if exiftool_data:
                log_message("Métadonnées extraites avec succès via ExifTool")
                return exiftool_data
            
            # Si sous Windows, essayer WMIC comme dernier recours
            if SYSTEM == 'Windows':
                log_message("Tentative d'extraction avec WMIC...")
                wmic_data = get_windows_file_metadata(file_path)
                if wmic_data:
                    log_message("Métadonnées extraites avec succès via WMIC")
                    return wmic_data
                
        except Exception as e:
            log_message(f"Erreur lors de l'extraction des données EXIF: {e}")
        
        # Retourner des métadonnées de base si toutes les méthodes échouent
        log_message("Utilisation des métadonnées de base")
        return _create_basic_metadata(file_path)

# ============================================================================
# TRAITEMENT DES DONNÉES GPS
# ============================================================================

# Constantes GPS pour faciliter l'extraction
GPSTAGS = {
    0: "GPSVersionID",
    1: "GPSLatitudeRef",
    2: "GPSLatitude",
    3: "GPSLongitudeRef",
    4: "GPSLongitude",
    5: "GPSAltitudeRef",
    6: "GPSAltitude",
    7: "GPSTimeStamp",
    8: "GPSSatellites",
    9: "GPSStatus",
    10: "GPSMeasureMode",
    11: "GPSDOP",
    12: "GPSSpeedRef",
    13: "GPSSpeed",
    14: "GPSTrackRef",
    15: "GPSTrack",
    16: "GPSImgDirectionRef",
    17: "GPSImgDirection",
    18: "GPSMapDatum",
    19: "GPSDestLatitudeRef",
    20: "GPSDestLatitude",
    21: "GPSDestLongitudeRef",
    22: "GPSDestLongitude",
    23: "GPSDestBearingRef",
    24: "GPSDestBearing",
    25: "GPSDestDistanceRef",
    26: "GPSDestDistance",
    27: "GPSProcessingMethod",
    28: "GPSAreaInformation",
    29: "GPSDateStamp",
    30: "GPSDifferential"
}


def get_gps_data(exif_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les informations GPS des données EXIF avec gestion robuste de différents formats.
    
    Args:
        exif_data: Dictionnaire contenant les données EXIF
        
    Returns:
        Dictionnaire contenant les informations GPS normalisées
    """
    if not exif_data:
        return {}
    
    gps_info = {}
    
    # Méthode 1: Extraction standard via le tag GPSInfo
    if 'GPSInfo' in exif_data:
        gps_data = exif_data['GPSInfo']
        
        # Format dictionnaire (provenant de PIL)
        if isinstance(gps_data, dict):
            for key in gps_data.keys():
                tag_name = GPSTAGS.get(key, key)
                gps_info[tag_name] = gps_data[key]
                
        # Format chaîne (provenant de la conversion exifread)
        elif isinstance(gps_data, str):
            try:
                import ast
                # Analyse sécurisée de la représentation en chaîne
                gps_dict = ast.literal_eval(gps_data.replace("'", '"'))
                for key, value in gps_dict.items():
                    gps_info[key] = value
            except Exception as e:
                print(f"Erreur lors de l'analyse des données GPS au format chaîne: {e}")
    
    # Méthode 2: Accès direct aux données IFD GPS (pour les fichiers HEIC/HEIF avec pillow_heif)
    elif hasattr(exif_data, 'get') and exif_data.get(0x8825):  # Tag IFD GPS
        gps_data = exif_data.get(0x8825)
        if isinstance(gps_data, dict):
            for k, v in gps_data.items():
                try:
                    gps_info[GPSTAGS.get(k, k)] = v
                except Exception:
                    gps_info[k] = v
    
    # Méthode 3: Recherche directe des tags GPS dans exif_data
    else:
        for tag_id, tag_name in GPSTAGS.items():
            if tag_id in exif_data:
                gps_info[tag_name] = exif_data[tag_id]
            elif tag_name in exif_data:
                gps_info[tag_name] = exif_data[tag_name]
    
    return gps_info

def get_coordinates(gps_info: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Convertit les données GPS en latitude et longitude décimales.
    
    Args:
        gps_info: Dictionnaire contenant les informations GPS
        
    Returns:
        Tuple (latitude, longitude) en degrés décimaux ou (None, None) si la conversion échoue
    """
    if not gps_info:
        return None, None
    
    try:
        # Extraire les données de latitude
        lat_data = gps_info.get('GPSLatitude', gps_info.get(2))
        lat_ref = gps_info.get('GPSLatitudeRef', gps_info.get(1, 'N'))
        
        # Extraire les données de longitude
        lon_data = gps_info.get('GPSLongitude', gps_info.get(4))
        lon_ref = gps_info.get('GPSLongitudeRef', gps_info.get(3, 'E'))
        
        if not all([lat_data, lon_data]):
            return None, None
            
        def convert_to_degrees(value):
            """Convertit une valeur GPS en degrés décimaux."""
            try:
                # Si c'est une liste ou un tuple de 3 éléments
                if isinstance(value, (list, tuple)) and len(value) == 3:
                    d = float(value[0])
                    m = float(value[1])
                    s = float(value[2])
                    return d + (m / 60.0) + (s / 3600.0)
                # Si c'est une valeur unique
                return float(value)
            except (ValueError, TypeError, IndexError):
                        return None
                
        # Convertir les coordonnées
        lat = convert_to_degrees(lat_data)
        lon = convert_to_degrees(lon_data)
        
        if lat is None or lon is None:
            return None, None
                
        # Appliquer les références
        if isinstance(lat_ref, str):
            lat_ref = lat_ref.upper()
            if lat_ref == 'S':
                lat = -lat
                
        if isinstance(lon_ref, str):
            lon_ref = lon_ref.upper()
            if lon_ref == 'W':
                lon = -lon
        
        # Vérifier les plages valides
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
        
        return None, None
        
    except Exception as e:
        print(f"Erreur lors de l'extraction des coordonnées GPS: {e}")
        return None, None
    
def get_image_gps_coordinates(file_path: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Fonction unifiée pour obtenir les coordonnées GPS d'une image, quel que soit son format.
    
    Args:
        file_path: Chemin vers le fichier image
        
    Returns:
        Tuple (latitude, longitude) ou (None, None) si aucune coordonnée n'est trouvée
    """
    from utils.file_utils import normalize_path
    
    # Normaliser le chemin du fichier
    file_path = normalize_path(file_path)
    if not os.path.exists(file_path):
        print(f"Le fichier n'existe pas: {file_path}")
        return None, None
    
    # Déterminer le format de fichier
    ext = os.path.splitext(file_path)[1].lower()
    
    # Traitement spécifique pour les fichiers HEIC/HEIF
    if ext in ['.heic', '.heif']:
        exif_data = get_heif_exif_data(file_path)
    else:
        # Utiliser la fonction standard pour les autres formats
        exif_data = get_exif_data(file_path)
    
    # Extraire les informations GPS
    gps_info = get_gps_data(exif_data)
    
    # Convertir en coordonnées
    return get_coordinates(gps_info)

def has_gps_data(file_path: str) -> bool:
    """
    Vérifie si une image contient des données GPS valides.
    
    Args:
        file_path: Chemin vers l'image
        
    Returns:
        True si l'image contient des coordonnées GPS valides, False sinon
    """
    coords = get_image_gps_coordinates(file_path)
    return coords[0] is not None and coords[1] is not None

def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calcule la distance en kilomètres entre deux points GPS (formule de Haversine).
    
    Args:
        coord1: Tuple (latitude, longitude) du premier point
        coord2: Tuple (latitude, longitude) du deuxième point
        
    Returns:
        Distance en kilomètres
    """
    # Rayon de la Terre en kilomètres
    R = 6371.0
    
    # Convertir les degrés en radians
    lat1 = math.radians(coord1[0])
    lon1 = math.radians(coord1[1])
    lat2 = math.radians(coord2[0])
    lon2 = math.radians(coord2[1])
    
    # Différence de longitude et latitude
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    # Formule de Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance

def generate_google_maps_link(latitude: float, longitude: float, zoom: int = 15) -> str:
    """
    Génère un lien Google Maps à partir de coordonnées GPS.
    
    Args:
        latitude: Latitude en degrés décimaux
        longitude: Longitude en degrés décimaux
        zoom: Niveau de zoom (1-20)
    
    Returns:
        Lien Google Maps pour les coordonnées
    """
    return f"https://www.google.com/maps?q={latitude},{longitude}&z={zoom}"

# ============================================================================
# EXTRACTION DE DATES
# ============================================================================
# (Imports already at top of file - removed duplicates)

def extract_image_date(file_path, fallback_to_file_date=True, origin_info=False):
    """
    Fonction unifiée pour extraire la date d'un fichier image avec une approche hiérarchique complète.
    
    Cette fonction combine intelligemment l'extraction depuis:
    1. Métadonnées EXIF (priorité maximale)
    2. Nom de fichier (nombreux formats spécifiques aux fabricants)
    3. Date du fichier système (en dernier recours)
    
    Args:
        file_path (str): Chemin complet ou nom de fichier
        fallback_to_file_date (bool): Si True, utilise la date du fichier comme dernier recours
        origin_info (bool): Si True, retourne aussi l'origine de la date extraite
        
    Returns:
        datetime ou tuple (datetime, str): Date extraite et optionnellement l'origine
    """
    log_message(f"\n=== DÉBUT EXTRACT_IMAGE_DATE pour: {file_path} ===")
    log_message(f"Paramètres: fallback_to_file_date={fallback_to_file_date}, origin_info={origin_info}")
    
    # Vérification stricte du type de file_path
    if not isinstance(file_path, (str, bytes, os.PathLike)):
        log_message(f"ERREUR: Type de chemin de fichier invalide dans extract_image_date: {type(file_path)}")
        log_message(f"Valeur reçue: {file_path}")
        if origin_info:
            log_message("Retour: (None, None) - Type de fichier invalide")
            return None, None
        log_message("Retour: None - Type de fichier invalide")
        return None
    
    # Normaliser le chemin du fichier
    file_path = normalize_path(file_path)
    log_message(f"Chemin normalisé: {file_path}")
    
    # Si c'est juste un nom de fichier sans chemin, essayer d'extraire la date du nom
    if not os.path.dirname(file_path):
        log_message("Aucun chemin de répertoire détecté - traitement comme nom de fichier uniquement")
        filename = os.path.basename(file_path)
        log_message(f"Nom de fichier à analyser: {filename}")
        # Essayer d'extraire la date du nom de fichier
        date_taken = None
        date_origin = None
        
        # Patterns pour les noms de fichiers
        patterns = [
            # Format Samsung (YYYYMMDD_HHMMSS)
            (r'(\d{8})_(\d{6})', 
        lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
        
            # Format iPhone (IMG_YYYYMMDD_HHMMSS)
            (r'IMG_(\d{8})_(\d{6})', 
             lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
            
            # Format Google Pixel (PXL_YYYYMMDD_HHMMSS)
            (r'PXL_(\d{8})_(\d{6})', 
             lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
        ]
        
        log_message(f"Vérification de {len(patterns)} patterns de noms de fichiers...")
        for i, (pattern, parser) in enumerate(patterns):
            log_message(f"Test du pattern {i+1}: {pattern}")
            match = re.search(pattern, filename)
            if match:
                log_message(f"Match trouvé avec le pattern {i+1}!")
                try:
                    date_taken = parser(match)
                    date_origin = "filename"
                    log_message(f"Date extraite: {date_taken} (origine: {date_origin})")
                    break
                except (ValueError, Exception) as e:
                    log_message(f"Erreur lors de l'analyse de la date: {e}")
                    continue
            else:
                log_message(f"Aucun match avec le pattern {i+1}")
        
        if date_taken:
            log_message(f"Date trouvée depuis le nom de fichier: {date_taken}")
            if origin_info:
                log_message(f"Retour: ({date_taken}, {date_origin})")
                return date_taken, date_origin
            log_message(f"Retour: {date_taken}")
            return date_taken
        else:
            log_message("Aucune date trouvée dans le nom de fichier")
    
    # Déterminer le type de fichier
    ext = os.path.splitext(file_path)[1].lower()
    log_message(f"Extension du fichier: {ext}")
    
    # Initialiser les variables
    date_taken = None
    date_origin = None
    filename = os.path.basename(file_path)
    log_message(f"Nom du fichier: {filename}")
    
    # 1. MÉTHODE PRIORITAIRE: Métadonnées EXIF si le fichier existe
    if os.path.exists(file_path):
        log_message("Le fichier existe, tentative d'extraction des métadonnées EXIF")
        try:
            # Extraire les métadonnées EXIF
            log_message("Extraction des données EXIF...")
            exif_data = get_exif_data(file_path)
            log_message(f"Données EXIF extraites: {len(exif_data) if exif_data else 0} éléments")
            
            # Essayer d'extraire la date des métadonnées EXIF
            if exif_data:
                # Parcourir les champs de date par ordre de priorité
                date_fields = [
                    'DateTimeOriginal', 'DateTime', 'CreateDate', 'DateTimeDigitized',
                    'ModifyDate', 'TrackCreateDate', 'MediaCreateDate'
                ]
                log_message(f"Recherche des dates EXIF dans les champs: {', '.join(date_fields)}")
                
                # Formats de date EXIF à essayer
                date_formats = [
                    '%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S',
                    '%Y:%m:%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S.%f', '%Y/%m/%d %H:%M:%S.%f'
                ]
                log_message(f"Formats de date à tester: {', '.join(date_formats)}")
                
                # Essayer chaque champ de date
                for field in date_fields:
                    log_message(f"Recherche du champ de date: {field}")
                    if field in exif_data:
                        date_str = exif_data[field]
                        log_message(f"Valeur trouvée pour {field}: {date_str}")
                        if isinstance(date_str, str):
                            # Essayer chaque format de date
                            for date_format in date_formats:
                                log_message(f"Test du format: {date_format}")
                                try:
                                    date_taken = datetime.strptime(date_str, date_format)
                                    date_origin = f"EXIF:{field}"
                                    log_message(f"Date EXIF extraite avec succès: {date_taken} (format: {date_format})")
                                    break
                                except ValueError as e:
                                    log_message(f"Format {date_format} incompatible: {e}")
                                    continue
                            if date_taken:
                                log_message(f"Date trouvée dans EXIF: {date_taken} (origine: {date_origin})")
                                break
                            else:
                                log_message(f"Aucun format compatible pour la valeur de {field}")
                    else:
                        log_message(f"Champ {field} non trouvé dans les données EXIF")
        except Exception as e:
            log_message(f"ERREUR lors de l'extraction de la date EXIF: {e}")
    else:
        log_message(f"Le fichier n'existe pas: {file_path}")
    
    # 2. REPLI: Extraction à partir du nom de fichier
    if not date_taken:
        log_message("Aucune date EXIF trouvée, tentative d'extraction depuis le nom de fichier")
        # Dictionnaire des modèles par fabricant avec leurs patterns et fonctions d'analyse
        manufacturer_patterns = {
            # Samsung Galaxy patterns
            'samsung': [
                (r'(\d{8})_(\d{6})(?:_\d+)?\.(?:heic|heif|jpg|jpeg|mp4)$', 
                 lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
                # Variante sans extension spécifique
                (r'^(\d{8})_(\d{6})(?:_\d+)?$', 
                 lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
            ],
            
            # iPhone patterns
            'iphone': [
                (r'^IMG_(\d{8})_(\d{6})\.', 
                 lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
                # Format standard Apple
                (r'^IMG_(\d{4})$', 
                 lambda m: datetime.strptime(f"20{m.group(1)[:2]}{m.group(1)[2:]}", "%Y%m%d") 
         if int(m.group(1)[:2]) <= 99 else None),
            ],
            
            # Google Pixel patterns
            'pixel': [
                (r'PXL_(\d{8})_(\d{9})_?(?:MP|TS)?', 
                 lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)[:6]}", "%Y%m%d_%H%M%S")),
            ],
            
            # WhatsApp patterns
            'whatsapp': [
                (r'IMG-(\d{8})-WA', 
                 lambda m: datetime.strptime(m.group(1), "%Y%m%d")),
                (r'VID-(\d{8})-WA\d{4}', 
                 lambda m: datetime.strptime(m.group(1), "%Y%m%d")),
            ],
            
            # GoPro patterns
            'gopro': [
                (r'GoPro(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',
                 lambda m: datetime(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)), 
                                    int(m.group(4)), int(m.group(5)), int(m.group(6)))),
            ],
            
            # Drone DJI patterns
            'dji': [
                (r'DJI_(\d{8})_(\d{6})(_\d+)?', 
                 lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
            ],
        }
        log_message(f"Test de {len(manufacturer_patterns)} modèles de fabricants")
        
        # Vérifier d'abord les patterns spécifiques aux fabricants
        for manufacturer, patterns in manufacturer_patterns.items():
            log_message(f"Vérification des patterns pour {manufacturer} ({len(patterns)} patterns)")
            for i, (pattern, parser) in enumerate(patterns):
                log_message(f"Test du pattern {manufacturer} #{i+1}: {pattern}")
                match = re.search(pattern, filename)
                if match:
                    log_message(f"Match trouvé avec pattern {manufacturer} #{i+1}!")
                    try:
                        date_result = parser(match)
                        log_message(f"Date analysée: {date_result}")
                        if date_result:
                            date_taken = date_result
                            date_origin = f"filename:{manufacturer}"
                            log_message(f"Date extraite: {date_taken} (origine: {date_origin})")
                            break
                        else:
                            log_message("Le parser a retourné None")
                    except (ValueError, Exception) as e:
                        log_message(f"Erreur lors de l'analyse de la date: {e}")
                        continue
                else:
                    log_message(f"Aucun match avec pattern {manufacturer} #{i+1}")
            if date_taken:
                log_message(f"Date trouvée avec les patterns de {manufacturer}")
                break
        
        # Patterns génériques (non spécifiques à un fabricant)
        generic_patterns = [
            # Format standard YYYYMMDD_HHMMSS
            (r'(?:^|[^0-9])(\d{8})_(\d{6})(?:[^0-9]|$)', 
             lambda m: datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S")),
            
            # Format avec tirets YYYY-MM-DD_HH-MM-SS
            (r'(\d{4})-(\d{2})-(\d{2})[\s_-](\d{2})[-_](\d{2})[-_](\d{2})', 
             lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 
                               int(m.group(4)), int(m.group(5)), int(m.group(6)))),
            
            # Format européen/américain DD-MM-YYYY ou MM-DD-YYYY
            (r'(\d{2})[.-](\d{2})[.-](\d{4})', 
             lambda m: _parse_ambiguous_date(m.group(1), m.group(2), m.group(3))),
            
            # Format avec mois en texte
            (r'(\d{2})[-_]([A-Za-z]{3})[-_](\d{4})', 
             lambda m: datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y")),
            
            # Format date simple YYYYMMDD
        (r'(?:^|[^0-9])(\d{4})(\d{2})(\d{2})(?:[^0-9]|$)', 
             lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
         if 1900 <= int(m.group(1)) <= 2100 and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31 
         else None),
        ]
        
        # Sinon, essayer les patterns génériques
        if not date_taken:
            log_message(f"Aucune date trouvée avec les patterns spécifiques, test des {len(generic_patterns)} patterns génériques")
            for i, (pattern, parser) in enumerate(generic_patterns):
                log_message(f"Test du pattern générique #{i+1}: {pattern}")
                match = re.search(pattern, filename)
                if match:
                    log_message(f"Match trouvé avec pattern générique #{i+1}!")
                    try:
                        date_result = parser(match)
                        log_message(f"Date analysée: {date_result}")
                        if date_result:
                            date_taken = date_result
                            date_origin = "filename:generic"
                            log_message(f"Date extraite: {date_taken} (origine: {date_origin})")
                            break
                        else:
                            log_message("Le parser a retourné None")
                    except (ValueError, Exception) as e:
                        log_message(f"Erreur lors de l'analyse de la date: {e}")
                        continue
                else:
                    log_message(f"Aucun match avec pattern générique #{i+1}")
    
    # 3. DERNIER RECOURS: Date du fichier
    if not date_taken and fallback_to_file_date and os.path.exists(file_path):
        log_message("Aucune date trouvée dans les métadonnées ou le nom de fichier, utilisation de la date du fichier")
        try:
            # Essayer d'abord la date de création si disponible
            if hasattr(os.path, 'getctime'):
                log_message("Tentative d'extraction de la date de création du fichier")
                creation_time = os.path.getctime(file_path)
                date_taken = datetime.fromtimestamp(creation_time)
                date_origin = "file:creation"
                log_message(f"Date de création du fichier: {date_taken}")
            else:
                # Utiliser la date de modification en dernier recours
                log_message("getctime non disponible, utilisation de la date de modification")
                modification_time = os.path.getmtime(file_path)
                date_taken = datetime.fromtimestamp(modification_time)
                date_origin = "file:modification"
                log_message(f"Date de modification du fichier: {date_taken}")
        except Exception as e:
            log_message(f"ERREUR lors de l'obtention de la date du fichier {file_path}: {e}")
    elif not date_taken:
        log_message("Aucune date trouvée et fallback_to_file_date est False ou le fichier n'existe pas")
    
    # Retourner le résultat selon le format demandé
    if origin_info:
        result = (date_taken, date_origin) if date_taken else (None, None)
        log_message(f"=== FIN EXTRACT_IMAGE_DATE: Retour avec origine: {result} ===\n")
        return result
    else:
        log_message(f"=== FIN EXTRACT_IMAGE_DATE: Retour sans origine: {date_taken} ===\n")
        return date_taken
    
def get_camera_info(exif_data: Dict[str, Any], file_path: Optional[str] = None, format_output: bool = True) -> Tuple[str, str]:
    """
    Extrait et formate les informations sur l'appareil photo à partir des données EXIF et/ou du nom de fichier.
    
    Cette fonction consolidée combine l'extraction des métadonnées EXIF, la déduction à partir du nom
    de fichier, et le formatage pour l'affichage.
    
    Args:
        exif_data: Dictionnaire contenant les données EXIF, ou chemin du fichier
        file_path: Chemin du fichier (optionnel si déjà présent dans exif_data)
        format_output: Appliquer le formatage pour l'affichage
        
    Returns:
        Tuple (make, model) sous forme de chaînes, 'Unknown' si non disponible
    """
    # Gérer le cas où exif_data est un chemin de fichier
    if isinstance(exif_data, str) and os.path.exists(exif_data):
        file_path = exif_data
        exif_data = get_exif_data(file_path)
    
    if not exif_data:
        if file_path:
            # Si on a un chemin de fichier mais pas de données EXIF,
            # essayer de déduire à partir du nom de fichier uniquement
            filename = os.path.basename(file_path)
            return _deduce_from_filename(filename, format_output)
        return 'Unknown', 'Unknown'
    
    # Extraire le fabricant
    make = 'Unknown'
    if 'Make' in exif_data:
        try:
            if isinstance(exif_data['Make'], str):
                make = exif_data['Make'].strip()
            else:
                make = str(exif_data['Make']).strip()
        except Exception:
            pass
    
    # Extraire le modèle
    model = 'Unknown'
    if 'Model' in exif_data:
        try:
            if isinstance(exif_data['Model'], str):
                model = exif_data['Model'].strip()
            else:
                model = str(exif_data['Model']).strip()
        except Exception:
            pass
    
    # Nettoyer les noms de fabricant et de modèle
    make = make.replace('_', ' ')
    model = model.replace('_', ' ')
    
    # Déduction basée sur le nom de fichier si les métadonnées sont absentes
    if (make == 'Unknown' or model == 'Unknown') and (file_path or 'FileName' in exif_data):
        filename = os.path.basename(file_path) if file_path else exif_data.get('FileName', '')
        
        # Pour les fichiers HEIC de l'iPhone
        if filename.startswith('IMG_') and filename.endswith(('.HEIC', '.heic')):
            make = 'Apple' if make == 'Unknown' else make
            model = 'iPhone' if model == 'Unknown' else model
        
        # Pour les fichiers Samsung Galaxy S23 (format YYYYMMDD_HHMMSS avec ou sans suffixe)
        elif re.match(r'^(\d{8})_(\d{6})(?:_\d+)?(?:\.\w+)?$', filename):
            # Ce pattern reconnaît :
            # - 8 chiffres pour la date (YYYYMMDD)
            # - underscore
            # - 6 chiffres pour l'heure (HHMMSS)
            # - optionnellement : underscore suivi d'un ou plusieurs chiffres (pour les doublons)
            # - optionnellement : point suivi de l'extension
            
            # Vérifier que la date est valide avant d'attribuer à Samsung
            match = re.match(r'^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
            if match:
                year, month, day, hour, minute, second = match.groups()
                year = int(year)
                month = int(month)
                day = int(day)
                
                # Validation basique de la date
                if 2000 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                    make = 'Samsung' if make == 'Unknown' else make
                    model = 'Galaxy S23' if model == 'Unknown' else model
        
        # Pour les fichiers Google Pixel (photos et vidéos)
        elif filename.startswith('PXL_'):
            make = 'Google' if make == 'Unknown' else make
            model = 'Pixel' if model == 'Unknown' else model
            # Vérification spécifique pour le format vidéo
            if re.match(r'^PXL_\d{8}_\d{6}\.mp4$', filename, re.IGNORECASE):
                model = 'Pixel Video'
    
    if format_output:
        # Normalisation et formatage pour l'affichage
        make, model = _format_camera_names(make, model)
    
    return make, model

def _deduce_from_filename(filename: str, format_output: bool = True) -> Tuple[str, str]:
    """
    Déduit la marque et le modèle de l'appareil photo à partir du nom de fichier.
    """
    make, model = 'Unknown', 'Unknown'
    
    # Pour les fichiers HEIC de l'iPhone
    if filename.startswith('IMG_') and filename.endswith(('.HEIC', '.heic')):
        make = 'Apple'
        model = 'iPhone'
    # Pour les fichiers Google Pixel (photos et vidéos)
    elif filename.startswith('PXL_'):
        make = 'Google'
        model = 'Pixel'
        # Vérification spécifique pour le format vidéo
        if re.match(r'^PXL_\d{8}_\d{6}\.mp4$', filename, re.IGNORECASE):
            model = 'Pixel Video'
    # Pour les fichiers Samsung Galaxy S23
    elif re.match(r'^\d{8}_\d{6}', filename):
            make = 'Samsung'
            model = 'Galaxy S23'
    
    if format_output:
        make, model = _format_camera_names(make, model)
    
    return make, model

def _format_camera_names(make: str, model: str) -> Tuple[str, str]:
    """
    Formate les noms de marque et modèle pour l'affichage.
    
    Args:
        make: Nom du fabricant
        model: Nom du modèle
        
    Returns:
        Tuple (make, model) formatés
    """
    # Normalisation de base
    make = make.strip().title() if make else 'Unknown'
    model = model.strip().title() if model else 'Unknown'
    
    # Cas spéciaux pour les noms de fabricants
    make_mapping = {
        'Google Inc': 'Google',
        'Google Inc.': 'Google',
        'Samsung Electronics': 'Samsung',
        'Samsung Electronics Co., Ltd.': 'Samsung',
        'Samsung Electronics Co.,Ltd.': 'Samsung',
        'Samsung Electronics Co., Ltd': 'Samsung',
        'Samsung Electronics Co.,Ltd': 'Samsung'
    }
    
    if make in make_mapping:
        make = make_mapping[make]
    
    # Cas spéciaux pour les modèles
    model_mapping = {
        'SM-S911B': 'Galaxy S23',
        'SM-S911U': 'Galaxy S23',
        'SM-S911W': 'Galaxy S23',
        'SM-S911N': 'Galaxy S23',
        'SM-S9110': 'Galaxy S23',
        'SM-S911B/DS': 'Galaxy S23',
        'SM-S911U1': 'Galaxy S23',
        'SM-S911W/DS': 'Galaxy S23',
        'SM-S911N/DS': 'Galaxy S23',
        'SM-S9110/DS': 'Galaxy S23',
        'Pixel 6': 'Pixel',
        'Pixel 6 Pro': 'Pixel',
        'Pixel 7': 'Pixel',
        'Pixel 7 Pro': 'Pixel',
        'Pixel 8': 'Pixel',
        'Pixel 8 Pro': 'Pixel'
    }
    
    if model in model_mapping:
        model = model_mapping[model]
    
    # Format avancé avec règles spéciales pour certains mots
    make_words = make.split()
    model_words = model.split()
    
    # Formater les mots (mots courts en majuscules, autres avec première lettre en majuscule)
    formatted_make = []
    formatted_model = []
    
    # Formatage du fabricant
    for word in make_words:
        # Séparer le mot en parties en utilisant les caractères spéciaux comme séparateurs
        parts = re.split(r'([^a-zA-Z0-9]+)', word)
        formatted_parts = []
        
        for part in parts:
            if not part:  # Ignorer les parties vides
                continue
            if re.match(r'[^a-zA-Z0-9]', part):  # Si c'est un caractère spécial
                formatted_parts.append(part)
            else:  # Si c'est une partie alphanumérique
                if len(part) <= 4:
                    formatted_parts.append(part.upper())
                elif part.isdigit():  # Si c'est une partie numérique
                    formatted_parts.append(part)
                else:
                    formatted_parts.append(part.capitalize())
        
        formatted_make.append(''.join(formatted_parts))
    
    # Formatage du modèle
    for word in model_words:
        # Séparer le mot en parties en utilisant les caractères spéciaux comme séparateurs
        parts = re.split(r'([^a-zA-Z0-9]+)', word)
        formatted_parts = []
        
        for part in parts:
            if not part:  # Ignorer les parties vides
                continue
            if re.match(r'[^a-zA-Z0-9]', part):  # Si c'est un caractère spécial
                formatted_parts.append(part)
            else:  # Si c'est une partie alphanumérique
                if len(part) <= 4:
                    formatted_parts.append(part.upper())
                elif part.isdigit():  # Si c'est une partie numérique
                    formatted_parts.append(part)
                else:
                    formatted_parts.append(part.capitalize())
        
        formatted_model.append(''.join(formatted_parts))
    
    # Cas spéciaux pour certains mots dans les noms
    special_words = {
        'Dslr': 'DSLR',
        'Mirrorless': 'Mirrorless',
        'Compact': 'Compact',
        'Bridge': 'Bridge',
        'Action': 'Action',
        'Drone': 'Drone',
        'Smartphone': 'Smartphone',
        'Samsung': 'Samsung',
        'Galaxy': 'Galaxy'
    }
    
    make = ' '.join(formatted_make)
    model = ' '.join(formatted_model)
    
    # Appliquer les cas spéciaux
    for old, new in special_words.items():
        make = make.replace(old, new)
        model = model.replace(old, new)
    
    return make, model


def get_image_dimensions(image_path: str) -> Optional[Tuple[int, int]]:
    """
    Obtient les dimensions d'une image (largeur, hauteur).
    
    Args:
        image_path: Chemin vers l'image
        
    Returns:
        Tuple (largeur, hauteur) ou None si l'extraction échoue
    """
    try:
        # Vérifier l'extension du fichier
        ext = os.path.splitext(image_path)[1].lower()
        
        # Traitement spécial pour les fichiers HEIC/HEIF
        if ext in ['.heic', '.heif']:
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()
                with Image.open(image_path) as img:
                    return img.size
            except ImportError:
                print("La bibliothèque pillow-heif n'est pas installée pour les fichiers HEIC/HEIF")
                return None
            except Exception as e:
                print(f"Erreur lors de l'ouverture du fichier HEIC/HEIF {image_path}: {e}")
                return None
        
        # Traitement spécial pour les vidéos
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.3gp', '.m4v', '.mpg', '.mpeg', '.mts', '.ts', '.vob']:
            try:
                import cv2
                cap = cv2.VideoCapture(image_path)
                if cap.isOpened():
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    return (width, height)
            except ImportError:
                print("OpenCV n'est pas installé pour les fichiers vidéo")
            except Exception as e:
                print(f"Erreur lors de l'ouverture de la vidéo {image_path}: {e}")
            return None
        
        # Pour les autres formats d'image
        with Image.open(image_path) as img:
            return img.size
            
    except Exception as e:
        print(f"Erreur lors de l'obtention des dimensions de l'image {image_path}: {e}")
        return None


def has_gps_data(image_path: str) -> bool:
    """
    Vérifie si une image contient des données GPS.
    
    Args:
        image_path: Chemin vers l'image
        
    Returns:
        True si l'image contient des coordonnées GPS valides, False sinon
    """
    exif_data = get_exif_data(image_path)
    gps_info = get_gps_data(exif_data)
    lat, lon = get_coordinates(gps_info)
    return lat is not None and lon is not None


def process_file(file_path):
    """Process a single file and return its metadata."""
    metadata = {}
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Traitement des images
        if file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.heic', '.heif']:
            exif_data = get_exif_data(file_path)
            
            # Extraction de la date
            date_taken = None
            for date_field in ['DateTimeOriginal', 'DateTime', 'CreateDate']:
                date_taken = exif_data.get(date_field)
                if date_taken:
                    try:
                        date_taken = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S')
                        break
                    except ValueError:
                        continue
            
            # Si pas de date EXIF, utiliser la date de modification
            if not date_taken:
                date_taken = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # Extraction des données GPS
            gps_data = get_gps_data(exif_data)
            lat, lon = get_coordinates(gps_data)
            
            # Extraction des informations de l'appareil photo
            make, model = get_camera_info(exif_data, file_path)
            
        # Traitement des vidéos
        elif file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.wmv']:
            date_taken = datetime.fromtimestamp(os.path.getmtime(file_path))
            lat, lon = None, None
            make, model = 'Unknown', 'Unknown'
            
        # Traitement des fichiers RAW
        elif file_ext in ['.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng']:
            date_taken = datetime.fromtimestamp(os.path.getmtime(file_path))
            lat, lon = None, None
            make, model = 'Unknown', 'Unknown'
        else:
            return None

        metadata = {
            "file_path": file_path,
            "date_taken": date_taken,
            "lat": lat,
            "lon": lon,
            "make": make,
            "model": model,
            "file_type": file_ext[1:].upper()  # Extension sans le point
        }
        
    except Exception as e:
        print(f"Erreur lors du traitement du fichier {file_path}: {e}")
        return None
    
    return metadata

def create_date_based_directory(root_dir, date_obj):
    """
    Crée une structure de répertoires basée sur la date au format :
    Année > Année_Mois > Année_Mois_Jour
    
    Args:
        root_dir: Répertoire racine
        date_obj: Objet datetime contenant la date
        
    Returns:
        Chemin du répertoire du jour créé
    """
    try:
        # Créer le répertoire de l'année
        year_dir = os.path.join(root_dir, str(date_obj.year))
        ensure_dir_exists(year_dir)
        
        # Créer le répertoire du mois (format: Année_Mois)
        month_dir = os.path.join(year_dir, f"{date_obj.year}_{date_obj.month:02d}")
        ensure_dir_exists(month_dir)
        
        # Créer le répertoire du jour (format: Année_Mois_Jour)
        day_dir = os.path.join(month_dir, f"{date_obj.year}_{date_obj.month:02d}_{date_obj.day:02d}")
        ensure_dir_exists(day_dir)
        
        return day_dir
    except Exception as e:
        print(f"Erreur lors de la création du répertoire de date: {e}")
        return root_dir

def _parse_ambiguous_date(part1, part2, part3):
    """
    Tente de deviner si le format est JJ-MM-AAAA ou MM-JJ-AAAA.
    Retourne un objet datetime si possible, sinon None.
    """
    try:
        # Essai JJ-MM-AAAA
        return datetime(int(part3), int(part2), int(part1))
    except ValueError:
        try:
            # Essai MM-JJ-AAAA
            return datetime(int(part3), int(part1), int(part2))
        except ValueError:
            return None