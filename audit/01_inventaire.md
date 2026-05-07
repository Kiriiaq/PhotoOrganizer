# Phase 1 — Inventaire & cartographie

## Stack technique
- **UI** : CustomTkinter 5.2+ (toolkit Tkinter modernisé)
- **Threading** : `threading.Thread(daemon=True)` pour les opérations longues, dispatch UI via `self.after(0, …)`
- **Format** : Python 3.11+, encodage UTF-8 mixte (certains modules en latin-1 hérité)
- **Stockage** : JSON pour la config (`%APPDATA%/PhotoOrganizer/`), SQLite probable pour le cache de hash, YAML pour la config doublons
- **Build** : `PyInstaller --onefile`, modes full + light

## Arborescence
```
PhotoOrganizer/
├── main.py                       # Bootstrap (Windows AppUserModelID + sys.path src/)
├── build.py                      # Wrapper PyInstaller (build full / --light)
├── pyproject.toml                # Métadonnées projet, ruff, pytest
├── requirements.txt
├── src/
│   ├── main.py                   # check_dependencies + setup_logging + lance app
│   ├── cli/duplicate_cli.py      # CLI de doublons (760 lignes — non utilisé par l'IHM)
│   ├── config/duplicate_config.py# Dataclasses YAML (Folders, Hashing, Conservation…)
│   ├── core/
│   │   ├── metadata/             # exif/gps/date/camera (1 117 lignes)
│   │   └── operations/
│   │       ├── file_manager.py   # copy/move/list/rollback (309 lignes)
│   │       ├── organizer.py      # SmartOrganizer + OrganizationOptions (347 lignes)
│   │       ├── duplicate_finder.py
│   │       └── duplicate_manager.py
│   ├── reports/duplicate_reporter.py
│   ├── ui/
│   │   ├── app.py                # PhotoOrganizerApp (CTk root, 4 onglets)
│   │   └── frames/
│   │       ├── organize_frame.py # 535 lignes
│   │       ├── duplicates_frame.py # 1 217 lignes
│   │       ├── history_frame.py  # 235 lignes
│   │       └── settings_frame.py # 347 lignes
│   └── utils/
│       ├── cache.py              # cache générique (mémoire + disque)
│       ├── hash_cache.py         # cache hash sqlite (567 lignes)
│       ├── config.py             # AppConfig + ConfigManager
│       ├── logger.py
│       └── splash_screen.py      # 176 lignes — non importé
├── tests/                        # 39 lignes au total : CASSÉS (importent des modules inexistants)
└── audit/                        # NEW — sortie de cet audit
```

Total : **9 267 LOC Python** (hors `__pycache__` et tests).

## Cartographie des onglets/fonctionnalités

### Onglet 📁 Organisation (`organize_frame.py`)
| Fonctionnalité                       | Statut    | Localisation                                                                 |
| ------------------------------------ | --------- | ---------------------------------------------------------------------------- |
| Sélection dossier source/destination | OK        | `_browse_source` / `_browse_dest`                                            |
| Liste des fichiers détectés (UI)     | **Manquant** | aucun widget pour afficher les fichiers ni leur compteur                    |
| Compteur de fichiers visible         | **Manquant** | jamais émis (c.f. tests T-030..T-033)                                       |
| Critères : date/camera/location      | OK        | options dataclass                                                            |
| Format de date                       | Partiel   | options figées (5 choix), pas de niveaux dynamiques                          |
| Multicouche + ordre des critères     | Partiel   | flag mais pas d'IHM pour réordonner                                          |
| Bouton Analyser                      | OK        |                                                                              |
| Bouton Organiser                     | OK        |                                                                              |
| Bouton Annuler                       | **Cassé** | `_cancel_requested = True` mais aucun `SmartOrganizer.cancel()` appelé       |
| Barre de progression                 | OK        | présente, init à 0                                                           |
| Phase scan visible avant organisation | **Manquant** | scan inclus dans la même thread, aucun feedback de découverte             |
| Raccourci clavier de navigation      | **Manquant** | aucun binding clavier dans `app.py`                                        |

### Onglet 🔍 Doublons (`duplicates_frame.py`)
| Fonctionnalité                       | Statut    | Localisation                                                                 |
| ------------------------------------ | --------- | ---------------------------------------------------------------------------- |
| Modes (Simulation/Delete/Move/Trash) | OK        | `_on_mode_change`                                                            |
| Charger/sauver config YAML           | OK        | `_load_config_file` / `_save_config_file`                                    |
| Filtres (taille, types, récursif)    | OK        |                                                                              |
| Règles de conservation               | OK        |                                                                              |
| Bouton Rechercher                    | OK        |                                                                              |
| Bouton Exécuter (état désactivé)     | **Cassé** | activé tant qu'aucune analyse, c.f. T-034                                    |
| Bouton Annuler (état désactivé)      | **Cassé** | démarre `disabled` mais le pattern visuel pas évident, c.f. T-035            |
| Liaison FileManager partagé          | **Manquant** | DuplicateManager n'enregistre pas l'historique global, donc rollback inutilisable |
| Exclusion corbeille/$Recycle.Bin     | **Manquant** | T-fictif : un re-scan après TRASH retrouve les fichiers en corbeille      |

