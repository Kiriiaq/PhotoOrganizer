#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modules principaux pour la gestion et l'analyse d'images.
"""

"""Module pour les opérations sur les fichiers comme copier, déplacer et organiser."""

import os
import shutil
import logging
import sys
import datetime
import numpy as np

# Add project root to path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import metadata
from utils.file_utils import ensure_dir_exists

logger = logging.getLogger(__name__)

def copy_file(source, destination):
    """Copies a file with metadata preservation."""
    try:        
        dest_dir = os.path.dirname(destination)
        ensure_dir_exists(dest_dir)
            
        # Use copy2 to preserve metadata for all file types
        shutil.copy2(source, destination)
        return True
    except Exception as e:
        print(f"Error copying file {source} to {destination}: {e}")
        return False

def run_smart_organization(file_paths, target_dir, options, progress_callback=None, log_file="organization_log.txt"):
    """
    Organise les fichiers selon les critères spécifiés.
    
    Args:
        file_paths: Liste des chemins de fichiers à organiser
        target_dir: Répertoire de destination
        options: Dictionnaire des options d'organisation
        progress_callback: Fonction de callback pour le suivi de la progression
        log_file: Chemin du fichier de log (par défaut: "organization_log.txt")
        
    Returns:
        Dictionnaire contenant les résultats de l'organisation
    """
    import sys
    import traceback

    # Configuration du système de journalisation avec encodage UTF-8 explicite
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[]  # On va configurer les handlers manuellement
    )
    
    logger = logging.getLogger("SmartOrganizer")
    logger.setLevel(logging.DEBUG)
    
    # Vider les handlers existants pour éviter les doublons
    if logger.handlers:
        logger.handlers.clear()
    
    # Configurer le handler pour le fichier avec encodage UTF-8 explicite
    try:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"AVERTISSEMENT: Impossible de configurer le fichier de log: {str(e)}")
    
    # Configurer le handler pour la console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    # Helper pour éviter les erreurs d'encodage
    def safe_log(level, message):
        try:
            if level == "INFO":
                logger.info(message)
            elif level == "DEBUG":
                logger.debug(message)
            elif level == "WARNING":
                logger.warning(message)
            elif level == "ERROR":
                logger.error(message)
            elif level == "CRITICAL":
                logger.critical(message)
        except UnicodeEncodeError:
            # Remplacer les caractères problématiques
            safe_message = message.encode('ascii', 'replace').decode('ascii')
            if level == "INFO":
                logger.info(safe_message)
            elif level == "DEBUG":
                logger.debug(safe_message)
            elif level == "WARNING":
                logger.warning(safe_message)
            elif level == "ERROR":
                logger.error(safe_message)
            elif level == "CRITICAL":
                logger.critical(safe_message)
    
    # Journalisation de début d'exécution
    safe_log("INFO", "="*80)
    safe_log("INFO", f"DÉMARRAGE DE L'ORGANISATION INTELLIGENTE - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_log("INFO", "="*80)
    safe_log("DEBUG", f"Version Python: {sys.version}")
    safe_log("DEBUG", f"Répertoire de travail: {os.getcwd()}")
    safe_log("INFO", f"Nombre de fichiers à traiter: {len(file_paths)}")
    safe_log("INFO", f"Répertoire cible: {target_dir}")
    safe_log("DEBUG", f"Options d'organisation: {options}")
    
    # Journaliser les 5 premiers fichiers comme exemple (si disponibles)
    if file_paths:
        safe_log("DEBUG", "Exemples de fichiers à traiter:")
        for i, path in enumerate(file_paths[:5]):
            safe_log("DEBUG", f"  - Fichier {i+1}: {path}")
        if len(file_paths) > 5:
            safe_log("DEBUG", f"  ... et {len(file_paths) - 5} autres fichiers")
    
    print("DEBUG: Début de run_smart_organization")
    print(f"DEBUG: Nombre de fichiers à traiter: {len(file_paths)}")
    print(f"DEBUG: Répertoire cible: {target_dir}")
    print(f"DEBUG: Options: {options}")
    
    # Validation des entrées
    if not file_paths:
        message = "Aucun fichier à traiter"
        safe_log("WARNING", message)
        print(f"DEBUG: {message}")
        return {
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'results': {
                'errors': [message]
            }
        }
    
    # Vérifier que le répertoire de destination existe et est accessible en écriture
    try:
        safe_log("INFO", "Vérification du répertoire de destination...")
        print("DEBUG: Vérification du répertoire de destination")
        ensure_dir_exists(target_dir)
        test_file = os.path.join(target_dir, '.write_test')
        safe_log("DEBUG", f"Création du fichier test: {test_file}")
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        safe_log("INFO", "Répertoire de destination vérifié avec succès")
        print("DEBUG: Répertoire de destination vérifié avec succès")
    except Exception as e:
        error_msg = f"Erreur d'accès au répertoire de destination: {str(e)}"
        safe_log("ERROR", error_msg)
        safe_log("ERROR", f"Détail de l'erreur: {traceback.format_exc()}")
        print(f"DEBUG: Erreur lors de la vérification du répertoire de destination: {str(e)}")
        return {
            'total': len(file_paths),
            'processed': 0,
            'skipped': 0,
            'errors': len(file_paths),
            'results': {
                'errors': [error_msg]
            }
        }
    
    # Initialiser les résultats
    results = {
        'total': len(file_paths),
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'results': {}
    }
    
    try:
        # Traiter chaque fichier
        for i, file_path in enumerate(file_paths):
            # Définir le nom du fichier au début de la boucle
            current_filename = os.path.basename(file_path) if file_path else "fichier inconnu"
            safe_log("INFO", f"[{i+1}/{len(file_paths)}] Traitement du fichier: {current_filename}")
            safe_log("DEBUG", f"Chemin complet: {file_path}")
            print(f"\nDEBUG: Traitement du fichier {i+1}/{len(file_paths)}: {current_filename}")
            
            try:
                # Mettre à jour la progression
                if progress_callback:
                    progress_value = i / len(file_paths) * 100
                    safe_log("DEBUG", f"Mise à jour de la progression: {progress_value:.2f}%")
                    progress_callback(progress_value)
                
                # Vérifier que le fichier existe
                if not os.path.exists(file_path):
                    error_msg = f"Le fichier n'existe pas: {file_path}"
                    safe_log("ERROR", error_msg)
                    print(f"DEBUG: {error_msg}")
                    results['errors'] += 1
                    results['results'].setdefault('errors', []).append(error_msg)
                    continue
                
                # EXTRACTION DES DATES - UNE SEULE FOIS AVEC LE CHEMIN COMPLET
                safe_log("DEBUG", "Extraction des métadonnées de date")
                print("DEBUG: Extraction des métadonnées de date")
                #Change
                
                try:
                    date_extraction_result = metadata.extract_image_date(file_path, fallback_to_file_date=True, origin_info=True)
                    
                    # Handle the case where extract_image_date returns None instead of a tuple
                    if date_extraction_result is None:
                        safe_log("WARNING", f"extract_image_date returned None for file: {file_path}")
                        date_result = None
                        date_origin = "not_found"
                    elif isinstance(date_extraction_result, tuple) and len(date_extraction_result) == 2:
                        date_result, date_origin = date_extraction_result
                    else:
                        # Fallback case - treat as single date value
                        safe_log("WARNING", f"extract_image_date returned unexpected format: {type(date_extraction_result)}")
                        date_result = date_extraction_result if hasattr(date_extraction_result, 'strftime') else None
                        date_origin = "unknown_format"
                        
                except Exception as e:
                    safe_log("ERROR", f"Exception during date extraction for {file_path}: {str(e)}")
                    date_result = None
                    date_origin = "extraction_error"
                
                date_str = date_result.strftime('%Y-%m-%d %H:%M:%S') if date_result else "Non trouvée"
                safe_log("DEBUG", f"Date extraite: {date_str} (source: {date_origin})")
                print(f"DEBUG: Date extraite: {date_str} (source: {date_origin})")
                
                # Obtenir les informations de l'image
                safe_log("DEBUG", "Récupération des informations de l'image")
                print("DEBUG: Récupération des informations de l'image")
                start_time = datetime.datetime.now()

                # NOUVEAU CODE D'EXTRACTION DES MÉTADONNÉES
                try:
                    safe_log("DEBUG", f"Démarrage de l'extraction des métadonnées pour: {file_path}")
                    
                    # Créer un dictionnaire pour stocker les informations avec la date déjà extraite
                    image_info = {
                        'file_path': file_path,
                        'filename': os.path.basename(file_path),
                        'date_taken': date_result,
                        'date_origin': date_origin
                    }
                    
                    try:
                        file_size = os.path.getsize(file_path)
                        image_info['file_size'] = file_size
                        safe_log("DEBUG", f"Taille du fichier: {file_size} octets ({file_size/1024/1024:.2f} MB)")
                    except Exception as e:
                        safe_log("WARNING", f"Impossible de déterminer la taille du fichier: {str(e)}")
                    
                    # Tenter d'obtenir les dimensions de l'image
                    try:
                        from PIL import Image
                        with Image.open(file_path) as img:
                            image_info['dimensions'] = img.size
                            image_info['format'] = img.format
                            safe_log("DEBUG", f"Dimensions: {img.size[0]}x{img.size[1]}, Format: {img.format}")
                    except Exception as e:
                        safe_log("WARNING", f"Impossible de déterminer les dimensions: {str(e)}")
                        image_info['dimensions'] = None
                    
                    # Extraire les données EXIF
                    try:
                        safe_log("DEBUG", "Extraction des données EXIF...")
                        exif_data = metadata.get_exif_data(file_path)
                        safe_log("DEBUG", f"Nombre d'éléments EXIF trouvés: {len(exif_data) if exif_data else 0}")

                        if exif_data:
                            # Extraire les informations sur l'appareil photo
                            safe_log("DEBUG", "Extraction des informations sur l'appareil photo")
                            make, model = metadata.get_camera_info(exif_data)
                            image_info['camera_make'] = make
                            image_info['camera_model'] = model
                            safe_log("DEBUG", f"Appareil photo: {make} {model}")

                            # Extraire les informations GPS
                            safe_log("DEBUG", "Recherche des coordonnées GPS")
                            coords = metadata.get_image_gps_coordinates(file_path)
                            has_gps = coords[0] is not None and coords[1] is not None
                            
                            image_info['has_gps'] = has_gps
                            image_info['gps_coordinates'] = coords
                            
                            if has_gps:
                                safe_log("DEBUG", f"Coordonnées GPS trouvées: Lat {coords[0]}, Long {coords[1]}")
                            else:
                                safe_log("DEBUG", "Pas de coordonnées GPS dans les métadonnées")
                            
                            # Extraire la date
                            try:
                                safe_log("DEBUG", "Extraction de la date de prise de vue")
                                date_extraction_result = metadata.extract_image_date(file_path, fallback_to_file_date=True, origin_info=True)
                                
                                # Handle the case where extract_image_date returns None instead of a tuple
                                if date_extraction_result is None:
                                    safe_log("WARNING", f"extract_image_date returned None for file: {file_path}")
                                    date_result = None
                                    origin = "not_found"
                                elif isinstance(date_extraction_result, tuple) and len(date_extraction_result) == 2:
                                    date_result, origin = date_extraction_result
                                elif isinstance(date_extraction_result, dict):
                                    # Si c'est un dictionnaire, essayer d'extraire les informations pertinentes
                                    safe_log("WARNING", f"extract_image_date returned dict for file: {file_path}")
                                    date_result = date_extraction_result.get('date')
                                    origin = date_extraction_result.get('origin', 'dict_format')
                                else:
                                    # Fallback case - treat as single date value
                                    safe_log("WARNING", f"extract_image_date returned unexpected format: {type(date_extraction_result)}")
                                    date_result = date_extraction_result if hasattr(date_extraction_result, 'strftime') else None
                                    origin = "unknown_format"
                                    
                            except Exception as e:
                                safe_log("ERROR", f"Exception during date extraction for {file_path}: {str(e)}")
                                date_result = None
                                origin = "extraction_error"
                            image_info['date_taken'] = date_result
                            image_info['date_origin'] = origin
                            
                            if date_result:
                                safe_log("DEBUG", f"Date de prise de vue: {date_result} (source: {origin})")
                            else:
                                safe_log("DEBUG", "Aucune date de prise de vue trouvée")
                    except Exception as e:
                        safe_log("WARNING", f"Erreur lors de l'extraction des métadonnées EXIF: {str(e)}")
                        safe_log("WARNING", traceback.format_exc())
                    
                    # Tenter d'obtenir des informations spécifiques au type de fichier
                    try:
                        ext = os.path.splitext(file_path)[1].lower()
                        image_info['extension'] = ext
                        
                        if ext in ['.jpg', '.jpeg']:
                            safe_log("DEBUG", "Fichier JPEG détecté, recherche de métadonnées spécifiques")
                            try:
                                with Image.open(file_path) as img:
                                    # Extraire la qualité JPEG si disponible
                                    if hasattr(img, 'info'):
                                        # Qualité de compression
                                        if 'quality' in img.info:
                                            image_info['jpeg_quality'] = img.info.get('quality')
                                            safe_log("DEBUG", f"Qualité JPEG: {img.info.get('quality')}")
                                        
                                        # Mode de compression
                                        if 'progressive' in img.info:
                                            image_info['jpeg_progressive'] = img.info.get('progressive')
                                            safe_log("DEBUG", f"JPEG progressif: {img.info.get('progressive')}")
                                        
                                        # Profil ICC
                                        if 'icc_profile' in img.info:
                                            image_info['has_icc_profile'] = True
                                            safe_log("DEBUG", "Profil ICC détecté")
                                        
                                        # DPI
                                        if 'dpi' in img.info:
                                            image_info['dpi'] = img.info.get('dpi')
                                            safe_log("DEBUG", f"DPI: {img.info.get('dpi')}")
                                    
                                    # Extraire les données EXIF supplémentaires
                                    exif = img.getexif()
                                    if exif:
                                        # Orientation
                                        if 274 in exif:  # Tag Orientation
                                            image_info['orientation'] = exif[274]
                                            safe_log("DEBUG", f"Orientation EXIF: {exif[274]}")
                                        
                                        # ISO
                                        if 34855 in exif:  # Tag ISOSpeedRatings
                                            image_info['iso'] = exif[34855]
                                            safe_log("DEBUG", f"ISO: {exif[34855]}")
                                        
                                        # Ouverture
                                        if 33437 in exif:  # Tag FNumber
                                            image_info['aperture'] = exif[33437]
                                            safe_log("DEBUG", f"Ouverture: f/{exif[33437]}")
                                            
                            except Exception as e:
                                safe_log("WARNING", f"Erreur lors de l'extraction des métadonnées JPEG: {str(e)}")
                        
                        elif ext in ['.heic', '.heif']:
                            safe_log("DEBUG", "Fichier HEIC/HEIF détecté")
                            try:
                                # Utiliser pillow_heif pour extraire des métadonnées supplémentaires
                                from pillow_heif import register_heif_opener
                                register_heif_opener()
                                
                                with Image.open(file_path) as img:
                                    # Mode de couleur
                                    image_info['color_mode'] = img.mode
                                    safe_log("DEBUG", f"Mode de couleur: {img.mode}")
                                    
                                    # Nombre de bandes de couleur
                                    if hasattr(img, 'getbands'):
                                        image_info['color_bands'] = img.getbands()
                                        safe_log("DEBUG", f"Bandes de couleur: {img.getbands()}")
                                    
                                    # Vérifier si c'est une image HDR
                                    if hasattr(img, 'info') and 'bit_depth' in img.info:
                                        bit_depth = img.info.get('bit_depth', 8)
                                        image_info['bit_depth'] = bit_depth
                                        image_info['is_hdr'] = bit_depth > 8
                                        safe_log("DEBUG", f"Profondeur de bits: {bit_depth}, HDR: {bit_depth > 8}")
                                    
                                    # Extraire les métadonnées Apple spécifiques
                                    exif = img.getexif()
                                    if exif:
                                        # Identifier le modèle d'iPhone via les tags maker notes
                                        if 37500 in exif:  # Tag MakerNote
                                            image_info['has_apple_maker_notes'] = True
                                            safe_log("DEBUG", "Notes du fabricant Apple détectées")
                                            
                            except Exception as e:
                                safe_log("WARNING", f"Erreur lors de l'extraction des métadonnées HEIC: {str(e)}")
                        
                        elif ext in ['.png']:
                            safe_log("DEBUG", "Fichier PNG détecté")
                            try:
                                with Image.open(file_path) as img:
                                    # Extraire les métadonnées textuelles PNG
                                    if hasattr(img, 'info'):
                                        png_info = img.info
                                        
                                        # Texte incorporé
                                        text_keys = ['Title', 'Author', 'Description', 'Copyright', 
                                                    'Creation Time', 'Software', 'Comment']
                                        png_text = {}
                                        for key in text_keys:
                                            if key in png_info:
                                                png_text[key] = png_info[key]
                                                safe_log("DEBUG", f"PNG {key}: {png_info[key]}")
                                        
                                        if png_text:
                                            image_info['png_text'] = png_text
                                        
                                        # Compression
                                        if 'compress_level' in png_info:
                                            image_info['png_compression'] = png_info['compress_level']
                                            safe_log("DEBUG", f"Niveau de compression PNG: {png_info['compress_level']}")
                                        
                                        # Gamma
                                        if 'gamma' in png_info:
                                            image_info['png_gamma'] = png_info['gamma']
                                            safe_log("DEBUG", f"Gamma PNG: {png_info['gamma']}")
                                        
                                        # Transparence
                                        if 'transparency' in png_info:
                                            image_info['has_transparency'] = True
                                            safe_log("DEBUG", "Transparence détectée dans le PNG")
                                    
                                    # Vérifier le type de PNG
                                    if img.mode == 'RGBA':
                                        image_info['png_type'] = 'RGBA (avec canal alpha)'
                                    elif img.mode == 'RGB':
                                        image_info['png_type'] = 'RGB (sans transparence)'
                                    elif img.mode == 'P':
                                        image_info['png_type'] = 'Palette indexée'
                                    else:
                                        image_info['png_type'] = img.mode
                                        
                                    safe_log("DEBUG", f"Type de PNG: {image_info['png_type']}")
                                    
                            except Exception as e:
                                safe_log("WARNING", f"Erreur lors de l'extraction des métadonnées PNG: {str(e)}")
                        
                        elif ext in ['.mp4', '.mov', '.avi']:
                            safe_log("DEBUG", "Fichier vidéo détecté")
                            try:
                                # Essayer d'utiliser ffprobe si disponible
                                import subprocess
                                import json
                                
                                try:
                                    # Commande ffprobe pour extraire les métadonnées
                                    cmd = [
                                        'ffprobe',
                                        '-v', 'quiet',
                                        '-print_format', 'json',
                                        '-show_format',
                                        '-show_streams',
                                        file_path
                                    ]
                                    
                                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                                    
                                    if result.returncode == 0:
                                        probe_data = json.loads(result.stdout)
                                        
                                        # Informations générales du format
                                        if 'format' in probe_data:
                                            format_info = probe_data['format']
                                            
                                            # Durée
                                            if 'duration' in format_info:
                                                duration = float(format_info['duration'])
                                                image_info['video_duration'] = duration
                                                image_info['video_duration_formatted'] = str(datetime.timedelta(seconds=int(duration)))
                                                safe_log("DEBUG", f"Durée vidéo: {image_info['video_duration_formatted']}")
                                            
                                            # Bitrate
                                            if 'bit_rate' in format_info:
                                                bitrate = int(format_info['bit_rate'])
                                                image_info['video_bitrate'] = bitrate
                                                image_info['video_bitrate_mbps'] = round(bitrate / 1000000, 2)
                                                safe_log("DEBUG", f"Bitrate vidéo: {image_info['video_bitrate_mbps']} Mbps")
                                            
                                            # Format
                                            if 'format_name' in format_info:
                                                image_info['video_format'] = format_info['format_name']
                                                safe_log("DEBUG", f"Format vidéo: {format_info['format_name']}")
                                        
                                        # Informations sur les flux
                                        if 'streams' in probe_data:
                                            for stream in probe_data['streams']:
                                                if stream.get('codec_type') == 'video':
                                                    # Codec vidéo
                                                    image_info['video_codec'] = stream.get('codec_name', 'inconnu')
                                                    safe_log("DEBUG", f"Codec vidéo: {image_info['video_codec']}")
                                                    
                                                    # Résolution
                                                    width = stream.get('width')
                                                    height = stream.get('height')
                                                    if width and height:
                                                        image_info['video_resolution'] = f"{width}x{height}"
                                                        image_info['dimensions'] = (width, height)
                                                        safe_log("DEBUG", f"Résolution vidéo: {width}x{height}")
                                                    
                                                    # Framerate
                                                    if 'r_frame_rate' in stream:
                                                        fps_str = stream['r_frame_rate']
                                                        try:
                                                            num, den = map(int, fps_str.split('/'))
                                                            fps = round(num / den, 2)
                                                            image_info['video_fps'] = fps
                                                            safe_log("DEBUG", f"Framerate: {fps} fps")
                                                        except:
                                                            pass
                                                    
                                                    # Rotation
                                                    if 'tags' in stream and 'rotate' in stream['tags']:
                                                        image_info['video_rotation'] = stream['tags']['rotate']
                                                        safe_log("DEBUG", f"Rotation vidéo: {stream['tags']['rotate']}°")
                                                    
                                                elif stream.get('codec_type') == 'audio':
                                                    # Codec audio
                                                    image_info['audio_codec'] = stream.get('codec_name', 'inconnu')
                                                    safe_log("DEBUG", f"Codec audio: {image_info['audio_codec']}")
                                                    
                                                    # Fréquence d'échantillonnage
                                                    if 'sample_rate' in stream:
                                                        image_info['audio_sample_rate'] = stream['sample_rate']
                                                        safe_log("DEBUG", f"Fréquence audio: {stream['sample_rate']} Hz")
                                        
                                        # Date de création pour les vidéos
                                        if 'format' in probe_data and 'tags' in probe_data['format']:
                                            tags = probe_data['format']['tags']
                                            
                                            # Chercher la date dans différents tags possibles
                                            date_tags = ['creation_time', 'date', 'datetime']
                                            for tag in date_tags:
                                                if tag in tags:
                                                    try:
                                                        # Parser la date ISO 8601
                                                        date_str = tags[tag]
                                                        video_date = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                                        image_info['video_creation_date'] = video_date
                                                        safe_log("DEBUG", f"Date de création vidéo: {video_date}")
                                                        
                                                        # Si pas de date extraite précédemment, utiliser celle-ci
                                                        if not image_info.get('date_taken'):
                                                            image_info['date_taken'] = video_date
                                                            image_info['date_origin'] = f"video_metadata:{tag}"
                                                        break
                                                    except:
                                                        pass
                                                        
                                except FileNotFoundError:
                                    safe_log("WARNING", "ffprobe non disponible, extraction vidéo limitée")
                                    # Fallback: extraire au moins la taille et l'extension
                                    image_info['video_format'] = ext[1:]  # Enlever le point
                                    
                                except subprocess.TimeoutExpired:
                                    safe_log("WARNING", "Timeout lors de l'analyse vidéo avec ffprobe")
                                    
                                except Exception as e:
                                    safe_log("WARNING", f"Erreur ffprobe: {str(e)}")
                                    
                            except Exception as e:
                                safe_log("WARNING", f"Erreur lors de l'extraction des métadonnées vidéo: {str(e)}")
                                
                    except Exception as e:
                        safe_log("WARNING", f"Erreur lors de l'analyse spécifique au format: {str(e)}")
                    
                    safe_log("DEBUG", "Extraction des métadonnées terminée avec succès")
                    
                except Exception as e:
                    safe_log("ERROR", f"Erreur globale lors de l'extraction des métadonnées: {str(e)}")
                    safe_log("ERROR", traceback.format_exc())
                    image_info = {
                        'file_path': file_path,
                        'filename': os.path.basename(file_path),
                        'error': str(e)
                    }

                end_time = datetime.datetime.now()
                duration = (end_time - start_time).total_seconds()
                safe_log("DEBUG", f"Temps total d'extraction des métadonnées: {duration:.3f} secondes")
                safe_log("DEBUG", f"Informations de l'image: {image_info}")
                print(f"DEBUG: Informations de l'image: {image_info}")
                
                # Construire le chemin de destination en fonction des critères
                current_path = target_dir
                safe_log("DEBUG", f"Chemin de base: {current_path}")
                
                # Organisation par date si demandée - UTILISER date_result AU LIEU DE date_from_filename
                if options.get('organize_by_date', False):
                    safe_log("INFO", "Organisation par date activée")
                    print("DEBUG: Organisation par date activée")
                    if date_result:  # Utiliser date_result au lieu de date_from_filename
                        date_str = date_result.strftime('%Y-%m-%d %H:%M:%S')
                        safe_log("DEBUG", f"Création du répertoire basé sur la date: {date_str}")
                        print(f"DEBUG: Création du répertoire basé sur la date: {date_str}")
                        date_dir = create_date_based_directory(current_path, date_result)
                        safe_log("DEBUG", f"Répertoire date créé: {date_dir}")
                        current_path = date_dir
                    else:
                        safe_log("WARNING", "Aucune date trouvée pour ce fichier")
                        print("DEBUG: Aucune date trouvée pour ce fichier")
                
                # Organisation par appareil si demandée
                if options.get('organize_by_camera', False):
                    safe_log("INFO", "Organisation par appareil activée")
                    print("DEBUG: Organisation par appareil activée")
                    
                    # Utiliser get_camera_info pour une extraction plus robuste
                    # Passer soit les données EXIF, soit le chemin du fichier
                    make, model = metadata.get_camera_info(
                        exif_data=exif_data if exif_data else {},
                        file_path=file_path,
                        format_output=True
                    )
                    
                    safe_log("DEBUG", f"Appareil photo: {make} {model}")
                    print(f"DEBUG: Appareil photo: {make} {model}")
                    
                    camera_dir = os.path.join(current_path, f"{make} {model}")
                    safe_log("DEBUG", f"Création du répertoire appareil: {camera_dir}")
                    ensure_dir_exists(camera_dir)
                    current_path = camera_dir
                
                # Organisation par localisation si demandée
                if options.get('organize_by_location', False):
                    safe_log("INFO", "Organisation par localisation activée")
                    print("DEBUG: Organisation par localisation activée")
                    if image_info.get('has_gps', False):
                        coords = image_info.get('gps_coordinates')
                        if coords:
                            safe_log("DEBUG", f"Coordonnées GPS trouvées: {coords}")
                            print(f"DEBUG: Coordonnées GPS trouvées: {coords}")
                            start_time = datetime.datetime.now()
                            location_name = get_location_name(coords[0], coords[1])
                            end_time = datetime.datetime.now()
                            duration = (end_time - start_time).total_seconds()
                            safe_log("DEBUG", f"Temps de géocodage: {duration:.3f} secondes")
                            safe_log("DEBUG", f"Nom de localisation: {location_name}")
                            print(f"DEBUG: Nom de localisation: {location_name}")
                            location_dir = os.path.join(current_path, location_name)
                            safe_log("DEBUG", f"Création du répertoire localisation: {location_dir}")
                            ensure_dir_exists(location_dir)
                            current_path = location_dir
                        else:
                            safe_log("WARNING", "Aucune coordonnée GPS trouvée")
                            print("DEBUG: Aucune coordonnée GPS trouvée")
                    else:
                        safe_log("WARNING", "Pas d'informations GPS disponibles")
                        print("DEBUG: Pas d'informations GPS disponibles")
                
                # Déterminer le chemin final
                dest_path = os.path.join(current_path, current_filename)
                safe_log("DEBUG", f"Chemin de destination initial: {dest_path}")
                print(f"DEBUG: Chemin de destination: {dest_path}")
                
                # Gérer les doublons
                if os.path.exists(dest_path):
                    safe_log("INFO", "Fichier en doublon détecté, génération d'un nouveau nom")
                    print("DEBUG: Gestion des doublons")
                    base_name, ext = os.path.splitext(current_filename)
                    counter = 1
                    while os.path.exists(dest_path):
                        new_filename = f"{base_name}_{counter}{ext}"
                        dest_path = os.path.join(current_path, new_filename)
                        counter += 1
                    safe_log("DEBUG", f"Nouveau nom de fichier pour éviter les doublons: {os.path.basename(dest_path)}")
                    print(f"DEBUG: Nouveau nom de fichier pour éviter les doublons: {os.path.basename(dest_path)}")
                
                # Copier ou déplacer le fichier
                if options.get('copy_not_move', True):
                    safe_log("INFO", "Mode copie activé")
                    print("DEBUG: Copie du fichier")
                    start_time = datetime.datetime.now()
                    success = copy_file(file_path, dest_path)
                    end_time = datetime.datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    safe_log("DEBUG", f"Temps de copie: {duration:.3f} secondes")
                else:
                    safe_log("INFO", "Mode déplacement activé")
                    print("DEBUG: Déplacement du fichier")
                    start_time = datetime.datetime.now()
                    success = move_file(file_path, dest_path)
                    end_time = datetime.datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    safe_log("DEBUG", f"Temps de déplacement: {duration:.3f} secondes")
                
                if success:
                    # Utiliser "->" au lieu de "→" pour éviter les problèmes d'encodage
                    safe_log("INFO", f"Succès: {os.path.basename(file_path)} -> {os.path.basename(dest_path)}")
                    print("DEBUG: Opération réussie")
                    results['processed'] += 1
                else:
                    error_msg = f"Erreur lors du traitement de {current_filename}"
                    safe_log("ERROR", error_msg)
                    print("DEBUG: Échec de l'opération")
                    results['errors'] += 1
                    results['results'].setdefault('errors', []).append(error_msg)
                
            except Exception as e:
                error_msg = f"Erreur lors du traitement du fichier {current_filename}: {str(e)}"
                safe_log("ERROR", error_msg)
                safe_log("ERROR", f"Détail de l'erreur: {traceback.format_exc()}")
                print(f"DEBUG: {error_msg}")
                results['errors'] += 1
                results['results'].setdefault('errors', []).append(error_msg)
        
        safe_log("INFO", "="*80)
        safe_log("INFO", f"FIN DE L'ORGANISATION - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        safe_log("INFO", f"Résumé - Total: {results['total']}, Traités: {results['processed']}, Erreurs: {results['errors']}")
        safe_log("INFO", "="*80)
        
        print("\nDEBUG: Fin du traitement de tous les fichiers")
        print(f"DEBUG: Résultats finaux: {results}")
        return results
        
    except Exception as e:
        error_msg = f"Erreur générale: {str(e)}"
        safe_log("CRITICAL", error_msg)
        safe_log("CRITICAL", f"Détail de l'erreur: {traceback.format_exc()}")
        print(f"DEBUG: {error_msg}")
        return {
            'total': len(file_paths),
            'processed': 0,
            'skipped': 0,
            'errors': len(file_paths),
            'results': {
                'errors': [error_msg]
            }
        }

def move_file(source, destination):
    """Moves a file with error handling for all formats."""
    try:
        # Ensure destination directory exists
        dest_dir = os.path.dirname(destination)
        ensure_dir_exists(dest_dir)
            
        # Use shutil.move for all file types for consistency
        shutil.move(source, destination)
        return True
    except Exception as e:
        print(f"Error moving file {source} to {destination}: {e}")
        return False

def list_files_by_extensions(directory, extensions, recursive=True):
    """Liste tous les fichiers avec les extensions spécifiées."""
    files = []
    
    if recursive:
        for root, _, file_names in os.walk(directory):
            for file in file_names:
                if any(file.lower().endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    files.append(full_path)
    else:
        for file in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, file)) and any(file.lower().endswith(ext) for ext in extensions):
                full_path = os.path.join(directory, file)
                files.append(full_path)
                
    return files

def list_image_files(directory, recursive=True, include_raw=True):
    """Liste tous les fichiers image dans un répertoire."""
    basic_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.heif', '.webp', '.tiff', '.tif',
                       '.svg', '.psd', '.xcf', '.jfif', '.jp2', '.jxr', '.avif', '.ico', '.eps', '.cgm', 
                       '.emf', '.wmf', '.pict', '.pcx']
    
    raw_extensions = ['.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.rw2', '.dng', '.3fr', '.ari',
                     '.bay', '.crw', '.dcr', '.erf', '.fff', '.iiq', '.k25', '.kdc', '.mef', '.mos',
                     '.mrw', '.nrw', '.pef', '.ptx', '.r3d', '.raf', '.rwl', '.sr2', '.srf', '.srw', 
                     '.x3f', '.drf', '.mdc', '.j6i', '.rwz', '.srw', '.x3f', '.kdc', '.mdc']
    
    extensions = basic_extensions + (raw_extensions if include_raw else [])
    return list_files_by_extensions(directory, extensions, recursive)

def create_date_based_directory(base_dir, date, format_type="year/month/day"):
    """
    Crée une structure de répertoires basée sur la date.
    
    Args:
        base_dir (str): Répertoire de base
        date (datetime): La date à utiliser
        format_type (str): Type de format de structure
            - "year/month/day" : 2024/03/15
            - "year/month" : 2024/03
            - "year" : 2024
            - "year_month" : 2024_03
            - "year_month_day" : 2024_03_15
            - "day_month_year" : 15_03_2024
            - "month_year" : 03_2024
    
    Returns:
        str: Chemin du répertoire créé
    """
    from utils.file_utils import ensure_dir_exists
    import os
    
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"
    
    # Créer la structure selon le format
    if format_type == "year/month/day":
        dest_dir = os.path.join(base_dir, year, month, f"{year}_{month}_{day}")
    elif format_type == "year/month":
        dest_dir = os.path.join(base_dir, year, f"{year}_{month}")
    elif format_type == "year":
        dest_dir = os.path.join(base_dir, year)
    elif format_type == "year_month":
        dest_dir = os.path.join(base_dir, f"{year}_{month}")
    elif format_type == "year_month_day":
        dest_dir = os.path.join(base_dir, f"{year}_{month}_{day}")
    elif format_type == "day_month_year":
        dest_dir = os.path.join(base_dir, f"{day}_{month}_{year}")
    elif format_type == "month_year":
        dest_dir = os.path.join(base_dir, f"{month}_{year}")
    else:  # Format par défaut
        dest_dir = os.path.join(base_dir, year, month, f"{year}_{month}_{day}")
    
    # Créer le répertoire et retourner son chemin
    ensure_dir_exists(dest_dir)
    return dest_dir

def group_files_by_location(files_input, max_distance_km=1.0):
    """
    Groupe les fichiers par proximité géographique.
    
    Args:
        files_input: Liste de chemins d'images OU liste de dictionnaires {file_path, date_taken}
        max_distance_km: Distance maximale en kilomètres pour considérer deux images comme
                        appartenant au même groupe
    
    Returns:
        dict: Dictionnaire avec les identifiants de lieu comme clés et les listes de chemins d'images comme valeurs
    """
    # Normaliser l'entrée
    if isinstance(files_input[0], str):
        # Convertir les chemins simples en dictionnaires
        file_info_list = [{'file_path': path} for path in files_input]
    else:
        file_info_list = files_input

    # Extraire les coordonnées GPS pour chaque fichier
    files_with_coords = []
    files_without_coords = []

    for file_info in file_info_list:
        file_path = file_info['file_path']
        coords = metadata.get_image_gps_coordinates(file_path)
        
        if coords[0] is not None and coords[1] is not None:
            files_with_coords.append({
                'file_path': file_path,
                'coords': coords
            })
        else:
            files_without_coords.append(file_path)
    
    # Si aucun fichier n'a de coordonnées, retourner un groupe unique
    if not files_with_coords:
        return {"sans_coordonnees_gps": files_without_coords}
    
    # Regrouper les fichiers par proximité
    location_groups = {}
    group_id = 0
    processed = set()
    
    for i, file_info in enumerate(files_with_coords):
        if file_info['file_path'] in processed:
            continue
        
        # Créer un nouveau groupe
        group_name = f"zone_{group_id}"
        group_id += 1
        
        current_group = [file_info['file_path']]
        processed.add(file_info['file_path'])
        
        # Trouver tous les fichiers proches de celui-ci
        for j, other_file in enumerate(files_with_coords):
            if other_file['file_path'] in processed:
                continue
                
            # Calculer la distance entre les deux points
            distance = metadata.calculate_distance(file_info['coords'], other_file['coords'])
            
            # Si la distance est inférieure au seuil, ajouter au groupe
            if distance <= max_distance_km:
                current_group.append(other_file['file_path'])
                processed.add(other_file['file_path'])
        
        # Enregistrer le groupe
        location_groups[group_name] = current_group
    
    # Ajouter les fichiers sans coordonnées dans un groupe séparé
    if files_without_coords:
        location_groups["sans_coordonnees_gps"] = files_without_coords
    
    return location_groups

def get_location_name(latitude, longitude, max_distance_km=1.0):
    """
    Tente d'obtenir un nom de lieu à partir de coordonnées GPS par reverse géocodage.
    
    Args:
        latitude: Latitude en degrés décimaux
        longitude: Longitude en degrés décimaux
        max_distance_km: Distance maximale en kilomètres pour regrouper les lieux
        
    Returns:
        str: Nom du lieu ou coordonnées formatées si le géocodage échoue
    """
    try:
        # Tentative d'utilisation de géocodage si la bibliothèque est disponible
        try:
            import requests
            
            # Utiliser le service de géocodage OpenStreetMap (Nominatim)
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=16&addressdetails=1"
            headers = {'User-Agent': 'ImageOrganizer/1.0'}
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Extraire les informations de localisation significatives
                if 'address' in data:
                    address = data['address']
                    components = []
                    
                    # Essayer de construire une hiérarchie significative : pays > ville > quartier
                    if 'country' in address:
                        components.append(address['country'])
                    
                    # Ajouter la ville/commune/village
                    for key in ['city', 'town', 'village']:
                        if key in address:
                            components.append(address[key])
                            break
                    
                    # Ajouter le quartier/banlieue
                    for key in ['district', 'suburb', 'neighbourhood']:
                        if key in address:
                            components.append(address[key])
                            break
                    
                    if components:
                        return " - ".join(components)
                
                # Utiliser display_name si les composants d'adresse n'ont pas pu être extraits
                if 'display_name' in data:
                    # Tronquer les noms longs
                    name = data['display_name']
                    if len(name) > 80:
                        name = name[:77] + "..."
                    return name
        except (ImportError, Exception) as e:
            print(f"Erreur de géocodage: {e}")
        
        # Formatage par défaut si le géocodage échoue
        return f"Lat_{latitude:.5f}_Lon_{longitude:.5f}"
    except Exception as e:
        print(f"Erreur lors de l'obtention du nom de lieu: {e}")
        return f"Lat_{latitude:.5f}_Lon_{longitude:.5f}"

def organize_by_location(files_input, destination_root, max_distance_km=1.0, copy_not_move=True, progress_callback=None):
    """
    Organise les fichiers par emplacement géographique.
    
    Args:
        files_input: Liste de chemins de fichiers
        destination_root: Répertoire de destination racine
        max_distance_km: Distance maximale en km pour considérer deux images comme du même lieu
        copy_not_move: Si True, copie les fichiers au lieu de les déplacer
        progress_callback: Fonction de rappel pour la progression
        
    Returns:
        dict: Statistiques sur l'organisation
    """
    from utils.file_utils import ensure_dir_exists, normalize_path
    # S'assurer que le répertoire de destination existe
    destination_root = normalize_path(destination_root)
    ensure_dir_exists(destination_root)

    # Normaliser les chemins de fichiers
    normalized_files = [normalize_path(f) for f in files_input]

    # Grouper les fichiers par localisation
    location_groups = group_files_by_location(normalized_files, max_distance_km)

    # Statistiques
    total_files = len(normalized_files)
    processed_files = 0
    skipped_files = 0
    error_files = 0

    # Traiter chaque groupe
    for group_name, file_paths in location_groups.items():
        try:
            # Déterminer le nom du répertoire
            if group_name != "sans_coordonnees_gps":
                # Prendre un fichier représentatif du groupe
                sample_file = file_paths[0]
                coords = metadata.get_image_gps_coordinates(sample_file)
                
                if coords[0] is not None and coords[1] is not None:
                    # Obtenir un nom de lieu basé sur les coordonnées
                    location_name = get_location_name(coords[0], coords[1])
                    
                    # Nettoyer le nom pour en faire un nom de dossier valide
                    import re
                    clean_name = re.sub(r'[<>:"/\\|?*]', '_', location_name)
                    clean_name = clean_name[:80]  # Limiter la longueur
                    
                    # Créer le répertoire de destination
                    target_dir = os.path.join(destination_root, clean_name)
                else:
                    target_dir = os.path.join(destination_root, group_name)
            else:
                target_dir = os.path.join(destination_root, "Sans coordonnées GPS")
            
            # Créer le répertoire cible
            ensure_dir_exists(target_dir)
            
            # Traiter chaque fichier du groupe
            for i, file_path in enumerate(file_paths):
                if progress_callback:
                    progress_callback(processed_files, total_files, f"Traitement de {os.path.basename(file_path)}")
                
                try:
                    # Déterminer le chemin de destination
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(target_dir, filename)
                    
                    # Vérifier si le fichier existe déjà
                    if os.path.exists(dest_path):
                        base, ext = os.path.splitext(filename)
                        dest_path = os.path.join(target_dir, f"{base}_{processed_files}{ext}")
                    
                    # Copier ou déplacer le fichier
                    if copy_not_move:
                        success = copy_file(file_path, dest_path)
                    else:
                        success = move_file(file_path, dest_path)
                    
                    if success:
                        processed_files += 1
                    else:
                        error_files += 1
                        
                except Exception as e:
                    print(f"Erreur lors du traitement du fichier {file_path}: {e}")
                    error_files += 1
                    
        except Exception as e:
            print(f"Erreur lors du traitement du groupe {group_name}: {e}")
            error_files += len(file_paths)
    
    # Retourner les statistiques
    return {
        'total': total_files,
        'processed': processed_files,
        'skipped': skipped_files,
        'errors': error_files
    }
