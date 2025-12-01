# 📸 PhotoOrganizer

**Version 1.0** - Outil professionnel pour organiser, analyser et gérer vos collections de photos

![Python](https://img.shields.io/badge/python-3.11+-green.svg) ![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg) ![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)

---

## ✨ Fonctionnalités

### 📊 Analyse Complète
- **45 formats supportés** : Images (JPG, PNG, HEIC, etc.), RAW (CR2, NEF, RW2, etc.), Vidéos (MP4, MOV, etc.)
- **Extraction EXIF complète** : Date, appareil photo, GPS, dimensions
- **Statistiques détaillées** : Distribution par type, date, appareil, localisation
- **Recommandations intelligentes** : Suggestions d'organisation basées sur vos données

### 🗂️ Organisation Intelligente
- **Par date** : AAAA-MM-JJ ou AAAA/MM/JJ
- **Par appareil photo** : Canon EOS 5D, LUMIX GH5, etc.
- **Par localisation GPS** : Coordonnées géographiques
- **Organisation multicouche** : Combinez plusieurs critères
- **Copier ou déplacer** : Préservez vos originaux

### 🎨 Interface Moderne
- **CustomTkinter** : Interface élégante et professionnelle
- **Barre de progression** : Suivi en temps réel
- **Fenêtre de résultats** : Affichage détaillé avec scroll
- **Contrôles intuitifs** : Analyser, Organiser, Annuler

---

## 🚀 Installation et Utilisation

### Exécutable Windows (Recommandé)
```bash
1. Aller dans: dist\
2. Double-cliquer sur: PhotoManager.exe
3. C'est tout! L'application se lance
```

### Mode Python
```bash
# Installer les dépendances
pip install customtkinter exifread piexif Pillow darkdetect

# Lancer l'application
cd PhotoOrganizerV5
python main.py
```

---

## 📖 Guide d'Utilisation

### Analyser des Fichiers

1. **Sélectionner le dossier source**
   - Cliquer sur "Parcourir" à côté de "Dossier source"
   - Choisir le dossier contenant vos photos

2. **Choisir les types de fichiers**
   - ☑ Images (.jpg, .jpeg, .png, etc.)
   - ☑ RAW (.raw, .arw, .cr2, .nef, .rw2, .dng, etc.)
   - ☑ Vidéos (.mp4, .mov, .avi, etc.)
   - ☑ Recherche récursive (inclure les sous-dossiers)

3. **Lancer l'analyse**
   - Cliquer sur **"Analyser les fichiers"**
   - Attendre la progression (peut prendre 30-60s pour 600+ fichiers)
   - Consulter les résultats dans la fenêtre modale

**Résultats affichés:**
- 📁 Nombre total de fichiers
- 📷 Types de fichiers et extensions les plus courantes
- 📅 Distribution par date (année, mois)
- 📸 Appareils photo détectés
- 🌍 Données GPS disponibles
- 💡 Recommandations d'organisation

---

### Organiser des Fichiers

1. **Sélectionner les dossiers**
   - **Source** : Dossier contenant vos photos à organiser
   - **Destination** : Dossier où seront copiées/déplacées les photos

2. **Choisir les critères d'organisation**
   - ☑ **Par date** : Organiser par AAAA-MM-JJ ou AAAA/MM/JJ
   - ☑ **Par appareil photo** : Créer des dossiers par appareil
   - ☑ **Par emplacement** : Organiser selon les coordonnées GPS

3. **Options avancées**
   - ☑ **Organisation multicouche** : Combiner plusieurs critères
   - ☑ **Copier au lieu de déplacer** : Préserver les fichiers originaux
   - Glisser-déposer pour définir l'ordre des critères

4. **Lancer l'organisation**
   - Cliquer sur **"Organiser les fichiers"**
   - Consulter le rapport d'organisation

**Exemple de résultat:**
```
Destination\
├── 2024-10\
│   ├── Canon EOS 5D\
│   │   ├── IMG_0001.jpg
│   │   └── IMG_0002.CR2
│   └── LUMIX GH5\
│       ├── P1200001.RW2
│       └── P1200002.JPG
└── 2024-11\
    └── Canon EOS 5D\
        └── IMG_0003.jpg
```

---

### Annuler une Opération

- Cliquer sur **"Annuler l'opération"** (bouton rouge)
- L'opération s'arrête immédiatement
- Les boutons sont automatiquement réactivés

---

## 📦 Formats Supportés (45 formats)

### Images (15)
`.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tiff` `.tif` `.webp` `.heic` `.heif` `.svg` `.psd` `.jfif` `.jp2` `.avif`

### RAW (17)
`.raw` `.arw` `.cr2` `.cr3` `.nef` `.orf` `.rw2` `.dng` `.3fr` `.raf` `.pef` `.srw` `.sr2` `.x3f` `.mef` `.iiq` `.rwl`

### Vidéos (13)
`.mp4` `.mov` `.avi` `.mkv` `.wmv` `.flv` `.webm` `.3gp` `.m4v` `.mpg` `.mpeg` `.mts` `.ts` `.vob`

---

## 🛠️ Créer l'Exécutable

### Avec PyInstaller
```bash
# Installer PyInstaller
pip install pyinstaller

# Créer l'exécutable
pyinstaller --noconfirm --onefile --windowed --name "PhotoManager" \
  --hidden-import "PIL._tkinter_finder" \
  --hidden-import "customtkinter" \
  --hidden-import "darkdetect" \
  --hidden-import "exifread" \
  --hidden-import "piexif" \
  main.py

# L'exécutable se trouve dans: dist\PhotoManager.exe
```

**Caractéristiques de l'exécutable:**
- Taille: ~101 MB
- Mode fenêtré (sans console)
- Autonome (toutes dépendances incluses)
- Portable (pas d'installation requise)

---

## 🔧 Dépannage

### Problème: Aucun fichier trouvé
**Solutions:**
- Vérifier que le dossier source existe
- Cocher les bonnes cases (Images/RAW/Vidéos)
- Activer "Recherche récursive" si photos dans sous-dossiers

### Problème: Les résultats ne s'affichent pas
**Solutions:**
- Attendre la fin de l'analyse (100%)
- Vérifier qu'il n'y a pas d'erreur dans la console

### Problème: L'organisation ne fonctionne pas
**Solutions:**
- Vérifier qu'un dossier de destination est sélectionné
- Vérifier qu'au moins un critère est coché
- Vérifier les permissions d'écriture

---

## 🤝 Contribuer

Les contributions sont les bienvenues! Pour contribuer:

1. Fork le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

### Signaler un Bug
Ouvrez une [issue GitHub](https://github.com/Kiriiaq/PhotoOrganizer/issues) avec:
- Description du bug
- Étapes pour reproduire
- Comportement attendu
- Version Python et OS

### Contact
📧 Email: manugrolleau48@gmail.com
☕ Ko-fi: https://ko-fi.com/kiriiaq

---

## 📋 Historique des Versions

### Version 1.0 (2025-12-01) - Stable
**Nouveautés:**
- ✅ Interface moderne avec CustomTkinter
- ✅ Analyse complète avec 45 formats
- ✅ Fenêtre de résultats défilable avec icônes
- ✅ Organisation multicouche
- ✅ Verrouillage des boutons pendant opérations
- ✅ Bouton annulation fonctionnel
- ✅ Exécutable Windows autonome

**Corrections:**
- ✅ Ajout de `ProgressManager.reset()`
- ✅ Correction import `datetime`
- ✅ Création des widgets de progression
- ✅ Ajout de `ScrollableFrame` manquante
- ✅ Réactivation boutons après annulation

---

## 💻 Architecture Technique

### Structure du Projet
```
PhotoOrganizerV5/
├── main.py                  # Point d'entrée
├── core/
│   ├── file_operations.py   # Opérations sur fichiers
│   └── metadata.py          # Extraction EXIF
├── gui/
│   ├── app.py              # Application principale
│   └── frames/
│       └── file_organization_frame.py  # Interface
├── utils/
│   ├── config_manager.py   # Configuration
│   ├── file_utils.py       # Utilitaires fichiers
│   ├── progress_utils.py   # Gestion progression
│   └── ui_utils.py         # Interface (ScrollableFrame)
└── dist/
    └── PhotoManager.exe    # Exécutable (101 MB)
```

### Technologies
- **Python 3.11+** - Langage principal
- **CustomTkinter** - Interface moderne
- **ExifRead** - Extraction EXIF
- **Piexif** - Manipulation EXIF
- **Pillow** - Traitement images
- **DarkDetect** - Détection thème système
- **PyInstaller** - Création exécutable

---

## 📄 Licence

Ce projet est sous **licence MIT avec Commons Clause** - voir le fichier [LICENSE](LICENSE) pour les détails complets.

### Résumé de la Licence

**MIT License + Commons Clause**

✅ **Ce que vous POUVEZ faire:**
- Utiliser le logiciel gratuitement (usage personnel et commercial interne)
- Modifier le code source
- Distribuer le logiciel
- Créer des œuvres dérivées
- Contribuer au projet

❌ **Ce que vous NE POUVEZ PAS faire:**
- Vendre le logiciel lui-même
- Vendre des services hébergés basés principalement sur ce logiciel
- Facturer pour du support/consulting où la valeur principale est ce logiciel

**En résumé:** Gratuit pour tous usages sauf la vente directe du logiciel ou de services basés dessus.

```
MIT License with Commons Clause - Copyright (c) 2025 PhotoOrganizer

Permission is granted for free use, modification, and distribution,
but NOT for selling the software or software-as-a-service offerings.
```

Voir [LICENSE](LICENSE) pour tous les détails et exemples d'utilisation autorisée.

---

## 🙏 Remerciements

- **CustomTkinter** - Interface moderne
- **ExifRead** - Extraction métadonnées
- **Pillow** - Manipulation images
- **Communauté Python** - Bibliothèques incroyables

---

<div align="center">

**Développé avec ❤️ pour la communauté photo**

Par Kiriiaq - [Ko-fi](https://ko-fi.com/kiriiaq) | [Email](mailto:manugrolleau48@gmail.com)

[⬆ Retour en haut](#-photoorganizer)

</div>
