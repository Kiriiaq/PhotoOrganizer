# Contexte projet pour Claude Code

> Fichier vivant. À mettre à jour à chaque phase de l'audit (4 → 7) et à chaque
> décision structurante prise dans une session future.
> Dernière mise à jour : 2026-05-19 (Phase 7 du méta-audit — drafts LinkedIn / X / Show HN).

## Identité du projet

- **Nom** : PhotoOrganizer
- **Pitch** : Organiseur automatique de photos par métadonnées EXIF, application Windows GUI.
- **Version actuelle** : 2.0.0 (sur branche `feat/v2.3-organize-tabview`), 1.0.0 = dernière release publique.
- **Statut** : WIP — refonte UI v2.3 active, audit méta-projet en cours (Phase 3/7).
- **Modèle économique** : Freemium (core Apache-2.0 + future édition Pro propriétaire dans `src/photoorganizer_pro/`).

## Stack & contraintes techniques

- **Langage** : Python 3.11+ (CI testée sur 3.11 et 3.12).
- **GUI** : CustomTkinter 5.2+ (héritage `ctk.CTk`), tkinter stdlib en dessous.
- **Packaging** : PyInstaller `--onefile` Windows x64, orchestré par `build.py`.
- **Gestionnaire deps** : pip + `pyproject.toml` (PEP 621, source de vérité) + `requirements.txt` (miroir synchronisé).
- **OS cibles** : Windows 10/11 (autres OS non testés explicitement, mais le core est platform-agnostic).
- **Conventions de code** :
  - Formatter/linter : `ruff` (configuré dans `pyproject.toml`, line-length 120, target py311).
  - `bandit` lancé par CI (zéro High issue).
  - Type hints encouragés mais non bloquants. Mypy installé mais hors CI.
  - Style mixte FR/EN dans les docstrings (le projet est francophone à l'origine, EN pour les commits et le README).
- **Commandes essentielles** :

  ```bash
  pip install -e ".[dev,dnd,toast]"   # install complet
  python main.py                       # lancer GUI depuis sources
  make test                            # 170 tests, ~25 s
  make lint                            # ruff + bandit
  python build.py                      # build EXE release
  python build.py --debug              # build EXE debug (console)
  python build.py --light              # build EXE minimal (suppose Python sur cible)
  ```

## Architecture

Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour le détail. Vue compacte :

```
main.py (shim)
   │
   ▼
src/main.py (check_dependencies + bootstrap)
   │
   ▼
src/ui/app.py  PhotoOrganizerApp(ctk.CTk)
   ├── frames/organize_frame    (3 423 LOC — onglet principal, le plus actif)
   ├── frames/duplicates_frame
   ├── frames/history_frame
   └── frames/settings_frame
   │
   ▼
src/core/{operations, metadata}    (logique métier — jamais d'import ui/)
   │
   ▼
src/utils/{cache, hash_cache, config, logger}    (infrastructure)
```

**Frontières strictes** :
- `core/` n'importe jamais `ui/`.
- `utils/` n'importe ni `core/` ni `ui/`.
- `photoorganizer_pro/` (vide pour l'instant) peut importer `core/` et `utils/`, jamais l'inverse.

**Points d'entrée** :
- GUI : `python main.py` ou `photo-organizer` (entry point pip) ou EXE.
- CLI doublons : `python -m src.cli.duplicate_cli` ou `photo-organizer-dedup`.

## Conventions de ce projet

### Où ajouter quoi

| Tu ajoutes... | Goes in |
|---|---|
| Lecteur EXIF / source de métadonnées | `src/core/metadata/` |
| Opération fichier (copy/move/rollback/scan) | `src/core/operations/` |
| Onglet UI | `src/ui/frames/<nom>_frame.py` + enregistrement dans `ui/app.py` |
| Format de rapport | `src/reports/duplicate_reporter.py` (ou nouveau fichier dans `src/reports/`) |
| Champ de configuration | `src/utils/config.py` (dataclass `AppConfig`) |
| Fixture de test | `test_data/inputs/<scenario>/` + scénario dans `test_data/scripts/run_tests.py` |
| Test pytest | `tests/{smoke,functional,perf,stress,volume}/test_<name>.py` |
| Module Pro | `src/photoorganizer_pro/<area>/` (jamais d'import depuis core) |

### Patterns à respecter

- **Lazy imports** pour les libs lourdes utilisées rarement (ex : `import requests` dans `_geocode_nominatim`, jamais top-level).
- **Sentinelles try/except** pour les libs optionnelles (`tkinterdnd2`, `plyer`, `send2trash`, `blake3`) avec un flag `*_AVAILABLE` global. Marquer l'import `# noqa: F401`.
- **Cache 2-tier** : pour toute opération coûteuse répétée, prévoir RAM + persistance SQLite (cf. `utils/cache.py`).
- **Cancel propagé** : toute opération longue doit accepter un flag d'annulation lu en boucle.
- **FileManager partagé** : un seul `FileManager` par session pour que History/Rollback restent cohérents (bug B5/B6 historique).

### Patterns à éviter

- Pas d'`asyncio` (le projet utilise `threading` + `ThreadPoolExecutor`).
- Pas de framework UI lourd (CustomTkinter suffit ; Qt ferait exploser l'EXE).
- Pas de dépendance pour 3 lignes de stdlib (ex : remplacer `requests` par `urllib.request` est planifié, cf. AUDIT_EXE F-08).
- Pas d'`except Exception: pass` muet — toujours logger.
- Pas de `print()` en code de prod — utiliser `logging`.

### Dépendances à ne pas ajouter sans discussion

Le projet bundle en `--onefile` PyInstaller. **Chaque dépendance ajoute 0.5 à 5 MB**.

**Déjà retirées (ne pas re-ajouter sans raison forte)** :
`piexif`, `chardet`, `cryptography`, `pandas`, `numpy`, `scipy`, `matplotlib`.

**Dépendances actuelles** (voir `pyproject.toml`) :
`customtkinter`, `darkdetect`, `Pillow`, `exifread`, `pillow-heif`, `requests`, `PyYAML`.
Optionnelles : `tkinterdnd2`, `plyer` (extras `dnd` et `toast`).

## État actuel & priorités

- **Branche active** : `feat/v2.3-organize-tabview` — refonte du panneau Organisation (tabview interne, exemples intégrés).
- **Audit méta-projet** : Phase 4/7 terminée (audit de complétude + gaps documentés). Phases restantes : 5 (monétisation), 6 (distribution), 7 (communication). Voir [AUDIT.md](AUDIT.md) §14 pour le plan d'action P0/P1.
- **Tests** : 170 / 170 verts (smoke 80, functional, perf, stress, volume).
- **Version code vs tag** : ⚠️ incohérence — `pyproject.toml` indique `2.0.0`, dernier tag publié est `v2.1.0`. À aligner (cf. AUDIT §14.2 D-09).

### Gaps prioritaires (issus de Phase 4)

| # | Action | Effort | Bloque |
|---:|---|---|---|
| 1 | **P0** Produire screenshot + GIF démo (au moins S-01 + G-01 dans `docs/media/`) | 4-6 h | Communication publique |
| 2 | **P1** Aligner version `2.0.0 → 2.2.0-dev` dans `pyproject.toml` et `src/ui/app.py` | 5 min | Cohérence releases |
| 3 | **P1** Ajouter `pip-audit` + `bandit` au workflow CI | 30 min | Confiance contributeurs |
| 4 | **P1** Remplacer le `bare except` `src/core/metadata/exif_extractor.py:193` par `except UnicodeDecodeError` | 5 min | Lint propre |
| 5 | **P1** Compléter `CHANGELOG.md` avec rétro v2.1.0 (entrée manquante entre v1.0.0 et v2.0.0) | 15 min | Cohérence |

### Roadmap courte (cf. README)

1. Fermer les gaps P0/P1 ci-dessus (~6-8 h).
2. Finir refonte v2.3 panneau Organisation.
3. Appliquer audit `.exe` (37 MB → 22 MB).
4. Lancer v2.4 avec EXE optimisé.
5. Démarrer v3.0 = premier module Pro (batch CLI d'organisation).

### Bugs connus (à inspecter avant toute modif)

- ExifTool fallback **désactivé en pratique** (chemin corrigé dans Phase 2 mais utilité douteuse, prévu pour retrait — cf. AUDIT_EXE F-01).
- `core/scheduler.py` : présent mais usage à vérifier (semi-dead code, candidat à confirmer ou retirer).
- `src/core/metadata/exif_extractor.py:193` : `bare except` à durcir en `except UnicodeDecodeError`.

## Décisions techniques actées

| Décision | Pourquoi |
|---|---|
| **License Apache-2.0** (depuis Phase 2 de l'audit, ex-MIT+Commons Clause) | Maximum adoption + protection brevet + compatibilité usage entreprise. Le freemium passe par une frontière de package, pas par la license. |
| **Modèle freemium core/Pro** (cf. [docs/MONETIZATION.md](docs/MONETIZATION.md)) | Core OSS pour visibilité et contributions, Pro propriétaire pour batch/scheduler/plugins/support payant. Voie principale **+** lead magnet portfolio cumulé. |
| **Pricing Pro** : 19 € personnelle / 49 € studio / 99 € lifetime sur Lemon Squeezy | Prix bas vs concurrence gratuite, volume > marge. Lemon Squeezy gère TVA EU. |
| **Activation Pro offline** (signature RSA, pas de serveur) | Zéro coût récurrent, crackable mais acceptable au prix. |
| **ExifTool bundlé à retirer avant lancement Pro** | Élimine ambiguïté GPL (cf. AUDIT_EXE F-01). |
| **CustomTkinter et pas Qt** | Toolkit plus léger (2 MB vs 50+), démarrage rapide, look moderne suffisant pour app desktop. |
| **PyInstaller `--onefile`** | Distribution mono-fichier, pas d'installation. Trade-off : démarrage 1-3s à cause de la décompression `%TEMP%`. |
| **`src/` layout (pas `photoorganizer/` à la racine)** | Évite des pièges avec `--add-data src;src` PyInstaller. Renommage en `src/photoorganizer/` réservé si publication PyPI. |
| **Cache 2-tier RAM + SQLite** | RAM pour la session courante, SQLite pour les relances. Bug T-114 corrigé : avant, le SQLite était jamais lu. |
| **Quarantaine plutôt que `send2trash` direct** | Permet rollback granulaire avec metadata.json. send2trash devient une dépendance optionnelle. |
| **Hash multi-algo avec fallback** | Blake3 si dispo (2-3x plus rapide), sinon SHA-1, sinon MD5. Le code reste fonctionnel sans Blake3. |
| **Pas d'asyncio, threading uniquement** | Le projet est I/O-bound sur FS + rare HTTPS, threading suffit et est plus simple à débugger. |
| **Tests en 5 catégories** (smoke/functional/perf/stress/volume) | Smoke doit rester < 10s pour CI rapide. Les autres sont marqués `slow` et lancés via `make test-all`. |
| **CI Windows-only** | OS cible. Si support multi-OS souhaité, créer une matrice (windows-latest + ubuntu-latest). |

## Instructions opérationnelles pour Claude Code

### Ce que tu peux faire seul

- Modifier le code source, écrire et exécuter des tests.
- Lancer `make test` et `make lint` pour valider.
- Refactorer dans la couche d'un module si la modification reste locale.
- Ajouter du logging.
- Écrire de la doc et des CHANGELOG entries.

### Ce que tu dois valider avant d'exécuter

- **Ajouter ou retirer une dépendance** (toujours discuter le coût EXE avant).
- **Modifier une frontière de couche** (`core/` ↔ `ui/` ↔ `utils/`).
- **Modifier le `.github/workflows/release.yml`** ou la signature du build.
- **Toucher à `LICENSE`, `pyproject.toml` `[project]`, ou aux URLs publiques**.
- **Renommer un fichier ou un module** (refs croisées).
- **Lancer un commit, un push, une PR** — interdit par défaut, voir préférence durable ci-dessous.

### Tests à lancer après modification

| Tu as modifié... | Lance |
|---|---|
| `src/ui/**` | `make test` (smoke contient `test_ui_v3.py` et `test_ux_v4.py`) |
| `src/core/operations/**` | `make test` + `tests/functional/test_file_manager.py`, `test_organizer.py`, `test_duplicates.py`, `test_quarantine.py` |
| `src/core/metadata/**` | `make test` + `tests/functional/test_exif_cache.py` |
| `src/utils/**` | `make test` + `tests/functional/test_config.py` |
| `build.py` | `python build.py --light` pour un build rapide, vérifier la taille du EXE produit |
| `pyproject.toml` ou `requirements.txt` | `pip install -e ".[dev]"` puis `make test` |

### Ce qu'il ne faut jamais toucher

- **`assets/tools/`** — c'est ExifTool importé de upstream, modifier serait perdre la trace.
- **`.git/`**, **`dist/`**, **`build/`** — générés ou versionnés à part.
- **`%LOCALAPPDATA%\PhotoOrganizer\`** — config et caches utilisateur. Si la session est sur le poste de l'auteur, ne pas effacer.
- **`test_data/inputs/` et `test_data/outputs_reference/`** — fixtures versionnées pour la non-régression, ne pas régénérer sans validation.
- **`LICENSE`** sans demande explicite de l'utilisateur (décision impactante).

### Préférences durables de l'utilisateur (rappel mémoire)

- **Pas de commit, push, ou PR sans demande explicite**. Modifier les fichiers et faire un `git status` récap.
- **Pas de fenêtres `Toplevel` dans l'onglet Organisation** — utiliser `OrganizeFrame._show_inline_panel` à la place.

## Glossaire rapide

| Terme | Sens dans ce projet |
|---|---|
| Frame | Onglet de l'app (Organisation, Doublons, Historique, Paramètres) |
| Operation | Une action utilisateur de type organize/duplicate/rollback, traçable dans History |
| Session | Ensemble cohérent d'opérations partageant un même `FileManager` (depuis un lancement de l'app jusqu'au prochain rollback global) |
| Quarantine | Stockage interne réversible pour les doublons "supprimés" (vs. corbeille système qui est terminale) |
| Rollback | Annulation propre d'une opération avec recréation des dossiers vidés |
| Light build | Variante PyInstaller sans les libs lourdes (Pillow, etc.) — suppose qu'elles sont déjà sur la machine cible |
| Geocoding | Conversion lat/lon → nom de lieu via Nominatim (OpenStreetMap) |

## Liens rapides

- Audit projet global : [AUDIT.md](AUDIT.md)
- Audit taille EXE : [docs/exe-optimization.md](docs/exe-optimization.md)
- Architecture : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Médias à produire : [docs/MEDIA.md](docs/MEDIA.md)
- Changelog : [CHANGELOG.md](CHANGELOG.md)
- Stratégie monétisation : [docs/MONETIZATION.md](docs/MONETIZATION.md)
- Plateformes & calendrier de lancement : [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md)
- Drafts LinkedIn / X / Show HN : [LINKEDIN_DRAFTS.md](LINKEDIN_DRAFTS.md)
- Dashboard projet : [PROJECT_OVERVIEW.html](PROJECT_OVERVIEW.html)
