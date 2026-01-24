# 📷 PhotoOrganizer v2.0.0

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

**Organiseur intelligent de photos et vidéos** avec interface moderne CustomTkinter.

Organisez automatiquement vos médias par **date**, **appareil photo** ou **localisation GPS**.

![PhotoOrganizer Screenshot](docs/screenshots/main_window.png)

---

## ✨ Fonctionnalités

### 🗂️ Organisation Intelligente
- **Par date** : Structure année/mois/jour personnalisable
- **Par appareil** : Samsung, iPhone, Pixel, GoPro, DJI, etc.
- **Par localisation** : Géocodage inverse automatique
- **Multicouche** : Combinez plusieurs critères

### 🔍 Détection des Doublons
- Algorithmes MD5, SHA1, SHA256
- Mode rapide (hash partiel)
- Suppression sécurisée

### ↩️ Annulation (Rollback)
- Historique complet des opérations
- Annulation individuelle ou totale
- Restauration des fichiers d'origine

### ⚡ Performance
- Cache intelligent des métadonnées
- Traitement multithread
- Support de grandes collections

### 📁 Formats Supportés

| Catégorie | Extensions |
|-----------|------------|
| **Images** | JPG, PNG, GIF, BMP, TIFF, WebP, AVIF |
| **HEIC/HEIF** | HEIC, HEIF (iPhone, etc.) |
| **RAW** | ARW, CR2, CR3, NEF, ORF, DNG, RAF, etc. |
| **Vidéos** | MP4, MOV, AVI, MKV, WMV, WebM |

---

## 🚀 Installation

### Prérequis
- Python 3.9 ou supérieur
- pip (gestionnaire de packages)

### Installation rapide

```bash
# Cloner le dépôt
git clone https://github.com/Kiriiaq/PhotoOrganizer.git
cd PhotoOrganizer

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python main.py
```

### Installation des dépendances optionnelles

```bash
# Support HEIC (iPhone)
pip install pillow-heif

# Support RAW complet
pip install rawpy
```

---

## 📖 Utilisation

### Lancement
```bash
python main.py
```

### Interface

L'application comporte 4 onglets principaux :

1. **📁 Organisation** : Organisez vos fichiers
2. **🔍 Doublons** : Trouvez les fichiers en double
3. **📜 Historique** : Consultez et annulez les opérations
4. **⚙️ Paramètres** : Configurez l'application

### Organisation des fichiers

1. Sélectionnez le **dossier source** contenant vos photos
2. Sélectionnez le **dossier destination**
3. Choisissez les **critères d'organisation** :
   - Par date de prise de vue
   - Par appareil photo
   - Par localisation GPS
4. Configurez les **options** :
   - Copier ou déplacer
   - Format de date
   - Types de fichiers
5. Cliquez sur **Organiser**

### Détection des doublons

1. Sélectionnez un dossier à analyser
2. Choisissez l'algorithme de hash (MD5 recommandé)
3. Cliquez sur **Rechercher**
4. Examinez les résultats
5. Supprimez les doublons si souhaité

---

## 📁 Structure du Projet

```
PhotoOrganizer/
├── main.py                 # Point d'entrée
├── requirements.txt        # Dépendances
├── README.md              # Documentation
├── LICENSE                # Licence MIT
│
├── core/                  # Logique métier
│   ├── metadata/          # Extraction EXIF, GPS, dates
│   │   ├── exif_extractor.py
│   │   ├── gps_processor.py
│   │   ├── date_extractor.py
│   │   └── camera_detector.py
│   │
│   └── operations/        # Opérations fichiers
│       ├── file_manager.py
│       ├── organizer.py
│       └── duplicate_finder.py
│
├── ui/                    # Interface utilisateur
│   ├── app.py             # Application principale
│   └── frames/            # Frames/onglets
│       ├── organize_frame.py
│       ├── duplicates_frame.py
│       ├── history_frame.py
│       └── settings_frame.py
│
├── utils/                 # Utilitaires
│   ├── config.py          # Configuration
│   ├── cache.py           # Cache métadonnées
│   └── logger.py          # Logging
│
└── tests/                 # Tests unitaires
```

---

## ⚙️ Configuration

La configuration est stockée dans :
- **Windows** : `%APPDATA%/PhotoOrganizer/config.json`
- **Linux/Mac** : `~/.config/PhotoOrganizer/config.json`

### Options principales

| Option | Description | Défaut |
|--------|-------------|--------|
| `theme` | Thème (dark/light/system) | dark |
| `default_action` | Copier ou déplacer | copy |
| `cache_enabled` | Cache des métadonnées | true |
| `geocoding_enabled` | Géocodage inverse | true |

---

## 🔧 API de Géocodage

PhotoOrganizer utilise OpenStreetMap Nominatim par défaut (gratuit, limité).

Pour un géocodage plus fiable, vous pouvez configurer une clé API PositionStack :

1. Créez un compte sur [positionstack.com](https://positionstack.com/)
2. Copiez votre clé API
3. Collez-la dans Paramètres > API & Services

---

## 🗺️ Roadmap

### Version 2.1.0
- [ ] Prévisualisation des images
- [ ] Éditeur de métadonnées
- [ ] Export des statistiques

### Version 2.2.0
- [ ] Reconnaissance faciale (optionnel)
- [ ] Tags et catégories personnalisées
- [ ] Synchronisation cloud

### Version 3.0.0
- [ ] Interface web
- [ ] API REST
- [ ] Mode serveur

---

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Forkez le projet
2. Créez votre branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add AmazingFeature'`)
4. Pushez vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

---

## 📄 Licence

Ce projet est sous licence **MIT** - voir le fichier [LICENSE](LICENSE) pour plus de détails.

**Ce logiciel peut être utilisé commercialement.**

---

## 👏 Crédits

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Interface moderne
- [Pillow](https://python-pillow.org/) - Traitement d'images
- [ExifRead](https://github.com/ianare/exif-py) - Lecture EXIF
- [OpenStreetMap](https://www.openstreetmap.org/) - Géocodage

---

## 📧 Contact

- **GitHub** : [@Kiriiaq](https://github.com/Kiriiaq)
- **Issues** : [Signaler un bug](https://github.com/Kiriiaq/PhotoOrganizer/issues)

---

*Fait avec ❤️ par la communauté PhotoOrganizer*
