---
project: PhotoOrganizer
version: 2.0.0
audit_date: 2026-05-19
auditor: audit-pyinstaller-customtkinter
exe_path: dist/PhotoOrganizer-2.0.0.exe
size_initial_mb: 37.06
size_target_mb: 22.0
gain_estimated_mb: 15.0
gain_estimated_pct: 40
methodology: pyi-archive_viewer + ruff F401/F841 + grep imports réels + mesure site-packages
---

# Audit d'optimisation `.exe` — PhotoOrganizer v2.0.0

> Mémoire long-terme pour Claude Code. Mise à jour à chaque action appliquée.
> Ne JAMAIS modifier l'UX, le comportement visible, l'arborescence des écrans.
> Toute optimisation doit rester réversible.

## 1. Synthèse

### Mesure actuelle
- **`.exe` : 37.06 MB** (`dist/PhotoOrganizer-2.0.0.exe`, build `--onefile`)
- **Contenu archive PyInstaller : 34.94 MB compressé** (1 721 fichiers)
- Delta 2.12 MB = runtime stub PyInstaller (bootloader + métadata)

### Décomposition par catégorie (compressé, sur 34.94 MB)
| # | Catégorie | MB | % | Fichiers |
|---|---|---:|---:|---:|
| 1 | **ExifTool (Perl bundle)** | 10.31 | 29.5 % | 508 |
| 2 | cryptography / OpenSSL | 4.19 | 12.0 % | 14 |
| 3 | Autres (stdlib `.pyd`, dll, dist-info) | 3.81 | 10.9 % | 241 |
| 4 | Pillow (PIL) | 3.55 | 10.2 % | 7 |
| 5 | PYZ (code projet + libs zip) | 3.47 | 9.9 % | 1 |
| 6 | pillow_heif + libheif/x265/de265 | 2.95 | 8.4 % | 4 |
| 7 | Tcl/Tk runtime | 2.05 | 5.9 % | 834 |
| 8 | Python runtime | 2.03 | 5.8 % | 4 |
| 9 | Icons projet (`assets/icons`) | 0.93 | 2.7 % | 2 |
| 10 | chardet | 0.82 | 2.3 % | 25 |
| 11 | tkinterdnd2 | 0.43 | 1.2 % | 67 |
| 12 | customtkinter | 0.19 | 0.5 % | 9 |
| 13 | requests stack (HTTP) | 0.14 | 0.4 % | 4 |
| 14 | PyYAML | 0.09 | 0.2 % | 1 |

