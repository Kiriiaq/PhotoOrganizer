# PhotoOrganizer — Architecture

> Carte des modules et flux principaux. Pour la liste des dépendances externes voir [`../pyproject.toml`](../pyproject.toml). Pour l'audit projet voir [`../AUDIT.md`](../AUDIT.md).

---

## Vue d'ensemble (3 couches)

```
┌──────────────────────────────────────────────────────────────────────┐
│                          src/ui/   (Présentation)                    │
│                                                                      │
│   app.py  ─►  4 frames (organize, duplicates, history, settings)     │
│           ─►  theme.py (fonts/couleurs)                              │
│           ─►  tooltip(s) (overlays informatifs)                      │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼  (jamais d'import inverse)
┌──────────────────────────────────────────────────────────────────────┐
│                       src/core/   (Logique métier)                   │
│                                                                      │
│   metadata/                              operations/                 │
│     ├── exif_extractor       │             ├── file_manager          │
│     ├── date_extractor       │             ├── organizer             │
│     ├── camera_detector      │             ├── duplicate_finder      │
│     └── gps_processor        │             ├── duplicate_manager     │
│                              │             └── quarantine            │
│   scheduler.py (timer reusable)                                      │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       src/utils/   (Infrastructure)                  │
│                                                                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐    │
│   │ cache.py     │  │ hash_cache   │  │ config   │  │ logger   │    │
│   │ EXIF 2-tier  │  │ SQLite TTL   │  │ JSON     │  │ rotation │    │
│   │ RAM+SQLite   │  │ file hashes  │  │ AppConfig│  │ filehnd  │    │
│   └──────────────┘  └──────────────┘  └──────────┘  └──────────┘    │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │ licensing.py  (v2.3+, pivot 2026-05-26)                      │   │
│   │   - Compteur HMAC dans %LOCALAPPDATA%\PhotoOrganizer\usage.dat│   │
│   │   - Machine binding SHA-256(MachineGuid + VolumeSerial)      │   │
│   │   - API : get_state / can_organize_now /                     │   │
│   │           record_successful_organize / activate_key          │   │
│   │   - Réutilise src/photoorganizer_pro/license/ (validator HMAC)│  │
│   └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                       Système : %LOCALAPPDATA%, FS, HTTPS
```

**Règle d'or** : `core/` ne dépend jamais de `ui/`. `utils/` ne dépend ni de `core/` ni de `ui/`. `photoorganizer_pro/` peut importer `core/` et `utils/`, jamais l'inverse. **Note pivot 2026-05** : `photoorganizer_pro/cli/`, `scheduler/`, `plugins/` sont *gelés v3.0+* (entry points pip commentés, tests skippés). Seul `photoorganizer_pro/license/` est actif, réutilisé par `utils/licensing.py`.

---

## Points d'entrée

| Entrée | Cible Python | Usage |
|---|---|---|
| Double-clic `PhotoOrganizer-X.Y.Z.exe` | bootloader PyInstaller → `main.py` → `src.main:main` → `PhotoOrganizerApp().mainloop()` | GUI Windows portable |
| `python main.py` | idem | Lancement source |
| `photo-organizer` (entry point pip) | `src.main:main` | Idem après `pip install -e .` |
| `photo-organizer-dedup` (entry point pip) | `src.cli.duplicate_cli:main` | CLI doublons (sans GUI) |
| `python -m PyInstaller PhotoOrganizer.spec` | Build EXE (cf. [docs/exe-optimization.md](exe-optimization.md)) | Packaging |
| Tag git `v*` → `.github/workflows/release.yml` → `python build.py` | Build EXE + checksums + release GitHub | Distribution |

---

## Flux principal — Organiser un dossier

