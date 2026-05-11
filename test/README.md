# Dossier de qualification — PhotoOrganizer 2.0.0

Dossier auto-contenu pour la **qualification fonctionnelle** de l'outil.
Structure conforme au prompt « Test IHM Advanced » (Edvance EPR/I&C).

## Structure

```
test/
├── matrice_tests.xlsx          ← 150 tests catégorisés + traçabilité exigences
├── validation_ihm.html         ← checklist interactive 117 widgets (autonome)
├── rapport_qualification.md    ← squelette du rapport à compléter
├── inputs/                     ← 11 jeux d'entrée réalistes
│   ├── input_nominal/                  (50 photos avec EXIF complet)
│   ├── input_vide/                     (dossier vide)
│   ├── input_volumineux/               (1000 photos, --large)
│   ├── input_mauvais_format/           (txt, pdf, docx factices)
│   ├── input_caracteres_speciaux/      (accents, μ, Ω, ±, °, emojis)
│   ├── input_corrompu/                 (jpg tronqué + 0 byte)
│   ├── input_gps_piexif/               (rationnels EXIF — Paris/London/...)
│   ├── input_pairs/                    (paires CR2 + JPEG)
│   ├── input_bursts/                   (rafale 5 photos < 3s)
│   ├── input_pas_exif/                 (photos sans métadonnées)
│   ├── input_doublons/                 (10 originaux + 10 doublons exacts)
│   └── input_keywords/                 (mots-clés EXIF)
├── outputs_reference/          ← 9 sorties figées comme vérité terrain
│   ├── T-051/  T-055/  T-057/  T-059/
│   ├── T-066/  T-068/  T-074/  T-076/  T-079/
├── outputs_reels/              ← rempli à chaque exécution de run_tests.py
└── scripts/
    ├── generate_matrix.py      ← (re)génère matrice_tests.xlsx
    ├── generate_inputs.py      ← (re)génère inputs/*
    ├── run_tests.py            ← lance 16 scénarios automatisés
    └── compare_outputs.py      ← diff réel vs référence (rapport Markdown)
```

## Quickstart

### 1. Régénérer matrice + inputs (idempotent)
```bash
python test/scripts/generate_matrix.py
python test/scripts/generate_inputs.py --large 1000
```

### 2. Exécuter les scénarios automatisés
```bash
python test/scripts/run_tests.py
# → produit test/outputs_reels/ + _run_summary.json
```

### 3. Vérifier la non-régression
```bash
python test/scripts/compare_outputs.py
# → produit test/outputs_reels/_diff_report.md
# 9/9 OK = aucune régression
```

### 4. Valider l'IHM manuellement
Double-clic sur **`test/validation_ihm.html`** dans l'explorateur Windows.
- Cocher chaque widget (OK / NOK / NA)
- Saisir une **valeur observée** et un **commentaire** si NOK
- État persisté en `localStorage` (reprendre où on s'est arrêté)
- **Exporter JSON** : sauvegarde la session pour archivage qualité
- **Générer Markdown** : copie un résumé dans le presse-papier, à coller dans `rapport_qualification.md`

### 5. Compiler le rapport final
- Ouvrir `rapport_qualification.md`
- Remplir les sections 3 (synthèse) et 4 (anomalies)
- Statuer GO/NO-GO/GO conditionnel en section 6

## Catégories et traçabilité

8 catégories × 150 tests numérotés `T-001` à `T-150`, traçables vers
8 référentiels d'exigences :

| Catégorie | Range | Exigences |
|---|---|---|
| IHM | T-001 à T-030 | REQ-IHM-01 à REQ-IHM-30 |
| Paramètres | T-031 à T-050 | REQ-PRM-01 à REQ-PRM-20 |
| Entrées | T-051 à T-065 | REQ-ENT-01 à REQ-ENT-15 |
| Sorties | T-066 à T-080 | REQ-SOR-01 à REQ-SOR-15 |
| Cas limites | T-081 à T-105 | REQ-LIM-01 à REQ-LIM-25 |
| Performance | T-106 à T-115 | REQ-PRF-01 à REQ-PRF-10 |
| Robustesse | T-116 à T-135 | REQ-ROB-01 à REQ-ROB-20 |
| Régression | T-136 à T-150 | REQ-REG-01 à REQ-REG-15 |

## Statut couverture (au moment de la livraison)

| | |
|---|---|
| **Tests automatisés exécutés** | 16 scénarios run_tests.py — 100 % OK |
| **Tests non-régression** | 9 / 9 ✅ (compare_outputs.py) |
| **Tests pytest internes** | 98 / 98 ✅ |
| **Tests IHM manuels** | 117 widgets listés, validation à effectuer |
| **Tests Performance manuels** | 10 (T-106 à T-115) à effectuer |
| **Anomalies bloquantes** | 0 |

## Réutilisation pour un autre outil

Le format est volontairement générique. Pour adapter à un autre outil :

1. Adapter `WIDGETS` dans `validation_ihm.html` (ligne ~150)
2. Adapter les `SCENARIOS` dans `scripts/run_tests.py`
3. Adapter la liste `tests = [...]` dans `scripts/generate_matrix.py`
4. Adapter les fonctions `gen_*` dans `scripts/generate_inputs.py`
5. Mettre à jour les sections 1, 2, 7 de `rapport_qualification.md`

L'esquelette HTML, scripts et structure sont conçus pour servir de **template
Edvance** réutilisable d'un outil à l'autre.
