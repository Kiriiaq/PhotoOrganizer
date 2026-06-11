"""Shim de rétrocompatibilité — code déplacé vers ``src/utils/license_validator``.

Lot F (audit 2026-06-11) : la validation de licence vit désormais dans
``src/utils/license_validator.py`` afin que la v2.x ne dépende plus du
package Pro gelé (frontière de couches CLAUDE.md : ``photoorganizer_pro``
peut importer ``utils``, jamais l'inverse).

Ce module ne fait que ré-exporter les symboles pour :

* ``keygen.py`` (outil auteur, jamais distribué) ;
* les tests historiques ``tests/functional/test_pro_license.py`` ;
* tout script externe de l'auteur qui importait l'ancien chemin.

Ne rien ajouter ici — toute évolution se fait dans
``src/utils/license_validator.py``.
"""

from src.utils.license_validator import (  # noqa: F401
    EDITION_LIFETIME,
    EDITION_PERSONAL,
    EDITION_STUDIO,
    SECRET_KEY,
    VALID_EDITIONS,
    LicenseExpiredError,
    LicenseInfo,
    LicenseInvalidError,
    _canonicalize,
    _get_current_machine_id,
    _license_storage_path,
    _sign,
    load_active_license,
    save_license_key,
    validate_license_key,
)
