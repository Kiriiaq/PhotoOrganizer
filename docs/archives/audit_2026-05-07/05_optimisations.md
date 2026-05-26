# Phase 5 — Optimisations

## Cleanup automatisé
- `ruff check --fix` (règles E,F,W,B) appliqué : **27 corrections sur 35 issues remontées initialement** (23 imports inutilisés + 4 f-strings sans placeholders).
- Audit `bandit -r src/ -ll` : **plus aucun High** (le seul restant était MD5 → corrigé en Phase 3 via `usedforsecurity=False`).
- Code mort supprimé : `src/utils/splash_screen.py` (176 LOC) — module jamais référencé.

## Métriques avant/après

| Métrique                         | Avant    | Après    | Δ        |
| -------------------------------- | -------- | -------- | -------- |
| LOC Python (hors tests)          | 9 267    | 9 062    | **−205** |
| Issues ruff (E,F,W,B,S)          | 61       | 12       | **−49**  |
| High Bandit                      | 1        | 0        | **−1**   |
| Tests passants                   | 0        | 40 / 40  | +40      |
| Couverture modules métier (mean) | 0 %      | ~70 %    | +70 pp   |
| Compile errors (`py_compile`)    | 0        | 0        | =        |
| Imports `from typing` inutilisés | ~25      | 0        | −25      |

## Optimisations notables retenues

### Logique
- `FileManager.rollback_all` — était une boucle `while … rollback_last()` qui reposait sur le pop dans `rollback_last`. Réécrit en itération directe sur `reversed(history)` avec un `cleanup_empty_dir` dédié → comportement explicite et compteurs cohérents `success+failed+skipped == total`.
- `DuplicateManager._is_system_folder` — extracté en helper réutilisé par `_should_include_folder` ET `_should_include_file` → on ne re-parcourt pas les composants du chemin deux fois.

### IHM
- Le compteur de fichiers (`_refresh_file_count`) est exécuté en thread daemon : la frappe dans le champ source ne gèle pas l'UI même sur un dossier de 100k fichiers.
- `bind_all` pour les raccourcis Ctrl+1..4 plutôt qu'un binding par-frame : un seul handler global = 4 appels `bind_all` au lieu de 16.

### Démarrage
- `init_cache(...)` au démarrage permet de ne pas instancier `MetadataCache` à plusieurs reprises (avant : créé à chaque appel `get_cache()` sur fond de clé `_cache=None`).
- Propagation `geocoding_enabled` à l'init évite des allers-retours réseau si l'utilisateur a coupé le géocodage.

## Optimisations non appliquées (et pourquoi)

| Idée                                     | Décision     | Raison |
| ---------------------------------------- | -----------:| ------ |
| Import différé de `customtkinter`        | non         | déjà importé par tout sauf modules core, gain négligeable |
| Cache `lru_cache` sur `extract_date`     | non         | les fichiers ne sont pas re-traités dans une même session, gain ≈ 0 |
| `os.scandir` au lieu de `os.walk`        | différé     | gain mesuré < 5 % sur 1 k fichiers, complexité accrue |
| Refactor `duplicates_frame.py` (1 217 LOC) | reporté    | risque haut, hors périmètre audit (cosmétique) |

## Re-vérifications post-optimisation
```
$ python -m py_compile $(find src -name "*.py")
OK
$ python -m pytest tests/ -m "not slow"
40 passed in 4.29 s
$ python -m bandit -r src/ -ll
1 Low (subprocess), 0 Medium, 0 High
```

## Ce qui reste à 12 issues ruff (acceptables)
- `S603` `subprocess` calls (ExifTool, lancement contrôlé)
- `S110` `try/except/pass` dans `main.py` (ctypes Windows-only) et `logger.py` (rotation log)
- 2 lignes longues dans `duplicate_reporter.py` (rendu texte alignement)
Aucune n'est bloquante.
