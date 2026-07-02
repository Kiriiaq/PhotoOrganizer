# -*- coding: utf-8 -*-
"""Génère les 10 jeux de données d'entrée pour la qualification PhotoOrganizer.

Tous les inputs sont créés sous ``test_data/inputs/`` à partir de photos PIL
synthétiques (rapide, reproductible, EXIF maîtrisé via piexif).

Usage :
    python test_data/scripts/generate_inputs.py
    python test_data/scripts/generate_inputs.py --large  # input_volumineux à 1000
"""

import argparse
import os
import shutil
from datetime import datetime, timedelta

import piexif
from PIL import Image

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT_OUT = os.path.abspath(os.path.join(HERE, "..", "inputs"))


# -----------------------------------------------------------------------------
# Helpers de génération
# -----------------------------------------------------------------------------
def make_jpeg(path: str, size=(200, 150), color=None,
              date_taken: datetime = None,
              make: str = None, model: str = None,
              lat_lon: tuple = None,
              rating: int = None,
              keywords: list = None):
    """Crée une photo JPEG avec EXIF maîtrisé.

    Paramètres None → tag EXIF correspondant absent.
    """
    if color is None:
        color = (120, 150, 180)
    img = Image.new("RGB", size, color)

    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}}
    if make:
        exif_dict["0th"][piexif.ImageIFD.Make] = make.encode('utf-8')
    if model:
        exif_dict["0th"][piexif.ImageIFD.Model] = model.encode('utf-8')
    if date_taken:
        date_str = date_taken.strftime("%Y:%m:%d %H:%M:%S").encode('ascii')
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str
    if rating is not None:
        # Rating XMP n'est pas piexif natif → on utilise EXIF UserComment (best effort)
        # Pour les vrais tests rating EXIF, on utilise piexif.ImageIFD.Rating
        exif_dict["0th"][piexif.ImageIFD.Rating] = rating
    if keywords:
        # Keywords IPTC : on utilise XPKeywords UTF-16-LE format Windows
        kw_str = ';'.join(keywords)
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = (kw_str + '\x00').encode('utf-16-le')
    if lat_lon:
        lat, lon = lat_lon
        lat_ref = b'N' if lat >= 0 else b'S'
        lon_ref = b'E' if lon >= 0 else b'W'
        lat, lon = abs(lat), abs(lon)
        exif_dict["GPS"][piexif.GPSIFD.GPSVersionID] = (2, 0, 0, 0)
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_ref
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = _to_dms(lat)
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_ref
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = _to_dms(lon)

    try:
        exif_bytes = piexif.dump(exif_dict)
        img.save(path, "jpeg", exif=exif_bytes, quality=85)
    except Exception:
        img.save(path, "jpeg", quality=85)


def _to_dms(decimal: float) -> tuple:
    """Convertit en (deg/1, min/1, sec/1000)."""
    d = int(decimal)
    m_full = (decimal - d) * 60
    m = int(m_full)
    s = (m_full - m) * 60
    return ((d, 1), (m, 1), (int(s * 1000), 1000))


