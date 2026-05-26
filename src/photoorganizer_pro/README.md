# PhotoOrganizer Pro — frontière freemium

> Ce dossier est volontairement vide pour l'instant. Il matérialise la séparation entre le **cœur open-source** (sous Apache-2.0, dans `src/`) et la **future version Pro** (propriétaire).

## Pourquoi cette frontière dès maintenant

Le projet PhotoOrganizer adopte un modèle **freemium** :

- **Core (gratuit, Apache-2.0)** — GUI Windows complète, organisation par date / caméra / GPS, détection de doublons, historique réversible, quarantaine.
- **Pro (payant, licence propriétaire)** — modules avancés pour utilisateurs power users et professionnels.

Définir la frontière de package dès la refactorisation évite les dépendances accidentelles `core → pro` qui rendraient le découpage impossible plus tard.

## Modules Pro envisagés (cf. `docs/MONETIZATION.md`)

| Module | Statut | Description |
|---|---|---|
| `cli.batch_organize` | À développer | CLI complet d'organisation (équivalent GUI mais scriptable, idéal CI/cron) |
| `scheduler.watch_folder` | À développer | Surveille un dossier et organise automatiquement les nouveaux fichiers |
| `plugins.api` | À spécifier | Hooks Python pour étendre les règles (renommage, filtres, post-actions) |
| `reports.advanced` | À développer | Rapports HTML/PDF avec graphiques, comparaisons inter-périodes |
| `cloud.sync` | À étudier | Synchronisation S3 / Backblaze / Drive après organisation |

## Règle d'architecture

- `src/core/`, `src/ui/`, `src/utils/`, `src/cli/duplicate_cli.py` → **core libre, à ne pas importer depuis Pro**.
- `src/photoorganizer_pro/` → peut importer le core. Jamais l'inverse.
- Chaque module Pro doit pouvoir être absent à l'exécution sans casser le core.

## License

Le code livré dans ce dossier sera sous **licence propriétaire** distincte. Il **n'est pas** régi par l'Apache-2.0 du reste du repo. Voir `LICENSE-PRO` (à créer au moment du premier module Pro).
