# `src/photoorganizer_pro/` — état post-pivot 2026-05-26

> Anciennement prévu comme édition Pro séparée (19/49/99 €). Suite au pivot
> économique du 26 mai 2026 vers le modèle **trial + unlock** (édition
> unique, 10 € lifetime, 1 PC), ce dossier joue maintenant un rôle
> hybride :
>
> - `license/` est **actif** et utilisé en production (réutilisé par
>   `src/utils/licensing.py` pour la signature HMAC des clés et du
>   `machine_id_bound`).
> - `cli/`, `scheduler/`, `plugins/` sont **gelés v3.0+** — code conservé
>   intact pour réactivation conditionnelle si la v2.x trouve sa traction.

Cf. [`../../CLAUDE.md`](../../CLAUDE.md), [`../../docs/MONETIZATION.md`](../../docs/MONETIZATION.md) et [`../../AUDIT.md`](../../AUDIT.md) §15 pour le détail du pivot.

---

## Statut par sous-module

| Sous-module | Statut v2.x | Tests | Rôle |
|---|---|---|---|
| `license/` | **ACTIF** | 14 tests verts + indirectement les 17 de `test_licensing.py` | Validation HMAC SHA-256 + machine binding |
| `cli/batch_organize.py` | DEFERRED v3.0+ | 10 tests `@pytest.mark.skip` | CLI scriptable d'organisation |
| `scheduler/watch_folder.py` | DEFERRED v3.0+ | 12 tests `@pytest.mark.skip` | Surveillance auto de dossier |
| `plugins/` | DEFERRED v3.0+ | 25 tests `@pytest.mark.skip` | Plugin API (5 hooks) |

Les entry points pip `photo-organizer-pro-batch` et `photo-organizer-pro-watch` sont **commentés** dans `pyproject.toml`. Tant qu'ils restent commentés, ces modules ne sont pas accessibles par les utilisateurs finaux.

## Frontière d'imports

- `src/core/`, `src/ui/`, `src/cli/duplicate_cli.py` → **n'importent jamais** depuis `photoorganizer_pro/cli/`, `scheduler/`, `plugins/`.
- `src/utils/licensing.py` → importe `photoorganizer_pro.license._secret.SECRET_KEY` et `validate_license_key` / `save_license_key` / `load_active_license`. C'est la **seule** dépendance directe du cœur vers ce package.
- `photoorganizer_pro/` peut importer `core/` et `utils/`, jamais l'inverse.
- Tout module gelé doit pouvoir être supprimé du dossier sans casser l'app v2.x.

## Critères de réactivation v3.0+

Voir [`../../docs/MONETIZATION.md`](../../docs/MONETIZATION.md) §8 :

1. > 200 ventes de la v2.x sur 6 mois (demande validée).
2. > 5 demandes explicites par mois pour batch / watch / plugins.
3. Disponibilité de 2-3 semaines pour livrer une v3.0 propre.

Si réactivation, la procédure est :

- Décommenter les entry points dans `pyproject.toml`.
- Retirer les décorateurs `pytestmark = pytest.mark.skip(...)` des 3 fichiers `tests/functional/test_pro_*.py`.
- Créer un produit Lemon Squeezy "PhotoOrganizer Pro Add-On" séparé du lifetime de base.
- Adapter les modules pour qu'ils vérifient à la fois la licence v2.x (lifetime) ET un flag `has_pro_addon`.

## License

- **Code Python** dans ce dossier : Apache-2.0 (cf. [`../../LICENSE`](../../LICENSE)) — pas de licence propriétaire séparée pour le code source.
- **Binaire compilé** distribué via Lemon Squeezy : régi par [`../../LICENSE-PRO`](../../LICENSE-PRO) (EULA de l'édition activable). À adapter pour refléter le pivot quand la v2.3.0 sera taggée publiquement.
- **Clé HMAC** dans `license/_secret.py` : **gitignored**. Ne JAMAIS commit. La perdre invalide toutes les clés émises.
