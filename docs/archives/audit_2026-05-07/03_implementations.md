# Phase 3 — Implémentations & corrections

Toutes les corrections respectent les conventions du codebase (style mixed FR/EN
hérité, dataclasses, threading + `self.after(0,…)`, logging via `logger`
module-scoped).

## 🔴 Lot A — Bugs runtime

| # | Fichier | Avant | Après |
| - | ------- | ----- | ----- |
| A1 | `ui/frames/duplicates_frame.py:879/943/986` | `lambda: …str(e)` capture la variable `e` du `except` qui est **détruite** par Python à la sortie du bloc → `NameError` lors de la prochaine erreur | Capture `err_msg = str(exc)` puis `lambda m=err_msg: …` (default-arg trick + log explicite via `logger.exception`) |
| A2 | `tests/test_modules.py` | importe `src.core.scanner.PhotoScanner` etc. — modules inexistants → tests cassés | Réécriture avec smoke tests sur l'API réelle (`FileManager`, `SmartOrganizer`, `OrganizationOptions`, `get_exif_data`) |
| A3 | `core/metadata/exif_extractor.py:_find_exiftool` | si `EXIFTOOL_PATH=""` → `subprocess.run([''])` lève `OSError WinError 87` non rattrapé | Skip si chemin vide + ajoute `OSError` à l'except |
| A4 | `utils/cache.py:72` MD5 | flag Bandit B324 (High) | `hashlib.md5(..., usedforsecurity=False)` |

## 🟠 Lot B — Cohérence multi-frame & fonctionnalités manquantes

| # | Description | Fichiers |
| - | ----------- | -------- |
| B1 | **FileManager partagé** entre OrganizeFrame, DuplicatesFrame et HistoryFrame. Avant : chacun créait son propre instance, l'historique restait toujours vide. | `ui/app.py`, `ui/frames/organize_frame.py`, `ui/frames/duplicates_frame.py`, `ui/frames/history_frame.py` |
| B2 | **`init_cache(...)`** appelé au démarrage avec les valeurs de `AppConfig` (TTL et max_size). Avant : valeurs par défaut figées. | `utils/cache.py`, `ui/app.py` |
| B3 | **`get_gps_processor().geocoding_enabled`** propagé depuis la config au démarrage. Avant : flag jamais propagé. | `ui/app.py` |
| B4 | **Refresh historique au changement d'onglet** (`_on_tab_changed` câblé via `tabview.configure(command=…)`) + méthode publique `HistoryFrame.refresh()`. | `ui/app.py`, `ui/frames/history_frame.py` |
| B5 | **Annulation propre** : `OrganizeFrame._cancel_operation` appelle désormais `self._current_organizer.cancel()`. Avant : flag local jamais lu par le worker. | `ui/frames/organize_frame.py` |
| B6 | **Rollback enrichi** : `FileManager.rollback_all()` retourne `{success, failed, skipped, total}` avec `success+failed+skipped == total`. `rollback_last` ignore les ops déjà en erreur, restaure le dossier source si effacé, nettoie les dossiers vides. Rétro-compat dans le frame (test `isinstance(int)`). | `core/operations/file_manager.py`, `ui/frames/history_frame.py` |
| B7 | **`FileManager.clear_history()`** (API publique) à la place de l'accès `_operations_history.clear()` direct. | `core/operations/file_manager.py`, `ui/frames/history_frame.py` |

## 🟢 Lot C — Features IHM neuves

| # | Description | Fichiers |
| - | ----------- | -------- |
| C1 | **Compteur de fichiers source** sous les boutons (T-030..T-033). Mis à jour automatiquement à chaque changement de `source_var`, `recursive`, `include_*`. Comptage en thread daemon pour ne pas geler l'UI. Affiche états « aucun dossier sélectionné », « introuvable », « N fichier(s) prêt(s) ». | `ui/frames/organize_frame.py:_refresh_file_count` |
| C2 | **Raccourcis clavier** Ctrl+1..Ctrl+4 via `bind_all` pour basculer entre les 4 onglets (T-016..T-019), F1 pour l'aide. | `ui/app.py:_install_shortcuts`, `_select_tab` |
| C3 | **Icône** : recherche prioritaire `resources/icons/icon.ico` puis fallback `src/ui/assets/icon.ico`. AppUserModelID Windows pour la barre des tâches. Fallback PNG via `iconphoto()`. | `ui/app.py:_install_icon` |
| C4 | **Exclusion corbeille système** (Windows `$Recycle.Bin`, macOS `.Trashes`, Linux `.Trash-{uid}`, `System Volume Information`). Filtrage à 2 niveaux : pendant la traversée et au filtrage fichier (garde-fou). | `core/operations/duplicate_manager.py:_is_system_folder`, `_should_include_folder`, `_should_include_file` |
| C5 | **Logging explicite** : remplace `except Exception: pass` par `except (OSError, ValueError) as exc: logger.warning(…)` dans `_analyze_files` (T-fictif : silencieux qui masque les erreurs EXIF). | `ui/frames/organize_frame.py` |
| C6 | **Imports nettoyés** sur `duplicates_frame.py` et `history_frame.py` (F401 supprimés). Logger ajouté à `duplicates_frame.py`. | idem |

## 🟡 Lot D — Hygiène mineure

| # | Description |
| - | ----------- |
| D1 | Ajout du module `logger = logging.getLogger(__name__)` dans `duplicates_frame.py` et `organize_frame.py` (manquant). |
| D2 | Suppression des imports inutilisés (`os`, `datetime`, `FileOperation`, `FolderFilter`, `ExtensionFilter`, `DuplicateGroupDecision`, `FileDecision`) dans `history_frame.py` et `duplicates_frame.py`. |
| D3 | `duplicates_frame.py:_create_actions_section` — la barre de progression et son label étaient déjà visibles à 0 % à l'init. Conservé. Le label « Pret » → ajout d'un compteur de fichiers analogue à OrganizeFrame est laissé en backlog (le scan/exécution émettent déjà l'avancement). |

## Décisions documentées
- **Pas d'ajout de `pytest-qt`/`pytest-customtkinter`** : la lib n'existe pas pour CTk, et lancer un Tk root en CI est instable. Les tests d'IHM se font via construction directe des frames avec mocks (Phase 4).
- **Compatibilité legacy** : `rollback_all` retourne maintenant un dict, mais le frame teste `isinstance(int)` pour ne pas casser un appelant externe non encore mis à jour.
- **`_install_shortcuts` use `bind_all`** : il existe une discussion classique sur `bind` vs `bind_all` ; pour des raccourcis "globaux" type Ctrl+1..N c'est attendu. Une `Entry` qui aurait absorbé la frappe utiliserait quand même les Control-Key (par défaut Tk les remonte).
