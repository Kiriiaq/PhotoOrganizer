# PhotoOrganizer — Plateformes de distribution & visibilité

> Phase 6 de l'audit méta-projet. Ordre de publication, titres/descriptions optimisés par plateforme, calendrier séquencé sur 6 semaines.
> Date : 2026-05-19. Pré-requis : Phase 5 ([docs/MONETIZATION.md](MONETIZATION.md)) validée.

---

## 1. Synthèse — quelle plateforme pour quoi

| Voie | Plateforme primaire | Plateformes secondaires |
|---|---|---|
| Distribution core (gratuit) | **GitHub Releases** | PyPI, AlternativeTo |
| Distribution Pro (payant) | **Lemon Squeezy** | (pas de fallback recommandé) |
| Lancement / découverte | **Product Hunt** | Show HN, Indie Hackers |
| Communautés thématiques | **Reddit** (r/photography, r/datahoarder) | Forums photo FR (Chassimages, Phototrend) |
| Réseaux sociaux | **LinkedIn** | X/Twitter, Mastodon |
| Articles techniques | **dev.to** | Medium, Hashnode |
| Démo vidéo | **YouTube** | LinkedIn (vidéo native) |
| Recensement | **AlternativeTo** | Softpedia (low priority) |

---

## 2. Détail par plateforme

### 2.1 GitHub Releases ⭐⭐⭐⭐⭐ — Distribution core (déjà actif)

- **Statut actuel** : déjà actif (v1.0.0 publié déc 2025, v2.1.0 taggé). Workflow `release.yml` produit automatiquement le .exe au push d'un tag `v*`.
- **Action** :
  - Publier proprement la prochaine release (v2.2.0 ?) avec notes complètes basées sur [CHANGELOG.md](../CHANGELOG.md).
  - Activer **GitHub Releases assets analytics** (gratuit, montre le nb de downloads).
  - Ajouter le **social preview image** (1280×640 px) dans Settings → General → Social preview. À produire : cf. [MEDIA.md](MEDIA.md) L-04.
- **Titre release** : `PhotoOrganizer v2.2.0 — Refonte panneau Organisation`
- **Description type** (à adapter par release) :

  ```markdown
  ## What's new
  - Refonte du panneau Organisation : onglets internes, exemples intégrés.
  - Quarantaine réversible pour les doublons.
  - Audit complet du projet (architecture, monétisation, plan optimisation EXE).

  ## Downloads
  - `PhotoOrganizer-2.2.0.exe` (37 MB, Windows 10/11, windowed)
  - `PhotoOrganizer-2.2.0-debug.exe` (37 MB, console + verbose logging)

  ## Verify integrity
  See `checksums-sha256.txt` attached.

  ## Full changelog
  https://github.com/Kiriiaq/PhotoOrganizer/blob/main/CHANGELOG.md
  ```

- **Tags GitHub repo** (Settings → Topics) : `python`, `customtkinter`, `photo-organizer`, `exif`, `windows`, `desktop-application`, `freemium`, `pyinstaller`, `apache-license`, `metadata-extraction`.
- **Calendrier** : à chaque release. **Pré-condition** : assets visuels S-01 et G-01 au moins (cf. Phase 4 gap P0).

### 2.2 PyPI ⭐⭐⭐ — Distribution pip install

