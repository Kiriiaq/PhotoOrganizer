# PhotoOrganizer — Drafts publication (post-pivot 2026-05-26)

> Modèle économique acté : **édition unique, 10 tris d'essai, 10 € lifetime, 1 PC, aucune réémission**.
> L'ancienne version de ce fichier (drafts freemium 19/49/99 €) est récupérable via `git log -p -- LINKEDIN_DRAFTS.md`.

Tous les drafts ci-dessous sont **prêts à coller** après revue finale.
Ordre conseillé de publication : `S+0 LinkedIn pivot` → `S+1 Reddit` → `S+2
Product Hunt + LinkedIn tech` → `S+3 Show HN`.

> ⚠️ **À vérifier avant de publier quoi que ce soit** (état au 2026-07-03) :
> 1. **La boutique Lemon Squeezy n'existe pas encore.** Plusieurs drafts citent
>    `photoorganizer.lemonsqueezy.com`. **Ne pas publier de draft contenant ce
>    lien tant que le store n'est pas en ligne** (cf. NEXT_STEPS §B). En
>    attendant, publier uniquement les drafts « GitHub only » (Reddit, Show HN)
>    ou retirer la ligne lemonsqueezy.
> 2. Version publiée = **v2.3.1** (la v2.3.0 a été retirée : ses clés ne
>    validaient pas). Toute mention de version doit dire v2.3.1.
> 3. Chiffres de référence à jour : **211 tests core**, EXE **~30 MB**,
>    **Pillow ≥ 12.2** (montée pour 7 CVE — ne PAS écrire « pin Pillow <12 »).

---

## Format 1 — LinkedIn (post pivot, storytelling)

**Quand** : jour de la release v2.3.1 (S+0).
**Cible** : ton réseau LinkedIn (devs, indie hackers, PM, photographes).
**Longueur** : 1500-1900 caractères (sweet spot LinkedIn 2026).

```
J'ai mis PhotoOrganizer en vente. Pas de version "Pro" séparée. Pas de
paywall sur des cases à cocher. Une seule app, 10 tris gratuits, 10 € à vie.

J'ai d'abord codé une édition Pro séparée (batch CLI, watch-folder,
plugins) à 19/49/99 €. 61 tests verts, deux binaires à maintenir,
calendrier de lancement freemium classique.

J'ai abandonné. Trois raisons :

→ Le testeur de la version gratuite ne testait PAS ce qu'il achèterait.
  Il devait croire la liste de features sur la page de vente. Friction +
  défiance.

→ Maintenir deux codebases pour un projet solo, c'est doubler la dette
  technique sans doubler le revenu.

→ "Achète pour débloquer une case à cocher" est moins convaincant que
  "tu as essayé, ça marche, continue à l'utiliser".

J'ai pivoté vers le modèle Sublime Text / WinRAR / IDM : édition unique,
trial limité par usage. Détails techniques que j'ai dû régler en 3 jours :

— Compteur signé HMAC SHA-256 dans %LOCALAPPDATA% pour empêcher la
  modification triviale du nombre de tris restants.
— Machine binding via SHA-256(MachineGuid + Volume Serial) pour limiter
  à 1 PC sans serveur d'auth.
— Modal d'activation inline (zéro Toplevel) pour rester cohérent avec
  l'UX de l'onglet Organisation.
— Politique stricte affichée, indulgence ponctuelle assumée en interne.

Aucun DRM offline n'est incassable. L'objectif n'est pas l'incassabilité
mais "contournement plus chiant que payer 10 €". Pour 10 €, c'est
largement assez.

Apache-2.0 sur le code, paiement sur le binaire. Premier feedback
bienvenu — surtout celui qui dérange.

🔗 GitHub : github.com/Kiriiaq/PhotoOrganizer
🔗 Lifetime 10 € : photoorganizer.lemonsqueezy.com
```

**Hashtags suggérés** : `#IndieHackers #Python #SoftwareEngineering #Bootstrapping`

---

## Format 2 — LinkedIn (post technique, audit EXE)

