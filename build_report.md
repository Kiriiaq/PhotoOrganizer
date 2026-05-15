# Build Report — PhotoOrganizer v2.0.0

## Métadonnées build

| Champ | Valeur |
|---|---|
| **Date / heure** | 2026-05-15 12:52 (rebuild après élargissement bursts auto) |
| **Branche** | `main` |
| **Commit HEAD** | `29d4921 feat(bursts): expose les bornes auto_min/auto_max + WIP filtres` |
| **Commit précédent** | `579a30e fix(bursts): mean/stddev calculé par dossier-destination (2026-05-15)` |
| **Python** | 3.11.9 |
| **PyInstaller** | 6.20.0 |
| **Plateforme** | Windows 10/11 64-bit |

## Pipeline complet

| Étape | Statut | Détail |
|---|---|---|
| 1. Pré-vérifs | ✅ | Working tree clean après commit, branche `main` |
| 2. Tests pytest | ✅ | **112/112** verts (25 functional dont 3 nouveaux burst tests) en 18.95 s |
| 3. Ruff check + format | ✅ | `All checks passed!` + format conforme |
| 4. Build debug | ✅ | `PhotoOrganizer-2.0.0-debug.exe` 36.0 MB |
| 5. Build release light | ✅ | `PhotoOrganizer-2.0.0-light.exe` 34.5 MB |
| 6. Smoke tests post-build | ✅ | debug ALIVE 6.15 s · light ALIVE 6.17 s (`audit/smoke_exe.py`) |
| 7. Rapport | ✅ | ce document |

> **Note 2026-05-15** : le 1ᵉʳ run du build debug a échoué sur un
> `FileNotFoundError: …PhotoOrganizer-2.0.0-debug.pkg` causé par un
> `build/` corrompu suite à une interruption précédente. Fix :
> `rm -rf build/ *.spec` avant relance — bug PyInstaller 6.20 connu
> avec `--debug=all`. Le 2ᵉ run a réussi. Idem pour `--light` (cache
> .spec laissé par le debug). À l'avenir : toujours `make clean` ou
> `rm -rf build/` entre deux builds successifs.

## Artefacts

| Fichier | Taille | SHA-256 |
|---|---:|---|
| `dist/PhotoOrganizer-2.0.0-debug.exe` | 37 781 329 B (36.0 MB) | `8dd94291ff308612fed8eed2834cfe973fc580739dc16168a3cc26eabd6d62bf` |
| `dist/PhotoOrganizer-2.0.0-light.exe` | 36 126 144 B (34.5 MB) | `3c177e1263f3a15b2e6ea04fd81a90d1497900985e977ead6c9bab545b3c0a29` |

**Builds précédents (2026-05-15 08:07/08:09)** conservés dans
`dist/debug/` et `dist/light/` pour comparaison/rollback :

| Fichier | Taille |
|---|---:|
| `dist/debug/PhotoOrganizer-2.0.0-debug.exe` | 36.0 MB |
| `dist/light/PhotoOrganizer-2.0.0-light.exe` | 34.4 MB |

**Évolution du poids** vs build du matin (08:09) :
- Debug : +14 KB (+0.04 %) — négligeable, timestamp PE + delta code burst expansion
- Light : +14 KB (+0.04 %) — idem

Les hashes SHA-256 diffèrent entre deux builds **même quand le code est
identique** : PyInstaller embarque un timestamp dans le PE header →
reproductibilité non bit-à-bit.

## Smoke tests post-build (`audit/smoke_exe.py`)

Chaque EXE est lancé depuis un **tempdir hermétique** (no `VIRTUAL_ENV`,
no `PYTHONPATH`), maintenu actif 6 s puis `taskkill /F /T /PID`.

### Profil debug

```
status    : ALIVE
hold_time : 6.15 s
log tail  :
    [PYI-33224:DEBUG] LOADER: successfully loaded system copy of VCRUNTIME140.dll.
    [PYI-33224:DEBUG] LOADER: attempting to pre-load system copy of VCRUNTIME140_1.dll...
    [PYI-33224:DEBUG] LOADER: successfully loaded system copy of VCRUNTIME140_1.dll.
    [PYI-33224:DEBUG] LOADER: calling SetDllDirectoryW: …\_MEI332242
    [PYI-33224:DEBUG] LOADER: splash screen is unavailable.
    [PYI-33224:DEBUG] LOADER: extracting files to temporary directory...
```

### Profil light

```
status    : ALIVE
hold_time : 6.17 s
(--debug=all désactivé en light → pas de log loader verbose)
```

## Détail tests pytest (2026-05-15)

| Suite | Tests | Statut |
|---|---:|---|
| `tests/smoke/` | 32 | ✅ |
| `tests/functional/test_organizer.py` | **25** | ✅ (3 nouveaux burst tests) |
| `tests/functional/test_file_manager.py` | 7 | ✅ |
| `tests/functional/test_duplicates.py` | 6 | ✅ |
| `tests/functional/test_config.py` | 4 | ✅ |
| `tests/functional/` (autres) | 36 | ✅ |
| `tests/perf/test_perf.py` | 2 (benchmark) | ✅ |
| **Total** | **112 / 112** | ✅ |