```
Utilisateur ► sélectionne source/dest ► coche critères (date/camera/GPS)
               │
               ▼
   OrganizeFrame.start_organization()
               │
               ▼
   FileManager.list_files(source, recursive=True, extensions=...)
               │
               ▼
   ExifExtractor.extract(file)  ← cache 2-tier consulté (utils/cache.py)
       ├── exifread (JPEG/TIFF/RAW)
       ├── Pillow (PIL.Image._getexif)
       ├── pillow_heif (HEIC/HEIF)
       └── ExifTool subprocess (fallback)
               │
               ▼
   DateExtractor + CameraDetector + GPSProcessor
               │
               ▼
   SmartOrganizer.organize(files, OrganizationOptions)
       │
       ├── pour chaque fichier : décide chemin cible
       │   (date_format, camera, location, rename_template…)
       │
       ├── copy/move via FileManager
       │
       └── enregistre l'opération dans history (sessions)
               │
               ▼
   OrganizeFrame met à jour progress + UI
               │
               ▼
   Notification fin (plyer Windows toast OU Toplevel fallback)
               │
               ▼
   HistoryFrame se rafraîchit (rollback possible)
```

Cancel à tout moment : `OrganizeFrame._cancel_operation()` → flag `SmartOrganizer.cancel()` → boucle d'organisation lit le flag → interruption propre.

---

## Flux principal — Détecter et gérer les doublons

```
DuplicatesFrame.start_search()
       │
       ▼
   DuplicateFinder.find(directories, algorithm=md5|sha1|blake3, recursive)
       │
       ├── scan parallèle (ThreadPoolExecutor)
       ├── exclusion auto : $Recycle.Bin, .Trash, System Volume Information
       ├── hash en streaming (lecture par blocs)
       └── HashCache SQLite : skip les fichiers déjà hashés (mtime+size match)
       │
       ▼
   DuplicateResult (groupes de fichiers identiques)
       │
       ▼
   DuplicateManager.apply_action(groups, strategy)
       ├── strategy.priority_dirs   : conserve l'original dans D:/Masters/
       ├── strategy.regex_keep      : règle conserve la 1ère qui matche
       ├── strategy.glob_keep       : idem avec glob
       └── strategy.action          : delete / move_to / quarantine
       │
       ▼
   QuarantineManager.quarantine(files)        ← réversible (cf. tests/functional/test_quarantine.py)
       └── déplace vers %LOCALAPPDATA%\PhotoOrganizer\quarantine\<session_id>\
       │
       ▼
   DuplicateReporter (CSV / JSON / HTML / Markdown)
```

---

## Modules par couche — détail rapide

### `src/ui/`

| Fichier | LOC | Rôle |
|---|---:|---|
| `app.py` | ~510 | `PhotoOrganizerApp(ctk.CTk)` : fenêtre principale, switch onglets, raccourcis clavier, icône, drag-and-drop bootstrap |
| `theme.py` | ~340 | Helpers `font_label()`, `font_section()`, `font_mono()`, `ScrollableFrame`, palette de couleurs |
| `tooltip.py` | ~170 | `attach_tooltip(widget, text)` — overlay sur survol |
| `tooltips_fr.py` | ~450 | Catalogue de libellés FR (un dict par onglet) |
| `prompt_examples.py` | ~50 | Templates de renommage prédéfinis |
| `frames/organize_frame.py` | **3 423** | Onglet principal — sélection, options, exécution, progress, drag-and-drop, exemples intégrés |
| `frames/duplicates_frame.py` | ~1 213 | Onglet doublons — config algo, scan, gestion groupes, exports |
| `frames/history_frame.py` | ~398 | Liste opérations, rollback par session |
| `frames/settings_frame.py` | ~615 | Thème, cache, géocodage, logs, notifications, DnD, raccourcis |

### `src/core/`

