# PROMPT — Roadmap fonctionnelle du panneau « Organisation »

> À fournir tel quel à un développeur (ou à un agent IA type Claude Code) pour
> piloter les évolutions du panneau Organisation de PhotoOrganizer. Le prompt
> couvre l'existant **et** les évolutions à valeur ajoutée à implémenter.

---

## 1. Contexte projet

Tu travailles sur **PhotoOrganizer v2.0.0**, application Windows desktop écrite en
**Python 3.11 + CustomTkinter 5.2**. L'application organise des photos et
vidéos dans une arborescence cible selon des critères métadata (date,
appareil, GPS — désactivé). Le code suit les patrons :
- Threading via `threading.Thread(daemon=True)` + dispatch UI `self.after(0, …)`
- Dataclasses pour les options (`OrganizationOptions`, `OrganizationResult`)
- Logging via `logger = logging.getLogger(__name__)` par module
- FileManager partagé entre frames (Organize, Duplicates, History) → toutes les
  opérations sont historisées et rollbackables depuis l'onglet Historique.
- Build PyInstaller via `build.py` (modes `--debug`, `--light`, release)
- Tests `pytest` dans `tests/{smoke,functional,volume,perf,stress}/`

Les fichiers clés du panneau Organisation :
- IHM : `src/ui/frames/organize_frame.py` (`OrganizeFrame`)
- Core : `src/core/operations/organizer.py` (`SmartOrganizer`, `OrganizationOptions`)
- File ops : `src/core/operations/file_manager.py` (`FileManager`)
- Métadonnées : `src/core/metadata/{exif_extractor, date_extractor, camera_detector, gps_processor}.py`
- Cache : `src/utils/cache.py` (singleton `MetadataCache` avec TTL)

Style/UI :
- Factories `_make_checkbox`/`_make_radio` au début du fichier `organize_frame.py`
- Palette grisée (`#dcdcdc / #e8e8e8 / #f0f0f0`) au lieu du blanc CTk par défaut
- Séparateurs visuels (`Frame height=2 fg_color=("gray70","gray30")`)
- Émojis dans les titres pour repère visuel (📁 📂 🗂️ ⚙️ 🧩 📅 📷)
- Tout le contenu est dans un `CTkScrollableFrame` (la fenêtre peut être réduite)
- Raccourci clavier global Ctrl+1 → cet onglet

---

## 2. Inventaire des fonctionnalités déjà implémentées (62)

### 📁 Sélection des dossiers
1. Champ Source + bouton parcourir (`📂 askdirectory`)
2. Champ Destination + bouton parcourir
3. Restauration auto des derniers chemins utilisés (`AppConfig.recent_sources/destinations`)

### 🗂️ Critères d'organisation
4. Case « Par date de prise de vue »
5. OptionMenu format date : `year/month/day`, `year/month`, `year`, `year_month_day`, `year_month`
6. Case « Par appareil photo »
7. Sanitization des noms (caractères Windows interdits → `_`, troncature 80 chars)
8. Fallbacks `Sans date` / `Appareil inconnu`
9. ⚠️ GPS retiré (mais `gps_processor` reste côté core, prêt à réintégrer)

### 🧩 Organisation avancée
10. CTkSwitch « Organisation multicouche » (combine date + appareil)
11. Sous-panneau « Ordre des critères » réordonnable via boutons ▲▼
12. Critères inactifs grisés avec mention *(désactivé)*
13. `criteria_order` exporté vers `OrganizationOptions` et appliqué par `SmartOrganizer`

### ⚙️ Options de traitement
14. Radio Copier / Déplacer
15. Case « Parcourir les sous-dossiers »
16. Cases types fichiers : Images / RAW / Vidéos
17. Préservation des métadonnées (`shutil.copy2`)
18. Auto-rename collisions (suffixe `_1`, `_2`…)

### 📊 Compteur de fichiers source
19. Label dynamique « 📂 ⟨source⟩ — N fichier(s) prêt(s) »
20. Update auto sur changement source / recursive / include_*
21. Comptage en thread daemon (UI ne gèle pas)
22. États : *Aucun dossier / Introuvable / Comptage en cours / N fichier(s)*

### 📈 Progression
23. Barre de progression visible dès l'init à 0 %
24. Label de progression dynamique
25. Diffusion vers status bar globale

### 🎯 Boutons
26. 📊 Analyser (stats EXIF + distribution par année / appareil)
27. 🚀 Organiser (vert) — confirmation modale
28. ❌ Annuler (rouge, propage `SmartOrganizer.cancel()`)
29. Boutons disabled pendant opération (try/finally)

