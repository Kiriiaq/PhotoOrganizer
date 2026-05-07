# Phase 2 — Analyse statique

## Outils exécutés
- `python -m py_compile` (toutes les sources) ✅ pas d'erreur de syntaxe
- `ruff check . --select=E,F,W,B,S` → **61 messages**
- `vulture --min-confidence 80` → 6 vraies remontées
- `bandit -r src/ -ll` → **1 High + 8 Low**
- Recherche manuelle TODO/FIXME/NotImplementedError → **0** dans `src/`

## Issues classées par criticité

### 🔴 BLOQUANT
| Fichier | Ligne | Issue | Description |
| ------- | ----- | ----- | ----------- |
| `ui/frames/duplicates_frame.py` | 879 | F821 | `lambda: ... str(e)` capture une variable `e` détruite par Python à la sortie du `except` → **NameError au runtime** |
| `ui/frames/duplicates_frame.py` | 943 | F821 | Idem |
| `ui/frames/duplicates_frame.py` | 986 | F821 | Idem |
| `tests/test_modules.py` | tout | ImportError | référencent `src.core.scanner.PhotoScanner`, `src.core.organizer.Organizer`, `src.core.metadata.MetadataExtractor` → modules **inexistants** |
| `ui/frames/history_frame.py` | 34 | logique | crée son propre `FileManager()` ⇒ historique vide même quand l'organisation a tourné |
| `ui/frames/organize_frame.py` | 473 | logique | `_cancel_operation` lève seulement un flag local, le `SmartOrganizer` n'est jamais informé ⇒ annulation cassée |
| `ui/frames/organize_frame.py` | 331/453 | logique | crée un nouveau `FileManager`/`SmartOrganizer` à chaque appel ⇒ pas de session partagée |

### 🟠 MAJEUR
| Fichier | Ligne | Issue |
| ------- | ----- | ----- |
| `main.py` | 20 | `try/except: pass` sur `ctypes.windll.shell32` |
| `core/metadata/exif_extractor.py` | 157 | bare `except:` (E722) avec `continue` |
| `core/metadata/exif_extractor.py` | 270 | subprocess sans validation d'entrée |
| `ui/frames/organize_frame.py` | 402 | `except Exception: pass` engloutit toutes erreurs d'analyse |
| `utils/cache.py` | 72 | MD5 sans `usedforsecurity=False` (B324 High) |
| `utils/logger.py` | 112 | `try/except/pass` silencieux |
| `core/operations/file_manager.py` | rollback | ne reconstruit pas le dossier source si supprimé, ne nettoie pas les dossiers vides |
| `ui/frames/duplicates_frame.py` | scan | corbeille `$Recycle.Bin` non exclue → un re-scan voit les fichiers déjà envoyés |

### 🟡 MINEUR
- ~25 `F401` imports inutilisés (cleanup mécanique)
- 4 variables `p`/`t` shadow dans les `lambda` des callbacks status (vulture)
- 3 `B007` boucles avec variable de contrôle inutilisée
- 2 `S112 try/except/continue` dans date_extractor
- 3 `E501` dépassements de ligne (130+ chars) dans rapporteur

## Décision pour la Phase 3
Lots prioritaires :
- **Lot A — bugs runtime** : 3× F821 lambdas + 1× tests existants impossibles à exécuter
- **Lot B — cohérence multi-frame** : FileManager partagé, refresh historique au switch d'onglet, init cache + propagation `geocoding_enabled`
- **Lot C — features manquantes IHM** : compteur fichiers, raccourcis clavier (Ctrl+1..4), exclusion corbeille système, annulation propre, scan-phase progress
- **Lot D — hygiène** : nettoyage des imports inutilisés, MD5 → `usedforsecurity=False`, retrait des `except: pass` les plus dangereux
