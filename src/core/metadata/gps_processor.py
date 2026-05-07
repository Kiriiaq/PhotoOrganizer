"""
Module de traitement des données GPS.
Extraction, conversion et géocodage inverse.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Tags GPS EXIF
GPS_TAGS = {
    0: "GPSVersionID", 1: "GPSLatitudeRef", 2: "GPSLatitude",
    3: "GPSLongitudeRef", 4: "GPSLongitude", 5: "GPSAltitudeRef",
    6: "GPSAltitude", 7: "GPSTimeStamp", 8: "GPSSatellites",
    9: "GPSStatus", 10: "GPSMeasureMode", 11: "GPSDOP",
    12: "GPSSpeedRef", 13: "GPSSpeed", 14: "GPSTrackRef",
    15: "GPSTrack", 16: "GPSImgDirectionRef", 17: "GPSImgDirection",
    18: "GPSMapDatum", 29: "GPSDateStamp"
}


class GPSProcessor:
    """Classe pour le traitement des données GPS."""

    def __init__(self, geocoding_enabled: bool = True, cache_size: int = 1000):
        """
        Initialise le processeur GPS.

        Args:
            geocoding_enabled: Activer le géocodage inverse
            cache_size: Taille du cache pour le géocodage
        """
        self.geocoding_enabled = geocoding_enabled
        self._location_cache: Dict[str, str] = {}
        self._cache_size = cache_size

    def extract_gps_data(self, exif_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrait les données GPS des métadonnées EXIF.

        Args:
            exif_data: Dictionnaire EXIF

        Returns:
            Dictionnaire des données GPS
        """
        if not exif_data:
            return {}

        gps_info = {}

        # Méthode 1: Tag GPSInfo
        if 'GPSInfo' in exif_data:
            gps_data = exif_data['GPSInfo']
            if isinstance(gps_data, dict):
                for key, value in gps_data.items():
                    tag_name = GPS_TAGS.get(key, str(key))
                    gps_info[tag_name] = value

        # Méthode 2: Tags GPS directs
        for tag_id, tag_name in GPS_TAGS.items():
            if tag_name in exif_data:
                gps_info[tag_name] = exif_data[tag_name]
            elif tag_id in exif_data:
                gps_info[tag_name] = exif_data[tag_id]

        return gps_info

    def get_coordinates(self, gps_info: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        """
        Convertit les données GPS en coordonnées décimales.

        Args:
            gps_info: Dictionnaire GPS

        Returns:
            Tuple (latitude, longitude) ou (None, None)
        """
        if not gps_info:
            return None, None

        try:
            # Extraire latitude
            lat_data = gps_info.get('GPSLatitude', gps_info.get(2))
            lat_ref = gps_info.get('GPSLatitudeRef', gps_info.get(1, 'N'))

            # Extraire longitude
            lon_data = gps_info.get('GPSLongitude', gps_info.get(4))
            lon_ref = gps_info.get('GPSLongitudeRef', gps_info.get(3, 'E'))

            if not lat_data or not lon_data:
                return None, None

            # Convertir en degrés décimaux
            lat = self._to_decimal(lat_data)
            lon = self._to_decimal(lon_data)

            if lat is None or lon is None:
                return None, None

            # Appliquer les références (N/S, E/W)
            if isinstance(lat_ref, str) and lat_ref.upper() == 'S':
                lat = -lat
            if isinstance(lon_ref, str) and lon_ref.upper() == 'W':
                lon = -lon

            # Valider les plages
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return round(lat, 6), round(lon, 6)

        except Exception as e:
            logger.debug(f"Erreur extraction coordonnées: {e}")

        return None, None

    def _to_decimal(self, value: Any) -> Optional[float]:
        """Convertit une valeur GPS en degrés décimaux.

        Formats supportés :
        - chaînes ``"48 deg 51' 24"`` (Pillow textual)
        - tuples ``(d, m, s)`` (Pillow IFDRational ou nombres)
        - tuples piexif rationnels ``((48,1), (51,1), (24,1))`` où chaque
          composante est elle-même un ``(numerator, denominator)``
        - objets exposant ``numerator`` / ``denominator`` (Pillow)
        - nombres directs
        """
        def _coerce(component: Any) -> float:
            """Tente de transformer un composant en float, en gérant :
            - tuples piexif rationnels ``(num, denom)``
            - chaînes ``'num/denom'`` (sérialisation EXIF abrégée)
            - objets numerator/denominator (Pillow IFDRational)
            - nombres directs
            """
            if isinstance(component, tuple) and len(component) == 2:
                num, denom = component
                return float(num) / float(denom) if float(denom) != 0 else 0.0
            if isinstance(component, str) and '/' in component:
                num_str, denom_str = component.split('/', 1)
                num = float(num_str.strip())
                denom = float(denom_str.strip())
                return num / denom if denom != 0 else 0.0
            if hasattr(component, 'numerator') and hasattr(component, 'denominator'):
                return float(component)
            return float(component)

        try:
            # Si c'est une chaîne, parser
            if isinstance(value, str):
                # Format "48 deg 51' 24.00""
                if 'deg' in value.lower():
                    parts = value.replace('deg', '').replace("'", '').replace('"', '').split()
                    if len(parts) >= 3:
                        return float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600
                # Format string "[48, 51, 24]" ou "[48.0, 51.0, 24.0]"
                # (sérialisation EXIF utilisée par get_exif_data)
                stripped = value.strip()
                if stripped.startswith('[') and stripped.endswith(']'):
                    inner = stripped[1:-1]
                    parts = [p.strip() for p in inner.split(',')]
                    if len(parts) >= 3:
                        d, m, s = (_coerce(p) for p in parts[:3])
                        return d + m / 60 + s / 3600
                # Essayer conversion directe
                return float(value)

            # Liste ou tuple [degrés, minutes, secondes]
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                d = _coerce(value[0])
                m = _coerce(value[1])
                s = _coerce(value[2])
                return d + m / 60 + s / 3600

            # Ratio Pillow IFDRational
            if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
                return float(value)

            return float(value)

        except (ValueError, TypeError, IndexError, ZeroDivisionError):
            return None

    def get_location_name(
        self,
        lat: float,
        lon: float,
        use_cache: bool = True
    ) -> str:
        """
        Obtient le nom d'un lieu par géocodage inverse.

        Args:
            lat: Latitude
            lon: Longitude
            use_cache: Utiliser le cache

        Returns:
            Nom du lieu ou coordonnées formatées
        """
        cache_key = f"{lat:.4f},{lon:.4f}"

        if use_cache and cache_key in self._location_cache:
            return self._location_cache[cache_key]

        if not self.geocoding_enabled:
            return self._format_coordinates(lat, lon)

        location_name = self._geocode_nominatim(lat, lon)

        if use_cache and len(self._location_cache) < self._cache_size:
            self._location_cache[cache_key] = location_name

        return location_name

    def _geocode_nominatim(self, lat: float, lon: float) -> str:
        """Géocodage via OpenStreetMap Nominatim."""
        try:
            import requests

            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 16,
                'addressdetails': 1
            }
            headers = {'User-Agent': 'PhotoOrganizer/2.0'}

            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()

                if 'address' in data:
                    address = data['address']
                    components = []

                    # Pays
                    if 'country' in address:
                        components.append(address['country'])

                    # Ville
                    for key in ['city', 'town', 'village', 'municipality']:
                        if key in address:
                            components.append(address[key])
                            break

                    # Quartier
                    for key in ['suburb', 'neighbourhood', 'district']:
                        if key in address:
                            components.append(address[key])
                            break

                    if components:
                        return ' - '.join(components)

                if 'display_name' in data:
                    name = data['display_name']
                    return name[:80] + '...' if len(name) > 80 else name

        except Exception as e:
            logger.debug(f"Géocodage échoué: {e}")

        return self._format_coordinates(lat, lon)

    def _format_coordinates(self, lat: float, lon: float) -> str:
        """Formate les coordonnées en nom de dossier."""
        return f"Lat_{lat:.4f}_Lon_{lon:.4f}"

    def generate_maps_link(self, lat: float, lon: float, zoom: int = 15) -> str:
        """Génère un lien Google Maps."""
        return f"https://www.google.com/maps?q={lat},{lon}&z={zoom}"

    def clear_cache(self):
        """Vide le cache de géocodage."""
        self._location_cache.clear()


