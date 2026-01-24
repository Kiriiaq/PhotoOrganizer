"""
Module de gestion des métadonnées.
Extraction EXIF, GPS, dates et informations appareil photo.
"""

from .exif_extractor import ExifExtractor, get_exif_data
from .gps_processor import GPSProcessor, get_gps_coordinates, calculate_distance
from .date_extractor import DateExtractor, extract_date
from .camera_detector import CameraDetector, get_camera_info

__all__ = [
    'ExifExtractor', 'get_exif_data',
    'GPSProcessor', 'get_gps_coordinates', 'calculate_distance',
    'DateExtractor', 'extract_date',
    'CameraDetector', 'get_camera_info'
]
