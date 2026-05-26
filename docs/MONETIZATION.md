# PhotoOrganizer — Stratégie de monétisation

> Phase 5 de l'audit méta-projet. Évaluation honnête des 8 voies, recommandation d'une voie principale + une voie fallback, chiffrage et plan d'action.
> Date : 2026-05-19.

---

## 1. Verdict en 30 secondes

| | Verdict |
|---|---|
| **Voie principale** | **Freemium** : core Apache-2.0 actuel + édition Pro propriétaire (batch CLI, scheduler, plugins) à **19 €** licence personnelle / **49 €** licence "studio". |
| **Voie complémentaire** | **Lead magnet / portfolio** : le projet est un meilleur démonstrateur de compétences (Python desktop, packaging, tests, CI) qu'un produit à fort revenu. **Cumuler** avec le freemium plutôt que choisir. |
| **Revenu réaliste 12 mois** | **200 € – 2 000 €** Pro (selon traction Product Hunt + LinkedIn) **+ 50 € – 300 €** Ko-fi dons + **valeur indirecte 5 k€ – 30 k€** si conversion en missions freelance. |
| **Effort estimé pour démarrer** | **5-8 jours-homme** pour livrer la V1 Pro (batch CLI + watch-folder) et la page de vente. |
| **Risque principal** | Niche modeste (photo amateur Windows) + concurrence gratuite (Lightroom, ACDSee, FastStone). Marketing > produit pour générer du revenu. |

**Lis honnêtement** : ce projet n'a pas le potentiel d'un SaaS à 6 chiffres. Mais il peut rapporter **un peu d'argent + beaucoup d'opportunités** si bien positionné.

---

## 2. Évaluation des 8 voies

### 2.1 Synthèse comparative

| # | Voie | Pertinence | Effort 12 mois | Revenu réaliste 12 mois | Risque |
|---:|---|:---:|---|---|---|
| 1 | Open-source + dons (Ko-fi/GH Sponsors) | ⭐⭐⭐ | 0-1 j | 50–500 € | Faible (déjà en place) |
| 2 | **Freemium / dual-license** | ⭐⭐⭐⭐⭐ | 5-8 j | 200–2 000 € | Modéré |
| 3 | Vente directe one-shot (sans freemium) | ⭐⭐ | 3 j | 100–800 € | Élevé (concurrence gratuit) |
| 4 | SaaS / abonnement | ❌ | 30+ j | imprévisible | Très élevé — inadapté à app desktop locale |
| 5 | **Lead magnet / portfolio** | ⭐⭐⭐⭐⭐ | 2-3 j | 0 € direct, **5–30 k€ indirect** (missions) | Faible |
| 6 | Formation / contenu payant | ⭐⭐ | 10-15 j | 200–1 500 € | Modéré (dépend audience LinkedIn) |
| 7 | Bounties / sponsoring entreprise | ⭐ | 1-2 j | 0–500 € | Très élevé (projet pas assez utilisé en prod entreprise) |
| 8 | Marketplace plugins | ❌ | n/a | n/a | PhotoOrganizer n'a pas d'écosystème |

### 2.2 Détail de chaque voie

#### Voie 1 — Open-source + dons ⭐⭐⭐ (déjà partiellement actif)

