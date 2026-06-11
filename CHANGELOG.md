# Changelog

All notable changes to PhotoOrganizer are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 2.3.0-dev

### Pivot stratégique (2026-05-26)

PhotoOrganizer abandonne le modèle "édition Pro séparée" (19/49/99 € avec batch CLI / watch-folder / plugins) au profit d'un modèle **trial + unlock** type Sublime Text :

- **Une seule app**, plus de variante Pro.
- **10 tris gratuits**, illimité après activation.
- **Prix unique : 10 € lifetime**, clé universelle liée au premier PC qui l'active (machine binding via MachineGuid + Volume Serial).
- **Aucune réémission** (changement PC / réinstall Windows / disque mort = nouvelle clé). Politique stricte affichée, geste commercial possible au cas par cas.

Cf. [docs/MONETIZATION.md](docs/MONETIZATION.md) (réécrit) et [NEXT_STEPS.html](docs/NEXT_STEPS.html) (procédure pas-à-pas).

### Added — Phase 1 du code (livrée 2026-05-26)

- **`src/utils/licensing.py`** *(nouveau)* — Compteur d'usages signé HMAC + machine binding.
  - Stockage `%LOCALAPPDATA%\PhotoOrganizer\usage.dat` (JSON enveloppé + signature HMAC SHA-256).
  - Anti-tampering : modification manuelle du `count` → reset à 0 (HMAC mismatch).
  - Anti-copie : `usage.dat` copié depuis un autre PC → reset à 0 (machine_id mismatch).
  - API publique : `get_state()`, `record_successful_organize()`, `can_organize_now()`, `activate_key()`, `get_machine_id()`, `get_machine_id_short()`.
  - Constantes : `TRIAL_LIMIT = 10`, `WARNING_THRESHOLDS = (8, 9)`.
- **`src/photoorganizer_pro/license/validator.py`** *(adapté)* — Machine binding au premier `save_license_key()`.
  - Nouveau format JSON pour `license.dat` : `{"payload": {"key", "machine_id_bound", "bound_at"}, "sig"}`.
  - Le `LicenseInfo` expose désormais `machine_id_bound: Optional[str]`.
  - `load_active_license()` vérifie l'enveloppe HMAC + le binding machine. Tolérant (renvoie `None` au lieu de lever).
  - Rétrocompatibilité avec l'ancien format (clé brute) préservée pour les tests historiques.
- **`src/ui/frames/organize_frame.py`** *(adapté)* — Hook trial+unlock + modal d'activation inline.
  - Hook dans `_organize_files()` : `can_organize_now()` → si bloqué, ouvre `_show_unlock_panel()` et stoppe.
  - Warnings dans la confirmation messagebox aux seuils `count == 8` et `count == 9`.
  - Compteur incrémenté UNIQUEMENT après `result.success > 0` et `not _cancel_requested` (un crash ou un Ctrl+C ne consomme pas).
  - Nouveau `_show_unlock_panel()` — utilise `_show_inline_panel` (pas de Toplevel, conformément à la préférence projet).
  - Champ entry pour coller la clé + bouton "Acheter" (ouvre Lemon Squeezy via `webbrowser.open`) + feedback inline avec messages d'erreur localisés (clé invalide / bound à un autre PC / expirée).
- **`src/ui/app.py`** *(adapté)* — Badge global d'état licence.
  - Bouton `self.license_badge` dans le header (à droite, à gauche des boutons thème/aide).
  - Texte dynamique selon état : `"Essai N/10"` / `"Limite atteinte · Activer"` / `"Activée · MAC-XXXX-XXXX"`.
  - Couleurs : gris (normal) / orange (warnings 8-9) / rouge (bloqué) / vert (activé).
  - `refresh_license_badge()` callable depuis n'importe quel frame.
  - Clic sur le badge → ouvre le panneau d'activation dans l'onglet Organisation.

### Tests

