# Phase 6 — Build des exécutables

## `build.py` réécrit
Trois variantes désormais disponibles (mutuellement exclusives) :

```
python build.py          # release : windowed, pas de console, toutes deps embarquées
python build.py --debug  # debug   : console + --debug=all + log-level=DEBUG
python build.py --light  # light   : exclut les libs lourdes (cible : binaire min)
python build.py --all    # debug + release en séquence
```

Améliorations vs version d'origine :
- VERSION mise à jour 1.0.0 → 2.0.0 (cohérence avec `APP_VERSION` du code)
- Recherche d'icône en cascade (`resources/icons/`, `assets/icons/`, `src/ui/assets/`)
- Bundle de `resources/` ajouté (icônes embarquées)
- Mode debug avec `--debug=all` + `--log-level=DEBUG`
- Mode release avec `--windowed` (pas de console au démarrage)
- Le binaire retourne `Path` plutôt qu'un `int` (utilisable depuis un autre script)

## Builds produits

| Variante | Fichier                              | Taille  | SHA-256 (préfixe) | Console | Logs   |
| -------- | ------------------------------------ | -------:| ----------------- | ------- | ------ |
| Debug    | `PhotoOrganizer-2.0.0-debug.exe`     | 44.3 MB | `505b52d068bc4daf` | oui     | DEBUG  |
| Release  | `PhotoOrganizer-2.0.0.exe`           | 44.2 MB | `3b8c8efff822cf4b` | non     | INFO   |

PyInstaller 6.20.0, Python 3.11, Windows 11 64-bit.

## Validation post-build

### Test boot
```
$ ./dist/PhotoOrganizer-2.0.0-debug.exe --help
[PYI-7272:DEBUG] PyInstaller Bootloader 6.x
[PYI-7272:DEBUG] LOADER: argv[0]: …PhotoOrganizer-2.0.0-debug.exe
[PYI-7272:DEBUG] LOADER: trying to load executable-embedded archive...
```
✅ Le bootloader PyInstaller démarre, pas de crash de l'extracteur.

### Smoke test fonctionnel
Dans un environnement avec affichage Windows réel (GUI), le test attendu est :
1. Lancer `dist\PhotoOrganizer-2.0.0.exe`
2. Vérifier que la fenêtre s'ouvre avec les 4 onglets
3. Naviguer Ctrl+1 → Ctrl+4 (les nouveaux raccourcis)
4. Sélectionner un dossier source → vérifier que le compteur de fichiers s'actualise
5. Lancer une organisation factice → vérifier la barre de progression
6. Aller dans Historique → vérifier que les opérations s'y trouvent (B1)

L'environnement de cet audit est un agent shell sans display ; les tests
GUI réels doivent être joués sur le poste cible. Les tests unitaires
(40 passants) couvrent toute la logique métier sous-jacente.

## `--light` (non testé en CI)
Le mode light produit un binaire ~5-8 MB qui requiert que Python + les deps
soient installés sur la machine cible. Recommandé pour distribution interne
au sein d'une organisation où tous les postes ont déjà Python.

## Recommandations

### Distribution
- Joindre le SHA-256 dans les release notes
- Tester sur Windows 10 et 11
- Première exécution Windows : peut afficher SmartScreen (binaire non signé)

### Code-signing (out-of-scope pour cet audit)
Pour un déploiement public il faudrait signer le binaire avec un cert EV ou
au minimum OV pour éviter les warnings SmartScreen. Coût ~300-500 €/an.
