# Archive — documents superseded par le pivot 2026-05-26

Ces documents reflètent la stratégie **antérieure** au pivot économique
acté le 26 mai 2026. Ils sont conservés pour traçabilité et pour
permettre une éventuelle réactivation des modules Pro en v3.0+.

## Contexte du pivot

PhotoOrganizer est passé d'un modèle "freemium par fonctionnalité"
(Pro séparée à 19 € / 49 € / 99 € avec batch CLI + watch-folder + plugins)
à un modèle "trial + unlock" (édition unique, 10 tris gratuits, puis
**10 € lifetime / 1 PC**). Détail du raisonnement dans :

- [CLAUDE.md](../../../CLAUDE.md) — section "Décisions techniques actées"
- [docs/MONETIZATION.md](../../MONETIZATION.md) — §2 *Pourquoi ce pivot*
- [AUDIT.md](../../../AUDIT.md) — §15 *Phase 8 — Pivot économique*

## Contenu de cette archive

| Fichier | Origine | Pourquoi archivé |
|---|---|---|
| `PRO.md` | `docs/PRO.md` | Documentait l'UX d'activation de l'édition Pro séparée. La nouvelle UX trial+unlock est documentée dans [NEXT_STEPS.html](../../../NEXT_STEPS.html) §A.5. |
| `CLOUD_SYNC_DESIGN.md` | `docs/CLOUD_SYNC_DESIGN.md` | Étude design d'un module Pro V2 "synchronisation cloud" (S3/B2/GDrive). Pertinent uniquement si l'add-on Pro est réactivé en v3.0+. |
| `LAUNCH_CHECKLIST.html` | Racine du repo | Checklist initiale (création Pro V1.1 + standards repo). Remplacée par `NEXT_STEPS.html` post-pivot. |

## Autres documents impactés (réécrits in place)

Ces fichiers ont été **réécrits** plutôt qu'archivés. L'ancien contenu
est récupérable via `git log -p` :

| Fichier | Commit avant pivot |
|---|---|
| `docs/MONETIZATION.md` | (à retrouver via `git log --before="2026-05-26" -- docs/MONETIZATION.md`) |
| `NEXT_STEPS.html` | (untracked au moment du pivot, pas de version git antérieure) |
| `README.md` (section "Modèle économique") | idem |
| `CLAUDE.md` (sections modèle économique + décisions) | idem |

## Réactivation conditionnelle

Les modules Pro existants (`src/photoorganizer_pro/cli/`, `scheduler/`,
`plugins/`) sont **conservés intacts** dans le code source, simplement
gelés via :

- Entry points commentés dans `pyproject.toml`
- Tests décorés `@pytest.mark.skip(reason="Deferred to v3.0+")`

Critères de réactivation v3.0+ (cf. [docs/MONETIZATION.md](../../MONETIZATION.md) §8) :

1. > 200 ventes de la v2.x sur 6 mois (demande validée)
2. > 5 demandes explicites par mois (besoin identifié)
3. Disponibilité de 2-3 semaines pour livrer une v3.0 propre

Tant que ces critères ne sont pas réunis, les documents archivés ici
restent en réserve sans plus d'évolution.
