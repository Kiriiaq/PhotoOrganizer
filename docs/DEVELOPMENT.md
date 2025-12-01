# 🛠️ Guide de Développement - PhotoOrganizer

> Documentation technique complète pour développeurs et contributeurs

**Développé par Kiriiaq**
- 📧 Email : manugrolleau48@gmail.com
- ☕ Ko-fi : https://ko-fi.com/kiriiaq
- 🐙 GitHub : https://github.com/Kiriiaq/PhotoOrganizer

---

## 📁 Structure du Projet

```
PhotoOrganizerV5/
│
├── 📂 core/                       # Logique métier principale
│   ├── metadata.py                # Extraction métadonnées EXIF/GPS
│   ├── file_operations.py         # Organisation et traitement de fichiers
│   └── format_conversion.py       # Conversion de formats d'images
│
├── 📂 gui/                        # Interface graphique
│   ├── app.py                     # Interface classique (Tkinter)
│   ├── app_modern.py              # Interface moderne (CustomTkinter)
│   ├── app_ultra_modern.py        # Interface ultra-moderne ⭐
│   ├── frames/                    # Composants d'interface
│   │   └── file_organization_frame.py
│   └── widgets/                   # Widgets personnalisés
│       └── scrollable_frame.py
│
├── 📂 utils/                      # Utilitaires
│   ├── file_utils.py              # Utilitaires fichiers
│   ├── hash_utils.py              # Calcul de hash
│   ├── metadata_cache.py          # Cache métadonnées
│   ├── preview_utils.py           # Prévisualisation images
│   ├── progress_utils.py          # Barres de progression
│   └── rollback_utils.py          # Système d'annulation
│
├── 📂 resources/                  # Ressources
│   ├── icons/                     # Icônes (ico, png)
│   └── assets/                    # ExifTool et binaires
│
├── 📂 docs/                       # Documentation
│   ├── DEVELOPMENT.md             # Ce fichier
│   └── GETTING_STARTED.md         # Guide démarrage rapide
│
├── 📂 .github/                    # Configuration GitHub
│   ├── FUNDING.yml                # Dons
│   └── ISSUE_TEMPLATE/            # Templates d'issues
│
├── main.py                        # Point d'entrée classique
├── main_modern.py                 # Point d'entrée moderne
├── main_ultra_modern.py           # Point d'entrée ultra-moderne ⭐
├── config.py                      # Configuration automatique
├── .env                           # Variables d'environnement
├── requirements.txt               # Dépendances Python
├── PhotoManager.spec              # Configuration PyInstaller
└── README.md                      # Documentation principale
```

---

## 🎯 Architecture et Modules

### Core Modules

#### `core/metadata.py`
Extraction et manipulation de métadonnées d'images.

**Fonctions principales** :
```python
get_exif_data(file_path)         # Lire métadonnées EXIF
extract_image_date(file_path)    # Extraire date de prise de vue
get_camera_info(file_path)       # Informations appareil photo
get_gps_coordinates(exif_data)   # Coordonnées GPS
```

**Dépendances** :
- PyExifTool (wrapper Python pour ExifTool)
- exifread (lecture EXIF pure Python)
- pillow-heif (support HEIF/HEIC)

#### `core/file_operations.py`
Opérations sur fichiers et organisation.

**Fonctions principales** :
```python
organize_files(...)              # Organisation automatique
find_duplicates(...)             # Détection de doublons
batch_rename(...)                # Renommage par lot
analyze_directory(...)           # Analyse statistique
```

### GUI Modules

#### Trois Interfaces Disponibles

1. **Interface Classique** (`gui/app.py`)
   - Tkinter standard
   - Légère et compatible
   - Pour systèmes anciens

2. **Interface Moderne** (`gui/app_modern.py`)
   - CustomTkinter
   - Design moderne
   - Thèmes clair/sombre

3. **Interface Ultra-Moderne** (`gui/app_ultra_modern.py`) ⭐ **RECOMMANDÉE**
   - CustomTkinter avancé
   - Sidebar de navigation
   - Cartes statistiques
   - Animations fluides

### Utilitaires

#### `utils/hash_utils.py`
Calcul de hash pour détection de doublons.
- Support MD5, SHA256
- Optimisé pour gros fichiers

#### `utils/metadata_cache.py`
Cache des métadonnées pour performances.
- Stockage SQLite
- Invalidation automatique

---

## 🔧 Configuration de l'Environnement

### 1. Prérequis

```bash
Python 3.8+
pip (gestionnaire de packages)
Git
ExifTool (inclus dans resources/assets/)
```

### 2. Installation

```bash
# Cloner le dépôt
git clone https://github.com/Kiriiaq/PhotoOrganizer.git
cd PhotoOrganizer

# Créer environnement virtuel
python -m venv venv

# Activer l'environnement
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt
```

