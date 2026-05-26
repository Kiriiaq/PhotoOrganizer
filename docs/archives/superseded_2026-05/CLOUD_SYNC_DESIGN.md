---
status: design / étude — aucun code livré
created: 2026-05-19
audience: décideur produit + équipe technique
decision_required_by: T+6 mois après lancement Pro V1
---

# PhotoOrganizer Pro — Synchronisation cloud (étude design)

> **Statut** : étude pré-implémentation. Ce document évalue les options pour ajouter une synchronisation cloud post-organisation à PhotoOrganizer Pro. **Aucune décision n'est prise ici.** Le but est de fournir au futur "moi" (ou à un contributeur) une analyse honnête des trade-offs avant d'écrire la moindre ligne de code.
>
> Décision à prendre **après** le lancement Pro V1 (cf. [docs/MONETIZATION.md](MONETIZATION.md)) — quand les retours utilisateurs permettront de valider la demande.

---

## 1. Problème et opportunité

### Le cas d'usage typique

> *"J'organise mes photos sur mon PC. Je voudrais que la version organisée se retrouve automatiquement dans mon Backblaze / mon S3 / mon Google Drive pour sauvegarde et accès depuis mon laptop."*

C'est la suite logique de la feature **watch-folder** déjà livrée en V1 Pro : on attrape le fichier en local, on l'organise, puis on l'envoie au cloud. Sans cette étape, l'utilisateur doit configurer un outil tiers (rclone, Duplicati) en parallèle.

### Qui veut ça (segmentation marché)

| Segment | Besoin | Volume données | Disposé à payer |
|---|---|---|---|
| Particulier photo amateur | Sauvegarde simple "au cas où" | 100 Go - 2 To | non spécifiquement (déjà couvert par Google Photos / iCloud) |
| Photographe pro freelance | Archivage client + accès depuis 2-3 postes | 1-10 To | oui, payeur natif de la version Studio |
| Petit studio (2-5 personnes) | Bibliothèque partagée + sauvegarde | 5-50 To | oui, payeur natif Studio + sup. |
| Entreprise (>10 postes) | Politique de rétention + audit | 100+ To | hors cible PhotoOrganizer |

