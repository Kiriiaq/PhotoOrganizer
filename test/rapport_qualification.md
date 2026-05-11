# Rapport de qualification — PhotoOrganizer

## 1. Identification

| Champ | Valeur |
|---|---|
| **Outil** | PhotoOrganizer |
| **Version** | 2.0.0 |
| **Testeur** | _(à compléter)_ |
| **Date** | _(à compléter)_ |
| **Environnement** | Windows 10/11 64-bit, Python 3.11, écran 1920×1080 |
| **Build hash** | _(à compléter — `git rev-parse HEAD`)_ |
| **Stack** | Python 3.11 + CustomTkinter 5.2 + tkinterdnd2 + plyer + Pillow + piexif |

## 2. Périmètre testé

### 2.1 Fonctionnalités couvertes

| Domaine | Couverture |
|---|---|
| **IHM** (4 panneaux) | 117 widgets interactifs identifiés, tous couverts par `validation_ihm.html` |
| **Organisation par critères** | Date / Appareil / GPS / Multilayer + ordre |
| **Filtres pré-traitement** | Date / Taille / Rating / Mots-clés |
| **Comportements avancés** | Skip identique / Pairs RAW+JPEG / Cleanup / Validate disk / Notif / Mode incrémental |
| **Détection rafales** | Sous-dossier Burst_NN/ avec threshold + min_count |
| **Renommage par template** | 10 exemples prêts à l'emploi + tokens dynamiques |
| **Presets** | Save / Load / Delete |
| **Doublons** | 4 modes (DRY_RUN/DELETE/MOVE/TRASH) × 4 algos × règles conservation |
| **Historique** | Rollback last / all + invariant arithmétique |
| **Paramètres** | Thème, planification, cache, géocodage, logs |
| **Schedule** | Planification quotidienne in-app |
| **Tooltips** | 110+ entrées centralisées en français |

### 2.2 Hors périmètre

- Tests UI multi-écran HiDPI (à valider manuellement via captures séparées)
- Tests sur Linux / macOS (Stack supporte mais qualif limitée à Windows)
- Tests sur Python autres que 3.11
- Tests de localisation autre que français

### 2.3 Données utilisées

| Jeu d'entrée | Contenu | Volume |
|---|---|---|
| `input_nominal` | Photos JPG avec EXIF complet (date+camera) | 50 |
| `input_vide` | Dossier vide | 0 |
| `input_volumineux` | Photos JPG synthétiques | 1000 (200 en dev) |
| `input_mauvais_format` | .txt / .pdf / .docx factices + 1 jpg valide | 4 |
| `input_caracteres_speciaux` | Noms avec accents / emojis / μ Ω ± ° | 8 |
| `input_corrompu` | JPG tronqué + 0 byte + 1 intact | 3 |
| `input_gps_piexif` | EXIF GPS rationnels piexif (Paris/London/NYC/Tokyo/Sydney) | 5 |
| `input_pairs` | Paires .CR2 + .JPG même stem | 20 (10 paires) |
| `input_bursts` | 5 photos à 1s d'écart + 1 isolée | 6 |
| `input_pas_exif` | Photos sans aucune métadonnée | 3 |
| `input_doublons` | 10 originaux + 10 doublons exacts | 20 |
| `input_keywords` | Photos avec mots-clés EXIF (vacances, mariage, …) | 5 |

## 3. Synthèse chiffrée

> ⚠️ Section à compléter après exécution complète. Les chiffres ci-dessous
> proviennent de l'exécution partielle (run_tests.py sur 16 scénarios).

### 3.1 Exécution automatisée (run_tests.py)

| Scénario | Input | Résultat |
|---|---|---|
| T-051 | input_nominal | 50/50 OK · 0 skip · 0 err · 0.26 s |
| T-052 | input_vide | 0/0 OK · 0 skip · 0 err · 0.00 s |
| T-053 | input_volumineux | 200/200 OK · 0 skip · 0 err · 0.31 s |
| T-055 | input_caracteres_speciaux | 8/8 OK · 0 skip · 0 err · 0.01 s |
| T-056 | input_corrompu | 3/3 OK · 0 skip · 0 err · 0.31 s |
| T-057 | input_gps_piexif | 5/5 OK · 0 skip · 0 err · 0.01 s |
| T-058 | input_pairs | 20/20 OK · 0 skip · 0 err · 2.33 s |
| T-059 | input_bursts | 6/6 OK · 0 skip · 0 err · 0.01 s |
| T-060 | input_pas_exif | 3/3 OK · 0 skip · 0 err · 0.02 s |
| T-066/068/069/070/074 | input_nominal | 50/50 OK chacun |
| T-076 | input_bursts | 6/6 OK |
| T-079 | input_pas_exif | 3/3 OK |

### 3.2 Non-régression (compare_outputs.py)

| Test | Statut | Détail |
|---|---|---|
| T-051 | ✅ OK | Arbo year/month/day identique vs ref |
| T-055 | ✅ OK | Caractères spéciaux préservés |
| T-057 | ✅ OK | GPS Lat_x_Lon_y reproductible |
| T-059 | ✅ OK | Burst_01/ avec 5 photos |
| T-066 | ✅ OK | Format year/month/day stable |
| T-068 | ✅ OK | Multilayer date+camera+location stable |
| T-074 | ✅ OK | Renommage template reproductible |
| T-076 | ✅ OK | Bursts vs ref |
| T-079 | ✅ OK | « Sans date » fallback stable |

