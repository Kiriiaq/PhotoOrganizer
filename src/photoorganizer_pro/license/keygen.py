"""Script de génération de clés Pro — usage AUTEUR uniquement.

NE PAS distribuer ce fichier au public. À conserver hors du repo public
si tu publies la version Pro (déplacer dans un repo privé séparé après
le lancement).

Usage typique : après réception d'une notification d'achat Lemon Squeezy,
exécuter ce script pour générer la clé et l'envoyer par email au client.

::

    python -m src.photoorganizer_pro.license.keygen \\
        --email user@example.com \\
        --edition PERS \\
        --years 1

Sortie :

::

    PROG-PERS-20271231-dXNlckBleGFtcGxlLmNvbQ==-a1b2c3...
"""

from __future__ import annotations

import argparse
import base64
import sys
from datetime import date, timedelta

from .validator import (
    EDITION_LIFETIME,
    EDITION_PERSONAL,
    EDITION_STUDIO,
    VALID_EDITIONS,
    _sign,
    validate_license_key,
)


def generate_key(email: str, edition: str, expires: date) -> str:
    """Génère une clé signée à partir des paramètres."""
    if edition not in VALID_EDITIONS:
        raise ValueError(f"Edition '{edition}' invalide. Choix : {sorted(VALID_EDITIONS)}")
    if "@" not in email:
        raise ValueError("Email mal formé")

    exp_str = expires.strftime("%Y%m%d")
    payload_b64 = base64.b64encode(email.encode("utf-8")).decode("ascii")
    sig_payload = f"{edition}-{exp_str}-{payload_b64}"
    sig = _sign(sig_payload)
    return f"PROG-{edition}-{exp_str}-{payload_b64}-{sig}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère une clé de licence PhotoOrganizer Pro.")
    parser.add_argument("--email", required=True, help="Email du licencié")
    parser.add_argument(
        "--edition",
        required=True,
        choices=sorted(VALID_EDITIONS),
        help=f"Édition. PERS={EDITION_PERSONAL} (1 PC), STUD={EDITION_STUDIO} (3 PC), LIFE={EDITION_LIFETIME}",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=1,
        help="Durée de validité en années (ignoré si --edition LIFE, qui force 30 ans)",
    )
    parser.add_argument("--verify-only", action="store_true", help="Vérifie une clé existante au lieu d'en générer une")
    parser.add_argument("--key", help="Clé à vérifier (avec --verify-only)")
    args = parser.parse_args()

    if args.verify_only:
        if not args.key:
            parser.error("--verify-only requiert --key")
        info = validate_license_key(args.key)
        print(f"OK : email={info.email} edition={info.edition} expires={info.expires.isoformat()}")
        return 0

    if args.edition == EDITION_LIFETIME:
        expires = date.today() + timedelta(days=365 * 30)
    else:
        expires = date.today() + timedelta(days=365 * args.years)

    key = generate_key(args.email, args.edition, expires)
    # Vérification immédiate (sanity check : si on l'a généré, on doit la valider)
    validate_license_key(key)
    print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
