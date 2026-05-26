# PhotoOrganizer — Audit projet (Phase 1)

**Date** : 2026-05-19
**Périmètre** : `D:\#Bureau\PhotoOrganizer` (branche `feat/v2.3-organize-tabview`)
**Auditeur** : audit-complet-valorisation
**Statut** : Phase 1 (inventaire) terminée. En attente GO Phase 2.

> Voir aussi : [`AUDIT_EXE.md`](AUDIT_EXE.md) (audit spécifique taille `.exe` — 19 findings, gain 40 % attendu).

---

## 1. Identité du projet

| Champ | Valeur |
|---|---|
| Nom | PhotoOrganizer |
| Pitch | Organiseur automatique de photos par métadonnées EXIF (Windows, GUI) |
| Version actuelle | 2.0.0 (sur branche), 1.0.0 (dernière release publique) |
| Branche active | `feat/v2.3-organize-tabview` |
| Auteur | Kiriiaq (manugrolleau48@gmail.com) |
| Ko-fi | <https://ko-fi.com/kiriiaq> |
| Repo | <https://github.com/Kiriiaq/PhotoOrganizer> |
| License | **MIT + Commons Clause** (interdit la revente du logiciel) |
| Statut | WIP — v2 en développement actif, refonte panneau Organisation en cours |

---

## 2. Stack technique détectée

| Couche | Choix |
|---|---|
| Langage | Python 3.11+ (`requires-python = ">=3.11"` dans `pyproject.toml`) |
| GUI | CustomTkinter 5.2.x + Tkinter stdlib |
| Packaging | PyInstaller `--onefile` (Windows) via `build.py` |
| Gestionnaire deps | pip + `requirements.txt` + `pyproject.toml` (PEP 621) |
| Linter / format | ruff (E,F,W,B,S) + bandit (sécurité) + mypy (types) |
| Tests | pytest + pytest-cov + pytest-benchmark — 170 tests collectés |
| CI/CD | GitHub Actions : `ci.yml` (lint+test sur Windows), `release.yml` (build exe sur tag `v*`) |
| OS cible | Windows 10/11 (autres non testés) |
| Drag-and-drop | tkinterdnd2 (optionnel, fallback gracieux) |
| Notifications | plyer Windows toast (optionnel, fallback Toplevel) |
| Logging | stdlib `logging` + handler fichier dans `%LOCALAPPDATA%\PhotoOrganizer\logs\` |
| Persistance | SQLite via `sqlite3` (cache hash + cache EXIF) + JSON (config user) |
| Réseau | `requests` pour 1 GET Nominatim (géocodage inverse) — remplaçable par stdlib |

**Versions épinglées** (`pyproject.toml`) :
```
customtkinter>=5.2.0,<6.0.0
darkdetect>=0.8.0,<1.0.0
Pillow>=10.0.0,<12.0.0       # à pinner si F-04 appliqué
exifread>=3.0.0,<4.0.0
piexif>=1.1.3,<2.0.0          # mort, à retirer (cf. AUDIT_EXE F-07)
pillow-heif>=0.13.0,<1.0.0
requests>=2.31.0,<3.0.0
```

---

## 3. Arborescence (3 niveaux)

```
.
+-- .github/                  CI + funding + templates
+-- assets/
|   +-- icons/                icon.ico (35 KB) + icon.png (945 KB sur-poids !)
|   +-- tools/                ExifTool Perl bundle (34 MB — fallback non câblé)
+-- audit/                    Anciens rapports d'audit (mai 2026, historiques)
+-- src/                      Code source (16 021 lignes, 38 fichiers .py)
|   +-- cli/                  duplicate_cli.py (767 LOC) — pas câblé en console_script
|   +-- config/               duplicate_config.py (dataclasses + YAML)
|   +-- core/
|   |   +-- metadata/         exif_extractor, date_extractor, camera_detector, gps_processor
|   |   +-- operations/       file_manager, organizer, duplicate_finder/manager, quarantine
|   |   +-- scheduler.py      (présent mais usage unclear)
|   +-- modules/              FAÇADE jamais importée — alias de core.operations (dead)
|   +-- reports/              duplicate_reporter (CSV/JSON/HTML)
|   +-- ui/                   7 924 LOC sur 11 fichiers — coeur du projet
|   |   +-- frames/           organize, duplicates, history, settings (4 onglets)
|   |   +-- app.py            ctk.CTk principal
|   |   +-- theme.py          helpers fonts + couleurs + ScrollableFrame
|   |   +-- tooltip.py        attach_tooltip()
|   |   +-- tooltips_fr.py    libellés FR pour tooltips
|   |   +-- prompt_examples.py templates nommage
|   +-- utils/                cache, config, hash_cache, logger (1 239 LOC)
|   +-- main.py               point d'entrée src.main:main
+-- test/                     Suite de qualif "métier" (matrice Excel + scripts) — vieux flow
|   +-- inputs/               fixtures (1.4 MB)
|   +-- outputs_reels/        sorties d'exécution (2.4 MB — ignorées par .gitignore)
|   +-- outputs_reference/    références (952 KB)
|   +-- scripts/              compare_outputs, generate_matrix, run_tests
+-- tests/                    Suite pytest moderne (3 351 LOC, 170 tests)
|   +-- functional/           test_config, test_duplicates, test_exif_cache, test_file_manager,
|   |                         test_organizer, test_quarantine
|   +-- perf/                 test_perf (benchmark)
|   +-- smoke/                test_imports, test_ui_v3, test_ux_v4 (80 tests rapides)
|   +-- stress/               test_stress
|   +-- volume/               test_volume
|   +-- conftest.py
|   +-- test_modules.py
+-- tools/                    Scripts d'analyse (audit breakdown + visual_audit)
+-- .gitignore                Python + assets propres
+-- AUDIT.md                  Ce fichier
+-- AUDIT_EXE.md              Audit taille .exe (mémoire persistante)
+-- LICENSE                   MIT + Commons Clause
+-- Makefile                  install / lint / test / build / clean
+-- README.md                 Anglais, 300 lignes, structure projet OBSOLÈTE (cf. §11)
+-- RELEASE_1.0.0.md          Notes release v1
+-- audit_report.html         Livrable audit .exe (Phase précédente)
+-- audit_report.md           Ancien audit (mai 2026)
+-- build.py                  CLI PyInstaller (release / debug / light)
+-- build_report.md           Compte-rendu build
+-- main.py                   shim qui appelle src.main:main
+-- pyproject.toml            PEP 621
+-- requirements.txt          Doublon des deps de pyproject
```

---

## 4. Cartographie du code

### Points d'entrée
| Entrée | Cible | Usage |
|---|---|---|
| `python main.py` | `src.main:main` → `PhotoOrganizerApp().mainloop()` | Lancement GUI |
| `python -m src.cli.duplicate_cli` | `duplicate_cli.main` | CLI doublons (existe, **pas câblé** dans `pyproject.scripts`) |
| `photo-organizer` (entry point) | `src.main:main` | Déclaré dans `pyproject.toml`, GUI |
| Tag git `v*` (CI) | `.github/workflows/release.yml` | Build PyInstaller + checksums + release GH |

### Modules internes & dépendances (vue logique)

```
                ┌──────────────────────────────────────┐
                │            src/main.py               │
                │  check_dependencies() + bootstrap    │
                └────────────────┬─────────────────────┘
                                 │
                                 ▼
                ┌──────────────────────────────────────┐
                │       src/ui/app.py (PhotoOrganizerApp)│  ◄── tkinterdnd2 (opt)
                └──┬───────────┬────────────┬──────────┘
                   │           │            │
                   ▼           ▼            ▼
            ┌──────────┐ ┌─────────┐ ┌──────────────────┐
            │ frames/  │ │ theme.py│ │ tooltip(s).py    │
            │ 4 onglets│ │ + fonts │ │  attach_tooltip  │
            └────┬─────┘ └─────────┘ └──────────────────┘
                 │
   ┌─────────────┼─────────────────────────────────┐
   ▼             ▼            ▼                    ▼