### Top 5 actions à impact maximal
| Rang | Action | Gain MB | Effort | Risque | ID |
|---:|---|---:|---|---|---|
| 1 | Exclure entièrement `assets/tools/` (ExifTool Perl) du bundle | ~10.3 | Faible | Moyen (fallback métadonnées) | [F-01](#f-01) |
| 2 | Construire dans un venv minimal isolé | ~5–6 | Faible | Nul | [F-02](#f-02) |
| 3 | Passer `pillow-heif` → `pi-heif` (HEVC read-only, sans libx265) | ~2.3 | Faible | Faible | [F-03](#f-03) |
| 4 | Exclure `PIL._avif` **par `--exclude-module`** (Option B ; le pin `Pillow<12` est ABANDONNÉ — CVE, cf. F-04) | ~1.8 | Faible | Faible (rare) | [F-04](#f-04) |
| 5 | Recompresser `assets/icons/icon.png` (945 KB → ~80 KB) | ~0.85 | Trivial | Nul | [F-05](#f-05) |

**Gain total estimé** : **~15 MB → cible 22 MB (−40 %)**.

---

## 2. Mesure de référence (détails)

### Top 20 fichiers les plus lourds dans l'exe (compressé)
| # | Taille | Fichier |
|---|---:|---|
| 1 | 3 555 KB | `PYZ.pyz` (bytecode projet + libs Python pures) |
| 2 | 2 583 KB | `cryptography\hazmat\bindings\_rust.pyd` |
| 3 | 2 314 KB | `libx265-215-…dll` (encoder HEVC) |
| 4 | 1 874 KB | `assets\tools\exiftool_files\lib\Image\ExifTool\Geolocation.dat` |
| 5 | 1 788 KB | `PIL\_avif.cp311-win_amd64.pyd` (décoder AVIF) |
| 6 | 1 636 KB | `python311.dll` |
| 7 | 1 486 KB | `libcrypto-3.dll` (OpenSSL) |
| 8 | 916 KB | `assets\icons\icon.png` |
| 9 | 821 KB | `perl532.dll` (×2 — une copie aussi dans `exiftool_files\`) |
| 10 | 785 KB | `PIL\_imaging.cp311-win_amd64.pyd` |
| 11 | 772 KB | `PIL\_imagingft.cp311-win_amd64.pyd` |
| 12 | 657 KB | `tcl86t.dll` |
| 13 | 632 KB | `sqlite3.dll` |
| 14 | 619 KB | `libstdc++-6-…dll` (×2) |
| 15 | 555 KB | `tk86t.dll` |
| 16 | 511 KB | `chardet\models\models.bin` |
| 17 | 505 KB | `libheif-…dll` |
| 18 | 429 KB | `assets\tools\exiftool_files\Licenses_Strawberry_Perl.zip` |
| 19 | 358 KB | `base_library.zip` (Python stdlib core) |
| 20 | 309 KB | `assets\tools\exiftool_files\lib\Image\ExifTool\TagNames.pod` |

### Commandes de reproduction
```bash
# 1) Lister l'exe
python -m PyInstaller.utils.cliutils.archive_viewer -l dist/PhotoOrganizer-2.0.0.exe > exe_listing.txt

# 2) Décomposition par catégorie (script fourni)
python tools/_audit_breakdown.py
```

---

## 3. Findings détaillés

### Phase 1 — Code source & imports

### [F-06] Imports morts détectés par ruff
**Statut**: ⬜ à faire  **Sévérité**: 🟢 faible  **Gain**: <50 KB
**Fichiers**:
- `src/core/operations/duplicate_manager.py:36` — `from send2trash import send2trash` (jamais appelé directement, c'est la sentinelle `TRASH_AVAILABLE` qui sert ; OK à garder mais flag `# noqa: F401`)
- `src/core/operations/quarantine.py:41` — `field` importé mais inutilisé
- `src/main.py:25` — `import customtkinter` pour test de disponibilité (déplacer en `importlib.util.find_spec`)
- 16 autres warnings F401/F841 (cf. `ruff check src/ --select F401,F841`)

**Action**:
```bash
ruff check src/ --select F401,F841 --fix
# Puis revoir les "noqa" manuels pour les sentinelles try/except
```
**Risque**: Nul si on garde les imports try/except (sentinelles de disponibilité).
**Pourquoi limité**: Le PYZ ne fait que 3.55 MB ; le bytecode projet est ~0.5 MB. Le gain est marginal.

---

### [F-07] `piexif` listé en hidden import mais JAMAIS importé
**Statut**: ⬜ à faire  **Sévérité**: 🟡 moyen  **Gain**: ~160 KB (raw) → ~50 KB compressé
**Fichier**: `build.py:29`, `requirements.txt:11`, `pyproject.toml:19`

Le code ne contient aucun `import piexif`. Seules deux mentions en docstring dans `gps_processor.py`.

**Avant**:
```python
# build.py
HIDDEN_IMPORTS = [..., "piexif", ...]
# requirements.txt
piexif>=1.1.3
# pyproject.toml
"piexif>=1.1.3,<2.0.0",
```
**Après**:
```python
# build.py — retirer "piexif" de HIDDEN_IMPORTS
# requirements.txt — retirer la ligne piexif
# pyproject.toml — retirer la ligne piexif
```
**Risque**: Vérifier qu'aucune extension d'image écrite ne nécessite piexif (recherche `grep -rE "piexif\." src/`). Actuellement zéro résultat → sûr.

---

### [F-08] `requests` utilisé pour 1 seul GET HTTP → remplaçable par `urllib.request` (stdlib)
**Statut**: ⬜ à faire  **Sévérité**: 🟡 moyen  **Gain**: ~140 KB requests stack + libère cryptography si seule cause (cf. [F-09])
**Fichier**: `src/core/metadata/gps_processor.py:216-266`

Le seul appel HTTP du projet est un GET vers Nominatim avec params + headers User-Agent + timeout=5. Trivialement remplaçable :

**Avant**:
```python
import requests
url = "https://nominatim.openstreetmap.org/reverse"
params = {'format':'json','lat':lat,'lon':lon,'zoom':16,'addressdetails':1}
headers = {'User-Agent': 'PhotoOrganizer/2.0'}
response = requests.get(url, params=params, headers=headers, timeout=5)
if response.status_code == 200:
    data = response.json()
```
**Après**:
```python
import json
import urllib.parse
import urllib.request

url = "https://nominatim.openstreetmap.org/reverse"
params = {'format':'json','lat':lat,'lon':lon,'zoom':16,'addressdetails':1}
full_url = f"{url}?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(full_url, headers={'User-Agent': 'PhotoOrganizer/2.0'})
try:
    with urllib.request.urlopen(req, timeout=5) as response:
        if response.status == 200:
            data = json.loads(response.read().decode('utf-8'))
        else:
            data = None
except Exception as e:
    logger.debug(f"Géocodage échoué: {e}")
    data = None
```
Puis :
```python
# build.py — retirer requests, urllib3, charset_normalizer, idna des HIDDEN_IMPORTS
# pyproject.toml + requirements.txt — retirer requests
```
**Risque**: TLS via stdlib `ssl` est suffisant pour OpenStreetMap (HTTPS). Pas de retry, mais le code actuel n'en a pas non plus.

---

### Phase 2 — Dépendances effectives

### [F-01] ExifTool bundle Perl (10.31 MB) — fallback non opérationnel
**Statut**: ⬜ à faire  **Sévérité**: 🔴 fort  **Gain**: ~10.3 MB compressé
**Fichiers**: `assets/tools/exiftool.exe` + `assets/tools/exiftool_files/**` (507 fichiers, 34 MB sur disque)

`ExifTool` est invoqué comme **fallback subprocess** uniquement dans `_try_exiftool()` (`src/core/metadata/exif_extractor.py:299`). Or :

1. Le code cherche le binaire à `assets/exiftool.exe` (sans `tools/`) — chemin **incorrect** depuis le packaging actuel.
2. Les méthodes primaires (`exifread`, `Pillow`, `pillow_heif`) couvrent JPEG/PNG/HEIC/RAW/vidéos pour les métadonnées essentielles (Make, Model, DateTime, GPS).
3. ExifTool n'est jamais effectivement déclenché en pratique (sauf si l'utilisateur a `exiftool` dans le PATH système).

**Avant** (`build.py:176-179`):
```python
for data_dir in ["assets", "resources", "src"]:
    src_path = project_dir / data_dir
    if src_path.exists():
        cmd.extend(["--add-data", f"{src_path}{os.pathsep}{data_dir}"])
```
Ce code embarque **toute** `assets/`, donc `assets/tools/` (= ExifTool).

**Après** — embarquer uniquement `assets/icons/` :
```python
# Whitelist explicite des sous-dossiers d'assets à bundler
ASSETS_INCLUDE = ["icons"]  # tools/ exclu (ExifTool fallback - 10 MB compressés)
for sub in ASSETS_INCLUDE:
    src_path = project_dir / "assets" / sub
    if src_path.exists():
        cmd.extend(["--add-data", f"{src_path}{os.pathsep}assets/{sub}"])
for data_dir in ["resources", "src"]:
    src_path = project_dir / data_dir
    if src_path.exists():
        cmd.extend(["--add-data", f"{src_path}{os.pathsep}{data_dir}"])
```

**Atténuation du risque** (= conserver le fallback sans le bundler) :
- Documenter dans le README qu'ExifTool est optionnel : si présent dans PATH ou installé via `winget install exiftool`, il sera détecté.
- Le code de détection (`_find_exiftool`) gère déjà l'absence (return None).

**Gain estimé**: ~10.3 MB compressé → exe passe de 37 → ~27 MB.
**Risque**: Perte du fallback pour quelques fichiers exotiques (DNG ancien, MOV propriétaires). Mais le chemin actuel est cassé donc personne ne l'a jamais utilisé.

---

### [F-09] `cryptography` (4.19 MB) embarqué mais non utilisé par le projet
**Statut**: ⬜ à faire  **Sévérité**: 🔴 fort  **Gain**: ~4.2 MB compressé
**Origine**: PyInstaller runtime hook `pyi_rth_cryptography_openssl` détecté à la phase Analysis car le venv de build contient `cryptography 48.0.0` installé globalement (tiré par `msoffcrypto-tool`, `pdfminer.six`, etc., hors PhotoOrganizer).

`grep -rE "import cryptography|from cryptography" src/` → **zéro match**.
`pip show cryptography` → `Required-by: msoffcrypto-tool, pdfminer.six, pyAesCrypt` (pas requests, pas urllib3).

**Action** (combine avec [F-02] venv minimal) :
```python
# build.py — ajouter dans EXCLUDE_MODULES
EXCLUDE_MODULES = [..., "cryptography", "cffi", "_cffi_backend"]
```
**Risque**: Vérifier que `urllib.request.urlopen` HTTPS fonctionne sans cryptography (= utilise `ssl` stdlib, OK). Si on garde `requests` ([F-08] non appliqué), urllib3≥2 peut tenter d'utiliser cryptography pour SecureTransport mais retombe sur ssl si absent.

---

### [F-10] `chardet` (823 KB) tiré inutilement
**Statut**: ⬜ à faire  **Sévérité**: 🟡 moyen  **Gain**: ~820 KB compressé
**Origine**: probablement tiré par `requests` (qui dépend de `charset_normalizer` OU `chardet`). Aucun import direct dans `src/`.

**Action**:
```python
# build.py
EXCLUDE_MODULES = [..., "chardet"]
```
**Risque**: Faible. Combiné à [F-08] (replace requests → urllib), le besoin disparaît totalement.

---

### Phase 3 — Assets

### [F-05] `assets/icons/icon.png` = 945 KB (sur-poids x10)
**Statut**: ⬜ à faire  **Sévérité**: 🟡 moyen  **Gain**: ~850 KB raw → ~800 KB compressé
**Fichier**: `assets/icons/icon.png` (~969 KB sur disque, 945 KB compressé dans exe)

Un PNG d'icône d'application devrait peser 30-100 KB max. La compression actuelle est défavorable (probablement non passée par un optimizer).

**Action** (réversible — garder l'original en `.orig`) :
```bash
# Avec pngquant (256 couleurs, qualité 80-95%) :
pngquant --quality=80-95 --strip --skip-if-larger \
  --output assets/icons/icon.optimized.png assets/icons/icon.png

# Ou avec oxipng (lossless mais agressif) :
oxipng -o max --strip safe assets/icons/icon.png
```
Cible : 80-150 KB sans perte visible.

**Risque**: Visuellement identique à 95% de qualité (icône d'app).

---

### [F-11] Assets CustomTkinter — fichiers `.DS_Store` macOS
**Statut**: ⬜ à faire  **Sévérité**: 🟢 faible  **Gain**: ~12 KB
**Origine**: `customtkinter/assets/.DS_Store` et `customtkinter/assets/icons/.DS_Store` (6 KB chacun) embarqués automatiquement.

**Action** — ajouter au build via post-Analysis hook ou exclusion :
```python
# build.py — datas filtering (nécessite passage en .spec mode)
# Plus simple : exclure customtkinter de l'auto-collecte des datas et re-add propre
```
**Pourquoi limité**: Gain négligeable, mais propre.

---

### [F-12] Thèmes CustomTkinter inutilisés
**Statut**: ⬜ à faire  **Sévérité**: 🟢 faible  **Gain**: ~9 KB
L'app utilise `set_default_color_theme("blue")` (ui/app.py:62) en dur → `dark-blue.json` (4.4 KB) et `green.json` (4.4 KB) sont morts dans le bundle.

**Action**: Custom hook PyInstaller `hook-customtkinter.py` qui retire les thèmes non utilisés. Effort > bénéfice.

---

### Phase 4 — PyInstaller / build.py

### [F-04] `PIL._avif` (1.79 MB compressé) non requis
**Statut**: ⬜ à faire (Option B uniquement)  **Sévérité**: 🔴 fort  **Gain**: ~1.8 MB compressé
**Origine**: Pillow 12+ embarque `_avif.cp311-win_amd64.pyd` (7.7 MB raw, 1.8 MB compressé).

Le projet liste `.avif` comme extension scannée (`exif_extractor.py:39`), mais l'extraction métadonnées passe par `exifread` ou `PIL.Image.open()`. AVIF métadata est rarissime dans l'usage cible (photo de smartphone JPEG/HEIC).

> ⚠️ **MàJ 2026-07-05 — l'Option A (pin `Pillow<12`) est ABANDONNÉE.**
> Pillow 11.3.0 porte **7 CVE** signalées par `pip-audit --strict` (job
> `audit` de la CI, corrigées en 12.2.0). La contrainte du projet a été
> **montée à `Pillow>=12.2.0,<13`** (commit `d633a77`). On accepte donc les
> ~1.8 MB de `_avif` : **la sécurité prime sur la taille**. Le gain de F-04
> ne reste atteignable que via l'Option B (exclusion du module au build),
> qui **conserve Pillow ≥ 12.2**.

**~~Option A — pin Pillow < 12~~ (ABANDONNÉE, cf. encart ci-dessus)** :
```
# NE PLUS FAIRE — réintroduirait 7 CVE (job audit CI en échec).
# Pillow>=10.0.0,<12.0.0
```
**Option B — exclure le module** (seule voie retenue ; Pillow charge `_avif` dynamiquement, donc à tester) :
```python
# build.py
EXCLUDE_MODULES = [..., "PIL._avif"]
```
**Risque**: Aucun pour l'usage standard. Si un utilisateur tente d'organiser des `.avif`, ils seront détectés (extension dans la liste) mais sans métadonnées EXIF profondes — le fallback `_extract_basic` extrait au moins FileName/FileSize/FileModifyDate.

---

### [F-03] `pillow_heif` → `pi_heif` (read-only, sans libx265)
**Statut**: ⬜ à faire  **Sévérité**: 🔴 fort  **Gain**: ~2.3 MB compressé (libx265-215-…dll = 2.31 MB)
**Origine**: `pillow_heif 1.3.0` embarque automatiquement libx265 (encodeur HEVC), même si le projet ne fait que **lire** des HEIC.

`pi_heif` est le sister-package read-only maintenu par le même auteur : <https://github.com/bigcat88/pillow_heif>. Il fournit la même API `register_heif_opener()` mais sans libx265.

**Avant**:
```
# requirements.txt
pillow-heif>=0.13.0
```
**Après**:
```
# requirements.txt
pi-heif>=0.20.0
```
Code source — aucune modification nécessaire :
```python
# src/core/metadata/exif_extractor.py:27
from pillow_heif import register_heif_opener  # FONCTIONNE TOUJOURS via pi_heif
```
> `pi_heif` expose le même nom de module top-level `pillow_heif` pour compatibilité. À confirmer sur la doc upstream avant d'appliquer.

**Risque**: Faible — l'app n'écrit jamais de HEIC.

---

### [F-13] `--onefile` vs `--onedir` — trade-off
**Statut**: ⬜ décision humaine  **Sévérité**: 🟡 moyen  **Gain**: ~5-8 MB sur certains setups + démarrage 5-10x plus rapide
`--onefile` décompresse le bundle dans `%TEMP%\_MEIxxxxx\` à chaque lancement (1-3 s sur HDD/Defender). Le binaire est compressé par PyInstaller (zlib + UPX si dispo).

`--onedir` produit un dossier `dist/PhotoOrganizer-2.0.0/` avec `PhotoOrganizer-2.0.0.exe` + tous les fichiers à plat. Plus gros sur disque (~50-60 MB total), mais :
- Démarrage instantané
- Pas de décompression
- Patch incrémental possible (mise à jour fichier par fichier)

**Décision** : à confirmer avec l'utilisateur selon contraintes de distribution (.exe portable mono-fichier vs dossier zippé).

---

### [F-14] UPX désactivé (`--noupx`)
**Statut**: ⬜ à faire  **Sévérité**: 🟡 moyen  **Gain**: ~3-5 MB compressé
**Origine**: `build.py:153` fallback `--noupx` quand `shutil.which("upx")` retourne None.

UPX (`https://upx.github.io/`) compresse les DLL/PYD natifs de 30-60 %. Combiné à `--lzma`, gain typique sur cet exe : 5-7 MB.

**Action**:
1. Installer UPX : `winget install upx-project.upx` ou télécharger depuis github.com/upx/upx/releases.
2. Mettre `upx.exe` dans `tools/upx/` du projet (versionné ou via script `install_upx.ps1`).
3. Modifier `build.py:150-154` :
```python
upx_dir = project_dir / "tools" / "upx"
upx_bin = upx_dir / "upx.exe"
if upx_bin.exists():
    cmd.extend(["--upx-dir", str(upx_dir)])
    # Exclure les DLL connues pour casser sous UPX (Qt, tcl/tk parfois)
    for excl in ["vcruntime140.dll", "python311.dll", "tcl86t.dll", "tk86t.dll"]:
        cmd.extend(["--upx-exclude", excl])
elif shutil.which("upx"):
    cmd.extend(["--upx-dir", str(Path(shutil.which("upx")).parent)])
else:
    cmd.append("--noupx")
```
**Risque**: Certaines DLL Windows (Defender, antivirus) lèvent un faux-positif sur exécutables UPX. À tester sur cible. Toujours possible de revenir à `--noupx`.

---

### [F-15] `EXCLUDE_MODULES` peut être enrichi
**Statut**: ⬜ à faire  **Sévérité**: 🟢 faible  **Gain**: ~200-500 KB
**Fichier**: `build.py:48-72`

Modules à ajouter qui apparaissent dans `archive_viewer -l` mais sont morts au runtime :
```python
EXCLUDE_MODULES = [..., 
    # Déjà dans la liste, on ajoute :
    "cryptography", "cffi", "_cffi_backend",  # cf. [F-09]
    "chardet",                                 # cf. [F-10]
    "PIL._avif",                               # cf. [F-04] (fragile)
    # Stdlib lourde rarement utilisée :
    "email.mime", "email.policy",  # SMTP non utilisé
    "html.parser",                  # déjà ajouté dans GLOBAL_EXCLUDES
    "xmlrpc", "wsgiref",
    "multiprocessing.popen_*",      # forkserver non utilisé sur Windows
    "concurrent.futures.process",   # déjà ajouté
    "pdb", "doctest",               # déjà ajouté
    # Codecs Asie peu utilisés :
    "encodings.cp932", "encodings.cp949", "encodings.cp950",
    "encodings.euc_jp", "encodings.euc_kr", "encodings.gb2312",
    "encodings.gbk", "encodings.iso2022_jp", "encodings.iso2022_kr",
]
```
**Risque**: Si l'app organise un jour des fichiers chinois/japonais/coréens, retirer les exclusions encodings. Faible probabilité sur usage France.

---

### [F-16] Duplication `perl532.dll` (×2) et `libstdc++-6.dll` (×2)
**Statut**: ⬜ investiguer  **Sévérité**: 🟡 moyen  **Gain**: ~1 MB
**Origine**: 
- `perl532.dll` (821 KB compressé) une fois à la racine et une fois dans `assets/tools/exiftool_files/`
- `libstdc++-6-9fabacf176759adf41c62dee1152fe69.dll` (619 KB) + `libstdc++-6.dll` (308 KB)
- `libde265-0-917e506a532d55cfb99a65f420b94dad.dll` + `libde265-0-c879c1b22181112cd8a685c7049f0058.dll`

PyInstaller collecte ces DLL via deux chemins différents (hooks `pillow_heif` + auto-detect des deps DLL natives), d'où la duplication.

**Action**: Résolu automatiquement par [F-01] (retrait ExifTool → 1ère copie perl532.dll). Les libstdc++/libde265 doublons : un `.spec` mode permet de filtrer `Analysis.binaries` post-collecte (voir [F-19]).

---

### [F-17] `--optimize=2` actif mais bénéfice limité
**Statut**: ✅ déjà appliqué (réf)  **Sévérité**: info
`build.py:149` active `--optimize=2` (équivalent `python -OO` : retire docstrings + assertions). Le PYZ de 3.47 MB en bénéficie déjà. Aucune action.

---

### [F-18] `--strip` actif mais limité sous Windows
**Statut**: ✅ déjà appliqué (réf)  **Sévérité**: info
`--strip` est efficace surtout pour les binaires ELF Linux/macOS. Sous Windows, PyInstaller le passe à `strip.exe` (de MinGW) sur les `.pyd` et `.dll`. Gain marginal (~100-300 KB) si strip.exe est dispo. Sinon ignoré silencieusement.

---

### Phase 5 — Environnement de build

### [F-02] Build depuis un venv minimal isolé (CRITIQUE)
**Statut**: ⬜ à faire  **Sévérité**: 🔴 fort  **Gain**: ~5-6 MB compressé
**Constat**: Le Python global utilisé pour le build contient **325 paquets** dont :
- `numpy 2.4.4`, `pandas 3.0.2`, `scipy 1.17.1`, `matplotlib 3.10.9`
- `ipython 9.13.0`, `flask 3.1.3`, `cryptography 48.0.0` (cf. [F-09])
- Beaucoup d'autres tirés par d'autres projets (`autobook`, `canif`, `morpholapse`, `videoforge`…)

Même avec `--exclude-module`, certains hooks PyInstaller collectent des binaires/datas inattendus parce qu'ils détectent les paquets installés.

**Action** — créer un venv minimal pour le build :
```powershell
# Création
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1

# Installation stricte de requirements.txt + pyinstaller
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller>=6.0

# Build
python build.py

# Désactivation
deactivate
```
Variante automatisée — ajouter à `build.py` un check :
```python
def _require_clean_env():
    """Vérifie qu'on est dans un venv minimal."""
    import importlib
    forbidden = ["numpy", "pandas", "scipy", "matplotlib", "jupyter", "ipython"]
    found = []
    for mod in forbidden:
        if importlib.util.find_spec(mod):
            found.append(mod)
    if found:
        print(f"[WARN] Build env pollué : {found}")
        print("       Recommandé : python -m venv .venv-build && pip install -r requirements.txt")
        if "--allow-polluted-env" not in sys.argv:
            sys.exit(1)
```
**Gain combiné avec [F-09]+[F-10]** : 5-6 MB de moins (cryptography, chardet, fragments numpy/pandas auto-détectés).
**Risque**: Nul — le venv est jetable.

---

### [F-19] Migrer `build.py` → `.spec` versionné (refactor optionnel)
**Statut**: ⬜ décision humaine  **Sévérité**: 🟢 faible  **Gain**: contrôle fin sur datas/binaries (gain indirect via filtrage)
**Constat**: Le script `build.py` reconstruit la commande à chaque appel. Pour un filtrage avancé (retirer les doublons DLL, filtrer les .DS_Store, etc.), un `.spec` est plus pratique.

**`PhotoOrganizer.spec` proposé** (cf. section 5 plus bas).

---

## 4. Plan d'action ordonné

| Ordre | ID | Action | Gain MB | Effort | Risque |
|---:|---|---|---:|---|---|
| 1 | [F-02](#f-02) | Créer un venv minimal isolé pour le build | 5–6 | 5 min | Nul |
| 2 | [F-01](#f-01) | Exclure `assets/tools/` (ExifTool) du bundle | 10.3 | 15 min | Moyen (docs README) |
| 3 | [F-03](#f-03) | `pillow-heif` → `pi-heif` (HEVC read-only) | 2.3 | 10 min | Faible |
| 4 | [F-04](#f-04) | Exclure `_avif` via `--exclude-module` (**PAS** de pin `Pillow<12` — CVE) | 1.8 | 5 min | Faible |
| 5 | [F-05](#f-05) | Recompresser `icon.png` (pngquant/oxipng) | 0.85 | 5 min | Nul |
| 6 | [F-09](#f-09) | Exclure `cryptography`+`cffi` du bundle | 4.2 | 2 min | Faible |
| 7 | [F-10](#f-10) | Exclure `chardet` du bundle | 0.8 | 2 min | Faible |
| 8 | [F-08](#f-08) | Remplacer `requests` → `urllib.request` | 0.15 + libère deps | 30 min | Faible |
| 9 | [F-07](#f-07) | Retirer `piexif` (mort) | 0.05 | 2 min | Nul |
| 10 | [F-14](#f-14) | Activer UPX (avec exclusions DLL critiques) | 3–5 | 30 min | Moyen (faux-positifs AV) |
| 11 | [F-06](#f-06) | `ruff --fix` imports morts | <0.05 | 5 min | Nul |
| 12 | [F-15](#f-15) | Enrichir `EXCLUDE_MODULES` (encodings, email) | 0.2–0.5 | 10 min | Faible |
| 13 | [F-11](#f-11), [F-12](#f-12), [F-16](#f-16) | Filtrer .DS_Store, thèmes morts, dll doublons | 0.05 | 30 min (`.spec`) | Nul |
| 14 | [F-13](#f-13) | Décider `--onefile` vs `--onedir` | variable | — | — |
| 15 | [F-19](#f-19) | Migrer `build.py` → `.spec` versionné | 0 (refactor) | 1 h | Nul |

**Cumul réaliste (lignes 1–9)** : **~25 MB** → **exe ≈ 22-24 MB**.
**Avec UPX (ligne 10)** : **~13 MB** → **exe ≈ 11-13 MB** (optimiste).

---

## 5. `.spec` PyInstaller optimisé proposé

> À placer en `PhotoOrganizer.spec` et invoquer via `pyinstaller PhotoOrganizer.spec`.

```python
# -*- mode: python ; coding: utf-8 -*-
"""PhotoOrganizer build spec — optimisé taille.

Préalable : créer un venv minimal isolé (cf. F-02) :
    python -m venv .venv-build
    .\.venv-build\Scripts\Activate.ps1
    pip install -r requirements.txt pyinstaller>=6.0
"""
import os
import shutil
from pathlib import Path

APP_NAME = "PhotoOrganizer"
VERSION = "2.0.0"
PROJECT_DIR = Path(SPECPATH)

# ---------- Hidden imports (réduits : piexif/requests retirés)
HIDDEN_IMPORTS = [
    "customtkinter", "darkdetect",
    "PIL", "PIL._imaging", "PIL._imagingft",
    "exifread", "pillow_heif",  # ou pi_heif (cf. F-03)
    "sqlite3", "_sqlite3",
    "yaml",
    "tkinterdnd2", "plyer", "plyer.platforms.win.notification",
]

# ---------- Exclusions agressives
EXCLUDE_MODULES = [
    # Libs lourdes jamais utilisées
    "scipy", "cv2", "dlib", "moviepy", "whisper", "oletools",
    "pandas", "numpy", "openpyxl", "fitz", "pymupdf",
    "docx", "pptx", "PyPDF2", "reportlab", "matplotlib", "seaborn", "win32com",
    "IPython", "jupyter", "notebook", "sphinx",
    "tornado", "zmq", "babel",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
    "pytz", "dateutil", "blake3",
    # F-09, F-10
    "cryptography", "cffi", "_cffi_backend", "chardet",
    # F-04 (exclusion module ; NE PAS pin Pillow<12 → 7 CVE, cf. F-04)
    # "PIL._avif",
    # F-08 si appliqué (remplace requests par urllib)
    # "requests", "urllib3", "charset_normalizer", "idna", "certifi",
    # Stdlib outils dev
    "unittest", "test", "tests", "pytest", "pydoc", "doctest",
    "lib2to3", "ensurepip", "venv", "distutils",
    "setuptools", "pkg_resources", "pip",
    "tkinter.test", "idlelib",
    "asyncio.test_support", "concurrent.futures.process",
    "email.test", "xmlrpc", "wsgiref",
    "ruff", "mypy", "vulture", "bandit",
    # Encodings Asie peu utilisés (F-15)
    "encodings.cp932", "encodings.cp949", "encodings.cp950",
    "encodings.euc_jp", "encodings.euc_kr",
    "encodings.gb2312", "encodings.gbk",
    "encodings.iso2022_jp", "encodings.iso2022_kr",
]

# ---------- Datas (F-01 : exclut assets/tools/)
def _icon_target() -> str | None:
    candidates = [
        "resources/icons/icon.ico",
        "assets/icons/icon.ico",
    ]
    for rel in candidates:
        if (PROJECT_DIR / rel).exists():
            return rel
    return None

ICON_PATH = _icon_target()

datas = []
# Whitelist explicite : seuls icons/ vont dans assets/, PAS tools/ (F-01)
icons_dir = PROJECT_DIR / "assets" / "icons"
if icons_dir.exists():
    datas.append((str(icons_dir), "assets/icons"))
# resources si présent
res_dir = PROJECT_DIR / "resources"
if res_dir.exists():
    datas.append((str(res_dir), "resources"))
# src bundle
src_dir = PROJECT_DIR / "src"
datas.append((str(src_dir), "src"))

# tkinterdnd2 native DLLs
try:
    import tkinterdnd2 as _tkdnd
    tkdnd_dir = Path(_tkdnd.__path__[0]) / "tkdnd"
    if tkdnd_dir.is_dir():
        datas.append((str(tkdnd_dir), "tkinterdnd2/tkdnd"))
except ImportError:
    pass


a = Analysis(
    [str(PROJECT_DIR / "main.py")],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDE_MODULES,
    noarchive=False,
    optimize=2,  # F-17 : équivalent python -OO
)

# ---------- Post-Analysis cleanup
# Retire les doublons DLL (F-16) et les .DS_Store (F-11)
_seen_names = set()
def _dedupe(files):
    out = []
    for entry in files:
        name = entry[0]
        base = os.path.basename(name).lower()
        # .DS_Store et fichiers indésirables
        if base in ('.ds_store', 'thumbs.db'):
            continue
        # Tester l'unicité par basename pour DLL natives
        if name.endswith(('.dll', '.pyd')) and base in _seen_names:
            continue
        _seen_names.add(base)
        out.append(entry)
    return out

a.datas = _dedupe(a.datas)
a.binaries = _dedupe(a.binaries)


pyz = PYZ(a.pure)


# ---------- UPX config (F-14)
UPX_DIR = str(PROJECT_DIR / "tools" / "upx") if (PROJECT_DIR / "tools" / "upx" / "upx.exe").exists() else None
UPX_EXCLUDES = [
    "vcruntime140.dll",
    "python311.dll",
    "tcl86t.dll",
    "tk86t.dll",
    "_tkinter.pyd",
]


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"{APP_NAME}-{VERSION}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # F-18
    upx=bool(UPX_DIR),
    upx_dir=UPX_DIR,
    upx_exclude=UPX_EXCLUDES,
    runtime_tmpdir=None,
    console=False,         # --windowed
    windowed=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_DIR / ICON_PATH) if ICON_PATH else None,
)
```

---

## 6. Commande de build finale recommandée

```bash
# 1) Préparer le venv minimal (une fois)
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller>=6.0

# 2) (Optionnel) installer UPX
winget install upx-project.upx
# OU télécharger upx.exe dans tools/upx/

# 3) Optimiser les assets (une fois)
pngquant --quality=80-95 --strip --skip-if-larger --ext .png --force assets/icons/icon.png
# OU oxipng -o max --strip safe assets/icons/icon.png

# 4) Builder
pyinstaller PhotoOrganizer.spec --noconfirm

# 5) Vérifier
ls -lh dist/PhotoOrganizer-2.0.0.exe
python -m PyInstaller.utils.cliutils.archive_viewer -l dist/PhotoOrganizer-2.0.0.exe | wc -l
```

---

## 7. Questions ouvertes (décision humaine requise)

1. **ExifTool fallback** ([F-01]) : tolérer la perte du fallback subprocess ? Ou packager une version "deluxe" séparée avec ExifTool pour les utilisateurs avancés ?
2. **AVIF support** ([F-04]) : faut-il maintenir AVIF dans la liste des extensions scannées ? (Si non, retirer aussi de `EXTENSIONS['image']` dans `exif_extractor.py` et `file_manager.py`.)
3. **`pi-heif` vs `pillow-heif`** ([F-03]) : confirmer que le projet ne *crée* jamais de HEIC (= encodage HEVC). Si le bouton "Convertir en HEIC" existe quelque part → garder `pillow-heif`.
4. **`--onefile` vs `--onedir`** ([F-13]) : portabilité (1 fichier) prioritaire ou démarrage rapide ?
5. **UPX et antivirus** ([F-14]) : tolérer le risque de faux-positif Windows Defender (heuristique vs UPX) sur cible utilisateur ?
6. **Reprise de l'audit** : appliquer les actions par ordre du plan §4 ? Choisir un sous-ensemble ?

---

## Journal

| Date | Action | Auteur |
|---|---|---|
| 2026-05-19 | Audit initial — mesure 37.06 MB, décomposition pyi-archive_viewer, 19 findings | audit-pyinstaller-customtkinter |
