# Inventaire des assets visuels à produire

> Ce fichier liste les captures, GIFs et vidéos à enregistrer pour rendre PhotoOrganizer présentable (README, page GitHub, posts LinkedIn, Product Hunt, Ko-fi).

Aucun de ces fichiers n'existe encore : tous les liens du `README.md` et de `PROJECT_OVERVIEW.html` pointent vers des chemins à remplir.

---

## 1. Captures d'écran (PNG, ratio 16:10 ou 4:3)

À produire à **1920×1200** ou **1600×1000** (rétrécir au besoin dans le README). Fond clair de préférence — meilleur rendu sur les pages GitHub.

| ID | Fichier cible | Sujet | Priorité |
|---|---|---|---|
| S-01 | `docs/media/screenshot-organize.png` | Onglet **Organisation** vide (fraîche ouverture) | 🔴 P0 — utilisé dans README |
| S-02 | `docs/media/screenshot-organize-running.png` | Onglet Organisation en cours d'exécution, progress bar à ~60 %, log scroll | 🔴 P0 |
| S-03 | `docs/media/screenshot-duplicates.png` | Onglet **Doublons** avec un scan terminé, groupes affichés | 🟡 P1 |
| S-04 | `docs/media/screenshot-history.png` | Onglet **Historique** avec 3-4 sessions et le bouton "Annuler" actif | 🟡 P1 |
| S-05 | `docs/media/screenshot-settings.png` | Onglet **Paramètres** complet, mode sombre + clair côte à côte (montage) | 🟢 P2 |
| S-06 | `docs/media/screenshot-dark.png` | App en mode sombre, onglet Organisation | 🟡 P1 |
| S-07 | `docs/media/screenshot-rename-template.png` | Zoom sur la zone "Renommer" avec un template visible et un exemple | 🟢 P2 |
| S-08 | `docs/media/screenshot-drag-drop.png` | Capture pendant un drag-and-drop d'un dossier sur l'app | 🟢 P2 |

---

## 2. GIFs animés (≤ 5 MB chacun)

Ratio 16:9, 1280×720 max, ≤ 15 fps, ≤ 10 secondes par GIF. Outil recommandé : [ScreenToGif](https://www.screentogif.com/) (gratuit, Windows).

| ID | Fichier cible | Sujet | Durée | Priorité |
|---|---|---|---|---|
| G-01 | `docs/media/demo-organize.gif` | Sélection dossier → choix critères → clic Organiser → progress → résultat | 8-10 s | 🔴 P0 |
| G-02 | `docs/media/demo-duplicates.gif` | Lancement détection doublons → groupes affichés → action quarantaine | 7-8 s | 🟡 P1 |
| G-03 | `docs/media/demo-rollback.gif` | Une opération → onglet Historique → clic Annuler → fichiers restaurés | 6 s | 🟡 P1 |
| G-04 | `docs/media/demo-dragdrop.gif` | Drag-and-drop d'un dossier sur la fenêtre | 4 s | 🟢 P2 |

---

## 3. Vidéo de présentation (MP4, ≤ 60 s)

Pour Product Hunt, LinkedIn, Ko-fi. Format vertical 9:16 secondaire pour reels/shorts.

| ID | Fichier cible | Sujet | Durée | Priorité |
|---|---|---|---|---|
| V-01 | `docs/media/intro.mp4` | Présentation horizontale 1920×1080 — pitch en voix off + démo flash des 4 onglets | 60 s | 🟡 P1 |
| V-02 | `docs/media/intro-vertical.mp4` | Version 1080×1920 pour LinkedIn / Reels | 30 s | 🟢 P2 |

Script de V-01 (proposition) :

```
00:00-00:05  Hook : "Vos photos sont en bordel. Vous avez 30 secondes."
00:05-00:15  Problème : montage 5 captures de dossiers nommés "DCIM", "20240612_171922_IMG_4567.JPG"
00:15-00:35  Solution : démo en accéléré de l'organisation par date + caméra
00:35-00:50  Bonus : détection doublons en 2 clics
00:50-00:60  Call to action : "Téléchargement libre sur github.com/Kiriiaq/PhotoOrganizer"
```

---

## 4. Icônes et logos (PNG transparent)

| ID | Fichier cible | Usage | Statut |
|---|---|---|---|
| L-01 | `assets/icons/icon.ico` (existe, 35 KB) | Icône Windows | ✅ OK |
| L-02 | `assets/icons/icon.png` (existe, **945 KB — sur-poids**) | Affichage UI | 🟡 À recompresser (cf. [exe-optimization.md](exe-optimization.md) F-05) |
| L-03 | `docs/media/logo.svg` | Logo vectoriel pour README et pages web | ⬜ À créer |
| L-04 | `docs/media/banner.png` | Bannière 1280×400 pour Product Hunt / GitHub social preview | ⬜ À créer |

---

## 5. Captures pour les posts LinkedIn (Phase 7)

Pour le carrousel 6-8 slides (1080×1350 portrait). À assembler dans Figma / Canva à partir des captures S-01 à S-08.

| Slide | Contenu | Source |
|---|---|---|
| 1 | Hook : "J'ai automatisé le tri de 10 000 photos" + screenshot avant/après | S-01 + capture d'un dossier en bordel |
| 2 | Problème en 1 phrase + chiffre | texte seul |
| 3 | Feature 1 : organisation multi-critères | S-02 |
| 4 | Feature 2 : détection doublons | S-03 |
| 5 | Feature 3 : rollback historique | S-04 |
| 6 | Stack technique (logos Python, CustomTkinter, PyInstaller) | texte + logos |
| 7 | Apprentissage clé (1 phrase) | texte seul |
| 8 | CTA : lien GitHub + Ko-fi | texte + QR code |

---

## 6. Checklist avant publication

Avant de pousser une release ou un post public, vérifier :

- [ ] S-01 et G-01 sont à jour (sinon le README a un lien cassé).
- [ ] Les captures sont en haute résolution et compressées (TinyPNG / Squoosh).
- [ ] Les GIFs pèsent moins de 5 MB (GitHub n'aime pas plus).
- [ ] Aucune capture ne révèle de chemin personnel ("D:\Photos perso de Manu") — utiliser des dossiers neutres.
- [ ] L'icône `icon.png` a été optimisée (cf. F-05).
- [ ] Le logo `logo.svg` existe pour la social preview GitHub.

---

## 7. Outils recommandés

- **Capture statique** : Win+Shift+S (outil capture Windows), ou ShareX.
- **Capture animée** : [ScreenToGif](https://www.screentogif.com/).
- **Capture vidéo** : OBS Studio, ou la capture intégrée à Windows 11.
- **Compression PNG** : [pngquant](https://pngquant.org/), [oxipng](https://github.com/shssoichiro/oxipng), ou [Squoosh](https://squoosh.app/).
- **Compression GIF** : [ezgif.com](https://ezgif.com/optimize) (en ligne).
- **Montage carrousel** : Figma (gratuit avec compte), Canva.
- **Voix off** : Audacity ou enregistrement smartphone + nettoyage.