organize_   duplicates_  history_           settings_
frame.py    frame.py     frame.py           frame.py
(3.4k LOC)  (1.2k LOC)   (0.4k LOC)         (0.6k LOC)
   │             │             │                    │
   └─────────────┴─────────────┴────────┐           │
                                         ▼           ▼
                          ┌──────────────────────────────────┐
                          │      src/core/operations/        │
                          │  file_manager, organizer,        │
                          │  duplicate_finder, duplicate_mgr,│
                          │  quarantine                       │
                          └──────────────┬───────────────────┘
                                         ▼
                          ┌──────────────────────────────────┐
                          │      src/core/metadata/          │
                          │  exif_extractor, date_extractor, │
                          │  camera_detector, gps_processor  │
                          └──────────────┬───────────────────┘
                                         ▼
                          ┌──────────────────────────────────┐
                          │         src/utils/               │
                          │  cache (EXIF), hash_cache,       │
                          │  config (JSON), logger           │
                          └──────────────────────────────────┘
```

### Dépendances externes (manifest vs imports réels)

| Lib | Manifeste ? | Importée ? | Verdict |
|---|---|---|---|
| customtkinter | ✅ | ✅ (ui partout) | OK |
| darkdetect | ✅ | ✅ (auto via ctk) | OK |
| Pillow | ✅ | ✅ (PIL.Image, ExifTags) | OK |
| exifread | ✅ | ✅ (exif_extractor) | OK |
| **piexif** | ✅ | ❌ (0 import) | **MORT** — à retirer |
| pillow-heif | ✅ | ✅ (register_heif_opener) | OK, mais cf. AUDIT_EXE F-03 |
| **requests** | ✅ | ✅ 1 GET (gps_processor lazy) | Remplaçable par `urllib.request` |
| PyYAML | non listé | ✅ (config YAML duplicates) | **manquant dans `requirements.txt`** |
| tkinterdnd2 | non listé | ✅ optionnel (try/except) | OK (extras `dev` ou opt) |
| plyer | non listé | ✅ optionnel | OK |
| send2trash | non listé | ✅ optionnel | OK |

### Services externes / I/O critiques

| Service | Usage | Config | Robustesse |
|---|---|---|---|
| Nominatim (OSM) | reverse geocoding GPS | `geocoding_enabled` (default ON) | `try/except` + timeout 5s, fallback "Lat_x_Lon_y" |
| Système fichiers | scan, copy, move, rollback, quarantine | n/a | gestion erreurs présente, logs détaillés |
| SQLite local | cache hash + cache EXIF dans `%LOCALAPPDATA%` | `%LOCALAPPDATA%\PhotoOrganizer\` | try/except + auto-création |
| Logs fichier | `%LOCALAPPDATA%\PhotoOrganizer\logs\photoorganizer.log` | rotation N/A | OK |

Aucune dépendance à des credentials, API keys, secrets. Pas de `.env` requis.

---

## 5. Inventaire fonctionnel (par onglet / module)

### Onglets UI

| Onglet | Fichier | Rôle | État |
|---|---|---|---|
| Organisation | `ui/frames/organize_frame.py` (3 423 LOC) | Sélection source/dest, options (date/camera/GPS), renommage, exécution + cancel, drag-and-drop | ✅ fonctionnel (refonte v2.3 en cours sur cette branche) |
| Doublons | `ui/frames/duplicates_frame.py` (1 213 LOC) | Détection doublons multi-algos (MD5/SHA1/Blake3), gestion (delete/move/quarantine), exports CSV/HTML/JSON | ✅ fonctionnel |
| Historique | `ui/frames/history_frame.py` (398 LOC) | Liste opérations, rollback par session, détails | ✅ fonctionnel (depuis fix B5/B6 partage FileManager) |
| Paramètres | `ui/frames/settings_frame.py` (615 LOC) | Thème, langue (FR seul), cache, géocodage, logs, notifications, drag-and-drop, raccourcis | ✅ fonctionnel |

### Modules métier

| Module | Fichier | Rôle | État |
|---|---|---|---|
| FileManager | `core/operations/file_manager.py` | Liste, copy, move, rollback, history, clear | ✅ |
| SmartOrganizer | `core/operations/organizer.py` | Plan d'organisation (date/camera/GPS combinés), exécution avec cancel | ✅ |
| DuplicateFinder | `core/operations/duplicate_finder.py` | Hash multi-algo + scan parallèle (ThreadPoolExecutor) | ✅ |
| DuplicateManager | `core/operations/duplicate_manager.py` | Décide action sur groupes (priorité dirs, regex, glob), gère exclusions corbeille | ✅ |
| QuarantineManager | `core/operations/quarantine.py` (nouveau, non commit) | Mise en quarantaine réversible avec metadata.json | 🟡 implémenté, non commit |
| ExifExtractor | `core/metadata/exif_extractor.py` | 4 méthodes en cascade (exifread → PIL → pillow_heif → exiftool subprocess) | 🟡 fallback ExifTool cassé (chemin invalide) |
| DateExtractor | `core/metadata/date_extractor.py` | Date EXIF + fallback nom fichier (regex) + mtime | ✅ |
| CameraDetector | `core/metadata/camera_detector.py` | Make/Model EXIF + heuristiques préfixes fichiers (PXL_, VID_, IMG_) | ✅ |
| GPSProcessor | `core/metadata/gps_processor.py` | DMS→decimal, reverse geocoding Nominatim, distance haversine | ✅ |
| MetadataCache | `utils/cache.py` | Cache EXIF 2 niveaux (RAM + SQLite) | ✅ (T-114 fix) |
| HashCache | `utils/hash_cache.py` | Cache hash SQLite avec TTL | ✅ |
| ConfigManager | `utils/config.py` | AppConfig dataclass + JSON persist | ✅ |
| Logger | `utils/logger.py` | Setup + rotation + niveau dynamique | ✅ |
| Scheduler | `core/scheduler.py` | Threading.Timer wrapper — usage non clair, à vérifier | 🟡 |
| duplicate_cli | `cli/duplicate_cli.py` (767 LOC) | CLI complet pour mode doublons | 🟡 **non câblé** dans `pyproject.scripts` |
| DuplicateReporter | `reports/duplicate_reporter.py` | Rapports CSV/JSON/HTML/Markdown | ✅ |

### Modules orphelins / morts

| Module | Fichier | Statut | Recommandation |
|---|---|---|---|
| `src/modules/__init__.py` | Façade ré-exportant `core.operations.*` | ❌ **Jamais importé** (`grep` 0 résultat hors lui-même) | À supprimer (Phase 2) |
| ExifTool fallback dans `exif_extractor.py:71` | Cherche `assets/exiftool.exe` au lieu de `assets/tools/exiftool.exe` | ❌ Chemin cassé | Corriger ou retirer (cf. AUDIT_EXE F-01) |
| `audit/` (8 fichiers) | Rapports d'audit historiques mai 2026 | ⚠️ Plus à jour | Archiver dans `docs/archives/` ou supprimer |
| `audit_report.md` (racine) | Ancien rapport mai 2026 | ⚠️ Plus à jour | Archiver / supprimer |
| `build_report.md` | Compte-rendu build | ⚠️ Ancien | Archiver |

---

## 6. Artefacts polluants détectés

| Élément | Taille | Statut | Action |
|---|---:|---|---|
| `.mypy_cache/` | **20 MB** | Présent (gitignored ✅) | À supprimer du disque, gardé ignoré |
| `__pycache__/` (récursif) | 2.2 MB | Présent (gitignored ✅) | `make clean` |
| `.pytest_cache/` | 23 KB | OK | gitignored |
| `.ruff_cache/` | 35 KB | OK | gitignored |
| `.coverage` | 52 KB | OK | gitignored |
| `.benchmarks/` | 0 | Vide | OK |
| `tools/_exe_listing.txt` | ~40 KB | Généré par mon audit | À ignorer (`tools/_*`) |
| `test/outputs_reels/` | 2.4 MB | Sorties d'exécution | gitignored ✅ |
| `test/outputs_reference/` | 952 KB | Références versionnées | OK (besoin pour comparaison) |
| `test/inputs/` | 1.4 MB | Fixtures binaires | OK (besoin pour tests) |
| `audit/`, `audit_report.md`, `build_report.md` | ~80 KB | Docs anciennes | À déplacer en `docs/archives/` |

**Secrets** : aucun détecté (grep API key / password / token / bearer = 0).
**Données perso** : aucune photo personnelle dans le repo (uniquement fixtures de test génériques dans `test/inputs/`).
**Paths absolus** : seulement dans docstrings/tooltips (exemples utilisateur) — pas dans la logique.

---

## 7. Code mort / duplications

### Imports inutilisés (ruff F401)
| Fichier | Ligne | Import |
|---|---:|---|
| `src/main.py` | 25 | `import customtkinter` (test dispo — garder avec `# noqa: F401`) |
| `src/main.py` | 30 | `from PIL import Image` (idem) |
| `src/core/operations/duplicate_manager.py` | 36 | `from send2trash import send2trash` (sentinelle, garder noqa) |
| `src/core/operations/quarantine.py` | 41 | `from dataclasses import field` (réellement mort, à retirer) |
| `src/cli/duplicate_cli.py` | ? | imports YAML conditionnels |