**9 / 9 tests de non-régression OK** — diff = 0 vs vérité terrain figée.

### 3.3 Tests pytest internes (préalables)

| Suite | Tests | Statut |
|---|---|---|
| Smoke tests UI v3 | 24 | ✅ |
| Smoke tests UX v4 | 21 | ✅ |
| Fonctionnels organizer | 20 | ✅ |
| Fonctionnels FileManager | 7 | ✅ |
| Fonctionnels Duplicates | 6 | ✅ |
| Fonctionnels Config | 4 | ✅ |
| Imports smoke | 8 | ✅ |
| Modules historiques | 8 | ✅ |
| **Total non-slow** | **98 / 98** | ✅ |

### 3.4 Tableau par catégorie (à compléter manuellement)

| Catégorie | Total | OK | NOK | NA | À faire | Taux |
|---|---|---|---|---|---|---|
| IHM | 30 | _( via validation_ihm.html )_ | | | | |
| Paramètres | 20 | | | | | |
| Entrées | 15 | _( via run_tests.py )_ | | | | |
| Sorties | 15 | | | | | |
| Cas limites | 25 | | | | | |
| Performance | 10 | | | | | |
| Robustesse | 20 | | | | | |
| Régression | 15 | 9 ✅ | 0 | 6 | 0 | 60 % auto |
| **TOTAL** | **150** | | | | | |

## 4. Anomalies détectées

> Section à remplir au fur et à mesure de l'exécution manuelle.

| ID Test | Sévérité | Description | Reproductibilité | Contournement |
|---|---|---|---|---|
| _(aucune anomalie détectée pour l'instant)_ | | | | |

## 5. Couverture fonctionnelle (matrice exigences × tests)

Référentiel d'exigences : 8 catégories préfixées `REQ-IHM-*`, `REQ-PRM-*`,
`REQ-ENT-*`, `REQ-SOR-*`, `REQ-LIM-*`, `REQ-PRF-*`, `REQ-ROB-*`, `REQ-REG-*`.

| Catégorie | Nombre d'exigences | Tests couvrants |
|---|---|---|
| REQ-IHM-* | 30 | T-001 à T-030 |
| REQ-PRM-* | 20 | T-031 à T-050 |
| REQ-ENT-* | 15 | T-051 à T-065 |
| REQ-SOR-* | 15 | T-066 à T-080 |
| REQ-LIM-* | 25 | T-081 à T-105 |
| REQ-PRF-* | 10 | T-106 à T-115 |
| REQ-ROB-* | 20 | T-116 à T-135 |
| REQ-REG-* | 15 | T-136 à T-150 |
| **Total** | **150** | **150** |

Couverture : **1 test par exigence** (mapping 1:1).
Détail complet dans `matrice_tests.xlsx` feuille « Exigences ».

## 6. Conclusion

| | |
|---|---|
| **Verdict provisoire** | _(GO / NO-GO / GO conditionnel — à statuer après exécution complète)_ |
| **Tests automatisés exécutés** | 16 scénarios run_tests.py + 9 non-régression + 98 pytest internes |
| **Tests IHM manuels** | 117 widgets via validation_ihm.html (à compléter) |
| **Anomalies bloquantes** | 0 détectée à ce stade |
| **Anomalies majeures** | 0 détectée à ce stade |

### Conditions pour passage en production

1. ✅ Exécution complète de `validation_ihm.html` (117 widgets) avec ≥ 95 % de OK
2. ✅ Tests Performance T-106 à T-115 manuels (cold-start, RAM, scan 10k)
3. ✅ Tests Cas limites T-081 à T-105 manuels (chemin UTF-8, espace disque, …)
4. ✅ Aucune anomalie bloquante ; ≤ 2 anomalies majeures avec contournement documenté

## 7. Annexes

| Livrable | Chemin |
|---|---|
| Matrice tests détaillée | `test/matrice_tests.xlsx` |
| Checklist IHM interactive | `test/validation_ihm.html` |
| Inputs de test | `test/inputs/` (11 jeux) |
| Sorties de référence | `test/outputs_reference/` (9 tests figés) |
| Script génération inputs | `test/scripts/generate_inputs.py` |
| Script génération matrice | `test/scripts/generate_matrix.py` |
| Script exécution scénarios | `test/scripts/run_tests.py` |
| Script comparaison diff | `test/scripts/compare_outputs.py` |
| Audit visuel automatisé | `tools/visual_audit.py` |
| Build report | `build_report.md` |

### Commandes utiles

```bash
# Génération initiale (à faire une seule fois)
python test/scripts/generate_matrix.py
python test/scripts/generate_inputs.py --large 1000

# Exécution des scénarios automatisés
python test/scripts/run_tests.py
python test/scripts/run_tests.py --only T-051

# Comparaison vs références
python test/scripts/compare_outputs.py

# Validation IHM (ouvrir le HTML)
start test/validation_ihm.html

# Audit visuel (smoke test invariants)
python tools/visual_audit.py
```
