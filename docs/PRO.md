# PhotoOrganizer Pro — Guide utilisateur

> Documentation des fonctionnalités de l'édition Pro (payante, licence propriétaire). Pour le cœur gratuit open-source, voir [README.md](../README.md).

---

## Qu'est-ce que PhotoOrganizer Pro

PhotoOrganizer Pro étend le cœur gratuit avec deux modules destinés aux utilisateurs avancés et professionnels :

1. **Batch CLI** (`photo-organizer-pro-batch`) — organiser depuis le terminal, scripter, planifier.
2. **Watch-folder** (`photo-organizer-pro-watch`) — surveiller un dossier et organiser automatiquement les nouveaux fichiers.

Pricing : 19 € (personnelle) / 49 € (studio, 3 PC) / 99 € (lifetime). Paiement unique, licence offline, pas d'abonnement.

Voir [LICENSE-PRO](../LICENSE-PRO) pour les termes complets.

---

## Acheter une licence

1. Aller sur la page produit Lemon Squeezy : **https://photoorganizer.lemonsqueezy.com** *(à publier)*.
2. Choisir l'édition (Personnelle / Studio / Lifetime).
3. Payer (carte ou PayPal). Lemon Squeezy gère la TVA EU automatiquement.
4. Tu reçois un email avec :
   - Ta **clé de licence** (format : `PROG-PERS-20271231-...`)
   - Le lien de téléchargement de `PhotoOrganizerPro.exe`
   - La facture PDF

---

## Activer la licence

Deux méthodes au choix.

### Méthode 1 — Via la GUI (Pro Edition)

1. Lancer `PhotoOrganizerPro.exe` (téléchargé via le lien email).
2. Ouvrir l'onglet **Paramètres** → section **Licence**.
3. Coller la clé reçue par email dans le champ **Clé de licence**.
4. Cliquer **Activer**.
5. La GUI confirme l'édition et la date d'expiration. Les modules Pro deviennent disponibles.

### Méthode 2 — Manuel (avancé)

Si tu utilises uniquement les CLI :

```powershell
# Windows PowerShell
$key = "PROG-PERS-20271231-dXNlckBleGFtcGxlLmNvbQ==-xxxxxx"
$file = "$env:LOCALAPPDATA\PhotoOrganizer\license.dat"
New-Item -ItemType Directory -Force -Path (Split-Path $file) | Out-Null
Set-Content -Path $file -Value $key -Encoding ASCII
```

Le fichier `license.dat` est lu automatiquement par les CLI au démarrage.

---

## Module 1 — Batch CLI

### Cas d'usage

- Lancement nocturne par Task Scheduler Windows / cron.
- Pipeline CI/CD qui réorganise un dépôt photos partagé.
- Scripts personnalisés combinant organisation + autres traitements.

### Commande de base

```bash
photo-organizer-pro-batch organize \
    --source "D:/Photos/import" \
    --dest "D:/Photos/library" \
    --by-date --by-camera \
    --copy
```

### Toutes les options

```
organize [options]
  --source, -s        Dossier source à scanner (requis)
  --dest, -d          Dossier destination (requis)
  --create-dest       Créer la destination si absente
  --recursive, -r     Scan récursif (défaut)
  --no-recursive      Désactiver récursif
  --by-date           Organiser par date EXIF
  --by-camera         Organiser par modèle d'appareil
  --by-gps            Organiser par coordonnées GPS
  --date-format       "year", "year/month" (défaut), "year/month/day"
  --copy              Copier (défaut)
  --move              Déplacer au lieu de copier
  --rename TEMPLATE   Template renommage. Variables : {date:%Y-%m-%d}, {counter:04d}, {model}, {ext}
  --dry-run           Simulation sans modifier les fichiers
```

### Exemples concrets

**1. Routine quotidienne (Task Scheduler Windows)**

```bash
photo-organizer-pro-batch organize \
    -s "D:/Camera Imports" \
    -d "D:/Photos/Archive" \
    --by-date --date-format "year/month" \
    --move
```

Crée un trigger Task Scheduler à minuit : Action "Démarrer un programme" → `photo-organizer-pro-batch` avec ces arguments.

**2. Template de renommage avancé**

```bash
photo-organizer-pro-batch organize \
    -s "D:/Photos/shoot-2026-05" \
    -d "D:/Clients/Mariage_Dupont" \
    --by-date \
    --rename "Dupont_{date:%Y%m%d}_{counter:04d}"
```

Donne `Dupont_20260515_0001.jpg`, `Dupont_20260515_0002.jpg`, etc.

**3. Mode dry-run avant le grand soir**

```bash
photo-organizer-pro-batch organize -s D:/Photos -d D:/Sorted --by-date --by-camera --dry-run
```

Affiche ce qui serait fait sans rien écrire. Utile pour valider les options avant le vrai run.

### Codes de sortie

