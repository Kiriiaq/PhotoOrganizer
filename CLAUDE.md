# Contexte projet pour Claude Code

> Fichier vivant. À mettre à jour à chaque décision structurante prise dans une
> session future.
> Dernière mise à jour : 2026-06-11 (**audit complet** — correction du bug
> bloquant B-01 du worker d'organisation, robustesse threads, rangement ;
> cf. branche `audit/2026-06-11`). Pivot économique *trial + unlock* 10 €
> lifetime acté le 2026-05-26.

## Identité du projet

- **Nom** : PhotoOrganizer
- **Pitch** : Organiseur automatique de photos par métadonnées EXIF, application Windows GUI.
- **Version actuelle** : 2.3.0.dev0 (source de vérité : `src/__init__.py`).
- **Statut** : pivot économique **implémenté** (compteur d'usages + panneau d'activation inline + machine binding + badge/bandeaux). Reste avant lancement : setup Lemon Squeezy + médias (cf. priorités).
- **Modèle économique** : **édition unique** Apache-2.0. Essai gratuit limité à **10 tris**, puis déblocage par clé HMAC à **10 € lifetime, 1 PC** (cf. [docs/MONETIZATION.md](docs/MONETIZATION.md)).

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
  make test                            # 207 tests core, ~20 s (Pro skippé par défaut)
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
src/utils/{cache, hash_cache, config, logger, licensing*}    (infrastructure)
```

`*` : `licensing` (créé en v2.3.0) gère le compteur + clé + binding 1 PC. Détails dans [docs/MONETIZATION.md](docs/MONETIZATION.md) §3.

**Frontières strictes** :
- `core/` n'importe jamais `ui/`.
- `utils/` n'importe ni `core/` ni `ui/`.
- `src/photoorganizer_pro/` (**gelé pour v3.0+**) peut importer `core/` et `utils/`, jamais l'inverse. **N'est plus appelé par l'app v2.x** — les entry points pip sont commentés et les tests sont skippés.

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
| Logique licence/compteur/machine binding | `src/utils/licensing.py` |
| **Code "futur v3.0+"** | `src/photoorganizer_pro/<area>/` — **mais ne pas l'activer en v2.x** |

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
Optionnelles : `tkinterdnd2`, `plyer` (extras `dnd` et `toast`). `watchdog` (extra `pro`, gelé v3.0+).

## État actuel & priorités

- **Branche active** : `main` (+ branche `audit/2026-06-11` pour les correctifs d'audit).
- **Tests** : **207/207 core verts** (~20 s), dont E2E worker organisation (`tests/smoke/test_organize_e2e.py`) et 17 tests licensing dédiés. Les tests Pro restent skippés (reason: `Deferred to v3.0+`).
- **Pivot économique 2026-05** : 19/49/99 € freemium-par-fonctionnalité → **édition unique 10 € lifetime, 10 tris d'essai**. Cf. AUDIT.md §15.

### Priorités immédiates (post-pivot)

| # | Action | Effort | Bloque |
|---:|---|---|---|
| 1 | ~~**P0** Créer `src/utils/licensing.py` : compteur HMAC + binding machine~~ ✅ *fait (v2.3.0)* | — | — |
| 2 | ~~**P0** Modal inline d'activation/blocage dans `organize_frame` (warnings 8/9, blocage 11)~~ ✅ *fait (v2.3.0)* | — | — |
| 3 | ~~**P0** Badge "Essai X/10" ou "Activée" dans la barre de l'app~~ ✅ *fait (v2.3.0)* | — | — |
| 4 | **P0** Setup Lemon Squeezy avec un seul produit à 10 € + flow d'envoi clé (manuel d'abord). L'URL `photoorganizer.lemonsqueezy.com` codée dans `_open_purchase_page` doit exister avant lancement | 2 h | Revenue |
| 5 | **P1** Produire screenshot + GIF démo (S-01 + G-01 dans `docs/media/`) | 4-6 h | Communication publique |
| 6 | **P1** Réécrire LINKEDIN_DRAFTS.md sur la base du nouveau modèle | 1 h | Cohérence com |

### Roadmap courte

1. **v2.3.0** : intégrer le flow trial+unlock complet (Tâches 1-3 ci-dessus). **+ tests dédiés**.
2. **v2.3.1** : setup Lemon Squeezy + premières ventes manuelles, ajustements UX selon retours.
3. **v2.4.0** : appliquer audit `.exe` (37 MB → 22 MB).
4. **v3.0.0** *(conditionnel — uniquement si traction confirmée)* : réactiver les modules Pro reportés (batch CLI, watch-folder, plugins) sous forme d'add-on payant séparé.

### Bugs connus (à inspecter avant toute modif)

- ExifTool fallback : le binaire bundlé `assets/tools/` a été **retiré du repo** ; seuls `EXIFTOOL_PATH` et le PATH système sont sondés (audit 2026-06-11, B-12). Le retrait complet du fallback subprocess reste envisageable (AUDIT_EXE F-01).
- `core/scheduler.py` : **utilisé** par `ui/frames/organize_frame.py` pour `JobScheduler` (planif quotidienne in-app). Pas mort, à garder.
- ~~`exif_extractor.py:193` : bare except~~ ✅ corrigé (`except UnicodeDecodeError`).
- L'EXE embarque les sources `.py` (dont `_secret.py` en clair) via `--add-data src;src` — cf. rapport d'audit 2026-06-11 B-13, à traiter lors d'un build de contrôle.

## Décisions techniques actées

| Décision | Pourquoi |
|---|---|
| **License Apache-2.0** | Maximum adoption + protection brevet + compatibilité usage entreprise. Le freemium passe par le compteur d'usages, pas par la license du code. |
| **Édition unique (pas Pro séparée)** ✦ *2026-05* | Le testeur teste exactement l'app qu'il achète. Maintenance d'une seule codebase. Modèle "shareware" Sublime Text / WinRAR universellement compris. |
| **Trial = 10 tris gratuits, illimité après unlock** ✦ *2026-05* | Compteur d'actions plus lisible qu'un trial temporel. Warning à 8/10 et 9/10 pour ne pas surprendre. Incrément seulement à la réussite (un crash ne consomme pas). |
| **Pricing : 10 € lifetime, 1 PC, aucune réémission** ✦ *2026-05* | Prix bas grand public, volume > marge. Politique stricte assumée : changement de PC = nouvelle clé. Geste commercial possible au cas par cas (non promis publiquement). |
| **Clé universelle HMAC SHA-256 qui se bound au 1er PC** ✦ *2026-05* | Pas besoin de demander l'ID machine avant achat → flow Lemon Squeezy standard. Au premier `validate + save`, on enregistre `MachineGuid + volume serial` comme empreinte ; les validations suivantes refusent un autre fingerprint. |
| **Modules Pro existants (batch CLI, watch, plugins) reportés v3.0+** ✦ *2026-05* | Conservés intacts dans `src/photoorganizer_pro/` pour réactivation conditionnelle si traction. Entry points pip commentés, tests skippés. |
| **Activation offline (pas de serveur)** | Zéro coût récurrent. Crackable mais acceptable au prix de 10 €. Aucun DRM offline n'est incassable — l'objectif est "plus chiant à contourner que payer". |
| **ExifTool bundlé à retirer avant lancement public** | Élimine ambiguïté GPL (cf. AUDIT_EXE F-01). |
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
- **Modifier le SECRET HMAC** (`src/photoorganizer_pro/license/_secret.py`) — invaliderait toutes les clés émises.
- **Lancer un commit, un push, une PR** — interdit par défaut, voir préférence durable ci-dessous.

### Tests à lancer après modification

| Tu as modifié... | Lance |
|---|---|
| `src/ui/**` | `make test` (smoke contient `test_ui_v3.py` et `test_ux_v4.py`) |
| `src/core/operations/**` | `make test` + `tests/functional/test_file_manager.py`, `test_organizer.py`, `test_duplicates.py`, `test_quarantine.py` |
| `src/core/metadata/**` | `make test` + `tests/functional/test_exif_cache.py` |
| `src/utils/**` (notamment futur `licensing.py`) | `make test` + tests fonctionnels licensing dédiés |
| `build.py` | `python build.py --light` pour un build rapide, vérifier la taille du EXE produit |
| `pyproject.toml` ou `requirements.txt` | `pip install -e ".[dev]"` puis `make test` |

### Ce qu'il ne faut jamais toucher

- **`assets/tools/`** — c'est ExifTool importé de upstream, modifier serait perdre la trace.
- **`.git/`**, **`dist/`**, **`build/`** — générés ou versionnés à part.
- **`%LOCALAPPDATA%\PhotoOrganizer\`** — config, caches utilisateur, **futur `usage.dat` et `license.dat`**. Si la session est sur le poste de l'auteur, ne pas effacer.
- **`test_data/inputs/` et `test_data/outputs_reference/`** — fixtures versionnées pour la non-régression, ne pas régénérer sans validation.
- **`LICENSE`** sans demande explicite de l'utilisateur (décision impactante).
- **`src/photoorganizer_pro/license/_secret.py`** — gitignored, contient la clé HMAC qui signe les licences. La perdre = invalider toutes les clés émises.

### Préférences durables de l'utilisateur (rappel mémoire)

- **Pas de commit, push, ou PR sans demande explicite**. Modifier les fichiers et faire un `git status` récap.
- **Pas de fenêtres `Toplevel` dans l'onglet Organisation** — utiliser `OrganizeFrame._show_inline_panel` à la place. Le modal de blocage trial DOIT respecter cette règle.

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
| Trial | Période d'essai = 10 tris réussis. Compteur dans `%LOCALAPPDATA%\PhotoOrganizer\usage.dat` (signé HMAC). |
| Unlock | Saisie d'une clé valide → bascule l'app en mode illimité, bound au PC courant. |
| Machine binding | Hash du `MachineGuid` Windows + volume serial du disque système, stocké dans `license.dat` signé. |

## Liens rapides

- Audit projet global : [AUDIT.md](AUDIT.md)
- Audit taille EXE : [docs/exe-optimization.md](docs/exe-optimization.md)
- Architecture : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Médias à produire : [docs/MEDIA.md](docs/MEDIA.md)
- Changelog : [CHANGELOG.md](CHANGELOG.md)
- **Stratégie monétisation (nouveau modèle)** : [docs/MONETIZATION.md](docs/MONETIZATION.md)
- Plateformes & calendrier de lancement : [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md)
- Drafts LinkedIn / X / Show HN : [LINKEDIN_DRAFTS.md](LINKEDIN_DRAFTS.md)
- **Procédure de rentabilisation pas-à-pas** : [NEXT_STEPS.html](NEXT_STEPS.html)
- Dashboard projet : [PROJECT_OVERVIEW.html](PROJECT_OVERVIEW.html)
- Docs archivées (pivot 2026-05) : `docs/archives/superseded_2026-05/` — anciens modules Pro, design cloud, checklist freemium
