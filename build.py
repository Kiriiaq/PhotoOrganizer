#!/usr/bin/env python3
"""Build PhotoOrganizer executable with PyInstaller.

Usage:
    python build.py                # Full build (release, no console, all libs)
    python build.py --debug        # Debug build (console, verbose logging)
    python build.py --light        # Release light (assumes Python + deps on host)
"""

import subprocess
import sys
import os
import shutil
import argparse
from pathlib import Path

APP_NAME = "PhotoOrganizer"
VERSION = "2.0.0"
# L'icône réelle est dans resources/icons (cf. _install_icon dans ui/app.py)
ICON_CANDIDATES = [
    "resources/icons/icon.ico",
    "assets/icons/icon.ico",
    "src/ui/assets/icon.ico",
]

HIDDEN_IMPORTS = [
    "customtkinter", "darkdetect",
    "PIL", "PIL._imaging", "PIL._imagingft",
    "exifread", "piexif", "pillow_heif",
    "sqlite3", "_sqlite3",
    # `requests` retiré car le géocodage GPS n'est plus exposé par l'IHM ;
    # le module `gps_processor` reste mais ne se déclenche plus depuis l'UI.
    # `send2trash`/`yaml`/`tqdm` ne sont pas obligatoires : l'app a des
    # fallbacks (try/except ImportError) — ne pas les forcer pour ne pas
    # tirer leur coût d'extraction au démarrage.
]

# Modules à exclure même en build full : ne sont jamais utilisés et
# représentent plusieurs Mo de poids inutile dans le binaire onefile.
EXCLUDE_MODULES = [
    "scipy", "cv2", "dlib", "moviepy", "whisper", "oletools",
    "pandas", "numpy", "openpyxl", "fitz", "pymupdf",
    "docx", "pptx", "PyPDF2", "reportlab", "matplotlib", "seaborn", "win32com",
    # Ajouts pour réduire encore le binaire :
    "IPython", "jupyter", "notebook", "sphinx",
    "tornado", "zmq", "babel",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
    "pytz", "dateutil",
    # Géocodage retiré de l'IHM → on peut sortir requests/urllib3/charset_normalizer
    # qui pèsent ~1.5 Mo combinés.
    "requests", "urllib3", "charset_normalizer", "idna",
    # Ces deux-là n'apparaissent jamais à l'exécution
    "blake3",
]

# Exclusions stdlib + outils de développement
GLOBAL_EXCLUDES = [
    "unittest", "test", "tests", "pytest", "pydoc", "doctest",
    "lib2to3", "ensurepip", "venv", "distutils",
    "setuptools", "pkg_resources", "pip",
    "tkinter.test", "idlelib",
    "matplotlib.tests", "numpy.tests", "pandas.tests", "scipy.tests",
    # Réducteurs supplémentaires
    "asyncio.test_support", "concurrent.futures.process",
    "email.test", "html.parser", "xmlrpc",
    "ruff", "mypy", "vulture", "bandit",
]

# All heavy libs to strip in --light mode
ALL_HEAVY_LIBS = [
    "numpy", "pandas", "scipy", "cv2", "matplotlib", "seaborn",
    "pymupdf", "fitz", "reportlab", "shapely", "dlib",
    "moviepy", "whisper", "PIL", "Pillow",
    "docx", "pptx", "openpyxl", "xlrd", "xlsxwriter",
    "PyPDF2", "oletools", "win32com", "pythoncom", "pywintypes",
    "customtkinter", "darkdetect", "requests", "pydantic",
    "ollama", "rawpy", "imageio", "pillow_heif",
    "tqdm", "exifread", "piexif", "tinydb", "edge_tts",
    "flask", "aiohttp", "openai", "gtts", "praw", "bs4",
    "CTkMessagebox", "CTkToolTip", "easygui",
    "chardet", "unidecode", "send2trash", "yaml",
    "tomli", "tomli_w", "pdfplumber",
]


def _resolve_icon(project_dir: Path) -> Path | None:
    for rel in ICON_CANDIDATES:
        p = project_dir / rel
        if p.exists():
            return p
    return None


