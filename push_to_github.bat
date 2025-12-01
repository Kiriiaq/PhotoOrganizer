@echo off
echo ========================================
echo PhotoOrganizer - GitHub Push Script
echo Developed by Kiriiaq
echo ========================================
echo.

REM Vérifier si Git est installé
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Git n'est pas installé ou n'est pas dans le PATH
    echo Téléchargez Git depuis: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [1/6] Initialisation du repository Git...
if not exist ".git" (
    git init
    echo Repository Git initialisé
) else (
    echo Repository Git déjà initialisé
)

echo.
echo [2/6] Configuration Git utilisateur...
git config user.name "Kiriiaq"
git config user.email "manugrolleau48@gmail.com"
echo Configuration utilisateur définie

echo.
echo [3/6] Ajout de tous les fichiers...
git add .
echo Fichiers ajoutés

echo.
echo [4/6] Création du commit initial...
git commit -m "Initial commit: PhotoOrganizer v1.0

✨ Features:
- Interface moderne avec CustomTkinter
- Analyse complète avec 45 formats supportés
- Organisation intelligente par date/appareil/GPS
- Fenêtre de résultats défilable avec icônes
- Barre de progression en temps réel
- Bouton d'annulation fonctionnel
- Exécutable Windows autonome

📦 Includes:
- Documentation complète (FR)
- Templates GitHub (issues, PR)
- Configuration Ko-fi

👨‍💻 Developer: Kiriiaq
📧 Contact: manugrolleau48@gmail.com
☕ Ko-fi: https://ko-fi.com/kiriiaq"

if %errorlevel% neq 0 (
    echo [INFO] Aucun changement à commiter ou commit déjà effectué
)

echo.
echo [5/6] Ajout du remote GitHub...
git remote add origin https://github.com/Kiriiaq/PhotoOrganizer.git 2>nul
if %errorlevel% equ 0 (
    echo Remote ajouté: https://github.com/Kiriiaq/PhotoOrganizer.git
) else (
    echo Remote déjà configuré
    git remote set-url origin https://github.com/Kiriiaq/PhotoOrganizer.git
    echo URL du remote mise à jour
)

echo.
echo [6/6] Push vers GitHub...
echo IMPORTANT: Assurez-vous d'avoir créé le repository sur GitHub avant de continuer
echo Repository URL: https://github.com/Kiriiaq/PhotoOrganizer
echo.
set /p CONFIRM="Voulez-vous continuer le push? (O/N): "
if /i "%CONFIRM%" neq "O" (
    echo Push annulé
    pause
    exit /b 0
)

git branch -M main
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ SUCCESS! Projet poussé sur GitHub
    echo ========================================
    echo.
    echo 🔗 Repository: https://github.com/Kiriiaq/PhotoOrganizer
    echo 📝 Next steps:
    echo    1. Vérifier le repository sur GitHub
    echo    2. Configurer les Settings/Topics
    echo    3. Créer une Release (voir docs/GETTING_STARTED.md)
    echo    4. Activer GitHub Discussions (optionnel)
    echo.
    echo 👨‍💻 Developer: Kiriiaq
    echo 📧 Contact: manugrolleau48@gmail.com
    echo ☕ Ko-fi: https://ko-fi.com/kiriiaq
    echo.
) else (
    echo.
    echo ========================================
    echo ❌ ERREUR lors du push
    echo ========================================
    echo.
    echo Causes possibles:
    echo   1. Le repository n'existe pas encore sur GitHub
    echo      → Créez-le sur https://github.com/new
    echo   2. Problème d'authentification
    echo      → Vérifiez vos credentials Git
    echo   3. Branche protégée
    echo      → Vérifiez les settings du repository
    echo.
    echo Pour plus d'aide, consultez: docs/GETTING_STARTED.md
    echo.
)

pause
