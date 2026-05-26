# Contributing to PhotoOrganizer

Thank you for considering a contribution. PhotoOrganizer is a freemium project: the **core is and stays open-source under Apache-2.0**. Contributions to the core are welcome from anyone.

> The future **Pro edition** (under `src/photoorganizer_pro/`) is reserved for proprietary modules and is not currently open to external contributions. See [src/photoorganizer_pro/README.md](src/photoorganizer_pro/README.md).

---

## Quick start (development setup)

```bash
git clone https://github.com/Kiriiaq/PhotoOrganizer.git
cd PhotoOrganizer

# Recommended: isolated venv (build & dev)
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
source .venv/bin/activate         # Linux/macOS

pip install --upgrade pip
pip install -e ".[dev,dnd,toast]"

# Run the GUI from sources
python main.py

# Run the test suite (170 tests, ~25 s)
make test
```

Python 3.11+ required. The application targets Windows but the core (non-UI) modules should remain platform-agnostic where possible.

---

## How to contribute

### 1. Open an issue first (for non-trivial changes)

For bug reports, feature requests, or refactors larger than 50 lines, please open an issue describing the problem or the proposed change before writing code. This avoids wasted effort if the change is out of scope.

For typo fixes, comment improvements, or small bug fixes, a direct PR is fine.

### 2. Fork, branch, code

- Branch from `main` (default) or from the active feature branch if applicable.
- Branch naming convention: `feat/<short-topic>`, `fix/<issue-or-bug>`, `docs/<topic>`, `refactor/<area>`.
- Keep one logical change per PR.

### 3. Code style

- **Formatter / linter** : [ruff](https://github.com/astral-sh/ruff) (configured in `pyproject.toml`). Run `make lint` before pushing.
- **Line length** : 120.
- **Type hints** encouraged for new public functions and class signatures.
- **Docstrings** : style libre, mais documenter le *pourquoi* d'un choix non évident (français OU anglais — le projet est mixte).
- **Comments**: not redundant with code. Comment intent and non-obvious constraints, not what the code already states.

### 4. Tests

Every behavioural change must come with at least one test.

| Test type | Location | When |
|---|---|---|
| Smoke | `tests/smoke/` | Import path / availability checks, must stay < 10 s total |
| Functional | `tests/functional/` | Pure logic for one module |
| Volume | `tests/volume/` | Large input handling (1000+ files) |
| Stress | `tests/stress/` | Concurrent / repeated cycles |
| Perf | `tests/perf/` | Benchmarks with `pytest-benchmark` |

Run before pushing:

```bash
make test           # quick (no slow markers)
make test-all       # everything incl. slow + benchmarks
```

A PR that drops the test count or breaks `make test` will not be merged.

### 5. Commit messages

Format inspired by Conventional Commits, but pragmatic:

```
type(scope): short imperative summary

Body if needed: explain the why, not the what. Reference issues with #N.
```

Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`, `ci`, `perf`.

Example:

```
fix(exif): correct ExifTool fallback path (was assets/, now assets/tools/)

The bundled exiftool.exe was unreachable because the code looked one level
above the actual location. Closes #42.
```

### 6. Open the Pull Request

- Target branch: `main` (unless the issue says otherwise).
- Fill in the PR template if present. Otherwise include:
  - Short description of the change.
  - Issue closed (`Closes #N`).
  - Test plan (what you ran, what passed).
  - Screenshots for UI changes.
- Mark as draft if you want early feedback.

CI must pass (lint + tests on Windows). PRs with red CI will be sent back to the author.

---

## Coding conventions

### Layer separation (do not break)

```
src/ui/         ←  Tkinter widgets, never imports from photoorganizer_pro
src/core/       ←  business logic, no UI imports
src/utils/      ←  generic helpers, no UI / core imports
src/config/     ←  dataclass configs, no I/O outside json/yaml
src/reports/    ←  report formatters, can import core/utils
src/photoorganizer_pro/  ←  Pro modules — may import core, never the reverse
```

If a new feature needs to cross a layer, raise it in the issue first.

### Where to add things

| You're adding... | Goes in |
|---|---|
| A new EXIF reader / metadata source | `src/core/metadata/` |
| A new file operation | `src/core/operations/` |
| A new UI tab | `src/ui/frames/<name>_frame.py`, registered in `ui/app.py` |
| A new report format | `src/reports/duplicate_reporter.py` (or new file in `src/reports/`) |
| A new config field | `src/utils/config.py` (`AppConfig` dataclass) |
| A new test fixture | `test_data/inputs/<scenario>/` + scenario in `test_data/scripts/run_tests.py` |
| A new dependency | Discuss in issue **first**. If accepted, add to both `pyproject.toml` and `requirements.txt`. |

### Dependencies — do not add without discussion

PhotoOrganizer ships as a `--onefile` PyInstaller binary. Every dependency inflates the EXE by 0.5 to 5 MB. Before adding a dependency, prefer stdlib.

Already removed (do not re-add unless strong case): `piexif`, `chardet`, `cryptography`, `pandas`, `numpy`.

### What you must not touch

- **Generated files**: `dist/`, `build/`, `.coverage`, `.*_cache/`.
- **Bundled tools**: `assets/tools/exiftool*` — they come from the upstream ExifTool project.
- **CI release workflow** without checking the impact on the EXE build first.
- **License headers and copyright notices** — preserve attribution.

---

## Reporting issues

Open a [GitHub issue](https://github.com/Kiriiaq/PhotoOrganizer/issues/new) with:

- **Summary** : one sentence.
- **Steps to reproduce** : numbered, minimal.
- **Expected vs actual behaviour**.
- **Environment** : Python version (`python --version`), OS (`winver`), PhotoOrganizer version (Settings → About).
- **Logs** : attach `%LOCALAPPDATA%\PhotoOrganizer\logs\photoorganizer.log` if relevant.

For security vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

---

## Acknowledgements

Contributors are credited in release notes. If you contribute substantially, you may also be added to a future `AUTHORS` file.

By contributing, you agree that your contributions will be licensed under the Apache License 2.0, the same as the rest of the core project.