**Quand** : S+2 ou S+5, après le pic d'attention du pivot.
**Cible** : devs Python, packaging, PyInstaller.

```
PyInstaller en --onefile, ~30 MB aujourd'hui. Cible de l'audit : 22 MB.

Audit complet de mon EXE PhotoOrganizer publié en open-source. Actions
ordonnées par ROI, métriques mesurées :

— F-01 : ExifTool bundlé retiré (déjà fait, ~34 MB décompressés)
   Ambiguïté GPL + fallback subprocess jamais déclenché en pratique.
   Gain immédiat sans régression fonctionnelle.

— F-02 : --strip + UPX (~5 MB)
   Strip enlève les symboles debug, UPX compresse l'EXE. Trade-off :
   démarrage +200 ms (acceptable pour onefile).

— Le contre-exemple assumé : Pillow.
   L'audit proposait de pinner Pillow <12 pour ne pas embarquer libavif
   (~1,8 MB inutilisés). Sauf que Pillow 11.3 traîne 7 CVE. J'ai fait
   l'inverse : Pillow ≥ 12.2 (patché), +1,8 MB acceptés. La sécurité
   passe avant la taille — un audit de poids n'annule pas un audit de
   sécurité (pip-audit --strict en CI).

— F-08 : requests → urllib stdlib (~3 MB, planifié)
   Le projet fait 1 GET vers Nominatim. urllib.request suffit.

— Autres : lazy imports, --exclude-module, datas filtrés (~3 MB cumulés)

Détail dans docs/exe-optimization.md du repo.

Mesurer avant d'optimiser, sinon on bouge des octets pour rien. PyInstaller
fournit un .toc en mode --debug=imports qui dit exactement ce qui pèse.

#Python #PyInstaller #Windows #Engineering
```

---

## Format 3 — LinkedIn (post portfolio / lead magnet)

**Quand** : S+5 ou S+8, pour cumuler avec le revenu direct.
**Cible** : recruteurs tech, CTO.

```
Ce que j'ai construit avec PhotoOrganizer, sur mon temps libre, en
Python pur :

→ Application desktop Windows complète (CustomTkinter, 4 onglets,
  drag-and-drop, toasts) ;
→ Pipeline EXIF multi-source avec fallback (Pillow + exifread +
  pillow-heif) sur 45 formats incluant RAW ;
→ Détection de doublons multi-algorithme (MD5, SHA-1, Blake3 si dispo)
  avec scan parallèle et cache SQLite 2-tier ;
→ Quarantaine réversible + historique par session avec rollback complet
  (recréation des dossiers vidés inclus) ;
→ Géocodage inverse OpenStreetMap Nominatim avec respect strict de
  l'usage policy (1 req/s, User-Agent identifiable, désactivable) ;
→ 211 tests pytest organisés en 5 catégories (smoke/functional/perf/
  stress/volume), avec un audit sécurité pip-audit --strict en CI ;
→ CI GitHub Actions (lint ruff + tests sur Windows, build EXE release
  auto sur tag git) ;
→ Système trial+unlock maison avec HMAC SHA-256 et machine binding
  (MachineGuid + Volume Serial), pour monétiser un binaire sans serveur
  d'auth ;
→ Packaging PyInstaller --onefile (~30 MB) documenté dans un audit
  de taille reproductible (cible 22 MB), sécurité arbitrée au-dessus
  du gain d'octets (Pillow ≥ 12.2 pour 7 CVE plutôt que le pin <12).

Apache-2.0 sur GitHub, librement consultable et forkable. Édition
activable à 10 € à vie pour ceux qui veulent l'utiliser sans limite
sur leur PC personnel.

Si vous cherchez du dev Python orienté product, je suis disponible
pour discuter.

Lien : github.com/Kiriiaq/PhotoOrganizer
```

---

## Format 4 — Product Hunt

**Tagline (60 chars max)** :

```
Automate photo organization by date, camera & GPS. Free trial.
```

**Description (260 chars)** :