**Total ruff stats** : 21 erreurs, dont 13 `E402` (imports pas en tête de fichier — souvent justifiés par le `sys.path.insert` avant import), 5 `F401`, 2 `I001` (ordre imports), 1 `E722` (bare except).

### Duplications structurelles
- `requirements.txt` (racine) + `pyproject.toml` (`[project] dependencies`) : doublons. Le `requirements.txt` est figé et obsolète (manque `pyyaml`).
- `src/LICENSE` + `LICENSE` (racine) : doublon.
- `src/README.md` (court, ancien) + `README.md` (racine, à jour).
- `src/requirements.txt` (vieux) + `requirements.txt` (racine).

### Modules / fonctions non appelées
- `src/modules/__init__.py` : façade complète, jamais importée par personne ailleurs que ce fichier lui-même.
- `src/core/scheduler.py` : `threading.Timer` wrapper — à vérifier si encore utilisé.
- `tools/visual_audit.py` : script standalone, usage unclear.

### Documentation obsolète
- `README.md:212-236` décrit une structure projet **complètement obsolète** (`core/file_operations.py`, `gui/`, etc.) qui ne correspond plus au repo actuel.
- `README.md:152-161` documente une commande PyInstaller qui ne correspond pas à `build.py` actuel.

---

## 8. CI/CD & qualité

