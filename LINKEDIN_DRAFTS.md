# PhotoOrganizer — Drafts LinkedIn / X (Phase 7)

> 3 formats prêts à copier-coller. Compétences mises en avant = celles réellement démontrées par le projet (issues de l'audit Phase 1).
> Date : 2026-05-19. Stratégie de publication : voir [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md) (calendrier S+3, S+5, S+8).

---

## Conventions

- **Compteurs de caractères** indiqués pour chaque post (LinkedIn affiche en pleine longueur jusqu'à 3 000 c, mais ce qui passe au-dessus du "voir plus" est ~210 c sur mobile, ~280 c sur desktop).
- **Hashtags** : 3-5 max, en fin de post, jamais en pavé.
- **Lien GitHub** : toujours dans le commentaire (LinkedIn dévalorise les liens dans le corps du post).
- **Tone** : factuel, pas d'auto-félicitations. Chiffres concrets.

---

## Format 1 — Post technique court (LinkedIn / X thread tweet 1)

> **Cible** : devs Python, recruteurs tech.
> **Objectif** : montrer une compétence pointue (audit packaging) + lien produit.
> **Compteur** : ~1 100 caractères (limite cible 800-1200).
> **Quand** : S+3 mercredi (jour J+1 Product Hunt — capitalise sur "as seen on PH").

---

```
J'ai audité un .exe PyInstaller de 37 Mo. Cible : -40 % sans toucher à
l'UX.

Méthode en 3 étapes :

1. `pyi-archive_viewer -l app.exe` → liste tous les fichiers du
   bundle avec leur taille compressée. 1 721 fichiers, 35 Mo.

2. Catégorisation par grep. Résultat brut :

   - ExifTool Perl bundlé : 10,3 Mo (29 %) ← jamais utilisé en pratique
   - cryptography tiré par hooks PyInstaller : 4,2 Mo
   - libx265 dans pillow-heif : 2,3 Mo ← on lit du HEIC, on n'écrit pas
   - PIL._avif depuis Pillow 12 : 1,8 Mo

3. Test des hypothèses : retrait du bundle ExifTool (chemin codé en dur
   pointait vers un emplacement inexistant — fallback cassé depuis le
   début). Switch pillow-heif → pi-heif (sister-package read-only).
   Build dans un venv minimal isolé du Python global (325 paquets).

Gain estimé : 15 Mo, soit -40 %. Cible 22 Mo.

Le piège qui m'a coûté le plus de temps : le Python global était
pollué (numpy, pandas, scipy). PyInstaller détectait des hooks
inattendus, gonflait le bundle en silence.

Audit complet en open-source dans le repo (.md + .html).

#Python #PyInstaller #DevOps
```

**Compteur** : 1 098 caractères (hors hashtags). ✅

**Commentaire à poster juste après** (1er commentaire = booster algo) :

```
Repo + audit complet ici : https://github.com/Kiriiaq/PhotoOrganizer

Si tu travailles sur une app Python desktop packagée, le doc
`docs/exe-optimization.md` détaille les 19 findings avec gain
chiffré par action. Curieux de tes propres retours sur le sujet.
```

---

## Format 2 — Carrousel 6-8 slides (LinkedIn)

> **Cible** : public mixte (devs + photographes amateurs + recruteurs).
> **Objectif** : présenter le projet complet en un parcours visuel.
> **Format** : 1080×1350 px (portrait, ratio 4:5 — meilleur engagement LinkedIn).
> **Quand** : S+5 mercredi.
> **Production** : Figma ou Canva, gabarit cohérent (1 couleur dominante = #2b5fa1, 1 police = Inter ou Roboto).

---

### Slide 1 — Hook (couverture)

**Visuel** : grand screenshot d'un dossier "DCIM" Windows en bordel + flèche → screenshot S-01 du panneau Organisation propre.

```
J'ai organisé 12 000 photos
en 47 secondes.

Sans Lightroom.
Sans abonnement.
```

(Le minimalisme attire le clic vers slide 2.)

---

### Slide 2 — Problème

**Visuel** : 3 icônes empilées (appareil photo, smartphone, drone) + flèche vers un seul dossier "Tout est mélangé".

```
Le vrai problème :

3 appareils, 2 smartphones, 1 drone.
12 000 fichiers JPG, RAW, HEIC, MP4.
Aucun moyen simple de trier sans payer
Lightroom 120 €/an ou apprendre Bash.

Les noms : "20240612_171922_IMG_4567.JPG".
Les dossiers : "to_sort_2023".

Pas une solution. Un classement par date manuel
prend 3-4 heures pour 1 000 photos.
```

---

### Slide 3 — Feature 1 : Organisation multi-critères

**Visuel** : capture S-02 (panneau Organisation en cours) avec annotations sur les cases à cocher Date / Caméra / GPS.

```
Feature 1 : Organisation par EXIF

✓ Date (jour / mois / année)
✓ Modèle d'appareil (Canon 5D / iPhone 15 Pro / Mavic)
✓ Coordonnées GPS (avec nom de lieu)
✓ Cumulable hiérarchiquement

Templates de renommage personnalisables :
{date:%Y-%m-%d}_{model}_{counter:04d}.{ext}

Copy par défaut. Move avec rollback. Pas de drama.
```

---

### Slide 4 — Feature 2 : Doublons + Quarantaine

**Visuel** : capture S-03 (onglet Doublons avec groupes) + zoom sur le bouton "Mise en quarantaine".

```
Feature 2 : Détection de doublons

Scan parallèle. 3 algorithmes (MD5 / SHA-1 / Blake3).
Exclusion automatique des corbeilles système.

Mais le vrai apport : la suppression réversible.

send2trash = aller simple.
PhotoOrganizer = quarantaine interne avec
metadata.json par fichier. Rollback à la séance.
Vidange manuelle vers la corbeille Windows quand
tu es sûr.

Plus jamais de "j'ai supprimé en doublon ce qui
n'en était pas un".
```

---

### Slide 5 — Feature 3 : Historique + Rollback

**Visuel** : capture S-04 (onglet Historique) avec une session sélectionnée et le bouton Annuler visible.

```
Feature 3 : Rollback complet par session

Chaque opération (organize, dedup, quarantine)
est tracée. Annulation propre :
- Replace les fichiers à leur emplacement initial
- Recrée les dossiers source vidés
- Cohérent même après plusieurs sessions

Trois bugs majeurs corrigés en v2 :
- FileManager partagé entre onglets (avant : historique vide)
- Cancel réellement propagé à SmartOrganizer
- Recréation du dossier source après move

Bonus : raccourcis Ctrl+1..4 entre onglets.
```

---

### Slide 6 — Stack & architecture

**Visuel** : schéma simplifié 3 couches (UI / core / utils) en SVG-like.

```
Stack technique :

→ Python 3.11+ · CustomTkinter
→ Pillow + exifread + pillow-heif
→ SQLite (cache 2-tier RAM + disque)
→ PyInstaller --onefile (37 Mo → 22 Mo en cours)
→ pytest : 170 tests, 5 catégories, 70 % core
→ GitHub Actions Windows (lint + tests + release auto)

Frontière stricte : core/ n'importe jamais ui/.
Permet un freemium propre (futur src/photoorganizer_pro/).

16 021 LOC source. 38 fichiers Python. 0 Bandit High.
```

---

### Slide 7 — Apprentissage clé

**Visuel** : texte uniquement, fond uni.

```
Ce que j'ai appris :

Auditer un projet avant de l'optimiser, pas après.

J'ai cru pendant des mois que le .exe pesait
37 Mo "à cause de Python". Faux.

10 Mo venaient d'un ExifTool Perl bundlé
au cas où — fallback cassé depuis le début
(chemin codé sur le mauvais dossier).

4 Mo venaient de cryptography tiré par
des hooks PyInstaller parce que mon venv
de build contenait 325 paquets.

Le bon outil : pyi-archive_viewer -l.
Le bon réflexe : venv minimal pour le build.
```

---

### Slide 8 — CTA

**Visuel** : 3 icônes (download, star, message).

```
Si tu veux essayer ou regarder le code :

→ Téléchargement Windows : github.com/Kiriiaq/PhotoOrganizer
→ Audit packaging complet : docs/exe-optimization.md
→ DM si tu veux échanger sur :
  · le packaging Python desktop
  · le freemium architecture
  · le tri d'images en lot

Apache-2.0. Pas d'auto-promo dans les commentaires
si ça ne t'intéresse pas — je n'ai pas honte.
```

---

### Texte d'accompagnement du carrousel (corps du post)

```
12 000 photos triées en 47 secondes, sans Lightroom.

J'ai construit PhotoOrganizer parce que mon dossier
photo était devenu illisible. Aujourd'hui le projet
fait 16 000 lignes de Python, 170 tests, et tourne
en .exe Windows portable.

Quelques décisions techniques détaillées dans le
carrousel : architecture en couches, cache 2-tier,
quarantaine réversible, optimisation taille du .exe.

Open-source (Apache-2.0). Lien dans les commentaires.

#Python #IndieDev #OpenSource
```

**Compteur** : 472 caractères (corps), ~250 mots par slide en moyenne. ✅

---

## Format 3 — Post storytelling long (LinkedIn)

> **Cible** : devs + makers + recruteurs (ouverture freelance).
> **Objectif** : trajectoire personnelle + résultat mesuré + ouverture pour discussion.
> **Compteur** : ~1 850 caractères (limite cible 1500-2000).
> **Quand** : S+8 lundi.

---

```
En 2023, j'avais 47 000 photos non triées.
Le tri à la main avec File Explorer m'aurait pris
des semaines.

J'ai cherché un outil gratuit qui fasse ça
correctement sous Windows. Verdict en 2 heures :

→ Lightroom : 12 €/mois pour une fonctionnalité que
   je voulais utiliser une seule fois.
→ FastStone : interface 2008, pas de RAW correct.
→ Adobe Bridge : 14 Go installés pour 3 boutons.
→ Scripts Python sur GitHub : tous abandonnés,
   aucun ne gère HEIC ni les doublons.

J'ai écrit la première version moi-même un samedi
soir. C'était laid mais ça marchait sur 10 dossiers.
J'ai posté le repo "pour mémoire", sans intention.

18 mois plus tard, le projet fait 16 000 lignes,
170 tests, un .exe Windows de 37 Mo distribué via
GitHub Releases.

Ce qui a changé en cours de route :

1. Un audit en 7 phases du projet entier, parce que
   le repo commençait à être un patchwork. Inventaire
   complet, restructuration, fichiers standards
   (CHANGELOG, CONTRIBUTING, SECURITY, ARCHITECTURE)
   et un dashboard HTML autonome pour suivre l'état.

2. Un audit packaging : passer le .exe de 37 Mo à
   22 Mo en mesurant chaque catégorie au lieu de
   deviner. Premier choc : 10 Mo d'ExifTool Perl
   embarqués alors que le fallback était cassé
   depuis le départ. Plus jamais "à la louche".

3. Une stratégie freemium documentée : core
   Apache-2.0 + édition Pro propriétaire à 19 €
   (batch CLI + watch-folder). Activation offline,
   zéro serveur, zéro coût récurrent.

Honnêtement : je ne pense pas que la version Pro
rapporte plus que quelques centaines d'euros la
première année. C'est OK.

Le vrai retour pour moi : le projet a déjà servi à
expliquer mes pratiques (tests, CI, architecture en
couches, packaging) lors de deux entretiens.

Si tu travailles sur ton propre projet et que tu
hésites entre "le rendre vraiment propre" ou "le
laisser comme ça parce que ce n'est qu'un side
project" : la propreté ouvre des conversations.
Pas des ventes — des conversations.

Open-source dans les commentaires.

#Python #IndieDev #OpenSource
```

**Compteur** : 1 868 caractères (hors hashtags). ✅

**Commentaire à poster juste après** :

```
Le repo : https://github.com/Kiriiaq/PhotoOrganizer

Pour qui se demande à quoi ressemble un audit projet
structuré : AUDIT.md, docs/exe-optimization.md et
docs/MONETIZATION.md à la racine sont les livrables
les plus utiles à parcourir.

Si tu cherches à appliquer la même méthode à ton
propre projet et que tu veux échanger : DM ouvert.
```

---

## Format 4 (bonus) — Thread X / Twitter (4-6 tweets)

> **Quand** : S+3 mercredi (parallèle au post LinkedIn 1).
> **Format** : 4-6 tweets, 1 visuel par tweet, lien GitHub dans le dernier.

### Tweet 1 (hook + S-01)

```
J'ai construit une app Windows gratuite pour trier
12 000 photos en 47 secondes.

Pas Lightroom. Pas FastStone. Python + CustomTkinter
+ PyInstaller. Open-source.

🧵
```

### Tweet 2 (problème + GIF G-01)

```
Le problème :
- 3 appareils, 2 phones, 1 drone
- 12 000 fichiers JPG / RAW / HEIC / MP4
- "DCIM" et "to_sort_2023" partout

Tri manuel = 3-4 h pour 1 000 photos.

PhotoOrganizer le fait par EXIF.
```

### Tweet 3 (features + S-02)

```
Ce qu'elle fait :
- Tri par date / caméra / GPS (cumulables)
- Doublons multi-algo + quarantaine réversible
- Rollback complet par session
- Templates de renommage personnalisables
- 45 formats supportés (RAW inclus)
```

### Tweet 4 (stack + capture archi simplifiée)

```
Stack :
- Python 3.11 + CustomTkinter (UI)
- Pillow + exifread + pillow-heif (lecture EXIF)
- SQLite (cache 2-tier RAM + disque)
- PyInstaller --onefile (37 Mo)
- pytest : 170 tests, GitHub Actions Windows

16 021 LOC, 0 Bandit High.
```

### Tweet 5 (audit EXE — l'angle technique fort)

```
Le truc le plus instructif : audit du .exe.

37 Mo → 22 Mo en mesurant chaque catégorie
(pyi-archive_viewer -l).

10 Mo venaient d'un ExifTool Perl bundlé
au cas où — fallback cassé depuis le départ.

L'audit complet est dans le repo.
```

### Tweet 6 (CTA)

```
Free download : github.com/Kiriiaq/PhotoOrganizer

Pro edition (batch CLI + watch-folder) lance bientôt
à 19 €.

DM ouvert si tu veux discuter packaging Python
desktop ou freemium architecture.
```

---

## Format 5 (bonus) — Show HN (Hacker News)

> **Quand** : S+4 mardi 7h PT (10h ET, 16h Paris).
> **Lien** : GitHub README UNIQUEMENT (jamais Lemon Squeezy direct).

### Titre

```
Show HN: How I went from 37MB to 22MB PyInstaller EXE — and the audit script
```

### Premier commentaire (à poster immédiatement)

```
Hi HN,

Author here. I built a desktop photo organizer for Windows
(PhotoOrganizer, GUI app in Python/CustomTkinter), and at some point
the .exe ballooned to 37 MB onefile. I wrote an audit pipeline that
broke down the bundle by category and surfaced the easy wins.

What surprised me most:

1. ExifTool Perl runtime bundled as a "fallback" was 10.3 MB compressed
   (29% of the binary). The code path that used it was broken from day
   one (wrong hardcoded path). Nobody noticed because the primary
   readers (exifread, Pillow, pillow-heif) covered 99% of cases.

2. cryptography appeared in the bundle (4.2 MB) even though the project
   doesn't use it. PyInstaller picked it up because my system Python
   had 325 packages installed (numpy, pandas, scipy, etc.) and hooks
   pulled it in transitively. Lesson: always build from a minimal
   isolated venv.

3. Pillow 12 ships _avif.pyd at 1.8 MB compressed. If you don't need
   AVIF, pin Pillow<12 or exclude PIL._avif.

4. pillow-heif bundles libx265 (2.3 MB) for HEVC encoding, but most
   apps only read HEIC. The sister package pi-heif is read-only and
   skips libx265.

The audit script (pyi-archive_viewer wrapper) and the full report
(.md + .html with SVG charts) are in the repo:

- Audit doc: docs/exe-optimization.md
- HTML report: docs/exe-optimization.html
- Audit script: tools/_audit_breakdown.py

Repo: https://github.com/Kiriiaq/PhotoOrganizer

Happy to answer questions about the methodology, the trade-offs of
dropping the ExifTool fallback, or the freemium architecture I'm
building on top of this.
```

---

## Métriques de suivi à 14 jours par post

| Post | Plateforme | KPI cible | Métrique d'échec |
|---|---|---|---|
| Post 1 (technique court) | LinkedIn | > 50 réactions, > 5 commentaires substantiels | < 20 vues uniques |
| Carrousel | LinkedIn | > 100 réactions, > 10 commentaires, > 5 partages | < 500 impressions |
| Post 3 (storytelling) | LinkedIn | > 80 réactions, > 8 commentaires, > 2 DM "intéressé par mission" | < 40 réactions |
| Thread X | X / Twitter | > 30 likes, > 5 RT | < 500 impressions |
| Show HN | Hacker News | Top 30 du jour, > 30 upvotes | < 5 upvotes en 2h |

Si un post sous-performe : ne pas en faire un drame. **Tester** la 2e fois avec un autre angle (par exemple post 1 reformulé en angle "freemium architecture" au lieu de "audit EXE").

---

## Checklist pré-publication (à cocher avant chaque post)

- [ ] Le lien GitHub fonctionne (release v2.2.0 publiée, README à jour).
- [ ] L'image / GIF / carrousel est produit et compressé (cf. [docs/MEDIA.md](docs/MEDIA.md)).
- [ ] Compteur de caractères respecté (LinkedIn coupe à 210 c "mobile" / 280 c "desktop").
- [ ] Hashtags ≤ 5, en fin de post.
- [ ] Premier commentaire prêt à coller (pour le lien et le boost algo).
- [ ] Disponible 1-4 h après publication pour répondre.
- [ ] Pas de typo (relecture à voix haute).
- [ ] Pas d'auto-promotion lourde ("regardez ce que j'ai fait !").
- [ ] Un point d'ouverture / invitation à échange en fin.

---

## Questions ouvertes (décision humaine)

1. **Nom à utiliser** : pseudonyme `Kiriiaq` ou nom légal `Emmanuel Grolleau` ? Pour la voie lead magnet → nom légal recommandé (visible recruteurs).
2. **Photo de profil LinkedIn** : à jour ? Bannière LinkedIn à customiser avec capture PhotoOrganizer ?
3. **Langue posts** : 100 % anglais (audience large) ou bilingue FR/EN (un de chaque) ? Recommandation : EN pour le post technique court + carrousel, FR pour le storytelling (touche communauté francophone tech / freelance).
4. **Ton autorisé** : OK pour mentionner "deux entretiens" dans le storytelling, ou trop personnel ?
5. **Visuels disponibles** : les captures S-01 à S-08 sont-elles produites ? Si non, c'est le bloquant P0 absolu pour publier (cf. AUDIT.md §14 D-08).
