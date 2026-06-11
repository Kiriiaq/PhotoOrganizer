# PhotoOrganizer — Plateformes de distribution & visibilité

> **Post-pivot 2026-05-26.** Ce document remplace l'ancienne stratégie de
> distribution alignée sur le modèle freemium 19/49/99 €. L'ancien plan
> détaillé (3 produits Lemon Squeezy, calendrier 6 semaines) est récupérable
> via `git log -p -- docs/DISTRIBUTION.md`.

L'objectif de la distribution est double :

1. **Visibilité gratuite** = un volume suffisant de personnes voient le projet
   pour que les conversions essai → achat à 10 € puissent générer du revenu
   d'appoint (cible : 10-150 ventes sur 90 j).
2. **Lead magnet** = le projet sert de démonstrateur de compétences pour
   débloquer des missions freelance ou des opportunités d'embauche
   (cf. `docs/MONETIZATION.md` §1, voie complémentaire).

Les drafts à publier sont dans [LINKEDIN_DRAFTS.md](marketing/LINKEDIN_DRAFTS.md).

---

## 1. Plateformes par ordre de ROI estimé

| # | Plateforme | Audience | Effort | ROI relatif | Bloquant ? |
|---:|---|---|---|---|---|
| 1 | **GitHub Releases** | Devs, power-users | 30 min | ⭐⭐⭐⭐⭐ | Oui — pré-requis tout le reste |
| 2 | **LinkedIn (post pivot)** | Réseau personnel + 2e degré | 30 min/post | ⭐⭐⭐⭐ | Non |
| 3 | **Reddit r/photography** | Photographes amateurs | 20 min + 4 h modération | ⭐⭐⭐⭐ | Non |
| 4 | **Product Hunt** | Early adopters tech | 2 h prep + 6 h jour J | ⭐⭐⭐ | Non |
| 5 | **Show HN** | Devs sceptiques | 1 h prep + 4 h modération | ⭐⭐⭐ | Non |
| 6 | **Reddit r/datahoarder** | Niche cible parfaite | 20 min + 2 h modération | ⭐⭐⭐ | Non |
| 7 | **PyPI** | Devs Python | 1-2 h | ⭐⭐ | Non (cosmétique credibilité) |
| 8 | **AlternativeTo** | Recherche d'alternatives | 30 min | ⭐⭐ | Non |
| 9 | **dev.to / Hashnode** | Devs (article technique) | 3-4 h par article | ⭐⭐ | Non |
| 10 | **X / Twitter thread** | Public dev international | 1 h | ⭐ | Non (faible portée organique 2026) |

---

## 2. Calendrier de lancement court (3 semaines)

Tableau condensé. Détail dans [NEXT_STEPS.html](NEXT_STEPS.html) §F.

| Jour | Action | Pré-requis |
|---|---|---|
| **S-1** | Pré-requis : auto-entreprise, Privacy Policy publiée, S-01 + G-01 + S-02 dans `docs/media/`, setup Lemon Squeezy | NEXT_STEPS §D |
| **S+0 lundi** | Push tag v2.3.0 → release auto + page Lemon Squeezy en mode publié | NEXT_STEPS §E.1 |
| **S+0 mercredi** | LinkedIn post storytelling pivot (LINKEDIN_DRAFTS Format 1) | Release publique |
| **S+1 mardi** | Reddit r/photography (Format 6) | LinkedIn S+0 OK |
| **S+2 mardi 9h Paris** | Product Hunt (Format 4) + X thread (Format 8) | Compte PH > 7j |
| **S+2 mardi 16h Paris** | Show HN (Format 5) — pas le même créneau que PH | — |
| **S+3 lundi** | Reddit r/datahoarder (Format 7) | — |
| **S+5 mercredi** | LinkedIn post technique PyInstaller (Format 2) | — |
| **S+8 mercredi** | LinkedIn post portfolio (Format 3) | — |
| **Continu** | Réponse < 4 h sur tous les threads ouverts | — |

