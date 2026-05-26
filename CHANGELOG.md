# Changelog

All notable changes to PhotoOrganizer are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 2.2.0-dev

### Added
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

[Unreleased]: https://github.com/Kiriiaq/PhotoOrganizer/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/Kiriiaq/PhotoOrganizer/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/Kiriiaq/PhotoOrganizer/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/Kiriiaq/PhotoOrganizer/releases/tag/v1.0.0
