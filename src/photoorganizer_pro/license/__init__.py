"""PhotoOrganizer — sous-package licence (actif en v2.3+).

Validation offline de clés signées HMAC SHA-256. Réutilisé par
``src/utils/licensing.py`` pour le modèle *trial + unlock* du pivot
2026-05-26 : 10 tris gratuits, puis activation par clé universelle qui se
bound au PC courant via ``machine_id_bound`` (cf. ``validator.py``).

Conception : pas de serveur d'authentification. La clé secrète est
embarquée dans le binaire. Le crack reste possible (binary analysis) mais
l'effort dépasse largement le prix de la licence (**10 € lifetime**).

* Génération côté auteur : ``keygen.py`` (jamais distribuée).
* Validation côté utilisateur : :func:`validate_license_key` +
  :func:`save_license_key` (binding au 1er PC) + :func:`load_active_license`.
* Stratégie économique détaillée : ``docs/MONETIZATION.md``.
* Stratégie de DRM offline : ``src/utils/licensing.py`` (§ "Caveat sécurité").

Les constantes ``EDITION_PERSONAL`` / ``EDITION_STUDIO`` sont conservées
pour rétrocompat (tests `test_pro_license.py`) et pour une éventuelle
réactivation v3.0+ d'un add-on multi-PC. En v2.x **seule
``EDITION_LIFETIME`` est émise**.
"""

from .validator import (
    EDITION_LIFETIME,
    EDITION_PERSONAL,
    EDITION_STUDIO,
    LicenseExpiredError,
    LicenseInfo,
    LicenseInvalidError,
    load_active_license,
    validate_license_key,
)

__all__ = [
    "EDITION_LIFETIME",
    "EDITION_PERSONAL",
    "EDITION_STUDIO",
    "LicenseExpiredError",
    "LicenseInfo",
    "LicenseInvalidError",
    "load_active_license",
    "validate_license_key",
]