| Élément | Statut | Détail |
|---|---|---|
| Tests collectés | ✅ 170 | smoke (80), functional (~60), perf, stress, volume, test_modules |
| Tests smoke pass | ✅ 80/80 en 7 s | sain |
| Couverture | 🟡 ~70 % modules métier (rapport_qualification.md) | OK pour core, faible sur UI |
| CI Windows | ✅ `.github/workflows/ci.yml` | ruff + pytest sur push/PR vers main |
| CI Release | ✅ `.github/workflows/release.yml` | Build PyInstaller + checksums + release GH sur tag `v*` |
| Lint ruff | 🟡 21 errors | E402 (acceptables), 5 F401 à nettoyer |
| Bandit | ✅ 0 High (depuis B4 fix MD5 `usedforsecurity=False`) |  |
| Mypy | 🟡 cache présent, pas dans CI | typings partiels |

⚠️ **Le workflow `release.yml` (lignes 27-63) duplique la logique de `build.py` en YAML**, et utilise des arguments différents (`--hidden-import piexif`, anciens excludes…). À factoriser : faire que la CI appelle `python build.py`.

---

## 9. Sécurité & conformité

| Item | Statut |
|---|---|
| Secrets committés | ✅ Aucun |
| `.env` exigé | ✅ Non |
| Dépendances avec CVE critiques | 🟡 À vérifier (`pip-audit` non lancé en CI) |
| Données personnelles | ✅ Aucune dans le repo |
| Manipulation réseau | 🟡 1 GET Nominatim (HTTPS, OSM public) — `User-Agent` propre, pas de tracking |
| Manipulation FS destructive | ⚠️ Move/delete réversible via Historique + Quarantaine (B5/B6/F8 fix), TRASH via send2trash si dispo |
| LICENSE compatibilité | ✅ MIT compat avec Pillow (MIT-CMU), CTk (CC0), exifread (BSD), pillow_heif (BSD), requests (Apache 2.0), tkinterdnd2 (MIT). **Commons Clause restreint la revente** par tiers — ne s'applique pas à l'auteur. |