### 🧠 Logique
30. Worker thread daemon pour analyse + organisation
31. `progress_callback(current, total, message)` chaîné UI
32. Création auto du répertoire de destination
33. Session FileManager auto-démarrée → opérations historisées
34. Rollback enrichi `{success, failed, skipped, total}`
35. Cleanup dossiers vides après rollback

### 🎨 Ergonomie
36. Frame scrollable, minsize 640×420
37. Factories `_make_checkbox` / `_make_radio` (bordure 2px, font 13)
38. Thème grisé (palette explicite light/dark)
39. Raccourci Ctrl+1 (navigation onglet)
40. Sauvegarde dossiers récents à la fermeture

### 🔍 Robustesse
41. Validation pré-organisation (source/dest non vides + existe)
42. Try/except spécifiques (`OSError`, `ValueError`) avec `logger.warning`
43. Affichage résultats : Total / Traités / Ignorés / Erreurs

(Numéros 44-62 = sous-options et comportements transverses détaillés dans
`audit/01_inventaire.md`.)

---

## 3. Roadmap des évolutions à valeur ajoutée

Classement par **ratio valeur/effort**. Chaque lot peut être implémenté
indépendamment sans casser les autres.

### 🟢 Lot Q — Quick wins (faible effort, forte valeur)

#### Q1 — Drag-and-drop des dossiers
Permettre de déposer un dossier depuis l'explorateur Windows directement
dans les champs Source/Destination. Utiliser `tkinterdnd2` (`pip install
tkinterdnd2`) ou l'API Win32 native. Compat avec PyInstaller : ajouter
`tkinterdnd2` aux `HIDDEN_IMPORTS` de `build.py`.

#### Q2 — Aperçu de l'arborescence (dry-run preview)
Avant clic sur « Organiser », afficher dans une **modale** l'arborescence
prévue pour les 100 premiers fichiers. Composant : `CTkTextbox` ou
arborescence ASCII type `└── 2026/`. Exécuter `_apply_*_organization` sans
faire de copy/move réel.

#### Q3 — Profils nommés (presets)
Le code dans `utils/config.py` expose déjà `save_preset(name, options)` /
`load_preset(name)` / `list_presets()` / `delete_preset(name)` mais aucune
UI ne les expose. Ajouter dans le panneau :
- OptionMenu « Profil » avec liste des presets + ⊕ et 🗑
- Bouton 💾 « Sauvegarder ce profil »
- Au chargement, applique le preset à toutes les `*Var`

#### Q4 — Templates de renommage de fichiers
Ajouter une option `rename_template: Optional[str]` à `OrganizationOptions`.
Exemple : `"{date:%Y%m%d}_{camera}_{counter:03d}{ext}"`. Évaluation par
`str.format` avec les vars exposées (`date`, `camera`, `counter`,
`original_name`, `ext`). UI : champ texte avec aperçu live.

#### Q5 — Notification système Windows à la fin
`from win10toast import ToastNotifier` (ou stdlib `winsound` + messagebox).
Afficher *« Organisation terminée : 1 234 fichiers traités »*. Optionnel via
case à cocher *« Notifier à la fin »* dans Paramètres.

#### Q6 — Bouton « Ouvrir le dossier de destination » après organisation
Dans la modale de résultats, bouton *📂 Ouvrir* qui appelle
`os.startfile(dest)` sous Windows / `subprocess.run(['xdg-open', dest])`
ailleurs.

---

### 🟡 Lot R — Refinements (effort moyen, forte valeur)

#### R1 — Filtres avancés (collapsible panel)
Sous une section dépliable « 🔬 Filtres » ajouter :
- **Date min / max** (`CTkEntry` au format `YYYY-MM-DD`, ou date picker via
  `tkcalendar`)
- **Taille min / max** (entry avec unités KB/MB/GB, parsing via la fonction
  `_parse_size` déjà présente dans `duplicates_frame.py`)
- **Rating EXIF min** (1-5 étoiles, lu via `XMP:Rating` / `EXIF:Rating`)
- **Mots-clés EXIF** (champ texte, comparaison par `in` sur EXIF Keywords)

Côté core, étendre `OrganizationOptions` :
```python
date_min: Optional[datetime] = None
date_max: Optional[datetime] = None
size_min_bytes: int = 0
size_max_bytes: Optional[int] = None
rating_min: int = 0
keywords_filter: List[str] = field(default_factory=list)
```

Et appliquer les filtres dans `_get_files()` ou dans `_process_file`
(skip + incrément `skipped` + log).

#### R2 — Skip si fichier identique déjà à destination
Avant copy/move, calculer le hash partiel du source et de la cible existante.
Si identique → skip (log « déjà présent, identique »). Si différent → comportement
auto_rename habituel. Réutiliser `core/operations/duplicate_finder.QuickHasher`.

