# 🚀 Guide de Démarrage Rapide

> Installation, configuration et publication sur GitHub

---

## 📥 Installation

### Option 1 : Exécutable Windows (Recommandé)

**Pour utilisateurs finaux - Aucune installation Python requise**

1. **Télécharger** l'exécutable depuis [Releases](https://github.com/Kiriiaq/PhotoOrganizer/releases)
   - Fichier : `PhotoManager Pro.exe` (82 MB)

2. **Lancer** l'application
   - Double-cliquez sur le fichier `.exe`
   - Aucune installation requise
   - Fonctionne sur n'importe quel PC Windows

3. **Premier lancement**
   - Peut prendre 5-10 secondes (extraction temporaire)
   - Lancements suivants plus rapides

### Option 2 : Installation depuis Source

**Pour développeurs et contributeurs**

#### Prérequis
```bash
Python 3.8 ou supérieur
pip (gestionnaire de packages Python)
Git
```

#### Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/Kiriiaq/PhotoOrganizer.git
cd PhotoOrganizer

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv

# 3. Activer l'environnement virtuel
# Windows :
venv\Scripts\activate
# Linux/Mac :
source venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt
```

#### Lancer l'Application

```bash
# Interface ultra-moderne (recommandée)
python main_ultra_modern.py

# Interface moderne
python main_modern.py

# Interface classique
python main.py
```

---

## ⚙️ Configuration Initiale

### ExifTool

L'application inclut ExifTool, mais vous pouvez le configurer manuellement :

**Windows** :
```bash
# Déjà inclus dans resources/assets/exiftool.exe
# Aucune action requise
```

**Linux** :
```bash
sudo apt-get install libimage-exiftool-perl
```

**macOS** :
```bash
brew install exiftool
```

### Fichier .env

Créé automatiquement au premier lancement avec :
```env
EXIFTOOL_PATH=resources/assets/exiftool.exe
```

Pour personnaliser :
```env
# Chemin personnalisé vers ExifTool
EXIFTOOL_PATH=C:\Custom\Path\exiftool.exe

# Désactiver le cache (dev uniquement)
DISABLE_CACHE=True
```

---

## 🎯 Utilisation Rapide (30 secondes)

### 1. Organisation de Photos

```
1. Lancez l'application
2. Onglet "Organisation" → "Sélectionner dossier source"
3. Choisissez le dossier contenant vos photos
4. Sélectionnez le format : Année/Mois ou Année/Mois/Jour
5. Cliquez "Organiser"
6. ✅ Photos organisées automatiquement !
```

### 2. Trouver les Doublons

```
1. Onglet "Analyse" → "Détecter doublons"
2. Sélectionnez un dossier
3. Choisissez la méthode : Hash, Contenu, ou Métadonnées
4. Cliquez "Analyser"
5. Prévisualisez et supprimez les doublons
```

### 3. Carte GPS

```
1. Onglet "Carte"
2. Sélectionnez un dossier contenant des photos avec GPS
3. La carte affiche automatiquement les emplacements
4. Cliquez sur les marqueurs pour voir les photos
```

---

## 🐙 Publier sur GitHub

### Étape 1 : Préparer le Projet

#### Personnaliser les Fichiers

**1. `.github/FUNDING.yml`**

Configuration actuelle :
```yaml
github: [Kiriiaq]
custom: ["https://ko-fi.com/kiriiaq"]
ko_fi: kiriiaq
```

**2. `README.md`**

Configuration actuelle :
```markdown
# Développeur : Kiriiaq
# GitHub : https://github.com/Kiriiaq/PhotoOrganizer
# Contact : manugrolleau48@gmail.com
# Ko-fi : https://ko-fi.com/kiriiaq
```

**3. Vérifier `.gitignore`**

Assurez-vous que ces fichiers sont exclus :
```gitignore
# Déjà configuré
*.pyc
__pycache__/
venv/
.env
*.log
```

### Étape 2 : Créer les Comptes de Dons

#### Buy Me a Coffee
1. Allez sur [buymeacoffee.com](https://www.buymeacoffee.com)
2. Créez un compte
3. Notez votre username
4. Ajoutez-le dans `FUNDING.yml`

#### PayPal.me
1. Créez un lien [paypal.me](https://www.paypal.com/paypalme/)
2. Format : `https://paypal.me/VOTRE_USERNAME`
3. Ajoutez-le dans `FUNDING.yml`

