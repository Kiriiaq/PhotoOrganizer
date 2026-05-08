# -*- coding: utf-8 -*-
"""
Bibliothèque d'exemples de templates de renommage prêts à l'emploi.

Chaque entrée propose :
  - ``label``       : nom court affichable dans la liste UI
  - ``template``    : valeur à coller dans le champ « Template »
  - ``description`` : phrase explicative (utilisée comme tooltip)
  - ``preview``     : aperçu du résultat appliqué à un fichier de démo

Tous les templates utilisent les tokens supportés par
``SmartOrganizer._apply_rename_template`` :
  {original}, {ext}, {date:%fmt}, {camera}, {counter:03d}

Convention : les exemples sont triés du plus simple au plus complet, pour
qu'un nouvel utilisateur puisse les essayer dans l'ordre.
"""

from typing import List, NamedTuple


class RenameTemplate(NamedTuple):
    label: str
    template: str
    description: str
    preview: str  # rendu pour IMG_0001.jpg, 2026-05-07, Sony ILCE-7M3, counter=42


# Liste ordonnée des exemples présentés dans l'IHM
RENAME_TEMPLATES: List[RenameTemplate] = [
    # === 1. Sans renommage ============================================
    RenameTemplate(
        label="Garder le nom d'origine",
        template="",
        description=(
            "N'applique aucun renommage : les fichiers gardent leur nom "
            "actuel (IMG_0001.jpg, DSC_42.NEF, etc.)."
        ),
        preview="IMG_0001.jpg → IMG_0001.jpg",
    ),

    # === 2. Date prefix simple ========================================
    RenameTemplate(
        label="Préfixe date — YYYYMMDD",
        template="{date:%Y%m%d}_{original}",
        description=(
            "Ajoute la date EXIF en préfixe au nom d'origine. Idéal pour "
            "un tri chronologique dans l'explorateur."
        ),
        preview="IMG_0001.jpg → 20260507_IMG_0001.jpg",
    ),

    # === 3. Date + compteur ===========================================
    RenameTemplate(
        label="Date + compteur 4 chiffres",
        template="{date:%Y%m%d}_{counter:04d}",
        description=(
            "Renomme entièrement avec date + numéro séquentiel sur 4 chiffres. "
            "Bon pour reset un nommage chaotique. Le {ext} est ajouté auto."
        ),
        preview="IMG_0001.jpg → 20260507_0042.jpg",
    ),

    # === 4. Format ISO complet ========================================
    RenameTemplate(
        label="Date ISO + heure (YYYY-MM-DD_HHmm)",
        template="{date:%Y-%m-%d_%H%M}_{counter:03d}",
        description=(
            "Format ISO 8601 lisible avec heure de prise de vue. "
            "Tri chronologique précis à la minute près."
        ),
        preview="IMG_0001.jpg → 2026-05-07_1430_042.jpg",
    ),

    # === 5. Appareil + date ===========================================
    RenameTemplate(
        label="Appareil + date",
        template="{camera}_{date:%Y%m%d}_{counter:03d}",
        description=(
            "Identifie le boîtier dans le nom de fichier. Pratique si tu "
            "mélanges plusieurs appareils dans le même dossier."
        ),
        preview="IMG_0001.jpg → Sony ILCE-7M3_20260507_042.jpg",
    ),

    # === 6. Date FR (DD-MM-YYYY) ======================================
    RenameTemplate(
        label="Date FR — JJ-MM-AAAA",
        template="{date:%d-%m-%Y}_{counter:03d}",
        description=(
            "Format français jour-mois-année. "
            "Plus lisible mais moins triable dans l'explorateur (préférer ISO)."
        ),
        preview="IMG_0001.jpg → 07-05-2026_042.jpg",
    ),

    # === 7. Année/Mois sans séparateur ================================
    RenameTemplate(
        label="Année-Mois (YYYY-MM)",
        template="{date:%Y-%m}_{original}",
        description=(
            "Préfixe court (juste année + mois). Utile en complément "
            "d'une organisation par dossier date/mois."
        ),
        preview="IMG_0001.jpg → 2026-05_IMG_0001.jpg",
    ),

    # === 8. Compteur seul =============================================
    RenameTemplate(
        label="Compteur séquentiel uniquement",
        template="photo_{counter:04d}",
        description=(
            "Numérotation simple sans date ni info EXIF. Bon pour un "
            "ensemble homogène (mariage, événement) à publier en série."
        ),
        preview="IMG_0001.jpg → photo_0042.jpg",
    ),

    # === 9. Préfixe personnalisable + compteur =======================
    RenameTemplate(
        label="Préfixe vacances + date",
        template="vacances_{date:%Y%m%d}_{counter:03d}",
        description=(
            "Préfixe thématique fixe + date + compteur. "
            "Édite 'vacances' selon ton événement (mariage, sortie…)."
        ),
        preview="IMG_0001.jpg → vacances_20260507_042.jpg",
    ),

    # === 10. Maximaliste : tout combiné ==============================
    RenameTemplate(
        label="Complet : date + heure + appareil + compteur",
        template="{date:%Y%m%d_%H%M}_{camera}_{counter:04d}",
        description=(
            "Tous les attributs présents. Verbose mais zéro ambiguïté. "
            "À réserver aux archivages méticuleux (workflow pro)."
        ),
        preview="IMG_0001.jpg → 20260507_1430_Sony ILCE-7M3_0042.jpg",
    ),
]


def get_template_by_label(label: str) -> str:
    """Retourne le template correspondant au label, ou '' si introuvable."""
    for tpl in RENAME_TEMPLATES:
        if tpl.label == label:
            return tpl.template
    return ""