### 3. Configuration ExifTool

Le fichier `.env` est automatiquement créé avec :
```env
EXIFTOOL_PATH=resources/assets/exiftool.exe
```

Le fichier `config.py` gère la détection automatique avec ordre de priorité :
1. Variable d'environnement `EXIFTOOL_PATH`
2. Chemin relatif `resources/assets/exiftool.exe`
3. Chemin système `C:\Exiftool\exiftool.exe`
4. PATH système

---

## 🚀 Lancer l'Application

### Mode Développement

```bash
# Interface ultra-moderne (recommandée)
python main_ultra_modern.py

# Interface moderne
python main_modern.py

# Interface classique
python main.py
```

### Mode Debug

Modifiez temporairement le code pour activer les logs :
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📦 Créer un Exécutable

### Configuration Actuelle

Le fichier `PhotoManager.spec` est configuré pour :
- **Mode un seul fichier** (`onefile=True`)
- **Pas de console** (`console=False`)
- **Taille** : ~82 MB
- **Icône intégrée** : `resources/icons/icon.ico`
- **Toutes dépendances incluses**

### Générer l'Exécutable

```bash
# Méthode recommandée (utilise PhotoManager.spec)
pyinstaller PhotoManager.spec --noconfirm

# Résultat : dist/PhotoManager Pro.exe (82 MB)
```

### Commande Alternative

```bash
pyinstaller --name="PhotoManager Pro" \
            --onefile \
            --windowed \
            --icon="resources/icons/icon.ico" \
            --add-data="resources;resources" \
            --add-data=".env;." \
            --hidden-import=customtkinter \
            --hidden-import=PIL._tkinter_finder \
            main.py
```

### Optimisations

**PhotoManager.spec inclut déjà** :
```python
# Exclusions pour réduire la taille
excludes=['matplotlib', 'numpy', 'pandas', 'scipy']

# Compression UPX activée
upx=True

# Imports cachés pour CustomTkinter
hiddenimports=['customtkinter', 'PIL._tkinter_finder', 'darkdetect']
```

### Comparaison des Modes

| Mode | Taille | Démarrage | Fichiers |
|------|--------|-----------|----------|
| **One-file (actuel)** | 82 MB | ~5s | 1 fichier |
| One-folder | 55-70 MB | ~1s | ~50 fichiers |

**Pour changer en mode One-Folder** :
Éditez `PhotoManager.spec` et changez `onefile=True` → `onefile=False`

---

## 🧪 Tests et Qualité

### Lancer les Tests

```bash
# Tests unitaires (si configurés)
pytest tests/

# Tests d'intégration
python -m unittest discover tests/
```

### Vérifications Manuelles

**Checklist avant commit** :
- [ ] Application se lance sans erreur
- [ ] Toutes les interfaces fonctionnent
- [ ] ExifTool détecté correctement
- [ ] Import/export fonctionnent
- [ ] Pas d'erreurs dans la console
- [ ] Code formaté (PEP 8)

### Linting

```bash
# Vérifier le style de code
pylint core/ gui/ utils/

# Formatter automatiquement
black core/ gui/ utils/

# Vérifier imports
isort core/ gui/ utils/
```

---

## 🔄 Workflow de Développement

### Branches

```
main              # Production stable
├── develop       # Développement actif
├── feature/*     # Nouvelles fonctionnalités
├── bugfix/*      # Corrections de bugs
└── hotfix/*      # Correctifs urgents
```

### Processus de Contribution

1. **Fork** le dépôt
2. **Créer une branche** : `git checkout -b feature/ma-fonctionnalite`
3. **Développer** et tester
4. **Commit** : `git commit -m "feat: ajout de ma fonctionnalité"`
5. **Push** : `git push origin feature/ma-fonctionnalite`
6. **Pull Request** vers `develop`

### Convention de Commits

```
feat: Nouvelle fonctionnalité
fix: Correction de bug
docs: Documentation
style: Formatage code
refactor: Refactoring
test: Tests
chore: Maintenance
```

---

## 🐛 Débogage

### Problèmes Courants

#### ExifTool non détecté

**Symptômes** : Métadonnées non lues, erreurs "ExifTool not found"

**Solutions** :
```bash
# Vérifier config.py
python -c "import config; print(config.check_exiftool())"

# Vérifier .env
cat .env

# Installer ExifTool manuellement
# Windows: Télécharger depuis https://exiftool.org
# Linux: sudo apt-get install libimage-exiftool-perl
# Mac: brew install exiftool
```

#### Import CustomTkinter échoue

**Symptômes** : `ModuleNotFoundError: No module named 'customtkinter'`

**Solutions** :
```bash
# Réinstaller CustomTkinter
pip uninstall customtkinter
pip install customtkinter>=5.2.0

# Vérifier version Python
python --version  # Doit être 3.8+
```