---

## 10. Documentation existante (inventaire)

| Doc | Contenu | Statut |
|---|---|---|
| `README.md` (racine) | EN, pitch produit, badges, installation, usage, formats, build | 🟡 Structure projet obsolète (§11), commande PyInstaller dépassée |
| `RELEASE_1.0.0.md` | Notes v1 | OK historique |
| `audit/01_inventaire.md`...`06_build.md` | Audit mai 2026 (rapport 7 phases) | ⚠️ Obsolète depuis v2.0.0 |
| `audit/RAPPORT_FINAL.md` | Synthèse audit | ⚠️ Réf v2.0.0 / 44 MB exe (avant optim) |
| `audit/PROMPT_ORGANIZE_ROADMAP.md` | Roadmap onglet Organisation v2 | OK |
| `audit_report.md` (racine) | Ancien audit | ⚠️ Doublon avec `audit/` |
| `build_report.md` (racine) | Compte-rendu build | ⚠️ Ancien |
| `test/README.md` | Doc suite qualif "métier" (matrice Excel) | OK |
| `test/rapport_qualification.md` | Rapport qualif itération | OK |
| `test/validation_ihm.html` | Captures IHM commentées | OK |
| `AUDIT_EXE.md` | Audit taille .exe (Phase précédente) | À jour |
| `audit_report.html` | Idem version HTML | À jour |

**Manquants standards** (Phase 3 attendue) :
- `CHANGELOG.md` — absent
- `CONTRIBUTING.md` — absent (section dans README seulement)
- `SECURITY.md` — absent
- `CLAUDE.md` — absent (à créer Phase 3)
- `PROJECT_OVERVIEW.html` — absent (à créer Phase 3)
- `docs/MEDIA.md` — absent
- `docs/ARCHITECTURE.md` — absent (le code est complexe, ce serait utile)

---

## 11. Incohérences notables

| # | Endroit | Constat |
|---|---|---|
| I-1 | `README.md:212-236` | Structure projet décrite ≠ structure réelle |
| I-2 | `README.md:152-161` | Commande PyInstaller ne correspond pas à `build.py` |
| I-3 | `LICENSE` (racine) | `Copyright (c) 2025 PhotoManager Pro` — nom du holder différent du projet |
| I-4 | `.github/workflows/release.yml` | Dupplique la logique de `build.py` en YAML avec args divergents |
| I-5 | `requirements.txt` (racine) + `pyproject.toml` | Doublon, requirements obsolète (manque pyyaml) |
| I-6 | `src/LICENSE`, `src/README.md`, `src/requirements.txt` | Doublons résiduels d'une ancienne structure |
| I-7 | `src/modules/` | Façade morte (jamais importée) |
| I-8 | `src/cli/duplicate_cli.py` | CLI complet existe mais `pyproject.scripts` n'expose que la GUI |
| I-9 | `build.py:71` | `assets/exiftool.exe` cherché mais l'exe est dans `assets/tools/exiftool.exe` |
| I-10 | `pyproject.toml:39` | `package-data` inclut `*.svg` — aucun SVG dans le projet |
| I-11 | Deux suites de tests : `test/` (qualif Excel) + `tests/` (pytest) | Coexistence légitime mais confusion possible |

---