- **Pertinence** : moyenne. Le projet est une **app GUI desktop** plus qu'une lib, donc `pip install photoorganizer` n'est pas le canal naturel. Mais cela permet à des power users / devs de lancer depuis sources rapidement.
- **Action** :
  - Vérifier que `pyproject.toml` produit un wheel propre : `python -m build`.
  - Tester en local : `pip install dist/photoorganizer-2.2.0-py3-none-any.whl && photo-organizer`.
  - Compte PyPI à créer (gratuit, 2FA obligatoire).
  - Upload : `twine upload dist/*` ou via [trusted publisher GitHub Actions](https://docs.pypi.org/trusted-publishers/).
- **Description PyPI** : reprendre le README.md (lu automatiquement).
- **Keywords** : déjà dans `pyproject.toml` (à enrichir : `cli`, `gui`, `tkinter`, `desktop`).
- **Conflit de nom** : vérifier `pip search photoorganizer` — si pris, fallback `photoorganizer-kiriiaq` ou `pyphotoorganizer`.
- **Calendrier** : S+1 (après GitHub Release officielle). Effort 2-3 h.
- **Risque** : nul. Gratuit, retirable.

### 2.3 Lemon Squeezy ⭐⭐⭐⭐⭐ — Distribution Pro (Phase 5)

- **Statut actuel** : pas en place. Pré-requis Phase 5.
- **Page produit (Lemon Squeezy Storefront ou site web custom)** :
  - **Titre** : `PhotoOrganizer Pro — Batch CLI & Watch-Folder for Windows`
  - **Tagline** : `Automate your photo organization. Run from terminal or auto-organize new photos as they arrive.`
  - **Description** :
    ```
    The free PhotoOrganizer GUI handles your one-shot needs.
    PhotoOrganizer Pro adds the two features power users keep asking for:

    1. Batch CLI — script your organization rules, schedule with Task Scheduler / cron.
    2. Watch-Folder — drop a photo, it lands organized in the right folder automatically.

    Built on the same proven core as the free version. One-time payment, offline activation, no subscription.
    ```
  - **Pricing display** : 3 cartes (Personnelle 19 € · Studio 49 € · Lifetime 99 €).
  - **Code promo lancement** : `EARLY30` (-30 % les 30 premiers jours).
- **Webhook** : `order.created` → Cloud Run / lambda gratuite → envoie email avec clé RSA signée.
- **Calendrier** : S+1 (page créée silencieusement, prête mais pas annoncée).
- **Effort** : 4-6 h (setup + page + webhook + test du flow).

### 2.4 Product Hunt ⭐⭐⭐⭐⭐ — Lancement principal

- **Pertinence** : haute. Vise les early adopters tech/design, traffic spike sur 24-48 h (typique : 500-5 000 visiteurs si Top 5 du jour).
- **Pré-requis stricts** :
  - Compte créé > 7 jours avant le launch (anti-spam).
  - Au moins **1 commentaire et 1 upvote sur 3-5 autres produits** dans la semaine précédente (signal de bonne foi).
  - **Hunter recommandé** : un utilisateur Product Hunt influent qui submit pour toi (visibilité ×3-5). Trouver un hunter via [PHHunters](https://hunterboard.io/) ou demander dans Indie Hackers.
- **Choix du jour** : **mardi** ou **mercredi** (concurrence plus faible que lundi, audience plus active que week-end). **Submission à 00:01 PT** (9h Paris).
- **Page Product Hunt** :
  - **Name** : `PhotoOrganizer`
  - **Tagline** (60 chars max) : `Automate photo organization by date, camera & GPS. Free.`
  - **Description** (260 chars max) :
    ```
    Sort thousands of photos by EXIF metadata in seconds. Multi-criteria
    organization (date / camera / GPS), duplicate detection with reversible
    quarantine, rollback history. Windows desktop, no install, free + open
    source. Pro edition adds batch CLI & watch-folder ($19).
    ```
  - **Topics** (≤ 5) : `Photography`, `Productivity`, `Open Source`, `Windows`, `Developer Tools`.
  - **Gallery** : 4-5 visuels (S-01, S-03, S-04, S-06, S-07 — voir [MEDIA.md](MEDIA.md)).
  - **First comment** (à poster toi-même immédiatement après publication) :
    ```
    Hi PH 👋

    I built PhotoOrganizer because my own photo library was a mess: thousands of
    files from 3 cameras, 2 phones, and a drone, all dumped in folders named
    "to_sort_2023". Lightroom does this but costs €120/yr. FastStone is dated.
    Nothing felt right.

    The free version handles 95% of needs (date / camera / GPS organization,
    duplicate detection with reversible quarantine, full rollback history).

    The Pro edition (€19 one-shot) adds:
    - Batch CLI: scriptable, runs from terminal / Task Scheduler / cron.
    - Watch-folder: drop a photo, it auto-organizes.

    Tech stack for the curious: Python 3.11, CustomTkinter, PyInstaller onefile,
    170 tests, Apache-2.0 core + proprietary Pro.

    Happy to answer questions about the freemium architecture, the EXE size
    optimization journey (37 MB → 22 MB target, audit published), or anything
    else. Cheers!
    ```
- **Calendrier** : S+3, mardi 9h Paris.
- **Effort** : 2-3 h le jour J pour répondre aux commentaires (critique pour le ranking).

### 2.5 Hacker News — Show HN ⭐⭐⭐⭐ — Lancement technique

- **Pertinence** : haute pour un projet open-source avec angle technique fort. PhotoOrganizer en a deux : **EXE optimization** (audit publié) et **freemium architecture pure offline**.
- **Format** : `Show HN: <title> — <one-line>` ; lien direct vers GitHub README (pas vers landing page commerciale, HN déteste ça).
- **Titre** (deux versions A/B possibles) :
  - Version A : `Show HN: PhotoOrganizer — Free Windows app to organize photos by EXIF metadata`
  - Version B : `Show HN: How I went from 37 MB to 22 MB PyInstaller EXE — and the audit script`
  - **Recommandation** : version B → angle technique = mieux pour HN, sera plus upvotée. Inclure PhotoOrganizer comme exemple, link vers `docs/exe-optimization.md`.
- **Calendrier** : **S+4, mardi-mercredi 7h PT** (10h ET, 16h Paris). Pas le jour du Product Hunt (concentrer l'attention).
- **Stratégie de réponse** : être disponible 4-6 h pour répondre aux commentaires (HN voit l'activité auteur comme un signal positif). Réponses techniques uniquement, pas commercial.
- **Risque** : HN peut être hostile au freemium si présenté maladroitement. Le ton doit être "voici comment c'est construit", pas "venez acheter".

### 2.6 Indie Hackers ⭐⭐⭐ — Lancement business

- **Pertinence** : audience makers/indie devs. Bon pour discuter le côté freemium/pricing.
- **Section** : "Show IH" puis post Milestone quand 1ère vente.
- **Titre** : `Launching PhotoOrganizer Pro — going freemium on a 16k LOC Python desktop app`
- **Contenu** (extrait) :
  ```
  After 18 months on the open-source GUI, I'm launching a Pro edition.
  Pricing: $19 / $49 / $99 lifetime. Platform: Lemon Squeezy.
  
  Decisions I'm second-guessing:
  - Offline RSA license vs online auth server (chose offline for zero recurring cost)
  - Bundling vs separate Pro EXE (chose separate to keep core install lean)
  - 19€ vs 39€ entry price (chose 19€ — race to volume, not margin)
  
  Curious to hear from anyone who's gone freemium on a desktop app.
  ```
- **Calendrier** : S+4, même semaine que Show HN mais jour différent (jeudi).

### 2.7 Reddit ⭐⭐⭐⭐ — Communautés thématiques

- **Pertinence** : haute si bien ciblé. **Risque modéré** : Reddit déteste l'auto-promotion mal cadrée (règle 9:1 — 9 contributions pour 1 self-promo).
- **Subreddits ciblés** :

  | Subreddit | Membres | Angle | Risque |
  |---|---|---|---|
  | r/photography | 5,2 M | Outil utile pour photographes amateurs | Modéré — peu de devs |
  | r/datahoarder | 800 k | "Organize my 50 TB of photos" | Faible — public technique tolérant |
  | r/Windows10 / r/Windows11 | 1,2 M / 600 k | App native Windows | Faible |
  | r/AskPhotography | 250 k | Réponse à des questions de tri | Faible si contextualisé |
  | r/photographyprotips | 95 k | Workflow pro | Modéré |
  | r/Lightroom | 200 k | Alternative gratuite | Élevé — pas trop polariser |
  | r/freeware | 200 k | App gratuite Windows | Faible |
  | r/opensource | 230 k | Apache-2.0, freemium model | Faible |

- **Format à privilégier** : pas "I built X, here's the link" mais "I had problem Y, I built X to solve it, here's what I learned" (storytelling).
- **Titre exemple r/datahoarder** : `Built a free Windows tool to organize 50k+ photos by EXIF metadata — sharing in case useful`
- **Calendrier** : étaler sur 2 semaines, 1 subreddit / 3 jours max (pour ne pas être flagué multi-post). Préférer après Product Hunt (peut référencer "as featured on PH").

### 2.8 LinkedIn ⭐⭐⭐⭐⭐ — Audience perso + lead magnet

- **Pertinence** : critique pour le lead magnet (voie 5 monétisation). Public mixte décideurs / devs / recruteurs.
- **Format** : 3 posts structurés (cf. Phase 7) sur 6 semaines.
  - **Post 1** : technique court (800-1200 c) — l'optimisation EXE, le freemium architecture.
  - **Post 2** : carrousel 6-8 slides — features, stack, archi.
  - **Post 3** : storytelling long (1500-2000 c) — d'où vient le projet, friction, résultat.
- **Hashtags** (3-5 max, pas en pavé) : `#Python`, `#WindowsDevelopment`, `#OpenSource`, `#IndieDev`.
- **CTA** : lien GitHub + offre de discussion ("DM si tu veux échanger sur le tri d'images, le packaging Python, ou la stratégie freemium").
- **Calendrier** : S+3 post 1, S+5 post 2, S+8 post 3. Espacement = pas saturer l'audience.

### 2.9 X / Twitter ⭐⭐⭐ — Snippets visuels

- **Pertinence** : moyenne. Bon pour visibilité dev / photo. Format court.
- **Thread structuré** : 4-6 tweets avec image par tweet.
  - Tweet 1 : hook + screenshot S-01.
  - Tweet 2 : problème en 1 phrase + chiffre (ex : "10 000 photos, 4 appareils").
  - Tweet 3 : G-01 (GIF démo).
  - Tweet 4 : stack tech (badge style).
  - Tweet 5 : audit EXE optimization (1 chiffre marquant).
  - Tweet 6 : CTA "Free on GitHub, Pro €19 — link in bio".
- **Calendrier** : S+3 (en parallèle Product Hunt) puis 1 thread / mois.

### 2.10 dev.to / Medium ⭐⭐⭐ — Articles techniques

- **Pertinence** : moyenne-haute pour SEO et pour le lead magnet. Génère du backlink GitHub.
- **Articles à écrire** :

  | # | Titre | Plateforme | Effort | Quand |
  |---|---|---|---|---|
  | A1 | `How I reduced a PyInstaller .exe from 37 MB to 22 MB` | dev.to | 4-6 h | S+5 |
  | A2 | `Freemium architecture for a Python desktop app: license validation without a server` | dev.to | 3-4 h | S+7 |
  | A3 | `CustomTkinter in production: 5 patterns I wish I knew before shipping 16k LOC` | dev.to | 3-4 h | S+10 |
- **Tags dev.to** (max 4) : `python`, `windows`, `opensource`, `tutorial`.
- **Cross-post** Medium / Hashnode 1 semaine après dev.to (SEO non-cannibalisé).

### 2.11 YouTube ⭐⭐ — Démo vidéo

- **Pertinence** : moyenne. Investissement temps élevé pour résultat incertain sans audience pré-existante.
- **Vidéo cible** : `intro.mp4` produite pour MEDIA.md V-01 (60 s pitch + démo).
- **Titre** : `PhotoOrganizer — Auto-sort thousands of photos by EXIF (Windows, free + open source)`
- **Description** : pitch + chapters + liens GitHub / Pro / Ko-fi.
- **Tags YouTube** : `photo organizer`, `exif metadata`, `windows photo software`, `python desktop app`, `customtkinter`, `free photo software`.
- **Calendrier** : S+5 (après production vidéo). Ne pas attendre la vidéo si elle bloque — c'est P2.

### 2.12 AlternativeTo ⭐⭐⭐ — Recensement gratuit

- **Pertinence** : SEO long terme. Quand quelqu'un cherche "Lightroom alternative free", PhotoOrganizer doit apparaître.
- **Action** : créer une entrée [alternativeto.net/software/lightroom/](https://alternativeto.net/) → "Suggest alternative" → PhotoOrganizer.
- **Description** : reprendre celle de Product Hunt.
- **Tags** : free, open-source, windows, photo-management.
- **Calendrier** : S+6 (après Product Hunt, pour pouvoir mentionner "Featured on PH").
- **Effort** : 30 min.

### 2.13 Plateformes écartées

| Plateforme | Raison du rejet |
|---|---|
| **Microsoft Store** | Certification stricte, signature .exe payante (300 €+/an), processus 1-3 semaines. Pas rentable au niveau de ventes attendu. |
| **Chocolatey** | Nécessite maintenance manifest + tests automatiques. Public dev/admin, pas la cible PhotoOrganizer. À reconsidérer si traction Windows pro. |
| **Snap Store / Flathub** | App Windows uniquement. Hors scope. |
| **Itch.io** | Plateforme game-focused. Hors scope. |
| **VSCode / Chrome / Figma Marketplace** | Pas un plugin de ces écosystèmes. |
| **Softpedia / FileHippo** | Audience qui ne convertit pas en Pro. Effort de soumission > gain. |
| **Mastodon** | Pertinent mais audience tech faible vs LinkedIn/X. À cumuler si déjà actif, sinon pas la peine de créer un compte. |

---

## 3. Calendrier de lancement sur 6 semaines

> **Règle d'or** : ne **jamais** lancer plusieurs canaux le même jour. Étaler permet de capitaliser sur l'effet "as seen on X" pour la plateforme suivante.

### Vue compacte

```
S-1 ────── S+0 ─── S+1 ─── S+2 ─── S+3 ─── S+4 ─── S+5 ─── S+6 ─── S+8 ─── S+10
 │           │       │       │       │       │       │       │       │       │
 prep      GitHub  PyPI    Reddit  Product  Show HN dev.to  Alt.To  LinkedIn dev.to
           Release LSqueezy r/free  Hunt    Indie   article banner  post 2   art 2
                            ware            Hackers A1      sociale  carrousel
```

### Détail jour par jour

| Date | Plateforme | Action | Pré-requis | Effort |
|---|---|---|---|---|
| **S-1** (prep) | — | Produire S-01 + G-01 + L-03 logo (cf. [MEDIA.md](MEDIA.md)) | rien | 4-6 h |
| **S-1** | GitHub | Préparer release notes complètes basées sur CHANGELOG | rien | 1 h |
| **S-1** | Lemon Squeezy | Configurer compte, page produit en mode brouillon | Pro V1 build OK | 4-6 h |
| **S+0 lundi** | GitHub | **Tag `v2.2.0` + Release** avec EXE + checksums | release notes | 1 h |
| **S+0 lundi** | Lemon Squeezy | **Publier page** en live (mais ne pas annoncer) | webhook OK | 30 min |
| **S+1 mercredi** | PyPI | **Upload `photoorganizer 2.2.0`** | wheel OK | 2-3 h |
| **S+1 jeudi** | Reddit | Post r/freeware (court, factuel) | rien | 1 h |
| **S+2 lundi** | Reddit | Post r/datahoarder (storytelling) | post r/freeware OK | 1 h |
| **S+3 mardi 9h Paris** | **Product Hunt** | **Submission jour J** + first comment + monitoring 4-6 h | Hunter trouvé, 4-5 visuels | 4-6 h |
| **S+3 mercredi** | LinkedIn | **Post 1** (technique court) | rien | 1 h écriture + 1 h interactions |
| **S+3 mercredi** | X / Twitter | **Thread** 4-6 tweets en parallèle LinkedIn | visuels prêts | 1 h |
| **S+4 mercredi** | **Hacker News** | **Show HN** : `How I went from 37 MB to 22 MB PyInstaller EXE` | audit EXE publié | 4-6 h monitoring |
| **S+4 jeudi** | Indie Hackers | Post Milestone freemium launch | rien | 1 h |
| **S+5 mardi** | Reddit | Post r/photography (positionnement utilisateur) | rien | 1 h |
| **S+5 mercredi** | LinkedIn | **Post 2** : carrousel 6-8 slides | carrousel produit (Figma) | 4 h écriture + 1 h interactions |
| **S+5 vendredi** | dev.to | **Article A1** : `How I reduced PyInstaller .exe from 37 MB to 22 MB` | audit publié | 4-6 h |
| **S+6 lundi** | AlternativeTo | Créer entrée comme alternative à Lightroom, FastStone, IrfanView | rien | 30 min |
| **S+7 mercredi** | dev.to | **Article A2** : `Freemium architecture for Python desktop app` | rien | 3-4 h |
| **S+8 lundi** | LinkedIn | **Post 3** : storytelling long | rien | 3-4 h |
| **S+10 mercredi** | dev.to | **Article A3** : `CustomTkinter in production` | rien | 3-4 h |

### Effort cumulé

- **Préparation S-1** : 9-13 h
- **Semaines 0-2** (publication + premières communautés) : 10-15 h
- **Semaines 3-4** (lancement Product Hunt + Show HN + LinkedIn) : 18-25 h
- **Semaines 5-10** (marketing organique) : 20-30 h

**Total 6-10 semaines : 60-85 h** (~ 8-11 jours-homme étalés).

---

## 4. Métriques à suivre (KPI)

| Métrique | Source | Cible 90 j |
|---|---|---|
| GitHub stars | github.com/Kiriiaq/PhotoOrganizer | 200-500 |
| Downloads EXE | GitHub Release insights | 1 000-3 000 |
| Visiteurs Product Hunt | dashboard PH | 500-3 000 |
| Upvotes Show HN | news.ycombinator.com | 30-150 |
| Followers LinkedIn (delta) | LinkedIn analytics | +50-200 |
| Ventes Lemon Squeezy | dashboard LS | 10-100 |
| Dons Ko-fi | dashboard Ko-fi | 5-30 |
| Backlinks / mentions | Google Alerts `"PhotoOrganizer" Kiriiaq` | 5-20 |
| Issues GitHub ouvertes | github issues | 5-30 |

**Décision à T+90j** : si ventes Pro > 50 → continuer V2 modules (plugin API, rapports avancés). Si < 10 → bascule sur lead magnet seul (voie 5), pas V2 Pro.

---

## 5. Erreurs à éviter

1. **Tout lancer le même jour** : disperse l'attention, perd l'effet "as seen on X".
2. **Soumettre Product Hunt sans Hunter** : visibilité ÷3-5. Soit attendre d'en trouver un, soit poster soi-même un mercredi calme.
3. **Reddit auto-promo brute** : `"I built X check it out"` → downvote en 5 min. Toujours storytelling + valeur d'abord.
4. **Show HN avec lien Lemon Squeezy en première place** : HN flag commercial. Lien GitHub README uniquement.
5. **Spam de subreddits** : 1 par 3 jours max, jamais 2 le même jour.
6. **LinkedIn hashtag-spam** (10+ #) : algorithme dévalorise. Max 5.
7. **Vidéo YouTube générique sans hook 3 secondes** : 80 % drop avant 10 s. Investir dans le hook ou ne pas faire.
8. **Annoncer Pro avant que le checkout marche** : 0 conversions, frustration utilisateur.

---

## 6. Questions ouvertes (décision humaine)

1. **Hunter Product Hunt** : as-tu un contact ou faut-il en trouver un via [PHHunters](https://hunterboard.io/) ?
2. **Compte PyPI** : déjà existant sur ton email ?
3. **Audience LinkedIn actuelle** : 500 ? 5 000 ? 50 000 ? (calibre les attentes posts).
4. **Disponibilité 4-6 h le jour Product Hunt** : pour répondre aux commentaires en temps réel.
5. **Tolérance Reddit** : OK pour gérer les downvotes / commentaires hostiles ?
6. **Vidéo YouTube** : prioritaire ou différée ? (60 s = ~1 j de prod ; intro brute = 3 h).
7. **Cible géographique** : francophone (forums photo FR) ou anglophone (PH, HN, Reddit US) en priorité ? Recommandé : anglophone pour volume, FR en complément.
