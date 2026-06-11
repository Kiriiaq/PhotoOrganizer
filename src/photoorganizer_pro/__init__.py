"""PhotoOrganizer Pro — modules différés v3.0+.

Statut au 2026-05-26 (pivot économique)
---------------------------------------

Ce package est **gelé pour la v2.x**. Suite au pivot vers le modèle
*trial + unlock* (10 tris gratuits / 10 € lifetime / 1 PC), les modules
ci-dessous ne sont plus le différentiateur commercial. Ils sont
conservés intacts pour une éventuelle réactivation en v3.0+ si la v2.x
trouve sa traction (cf. critères dans ``docs/MONETIZATION.md`` §8) :

* ``cli/batch_organize.py`` — CLI batch d'organisation (gelé)
* ``scheduler/watch_folder.py`` — surveillance auto de dossier (gelé)
* ``plugins/`` — Plugin API extensible (gelé)

Le seul sous-package **toujours actif** en v2.x est :

* ``license/`` — validation HMAC SHA-256 des clés. Sera étendu en v2.3.0
  pour gérer le ``machine_id_bound`` (binding au 1er PC qui active une
  clé) — voir [NEXT_STEPS.html](../../docs/NEXT_STEPS.html) §A.2.

État opérationnel
-----------------

* Les entry points CLI Pro sont **commentés** dans ``pyproject.toml``
  (lignes ``photo-organizer-pro-batch`` et ``photo-organizer-pro-watch``).
* Les tests Pro (batch / watch / plugins) sont **skippés** via
  ``@pytest.mark.skip(reason="Deferred to v3.0+")``.
* L'app GUI v2.x n'importe aucun de ces modules — la frontière est
  vérifiable par ``grep -r photoorganizer_pro src/ui/`` (doit être vide).

Si tu lis ce package en tant que dev qui débarque : **n'active rien
sans valider avec l'auteur**. Le pivot 2026-05 est documenté dans
[AUDIT.md](../../AUDIT.md) §15 et [CLAUDE.md](../../CLAUDE.md).
"""