Option UI : case « Ignorer si déjà présent et identique ».

#### R3 — Pairs RAW+JPEG (les garder ensemble)
Si un fichier `IMG_001.CR2` ET `IMG_001.JPG` existent dans le source, les
ranger dans le même dossier de destination même si les filtres types
fichiers diffèrent. Implémentation : pré-pass groupant par stem, puis
forçage du déplacement de tous les membres du groupe ensemble.

Option UI : case « Garder les paires RAW+JPEG ensemble ».

#### R4 — Sources multiples
Remplacer le champ texte unique par un `CTkTextbox` multi-ligne ou un
listbox avec ⊕/🗑. Stocker dans `source_var` une liste séparée par `;`
(ou bouger vers une `tk.Variable` multi-valeur via JSON serialize).

`SmartOrganizer.organize` accepte déjà une `List[str]` → fusionner en amont
les `list_files` de chaque source.

#### R5 — Nettoyage post-organisation
Après un MOVE complet réussi, proposer (case à cocher) :
*« Supprimer les sous-dossiers vides du source à la fin »*.
Réutiliser `_cleanup_empty_dir` du `FileManager`.

#### R6 — Validation espace disque
Avant exécution, comparer `sum(filesizes)` et `shutil.disk_usage(dest).free`.
Si insuffisant → modale *« 12 GB nécessaires, 4 GB disponibles. Continuer ? »*.

#### R7 — Index export
Après organisation, générer optionnellement un fichier `index.csv` ou
`index.json` listant : `original_path,destination_path,date,camera,size,hash`.
Réutiliser `reports/duplicate_reporter.py` pour la structure.

---

### 🟠 Lot S — Smart features (effort élevé, très forte valeur)

#### S1 — Détection de bursts (rafales)
Grouper les photos prises à moins de N secondes d'intervalle (param config).
Créer un sous-dossier `Burst/` à l'intérieur du dossier date.

Algorithme :
- Trier par `DateTimeOriginal`
- Glisser une fenêtre : si `delta < threshold` → même groupe, sinon nouveau groupe
- Si `len(group) >= 3` → c'est une rafale, sinon photo unique

#### S2 — Détection HDR/bracketing
Détecter par `ExposureBiasValue` : 3+ photos consécutives avec EV différent
(ex: -2, 0, +2) → groupe HDR. Sous-dossier `HDR/` ou suffixe `_HDR1`,
`_HDR2`…

#### S3 — Vignettes parallèles
Pendant l'organisation, en thread bonus, générer une vignette 256x256 PNG
dans `<dest>/.thumbnails/<hash>.png`. Utiliser `PIL.Image.thumbnail`.
Optionnel via case « Générer les vignettes ».

#### S4 — Watch mode (surveillance temps réel)
`watchdog` library (`pip install watchdog`). Quand activé, surveille
`source` et organise automatiquement chaque nouveau fichier qui apparaît.
UI : toggle « 👁 Surveiller ce dossier » qui démarre/arrête un Observer.

#### S5 — Mode incrémental
Hash partiel des fichiers déjà à destination → skip systématique des
fichiers déjà organisés. Persiste un cache `<dest>/.photoorganizer_index.json`
indexé par hash. Bénéfice : ré-exécutions rapides sur le même couple
source/destination.

---

### 🔴 Lot E — Évolutions ambitieuses (effort très élevé)

#### E1 — Drag-and-drop pour réordonner les critères
Remplacer les boutons ▲▼ par un drag des lignes dans le `criteria_rows_container`.
Implémentation : `bind('<B1-Motion>', ...)` + animation de glissement.

#### E2 — Cloud destinations
Support Google Drive (`pydrive2`), Dropbox (SDK officiel), OneDrive
(Microsoft Graph). UI : OptionMenu *« Type de destination »*. Sélection
d'un compte authentifié → liste des dossiers cloud disponibles.

#### E3 — Conversion HEIC → JPEG optionnelle
Case « Convertir HEIC en JPEG (qualité 90 %) ». Utiliser `pillow_heif`
déjà installé. Garde le HEIC original ou le supprime selon option.

#### E4 — Watermarking
Ajouter un texte/image en bas-droite des photos copiées. UI :
champ texte + couleur + opacité.

#### E5 — Programmation
*« Organiser tous les jours à 23h »*. Utiliser `schedule` library
(`pip install schedule`) + un thread persistent. Persiste les jobs dans
`AppConfig`.

#### E6 — Tableau de bord visuel
Remplacer le `messagebox` de fin par une fenêtre avec **histogramme par
mois** (matplotlib? mais lourd. Alternative : dessiner manuellement sur un
`CTkCanvas`). Stats par appareil, par taille, par année.