| Code | Sens |
|---:|---|
| 0 | Succès complet (tous les fichiers traités) |
| 1 | Au moins un fichier en échec |
| 2 | Licence manquante / expirée |
| autres | Erreur shell / argument invalide |

---

## Module 2 — Watch-folder

### Cas d'usage

- Photographe qui importe en continu depuis sa carte SD.
- Bureau partagé où plusieurs personnes déposent des fichiers à organiser.
- Workflow "drop and forget" : tu glisses, c'est rangé.

### Commande de base

```bash
photo-organizer-pro-watch \
    --source "D:/Camera Imports" \
    --dest "D:/Photos/library" \
    --by-date --by-camera --copy
```

Ctrl+C pour arrêter.

### Toutes les options

```
photo-organizer-pro-watch [options]
  --source, -s     Dossier source à surveiller (requis)
  --dest, -d       Dossier destination organisé (requis)
  --by-date        (défaut ON)
  --no-by-date
  --by-camera
  --by-gps
  --date-format    "year/month" (défaut)
  --copy           (défaut)
  --move
  --debounce N     Délai (s) avant traitement après détection. Défaut : 5
```

### Comportement détaillé

- À chaque nouveau fichier détecté dans `--source` (récursif), attend `--debounce` secondes (laisse le temps à un transfert SD card de finir), puis organise vers `--dest`.
- Seuls les formats reconnus déclenchent une action (45 extensions, alignées avec le core).
- Si `watchdog` est installé (extras `pro` du pyproject), utilise une vraie surveillance temps réel. Sinon retombe sur un polling toutes les 10 s.

### Démarrer comme service Windows

Pour qu'il tourne en permanence en arrière-plan, utiliser [NSSM](https://nssm.cc/) :

```powershell
# Installation (une fois)
choco install nssm

# Création du service
nssm install PhotoOrganizerWatch "C:\Program Files\PhotoOrganizer\PhotoOrganizerPro.exe"
nssm set PhotoOrganizerWatch AppParameters "watch -s D:\Imports -d D:\Library --by-date"
nssm set PhotoOrganizerWatch DisplayName "PhotoOrganizer Watch-Folder"
nssm set PhotoOrganizerWatch Description "Organise automatiquement les nouvelles photos déposées dans D:\Imports"
nssm start PhotoOrganizerWatch
```

Désinstallation : `nssm remove PhotoOrganizerWatch confirm`.

---

## Mise à jour

- Personnelle : mises à jour mineures (2.2.x → 2.2.y) gratuites pendant 1 an. Majeures (2.x → 3.x) : 50 % du prix.
- Studio : 2 ans de mises à jour mineures gratuites.
- Lifetime : tout gratuit, à vie.

Tu reçois un email à chaque release majeure (Personnelle / Studio sous garantie ; Lifetime à vie).

---

## Support

- Email : <manugrolleau48@gmail.com> avec sujet `[PhotoOrganizer Pro] <ta question>`.
- Réponse cible : 5 jours ouvrés (Personnelle) / 2 jours ouvrés (Studio prioritaire).
- Issues GitHub : utiliser pour les bugs du **core open-source uniquement** (les modules Pro ne sont pas open-source, le bug-tracker public ne les couvre pas).

---

## Désactivation / désinstallation

- Supprimer le fichier `%LOCALAPPDATA%\PhotoOrganizer\license.dat` pour libérer le siège de licence (utile si tu veux migrer la licence sur un autre PC).
- Désinstaller l'EXE Pro depuis Programmes Windows comme n'importe quelle app.
- Le cœur gratuit (`PhotoOrganizer.exe`) reste fonctionnel.

---

## FAQ

**Q : Puis-je utiliser la licence Personnelle sur mon laptop ET mon desktop ?**
R : Pas simultanément. La Personnelle = 1 PC actif. La Studio = jusqu'à 3 PC simultanés.

**Q : Que se passe-t-il si je ne renouvelle pas après 1 an ?**
R : La version que tu as installée continue de fonctionner indéfiniment. Tu n'as juste plus accès aux nouvelles versions mineures gratuites.

**Q : Le Pro fonctionne-t-il sans internet ?**
R : Oui, complètement. La licence est validée offline. Aucun serveur n'est contacté.

**Q : Comment migrer ma licence vers un nouveau PC ?**
R : Copier le fichier `%LOCALAPPDATA%\PhotoOrganizer\license.dat` vers le même chemin sur le nouveau PC, ou ré-entrer la clé manuellement via la GUI.

**Q : Y a-t-il un essai gratuit ?**
R : Pas pour le moment. Mais le cœur gratuit (open-source, Apache-2.0) couvre 95 % des besoins individuels — essaie-le avant d'envisager le Pro.

**Q : Combien de temps prend l'activation ?**
R : Immédiat. La licence est validée en local par signature, sans contact serveur.

**Q : Je veux contribuer au Pro / corriger un bug. Possible ?**
R : Le Pro est propriétaire et fermé. Pour contribuer, vise le cœur (cf. [CONTRIBUTING.md](../CONTRIBUTING.md)).