### Onglet 📜 Historique (`history_frame.py`)
| Fonctionnalité                       | Statut    | Localisation                                                                 |
| ------------------------------------ | --------- | ---------------------------------------------------------------------------- |
| Affichage des opérations             | OK        | en théorie                                                                    |
| Partage du FileManager avec Organize | **Cassé** | `HistoryFrame.__init__` crée son **propre** `FileManager()` → toujours vide  |
| Rollback dernière / toutes           | OK (logique)| mais inutilisable à cause du bug ci-dessus                                  |
| Compte-rendu détaillé du rollback    | Partiel   | `rollback_all()` retourne juste un int, sans success/skipped/failed          |
| Effacer l'historique                 | OK        | mais accède à `_operations_history` (privé)                                  |

### Onglet ⚙️ Paramètres (`settings_frame.py`)
| Fonctionnalité                       | Statut    | Localisation                                                                 |
| ------------------------------------ | --------- | ---------------------------------------------------------------------------- |
| Thème (sombre/clair/système)         | OK        |                                                                              |
| Action par défaut, récursif          | OK        |                                                                              |
| Activer cache                        | OK        |                                                                              |
| Statistiques cache                   | Partiel   | calculées à l'init seulement, ne sont pas rafraîchies                        |
| Géocodage + clé API                  | OK        |                                                                              |
| Niveau de log                        | OK        |                                                                              |
| Sauvegarder / Réinitialiser          | OK        |                                                                              |
| Effacer dossiers récents             | OK        |                                                                              |

### Application principale (`ui/app.py`)
| Fonctionnalité                       | Statut    | Localisation                                                                 |
| ------------------------------------ | --------- | ---------------------------------------------------------------------------- |
| 4 onglets via CTkTabview             | OK        |                                                                              |
| Header avec toggle thème + ?         | OK        |                                                                              |
| Status bar en bas                    | OK        |                                                                              |
| Sauvegarde géométrie au close        | OK        |                                                                              |
| Restauration dossiers récents        | OK        |                                                                              |
| Initialisation cache (ttl/max_size)  | **Manquant** | `init_cache(...)` n'est jamais appelé                                      |
| Initialisation `geocoding_enabled`   | **Manquant** | la valeur de `AppConfig` n'est jamais propagée vers le `gps_processor`     |
| Raccourcis clavier                   | **Manquant** | aucun bind                                                                   |
| FileManager partagé entre frames     | **Manquant** | chaque frame instancie son propre FileManager                              |
| Refresh history au changement onglet | **Manquant** | aucun callback `command=` sur le tabview                                    |
| Icône Windows                        | Partiel   | cherche `src/ui/assets/icon.ico` mais l'icône réelle est `resources/icons/`  |

## Modules core / utils
| Module | Statut | Notes |
| ------ | ------ | ----- |
| `core/metadata/exif_extractor.py` | OK | dépendance optionnelle PIL/exifread/pillow_heif gérée |
| `core/metadata/gps_processor.py` | OK | `geocoding_enabled` flag mais jamais propagé depuis l'UI |
| `core/operations/file_manager.py` | Partiel | rollback ne réinjecte pas dossier source, pas de cleanup dossiers vides |
| `core/operations/organizer.py` | Partiel | format date figé, pas d'aperçu, pas de dispatch GPS clusterisé |
| `core/operations/duplicate_*.py` | OK | mais `_should_include_folder` ne filtre pas les corbeilles système |
| `utils/cache.py` | OK | `init_cache(...)` jamais appelé → defaults non configurables |
| `utils/splash_screen.py` | Code mort | jamais importé |

## Couverture initiale (matrice agrégée)
- **OK** : 32
- **Partiel** : 7
- **Manquant** : 11
- **Cassé** : 4
- **Total** : **54 fonctionnalités identifiées**

## Dépendances externes
```
customtkinter>=5.2.0,<6.0.0    UI
darkdetect>=0.8.0              auto-thème
Pillow>=10.0.0                 décodage images
exifread>=3.0.0                fallback EXIF
piexif>=1.1.3                  écriture EXIF
pillow-heif>=0.13.0            HEIC
requests>=2.31.0               géocodage
```
Optionnels : `blake3` (hash plus rapide), `send2trash` (corbeille), `PyYAML` (config doublons).

## Zones les plus à risque
1. **Cohérence FileManager partagé** — chaque frame en crée un sien : Historique cassé, rollback inopérant.
2. **Annulation `_cancel_requested`** — flag posé mais jamais lu par `SmartOrganizer` ni par les threads de doublons en cours d'organisation.
3. **Tests unitaires existants** — référencent `src.core.scanner.PhotoScanner`, `src.core.organizer.Organizer`, `src.core.metadata.MetadataExtractor` qui **n'existent pas**. La suite ne s'exécute pas.
4. **Filtrage des dossiers système** dans le scan de doublons (récursion sur `$Recycle.Bin` après TRASH).
5. **Compteur fichiers source absent** côté UI (T-030..T-033 du contexte tests).