## Élargissement bursts intégré à ce build

Le commit `29d4921` ajoute deux options avancées au mode auto de
détection de rafales :

```python
OrganizationOptions(
    detect_bursts=True,
    burst_mode="auto",
    burst_auto_min_seconds=1,    # default = comportement historique
    burst_auto_max_seconds=600,  # idem
)
```

Cas d'usage :
- **Timelapse / pose longue** : `burst_auto_max_seconds=3600` capture
  des séries dont les Δ atteignent 1 h.
- **Vraies rafales rapides** : `burst_auto_min_seconds=20` ignore les
  pauses normales (< 20 s) entre clichés d'un même endroit.

UI : nouvelle ligne **« Bornes auto : min/max »** dans le sous-bloc
bursts du panneau Avancé > Comportements, visible **uniquement** quand
le mode auto est actif (l'`Écart max` est caché à ce moment-là).
Pré-sets min = {1, 2, 3, 5, 10, 30} s · max = {60, 120, 300, 600,
1800, 3600} s.

Tests dédiés :
- `test_burst_detection_auto_clamp_bounds_are_configurable` : 7 photos
  espacées d'1 h. Defaults → 0 burst. `auto_max=7200` → 1 burst de 7.
- `test_burst_detection_auto_min_clamp_floors_threshold` : `auto_min=60`
  force toutes les photos à fusionner en 1 burst.
- `test_burst_detection_auto_bounds_inverted_are_repaired` : bornes
  inversées (min > max) → re-ordonnées en interne, pas de crash.

## Warnings PyInstaller

Aucun warning bloquant lors du build final.

Hidden imports résolus : `customtkinter`, `darkdetect`, `PIL`,
`PIL._imaging`, `PIL._imagingft`, `exifread`, `piexif`, `pillow_heif`,
`sqlite3`, `_sqlite3`, `yaml`, `tkinterdnd2`, `plyer`,
`plyer.platforms.win.notification`, `requests`, `urllib3`,
`charset_normalizer`, `idna`.

Modules exclus (réduction du binaire) : `scipy`, `cv2`, `dlib`,
`moviepy`, `whisper`, `oletools`, `pandas`, `numpy`, `openpyxl`,
`fitz`, `pymupdf`, `docx`, `pptx`, `PyPDF2`, `reportlab`, `matplotlib`,
`seaborn`, `win32com`, `IPython`, `jupyter`, `notebook`, `sphinx`,
`tornado`, `zmq`, `babel`, `PyQt5/6`, `PySide2/6`, `wx`, `pytz`,
`dateutil`, `blake3`.

## Points à surveiller

| Point | Niveau | Note |
|---|---|---|
| Taille EXE 36 MB (debug) / 34.5 MB (light) | 🟡 OK | Stable. Le delta debug/light vient principalement de `--strip` et `--optimize=2` en light. |
| Faux-positifs Defender SmartScreen | 🟡 Connu | Comportement attendu pour un onefile non signé. Pas de signature de code dans cette release. |
| Démarrage à froid ~3-5 s | 🟢 OK | Premier lancement Windows à cause de la décompression `_MEIxxxxxx` dans `%TEMP%`. À chaud (~1 s). |
| `git push` non effectué | 🟢 Conformité | Pas de modification du remote (working only in main, local). |

## Commandes pour reproduire

```bash
# Suite complète
python -m pytest -q

# Lint
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/

# Build (nettoyer avant si build/ existe — bug PyInstaller 6.20)
rm -rf build/ *.spec
python build.py --debug
rm -rf build/ *.spec
python build.py --light

# Smoke test
python audit/smoke_exe.py

# Cleanup
make clean
```

## Log git (5 derniers commits sur `main`)

```
29d4921 feat(bursts): expose les bornes auto_min/auto_max comme option avancée + WIP filtres
579a30e fix(bursts): mean/stddev calculé par dossier-destination (audit 2026-05-15)
f31a274 Merge branch 'feat/v2.1-refonte-ux'
a54b928 feat(ux): logo PhotoOrganizer en haut-gauche dans toutes les modales
ad27798 feat(ux): tooltips exhaustifs sur tous les boutons d'action
```

## Verdict global

✅ **Build OK** — les 7 étapes du pipeline ont réussi, 1 retry sur le
debug profile (cache PyInstaller corrompu, résolu par `rm -rf build/`).

Les deux artefacts `dist/PhotoOrganizer-2.0.0-debug.exe` (debug, console
verbose, `--debug=all`) et `dist/PhotoOrganizer-2.0.0-light.exe`
(release sans libs lourdes, `--windowed --optimize=2 --strip`) sont
prêts à être distribués. La nouvelle option avancée `auto_min/auto_max`
des bursts est embarquée et exposée dans l'UI.