```
PhotoOrganizer is a Windows desktop app that sorts thousands of photos
by EXIF date, camera model, and GPS location. Reversible duplicate
detection. 10 free runs to test, then 10€ lifetime unlock per PC.
Code open-source under Apache-2.0.
```

**First comment** (à coller dans les 30 secondes après publication) :

```
Hey Product Hunt 👋

I built PhotoOrganizer over a year of evenings to solve my own problem:
20 years of photos on a single drive, dumped from 12 different devices,
none consistently tagged.

What it does:
• Reads EXIF metadata (Date / Camera / GPS / 45 formats including RAW)
• Sorts by criteria you choose, cumulatively (e.g. Year > Camera > City)
• Detects duplicates with MD5/SHA-1/Blake3 + reversible "quarantine"
• Full session rollback if you change your mind

What it doesn't do:
• Upload anything anywhere (100% local)
• Track you (no telemetry)
• Subscribe you to anything (one payment, lifetime)

The business model is "shareware" style: 10 free runs to test on real
files, then a 10€ one-time unlock if you want to keep using it. One PC,
no renewals. The code itself stays Apache-2.0 — you can fork it and
build whatever you want.

Happy to answer technical questions about:
— PyInstaller onefile optimization (37 → 22 MB audit ongoing)
— Offline HMAC + machine binding for indie software monetization
— CustomTkinter for production-grade desktop UIs in 2026

Honest feedback (including critical) welcomed.
```

---

## Format 5 — Show HN

**Titre** :

```
Show HN: PhotoOrganizer – shareware-style photo organizer with offline HMAC trial counter
```

**Lien** : `https://github.com/Kiriiaq/PhotoOrganizer` (PAS la page Lemon Squeezy, HN flag commercial).

**First comment** (à coller immédiatement) :

```
Hi HN. Solo dev, weekend project that grew. Posting the technical side
because the product side is niche (Windows photo organizer).

Some pieces that might be interesting to discuss:

1. Trial counter that resists trivial tampering, no server.
   - %LOCALAPPDATA%\PhotoOrganizer\usage.dat with HMAC-SHA256 envelope.
   - Embedded secret in the PyInstaller binary.
   - Delete the file → reset to 0 (trivially circumventable, accepted
     at the 10 € price point).
   - Edit the JSON count without regenerating HMAC → reset to 0.
   - Bonus: file copied from another PC is rejected because the
     machine_id is part of the signed payload.

2. Machine binding without an auth server.
   - sha256(MachineGuid || '|' || VolumeSerial_C).
   - First successful activate_key() writes the current machine_id
     to license.dat. Subsequent loads compare and reject if different.
   - Caveat: Windows reinstall invalidates the license (policy: no
     re-issuance, the user buys again — explicitly stated upfront).

3. PyInstaller --onefile size audit, ~30 MB now, 22 MB target.
   - ExifTool bundle removed (~34 MB uncompressed, GPL ambiguity gone).
   - --strip + UPX (-5 MB, +200ms startup).
   - requests → urllib.request (-3 MB, planned).
   - The one I reversed: the audit said "pin Pillow <12" to drop the
     unused libavif (~1.8 MB). But 11.3 carries 7 CVEs, so I went the
     other way — Pillow >=12.2, +1.8 MB, security over size. A size
     audit doesn't get to override a security audit (pip-audit --strict
     runs in CI).

4. Single codebase + trial gate beats "free vs Pro" dual binary for
   solo dev maintenance. Sublime Text / WinRAR were right.

Code: Apache-2.0. The HMAC secret is gitignored (placeholder shipped
in the public repo); real production secret is injected at build time
and only exists on my disk + my password manager.

Happy to take all questions. Especially the "how is this not trivially
crackable" ones — short answer: it is, and that's fine at 10 €.
```

---

## Format 6 — Reddit r/photography

**Subreddit** : `r/photography`, `r/photos`.
**Quand** : S+1.
**Ton** : factuel, pas marketing.

**Titre** :