def safe_mkdir(path: str):
    """Crée le dossier ; vide-le s'il existe déjà (régénération propre)."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


# -----------------------------------------------------------------------------
# Jeux d'inputs
# -----------------------------------------------------------------------------
def gen_nominal():
    """50 photos avec EXIF date+camera variés (cas standard)."""
    out = os.path.join(ROOT_OUT, "input_nominal")
    safe_mkdir(out)
    cameras = [
        ("Sony", "ILCE-7M3"),
        ("Canon", "EOS R5"),
        ("Nikon", "Z6 II"),
        ("Apple", "iPhone 15 Pro"),
        ("Samsung", "Galaxy S23"),
    ]
    base_date = datetime(2024, 6, 1, 14, 0, 0)
    for i in range(50):
        d = base_date + timedelta(days=i, hours=i % 6, minutes=i * 3)
        make, model = cameras[i % len(cameras)]
        path = os.path.join(out, f"IMG_{i:04d}.jpg")
        make_jpeg(path, color=(50 + i*3 % 200, 100, 200 - i*2 % 100),
                  date_taken=d, make=make, model=model)
    print("  input_nominal : 50 photos")


def gen_vide():
    """Dossier vide."""
    out = os.path.join(ROOT_OUT, "input_vide")
    safe_mkdir(out)
    # Garde le dossier vide (pas de .gitkeep pour rester strict)
    print("  input_vide : dossier vide")


def gen_volumineux(count: int = 1000):
    """1000 photos pour les tests de volume / performance."""
    out = os.path.join(ROOT_OUT, "input_volumineux")
    safe_mkdir(out)
    base_date = datetime(2023, 1, 1)
    for i in range(count):
        d = base_date + timedelta(hours=i)
        path = os.path.join(out, f"photo_{i:05d}.jpg")
        make_jpeg(path, size=(100, 75),
                  color=((i * 17) % 256, (i * 31) % 256, (i * 53) % 256),
                  date_taken=d, make="Test", model="VolumeBench")
    print(f"  input_volumineux : {count} photos")


def gen_mauvais_format():
    """Fichiers de types non supportés : .txt, .pdf factice, .docx factice."""
    out = os.path.join(ROOT_OUT, "input_mauvais_format")
    safe_mkdir(out)
    with open(os.path.join(out, "notes.txt"), "w", encoding="utf-8") as f:
        f.write("Ceci n'est pas une photo.\nDocument texte arbitraire.\n")
    # PDF factice (juste les bytes header pour qu'il soit détecté)
    with open(os.path.join(out, "rapport.pdf"), "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"\x00" * 200)
    # DOCX (zip vide)
    with open(os.path.join(out, "memo.docx"), "wb") as f:
        f.write(b"PK\x03\x04" + b"\x00" * 100)
    # Une photo correcte pour valider que le filtre n'élimine pas tout
    make_jpeg(os.path.join(out, "valid_photo.jpg"),
              date_taken=datetime(2024, 6, 1))
    print("  input_mauvais_format : 4 fichiers (3 invalides + 1 jpg valide)")


def gen_caracteres_speciaux():
    """Photos avec noms contenant accents, emojis, symboles I&C (°, ±, μ, Ω)."""
    out = os.path.join(ROOT_OUT, "input_caracteres_speciaux")
    safe_mkdir(out)
    names = [
        "été_2024.jpg",
        "café ☕.jpg",
        "résolution±.jpg",
        "température_25°C.jpg",
        "impédance_μΩ.jpg",
        "photo_avec espaces.jpg",
        "🎉_anniversaire.jpg",
        "Réunion_n°7.jpg",
    ]
    base = datetime(2024, 7, 14, 12, 0)
    for i, name in enumerate(names):
        make_jpeg(os.path.join(out, name),
                  date_taken=base + timedelta(hours=i),
                  make="Test", model="UnicodeBench")
    print(f"  input_caracteres_speciaux : {len(names)} photos")


def gen_corrompu():
    """Photo JPG dont les 50% derniers octets ont été tronqués."""
    out = os.path.join(ROOT_OUT, "input_corrompu")
    safe_mkdir(out)
    # Crée une photo valide puis la tronque
    valid_path = os.path.join(out, "corrompu_tronque.jpg")
    make_jpeg(valid_path, size=(400, 300),
              date_taken=datetime(2024, 1, 1))
    size = os.path.getsize(valid_path)
    with open(valid_path, "rb") as f:
        data = f.read()
    # Tronque à 50%
    with open(valid_path, "wb") as f:
        f.write(data[: size // 2])
    # Photo vide (0 byte)
    open(os.path.join(out, "vide_0_byte.jpg"), "wb").close()
    # Photo valide pour comparaison
    make_jpeg(os.path.join(out, "intacte.jpg"),
              date_taken=datetime(2024, 1, 2))
    print("  input_corrompu : 3 fichiers (1 tronqué + 1 vide + 1 intact)")


def gen_gps_piexif():
    """5 photos avec coordonnées GPS encodées via piexif rationnels."""
    out = os.path.join(ROOT_OUT, "input_gps_piexif")
    safe_mkdir(out)
    locations = [
        ("paris", 48.8566, 2.3522),
        ("london", 51.5074, -0.1278),
        ("nyc", 40.7128, -74.0060),
        ("tokyo", 35.6762, 139.6503),
        ("sydney", -33.8688, 151.2093),
    ]
    base = datetime(2024, 5, 1)
    for i, (name, lat, lon) in enumerate(locations):
        make_jpeg(os.path.join(out, f"{name}.jpg"),
                  date_taken=base + timedelta(days=i),
                  make="Canon", model="EOS R5",
                  lat_lon=(lat, lon))
    print(f"  input_gps_piexif : {len(locations)} photos (Paris/London/NYC/Tokyo/Sydney)")


def gen_pairs():
    """10 paires RAW+JPEG (CR2 simulé par un fichier binaire)."""
    out = os.path.join(ROOT_OUT, "input_pairs")
    safe_mkdir(out)
    base = datetime(2024, 8, 15)
    for i in range(10):
        d = base + timedelta(hours=i)
        # JPEG
        make_jpeg(os.path.join(out, f"DSC_{i:04d}.jpg"),
                  date_taken=d, make="Canon", model="EOS R5")
        # CR2 factice (binaire avec en-tête approximatif)
        cr2_path = os.path.join(out, f"DSC_{i:04d}.cr2")
        with open(cr2_path, "wb") as f:
            f.write(b"II*\x00\x10\x00\x00\x00CR" + b"\x00" * 1000)
    print("  input_pairs : 20 fichiers (10 paires CR2+JPEG)")


def gen_bursts():
    """5 photos prises à 1 seconde d'écart (rafale)."""
    out = os.path.join(ROOT_OUT, "input_bursts")
    safe_mkdir(out)
    base = datetime(2024, 9, 1, 15, 0, 0)
    for i in range(5):
        d = base + timedelta(seconds=i)
        make_jpeg(os.path.join(out, f"BURST_{i:03d}.jpg"),
                  date_taken=d, make="Sony", model="ILCE-7M3")
    # Photo isolée plus tard
    make_jpeg(os.path.join(out, "BURST_isolee.jpg"),
              date_taken=base + timedelta(minutes=10),
              make="Sony", model="ILCE-7M3")
    print("  input_bursts : 6 fichiers (5 en rafale + 1 isolée)")