| Sous-paquet | Fichier | Rôle |
|---|---|---|
| `metadata/` | `exif_extractor.py` | Cascade 4 méthodes (exifread → PIL → pillow_heif → ExifTool) avec cache |
| | `date_extractor.py` | EXIF Date + fallback regex sur nom de fichier + mtime |
| | `camera_detector.py` | Make/Model EXIF + heuristiques préfixes (PXL_, VID_, IMG_) |
| | `gps_processor.py` | DMS↔decimal, distance haversine, reverse geocoding Nominatim (lazy `requests`) |
| `operations/` | `file_manager.py` | `list_files`, `copy_file`, `move_file`, `rollback_*`, history par session |
| | `organizer.py` | `SmartOrganizer` — plan d'organisation + exécution avec cancel |
| | `duplicate_finder.py` | Hash multi-algo, scan parallèle, cache hash |
| | `duplicate_manager.py` | Décide action sur groupes (priorité dirs, regex, glob, exclusion corbeilles) |
| | `quarantine.py` | Quarantaine réversible avec `metadata.json` par opération |
| (racine `core/`) | `scheduler.py` | `threading.Timer` wrapper (présent mais usage à confirmer) |

### `src/utils/`

| Fichier | Rôle |
|---|---|
| `cache.py` | `MetadataCache` — cache 2-tier EXIF (RAM + SQLite), TTL configurable, init via `init_cache()` |
| `hash_cache.py` | `HashCache` SQLite — réutilise les hashes si `(mtime, size)` inchangés |
| `config.py` | `AppConfig` dataclass + persistance JSON dans `%LOCALAPPDATA%\PhotoOrganizer\config.json` |
| `logger.py` | `setup_logging()`, rotation fichier, niveau dynamique |

### `src/config/`

| Fichier | Rôle |
|---|---|
| `duplicate_config.py` | `DuplicateManagerConfig` dataclass, sérialisation YAML (load/save) |

### `src/cli/`

| Fichier | Rôle |
|---|---|
| `duplicate_cli.py` | CLI complet pour le mode doublons (sans GUI) — exposé via entry point `photo-organizer-dedup` |

### `src/reports/`

| Fichier | Rôle |
|---|---|
| `duplicate_reporter.py` | Génération de rapports CSV / JSON / HTML / Markdown pour les résultats doublons |

### `src/photoorganizer_pro/` (partiellement actif post-pivot 2026-05-26)

| Sous-module | Statut v2.x | Rôle |
|---|---|---|
| `license/` | **ACTIF** | Validation HMAC SHA-256 + machine binding. Importé par `src/utils/licensing.py`. |
| `cli/batch_organize.py` | DEFERRED v3.0+ | Batch CLI scriptable. Entry point pip commenté dans `pyproject.toml`. Tests skip. |
| `scheduler/watch_folder.py` | DEFERRED v3.0+ | Surveillance auto de dossier. Idem. |
| `plugins/` | DEFERRED v3.0+ | Plugin API (5 hooks). Idem. |

Critères de réactivation v3.0+ : cf. [`MONETIZATION.md`](MONETIZATION.md) §8.

---

## Persistance — où vont les fichiers utilisateur

