"""PhotoOrganizer Pro — sous-package licence.

Validation offline de clés signées HMAC SHA-256.

Conception : pas de serveur d'authentification. La clé secrète est
embarquée dans le binaire Pro. Le crack reste possible (binary analysis)
mais l'effort dépasse largement le prix de la licence (19 €).

Voir ``docs/PRO.md`` pour l'expérience utilisateur et
``src/photoorganizer_pro/license/keygen.py`` pour la génération de clés
côté auteur.
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
