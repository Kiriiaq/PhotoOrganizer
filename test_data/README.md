# Dossier de qualification — PhotoOrganizer 2.3-dev

Dossier auto-contenu pour la **qualification fonctionnelle** de l'outil.
Structure conforme au prompt « Test IHM Advanced » (Edvance EPR/I&C).

> **Mise à jour 2026-05-19** — Ajout des tests T-151 à T-175 (25 nouveaux)
> pour la refonte v2.3 du panneau Organisation (4 onglets internes +
> bouton 💡 Exemples de marques + panneaux intégrés remplaçant les anciennes
> fenêtres modales) **et** le bouton 💡 Exemples de filtres dans l'onglet
> Filtrer (valeurs standards pour mots-clés, extensions, dimensions,
> orientation, note). Widgets W118-W134 ajoutés dans `validation_ihm.html`.

## Structure

```
test_data/
├── matrice_tests.xlsx          ← 189 tests catégorisés + traçabilité exigences (v2.3)
├── validation_ihm.html         ← checklist interactive 136 widgets (autonome, v2.3)
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
python test_data/scripts/generate_matrix.py
python test_data/scripts/generate_inputs.py --large 1000
```

### 2. Exécuter les scénarios automatisés
```bash
python test_data/scripts/run_tests.py
# → produit test_data/outputs_reels/ + _run_summary.json
```

### 3. Vérifier la non-régression
```bash
python test_data/scripts/compare_outputs.py
# → produit test_data/outputs_reels/_diff_report.md
# 9/9 OK = aucune régression
```

### 4. Valider l'IHM manuellement
Double-clic sur **`test_data/validation_ihm.html`** dans l'explorateur Windows.
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

8 catégories × 189 tests numérotés `T-001` à `T-175`, traçables vers
8 référentiels d'exigences :

| Catégorie | Range v2.0 | Range v2.3 ajout | Finition 2026-05-19 | Exigences |
|---|---|---|---|---|
| IHM | T-001 à T-030 | T-151 à T-159 | T-166 à T-168 | REQ-IHM-01 à REQ-IHM-42 |
| Paramètres | T-031 à T-050 | T-160 à T-164 | T-169 à T-174 | REQ-PRM-01 à REQ-PRM-31 |
| Entrées | T-051 à T-065 | — | — | REQ-ENT-01 à REQ-ENT-15 |
| Sorties | T-066 à T-080 | — | — | REQ-SOR-01 à REQ-SOR-15 |
| Cas limites | T-081 à T-105 | — | — | REQ-LIM-01 à REQ-LIM-25 |
| Performance | T-106 à T-115 | — | — | REQ-PRF-01 à REQ-PRF-10 |
| Robustesse | T-116 à T-135 | — | — | REQ-ROB-01 à REQ-ROB-20 |
| Régression | T-136 à T-150 | T-165 | T-175 | REQ-REG-01 à REQ-REG-17 |

### Périmètre v2.3 (15 tests T-151 à T-165)

| ID | Couverture |
|---|---|
| T-151 → T-152 | Onglets internes du panneau Organisation : 4 onglets, défaut « Organiser » |
| T-153 → T-154 | Bouton 💡 Exemples de marques + info-bulle |
| T-155 → T-159 | Panneau intégré (Aperçu, fin d'opération, sauvegarder un preset, liste des fichiers) |
| T-160 → T-164 | Comportement du panneau 💡 marques (ajout, déduplication, vider, marques EXIF de la source, liste des marques courantes) |
| T-165 | Invariant de non-régression : aucune nouvelle fenêtre créée sur les actions du panneau Organisation |

### Périmètre finition 2026-05-19 — II — Quarantaine réversible (14 tests T-176 à T-189)

| ID | Couverture |
|---|---|
| T-176 → T-179 | Quarantaine : déplacement, manifest JSON, collisions, erreurs |
| T-180 → T-182 | Restauration : retour à la source, recréation dossier, suffixe `_restored` |
| T-183 → T-184 | Vidage vers corbeille système + rechargement manifest après crash |
| T-185 → T-187 | Intégration `file_manager` : record_operation('trash'), rollback_last, rollback_all mixte |
| T-188 → T-189 | IHM : bouton « 🗑 Vider quarantaine » + API DuplicateManager |

### Périmètre finition 2026-05-19 (10 tests T-166 à T-175)

| ID | Couverture |
|---|---|
| T-166 → T-168 | Bouton 💡 Exemples de filtres présent + info-bulle + panneau intégré |
| T-169 | Section Mots-clés : un clic ajoute au CSV `filter_keywords` ; déduplication |
| T-170 | Section Extensions : 3 sous-listes (images / RAW / vidéos) cumulent dans `filter_extensions` |
| T-171 | Section Dimensions : boutons ↧ min et ↥ max appliquent au bon champ |
| T-172 | Section Orientation : 4 boutons (Toutes / Paysage / Portrait / Carré) |
| T-173 | Section Note : 6 boutons (0 toutes, ★ à ★★★★★) appliquent 0 à 5 |
| T-174 | Constantes standards exposées : COMMON_KEYWORDS / EXTENSIONS_* / DIMENSIONS / ORIENTATIONS |
| T-175 | Invariant de non-régression : aucune nouvelle fenêtre sur l'ouverture du panneau 💡 Filtres |

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