**Conclusion segmentation** : cible prioritaire = photographe pro + petit studio. Pas le particulier (qui a déjà Google Photos gratuit jusqu'à un certain volume) et pas l'entreprise (qui a Synology / NAS pro).

### Concurrence directe sur ce besoin

| Outil | Force | Faiblesse |
|---|---|---|
| **rclone** | Universel, gratuit, scriptable | CLI uniquement, courbe d'apprentissage, pas d'organisation EXIF |
| **Duplicati** | GUI, planning, chiffrement | Pas d'organisation, complexe à configurer |
| **Backblaze CB** | Idiot-proof | Tout ou rien, pas de filtre par EXIF |
| **Adobe Lightroom Cloud** | Intégration native | 10 €/mois minimum, vendor lock |

L'angle PhotoOrganizer : **"organisé + chiffré + envoyé"** en une seule action, pas trois outils chaînés.

---

## 2. Options de backend cloud

### 2.1 Comparatif

| Backend | Coût stockage (1 To) | Coût egress | API Python officielle | Auth | Adoption marché PhotoOrganizer |
|---|---|---|---|---|---|
| **Backblaze B2** | 6 $/mois | 1 $ / Go (gratuit jusqu'à 3× le stockage) | ✅ ``b2sdk`` | App key | ⭐⭐⭐⭐ |
| **AWS S3 Standard** | 23 $/mois | 0,09 $ / Go | ✅ ``boto3`` | Access key | ⭐⭐⭐ |
| **AWS S3 Glacier IR** | 4 $/mois | 0,03 $ / Go récupération | ✅ ``boto3`` | Idem | ⭐⭐ |
| **Cloudflare R2** | 15 $/mois | **0 $** | ✅ S3-compatible (``boto3``) | Access key | ⭐⭐⭐ |
| **Wasabi** | 7 $/mois | **0 $** (avec contrainte 90 j min) | ✅ S3-compatible | Access key | ⭐⭐ |
| **Google Drive** | 100 Go = 2 €/mois<br>2 To = 10 €/mois<br>5 To = 25 €/mois | inclus | ✅ ``google-api-python-client`` | OAuth 2.0 | ⭐⭐⭐⭐ |
| **OneDrive** | 1 To = 7 €/mois | inclus | ✅ Microsoft Graph SDK | OAuth 2.0 | ⭐⭐ |
| **iCloud Drive** | 2 To = 10 €/mois | inclus | ❌ pas d'API public | — | ⭐ |
| **Dropbox** | 2 To = 12 €/mois | inclus | ✅ ``dropbox`` SDK | OAuth 2.0 | ⭐⭐ |
| **Self-hosted (Nextcloud / WebDAV)** | propre serveur | propre bande passante | ✅ ``webdavclient3`` | basic auth | ⭐⭐⭐ (techies) |

⭐⭐⭐⭐⭐ recommandation MVP

### 2.2 Recommandation V1 cloud

Au lieu de "supporter 10 backends d'un coup", démarrer petit :

**MVP cloud** = **2 backends** :
1. **Backblaze B2** — meilleur rapport coût/qualité pour la sauvegarde froide. Cible photographe pro qui veut stocker pas cher.
2. **Google Drive** — couvre le cas du particulier qui a déjà un compte Google et veut "juste" envoyer ses photos organisées sur son cloud existant.

**V2 cloud** (si demande) : ajouter Cloudflare R2 (techies, 0 $ egress = attractif), Dropbox, WebDAV.

**Hors V1 / V2** : Glacier (trop spécifique), iCloud (pas d'API), OneDrive (faible audience photo).

### 2.3 Rationale du choix MVP

- **B2** = -75 % vs S3 sur stockage, egress généreux, l'auteur Backblaze (B2) est très open-source-friendly.
- **Google Drive** = barrière à l'entrée nulle pour le particulier, comme c'est OAuth on évite la friction "où je trouve mes API keys".

---

## 3. Architecture proposée

### 3.1 Couches

```
                ┌──────────────────────────────────────────┐
                │     src/photoorganizer_pro/cloud/        │
                │                                          │
                │   sync_engine.py  (orchestrateur)        │
                │   ├── policies.py    (rétention, filtres)│
                │   ├── encryption.py  (chiffrement client)│
                │   └── manifest.py    (état local SQLite) │
                │                                          │
                │   backends/                              │
                │     ├── base.py    (CloudBackend ABC)    │
                │     ├── b2.py      (Backblaze B2)        │
                │     └── gdrive.py  (Google Drive)        │
                └──────────────────────────────────────────┘
                                  │
                                  ▼  (intègre via)
                ┌──────────────────────────────────────────┐
                │   Plugin API (déjà livrée en V1)         │
                │                                          │
                │   cloud/cloud_plugin.py implémente       │
                │     BasePlugin.post_action()              │
                │     → enqueue upload                     │
                └──────────────────────────────────────────┘
```

**Décision architecture** : la synchro cloud ne s'intègre **pas** dans le core. Elle utilise la **Plugin API** déjà livrée, via un plugin officiel qui s'enregistre comme n'importe quel autre.

Avantages :
- Aucun couplage core ↔ cloud.
- Activable / désactivable comme un plugin (la GUI Settings expose un toggle).
- Si la feature ne décolle pas, on peut la retirer sans casser le core.

### 3.2 Le contrat ``CloudBackend``

```python
class CloudBackend(ABC):
    """Interface stable. Tout nouveau backend l'implémente."""

    name: str          # ex "backblaze_b2", "google_drive"
    display_name: str  # ex "Backblaze B2", "Google Drive"

    @abstractmethod
    def authenticate(self, credentials: dict) -> None: ...

    @abstractmethod
    def upload(self, local: Path, remote_key: str) -> UploadResult: ...

    @abstractmethod
    def exists(self, remote_key: str) -> bool: ...

    @abstractmethod
    def list_remote(self, prefix: str) -> Iterator[RemoteEntry]: ...

    @abstractmethod
    def delete(self, remote_key: str) -> bool: ...

    @abstractmethod
    def get_usage(self) -> Usage: ...  # quota / utilisation actuelle
```

### 3.3 ``sync_engine.py`` — orchestrateur

Responsabilités :

1. **Queue** des fichiers à uploader (SQLite WAL pour persister, survivre aux crashs).
2. **Throttling** : limite débit upload configurable (utile pour ne pas saturer une connexion résidentielle).
3. **Retry exponentiel** avec backoff sur erreur réseau / 429 / 503.
4. **Idempotence** : ne pas réuploader un fichier déjà présent (vérifié via ``exists()`` ou checksum dans le manifest local).
5. **Lifecycle** : démarrage / pause / reprise propre.

### 3.4 ``manifest.py`` — état local

Stocke pour chaque fichier organisé :
- chemin local
- chemin distant (remote_key)
- timestamp de dernier upload réussi
- hash du fichier (détecter changements après organisation)
- backend cible

Permet de :
- éviter les ré-uploads inutiles ;
- offrir un "status" GUI : combien de fichiers en attente, combien en erreur ;
- migrer vers un autre backend sans tout re-uploader (compare manifest vs liste distante).

Format : SQLite dans ``%LOCALAPPDATA%\PhotoOrganizer\cloud_manifest.db``.

### 3.5 ``encryption.py`` — chiffrement client-side

Optionnel mais **fortement recommandé** pour le segment pro (les photographes signent des NDA avec leurs clients).

| Approche | Pour | Contre |
|---|---|---|
| **Pas de chiffrement** | UX simple, fichiers visibles dans le navigateur cloud | Fuite si compte cloud compromis |
| **AES-256 GCM avec mot de passe** | Standard, lib ``cryptography`` | Si mdp perdu, données perdues |
| **Backblaze native server-side** | Zero-config | Backblaze a la clé technique |

Recommandation V1 : **opt-in AES-256 GCM**. Mot de passe stocké dans le keyring Windows via ``keyring`` lib. Documenté : *"si tu perds ce mot de passe, tu perds les fichiers chiffrés"*.

---

## 4. Sécurité

### 4.1 Stockage des credentials

| Backend | Format credentials | Stockage local |
|---|---|---|
| Backblaze B2 | App key ID + App key | Windows Credential Manager via ``keyring`` |
| Google Drive | OAuth refresh token | Idem |
| Cloudflare R2 | Access key + secret | Idem |

**Jamais** stocker les credentials dans un fichier JSON / config plain text à côté du binaire.

### 4.2 Permissions minimales

- **B2** : créer une App Key restreinte au bucket cible avec capabilities ``writeFiles`` + ``readFiles`` uniquement. Pas ``deleteFiles`` sauf si l'utilisateur active la suppression côté local → distante.
- **Google Drive** : OAuth scope ``drive.file`` (ne donne accès qu'aux fichiers créés par l'app), pas ``drive`` (= accès total). UX moins flexible mais privacy max.

### 4.3 Surface de risque

| Risque | Impact | Mitigation |
|---|---|---|
| Compte cloud compromis (mot de passe Google volé) | Tous les fichiers PhotoOrganizer accessibles | Chiffrement client opt-in |
| Code malveillant via plugin tiers qui aurait accès au CloudBackend | Exfiltration | API plugin ne donne PAS d'accès au backend ; seul ``cloud_plugin.py`` interne l'utilise |
| App key fuit (logs, screenshot, screenshare) | Upload sauvage | Permissions minimales (scope bucket) |
| Bug d'upload (move alors qu'on voulait copy) | Perte fichier local | Le local est toujours préservé ; sync = "ajouter au cloud", jamais "déplacer vers le cloud" |

### 4.4 RGPD

La synchro cloud transmet **les photos de l'utilisateur** vers un tiers (B2 / Google). Implications :
- La doc Pro doit dire **clairement** quel backend reçoit quoi.
- Le choix du backend appartient à l'utilisateur (pas de cloud "PhotoOrganizer-hosted" = on ne devient pas sous-traitant RGPD).
- Mise à jour de [docs/PRIVACY.md](PRIVACY.md) : nouvelle section "Cloud sync" avec processeurs déclarés.

---

## 5. UX dans la GUI

### 5.1 Activation

Onglet *Paramètres* → nouvelle section *"Synchronisation cloud (Pro)"*. Si pas de licence Pro → message d'info "Pro feature, upgrade here".

```
┌─ Synchronisation cloud ──────────────────────────────────┐
│ Backend  : ◉ Backblaze B2   ◯ Google Drive   ◯ Aucun     │
│ Bucket   : [ photoorganizer-emmanuel        ]            │
│ État     : ✓ connecté · 1 247 fichiers synchronisés      │
│            5,2 Go / 1 To utilisés                        │
│                                                          │
│ ☑ Chiffrer côté client (AES-256)                        │
│   Mot de passe stocké dans Windows Credential Manager   │
│                                                          │
│ ☑ Synchroniser automatiquement après chaque organisation│
│ Débit max : [ 10 Mo/s ▼ ]                                │
│                                                          │
│ [Tester la connexion] [Pause sync] [Voir manifeste]     │
└──────────────────────────────────────────────────────────┘
```

### 5.2 Feedback dans l'onglet Organisation

Pendant un batch, sous la progress bar :
```
Organisation : 247/1 200 fichiers (20%)
Cloud sync   : 198 uploads OK · 12 en file · 0 erreur
```

### 5.3 Gestion d'erreur

- Erreur réseau temporaire → retry silencieux, log dans le manifest.
- Erreur auth (token expiré) → notif système + ouvre Paramètres.
- Quota dépassé → notif + suspend automatique.

---

## 6. Pricing impact

| Option pricing pour la feature cloud | Pour | Contre |
|---|---|---|
| Inclus dans Pro Studio (49 €) + Lifetime (99 €) | UX simple, différenciation Personal vs Studio | Hausse perçue du Studio |
| Add-on séparé "PhotoOrganizer Cloud" 9 €/an | Modèle récurrent (rare pour le projet) | Friction supplémentaire |
| Inclus dans toutes les éditions Pro | Maximum de conversion | Réduit l'incitation Studio |

**Recommandation** : **inclus dans Studio + Lifetime**. La feature est lourde (estimation effort §7), il faut qu'elle motive l'upsell.

---

## 7. Estimation de l'effort

| Lot | Tâche | Effort |
|---|---|---|
| L1 — Fondations | ``CloudBackend`` ABC, ``manifest.py``, queue SQLite | 3-4 j |
| L2 — Backblaze B2 | Implémentation backend + auth + tests intégration | 2-3 j |
| L3 — Sync engine | Orchestrateur, retry, throttling | 2-3 j |
| L4 — Chiffrement | AES-256 GCM + keyring | 1-2 j |
| L5 — Plugin cloud | Intégration via Plugin API (``post_action``) | 1 j |
| L6 — UI Paramètres | Section dédiée + status realtime | 2-3 j |
| L7 — Google Drive | Implémentation OAuth + backend | 3-4 j |
| L8 — Doc + Privacy maj | docs/CLOUD_SYNC.md + maj PRIVACY | 1 j |
| L9 — Tests | Unitaires + 1 test intégration sandbox B2 | 2-3 j |

**Total V1 cloud (B2 only)** : **14-19 j-h** sans Google Drive.
**Total V1 cloud (B2 + GDrive)** : **17-23 j-h**.

À comparer aux 5-8 j-h pour la V1 Pro (batch + watch-folder + licence). La feature cloud est **2-3× plus lourde** que tout le V1 Pro réuni.

### Recommandation timing

- **Ne PAS lancer cloud en V1 Pro.** Risque d'enliser le lancement.
- **Évaluer après 3 mois de V1 Pro en vente** : si > 50 demandes utilisateurs sur la sync cloud → lancer V2. Sinon retirer du roadmap.

---

## 8. Métriques pour décider de lancer

À T+3 mois après V1 Pro :

| Signal | Décision |
|---|---|
| ≥ 20 demandes utilisateurs explicites "sauvegarde cloud" | GO V2 cloud (B2 only) |
| ≥ 50 demandes | GO V2 cloud (B2 + GDrive) |
| ≤ 5 demandes | Retirer du roadmap, autre priorité |
| Revente d'un compétiteur intégrant rclone | Reconsidérer notre angle |

---

## 9. Alternatives à explorer si on ne lance pas

Si l'effort cloud paraît trop important :

1. **Documenter rclone + PhotoOrganizer ensemble** dans `docs/cookbook/rclone-integration.md`. Coût : 1 j. Permet aux utilisateurs déjà familiers de chaîner les deux.

2. **Hook officiel pour outils tiers** : exposer un événement `file_organized(path, destination)` que rclone watch / SyncBackPro peut écouter via le watch-folder Windows natif. Coût : 0 j (déjà couvert par watch-folder qui dépose les fichiers à un endroit prévisible).

3. **Partnership** : recommander explicitement **Backblaze Personal Backup** comme solution complémentaire dans la doc. Affiliation possible (10-20 % de commission première année).

---

## 10. Décision attendue (humain, post-V1)

Après le lancement Pro V1 et 3 mois de données, répondre :

- [ ] La demande utilisateurs est-elle réelle (≥ 20 demandes explicites) ?
- [ ] Le compétiteur a-t-il pris l'angle "organisation + sync" entre-temps ?
- [ ] L'effort 14-19 j-h est-il bloquant pour la roadmap des autres modules ?
- [ ] Y a-t-il un photographe pro early adopter prêt à co-spécifier la feature ?

Si **3 oui sur 4** → ouvrir un ticket "Cloud V1 implementation" et démarrer L1. Sinon → archiver ce document dans `docs/archives/`.

---

## Annexes

### A. Pourquoi ne pas utiliser rclone en interne

Tentation initiale : embarquer rclone comme sous-process, l'app sert juste de wrapper.

Contre :
- Distribution : +20 Mo dans le bundle EXE.
- Compatibilité : rclone bouge, ses configs aussi. Coût de maintien long-terme.
- Différenciation : si on est "juste un wrapper rclone", l'utilisateur peut le faire lui-même (et il le sait).

Conclusion : **non**, on implémente nos propres backends avec les SDK officiels (``b2sdk``, ``google-api-python-client``). C'est plus de code mais c'est notre valeur ajoutée.

### B. Pourquoi pas un cloud "PhotoOrganizer-hosted"

Tentation : on héberge un bucket S3, l'utilisateur achète un quota chez nous. Modèle SaaS récurrent.

Contre :
- Coûts opérationnels : minimum 200 €/mois pour offrir 100 Go × 100 users.
- Statut RGPD : on devient sous-traitant. DPA, registre des traitements, etc.
- Risque : si on coule, les données utilisateurs partent.

Conclusion : **non**, on reste BYO-cloud (Bring Your Own Cloud). L'utilisateur reste maître de ses données et de ses dépenses cloud.

---

## Historique des révisions

| Date | Version | Auteur | Notes |
|---|---|---|---|
| 2026-05-19 | 1.0 | Kiriiaq | Document initial — étude post-lancement V1 Pro |
