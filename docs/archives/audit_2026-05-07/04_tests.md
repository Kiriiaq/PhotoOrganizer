# Phase 4 — Tests pytest

## Architecture
```
tests/
├── conftest.py                 # fixtures partagées + sys.path + marqueurs
├── test_modules.py             # tests d'intégration migrés (réécrits depuis 0)
├── smoke/
│   └── test_imports.py         # tous les modules importables, classes exposées
├── functional/
│   ├── test_file_manager.py    # 8 tests : copy/move/rollback/list_files
│   ├── test_organizer.py       # 7 tests : organize/cancel/dataclass
│   ├── test_duplicates.py      # 6 tests : exclusion corbeille système
│   └── test_config.py          # 6 tests : ConfigManager + presets
├── volume/
│   └── test_volume.py          # 3 tests `@slow` : 10k fichiers, 10 Mo, fuites
├── perf/
│   └── test_perf.py            # 2 benchs pytest-benchmark
└── stress/
    └── test_stress.py          # 3 tests `@slow` : 1k cycles, 8 threads, cancel
```

## Résultats — `pytest -m "not slow"`
```
40 passed, 6 deselected in 4.52 s
```
0 échec, 0 warning bloquant. Les tests slow (volume + stress) sont collectés
mais désélectionnés par défaut — `pytest -m slow` pour les exécuter.

## Couverture
Globale : **29 %** (lignes physiques sur 4 103). Détail :

| Zone                | Couverture | Notes                                         |
| ------------------- | ----------:| --------------------------------------------- |
| `core/operations/file_manager.py` | **73 %** | branches rollback couvertes |
| `core/operations/organizer.py`    | **68 %** | branches `cancel`, dataclass, sanitize OK |
| `core/metadata/camera_detector.py`| **79 %** | |
| `core/metadata/date_extractor.py` | **66 %** | parsing de noms de fichier exercé |
| `core/metadata/exif_extractor.py` | **47 %** | les chemins ExifTool/HEIC nécessitent fixtures réelles |
| `src/config/duplicate_config.py`  | **75 %** | YAML + dataclasses |
| `core/operations/duplicate_*.py`  | 23-24 %  | core de scan partiellement couvert |
| `utils/config.py`                 | **84 %** | round-trip + reset + corruption |
| `src/cli/duplicate_cli.py`        | 0 %      | non utilisé par l'IHM, code à part |
| `src/ui/frames/*`                 | 9-15 %   | nécessite Tk root → tests UI off CI |
| `src/utils/splash_screen.py`      | 0 %      | code mort, à supprimer en Phase 5 |

**L'objectif de ≥ 80 % global** est inaccessible sans monter une suite UI Tk
réelle (instable en CI). Les modules de logique métier (file_manager, organizer,
config) sont au-dessus de 65 %.

## Bugs révélés par les tests
1. **`exif_extractor._find_exiftool` crashait** quand `EXIFTOOL_PATH=""` (chaîne vide) → `OSError WinError 87`. Corrigé pendant la Phase 3 (un test passait grâce à ça).
2. **`tests/test_modules.py` ancien** importait des modules inexistants — la suite était collectivement non-exécutable. Réécrit.

## Benchmarks (pytest-benchmark)
| Test                        | Min       | Mean      | Cible     | Statut |
| --------------------------- | ---------:| ---------:| ---------:| ------ |
| `_get_unique_name` simple   |  240 µs   |  261 µs   | < 1 ms    | ✅     |
| `list_files` sur 1 000 fichiers | 128 ms | 132 ms | < 200 ms | ✅     |

## Tests slow (à lancer manuellement)
```
pytest -m slow                   # ~30-60 s
```
- `test_list_files_large_directory` : 10 000 entrées (~1.5 s sur le poste)
- `test_no_memory_leak_repeated_scan` : 20 itérations × 500 entrées avec
  `tracemalloc.compare_to`. Tolérance : 2 Mo de croissance résiduelle.
- `test_copy_large_file` : 10 Mo
- `test_repeated_copy_rollback_cycle` : 1 000 cycles
- `test_concurrent_list_files` : 8 threads en parallèle
- `test_organizer_cancellable_under_stress` : annulation après 5 fichiers sur 50

## Commande
```
make test           # rapide (sans slow)
make test-all       # tout, y compris slow et benchmark
```