- **Mécanique** : Ko-fi (déjà configuré : <https://ko-fi.com/kiriiaq>), GitHub Sponsors (déjà dans `.github/FUNDING.yml`), Liberapay (optionnel).
- **Pré-requis** : audience qui découvre et utilise le projet. **Aujourd'hui, la traction GitHub est probablement faible** (à vérifier : nombre de stars, downloads des releases v1.0.0).
- **Conversion typique** : ~0,5 % à 2 % des utilisateurs actifs donnent. Pour 100 utilisateurs/mois → 1-2 dons à 3-10 € → 5-20 €/mois.
- **Revenu 12 mois** : **50–500 €** si la traction reste artisanale, **500-3 000 €** si un coup médiatique (HN front page, LinkedIn viral) attire 10 000+ visiteurs.
- **Effort** : zéro additionnel — c'est en place. Effort = communication régulière.
- **Risque** : minimal. Pas d'engagement de support, pas d'obligation.
- **Recommandation** : **garder activé en complément**. Ne pas en faire la voie principale.

#### Voie 2 — Freemium / dual-license ⭐⭐⭐⭐⭐ (CHOIX RETENU)

- **Mécanique** :
  - **Core** : Apache-2.0 (déjà actuel), GUI complète gratuite.
  - **Pro** : modules propriétaires distribués séparément, licence "PhotoOrganizer Pro EULA" basée sur clé de licence (offline activation simple, pas de serveur).
- **Modules Pro V1 (réalistes pour 5-8 j-h)** :
  - `cli/batch_organize.py` : CLI complet d'organisation (équivalent GUI mais scriptable, idéal pour cron / Task Scheduler).
  - `scheduler/watch_folder.py` : surveille un dossier et organise automatiquement les nouveaux fichiers (`watchdog` package).
- **Modules Pro V2 (futur, 10-15 j-h)** :
  - `plugins/api.py` : hooks Python pour règles de renommage / filtres / post-actions personnalisés.
  - `reports/advanced.py` : rapports HTML/PDF avec graphiques (`matplotlib` lazy import).
- **Pricing recommandé** :

  | Édition | Prix | Cible |
  |---|---|---|
  | Personnelle | **19 €** one-shot, 1 PC, mises à jour mineures gratuites 1 an | Particulier, photographe amateur |
  | Studio | **49 €** one-shot, 3 PC, mises à jour mineures gratuites 2 ans | Petit studio, photographe pro freelance |
  | Source code | Non vendu — Pro reste fermé. |

  Pricing **délibérément modeste** : la concurrence gratuite (FastStone, IrfanView) est rude. Cible : "celui qui veut vraiment automatiser et qui a déjà essayé le core gratuit".

- **Plateforme** : **Lemon Squeezy** (recommandé, gère TVA EU + factures auto), alternative **Gumroad** (plus simple mais TVA à gérer soi-même).
- **Activation** :
  - Génération clé de licence côté Lemon Squeezy.
  - Validation locale offline (signature RSA d'un payload contenant email + édition + date d'expiration). Pas de serveur d'auth = pas de coût récurrent.
  - Implémenter dans `src/photoorganizer_pro/license/validator.py` (~150 LOC).
- **Effort détaillé** :

  | Tâche | Effort |
  |---|---|
  | Implémenter `cli/batch_organize.py` (réutilise `core/operations/organizer.py`) | 1-2 j |
  | Implémenter `scheduler/watch_folder.py` avec `watchdog` | 1 j |
  | Système de licence offline (RSA signature + UI activation) | 1 j |
  | EULA propriétaire (LICENSE-PRO) + page de vente | 0,5 j |
  | Setup Lemon Squeezy + webhook → email de la clé | 0,5 j |
  | Build dual : `PhotoOrganizer.exe` (core, gratuit) + `PhotoOrganizerPro.exe` (avec modules Pro) | 1 j |
  | Tests, doc, page web simple | 1-2 j |

  **Total : 5-8 j-h** pour la V1 Pro.

- **Revenu réaliste 12 mois** : 10-100 ventes selon traction → **200-2 000 €**. À 19 €/licence, il faut 11 ventes/mois pour 200 €. Réalisable avec un bon lancement Product Hunt + un post LinkedIn relayé.
- **Risque** :
  - **Maintenance de deux binaires** (overhead CI). Mitigé par `build.py --pro`.
  - **Support utilisateur payant** : engagement implicite. Prévoir un canal email dédié et un SLA "best effort".
  - **Piratage** : licence offline = crackable. Acceptable pour ce niveau de prix (effort de crack > coût d'achat).
- **Recommandation** : **voie principale**. Commencer par la V1 Pro (batch + watch-folder), évaluer les premières ventes avant d'investir dans V2.

#### Voie 3 — Vente directe one-shot SANS freemium ⭐⭐

- **Mécanique** : tout est payant, plus de core gratuit.
- **Verdict** : **mauvaise idée pour ce projet**. Le core est déjà open-source publiquement (v1.0.0 + v2.1.0 sur GitHub). Faire marche arrière serait perçu négativement par la communauté et bloquerait l'adoption.
- **Recommandation** : ne pas faire. Garder le freemium.

#### Voie 4 — SaaS / abonnement ❌

- **Mécanique** : transformer en service web où l'utilisateur upload ses photos pour les organiser et télécharge le résultat.
- **Verdict** : **incompatible** avec la nature du produit. Les photos sont des fichiers volumineux (RAW = 30 MB, HEIC = 5 MB). Uploader 10 000 photos = 100+ GB. Coût hébergement + bande passante explosif. UX dégradée vs le local.
- **Effort de refonte** : 30+ j-h pour réécrire le core en backend FastAPI + frontend React + storage S3 + queue Celery.
- **Recommandation** : **ne pas faire**. Reste dans le local desktop.

#### Voie 5 — Lead magnet / portfolio ⭐⭐⭐⭐⭐ (CUMULER avec voie 2)

- **Mécanique** : le projet sert de **preuve de compétence** pour décrocher des missions freelance ou des opportunités d'embauche.
- **Compétences démontrées** (extraites de l'analyse Phase 1) :
  - **Python desktop** : CustomTkinter, threading, callbacks, drag-and-drop.
  - **Packaging Windows** : PyInstaller `--onefile`, gestion des hidden imports, optimisation taille EXE (audit documenté).
  - **Architecture en couches** : UI / core / utils strict, no-cross-import.
  - **Tests** : suite pytest 5 catégories, 170 tests, couverture 70 % modules métier, benchmarks `pytest-benchmark`.
  - **CI/CD** : GitHub Actions Windows (lint + tests + release auto sur tag).
  - **Audit & documentation** : `AUDIT.md`, `ARCHITECTURE.md`, `MONETIZATION.md`, `CLAUDE.md` — preuve de capacité à structurer un projet pro.
  - **Modélisation de données** : SQLite 2-tier cache, rollback historisé, hash multi-algo.
- **Effort** : 2-3 j pour produire les assets visuels (cf. [MEDIA.md](MEDIA.md)) + 3 posts LinkedIn structurés (Phase 7).
- **Revenu direct** : 0 €.
- **Revenu indirect (12 mois)** : **5 000 – 30 000 €** si 1-2 missions freelance déclenchées par la visibilité. À 400-600 €/jour TJM, une mission de 10 jours rapporte plus que 200 ventes Pro.
- **Risque** : faible. C'est une conversion d'effort en visibilité.
- **Recommandation** : **voie complémentaire de la voie 2**. Le projet rapporte peu en direct mais beaucoup en opportunités. Optimiser le README pour "se vendre" implicitement (badge auteur, lien LinkedIn, lien portfolio).

#### Voie 6 — Formation / contenu payant ⭐⭐

- **Mécanique** : ebook ou cours vidéo sur "Comment j'ai construit une app Windows portable en Python avec CustomTkinter et PyInstaller".
- **Pré-requis** : audience LinkedIn / Twitter / YouTube qui te suit déjà (inconnu, à vérifier). Sans audience, un ebook se vend 0 fois.
- **Effort** : 10-15 j pour écrire et publier un ebook de 60-100 pages sur Gumroad (~15 €).
- **Revenu réaliste** : 200-1 500 € sur 12 mois si l'audience existe. Sinon proche de 0.
- **Recommandation** : **différer**. Pertinent uniquement après avoir construit l'audience via voie 5 (lead magnet). Réévaluer dans 6-12 mois.

#### Voie 7 — Bounties / sponsoring entreprise ⭐

- **Mécanique** : Open Collective ou Tidelift, entreprises sponsorisent les libs qu'elles utilisent en prod.
- **Verdict** : **non applicable**. PhotoOrganizer est une application desktop end-user, pas une lib utilisée en pipeline entreprise.
- **Recommandation** : ne pas faire.

#### Voie 8 — Marketplace plugins ❌

- **Mécanique** : publier le projet comme plugin VSCode / Obsidian / Figma…
- **Verdict** : **non applicable**. PhotoOrganizer n'est pas un plugin d'un autre écosystème, c'est une app standalone.
- **Recommandation** : ne pas faire.

---

## 3. Plan d'action freemium V1 Pro (recommandation détaillée)

### 3.1 Périmètre V1 Pro

| Module | Fichier cible | Effort | Valeur perçue |
|---|---|---|---|
| Batch CLI organize | `src/photoorganizer_pro/cli/batch_organize.py` | 1-2 j | Élevée — "scriptable" |
| Watch-folder scheduler | `src/photoorganizer_pro/scheduler/watch_folder.py` | 1 j | Élevée — "automatique" |
| Système de licence offline | `src/photoorganizer_pro/license/validator.py` | 1 j | Invisible mais critique |
| EULA + page de vente | `LICENSE-PRO` + page web simple (GitHub Pages ou Lemon Squeezy storefront) | 0,5 j | Indispensable légal |
| Build dual `build.py --pro` | `build.py` enrichi avec flag `--pro` | 1 j | Pipeline complet |
| Doc + tests | `docs/PRO.md` + `tests/functional/test_pro_license.py` | 1-2 j | Confiance utilisateur |

**Total : 5-8 j-h.**

### 3.2 Architecture d'activation

```
Utilisateur achète sur Lemon Squeezy
       │
       ▼
Lemon Squeezy webhook → email avec clé (format : XXXX-XXXX-XXXX-XXXX-signature)
       │
       ▼
Utilisateur lance PhotoOrganizer Pro.exe → onglet "Licence"
       │
       ▼
Colle la clé → src/photoorganizer_pro/license/validator.py
       │
       ├── Décode payload base64 (email, édition, expiration)
       ├── Vérifie signature RSA avec clé publique embedée
       │   (clé privée garde par l'auteur, jamais distribuée)
       ├── Si valide : écrit license.dat dans %LOCALAPPDATA%\PhotoOrganizer\
       │
       ▼
Modules Pro activés (batch, watch-folder)
```

**Pas de serveur d'authentification = zéro coût récurrent.** Crackable, mais effort de crack > 19 €.

### 3.3 Pricing

| Édition | Prix HT | Inclus | Mises à jour |
|---|---|---|---|
| **Core (open-source)** | Gratuit | GUI complète, 4 onglets, 170 tests, Apache-2.0 | Gratuites à vie |
| **Pro Personnelle** | **19 €** | + Batch CLI + Watch-folder + Activation 1 PC | Mineures gratuites 1 an, majeures 50 % off |
| **Pro Studio** | **49 €** | + Activation 3 PC + email support prioritaire | Mineures gratuites 2 ans, majeures 50 % off |
| **Lifetime Pro** | **99 €** (lancement) | Pro Studio + toutes les majeures à vie | À vie |

**Prix volontairement bas** : se positionner comme "outil utile pas cher" vs "outil pro à 200 €". Volume > marge.

**Promotion de lancement** : "early bird" -30 % les 30 premiers jours (`PHOTORG30` code Lemon Squeezy) pour stimuler les premières ventes.

### 3.4 Plateforme : Lemon Squeezy

**Pourquoi Lemon Squeezy plutôt que Gumroad ou Paddle** :

| | Lemon Squeezy | Gumroad | Paddle | Stripe Payment Links |
|---|---|---|---|---|
| TVA EU gérée (Merchant of Record) | ✅ | ❌ | ✅ | ❌ |
| Facturation auto | ✅ | ✅ | ✅ | ⚠️ Stripe Tax payant |
| Webhooks (auto-envoi clé) | ✅ | ✅ | ✅ | ✅ |
| Frais | 5 % + 0,50 $ | 10 % | 5 % + 0,50 $ | 1,5 % + 0,25 $ |
| Setup | Très simple | Très simple | Complexe | Manuel |
| **Verdict pour PhotoOrganizer** | ✅ choix par défaut | OK fallback | Overkill | Trop technique |

### 3.5 Calendrier de lancement (proposition)

| Semaine | Tâche | Livrable |
|---|---|---|
| S+0 | Implémenter Pro V1 (modules + licence) | Code |
| S+1 | Build dual, tests, doc | Pipeline CI |
| S+2 | Page de vente Lemon Squeezy + assets visuels (cf. MEDIA.md) | Page en ligne |
| S+3 | Lancement soft : LinkedIn personnel + Twitter | 50-200 visiteurs |
| S+4 | Lancement hard : Product Hunt (mardi 9h PT recommandé) + Show HN | 500-5 000 visiteurs |
| S+5 → S+12 | Marketing organique : 1 post LinkedIn / 2 semaines + réponse aux issues GitHub | Construction audience |

---

## 4. Vérifications avant monétisation (juridique + IP)

### 4.1 Droits sur le code ⚠️ À CONFIRMER

- **Auteur unique** : Kiriiaq (Emmanuel Grolleau) selon `pyproject.toml` et `git log --pretty=%an | sort -u`. À vérifier qu'aucun contributeur externe n'a poussé du code sans cession explicite (la `CONTRIBUTING.md` créée en Phase 3 demande l'accord Apache-2.0 mais c'est pour le futur).
- **Clauses employeur** : si le développement a été fait pendant des heures de travail ou avec du matériel employeur, certaines juridictions (France notamment) attribuent les droits à l'employeur. **À auto-vérifier** :
  - Contrat de travail actuel inclut-il une clause de cession des "œuvres créées" ?
  - Le code a-t-il été commit depuis un poste/réseau employeur ?
  - Si oui, demander une autorisation écrite avant de monétiser.
- **Pseudonyme Kiriiaq** : la monétisation va exiger un nom légal pour les factures (auto-entreprise, EURL, etc. en France). Lemon Squeezy/Gumroad demandent un identifiant fiscal.

### 4.2 Licences des dépendances ✅ COMPATIBLES

| Dépendance | Licence | Compatible Pro propriétaire ? |
|---|---|---|
| customtkinter | CC0 (domaine public) | ✅ |
| Pillow | MIT-CMU | ✅ |
| exifread | BSD-3-Clause | ✅ |
| pillow-heif | BSD-3-Clause | ✅ (avec attribution) |
| requests | Apache-2.0 | ✅ |
| PyYAML | MIT | ✅ |
| darkdetect | BSD-3-Clause | ✅ |
| tkinterdnd2 | MIT | ✅ |
| plyer | MIT | ✅ |
| send2trash | BSD | ✅ |
| **ExifTool** (bundled) | **Perl Artistic OR GPL 1** | ⚠️ **À retirer** (cf. AUDIT_EXE F-01 : déjà prévu) |
| Python stdlib | PSF | ✅ |

**Action requise** : exécuter [AUDIT_EXE F-01](exe-optimization.md#f-01) (retrait du bundle ExifTool) **avant** de lancer la version Pro. Tant qu'ExifTool est bundlé, la GPL peut être invoquée (même si subprocess, c'est ambigu). Une fois retiré, plus aucun frein juridique.

### 4.3 Données et logos tiers

- **Logos** : aucun logo tiers utilisé visuellement (sauf badges shields.io du README, qui sont publics et libres).
- **Données** : aucune base de données tierce embarquée (le Geolocation.dat d'ExifTool sortira avec lui).
- **API tierce** : Nominatim (OpenStreetMap) — usage limité par leur [usage policy](https://operations.osmfoundation.org/policies/nominatim/) : max 1 req/sec, User-Agent identifiable (déjà conforme : `User-Agent: PhotoOrganizer/2.0`).

### 4.4 RGPD et données personnelles

- **Pas de collecte** : l'app est 100 % locale. Aucune télémétrie, aucun tracking.
- **Géocodage** : envoie `(lat, lon)` à Nominatim. **Désactivable** dans Paramètres (déjà le cas).
- **Photos utilisateur** : restent sur le PC de l'utilisateur. Jamais transmises.
- **Pas de DPO requis**, pas de mention CNIL.
- **Pour la version Pro** : le formulaire de licence collecte `email` (via Lemon Squeezy). Lemon Squeezy est responsable de traitement, conforme RGPD. **Action** : ajouter une page Privacy Policy minimale (1 page) avant le lancement.

### 4.5 Conformité fiscale (France, hypothèse)

- **Statut requis** : minimum **auto-entreprise** (micro-entreprise) pour facturer légalement.
- **Plafond CA** : 188 700 € pour vente de biens (jamais atteint au volume prévu). 77 700 € pour services. **Vente de licence logicielle = vente de bien si livraison numérique sans intervention humaine récurrente**.
- **TVA** : sous le plafond de franchise (36 800 € pour services, 91 900 € pour biens), pas de TVA à facturer. **Lemon Squeezy fait office de Merchant of Record** → ils facturent la TVA aux clients pour toi et te reversent le net. Tu déclares juste tes revenus.
- **Action** : si pas déjà fait, créer une auto-entreprise (5 min en ligne, gratuit) avant le premier euro encaissé. Activité = "édition de logiciels".

---

## 5. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Pas de traction (0-10 ventes) | Moyenne | Modéré (effort 5-8 j) | Voie 5 (lead magnet) reste payante en compétence |
| Support utilisateur chronophage | Moyenne | Élevé (peut consumer 1 j/semaine) | Doc FAQ visible, SLA "best effort" explicite dans EULA, pas de support téléphonique |
| Piratage clés Pro | Élevée | Faible (prix bas) | Tolérer. Itérer rapidement = moins de valeur du crack |
| Bug critique en Pro → remboursements | Faible | Modéré | Politique remboursement 14 j (légal EU), CI stricte, beta test 30 j auprès de 5-10 users |
| Concurrence sort une fonction équivalente gratuite | Moyenne | Modéré | Pivot vers spécialisation (ex : focus photographe pro) |
| Changement de loi (TVA, RGPD) | Faible | Faible | Lemon Squeezy gère, à suivre via leurs alertes |

---

## 6. Recommandation finale en 3 puces

1. **Voie principale = Freemium V1 Pro** : core OSS + batch CLI + watch-folder à 19 €/49 € sur Lemon Squeezy. Effort 5-8 j-h. Revenu cible 12 mois : 200-2 000 €.
2. **Cumuler systématiquement avec voie 5 (lead magnet)** : optimiser le README et les posts LinkedIn pour démontrer les compétences. Valeur indirecte potentielle 5-30 k€ en missions freelance, bien supérieure aux ventes Pro.
3. **Pré-requis non négociables AVANT lancement** :
   - Confirmer droits IP (clause employeur, pseudonyme → nom légal).
   - Retirer ExifTool bundlé (AUDIT_EXE F-01) → élimine ambiguïté GPL.
   - Créer auto-entreprise si pas déjà fait.
   - Produire au minimum S-01 + G-01 (assets visuels Phase 4 / MEDIA.md).
   - Page Privacy Policy minimale pour le checkout Lemon Squeezy.

**Si l'un de ces pré-requis bloque, lancer d'abord la voie 5 seule** (lead magnet via posts LinkedIn structurés — Phase 7 du méta-audit) — elle ne nécessite aucun pré-requis juridique.

---

## 7. Questions ouvertes (décision humaine)

1. **Statut juridique** : auto-entreprise déjà créée, ou à faire ? Activité déclarée compatible ?
2. **Audience LinkedIn / Twitter** : combien de followers actuellement ? (calibre la voie 6 formation).
3. **Temps disponible** : 5-8 j-h sur les 4 prochaines semaines, c'est tenable ?
4. **Tolérance au support utilisateur** : prêt à répondre 30-60 min/semaine à des emails utilisateurs ?
5. **Modules Pro V1** : batch CLI + watch-folder = bons choix ? Ou un autre module a plus de valeur perçue (ex : rapports HTML avancés, plugin API) ?
6. **Lancement Product Hunt** : oui/non ? Si oui, prévoir un "Hunter" influent qui submit pour toi → +3-5x visibilité.