## 12. Métriques globales

| Métrique | Valeur |
|---|---:|
| Lignes Python (src/) | **16 021** |
| Fichiers Python (src/) | 38 |
| Lignes Python (tests/) | 3 351 |
| Fichiers Python (tests/) | 20 |
| Tests pytest collectés | 170 |
| Tests smoke pass | 80/80 en ~7 s |
| Module le plus gros | `ui/frames/organize_frame.py` (~3 400 LOC) |
| .exe actuel (Win64, onefile) | **37.06 MB** |
| Cible .exe optimisée (cf. AUDIT_EXE) | ~22 MB (−40 %) |
| Dépendances runtime (manifest) | 7 (dont 1 morte `piexif`) |
| Dépendances effectivement utilisées | 8 (incl. `pyyaml` non listé) |
| Bandit High | 0 |
| Issues ruff | 21 (toutes mineures) |
| Commits récents (5) | refonte v2.3 onglet Organisation, retours testeur |

---

## 13. Constat global

**Forces**
- Code structuré (Python conventionnel, séparation UI / core / utils claire).
- Suite pytest moderne avec 170 tests, smoke à 100 % en 7 s.
- CI GitHub Actions fonctionnelle (lint + test + release auto sur tag).
- Multi-couches (cache 2-tier, hash multi-algo, rollback réversible, quarantine).
- Application fonctionnelle, distribuable (.exe 37 MB), avec stable v1.0.0 publiée.
- Audit `.exe` déjà fait (AUDIT_EXE.md → −40 % attendu).

**Faiblesses**
- README structure projet obsolète → barrière à la contribution / découverte.
- Doublons `requirements.txt` / `pyproject.toml`, `LICENSE` × 2, `README.md` × 2, dépendances mortes (`piexif`).
- Façade `src/modules/` morte, fallback ExifTool câblé sur chemin invalide.
- Workflows CI release ne réutilise pas `build.py` (double maintenance).
- `audit/` + `audit_report.md` + `build_report.md` à la racine = bruit visuel.
- Absent : `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md`, `PROJECT_OVERVIEW.html`, `docs/ARCHITECTURE.md`.
- Hardcodé Windows only (paths Windows + tests CI Windows uniquement) — pas un défaut mais à expliciter.

**Verdict d'audit Phase 1**
Projet **mature techniquement** (16k LOC organisées, tests, CI, releases) mais **insuffisamment présentable** (doc obsolète, fichiers de méta-organisation manquants). Travail de restructuration **modeste** attendu en Phase 2 (déplacements + suppressions ciblées, 1-2 j-h). Phases 3+ (fichiers standards + dashboard + monétisation) : 2-3 j-h supplémentaires.

---

## En attente — Phase 2 (à venir sur GO)
Je proposerai :
1. Structure cible définitive (déplacements / renommages / suppressions).
2. Réconciliation `requirements.txt` ↔ `pyproject.toml`.
3. Nettoyage `audit/` + doublons racine.
4. Suppression de `src/modules/` (façade morte) et fix chemin ExifTool.
5. Refactor : `release.yml` appelle `build.py` (DRY).

**Stop. J'attends ton GO avant d'appliquer.**

---

## Phase 2 — appliquée le 2026-05-19

Restructuration faite : 572 fichiers renommés (dont 561 fixtures `test/ → test_data/`), 4 suppressions (doublons + façade morte), 7 refactors (LICENSE Apache-2.0, pyproject, requirements miroir, .gitignore, fix ExifTool, release.yml DRY, README structure obsolète retirée), 7 créations (`docs/`, `src/photoorganizer_pro/` stub). Tests : 170/170 verts.

## Phase 3 — appliquée le 2026-05-19

Fichiers standards créés : `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md`, `PROJECT_OVERVIEW.html`, `docs/ARCHITECTURE.md`, `docs/MEDIA.md`. `README.md` réécrit de bout en bout (pitch, badges, install, usage, features, archi, roadmap, freemium, contact).

---

## 14. Gaps — audit de complétude (Phase 4)

Évaluation post-Phase 3. Statuts : 🟢 OK · 🟡 à compléter · 🔴 bloquant pour valorisation publique.

### 14.1 Synthèse

| # | Dimension | Statut | Priorité | Effort |
|---|---|:---:|:---:|:---:|
| D-01 | Onboarding (install + run < 5 min) | 🟢 | — | — |
| D-02 | Configuration (paths/secrets externalisés) | 🟢 | P2 | 15 min |
| D-03 | Robustesse (gestion erreurs I/O, messages utilisateur) | 🟡 | P2 | 10 min |
| D-04 | Packaging (artefact distribuable testé) | 🟢 | — | — |
| D-05 | Cross-platform | 🟡 | P2 | 4-8 h si Linux/macOS visé |
| D-06 | Tests (smoke + chemins critiques) | 🟢 | P1 | 1-2 j si couverture UI cible |
| D-07 | Docs (compréhension en 30 s) | 🟢 | — | — |
| D-08 | **Démo visuelle** (GIF/vidéo/screenshot) | 🔴 | **P0** | **4-6 h** |
| D-09 | Versionning (tag + release publié) | 🟡 | P1 | 30 min |
| D-10 | Sécurité (secrets, CVE deps) | 🟡 | P1 | 1 h |