def build(*, light: bool = False, debug: bool = False) -> Path:
    """Build une variante de l'exécutable.

    - ``debug`` : ``--console --debug=all --log-level=DEBUG`` pour diagnostiquer
      au lancement. Inclut Pillow/HEIC pour ne pas s'auto-bloquer.
    - ``light`` : exclut les libs lourdes (cible : binaire min, suppose Python
      installé sur la machine cible — ou modules dynamiquement présents).
    - défaut : release windowed (pas de console).
    """
    project_dir = Path(__file__).parent

    if debug:
        suffix = "-debug"
    elif light:
        suffix = "-light"
    else:
        suffix = ""

    output_name = f"{APP_NAME}-{VERSION}{suffix}"
    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"

    # Clean build artifacts
    if build_dir.exists():
        shutil.rmtree(build_dir)
    for spec in project_dir.glob("*.spec"):
        spec.unlink()
    dist_dir.mkdir(exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", output_name,
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(project_dir),
        "--noconfirm",
    ]

    if debug:
        cmd.extend(["--console", "--debug=all", "--log-level=DEBUG"])
    else:
        # Release : pas de fenêtre console sous Windows + optimisations
        cmd.append("--windowed" if sys.platform == "win32" else "--console")
        # --optimize 2  : retire docstrings + assertions (bytecode plus petit
        #                 et chargement légèrement plus rapide)
        # --strip       : strip les symboles de debug des binaires natifs
        # UPX           : compression du runtime PyInstaller (-30 à -50 % en
        #                 général). On l'active si l'utilitaire est trouvé,
        #                 sinon `--noupx` pour éviter un warning bruyant.
        cmd.extend(["--optimize=2", "--strip"])
        if shutil.which("upx"):
            cmd.append("--upx-dir")
            cmd.append(str(Path(shutil.which("upx")).parent))
        else:
            cmd.append("--noupx")

    icon_path = _resolve_icon(project_dir)
    if icon_path:
        cmd.extend(["--icon", str(icon_path)])

    if light:
        keep = set(HIDDEN_IMPORTS)
        for mod in ALL_HEAVY_LIBS:
            if mod not in keep:
                cmd.extend(["--exclude-module", mod])
        for hi in HIDDEN_IMPORTS:
            cmd.extend(["--hidden-import", hi])
        for mod in GLOBAL_EXCLUDES:
            cmd.extend(["--exclude-module", mod])
    else:
        for hi in HIDDEN_IMPORTS:
            cmd.extend(["--hidden-import", hi])
        for mod in EXCLUDE_MODULES + GLOBAL_EXCLUDES:
            cmd.extend(["--exclude-module", mod])

    # Bundle assets/resources/src
    for data_dir in ["assets", "resources", "src"]:
        src_path = project_dir / data_dir
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{os.pathsep}{data_dir}"])

    cmd.append(str(project_dir / "main.py"))

    mode = "debug" if debug else ("light (no libs)" if light else "release")
    print(f"Building {output_name}.exe ({mode})...")
    result = subprocess.run(cmd, cwd=str(project_dir))

    # Cleanup
    if build_dir.exists():
        shutil.rmtree(build_dir)
    for spec in project_dir.glob("*.spec"):
        spec.unlink()

    exe = dist_dir / (f"{output_name}.exe" if sys.platform == "win32" else output_name)
    if result.returncode == 0 and exe.exists():
        size = exe.stat().st_size / (1024 * 1024)
        print(f"OK: {exe.name} ({size:.1f} MB)")
        return exe
    else:
        print("BUILD FAILED")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Build {APP_NAME}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--light", action="store_true",
                       help="Light build (no heavy libs, smaller binary)")
    group.add_argument("--debug", action="store_true",
                       help="Debug build (console + verbose logging)")
    parser.add_argument("--all", action="store_true",
                        help="Build debug + release (no light)")
    args = parser.parse_args()

    if args.all:
        build(debug=True)
        build()
    else:
        build(light=args.light, debug=args.debug)