#### GitHub Sponsors (Optionnel)
1. Activez [GitHub Sponsors](https://github.com/sponsors)
2. Complétez votre profil
3. GitHub ajoute automatiquement le bouton "Sponsor"

#### Ko-fi / Patreon (Optionnels)
- [ko-fi.com](https://ko-fi.com)
- [patreon.com](https://www.patreon.com)

### Étape 3 : Initialiser Git

```bash
# Dans le dossier du projet
cd PhotoOrganizer

# Initialiser Git (si pas déjà fait)
git init

# Ajouter tous les fichiers
git add .

# Premier commit
git commit -m "Initial commit: PhotoOrganizer v1.0

✨ Features:
- Interface ultra-moderne CustomTkinter
- Organisation automatique par date
- Détection de doublons
- Carte GPS des photos
- Support EXIF complet
- Thème clair/sombre

📦 Includes:
- 3 interfaces (classique, moderne, ultra-moderne)
- Exécutable Windows standalone
- Documentation complète
"
```

### Étape 4 : Créer le Repository GitHub

#### Via Interface Web

1. **Allez sur** [github.com/new](https://github.com/new)

2. **Remplissez** :
   ```
   Repository name: PhotoOrganizer
   Description: 📸 Professional photo organizer with EXIF analysis and smart organization
   Public ✓
   ```

3. **Ne cochez PAS** :
   - ❌ Add README
   - ❌ Add .gitignore
   - ❌ Choose license

   (Nous avons déjà ces fichiers)

4. **Créez** le repository

#### Lier au Repository Local

```bash
# Ajouter le remote
git remote add origin https://github.com/Kiriiaq/PhotoOrganizer.git

# Renommer branche en main
git branch -M main

# Pousser le code
git push -u origin main
```

### Étape 5 : Configurer le Repository

#### Settings → General

```
✓ Issues enabled
✓ Preserve this repository (si important)
✓ Wikis (optionnel)
✓ Discussions (recommandé)
```

#### Topics (Tags)

Ajoutez ces topics pour visibilité :
```
python
photo-manager
exif
gps
duplicate-detection
customtkinter
photo-organizer
image-metadata
tkinter
windows
```

#### About Section

```
Description:
📸 Professional photo organizer with automatic organization and EXIF metadata analysis. Modern UI with CustomTkinter.

Developer: Kiriiaq
Contact: manugrolleau48@gmail.com

Website: (votre site si vous en avez un)
Topics: python, photo-manager, exif, gps, customtkinter
```

### Étape 6 : Créer une Release

```bash
# 1. Créer un tag
git tag -a v1.0 -m "Release v1.0 - Initial public release"
git push origin v1.0

# 2. Générer l'exécutable (si pas déjà fait)
pyinstaller PhotoManager.spec --noconfirm

# 3. Créer archive
7z a PhotoOrganizer_v1.0.zip "dist/PhotoManager Pro.exe"

# 4. Générer checksum
certutil -hashfile "dist/PhotoManager Pro.exe" SHA256 > SHA256SUMS.txt
```

#### Sur GitHub

1. **Onglet Releases** → **Create a new release**

2. **Tag** : `v1.0`

3. **Title** : `PhotoOrganizer v1.0 - Initial Release`

4. **Description** :
```markdown
## 🎉 PhotoOrganizer v1.0

Premier release public de PhotoOrganizer !

### ✨ Fonctionnalités

- **Interface ultra-moderne** avec CustomTkinter
- **Organisation automatique** par date (EXIF)
- **Détection de doublons** (hash, contenu, métadonnées)
- **Carte GPS interactive** pour géolocalisation
- **Thèmes** clair/sombre
- **Support complet EXIF** (ExifTool intégré)
- **3 interfaces** au choix (classique, moderne, ultra-moderne)

### 📦 Téléchargement

**Windows (Recommandé)** :
- `PhotoManager Pro.exe` (82 MB) - Exécutable standalone
- Aucune installation requise
- Fonctionne sans Python

**Source** :
- `Source code (zip)` - Code source complet
- Requiert Python 3.8+

### 🔐 Checksum SHA256
Voir `SHA256SUMS.txt`

### 📚 Documentation
- [Guide de démarrage rapide](docs/GETTING_STARTED.md)
- [Guide développeur](docs/DEVELOPMENT.md)
- [README](README.md)

### 🙏 Support
Si ce projet vous aide, considérez un don :
- ☕ [Ko-fi](https://ko-fi.com/kiriiaq)

### 🐛 Bugs & Suggestions
Utilisez les [Issues](https://github.com/Kiriiaq/PhotoOrganizer/issues)

### 📧 Contact
- **Email:** manugrolleau48@gmail.com
- **Développeur:** Kiriiaq
```

5. **Uploader les fichiers** :
   - `PhotoManager Pro.exe`
   - `PhotoOrganizer_v1.0.zip`
   - `SHA256SUMS.txt`

6. **Publier** la release

---

## 🎨 Créer une Icône Personnalisée (Optionnel)

### Méthode 1 : AI Generator (Recommandé)

**Outils** :
- [DALL-E](https://openai.com/dall-e-2) (OpenAI)
- [Midjourney](https://midjourney.com)
- [Stable Diffusion](https://stablediffusion.fr)

**Prompt pour l'IA** :
```
Create a modern, professional app icon for a photo management software.

Design Requirements:
- Main element: Camera lens or photo frames
- Style: Flat design, modern, minimalist
- Colors: Blue gradient (#2563EB to #3B82F6) with white accents
- Background: Rounded square with subtle shadow
- Icon should work at both large (512x512) and small (32x32) sizes
- Professional look, suitable for Windows desktop app

Additional elements to consider:
- Folder/file organization symbols
- GPS pin (subtle)
- Checkmark or organization indicator
- Clean, simple geometric shapes

Mood: Professional, trustworthy, modern, efficient
Format: High resolution (1024x1024), PNG with transparency
```

### Méthode 2 : Outils en Ligne Gratuits

**Icon Generators** :
- [Canva](https://www.canva.com) - Templates d'icônes
- [Flaticon](https://www.flaticon.com) - Icônes gratuites
- [IconMonstr](https://iconmonstr.com) - Icônes simples

### Méthode 3 : Logiciels Desktop

**Outils** :
- Adobe Illustrator
- Figma (gratuit)
- Inkscape (gratuit, open-source)
- GIMP (gratuit)

**Specifications** :
```
Format source: SVG ou PNG haute résolution (1024x1024)
Formats de sortie nécessaires:
  - icon.ico (16x16, 32x32, 48x48, 256x256)
  - icon.png (512x512, transparent background)
```

### Conversion PNG → ICO

**En ligne** :
- [ConvertICO.com](https://convertico.com)
- [ICO Convert](https://icoconvert.com)

**Ligne de commande** (ImageMagick) :
```bash
convert icon.png -define icon:auto-resize=256,128,96,64,48,32,16 icon.ico
```

### Intégrer l'Icône

```bash
# 1. Remplacer les fichiers
cp votre_nouvelle_icon.ico resources/icons/icon.ico
cp votre_nouvelle_icon.png resources/icons/icon.png

# 2. Rebuilder l'exe
pyinstaller PhotoManager.spec --noconfirm

# 3. Vérifier
ls -lh "dist/PhotoManager Pro.exe"
```

---

## ✅ Checklist Finale

### Avant Publication

- [ ] Tous les liens personnalisés (FUNDING.yml, README.md)
- [ ] Comptes de dons créés et configurés
- [ ] `.gitignore` vérifié (pas de fichiers sensibles)
- [ ] Tests manuels de l'application
- [ ] Exécutable généré et testé
- [ ] Documentation à jour
- [ ] Captures d'écran ajoutées à `docs/screenshots/`

### Après Publication

- [ ] Repository public activé
- [ ] Release créée avec exe
- [ ] Topics/tags configurés
- [ ] About section remplie
- [ ] Issues templates testés
- [ ] Bouton sponsor visible
- [ ] README s'affiche correctement
- [ ] Liens de téléchargement fonctionnels

### Marketing (Optionnel)

- [ ] Partager sur Reddit ([r/Python](https://reddit.com/r/Python), [r/opensource](https://reddit.com/r/opensource))
- [ ] Tweet avec hashtags #Python #OpenSource #Photography
- [ ] Article dev.to ou Medium
- [ ] Soumettre à [awesome-python](https://github.com/vinta/awesome-python)
- [ ] Ajouter à [Product Hunt](https://www.producthunt.com)

---

## 🆘 Résolution de Problèmes

### Git Push Échoue

**Erreur** : `! [rejected] main -> main (fetch first)`

**Solution** :
```bash
git pull origin main --rebase
git push origin main
```

### Funding Button Absent

**Causes possibles** :
1. `FUNDING.yml` pas dans `.github/`
2. Format YAML incorrect
3. GitHub met ~1h à détecter

**Solution** :
```bash
# Vérifier format
cat .github/FUNDING.yml

# Forcer update
git add .github/FUNDING.yml
git commit -m "fix: update funding config"
git push
```

### Exe Trop Gros

**Taille normale** : 82 MB (mode onefile avec toutes dépendances)

**Pour réduire** :
```python
# Dans PhotoManager.spec, ajouter exclusions
excludes=[
    'matplotlib', 'numpy', 'pandas', 'scipy',
    'IPython', 'jedi', 'pygments'  # Ajouter ces
]
```

### Badges Non Fonctionnels

**Problème** : Badges "404 Not Found"

**Solution** : Attendre 5-10 minutes après création du repo, puis forcer refresh
```bash
# Mettre à jour README avec timestamp
git commit -am "docs: update badges"
git push
```

---

## 📞 Support et Ressources

### Documentation

- **README** : Vue d'ensemble et features
- **DEVELOPMENT.md** : Guide développeur complet
- **CONTRIBUTING.md** : Guide de contribution
- **Ce guide** : Installation et publication

### Communauté

- **Issues** : [github.com/Kiriiaq/PhotoOrganizer/issues](https://github.com/Kiriiaq/PhotoOrganizer/issues)
- **Discussions** : [github.com/Kiriiaq/PhotoOrganizer/discussions](https://github.com/Kiriiaq/PhotoOrganizer/discussions)
- **Email** : manugrolleau48@gmail.com
- **Ko-fi** : https://ko-fi.com/kiriiaq

### Liens Utiles

- [Guide Markdown GitHub](https://guides.github.com/features/mastering-markdown/)
- [Guide GitHub Actions](https://docs.github.com/actions)
- [Guide GitHub Sponsors](https://docs.github.com/sponsors)
- [Awesome README](https://github.com/matiassingers/awesome-readme)

---

## 🎉 Félicitations !

Votre projet PhotoOrganizer est maintenant :
- ✅ Installé et configuré
- ✅ Publié sur GitHub
- ✅ Prêt à recevoir des contributions
- ✅ Configurable pour recevoir des dons

**Développé par Kiriiaq**
- 📧 Contact : manugrolleau48@gmail.com
- ☕ Ko-fi : https://ko-fi.com/kiriiaq

**Prochaines étapes** :
1. Promouvoir votre projet
2. Répondre aux issues
3. Accepter les pull requests
4. Créer de nouvelles releases

---

**Bonne chance avec votre projet ! 🚀**

*Dernière mise à jour : Décembre 2025*