def gen_pas_exif():
    """3 photos sans aucune métadonnée EXIF.

    Qualification 2026-06-12 (ANO-Q1) : sans EXIF, l'organiseur retombe sur
    le **mtime** du fichier — qui n'est pas versionné par git et changeait à
    chaque régénération, rendant la référence T-079 non reproductible. On
    fige donc le mtime à une date fixe (2026-05-11 12:00, date de gel de la
    référence) pour rendre le scénario déterministe.
    """
    out = os.path.join(ROOT_OUT, "input_pas_exif")
    safe_mkdir(out)
    fixed_ts = datetime(2026, 5, 11, 12, 0, 0).timestamp()
    for i in range(3):
        path = os.path.join(out, f"sans_exif_{i:02d}.jpg")
        img = Image.new("RGB", (200, 150), (50 + i*30, 100, 200))
        img.save(path, "jpeg", quality=85)
        os.utime(path, (fixed_ts, fixed_ts))
    print("  input_pas_exif : 3 photos sans EXIF (mtime figé 2026-05-11)")


def gen_doublons():
    """20 photos dont 10 doublons exacts (mêmes octets)."""
    out = os.path.join(ROOT_OUT, "input_doublons")
    safe_mkdir(out)
    base = datetime(2024, 10, 1)
    # 10 photos uniques
    for i in range(10):
        d = base + timedelta(days=i)
        original_path = os.path.join(out, f"original_{i:02d}.jpg")
        make_jpeg(original_path, size=(300, 200),
                  color=(i * 25 % 256, 100 + i * 7, 200 - i * 10),
                  date_taken=d, make="Canon", model="EOS R5")
        # Copie exacte pour faire le doublon
        shutil.copy(original_path,
                    os.path.join(out, f"dup_{i:02d}_copy.jpg"))
    print("  input_doublons : 20 fichiers (10 originaux + 10 doublons exacts)")


def gen_keywords():
    """5 photos avec mots-clés EXIF variés."""
    out = os.path.join(ROOT_OUT, "input_keywords")
    safe_mkdir(out)
    samples = [
        ("vacances_mer.jpg", ["vacances", "mer", "été"]),
        ("mariage_pierre.jpg", ["mariage", "famille"]),
        ("anniversaire.jpg", ["anniversaire", "famille"]),
        ("travail_meeting.jpg", ["travail", "conférence"]),
        ("randonnee.jpg", ["sport", "montagne"]),
    ]
    base = datetime(2024, 11, 1)
    for i, (name, kws) in enumerate(samples):
        make_jpeg(os.path.join(out, name),
                  date_taken=base + timedelta(days=i),
                  make="Sony", model="ILCE-7M3",
                  keywords=kws)
    print(f"  input_keywords : {len(samples)} photos avec mots-clés")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--large", type=int, default=1000,
                        help="Nombre de photos dans input_volumineux (défaut 1000)")
    parser.add_argument("--skip-large", action="store_true",
                        help="Ne pas générer input_volumineux (gain de temps)")
    args = parser.parse_args()

    print("=== Génération des inputs PhotoOrganizer QA ===")
    print(f"Cible : {ROOT_OUT}\n")

    gen_nominal()
    gen_vide()
    gen_mauvais_format()
    gen_caracteres_speciaux()
    gen_corrompu()
    gen_gps_piexif()
    gen_pairs()
    gen_bursts()
    gen_pas_exif()
    gen_doublons()
    gen_keywords()

    if not args.skip_large:
        gen_volumineux(args.large)
    else:
        print("  input_volumineux : SKIPPED (--skip-large)")

    print(f"\n=== Inputs générés sous {ROOT_OUT} ===")


if __name__ == "__main__":
    main()