| Type | Chemin Windows | Géré par |
|---|---|---|
| Configuration | `%LOCALAPPDATA%\PhotoOrganizer\config.json` | `utils/config.py` |
| Cache métadonnées EXIF | `%LOCALAPPDATA%\PhotoOrganizer\cache.db` (SQLite) | `utils/cache.py` |
| Cache hashes fichiers | `%LOCALAPPDATA%\PhotoOrganizer\hashes.db` (SQLite) | `utils/hash_cache.py` |
| Logs application | `%LOCALAPPDATA%\PhotoOrganizer\logs\photoorganizer.log` | `utils/logger.py` |
| Quarantaine doublons | `%LOCALAPPDATA%\PhotoOrganizer\quarantine\<session>\` | `core/operations/quarantine.py` |
| Historique opérations | en mémoire dans `FileManager`, persisté via session JSON | `core/operations/file_manager.py` |
| Compteur trial (HMAC) | `%LOCALAPPDATA%\PhotoOrganizer\usage.dat` (JSON signé) | `utils/licensing.py` |
| Licence activée (HMAC + machine binding) | `%LOCALAPPDATA%\PhotoOrganizer\license.dat` (JSON signé) | `photoorganizer_pro/license/validator.py` |

Aucun secret, aucun token, aucune donnée personnelle utilisateur n'est envoyée à l'extérieur — sauf le couple `(lat, lon)` à Nominatim si le géocodage est activé (par défaut ON, désactivable dans Paramètres).

---

## Dépendances externes — où elles sont utilisées

| Lib | Importée par | Critique ? |
|---|---|---|
| `customtkinter` | tout `src/ui/` | Oui — UI |
| `darkdetect` | implicitement par `customtkinter` (mode système) | Optionnel mais bundlé |
| `Pillow` | `core/metadata/exif_extractor.py`, plugins images | Oui |
| `exifread` | `core/metadata/exif_extractor.py` | Oui (méthode 1) |
| `pillow_heif` | `core/metadata/exif_extractor.py` | Oui pour HEIC/HEIF |
| `requests` | `core/metadata/gps_processor.py` (1 GET lazy) | Remplaçable par `urllib.request` stdlib (cf. AUDIT_EXE F-08) |
| `PyYAML` | `config/duplicate_config.py` | Oui (config doublons) |
| `tkinterdnd2` | `ui/app.py`, `ui/frames/organize_frame.py` (try/except) | Optionnel — DnD |
| `plyer` | `ui/frames/organize_frame.py` (try/except) | Optionnel — toasts Windows |
| `send2trash` | `core/operations/duplicate_manager.py`, `quarantine.py` (try/except) | Optionnel — corbeille système |

---

## Build & packaging

Voir [`../build.py`](../build.py) et [`exe-optimization.md`](exe-optimization.md) pour les détails. Résumé :

- **Cible** : Windows x64, Python 3.11, `--onefile` PyInstaller.
- **Taille actuelle** : 37 MB.
- **Taille cible** (après optimisations documentées dans exe-optimization.md) : 22 MB.
- **Variantes** : `release` (windowed), `debug` (console verbose), `light` (suppose Python sur la cible).

---

## Tests — organisation

| Type | Dossier | Fixtures | Marqueur |
|---|---|---|---|
| Smoke | `tests/smoke/` | aucune lourde | par défaut |
| Functional | `tests/functional/` | générées dans `test_data/inputs/` | par défaut |
| Perf | `tests/perf/` | grands inputs | `@pytest.mark.benchmark` |
| Stress | `tests/stress/` | cycles intensifs | `@pytest.mark.slow` |
| Volume | `tests/volume/` | 1000+ fichiers | `@pytest.mark.slow` |

`test_data/` (ex-`test/`) abrite la **qualification métier** (matrice Excel 189 tests, checklist IHM HTML, scripts de comparaison output réel vs référence). Indépendante de `tests/` (pytest).

---

## Décisions architecturales notables

- **`src/` layout** plutôt que `photoorganizer/` à la racine : permet le `--add-data src;src` PyInstaller sans piéger des imports en mode développement. Un renommage en `src/photoorganizer/` est prévu si publication PyPI envisagée.
- **`PhotoOrganizerApp(ctk.CTk)`** hérite directement de `ctk.CTk` plutôt que `TkinterDnD.Tk` pour pouvoir bénéficier des thèmes CustomTkinter ; le mixin DnD est branché dynamiquement (`_enable_tk_dnd`).
- **Quarantaine plutôt que `send2trash` direct** : permet le rollback granulaire (`metadata.json` par fichier) et évite la dépendance dure à `send2trash`. La quarantaine peut être vidée vers la corbeille système à la demande.
- **Cache 2-tier RAM + SQLite** : la RAM accélère les re-scans en session, le SQLite survit aux relances et est partagé entre sessions.
- **Hash multi-algo avec préférence Blake3** : Blake3 est 2-3 fois plus rapide que SHA-1 sur gros fichiers ; fallback transparent si la lib n'est pas dispo.
- **Pas d'asyncio** : le code utilise `threading` + `ThreadPoolExecutor`. Choix simple, suffisant pour des opérations FS et HTTP unique.
- **Pas de framework UI lourd** : CustomTkinter pèse 2 MB, Qt en pèserait 50+. Démarrage rapide prioritaire sur richesse visuelle.
