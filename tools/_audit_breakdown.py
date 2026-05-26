"""Décompose le contenu compressé de PhotoOrganizer-2.0.0.exe par catégorie."""
import re
from collections import defaultdict
from pathlib import Path

src = Path('/tmp/exe_full.txt') if Path('/tmp/exe_full.txt').exists() else Path(__file__).parent.parent / 'tools' / '_exe_listing.txt'
lines = src.read_text(encoding='utf-8', errors='replace').splitlines()

cats = defaultdict(lambda: [0, 0])
total = 0
unmatched = []
for line in lines:
    m = re.match(r"^\s*\d+,\s*(\d+),\s*\d+,\s*\d,\s*'.',\s*'([^']*)'", line)
    if not m:
        continue
    sz = int(m.group(1))
    name = m.group(2)
    total += sz
    n = name.replace('\\\\', '/').replace('\\', '/').lower()

    if 'exiftool' in n or 'perl532' in n or 'strawberry_perl' in n:
        cat = 'ExifTool (Perl)'
    elif n.startswith('pil/') or '/pil/' in n or n.startswith('pillow'):
        cat = 'Pillow (PIL)'
    elif 'customtkinter' in n:
        cat = 'customtkinter'
    elif 'tkinterdnd' in n:
        cat = 'tkinterdnd2'
    elif n.startswith('_tcl_data') or 'tcl86' in n or 'tk86' in n or '_tkinter' in n:
        cat = 'Tcl/Tk runtime'
    elif 'cryptography' in n or 'libcrypto' in n or 'libssl' in n:
        cat = 'cryptography / OpenSSL'
    elif 'requests' in n or 'urllib3' in n or 'charset_normalizer' in n or 'idna' in n or 'certifi' in n:
        cat = 'requests stack (HTTP)'
    elif 'chardet' in n:
        cat = 'chardet'
    elif 'pillow_heif' in n or 'libheif' in n or 'libde265' in n or 'libx265' in n:
        cat = 'pillow_heif + heif/x265/de265'
    elif n.startswith('yaml/') or 'pyyaml' in n or '/yaml/' in n:
        cat = 'PyYAML'
    elif 'exifread' in n:
        cat = 'exifread'
    elif 'piexif' in n:
        cat = 'piexif'
    elif 'plyer' in n:
        cat = 'plyer'
    elif 'darkdetect' in n:
        cat = 'darkdetect'
    elif 'send2trash' in n:
        cat = 'send2trash'
    elif n.startswith('python') or n.startswith('vcrun') or n.startswith('base_library'):
        cat = 'Python runtime'
    elif n == 'pyz.pyz' or n == "'pyz.pyz'":
        cat = 'PYZ (code projet + libs zip)'
    elif 'icon.png' in n or 'icon.ico' in n or 'assets/icons' in n or 'assets\\icons' in n:
        cat = 'Icons (projet)'
    else:
        cat = 'Autres (stdlib pyd, dll, dist-info)'
        if sz > 50000:
            unmatched.append((sz, name))
    cats[cat][0] += sz
    cats[cat][1] += 1

print(f"{'Catégorie':<38} {'Taille (MB)':>12} {'%':>7} {'Files':>6}")
print("-" * 70)
for name, (sz, n) in sorted(cats.items(), key=lambda x: -x[1][0]):
    pct = sz * 100 / total if total else 0
    print(f"{name:<38} {sz/1024/1024:>12.2f} {pct:>6.1f}% {n:>6}")
print("-" * 70)
print(f"{'TOTAL':<38} {total/1024/1024:>12.2f} {100.0:>6.1f}% {sum(v[1] for v in cats.values()):>6}")

if unmatched:
    print('\nTop unmatched > 50 KB:')
    for sz, name in sorted(unmatched, reverse=True)[:15]:
        print(f"  {sz/1024:>8.1f} KB  {name}")
