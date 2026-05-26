# PhotoOrganizer — Stratégie de monétisation

> **Pivot 2026-05-26** : abandon de l'édition Pro séparée à 19/49/99 €. Adoption d'un
> modèle "trial + unlock" type Sublime Text / WinRAR : une seule app, 10 tris gratuits,
> 10 € lifetime, clé liée à 1 PC, aucune réémission.
>
> L'ancienne stratégie est archivée dans `docs/archives/superseded_2026-05/MONETIZATION_old.md`
> pour traçabilité.

---

## 1. Verdict en 30 secondes

| | Verdict |
|---|---|
| **Modèle** | Édition unique. Essai gratuit limité à **10 tris**. Au-delà : blocage par modal, déblocage par clé. |
| **Prix** | **10 € lifetime, 1 PC**. Aucun autre tier. |
| **Plateforme** | Lemon Squeezy (un seul produit). Clé envoyée par email (manuel jusqu'à ~10 ventes/sem, automatique ensuite). |
| **Politique** | Aucune réémission en cas de changement de PC / réinstall Windows / disque mort. Geste commercial possible au cas par cas, jamais promis. |
| **Effort de mise en place** | **2-3 jours-homme** (vs 5-8 j de l'ancien modèle). Compteur + modal + setup Lemon Squeezy. |
| **Revenu réaliste 12 mois** | **100 € – 1 500 €** selon traction. À 10 €/vente, 10 ventes/mois = 100 € (atteignable). 100 ventes/mois = 1 000 € (très bonne traction). |
| **Risque principal** | Niche modeste + concurrence gratuite (FastStone, IrfanView). Le pivot ne change pas ce constat. |

**À lire honnêtement** : ce projet n'a pas vocation à devenir un SaaS à 6 chiffres. L'objectif est :
1. **Vente directe** : couvrir les frais d'hébergement + faire un peu de revenu d'appoint.
2. **Lead magnet** : démontrer des compétences (Python desktop, packaging, tests, freemium maison) pour ouvrir des opportunités freelance ou d'embauche.

Les deux se cumulent sans conflit.

---

## 2. Pourquoi ce pivot

L'ancien modèle (Pro séparée 19/49/99 € avec batch CLI, watch-folder, plugins) avait quatre faiblesses :

1. **Codebase double** : maintenir une variante Pro nécessitait `build.py --pro`, des entry points dédiés, et 61 tests spécifiques Pro qui n'apportaient pas de valeur business directe.
2. **Testeur ≠ acheteur** : le visiteur testait la version gratuite, n'avait aucune idée de ce qu'il achetait, et devait croire la liste de features sur la page de vente.
3. **Friction d'entrée** : il fallait acheter et installer un autre binaire pour découvrir la Pro. Aucun essai gratuit de la valeur ajoutée.
4. **Positionnement flou** : 19 € pour 2 features (batch CLI + watch-folder) vs Lightroom à 12 €/mois → comparaison défavorable.

Le nouveau modèle inverse ces points :

| Avant | Après |
|---|---|
| Le visiteur lit la promesse Pro | Le visiteur **utilise** l'app gratuitement 10 fois et **sait** ce qu'il achète |
| 2 EXE à maintenir | 1 EXE |
| 3 tiers de prix (19/49/99) à arbitrer | 1 prix unique : 10 € |
| Pro = features additionnelles | Pro = **continuer à utiliser** l'outil qu'on connaît déjà |

Ce modèle est éprouvé : **Sublime Text**, **WinRAR**, **IDM**, **Beyond Compare** l'utilisent depuis 10-20 ans avec succès.

---

## 3. Mécanique du modèle (architecture)

### 3.1 Compteur d'usages

- **Stockage** : `%LOCALAPPDATA%\PhotoOrganizer\usage.dat`
- **Format** : JSON signé HMAC SHA-256 avec une clé embarquée dans l'EXE.
  ```json
  {
    "count": 7,
    "first_run": "2026-05-26T14:30:00Z",
    "machine_id": "ab12cd34...",
    "sig": "<hmac>"
  }
  ```
- **Anti-tampering** : la signature HMAC empêche l'utilisateur de modifier le `count` manuellement. Sans la clé HMAC (embarquée dans le binaire), impossible de regénérer une signature valide.
- **Anti-suppression** : si le fichier est supprimé, on le recrée avec `count=0`. **C'est la faille assumée**. Pour rendre le contournement plus pénible, on dupliquera le compteur dans le registre Windows `HKCU\Software\PhotoOrganizer` (Phase 1.5 si nécessaire).
- **Incrément** : uniquement après un tri **réussi** (un crash ou un Ctrl+C n'incrémente pas).
- **Warnings** : à `count == 8` et `count == 9` → bandeau jaune "Avant-dernier / dernier tri gratuit". À `count == 10` → tri normal puis bascule en état "limite atteinte". À `count == 11` (et au-delà) → blocage hard via modal.

### 3.2 Machine binding

- **Empreinte** : SHA-256 de `MachineGuid (HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid) + Volume Serial Number du disque système`.
- **Stable** sur un même PC tant que Windows n'est pas réinstallé et que le disque C: n'est pas changé.
- **Affichée à l'utilisateur** sous forme courte tronquée : `MAC-7A3F-9C2E` (8 chars hex visibles, suffit pour le support).
- **Stockée** dans `%LOCALAPPDATA%\PhotoOrganizer\license.dat` au format JSON signé HMAC :
  ```json
  {
    "key": "PROG-LIFE-...-...",
    "machine_id_bound": "ab12cd34...",
    "bound_at": "2026-05-27T10:00:00Z",
    "sig": "<hmac>"
  }
  ```

### 3.3 Clé de licence

- **Format actuel** (à conserver) : `PROG-LIFE-<YYYYMMDD>-<base64email>-<hmac>` (cf. `src/photoorganizer_pro/license/validator.py`). La date d'expiration reste à 30 ans = lifetime.
- **Émission** : universelle, sans empreinte machine au moment de la génération → flow Lemon Squeezy standard sans champ custom.
- **Activation 1er PC** : à la première saisie valide, l'app calcule le `machine_id` du PC courant et l'écrit dans `license.dat`. La clé devient *bound*.
- **Activation 2e PC** : si la même clé est saisie sur un autre PC, le `machine_id` calculé ne matche pas celui stocké → `LicenseInvalidError`. L'utilisateur voit le message "Cette clé est déjà liée à un autre ordinateur."
- **Implémentation** : extension du `validator.py` actuel — ajout d'un `LicenseInfo.machine_id_bound: Optional[str]` et d'une fonction `bind_license_to_machine(key, current_machine_id) -> None` qui réécrit `license.dat`.

### 3.4 Flow d'achat

```
1. Visiteur télécharge PhotoOrganizer.exe → essai gratuit
       │
       ▼
2. Utilise 10 fois → bandeau "limite atteinte"
       │
       ▼
3. Clique "Activer une licence" → modal inline (pas Toplevel)
       │
       ├── Champ "Coller la clé" + bouton "Activer"
       └── Bouton "Acheter une licence (10 €)" → https://photoorganizer.lemonsqueezy.com
       │
       ▼
4. Lemon Squeezy → checkout standard → email confirmation
       │
       ▼
5. Auteur reçoit notification "new order"
       │
       ├── Mode manuel (10 premières ventes) :
       │     python -m src.photoorganizer_pro.license.keygen \
       │         --email <client> --edition LIFE
       │     → copie la clé dans une réponse email
       │
       └── Mode automatique (à partir de S+30j) :
             webhook Lemon Squeezy → Cloudflare Worker
             → génère la clé → envoie via Resend/Brevo
       │
       ▼
6. Client reçoit la clé → la colle dans le modal → débloquée pour toujours sur ce PC
```

---

## 4. Pricing et politiques

### 4.1 Prix unique

| Édition | Prix | Inclus | Mises à jour |
|---|---|---|---|
| **Essai gratuit** | 0 € | App complète, 10 tris max | — |
| **PhotoOrganizer Unlimited** | **10 €** one-shot | App complète, 1 PC, illimité | **Toutes les versions futures gratuites, à vie** |

**Promo de lancement** : `EARLY30` = -30 % les 30 premiers jours (7 €). À évaluer selon traction.

### 4.2 Politique de réémission

| Cas | Politique officielle | Geste commercial possible |
|---|---|---|
| Changement de PC | Nouvelle clé à racheter | Possible 1× par client si fidèle, jamais promis publiquement |
| Réinstall Windows (MachineGuid change) | Nouvelle clé à racheter | Idem |
| Disque dur mort | Nouvelle clé à racheter | Idem |
| Disque dur restauré (image complète) | Marche probablement (machine_id préservé) | Pas besoin de re-acheter |
| Bug applicatif côté éditeur | Réémission gratuite | Garantie |

**Stratégie** : politique stricte affichée dans les CGV pour décourager le partage, indulgence ponctuelle pour préserver la satisfaction client. À 10 €, une mauvaise review coûte plus cher qu'une clé réémise gratuitement.

### 4.3 Remboursement

- **Loi consommateur EU** : 14 jours de droit de rétractation **sauf** pour les "contenus numériques fournis sur un support immatériel dont l'exécution a commencé avec l'accord du consommateur" (CGV à inclure : case à cocher au checkout).
- **Politique éditeur** : remboursement sans question dans les 14 jours via Lemon Squeezy. Au-delà : refus sauf cas exceptionnel.

---

## 5. Plan d'implémentation V1

### 5.1 Périmètre

| Étape | Livrable | Effort |
|---|---|---|
| 5.1.1 | `src/utils/licensing.py` — compteur + binding (signature HMAC, fonction `record_successful_organize()`, fonction `check_can_organize() -> (allowed, count, locked)`) | 3-4 h |
| 5.1.2 | Adaptation `src/photoorganizer_pro/license/validator.py` — ajout `machine_id_bound`, fonction `bind_license_to_machine()` | 1-2 h |
| 5.1.3 | Tests pytest `tests/functional/test_licensing.py` — 10 tris OK / 11e bloqué / clé bound = OK / clé bound ailleurs = refus / compteur signé tampering = reset | 2-3 h |
| 5.1.4 | Hook dans `src/ui/frames/organize_frame.py` avant `_do_organize()` (warning 8/9, blocage 11) | 1-2 h |
| 5.1.5 | Modal inline d'activation/blocage (pas Toplevel, cf. préférence projet) — champ clé + bouton activer + bouton acheter | 2-3 h |
| 5.1.6 | Badge global dans l'app (titre ou sidebar) : "Essai 7/10" / "Licence active · MAC-7A3F" | 30 min |
| 5.1.7 | Setup Lemon Squeezy : 1 produit, 1 page, lien copié dans le modal | 1 h |
| 5.1.8 | Mode manuel : procédure d'envoi de clé documentée dans `NEXT_STEPS.html` | 30 min |

**Total : 2-3 jours-homme.**

### 5.2 Flow d'envoi clé — Option A (manuel) vs Option B (automatique)

#### Option A — Manuel (10 premières ventes)

1. Lemon Squeezy notifie l'auteur par email à chaque vente.
2. L'auteur exécute en local :
   ```powershell
   python -m src.photoorganizer_pro.license.keygen `
       --email client@example.com --edition LIFE
   ```
3. Copie la clé dans la réponse au client (template email préparé).
4. **Avantage** : 0 infra, 0 dev backend.
5. **Limite** : tenable jusqu'à ~10 ventes/semaine. Au-delà, le temps de traitement devient pénible.

#### Option B — Automatique (au-delà de 10 ventes/semaine)

1. Webhook Lemon Squeezy → Cloudflare Worker (free tier) ou Vercel Function.
2. Le Worker :
   - Vérifie la signature du webhook
   - Extrait email
   - Génère la clé via un mini-portage JS de `keygen.py` (~30 lignes de code crypto)
   - Envoie un email via Resend (free tier 100 emails/jour) ou Brevo
3. **Effort** : 3-4 h pour quelqu'un qui a déjà déployé sur Cloudflare/Vercel.
4. **Coût** : 0 € jusqu'à des volumes significatifs.

**Recommandation** : commencer en mode A, basculer en B après confirmation du volume.

### 5.3 Setup Lemon Squeezy minimal

1. Créer le store `photoorganizer.lemonsqueezy.com` (cf. NEXT_STEPS §C).
2. Créer **un seul produit** :
   - Nom : *PhotoOrganizer — Lifetime Unlock*
   - Prix : **10 €** one-time
   - Description : reprendre le pitch du README
   - Image : `docs/media/screenshot-organize.png` (à produire)
   - Thank you page : "Tu vas recevoir ta clé par email d'ici 1 minute (mode manuel : sous 24 h). Si rien après 5 min/1 jour, écris à manugrolleau48@gmail.com avec ton numéro de commande."
3. CGV à inclure : politique de rétractation 14 jours, politique de réémission stricte.
4. Webhook : on_order_created → URL Worker (option B) ou requestbin (option A).

---

## 6. Vérifications juridiques (héritées, toujours valides)

### 6.1 Droits sur le code

- **Auteur unique** : Kiriiaq (Emmanuel Grolleau) selon `pyproject.toml` et `git log --pretty=%an | sort -u`.
- **Clauses employeur** : à auto-vérifier. Si une clause de cession des "œuvres créées" s'applique aux projets perso, demander une autorisation écrite avant de monétiser.
- **Pseudonyme Kiriiaq** : la monétisation exige un nom légal pour les factures. Lemon Squeezy demande nom + adresse + SIRET.

### 6.2 Licences des dépendances

| Dépendance | Licence | Compatible monétisation ? |
|---|---|---|
| customtkinter | CC0 | ✅ |
| Pillow | MIT-CMU | ✅ |
| exifread | BSD-3-Clause | ✅ |
| pillow-heif | BSD-3-Clause | ✅ (avec attribution) |
| requests | Apache-2.0 | ✅ |
| PyYAML | MIT | ✅ |
| darkdetect | BSD-3-Clause | ✅ |
| tkinterdnd2 | MIT | ✅ |
| plyer | MIT | ✅ |
| send2trash | BSD | ✅ |
| **ExifTool** (bundled) | **Perl Artistic OR GPL 1** | ⚠️ **À retirer** (cf. AUDIT_EXE F-01) |
| Python stdlib | PSF | ✅ |

**Action** : retrait ExifTool prévu (déjà tracké dans AUDIT_EXE F-01).

### 6.3 RGPD

- **App locale** : 0 collecte, 0 télémétrie.
- **Géocodage Nominatim** : envoie `(lat, lon)`, désactivable.
- **Lemon Squeezy** : Merchant of Record, gère RGPD côté checkout.
- **Privacy Policy** : `docs/PRIVACY.md` déjà rédigée, à publier sur GitHub Pages ou lien direct.

### 6.4 Fiscal France

- **Auto-entreprise (micro-entreprise)** suffit. Activité : "Édition de logiciels" (APE 5829C).
- **Franchise en base de TVA** : sous 36 800 €/an, pas de TVA à facturer.
- **Lemon Squeezy = Merchant of Record** : il facture la TVA aux clients et te reverse le net hors TVA.
- **Action** : créer l'auto-entreprise si pas déjà fait (gratuit, 5 min en ligne).

---

## 7. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Pas de traction (< 10 ventes/mois) | Moyenne | Modéré (effort 2-3 j) | Reste utilisable comme lead magnet portfolio |
| Contournement compteur (suppression fichier) | Élevée | Faible | Acceptable à 10 €. Duplication registre si nécessaire en v2.3.1 |
| Crack binaire (patch de la check) | Faible | Faible | Effort de crack > 10 €. Acceptable. |
| Support utilisateur sur réémissions | Moyenne | Modéré | CGV strictes affichées + gestes ponctuels |
| Client se plaint du binding 1 PC après réinstall | Moyenne | Modéré | FAQ claire dès la page de vente, réémission ponctuelle gratuite |
| Bug critique en production | Faible | Élevé | CI stricte + beta test 5-10 users avant lancement public |
| Concurrent gratuit ajoute notre feature | Moyenne | Modéré | Itération produit > marketing. Continuer à améliorer. |

---

## 8. Modules Pro reportés v3.0+

L'ancien projet "Pro" (`src/photoorganizer_pro/`) contient du code fonctionnel et testé qui est **gelé** mais conservé pour une éventuelle v3.0+ conditionnelle à la traction de la v2.x :

- **Batch CLI** (`cli/batch_organize.py`) — 335 LOC, 10 tests
- **Watch-folder** (`scheduler/watch_folder.py`) — 279 LOC, 12 tests
- **Plugin API** (`plugins/`) — 401 LOC, 25 tests
- **Système de licence** (`license/`) — base qui sera **adaptée**, pas jetée, pour gérer le compteur + binding v2.x

**Critères de réactivation v3.0+** :
- > 200 ventes de la v2.x sur 6 mois (= demande validée)
- > 5 demandes explicites de batch / watch / plugins par mois (= besoin identifié)
- Disponibilité de 2-3 semaines pour livrer une v3.0 propre

Tant que ces critères ne sont pas réunis, ces modules restent en sourdine :
- Entry points pip commentés dans `pyproject.toml`
- Tests skippés avec `@pytest.mark.skip(reason="Deferred to v3.0+")`
- Fichiers gardés intacts pour réactivation rapide

---

## 9. Recommandation finale en 3 puces

1. **Implémenter le flow trial+unlock en 2-3 j** : compteur + modal + badge + Lemon Squeezy en mode manuel. Lancement v2.3.0.
2. **Cumuler avec la voie "lead magnet portfolio"** : un post LinkedIn structuré expliquant le pivot et la mécanique trial+unlock est en soi un démonstrateur de compétences (architecture, pragmatisme business, dev solo).
3. **Pré-requis non négociables AVANT lancement** :
   - Confirmer droits IP (clause employeur, pseudonyme → nom légal).
   - Retirer ExifTool bundlé (AUDIT_EXE F-01) → élimine ambiguïté GPL.
   - Créer auto-entreprise si pas déjà fait.
   - Produire S-01 + G-01 (screenshot + GIF démo).
   - Publier `docs/PRIVACY.md` accessible publiquement.

---

## 10. Questions ouvertes (décision humaine)

1. **Statut juridique** : auto-entreprise déjà créée ?
2. **Promo de lancement** : on tente `EARLY30` (-30 % les 30 premiers jours) ou prix plein direct ?
3. **Option A vs B** : on démarre tout de suite avec l'automatisation (Cloudflare Worker) ou on attend de valider le volume avec le mode manuel ?
4. **Faut-il un mode "essai prolongé"** sur demande explicite (ex : un photographe pro qui veut tester sur 50 photos avant d'acheter) ? Ou on tient strictement les 10 ?
5. **Communication du pivot** : faut-il un post public expliquant le changement de modèle (transparent et différenciant) ou silencieux ?

---

## Annexe — Historique des décisions

| Date | Décision | Source |
|---|---|---|
| 2026-05-19 | Voie freemium 19/49/99 € validée comme stratégie initiale | AUDIT.md Phase 5 |
| 2026-05-19 | Livraison modules Pro V1.1 (batch + watch + plugins) | Commit `5730f099` |
| **2026-05-26** | **Pivot vers édition unique 10 € / 10 tris / 1 PC** | **Session de cadrage Claude Code 2026-05-26** |