def calculate_distance(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float]
) -> float:
    """
    Calcule la distance entre deux points GPS (formule de Haversine).

    Args:
        coord1: (latitude, longitude) premier point
        coord2: (latitude, longitude) deuxième point

    Returns:
        Distance en kilomètres
    """
    R = 6371.0  # Rayon de la Terre en km

    lat1 = math.radians(coord1[0])
    lon1 = math.radians(coord1[1])
    lat2 = math.radians(coord2[0])
    lon2 = math.radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def group_by_proximity(
    files_with_coords: List[Dict],
    max_distance_km: float = 1.0
) -> Dict[str, List[str]]:
    """
    Groupe les fichiers par proximité géographique.

    Args:
        files_with_coords: Liste de {'file_path': str, 'coords': (lat, lon)}
        max_distance_km: Distance maximale pour le regroupement

    Returns:
        Dictionnaire {zone_name: [file_paths]}
    """
    groups = {}
    processed = set()
    group_id = 0

    for i, file_info in enumerate(files_with_coords):
        file_path = file_info['file_path']
        if file_path in processed:
            continue

        coords = file_info.get('coords')
        if not coords or coords[0] is None:
            groups.setdefault('sans_gps', []).append(file_path)
            processed.add(file_path)
            continue

        # Nouveau groupe
        group_name = f"zone_{group_id}"
        group_id += 1
        current_group = [file_path]
        processed.add(file_path)

        # Trouver les fichiers proches
        for other in files_with_coords:
            other_path = other['file_path']
            if other_path in processed:
                continue

            other_coords = other.get('coords')
            if not other_coords or other_coords[0] is None:
                continue

            distance = calculate_distance(coords, other_coords)
            if distance <= max_distance_km:
                current_group.append(other_path)
                processed.add(other_path)

        groups[group_name] = current_group

    return groups


# Instance globale
_processor: Optional[GPSProcessor] = None


def get_processor() -> GPSProcessor:
    """Retourne l'instance globale du processeur GPS."""
    global _processor
    if _processor is None:
        _processor = GPSProcessor()
    return _processor


def get_gps_coordinates(file_path: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Fonction utilitaire pour obtenir les coordonnées GPS d'un fichier.

    Args:
        file_path: Chemin du fichier

    Returns:
        Tuple (latitude, longitude) ou (None, None)
    """
    from .exif_extractor import get_exif_data

    exif_data = get_exif_data(file_path)
    processor = get_processor()
    gps_info = processor.extract_gps_data(exif_data)
    return processor.get_coordinates(gps_info)