- **`tests/functional/test_licensing.py`** *(nouveau)* — 17 tests (10 scénarios listés dans NEXT_STEPS §A.3 + bonus machine_id / badge).
- **`tests/smoke/test_ux_v4.py`** *(complété)* — 7 nouveaux tests : badge présent, refresh callable, texte cohérent avec `get_state()`, modal d'activation ne crée pas de Toplevel.
- **`tests/functional/test_pro_license.py`** *(inchangé)* — Les 14 tests historiques continuent à passer (rétrocompat préservée).
- **Bilan : 201 passed, 47 skipped (47 = tests Pro `batch/watch/plugins` deferred v3.0+).**

### Versioning

- Version bumpée à `2.3.0.dev0` dans `pyproject.toml`, `src/__init__.py`, `src/core/__init__.py`, et `src/ui/app.py` (`APP_VERSION`).
- À-propos de l'app corrigé : "Licence MIT" → "Licence Apache-2.0 (code) — Édition activable 10 € (binaire)".

### To do (avant tag v2.3.0)

- [ ] **Setup commercial** : Lemon Squeezy avec 1 produit unique à 10 €.
- [ ] **Privacy Policy** publiée (lien GitHub direct).
- [ ] **Auto-entreprise** si pas créée.
- [ ] **Assets visuels** : S-01 (capture onglet Organisation), G-01 (GIF démo 10s), S-02 (capture modal d'activation).
- [ ] **Tag v2.3.0** + GitHub Release.

### Changed (pivot — mise en cohérence doc)

- `CLAUDE.md` : nouveau modèle économique acté, modules Pro étiquetés "v3.0+", roadmap mise à jour.
- `docs/MONETIZATION.md` : réécriture complète. L'ancien contenu (analyse 8 voies, freemium 19/49/99) archivé dans `docs/archives/superseded_2026-05/MONETIZATION_old.md`.
- `NEXT_STEPS.html` : nouvelle procédure de rentabilisation post-pivot. Ancienne version (Lemon Squeezy 3 produits, calendrier 6 sem) archivée.
- `README.md` : section "Modèle économique" réécrite, roadmap simplifiée.
- `AUDIT.md` : ajout d'une Phase 8 actant le pivot et marquant Phase 5 (monétisation 19/49/99) comme superseded.

### Deferred to v3.0+

Modules Pro existants conservés intacts mais mis en sourdine, réactivation conditionnelle à la traction v2.x :

- `src/photoorganizer_pro/cli/batch_organize.py` (335 LOC, 10 tests skip)
- `src/photoorganizer_pro/scheduler/watch_folder.py` (279 LOC, 12 tests skip)
- `src/photoorganizer_pro/plugins/` (401 LOC, 25 tests skip)
- Entry points `photo-organizer-pro-batch` et `photo-organizer-pro-watch` commentés dans `pyproject.toml`.

Le module `src/photoorganizer_pro/license/` est conservé et **adapté** pour gérer la nouvelle logique trial+unlock (ajout de `machine_id_bound` dans `LicenseInfo` + binding à la 1ère activation).

## [2.2.0] — 2026-05-19

### Cleanup (ménage repo)
- Versions alignées : `src/__init__.py` et `src/core/__init__.py` passent de `2.0.0` à `2.2.0` (cohérence avec `pyproject.toml` et `src/ui/app.py`).
- `__author__` dans `src/core/__init__.py` corrigé : "Kiriiaq (Emmanuel Grolleau)" au lieu de la mention fictive "PhotoOrganizer Team".
- Lint ruff complet : passé de 67 erreurs à **0** (34 auto-fixées + 1 F811 doublon import + 3 E702 dépliés + config étendue pour exclure `test_data/scripts/generate_matrix.py`).
- Bandit High severity : 1 → **0** (`quarantine.py:165` SHA-1 désormais marqué `usedforsecurity=False`).
- Docstring `tools/smoke_exe.py` corrigée (`audit/` → `tools/`, suite au renommage Phase 2).
- Suppressions disque (~40 Mo libérés, tous gitignored) : `dist/PhotoOrganizer-2.0.0.exe` obsolète, `.benchmarks/`, `.pytest_cache/`, `.ruff_cache/`, `test_data/outputs_reels/`.
- Configuration ruff explicitement documentée : `ignore = ["E501", "E402"]` (justifications dans le `pyproject.toml`).

### Added — Pro features V1.1
- **Plugin API** (`src/photoorganizer_pro/plugins/`) :
  - `BasePlugin` abstract avec 5 hooks (`pre_organize`, `filter_file`, `rename`, `post_action`, `post_organize`).
  - `PluginManager` avec découverte via entry points pip ET dossier local `%LOCALAPPDATA%\PhotoOrganizer\plugins\`.
  - `OrganizeContext` partagé entre hooks d'un même batch (état dict libre).
  - Résilience aux exceptions plugin (log + continue, le batch ne s'arrête pas).
  - Plugin exemple `geotag_renamer` complet et documenté.
  - 25 tests fonctionnels.
- **Batch CLI Pro** complété (`src/photoorganizer_pro/cli/batch_organize.py`) :
  - Sous-commande `dedup` avec algos MD5 / SHA-1 / Blake3 + export rapport (CSV / JSON / HTML / Markdown).
  - Sous-commande `info` (état licence, ne nécessite pas de licence valide).
  - Mode `--dry-run` sur `organize` (n'écrit rien, montre options + échantillon).
  - Gestion KeyboardInterrupt avec cancel propagé à `SmartOrganizer`.
  - 10 tests fonctionnels (parsing, dispatch, licence gate, dry-run).
- **Watch-folder Pro** durci (`src/photoorganizer_pro/scheduler/watch_folder.py`) :
  - Refactor avec injection `sleep_fn` pour tests rapides.
  - Méthodes publiques testables : `is_watched`, `handle_path`, `poll_once`.
  - Résilience aux exceptions de l'organiseur (log + continue).
  - Anti-doublon via `_processed` set.
  - 12 tests fonctionnels.
- **Étude design Cloud Sync** (`docs/CLOUD_SYNC_DESIGN.md`) : analyse 10 backends, architecture proposée (via Plugin API existante), pricing, sécurité, RGPD, effort 14-19 j-h, métriques de décision T+3 mois.

### Added — Phase 3 audit (avant 2.2.0-dev)
- `src/photoorganizer_pro/` — placeholder package for the future Pro edition (proprietary).
- `docs/` directory with archives, exe-optimization audit, architecture and media inventories.
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md`, `PROJECT_OVERVIEW.html`.
- `photo-organizer-dedup` console script entry point (duplicate CLI now installable).
- Extras `dnd` and `toast` in `pyproject.toml` for optional `tkinterdnd2` and `plyer`.

### Changed
- **License**: switched from MIT + Commons Clause to **Apache License 2.0**.
- README rewritten end-to-end (French primary text, project structure aligned with reality).
- `test/` renamed to `test_data/` to remove the confusion with `tests/` (pytest suite).
- `.github/workflows/release.yml` now calls `python build.py` instead of duplicating the PyInstaller command.
- `pyproject.toml` reorganised: PEP 621 classifiers, URLs, optional extras, Apache-2.0 SPDX identifier.
- `requirements.txt` is now a synchronised mirror of `pyproject.toml` dependencies.

### Fixed
- ExifTool fallback path in `src/core/metadata/exif_extractor.py` (was pointing at `assets/exiftool.exe`, now correctly resolves `assets/tools/exiftool.exe`).
- 5 ruff F401 imports cleaned up; remaining "unused" imports are now marked `# noqa: F401` as availability sentinels (try/except blocks).
- `bare except` in `exif_extractor.py:193` (EXIF byte decoding) replaced with explicit `except UnicodeDecodeError`.
- Version mismatch: code was on `2.0.0` while the published tag was `v2.1.0`. Bumped to `2.2.0` to reflect the current branch's scope (Pro modules + organize tab v2.3 redesign).

### Security
- CI workflow extended: `bandit -r src -ll` runs on every push; `pip-audit --requirement requirements.txt --strict` runs in a dedicated job.

### Removed
- Dead `src/modules/` re-export façade (never imported externally).
- Duplicate `src/LICENSE`, `src/README.md`, `src/requirements.txt`.
- `piexif` dependency (was listed in manifests but never imported).
- **Bundled ExifTool Perl runtime** (`assets/tools/`, 34 MB on disk, ~10 MB compressed in EXE). The fallback subprocess was broken in practice (wrong hardcoded path) and primary readers (exifread, Pillow, pillow-heif) cover the supported use cases. Users who need the fallback can install `exiftool` system-wide (`winget install exiftool`). Removal also eliminates GPL/proprietary license tension for the upcoming Pro distribution.

## [2.1.0] — 2026-05-15

Industrialisation : pipeline CI/CD, packaging moderne, distribution professionnelle.

### Added
- Pipeline GitHub Actions complète (`.github/workflows/ci.yml` lint + tests Windows, `release.yml` build EXE automatique sur tag `v*`).
- `pyproject.toml` PEP 621 (remplace `setup.py`).
- Badge de téléchargement bien visible en haut du README.
- Template `.env.example` (remplace `.env` qui ne devait jamais être commit).

### Changed
- Packaging modernisé : entry point `photo-organizer` déclaré dans `pyproject.toml`.
- Release auto sur tag : génère release `windowed` + `debug`, attache `checksums-sha256.txt`.

## [2.0.0] — 2026-05-07

Major refactor and qualification pass (v1 → v2). See `docs/archives/audit_2026-05-07/RAPPORT_FINAL.md` for the full audit report.

### Added
- 4-tab interface: Organisation, Duplicates, History, Settings (CustomTkinter).
- Multi-criteria organisation: by date, camera model, GPS location, or hierarchical combination.
- Configurable rename templates with date / counter / model variables.
- Duplicate detection with parallel scan and three hash algorithms (MD5, SHA-1, Blake3).
- Quarantine-based reversible deletion (no more one-way `send2trash`).
- Two-tier metadata cache (in-memory + persistent SQLite).
- Geocoding via OpenStreetMap Nominatim (toggle in Settings).
- Drag-and-drop folder support (optional, via `tkinterdnd2`).
- Windows toast notifications for long operations (optional, via `plyer`).
- Keyboard shortcuts Ctrl+1..4 for tab navigation, F1 for About.
- Real-time source file counter in the Organisation tab.
- 170-test pytest suite (smoke, functional, perf, stress, volume) reaching ~70 % coverage on core modules.
- `Makefile` with `install / lint / test / build / clean / all` targets.
- GitHub Actions: CI (lint + tests on Windows) and Release (auto-build EXE on `v*` tags).
- `build.py` orchestrator with `--release` / `--debug` / `--light` modes.

### Fixed (vs v1.0.0)
- 3 critical runtime bugs (F821 NameError in lambdas, broken test imports, `OSError WinError 87` in ExifTool path probing).
- 4 features now share the same `FileManager` instance (history, rollback, sessions stay consistent).
- Bandit High issue: MD5 calls flagged `usedforsecurity=False`.
- `_cancel_operation` now actually propagates the cancel to `SmartOrganizer`.
- System recycle bins (`$Recycle.Bin`, `.Trash`, `System Volume Information`) are excluded automatically.

## [1.0.0] — 2025-12-14

Initial stable release.

### Added
- Modern CustomTkinter interface with dark/light theme support.
- Complete EXIF metadata extraction (Pillow + exifread + pillow-heif).
- Support for 45 file formats (images, RAW, videos).
- Multi-layer organisation (Date > Camera > GPS).
- Copy or move modes.
- Progress tracking with cancel button.
- Scrollable results window.
- Standalone Windows executable (~100 MB onefile).

[Unreleased]: https://github.com/Kiriiaq/PhotoOrganizer/compare/v2.2.0...HEAD
[2.2.0]: https://github.com/Kiriiaq/PhotoOrganizer/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Kiriiaq/PhotoOrganizer/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/Kiriiaq/PhotoOrganizer/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/Kiriiaq/PhotoOrganizer/releases/tag/v1.0.0