#### Erreur PyInstaller "Failed to execute script"

**Symptômes** : L'exe ne se lance pas

**Solutions** :
```bash
# Nettoyer et rebuilder
rm -rf build dist
pyinstaller PhotoManager.spec --noconfirm --clean

# Activer mode debug dans PhotoManager.spec
console=True  # Pour voir les erreurs
debug=True
```

#### Icône ne s'affiche pas

**Symptômes** : Icône par défaut au lieu de l'icône custom

**Solutions** :
```bash
# Vérifier le fichier existe
ls resources/icons/icon.ico

# Vérifier le chemin dans .spec
# icon='resources/icons/icon.ico'

# Rebuilder
pyinstaller PhotoManager.spec --noconfirm
```

### Activer Logs Détaillés

```python
# Ajouter au début de main.py
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='photomanager.log'
)
```

---

## 📊 Performance

### Profiling

```python
# Profiler le code
python -m cProfile -o profile.stats main.py

# Analyser les résultats
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumtime'); p.print_stats(20)"
```

### Optimisations Appliquées

1. **Cache de métadonnées** (`utils/metadata_cache.py`)
   - Évite lectures répétées
   - Stockage SQLite performant

2. **Threads pour UI**
   - Opérations longues en arrière-plan
   - Interface toujours réactive

3. **Lazy loading**
   - Prévisualisation d'images à la demande
   - Chargement progressif des listes

---

## 🔐 Sécurité

### Bonnes Pratiques

1. **Pas de credentials dans le code**
   - Utiliser `.env` pour secrets
   - `.env` est dans `.gitignore`

2. **Validation des entrées**
   - Chemins de fichiers validés
   - Pas d'exécution de code non sanitisé

3. **Permissions fichiers**
   - Lecture/écriture minimale requise
   - Pas de droits admin nécessaires

---

## 📚 Ressources

### Documentation Externe

- [CustomTkinter Docs](https://github.com/TomSchimansky/CustomTkinter)
- [Pillow Documentation](https://pillow.readthedocs.io/)
- [ExifTool Documentation](https://exiftool.org/)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)

### Dépendances Clés

```txt
customtkinter>=5.2.0      # Interface moderne
Pillow>=10.0.0            # Manipulation d'images
exifread>=3.0.0           # Lecture EXIF
PyExifTool>=0.5.0         # Wrapper ExifTool
pillow-heif>=0.13.0       # Support HEIF/HEIC
darkdetect>=0.8.0         # Détection thème système
packaging>=23.0           # Gestion de versions
```

---

## 🚀 Distribution

### Créer une Release

```bash
# 1. Tag version
git tag v1.0
git push origin v1.0

# 2. Générer exe
pyinstaller PhotoManager.spec --noconfirm

# 3. Créer archive
7z a PhotoOrganizer_v1.0.zip "dist/PhotoManager Pro.exe"

# 4. Générer checksum
certutil -hashfile "dist/PhotoManager Pro.exe" SHA256 > checksum.txt

# 5. Créer release GitHub avec :
# - Archive .zip
# - Exe standalone
# - checksum.txt
# - Release notes
```

### Release Notes Template

```markdown
## PhotoOrganizer v1.0

### ✨ Nouvelles Fonctionnalités
- Interface ultra-moderne avec CustomTkinter
- Cartes statistiques en temps réel
- Thème clair/sombre

### 🐛 Corrections
- Correction détection ExifTool
- Fix imports métadonnées

### 📦 Téléchargement
- Windows: PhotoOrganizer_v1.0.exe (82 MB)
- Source: v1.0.zip

### 🔐 Checksum SHA256
`[checksum ici]`
```

---

## 💡 Contribution

Pour contribuer, consultez [CONTRIBUTING.md](../CONTRIBUTING.md)

### Domaines de Contribution

- 🎨 **UI/UX** : Améliorer l'interface
- 🐛 **Bugs** : Corriger les bugs
- 📚 **Documentation** : Améliorer les docs
- 🌍 **i18n** : Traductions
- ⚡ **Performance** : Optimisations
- ✅ **Tests** : Ajouter tests unitaires

---

## 📞 Support

- **Issues GitHub** : [github.com/Kiriiaq/PhotoOrganizer/issues](https://github.com/Kiriiaq/PhotoOrganizer/issues)
- **Discussions** : [github.com/Kiriiaq/PhotoOrganizer/discussions](https://github.com/Kiriiaq/PhotoOrganizer/discussions)
- **Email** : manugrolleau48@gmail.com
- **Ko-fi** : https://ko-fi.com/kiriiaq

---

**Dernière mise à jour** : Décembre 2025
**Version du guide** : 1.0

**Développé avec ❤️ par Kiriiaq**
- Email : manugrolleau48@gmail.com
- Ko-fi : https://ko-fi.com/kiriiaq