**Charge cumulée** : ~12-15 h sur 3 semaines, principalement de la modération
de fils. Aucune sur-publication (la fatigue éditoriale et le burn-out de
l'algorithme LinkedIn sont des écueils classiques).

---

## 3. Titres et descriptions par plateforme

### 3.1 GitHub Release v2.3.0

**Titre** : `v2.3.0 — Trial + unlock model · 10 free runs · 10€ lifetime`

**Description** :

```markdown
PhotoOrganizer adopts a "trial + unlock" model (Sublime Text style).

### Highlights
- 🆕 10 free organize runs per machine (counter signed HMAC SHA-256)
- 🔓 10€ lifetime unlock per PC (machine binding via MachineGuid + Volume Serial)
- 🛡️ Strict no-reissue policy on PC change (commercial gesture possible
       case-by-case, never promised upfront)
- 🧊 Pro modules (batch CLI, watch-folder, plugin API) deferred to v3.0+

### Downloads
- `PhotoOrganizer-2.3.0.exe` — main binary, Defender SmartScreen may warn
  on first run (not code-signed, see SECURITY.md)
- `PhotoOrganizer-2.3.0-debug.exe` — debug build with console
- `checksums-sha256.txt`

### What's not included
- ExifTool bundle (removed, GPL ambiguity gone — install separately via
  `winget install exiftool` if you need the fallback)

### Test plan
Run the EXE, organize 9 small folders → counter "Essai 9/10" appears.
On 10th success, app moves to "Limit reached" state. Modal opens. Pay
10€ on https://photoorganizer.lemonsqueezy.com, paste the emailed key.
```

### 3.2 Product Hunt

Tagline + description + first comment : dans
[LINKEDIN_DRAFTS.md Format 4](marketing/LINKEDIN_DRAFTS.md).

**Stratégie**:
- Submit un **mardi ou mercredi** entre 8 h et 9 h heure de Californie (= 17 h
  ou 18 h Paris). Cible : maximiser les 24 h de fenêtre de vote.
- Préparer 4-5 visuels : S-01 (capture statique), S-02 (modal d'activation),
  G-01 (GIF 10 s), screenshot mode sombre.
- Premier commentaire posté **dans les 30 s** après publication. Le ratio
  commentaires/votes dans la première heure pèse lourd dans le ranking.
- Disponible 4-6 h le jour J pour répondre aux commentaires.

### 3.3 Show HN

Titre + first comment : [LINKEDIN_DRAFTS.md Format 5](marketing/LINKEDIN_DRAFTS.md).

**Pièges à éviter**:
- ❌ Lien direct vers Lemon Squeezy (HN flag commercial).
- ❌ Demande explicite d'upvotes (HN ban à vie).
- ✅ Lien GitHub uniquement. Le binaire payant est mentionné dans le first
  comment.
- ✅ Heure : mardi/mercredi 7 h PT (= 16 h Paris).

### 3.4 Reddit

**Règles d'or**:
- **Lire la sidebar** du subreddit avant de poster (chaque sub a ses règles).
- **r/photography** interdit certains types de "self-promotion". Vérifier que
  "tool I built" est OK (généralement oui s'il y a une vraie value).
- **r/datahoarder** est plus permissif mais préfère les posts factuels et
  techniques.
- **Premier commentaire** sur ton propre post : ne pas re-coller le lien.
  Répondre à la première question légitime.

### 3.5 PyPI

**Pré-requis** : nom `photoorganizer` libre (à vérifier).

```bash
# Vérifier que le nom est libre
curl -s https://pypi.org/pypi/photoorganizer/json
# Si "Not Found" → libre. Sinon → adapter `name` dans pyproject.toml.

# Build
pip install --upgrade build twine
python -m build
ls dist/   # photoorganizer-2.3.0-py3-none-any.whl + .tar.gz

# Upload TestPyPI d'abord
twine upload --repository testpypi dist/*

# Puis prod
twine upload dist/*
```

PyPI n'apporte pas de ventes directes mais améliore la crédibilité auprès
des devs (le projet apparaît dans `pip search`, dans les badges, dans les
ranking pypi.io).

### 3.6 AlternativeTo

Recensement vs Lightroom, FastStone, IrfanView, ACDSee. Lien
[alternativeto.net/category/photography/photo-organizers/](https://alternativeto.net/category/photography/photo-organizers/).

Effort : 30 min de création de fiche. ROI : 2-10 visites/mois sur le moyen
terme, mais elles sont qualifiées (utilisateurs qui cherchent activement
une alternative).

---

## 4. KPI à suivre (90 jours)

| KPI | Source | Cible 90 j | Échec si < |
|---|---|---|---|
| GitHub stars | repo | 100-300 | 30 |
| Downloads EXE | Release insights | 500-2 000 | 100 |
| Ventes Lemon Squeezy | dashboard LS | 10-150 | 3 |
| Taux conversion télécharg → vente | calculé | 1-5 % | < 0,5 % |
| Demandes de réémission | email support | < 10 % des ventes | > 30 % |
| Avis externes (Reddit, dev.to, etc.) | recherche Google "PhotoOrganizer Kiriiaq" | ≥ 3 | 0 |

---

## 5. Décision à T+90 jours

| Si... | Alors... |
|---|---|
| Ventes > 100 | Continuer vers v3.0 (réactivation modules Pro batch/watch/plugins comme add-on payant séparé) |
| Ventes 20-100 | Optimiser pricing/copy, ajuster la limite gratuite (10 → 15 ?), basculer en mode B automatique pour l'envoi clé |
| Ventes < 20 | Garder la boutique en mode passif, repositionner le projet comme lead magnet portfolio (voie complémentaire MONETIZATION §1) |

---

## 6. Risques de distribution et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Compte Lemon Squeezy bloqué (anti-fraude) | Faible | Haut | Lire les CGU LS avant inscription, fournir un site web vitrine (README GitHub suffit). Backup : Gumroad. |
| Defender SmartScreen bloque l'EXE | Élevée | Modéré | Documenté dans README et SECURITY.md. Coût certificat code-sign ~80 €/an reporté à T+90 si traction. |
| Product Hunt low score → invisibilité | Élevée | Faible (effort 2 h) | Submit un jour calme, préparer un hunter influent si possible. Ne pas en faire la stratégie principale. |
| HN downvotes massifs | Modérée | Modéré | Soigner le first comment technique, accepter que HN soit imprévisible. |
| Reddit ban pour auto-promo | Modérée | Modéré | Lire chaque sidebar avant de poster, espacer les posts, jamais de cross-post simultané. |

---

## 7. Documents associés

- **Drafts de publication** : [LINKEDIN_DRAFTS.md](marketing/LINKEDIN_DRAFTS.md)
- **Stratégie monétisation** : [docs/MONETIZATION.md](MONETIZATION.md)
- **Procédure pas-à-pas** : [NEXT_STEPS.html](NEXT_STEPS.html)
- **Assets à produire** : [docs/MEDIA.md](MEDIA.md)
- **Privacy Policy** : [docs/PRIVACY.md](PRIVACY.md)