```
Made a free Windows app to organize photos by date / camera / GPS — 10 free runs, 10€ lifetime
```

**Corps** :

```
Hey r/photography,

After fighting with my own 20-year photo archive (different cameras,
different cards, different naming chaos), I wrote a small Windows app
to sort everything by EXIF data.

What it does:
- Reads EXIF / IPTC from 45 formats (JPG, HEIC, RAW from Canon /
  Sony / Nikon / Fuji, plus video formats)
- Sorts into folders by date, camera model, or GPS-derived city,
  cumulatively (Year > Camera > City works)
- Detects duplicates with hashing — moves them to a reversible
  quarantine, not the actual trash
- Lets you roll back any session if you don't like the result

What it doesn't do:
- Upload anything (no cloud, no servers, no account)
- Track you (no telemetry)
- Edit your files unless you confirm

Business model honestly: 10 free runs to test it on real folders, then
10€ one-time unlock per PC if you want to keep using it. The source
code is Apache-2.0 on GitHub — you can fork it and build your own
binary for free.

GitHub: https://github.com/Kiriiaq/PhotoOrganizer

Genuine feedback welcome, especially "this doesn't handle X format I
shoot in". The 45-format list is from EXIF library coverage, not from
extensive RAW testing — I shoot Sony, so other brands' RAWs are less
battle-tested.
```

---

## Format 7 — Reddit r/datahoarder

**Subreddit** : `r/datahoarder`, `r/PostCollapse`.
**Quand** : S+2.
**Ton** : storytelling longue durée.

**Titre** :

```
[Tool] Sorted 50 TB of photos by EXIF in a weekend — open-sourced the tool
```

**Corps** :

```
TL;DR — Windows app I built, Apache-2.0 on GitHub, sorts photos
recursively by EXIF metadata. 10 free runs, 10€ lifetime unlock if
you want it without limits. https://github.com/Kiriiaq/PhotoOrganizer

The story:

I had a 6 TB NAS, photos from 2003 to 2026, multiple cameras, multiple
phones, multiple "imports" from old hard drives, zero consistent
naming. Lightroom catalogs got corrupted twice. Manual sorting was
tried, abandoned, retried, re-abandoned.

What I wanted:
- A tool that reads EXIF and creates folders like
  D:/Photos/2017/03/2017-03-15_Sony-A7III_Paris
- Without uploading anything anywhere
- Reversible (so I can undo a bad run on 30k files)
- With duplicate detection that doesn't permanently delete

Found a few candidates, all had at least one dealbreaker:
- ACDSee: Windows-only AND paid AND no per-run rollback
- Lightroom: subscription, "library" obsession, slow on first scan
- ExifTool CLI: works but you write a Perl one-liner per use case
- Various Python scripts on GitHub: rarely maintained, no UI, no
  duplicate handling

So I wrote one. Single-file EXE (~30 MB, size optimization to 22 MB
ongoing), no installer, no admin rights, no telemetry.

Detail likely interesting to r/datahoarder:
- Quarantine instead of send2trash for duplicates — you can recover
  anything within a session.
- History persists across runs (SQLite cache) so you can rollback
  3 weeks later if you find a missing photo.
- Hash multi-algo with fallback: Blake3 if available (2-3x faster),
  else SHA-1, else MD5. Cache so re-scans are instant.
- Geocoding via OpenStreetMap Nominatim, respects their 1 req/sec
  usage policy, fully disableable.

I'm running a "10 free runs then 10€ lifetime unlock per PC" model
(Sublime Text style). The code is fully open-source under Apache-2.0,
so if you don't want to pay you can compile it yourself with
PyInstaller. No DRM crusade.

Feedback welcomed, especially "your tool ate my photos" stories
(spoiler: shouldn't, but I want to hear it if it does).
```

---

## Format 8 — Twitter / X thread

**Quand** : en parallèle de Product Hunt (S+2).
**Style** : 4-6 tweets numérotés.