#### E7 — Tags personnalisés
Permettre de tagger des fichiers avant organisation (sélection multiple →
clic droit → ajouter tag). Le tag devient un critère de tri.

---

## 4. Contraintes techniques

À respecter impérativement :

- **Python 3.11+**, encodage UTF-8, fins de ligne LF
- **Threading** : worker daemon + `self.after(0, …)` pour tout dispatch UI.
  **Jamais** d'appel direct à un widget depuis un thread non-UI.
- **Logging** : `logger = logging.getLogger(__name__)` au module-scope, pas
  de `print()` dans le code livré.
- **Dataclasses** : étendre `OrganizationOptions` pour toute nouvelle option.
  Garder rétro-compat via `__post_init__` (cf. exemple existant pour
  `date_levels`).
- **Style UI** : utiliser les factories `_make_checkbox` / `_make_radio`.
  Pour les nouveaux switchs/sliders, factoriser pareil. Couleurs explicites
  `("light", "dark")`.
- **Tests** : ajouter au moins 1 test fonctionnel par feature dans
  `tests/functional/`. Lancer `pytest -m "not slow"` après chaque commit.
- **Build** : si la feature nécessite un nouveau module, l'ajouter à
  `HIDDEN_IMPORTS` de `build.py`. Vérifier le nouveau poids EXE (cible :
  rester sous 50 MB).
- **Compat PyInstaller --onefile** : pas de `__file__` brut, utiliser
  `sys._MEIPASS` quand on accède à des assets bundlés (cf. `_install_icon`
  dans `ui/app.py`).
- **Accessibilité** : tous les nouveaux widgets doivent être atteignables
  via Tab. Couleurs avec contraste suffisant.
- **i18n** : libellés en français cohérents avec le reste (pas de mélange
  langue, pas de jargon technique exposé à l'utilisateur).

## 5. Critères de réussite (definition of done)

Pour chaque lot ou feature, valider :

- [ ] `pytest -m "not slow"` : 100 % passants (régression nulle)
- [ ] Nouveau test fonctionnel ajouté pour la feature
- [ ] Code compile (`python -m py_compile`)
- [ ] Ruff sans nouvelle erreur (`ruff check src/ --select=E,F,W,B`)
- [ ] Bandit sans nouveau High (`bandit -r src/ -ll`)
- [ ] EXE rebuildé sous `python build.py` — démarre sans `ModuleNotFoundError`
- [ ] Smoke-test : ouverture du panneau, scroll, multilayer ON/OFF, reorder
- [ ] Documentation : entrée dans `audit/03_implementations.md` (ce que la
  feature fait + risques connus)
- [ ] Logging cohérent + au moins un message INFO ou DEBUG par opération

## 6. Process de livraison recommandé

1. **Pick** un lot ou une feature dans la roadmap
2. Branche `feature/<nom-court>` (ou commit direct sur `main` si fix mineur)
3. Implémenter la feature en respectant les contraintes section 4
4. Ajouter le test fonctionnel
5. Lancer la suite complète `make test` (ou `pytest -m "not slow"`)
6. Lancer `make build-debug` et tester le binaire localement
7. Commit atomique avec message conventionnel :
   - `feat(organize): <description>`
   - `fix(organize): <description>`
   - `refactor(organize): <description>`
8. Push sur `main` (ou PR si workflow équipe)
9. Mettre à jour `audit/PROMPT_ORGANIZE_ROADMAP.md` (ce fichier) en
   marquant la feature comme livrée :
   ```
   #### Q1 — Drag-and-drop des dossiers ✅ (livré ⟨commit⟩ ⟨date⟩)
   ```

## 7. Démarrage

Quand tu prends un ticket dans cette roadmap :

> **« Implémente la feature ⟨ID⟩ — ⟨titre⟩ du panneau Organisation de
> PhotoOrganizer en suivant `audit/PROMPT_ORGANIZE_ROADMAP.md`. Respecte les
> contraintes section 4 et les critères de réussite section 5. Ajoute le
> test fonctionnel correspondant et marque la feature comme livrée dans le
> document à la fin. »**

Ou pour bootstrap un agent :

> **« Lis `audit/PROMPT_ORGANIZE_ROADMAP.md`, choisis la feature avec le
> meilleur ratio valeur/effort encore non livrée, et implémente-la
> entièrement (code + tests + doc). Ne demande aucune confirmation
> intermédiaire. »**

---

*Document maintenu sur `main`. Dernière mise à jour : session d'audit
2026-05-07. Si tu livres une feature, mets à jour cette section avec la
date et le commit hash.*