**Bilan** : un bloquant (D-08 démo), deux priorités P1 (D-06 tests UI, D-09 versionning, D-10 sécurité CI), le reste OK ou cosmétique. **Estimation totale pour fermer P0+P1** : environ **6-8 h**.

### 14.2 Détail par dimension

#### D-01 — Onboarding 🟢
- `.exe` Windows téléchargeable depuis GitHub Releases (1 min).
- Depuis sources : `git clone → pip install -e ".[dev]" → python main.py` (< 5 min).
- README rewrité avec sections Installation et Usage.
- **OK. Aucune action.**

#### D-02 — Configuration 🟢 (note P2 cosmétique)
- Aucun credential, API key, secret committé (grep vérifié).
- Pas de `.env` requis. URL Nominatim hardcodée (acceptable, c'est une convention).
- Tous les paths runtime sont relatifs ou résolus via `%LOCALAPPDATA%`.
- **P2 (optionnel)** : externaliser l'URL Nominatim dans `AppConfig` pour permettre un fork à utiliser un autre fournisseur de géocodage. Effort 15 min.

#### D-03 — Robustesse 🟡
- `try/except` partout sur les I/O critiques (FS, EXIF cascade, geocoding, hash).
- Logs détaillés rotation fichier `%LOCALAPPDATA%\PhotoOrganizer\logs\`.
- Quarantaine réversible + Rollback historique.
- Cancel propagé à `SmartOrganizer`.
- **P2** : 1 `bare except` détecté `src/core/metadata/exif_extractor.py:193` (decode UTF-8 d'un tag binaire) — remplacer par `except UnicodeDecodeError`. Effort 5 min.
- **P2** : 13 erreurs `ruff E402` (imports tardifs après `sys.path.insert`) — justifiées mais à marquer `# noqa: E402` pour faire passer le lint propre. Effort 5 min.

#### D-04 — Packaging 🟢
- `.exe` Windows 37 MB onefile produit par `python build.py`.
- Variantes : `release` (windowed), `debug` (console), `light` (minimal).
- Release auto sur tag git via `.github/workflows/release.yml` (Phase 2 : maintenant appelle `build.py` au lieu de dupliquer la commande).
- Checksums SHA-256 inclus.
- Non signé (Defender SmartScreen warning au premier lancement) — limitation acceptée, documentée dans SECURITY.md.
- Optimisation taille planifiée (37 → 22 MB, cf. [docs/exe-optimization.md](docs/exe-optimization.md)).
- **OK. Aucune action immédiate.**

#### D-05 — Cross-platform 🟡 (selon objectif)
- Code core probablement portable (`pathlib`, `os.path`, `sqlite3`, `subprocess` avec creationflags conditionnels).
- `creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0` déjà conditionné.
- CI Windows-only.
- Aucun test sur Linux/macOS.
- Si **objectif Windows-only assumé** (cible utilisateur photo amateur) → **OK** (P3 = jamais).
- Si **objectif multi-OS** → P2, effort 4-8 h : matrice CI `[windows-latest, ubuntu-latest, macos-latest]`, vérifier `tkinter` packagé sur chaque, adapter `build.py` pour produire des artefacts par OS.

#### D-06 — Tests 🟢 (note P1 sur couverture UI)
- **170 tests pytest** organisés en 5 catégories.
- Couverture **~70 %** modules métier (rapporté dans `test_data/rapport_qualification.md`).
- Couverture **UI faible** : 80 tests smoke vérifient l'instanciation et le no-Toplevel, mais peu de tests fonctionnels sur les actions UI (clic, validation, etc.).
- Suite qualif "métier" séparée dans `test_data/` (matrice Excel 189 tests + checklist IHM HTML).
- **P1** : compléter les tests UI fonctionnels (notamment `tests/functional/test_organize_frame.py` qui n'existe pas). Effort 1-2 j si on vise 50 % couverture UI.

#### D-07 — Docs 🟢
- README rewrité avec démo placeholder + install + usage 30 s + features + archi.
- `docs/ARCHITECTURE.md`, `docs/MEDIA.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md`, `PROJECT_OVERVIEW.html` tous présents.
- Anciens rapports archivés dans `docs/archives/`.
- **OK. Aucune action.**

#### D-08 — Démo visuelle 🔴 **BLOQUANT**
- **Aucun asset visuel n'existe** : aucune capture, aucun GIF, aucune vidéo.
- Le README pointe vers `docs/media/screenshot-organize.png` qui n'existe pas → **image cassée** en haut du README.
- Liste complète des assets à produire dans [docs/MEDIA.md](docs/MEDIA.md) : 8 captures (P0/P1/P2), 4 GIFs, 2 vidéos, 1 logo SVG, 1 bannière.
- **Priorité P0** : produire au moins **S-01** (`screenshot-organize.png`) et **G-01** (`demo-organize.gif`) pour rendre le README présentable. Effort **4-6 h** (lancement de l'app + captures + retouches + compression).
- Sans ces deux assets, toute communication publique (Product Hunt, LinkedIn, Show HN) sera handicapée.

#### D-09 — Versionning 🟡
- Tag `v1.0.0` posé et release publiée (déc 2025) ✅.
- Tag `v2.1.0` posé sur le repo distant (`ed5b485`) ✅.
- **Incohérence détectée** : `pyproject.toml` et `src/ui/app.py` indiquent **`2.0.0`** alors que le dernier tag publié est **`v2.1.0`**. La version du code est en retard sur le tag.
- **P1** : aligner. Deux options :
  - **Option A** (recommandée) : passer la version du code à `2.2.0-dev` (puisque la branche actuelle ajoute la refonte v2.3 = quarantaine, panneau Organisation, etc.). Effort 5 min.
  - **Option B** : bumper le code à `2.1.1` si on considère que les changements actuels n'ajoutent rien de nouveau (peu probable vu le contenu de la branche).
- Pas de `CHANGELOG.md` jusqu'à Phase 3 — maintenant en place (avec rétro v1.0.0 + v2.0.0 → à compléter v2.1.0 dans une prochaine maj).

#### D-10 — Sécurité 🟡
- 0 secret dans le repo ✅ (grep + `git log -p | grep -iE "api_key|password|secret|token"` propre).
- Bandit 0 High ✅.
- `pip-audit` lancé manuellement : aucune CVE remontée sur les deps PhotoOrganizer (`customtkinter`, `Pillow`, `exifread`, `pillow-heif`, `requests`, `PyYAML`).
- `SECURITY.md` créé en Phase 3.
- **P1** : ajouter `pip-audit` au workflow CI (`ci.yml`) — étape `pip-audit -r requirements.txt --strict`. Effort 15 min.
- **P1** : ajouter une étape `bandit -r src/ -ll` au workflow CI (actuellement seulement ruff). Effort 5 min.
- **P2** : signer le binaire .exe avec un certificat Authenticode (≈ 250 €/an, hors budget projet OSS — limitation documentée).

### 14.3 Plan d'action P0 → P1

| Ordre | Action | Dimension | Effort | Bloque ? |
|---:|---|---|---|---|
| 1 | Produire S-01 (screenshot Organisation) + G-01 (GIF démo) | D-08 | 4-6 h | Communication publique |
| 2 | Aligner version `pyproject.toml` + `ui/app.py` → `2.2.0-dev` (ou `2.1.1`) | D-09 | 5 min | Cohérence releases |
| 3 | Ajouter `pip-audit` + `bandit` au CI | D-10 | 30 min | Confiance des contributeurs |
| 4 | Remplacer le `bare except` `exif_extractor.py:193` par `except UnicodeDecodeError` | D-03 | 5 min | Lint propre |
| 5 | Compléter `CHANGELOG.md` avec la rétro v2.1.0 (si non documentée) | D-09 | 15 min | Cohérence |
| 6 | (Optionnel P1) Ajouter `tests/functional/test_organize_frame.py` | D-06 | 1-2 j | Confiance refactor v2.3 |
| 7 | (Optionnel P2) Externaliser URL Nominatim dans `AppConfig` | D-02 | 15 min | Fork friendly |
| 8 | (Optionnel P2) Matrice CI multi-OS si stratégie cross-platform | D-05 | 4-8 h | Élargir audience |

**Cumul P0+P1 (lignes 1-5)** : environ **5-7 h** pour rendre le projet pleinement présentable et "shippable" publiquement.

---

## Journal de l'audit projet

| Date | Phase | Action |
|---|---|---|
| 2026-05-19 | 1 | Inventaire complet (LOC, modules, deps, artefacts, code mort, incohérences). |
| 2026-05-19 | 2 | Restructuration appliquée — 572 renommages, 4 suppressions, 7 refactors, 0 régression de test. |
| 2026-05-19 | 3 | Fichiers standards générés (README rewrité, CHANGELOG, CONTRIBUTING, SECURITY, CLAUDE, PROJECT_OVERVIEW, docs/ARCHITECTURE, docs/MEDIA). |
| 2026-05-19 | 4 | Audit de complétude — 10 dimensions évaluées, 1 P0 (démo visuelle), 4 P1, plan d'action 6-8 h. |