```
1/ I shipped PhotoOrganizer with a "trial + unlock" model instead of a
   freemium-by-feature one.

   10 free runs. 10€ lifetime. 1 PC. No re-issuance.

   Here's why I think this is the right model for indie desktop apps
   in 2026 👇

2/ Freemium-by-feature problems for solo devs:
   - Maintain 2 binaries (free + pro)
   - Maintain 2 test suites (61 extra pro tests)
   - Visitors can't test the value they're buying
   - "Pay to unlock checkboxes" feels worse than "pay to keep using"

3/ Trial + unlock solves all four:
   - 1 binary, 1 test suite, 1 release pipeline
   - Visitor tests the FINAL product on real files
   - At purchase, they're buying continuity not a list of features

4/ Technical bits I had to solve:
   - HMAC-signed counter in %LOCALAPPDATA% (resists trivial tampering)
   - Machine binding via SHA256(MachineGuid + VolumeSerial)
   - Inline activation modal (no Toplevel — UX consistency)
   - Strict "no re-issuance on PC change" policy, indulgent in practice

5/ This is Sublime Text's model, WinRAR's model, IDM's model.
   Proven for 20 years. Why did I try freemium-by-feature first?
   Because that's what current SaaS literature recommends, and that
   advice doesn't transfer to single-payment desktop apps.

6/ Apache-2.0 on the code, paid on the binary.
   github.com/Kiriiaq/PhotoOrganizer
   photoorganizer.lemonsqueezy.com

   AMA on the technical or business side.
```

---

## Calendrier suggéré (3 semaines, faible intensité)

| Jour | Action | Plateforme |
|---|---|---|
| **S+0 lundi** | v2.3.1 publiée sur GitHub (fait) + boutique Lemon Squeezy en ligne | GitHub + LS |
| **S+0 mercredi** | Format 1 (LinkedIn pivot storytelling) | LinkedIn |
| **S+1 mardi** | Format 6 (Reddit r/photography) | Reddit |
| **S+2 mardi 9h Paris** | Format 4 (Product Hunt) + Format 8 (X thread) | PH + X |
| **S+2 mardi 16h Paris** | Format 5 (Show HN) | HN |
| **S+3 lundi** | Format 7 (Reddit r/datahoarder) | Reddit |
| **S+5 mercredi** | Format 2 (LinkedIn technique PyInstaller) | LinkedIn |
| **S+8 mercredi** | Format 3 (LinkedIn portfolio) | LinkedIn |
| **Continu** | Réponse < 4 h sur tous les threads ouverts | tous |

---

## Conseils de modération de fil

- **Product Hunt** : être disponible 4-6 h après publication. Le ranking PH dépend du ratio commentaires/votes dans la première heure. Ne pas demander d'upvotes — illégal sur PH.
- **Show HN** : répondre aux questions techniques **précisément**. La qualité des réponses auteur pèse plus que le contenu original dans le ranking HN.
- **Reddit** : zéro lien dans les premiers commentaires de ton propre post. Reddit pénalise les nouveaux comptes qui linkent agressivement.
- **LinkedIn** : commenter 2-3 fois sur ton propre post dans les 24h amplifie la portée organique (réveille l'algorithme).

---

## Notes anti-bad-faith

Quelques objections que tu vas recevoir et comment y répondre courtement :

- **"C'est crackable"** → "Oui. À 10 € le crack ne vaut pas l'effort. Si vous voulez patcher l'EXE, le code est sous Apache-2.0, faites-le."
- **"Sublime Text c'est nag screen, pas blocage"** → "Vrai. Tradeoff assumé : blocage clair > frustration ambiguë."
- **"Pourquoi pas plus cher ?"** → "Volume > marge. À 10 € j'élimine la résistance d'achat de l'utilisateur lambda."
- **"Politique aucune réémission est trop dure"** → "Affichée dans les CGV. Geste commercial possible au cas par cas, pas promis publiquement."
- **"Apache-2.0 + binaire payant c'est bizarre"** → "Le code est libre. Le binaire compilé que je distribue est mon travail packagé, payant. Vous pouvez compiler le vôtre."
