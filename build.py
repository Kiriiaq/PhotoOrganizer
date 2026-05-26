#!/usr/bin/env python3
"""Build PhotoOrganizer executable with PyInstaller.

Usage:
    python build.py                # Full build (release, no console, all libs)
    python build.py --debug        # Debug build (console, verbose logging)
    python build.py --light        # Release light (assumes Python + deps on host)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "PhotoOrganizer"


def _read_version() -> str:
    """Lit ``__version__`` depuis ``src/__init__.py`` (source de vérité unique).

    Évite le risque de désynchro entre ``build.py``, ``pyproject.toml`` et
    ``src/__init__.py`` qui a déjà été un bug historique (cf. AUDIT D-09).
    """
    init_path = Path(__file__).parent / "src" / "__init__.py"
    try:
        text = init_path.read_text(encoding="utf-8")
    except OSError:
        return "0.0.0-unknown"
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else "0.0.0-unknown"


VERSION = _read_version()
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
    # `yaml` est un import DUR dans src/config/duplicate_config.py:14 — sans
    # lui le simple chargement du module duplicate_manager casse au démarrage.
    "yaml",
    # `tkinterdnd2` (drag-and-drop) et `plyer` (toasts Windows) sont
    # optionnels au runtime mais on les bundle si présents dans l'env de
    # build. Si absents, le code retombe sur les fallbacks (try/except).
    "tkinterdnd2", "plyer", "plyer.platforms.win.notification",
    # `requests` est importé tardivement par gps_processor.get_location_name.
    # Même si le géocodage n'est plus exposé par l'IHM, `load_config_from_yaml`
    # peut activer location → on garde le module bundlé pour ne pas
    # provoquer un ImportError différé.
    "requests", "urllib3", "charset_normalizer", "idna",
    # `send2trash` et `tqdm` ont des fallbacks try/except → non listés ici.
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
    # blake3 n'est pas obligatoire (fallback hashlib dans duplicate_finder)
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


def build(*, light: bool = False, debug: bool = False, pro: bool = False) -> Path:
    """Build une variante de l'exécutable.

    - ``debug`` : ``--console --debug=all --log-level=DEBUG`` pour diagnostiquer
      au lancement. Inclut Pillow/HEIC pour ne pas s'auto-bloquer.
    - ``light`` : exclut les libs lourdes (cible : binaire min, suppose Python
      installé sur la machine cible — ou modules dynamiquement présents).
    - ``pro`` : inclut le package ``src/photoorganizer_pro`` et change le nom
      en ``PhotoOrganizerPro-X.Y.Z.exe``. À distribuer SÉPARÉMENT du build
      gratuit (les deux peuvent coexister sur la même machine).
    - défaut : release windowed (pas de console).

    Note Pro : ce script utilise le ``SECRET_KEY`` actuel de
    ``photoorganizer_pro/license/validator.py``. Pour un build de
    production, créer ``photoorganizer_pro/license/_secret.py`` (gitignored)
    avec ``SECRET_KEY = b"<vraie clé>"`` avant de lancer le build.
    """
    project_dir = Path(__file__).parent

    if debug:
        suffix = "-debug"
    elif light:
        suffix = "-light"
    else:
        suffix = ""

    base_name = f"{APP_NAME}Pro" if pro else APP_NAME
    output_name = f"{base_name}-{VERSION}{suffix}"
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

    # Bundle datas — whitelist explicite des sous-dossiers d'assets.
    # On ne bundle PAS `assets/tools/` (ExifTool Perl ~10 MB compressés) :
    # le fallback subprocess n'est plus utilisé (méthodes primaires
    # exifread / Pillow / pillow_heif suffisent), et la GPL d'ExifTool
    # est incompatible avec la distribution Pro propriétaire.
    # Si un utilisateur veut le fallback, il installe `exiftool` dans
    # le PATH (winget install exiftool), le code de détection le trouve.
    assets_icons = project_dir / "assets" / "icons"
    if assets_icons.exists():
        cmd.extend(["--add-data", f"{assets_icons}{os.pathsep}assets/icons"])
    for data_dir in ["resources", "src"]:
        src_path = project_dir / data_dir
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{os.pathsep}{data_dir}"])

    # tkinterdnd2 a besoin de ses binaires Tcl natifs (`tkdnd*.dll`) à côté
    # du module Python. PyInstaller ne les détecte pas automatiquement, on
    # les pousse explicitement dans le bundle pour que le drag-and-drop
    # fonctionne dans l'EXE final. Si la lib n'est pas installée, l'app
    # retombe gracieusement sans DnD (try/except dans organize_frame.py).
    try:
        import tkinterdnd2 as _tkdnd
        tkdnd_dir = os.path.join(_tkdnd.__path__[0], "tkdnd")
        if os.path.isdir(tkdnd_dir):
            cmd.extend([
                "--add-data",
                f"{tkdnd_dir}{os.pathsep}tkinterdnd2/tkdnd",
            ])
    except ImportError:
        pass

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
    parser.add_argument("--pro", action="store_true",
                        help="Build Pro edition (bundles src/photoorganizer_pro/, "
                             "renames output to PhotoOrganizerPro-X.Y.Z.exe). "
                             "PRE-REQ: replace SECRET_KEY in license/validator.py "
                             "via license/_secret.py (gitignored) before running.")
    parser.add_argument("--all", action="store_true",
                        help="Build debug + release (no light)")
    args = parser.parse_args()

    if args.all:
        build(debug=True)
        build()
    else:
        build(light=args.light, debug=args.debug, pro=args.pro)
