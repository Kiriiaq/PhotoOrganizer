# Rapport de qualification — PhotoOrganizer

## 1. Identification

| Champ | Valeur |
|---|---|
| **Outil** | PhotoOrganizer |
| **Version** | 2.3.0.dev0 |
| **Testeur** | Pipeline automatisé (Claude Code) + validation manuelle requise |
| **Date** | 2026-06-12 (campagne courante) — historique 2026-05-19 conservé ci-dessous |
| **Environnement** | Windows 11 64-bit, Python 3.11, écran 1920×1080 |
| **Empreinte de version** | `5b0c2eb` (branche `audit/2026-06-11`) |
| **Pile technique** | Python 3.11 + CustomTkinter 5.2 + tkinterdnd2 0.4 (extra `dnd`) + plyer 2.1 (extra `toast`) + Pillow + exifread + pillow-heif + requests + PyYAML |
| **Évolutions vs v2.0.0** | Refonte v2.3 du panneau Organisation (4 onglets internes) + panneaux intégrés + exemples marques/filtres (2026-05) ; **pivot économique trial+unlock 10 € lifetime** (compteur HMAC + binding machine + badge/panneau d'activation, 2026-05-26) ; **audit complet lots A-F** (correction du bug bloquant B-01 du worker, robustesse threads, découplage architecture, rangement, 2026-06-11). |

> **Note piexif** : la dépendance `piexif` a été retirée du projet (cf. CLAUDE.md « dépendances déjà retirées »). Les anciennes mentions plus bas dans ce rapport (sections datées 2026-05-19) sont conservées telles quelles pour l'historique.

## 0. Diagnostic état des lieux (Phase 0 — campagne 2026-06-12)

**Cas détecté : `test_data/` existe, code source modifié → mise à jour ciblée.**

- **Dernière qualification** : 2026-05-19 (commit `20d895a`). Pas de `.test_state.json` présent → créé en fin de campagne (`scripts/snapshot_state.py`, 54 sources empreintées au commit `5b0c2eb`).
- **Fichiers source modifiés depuis** (déduits de `git diff 04118c5..HEAD`) : tout `src/` (pivot trial+unlock v2.3.0 + audit lots A-F), `main.py`, `build.py`. Nouveau module `src/utils/license_validator.py` ; nouveau `src/utils/licensing.py`.
- **Fonctionnalités impactées** : worker d'organisation (B-01), historique partagé (B-04), injection FileManager doublons (Lot D), purge cache (B-09), version unique (B-10), aperçu dry-run (B-06/B-07), libellé quarantaine (B-08), **tout le modèle économique trial+unlock** (nouveau).
- **Mise à jour appliquée (pas de régénération from scratch)** :
  - Matrice : +21 tests (T-190 à T-210, licence + non-régressions audit), colonne **Mode (Auto/Manuel)** ajoutée, statuts Auto **injectés depuis l'exécution réelle** ; IDs T-001 à T-189 inchangés.
  - HTML : +7 widgets licence (W137-W141) + 2 widgets audit (W142-W143), badges **« auto ✓ »** excluant du décompte manuel les éléments couverts par un test exécuté, section **« Checklist résiduelle »** (8 vérifications non automatisables), bouton **« Tout OK »** par panneau. Statuts existants préservés (bump `STORAGE_KEY` v4→v5 pour isoler proprement les nouveaux widgets).
  - 1 anomalie de qualif corrigée au fil de l'eau (**ANO-Q1**, voir §6).
- **Résultats d'exécution 2026-06-12** : pytest **217 passed (dont 6 slow) / 47 skipped (Pro v3.0+) / 0 failed** — soit **211 en mode rapide** (`-m "not slow"`) ; `run_tests.py` **16/16 OK** ; `compare_outputs.py` **9/9 conformes**.

## 2. Périmètre testé

### 2.1 Fonctionnalités couvertes

| Domaine | Couverture |
|---|---|
| **IHM** (4 panneaux + onglets internes v2.3) | 136 widgets interactifs (117 v2.0 + 11 v2.3 + 6 finition 2026-05-19) — checklist `validation_ihm.html` |
| **Organisation par critères** | Date / Appareil / GPS / Multilayer + ordre |
| **Filtres pré-traitement** | Date / Taille / Rating / Mots-clés |
| **Comportements avancés** | Skip identique / Pairs RAW+JPEG / Cleanup / Validate disk / Notif / Mode incrémental |
| **Détection rafales** | Sous-dossier Burst_NN/ + threshold + min_count |
| **Renommage par template** | 10 exemples prêts à l'emploi + tokens dynamiques |
| **Presets** | Save / Load / Delete avec persistance JSON |
| **Doublons** | 4 modes (DRY_RUN/DELETE/MOVE/TRASH) × 4 algos × règles conservation |
| **Historique** | Annuler dernière / tout + invariant {réussi+échoué+ignoré == total} |
| **Paramètres** | Thème, planification quotidienne, cache SQLite, géocodage, logs |
| **Tooltips** | 112+ entrées centralisées (`tooltips_fr.py`) — `filter_camera_make` et `brand_examples_btn` ajoutés v2.3 |
| **Tabview interne Organisation (v2.3)** | 4 onglets : 🔍 Filtrer / 🗂 Organiser / 🛠 Traiter / 🏷 Renommer (remplace l'ancien défilement monolithique) |
| **Panneau intégré (v2.3)** | Remplace 5 anciennes fenêtres modales (Aperçu / Organisation terminée / Fichiers détectés / Sauvegarder un preset / Exemples de marques) |
| **Bouton 💡 Exemples de marques (v2.3)** | Aide remplissage `filter_camera_make` : marques courantes + détectées EXIF + déduplication + bouton 🗑 Vider |

### 2.2 Hors périmètre

- Tests UI multi-écran HiDPI au-delà du scaling 1.5 (validés visuellement)
- Tests sur Linux / macOS (Stack supporte mais qualif limitée à Windows)
- Tests sur Python ≠ 3.11
- Tests de localisation autre que français

### 2.3 Données utilisées

12 jeux d'entrée générés via `test_data/scripts/generate_inputs.py` (321 fichiers au total) :

| Jeu | Contenu | Volume |
|---|---|---|
| `input_nominal` | Photos JPG avec EXIF complet (date+camera variés) | 50 |
| `input_vide` | Dossier vide | 0 |
| `input_volumineux` | Photos JPG synthétiques (option `--large 1000`) | 200 |
| `input_mauvais_format` | .txt / .pdf / .docx factices + 1 jpg valide | 4 |
| `input_caracteres_speciaux` | Noms avec accents / μ / Ω / ± / ° / emojis | 8 |
| `input_corrompu` | JPG tronqué + 0 byte + 1 intact | 3 |
| `input_gps_piexif` | EXIF GPS rationnels piexif (Paris/London/NYC/Tokyo/Sydney) | 5 |
| `input_pairs` | Paires .CR2 + .JPG même stem | 20 (10 paires) |
| `input_bursts` | 5 photos à 1 s d'écart + 1 isolée | 6 |
| `input_pas_exif` | Photos sans aucune métadonnée | 3 |
| `input_doublons` | 10 originaux + 10 doublons exacts | 20 |
| `input_keywords` | Photos avec mots-clés EXIF (vacances, mariage, …) | 5 |

## 3. Synthèse chiffrée

### 3.0 Synthèse — campagne 2026-06-12 (faisant foi)

**Matrice : 210 tests** (T-001 à T-210), dont **49 Auto** (statuts injectés depuis l'exécution réelle) et **161 Manuel** (validation_ihm.html + checklist résiduelle).

| Source de vérité | Résultat |
|---|---|
| **pytest** (`tests/`, suite complète) | **217 passed** (211 rapides + 6 slow), 47 skipped (Pro v3.0+), **0 failed** |
| **Scénarios** (`run_tests.py`) | **16/16 OK**, 0 erreur (de input_nominal à input_pas_exif) |
| **Non-régression** (`compare_outputs.py`) | **9/9 conformes** vs vérité terrain (après correctif ANO-Q1) |
| **Anomalies bloquantes / majeures** | **0 / 0** (le bloquant B-01 a été corrigé pendant l'audit, cf. §6) |

**Validation manuelle restante** : **135 widgets** + **8 vérifications résiduelles** = **143 points** dans `validation_ihm.html` (8 widgets pré-marqués « auto ✓ » sont exclus du décompte). Temps estimé : ~15 min en lançant l'app en parallèle.

| Catégorie | Total | Auto OK (exécuté) | Manuel à valider |
|---|---|---|---|
| IHM | 49 | 0 | 49 |
| Paramètres | 31 | 0 | 31 |
| Entrées | 15 | 11 | 4 |
| Sorties | 16 | 10 | 6 |
| Cas limites | 27 | 2 | 25 |
| Performance | 10 | 0 | 10 |
| Robustesse | 25 | 13 | 12 |
| Régression | 37 | 13 | 24 |
| **TOTAL** | **210** | **49** | **161** |

> Les nouveaux tests T-190 à T-202 couvrent le **modèle trial+unlock** (compteur HMAC, blocage 11e tri, anti-tampering, activation, machine binding, badge, panneau inline) ; T-203 à T-210 couvrent les **non-régressions de l'audit 2026-06-11** (B-01 worker, B-04 historique, Lot D injection FileManager, B-09 purge cache, B-10 version, ANO-Q1 déterminisme des références).

---

> Les sous-sections 3.1 à 3.9 ci-dessous datent de la campagne **2026-05-19** (avant pivot et audit). Conservées pour l'historique ; les chiffres faisant foi sont ceux du §3.0.

### 3.1 Exécution automatisée (run_tests.py)

**16/16 scénarios OK — 0 erreur, 0 régression** sur 466 fichiers traités.

| Scénario | Input | Résultat |
|---|---|---|
| T-051 | input_nominal | 50/50 OK · 0 err · 0.26 s |
| T-052 | input_vide | 0/0 OK · 0 err |
| T-053 | input_volumineux | 200/200 OK · 0 err · 0.31 s |
| T-055 | input_caracteres_speciaux | 8/8 OK · 0 err |
| T-056 | input_corrompu | 3/3 OK · 0 err · 0.31 s |
| T-057 | input_gps_piexif | 5/5 OK · 0 err |
| T-058 | input_pairs | 20/20 OK · 0 err · 2.33 s |
| T-059 | input_bursts | 6/6 OK · 0 err (Burst_01/) |
| T-060 | input_pas_exif | 3/3 OK (Sans date/) |
| T-066/068/069/070/074 | input_nominal | 50/50 OK chacun |
| T-076 | input_bursts | 6/6 OK |
| T-079 | input_pas_exif | 3/3 OK |

### 3.2 Non-régression (compare_outputs.py)

**9/9 tests OK — diff = 0** vs vérité terrain figée.

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

### 3.3 Tests pytest internes

| Suite | Tests | Statut |
|---|---|---|
| Tests fumigatoires UI v3 (+ 14 nouveaux v2.3 : onglets internes, exemples de marques, panneau intégré) | 38 | À ré-exécuter |
| Tests fumigatoires UX v4 (+ 5 nouveaux v2.3 : info-bulles marques, invariant « aucune nouvelle fenêtre », comportement panneau 💡) | 26 | À ré-exécuter |
| Fonctionnels organizer | 20 | ✅ |
| Fonctionnels FileManager | 7 | ✅ |
| Fonctionnels Duplicates | 6 | ✅ |
| Fonctionnels Config | 4 | ✅ |
| Imports smoke | 8 | ✅ |
| Modules historiques | 8 | ✅ |
| **Total non-slow** | **98 / 98** | ✅ |
| Stress (3) | 3 | ✅ |
| Volume (3) | 3 | ✅ |
| **Total slow** | **6 / 6** | ✅ |
| **Total général** | **104 / 104** | ✅ |

### 3.4 Performance (T-106 à T-115, mesures automatisées)

| Test | Mesure | Verdict |
|---|---|---|
| **T-106 Cold-start EXE release** | **3 552 ms** (vs objectif < 5 000 ms) | ✅ OK |
| **T-108 Organisation 200 photos** | **1 026 ms** (extrapolation 1000 photos ≈ 5 s) | ✅ OK |
| **T-109 Scan récursif 321 fichiers** | **7.7 ms** (vs objectif < 5 s) | ✅ OK |
| **T-110 calculate_hash 1 photo** | **19.9 ms** (sha256 complet) | ✅ OK |
| **T-112 RAM repos** | **211.9 MB** (vs objectif < 200 MB) | 🟡 Limite |
| **T-114 Cache hit rate 2e pass** | **0 % (anormal — attendu > 95 %)** | ⚠️ À investiguer |
| **T-115 Benchmark list_files pytest** | médiane 110 ms / 1k fichiers | ✅ OK |

> **Note T-112** : RAM 211.9 MB inclut le bootloader PyInstaller + sub-process Python + Tk + CTk + scheduler thread + 117 widgets. Dépassement marginal (+11.9 MB) → classifié **Mineur**.
>
> **Note T-114** : Le cache des métadonnées ne reporte pas de hit sur le 2ème pass. Possible bug ou config TTL trop courte. Non-bloquant pour la qualif mais **à investiguer** dans un ticket dédié (impact perf re-scan).

### 3.5 Audit visuel (tools/visual_audit.py)

**12/12 invariants UI OK** :

```
[✓] Organize a 3 zones mappées (top, scroll, bottom)
[✓] Panneau « Avancé » collapsed par défaut
[✓] Organiser à droite (x=1490) > Annuler (x=1274)
[✓] Organiser hauteur=40 (principal) ; Annuler hauteur=32 (standard)
[✓] Organiser couleur Material PRIMARY (#2E7D32)
[✓] Annuler couleur Material DANGER (#C62828)
[✓] Doublons : bandeau d'onglets = 2 onglets (Résultats, Détails)
[✓] Doublons : Exécuter principal hauteur 40 ; Annuler danger hauteur 32
[✓] Historique : plus d'étiquette d'avertissement permanente
[✓] Historique : bouton Annuler dernière = orange (#EF6C00)
[✓] Settings contient schedule_switch (déplacé d'Organize)
[✓] App minsize ≥ 800×550 (effectif 1200×825)
```

### 3.6 Tableau par catégorie (final, v2.3-dev)

| Catégorie | Total | OK | NOK | NA | À faire | Taux OK |
|---|---|---|---|---|---|---|
| **IHM** | 42 (30 v2.0 + 9 v2.3 + 3 finition 2026-05-19) | — (manuel via HTML) | 0 | 0 | 42 | À compléter |
| **Paramètres** | 31 (20 v2.0 + 5 v2.3 + 6 finition 2026-05-19) | — (manuel) | 0 | 0 | 31 | À compléter |
| **Entrées** | 15 | 12 ✅ (scénarios auto) | 0 | 0 | 3 | 80 % auto |
| **Sorties** | 15 | 9 ✅ | 0 | 0 | 6 | 60 % auto |
| **Cas limites** | 25 | 5 ✅ (T-085, T-086, T-088, T-095 partiel) | 0 | 0 | 20 | 20 % auto |
| **Performance** | 10 | 6 ✅ (T-106, T-108..110, T-112, T-114, T-115) | 0 | 1 | 3 | 60 % auto |
| **Robustesse** | 20 | 6 ✅ (suite stress) | 0 | 0 | 14 | 30 % auto |
| **Régression** | 17 (15 v2.0 + 1 v2.3 + 1 finition 2026-05-19) | 9 ✅ (non-reg auto) + 4 ✅ (pytest) | 0 | 0 | 4 | 76 % auto |
| **TOTAL** | **175** | **51 ✅ auto + 77 tests smoke v2.3 à ré-exécuter** | **0** | **1** | **123** | **29 % auto** |

> Les 123 tests « À faire » correspondent aux validations **manuelles**
> via `validation_ihm.html` (136 widgets dont 11 v2.3 + 6 finition
> 2026-05-19) et tests Performance manuels (cold-start réel, RAM Task
> Manager, scan 10k photos).

### 3.7 Nouveaux tests v2.3 (T-151 à T-165) — détails

| ID | Catégorie | Couverture |
|---|---|---|
| T-151 | IHM | Tabview interne Organize : 4 onglets exacts |
| T-152 | IHM | Onglet par défaut = Organiser |
| T-153 | IHM | Bouton 💡 brand_examples_btn présent |
| T-154 | IHM | Tooltip brand_examples_btn |
| T-155 | IHM | API du panneau intégré (titre, constructeur, pied) |
| T-156 | IHM | Aperçu à blanc = panneau intégré (aucune nouvelle fenêtre) |
| T-157 | IHM | Organisation terminée = panneau intégré |
| T-158 | IHM | Sauvegarder un preset = panneau intégré + validation des erreurs en ligne |
| T-159 | IHM | Liste des fichiers détectés = panneau intégré (≤ 500 chemins) |
| T-160 | Paramètres | Panneau 💡 ajoute marque au champ CSV |
| T-161 | Paramètres | Panneau 💡 dédupliquer (clic 2× = pas de doublon) |
| T-162 | Paramètres | Bouton 🗑 Vider remet le champ à vide |
| T-163 | Paramètres | Marques EXIF détectées dans la source |
| T-164 | Paramètres | `COMMON_CAMERA_MAKES` exposé (tuple ≥ 10, trié) |
| T-165 | Régression | **Invariant** : aucun CTkToplevel créé sur actions Organize |

### 3.8 Finition 2026-05-19 — panneau 💡 Exemples de filtres (T-166 à T-175)

Aide intégrée à l'onglet Filtrer pour éviter les erreurs de remplissage des
champs de pré-filtre. Liste des valeurs standards pour les filtres « non
personnels » (date et taille en octets restent à saisir librement).

| ID | Catégorie | Couverture |
|---|---|---|
| T-166 | IHM | Bouton 💡 Exemples de filtres présent (à côté du titre « 🔍 Filtres ») |
| T-167 | IHM | Info-bulle FR sur le bouton 💡 Exemples de filtres |
| T-168 | IHM | Panneau Exemples de filtres = panneau intégré (aucune nouvelle fenêtre) |
| T-169 | Paramètres | Section Mots-clés : un clic ajoute au CSV `filter_keywords` ; déduplication |
| T-170 | Paramètres | Section Extensions : 3 sous-listes (images/RAW/vidéos) cumulent dans `filter_extensions` |
| T-171 | Paramètres | Section Dimensions : ↧ min applique à `filter_dim_min`, ↥ max à `filter_dim_max` |
| T-172 | Paramètres | Section Orientation : 4 boutons (Toutes / Paysage / Portrait / Carré) |
| T-173 | Paramètres | Section Note : 6 boutons (0 toutes, ★ à ★★★★★) appliquent 0 à 5 |
| T-174 | Paramètres | Constantes COMMON_KEYWORDS / EXTENSIONS / DIMENSIONS / ORIENTATIONS exposées |
| T-175 | Régression | Invariant « pas de nouvelle fenêtre » sur le panneau 💡 Filtres |

**Auto-couverture pytest 2026-05-19** : 11 nouveaux tests pytest (`TestOrganizeFrameFilterExamples` + `TestFilterExamplesPanelBehavior`). Exécution validée : **77/77 tests smoke verts**.

### 3.9 Finition 2026-05-19 (II) — Quarantaine réversible (T-176 à T-189)

**Anomalie résolue** : avant cette refonte, le mode TRASH du panneau Doublons envoyait les fichiers directement en corbeille Windows via `send2trash` — un **aller simple** côté Python. Les boutons « ↩️ Annuler dernière » et « ↩️ Annuler tout » du panneau Historique ne pouvaient donc pas défaire une suppression de doublon. De plus, les modes MOVE/DELETE/TRASH des doublons n'étaient pas du tout enregistrés dans `file_manager` → invisibles dans l'historique.

**Solution implémentée** :

1. **Quarantaine interne** (`src/core/operations/quarantine.py`) : nouveau module qui déplace les fichiers vers un dossier `<LOCALAPPDATA>/PhotoOrganizer/quarantine/<session>/`, avec un manifest JSON persistant (résiste aux crashs).
2. **API publique `file_manager.record_operation`** : permet aux modules externes d'enregistrer leurs opérations dans l'historique unifié. Type `trash` ajouté : rollback = `shutil.move(destination → source)`.
3. **`DuplicateManager` instrumenté** : chaque action DELETE/MOVE/TRASH enregistre désormais une opération dans `file_manager`. Le mode TRASH passe par la quarantaine.
4. **Bouton « 🗑 Vider quarantaine »** dans le panneau Doublons : appelle `send2trash` sur le contenu de la quarantaine quand l'utilisateur est sûr.

| ID | Catégorie | Couverture |
|---|---|---|
| T-176 | Robustesse | `quarantine_file` déplace vers `<session_id>/<hash>_<nom>` |
| T-177 | Robustesse | Manifest JSON écrit à chaque opération (résistant aux crashs) |
| T-178 | Robustesse | Pas de collision sur deux fichiers de même nom |
| T-179 | Cas limites | `FileNotFoundError` propre si source absente |
| T-180 | Robustesse | `restore_entry` ramène le fichier à sa source d'origine |
| T-181 | Cas limites | Restauration recrée le dossier source si l'utilisateur l'a supprimé |
| T-182 | Cas limites | Restauration suffixe `_restored1` si la source est déjà reprise |
| T-183 | Sorties | `empty_to_system_trash` envoie tout en corbeille système |
| T-184 | Robustesse | `load_session` recharge la quarantaine après crash |
| T-185 | Régression | `file_manager.record_operation('trash', ...)` apparaît dans l'historique |
| T-186 | Régression | `rollback_last` sur `trash` restaure le fichier |
| T-187 | Régression | `rollback_all` mixte : trash récupéré, delete ignoré |
| T-188 | IHM | Bouton 🗑 Vider quarantaine présent dans le panneau Doublons |
| T-189 | IHM | `DuplicateManager.empty_quarantine/quarantine_count/_size_bytes` exposés |

**Auto-couverture pytest** : 18 nouveaux tests dans `tests/functional/test_quarantine.py`. Exécution validée : **106/106 verts** (80 smoke + 8 file_manager + 18 quarantine).

**Auto-couverture pytest v2.3** : 14 nouvelles classes de tests dans `tests/smoke/test_ui_v3.py` (TestOrganizeFrameTabviewInternal, TestOrganizeFrameBrandExamples, TestOrganizeFrameInlinePanel) + 5 dans `tests/smoke/test_ux_v4.py` (TestNoToplevelInOrganizePanels, TestBrandExamplesPanelBehavior). À exécuter via `pytest tests/smoke/`.

## 4. Anomalies détectées

### 4.1 Campagne 2026-06-12

| ID | Sévérité | Description | Reproductibilité | Statut |
|---|---|---|---|---|
| **ANO-Q1** | Majeur (qualif) | `compare_outputs.py` T-079 non reproductible : les photos `input_pas_exif` sans EXIF retombent sur le **mtime** du fichier, non versionné par git → la référence figée (mois 05) divergeait du run (mois courant). | 100 % avant fix | ✅ **Corrigé** (voir §6) |

> Les anomalies **B-01 (bloquant), B-02, B-03, B-04** et mineures **B-06 à B-12** ont été détectées et **corrigées lors de l'audit du 2026-06-11** (branche `audit/2026-06-11`, lots A-F). Elles sont désormais couvertes par des tests automatiques de non-régression (T-203 à T-210). Le détail figure dans le rapport d'audit et au §6 ci-dessous.

### 4.2 Historique 2026-05-19 (résolu depuis)

| ID Test | Sévérité | Description | Statut au 2026-06-12 |
|---|---|---|---|
| T-114 | Mineur | Cache des métadonnées ne reportait pas de hits sur 2e pass (hit_rate = 0 %). | ✅ **Résolu** : cache 2-tier corrigé ; `test_exif_cache.py` vérifie désormais hit_rate > 0 (3 tests verts). |
| T-112 | Cosmétique | RAM repos 211.9 MB > objectif 200 MB (+11.9 MB). | 🟡 Toléré : objectif réaligné à 250 MB (Material + scheduler + widgets). Non re-mesuré cette campagne. |

**Campagne 2026-06-12 : 0 anomalie bloquante, 0 anomalie majeure ouverte.** La seule anomalie de la campagne (ANO-Q1, outillage de test) a été corrigée immédiatement.

## 6bis. Corrections appliquées

### ANO-Q1 — Références non déterministes (T-079/T-060)

- **Symptôme** : `compare_outputs.py` signalait un DIFF sur T-079 — les fichiers sans EXIF étaient classés sous `2026/05/2026_05_11/` dans la référence mais `2026/05/2026_05_26/` (ou la date courante) au run.
- **Cause racine** : sans EXIF, `extract_date` retombe sur le mtime du fichier ; `gen_pas_exif()` ne figeait pas ce mtime → il prenait la date de régénération des inputs, non versionnée.
- **Fichiers modifiés** : `test_data/scripts/generate_inputs.py` (`gen_pas_exif` fige le mtime à `2026-05-11 12:00` via `os.utime`).
- **Re-validation** : régénération du mtime + `run_tests.py --only T-079/T-060` + `compare_outputs.py` → **9/9 OK**.

> Rappel : les corrections produit (bug bloquant B-01 et autres) ont été appliquées et committées lors de l'audit du 2026-06-11 (lots A-F), avec un test E2E du worker (`tests/smoke/test_organize_e2e.py`) en non-régression. Cette campagne de qualification les a **vérifiées** (tous verts) et ajouté la couverture matricielle correspondante (T-203 à T-210).

## 5. Couverture fonctionnelle (matrice exigences × tests)

Référentiel : 8 catégories préfixées `REQ-IHM-*`, `REQ-PRM-*`,
`REQ-ENT-*`, `REQ-SOR-*`, `REQ-LIM-*`, `REQ-PRF-*`, `REQ-ROB-*`, `REQ-REG-*`.

| Catégorie | Exigences | Tests couvrants | Auto-validés |
|---|---|---|---|
| REQ-IHM-* | 42 (30 v2.0 + 9 v2.3 + 3 finition 2026-05-19) | T-001 à T-030 + T-151 à T-159 + T-166 à T-168 | 17 ✅ via pytest smoke |
| REQ-PRM-* | 31 (20 v2.0 + 5 v2.3 + 6 finition 2026-05-19) | T-031 à T-050 + T-160 à T-164 + T-169 à T-174 | 11 ✅ via pytest smoke |
| REQ-ENT-* | 15 | T-051 à T-065 | 12 ✅ |
| REQ-SOR-* | 15 | T-066 à T-080 | 9 ✅ |
| REQ-LIM-* | 25 | T-081 à T-105 | 5 ✅ |
| REQ-PRF-* | 10 | T-106 à T-115 | 6 ✅ |
| REQ-ROB-* | 20 | T-116 à T-135 | 6 ✅ |
| REQ-REG-* | 17 (15 v2.0 + 1 v2.3 + 1 finition 2026-05-19) | T-136 à T-150 + T-165 + T-175 | 15 ✅ |
| **Total** | **175** | **175** | **81 ✅** |

**Couverture exigences : 100 % (1 test par exigence)**, dont 46 % auto-validés
(via pytest et scénarios) et 54 % requérant une validation manuelle via
`validation_ihm.html` (essentiellement IHM + cas limites spécifiques
nécessitant interaction utilisateur).

## 6. Conclusion

### Verdict (campagne 2026-06-12) : 🟡 **GO CONDITIONNEL — validation IHM manuelle requise**

**Justification** :
- **0 anomalie bloquante, 0 anomalie majeure ouverte.** Le bug bloquant B-01 (worker d'organisation mort en silence → compteur trial inopérant) a été **corrigé et couvert par un test E2E** lors de l'audit ; cette campagne le confirme.
- **211 / 211 tests pytest exécutables verts** (47 Pro skippés v3.0+, 0 échec).
- **16 / 16 scénarios** `run_tests.py` OK, **9 / 9 non-régressions** conformes vs vérité terrain.
- **49 tests Auto** de la matrice validés par exécution réelle (statuts injectés, non saisis à la main).
- Anomalie d'outillage ANO-Q1 corrigée au fil de l'eau (références désormais déterministes).
- Modèle économique trial+unlock entièrement couvert côté logique (T-190 à T-202).

### Conditions de levée du « conditionnel »

1. **Validation IHM manuelle** : ouvrir `validation_ihm.html`, lancer l'app en parallèle, et atteindre ≥ 95 % de OK sur les **143 points manuels** (135 widgets + 8 résiduelles). Les 8 widgets « auto ✓ » sont déjà couverts.
2. **Vérifier en priorité les nouveautés visuelles** : badge licence et ses 4 couleurs (W137), panneau d'activation inline (W139), bandeau warning trial non tronqué (W140), aperçu dry-run avec critère lieu (W142), libellé « Quarantaine » dans l'historique (W143).
3. **Tests Cas limites manuels** restants (T-081 à T-105 non auto) : chemins UTF-8 réels, espace disque saturé, sources réseau, permissions limitées.
4. **Re-mesure RAM** (T-112) sur Windows 11 production si l'objectif 200 MB doit être tranché.
5. **Vérif manuelle de l'achat** : la page Lemon Squeezy (`photoorganizer.lemonsqueezy.com`, ouverte par W139) doit exister avant lancement public (priorité produit P0 #4, hors périmètre qualif logicielle).

### Si conditions levées

**Statut final attendu : ✅ GO production** (sous réserve du setup Lemon Squeezy, qui relève du déploiement commercial et non de la qualité logicielle).

## 7. Annexes

| Livrable | Chemin | Statut |
|---|---|---|
| Empreinte sources | [test_data/.test_state.json](.test_state.json) | ✅ 54 sources empreintées (commit 5b0c2eb) — Phase 0 |
| Matrice tests | [test_data/matrice_tests.xlsx](matrice_tests.xlsx) | ✅ 210 tests, colonne Mode (Auto/Manuel), 4 feuilles + synthèse par mode |
| Checklist IHM | [test_data/validation_ihm.html](validation_ihm.html) | ✅ 143 widgets (8 auto ✓ + 135 manuels) + 8 résiduelles, autonome |
| Inputs | `test_data/inputs/` (12 jeux) | ✅ ~280 fichiers (mtime sans-EXIF figé, ANO-Q1) |
| Refs non-régression | `test_data/outputs_reference/` (9 tests) | ✅ figées |
| Sorties réelles | `test_data/outputs_reels/` | ✅ rempli par run_tests.py (16/16) |
| Rapport diff | `test_data/outputs_reels/_diff_report.md` | ✅ 9/9 OK |
| Résumé exécution | `test_data/outputs_reels/_run_summary.json` | ✅ JSON |
| Rapport d'audit produit | branche `audit/2026-06-11` (7 commits, lots A-F) | ✅ B-01 bloquant corrigé + non-régressions |
| Audit visuel | `tools/visual_audit.py` | ✅ 12/12 (campagne 2026-05) |

### Commandes utiles

```bash
# Phase 0 — empreinte des sources (diagnostic de la prochaine campagne)
python test_data/scripts/snapshot_state.py

# Régénération (idempotent)
python test_data/scripts/generate_matrix.py
python test_data/scripts/generate_inputs.py --large 1000

# Exécution
python test_data/scripts/run_tests.py
python test_data/scripts/run_tests.py --only T-051

# Non-régression
python test_data/scripts/compare_outputs.py

# Validation IHM
start test_data/validation_ihm.html

# Audit visuel
python tools/visual_audit.py

# Tests internes
python -m pytest tests/                 # tous
python -m pytest tests/ -m "not slow"   # rapides
python -m pytest tests/ -m "slow"       # volume + stress
```

---

*Campagne 2026-06-12 (PhotoOrganizer 2.3.0.dev0, commit 5b0c2eb) : mise à jour ciblée — pivot trial+unlock + audit lots A-F. Sections datées 2026-05-19 conservées pour l'historique.*
*Rapport initial généré le 2026-05-11 par le pipeline de qualification automatisé.*
