# -*- coding: utf-8 -*-
"""
Dictionnaire centralisé des tooltips PhotoOrganizer (français).

Tous les textes UI complémentaires (info-bulles au survol) vivent ici.
Avantages :
  - Maintenance simple : un seul fichier à modifier pour ajuster un libellé.
  - Auditable : on peut lister les widgets sans tooltip via une simple
    diff entre les attributs du frame et les clés du dictionnaire.
  - Réutilisable : même tooltip pour 2 boutons identiques sur 2 panneaux.

Convention de rédaction :
  - 1 phrase action + effet, ponctuée.
  - Préciser durée (s/min), taille (Mo/Go), valeur par défaut quand pertinent.
  - Format attendu (regex, pattern, casse) si pas évident.
  - Éviter le jargon technique sauf si déjà visible dans l'IHM.

Exemple :
    "Lance le scan des doublons sur le dossier sélectionné. "
    "Peut prendre plusieurs minutes selon la taille (1000 fichiers ≈ 30 s)."
"""

# =============================================================================
# OrganizeFrame — Sélection des dossiers
# =============================================================================

ORGANIZE = {
    # ---- Champs Source(s) / Destination ----
    "source_entry": (
        "Dossier(s) source à organiser. Plusieurs chemins possibles "
        "séparés par ';' (ex. : C:\\Photos2024;D:\\Vacances). "
        "Tu peux aussi glisser-déposer des dossiers depuis l'explorateur."
    ),
    "browse_source": "Parcourir et sélectionner le dossier source principal.",
    "add_source": "Ajouter un dossier source supplémentaire à la liste actuelle.",

    "dest_entry": (
        "Dossier de destination où les photos seront organisées. "
        "Sera créé si inexistant. Ex. : D:\\Photos_organisees"
    ),
    "browse_dest": "Parcourir et sélectionner le dossier de destination.",
    "open_dest":   "Ouvre le dossier de destination dans l'explorateur Windows.",

    "file_count": (
        "Nombre de fichiers détectés dans la source avec les filtres actuels. "
        "Mis à jour automatiquement quand tu changes la source ou les types."
    ),

    # ---- Critères d'organisation ----
    "by_date": (
        "Range les photos dans des dossiers selon leur date de prise de vue (EXIF). "
        "Si pas d'EXIF, fallback sur 'Sans date'."
    ),
    "date_format": (
        "Hiérarchie de dossiers par date. Ex. 'year/month/day' donne "
        "2026/03/2026_03_07/photo.jpg ; 'year' donne juste 2026/photo.jpg."
    ),
    "by_camera": (
        "Range par marque + modèle d'appareil photo (lu dans l'EXIF). "
        "Ex. : Sony ILCE-7M3/. Fallback : 'Appareil inconnu'."
    ),
    "by_location": (
        "Range par lieu géographique (GPS EXIF). Active la sous-section "
        "Géocodage pour avoir des noms de villes au lieu de coordonnées."
    ),
    "use_geocoding": (
        "Convertit les coordonnées GPS en noms de lieux (ex. 'Paris') "
        "via OpenStreetMap. Décoché : sous-dossiers Lat_X.X_Lon_Y.Y."
    ),
    "max_distance": (
        "Distance max (km) pour regrouper plusieurs photos dans le même lieu. "
        "Typique : 1 km en ville, 5–10 km à la campagne. Précision 100 m."
    ),

    # ---- Mode multicouche ----
    "multilayer": (
        "Combine plusieurs critères en cascade. Ex. coché + Date + Appareil → "
        "Année/Mois/Appareil/photo.jpg. Décoché : un seul critère actif."
    ),
    "criteria_order_btn": (
        "Réordonne les critères en mode multicouche : ▲ remonte, ▼ descend. "
        "L'ordre détermine la hiérarchie de dossiers générée."
    ),

    # ---- Action / conflits ----
    "copy_radio": (
        "Copie les fichiers (l'original reste dans la source). "
        "Plus sûr mais utilise 2× l'espace disque."
    ),
    "move_radio": (
        "Déplace les fichiers (l'original disparaît de la source). "
        "Économe en espace, mais irréversible sans rollback."
    ),
    "recursive": (
        "Inclut les sous-dossiers de la source. Décoché : seulement le dossier "
        "racine est scanné."
    ),
    "include_images": (
        "Inclut JPG/JPEG, PNG, GIF, BMP, TIFF/TIF, WebP, JFIF, JP2, "
        "AVIF, HEIC/HEIF."
    ),
    "include_raw": (
        "Inclut tous les RAW grand public : ARW, CR2, CR3, NEF, DNG, ORF, "
        "RW2, RAF, PEF, SRW, SR2, X3F, MEF, IIQ, RWL, K25, KDC, MRW, ERF, NRW."
    ),
    "include_videos": (
        "Inclut MP4, MOV, AVI, MKV, WMV, M4V, MPG/MPEG, 3GP, FLV, WebM, "
        "MTS/TS, VOB. Décoché par défaut."
    ),

    # ---- Filtres avancés (R1) ----
    "filter_date_min": (
        "Ne garde que les photos prises à partir de cette date. "
        "Format : YYYY-MM-DD. Ex. : 2024-06-01."
    ),
    "filter_date_max": (
        "Ne garde que les photos prises jusqu'à cette date. "
        "Format : YYYY-MM-DD."
    ),
    "filter_size_min": (
        "Taille minimale d'un fichier pour être traité. "
        "Ex. : '100KB' rejette les vignettes ; '1MB' rejette les petites JPG."
    ),
    "filter_size_max": (
        "Taille maximale. Ex. : '50MB' rejette les vidéos longues. "
        "Vide = pas de limite haute."
    ),
    "filter_rating_min": (
        "Note EXIF/XMP minimale (0-5). 0 = pas de filtre. "
        "3 ou 4 typique pour ne garder que les bonnes photos."
    ),
    "filter_keywords": (
        "Mots-clés EXIF ou XMP à chercher (séparés par ,). "
        "Match si AU MOINS UN mot-clé est trouvé. Ex. : vacances, mariage."
    ),
    "filter_camera_make": (
        "Limite l'organisation aux photos prises avec ces marques. "
        "CSV — ex. : Sony,Canon. Vide = toutes les marques. "
        "Le bouton 💡 ouvre un panneau avec marques courantes et celles "
        "détectées dans le dossier source."
    ),
    "brand_examples_btn": (
        "Ouvre un panneau d'exemples : marques courantes + celles détectées "
        "dans la source. Un clic sur une marque l'ajoute au champ."
    ),
    "filter_examples_btn": (
        "Ouvre un panneau d'exemples standards pour les filtres : mots-clés "
        "EXIF courants, extensions images/RAW/vidéos, dimensions classiques "
        "(Full HD, 4K…), orientation et note. Un clic = remplit le champ "
        "correspondant. La date et la taille restent à saisir librement "
        "(valeurs propres à chaque utilisateur)."
    ),

    # ---- Comportements avancés ----
    "skip_if_identical": (
        "Si un fichier identique existe déjà à destination (même hash), "
        "on l'ignore au lieu de le renommer en _1, _2…"
    ),
    "keep_raw_jpeg_pairs": (
        "Si IMG_001.CR2 ET IMG_001.JPG existent, garde-les ensemble dans le "
        "même dossier de destination, même si leurs critères diffèrent."
    ),
    "cleanup_empty_source": (
        "Après un MOVE, supprime les sous-dossiers source devenus vides. "
        "Ne s'applique pas en mode COPY."
    ),
    "validate_disk_space": (
        "Vérifie qu'il y a assez d'espace libre à destination avant de lancer "
        "(somme des tailles vs shutil.disk_usage)."
    ),
    "notify_on_finish": (
        "Notification système Windows à la fin de l'organisation, "
        "avec récap : N fichiers traités. Non-bloquante."
    ),
    "incremental_mode": (
        "Skip les fichiers déjà traités lors d'une session précédente. "
        "Cache persistant : <destination>/.photoorganizer_index.json."
    ),
    "detect_bursts": (
        "Détecte les rafales (photos prises à < N secondes d'écart) et les "
        "regroupe dans un sous-dossier Burst_NN/ pour chaque série."
    ),
    "burst_mode_manual": (
        "Seuil fixe défini par l'utilisateur (Écart max en secondes). "
        "Recommandé quand tu connais le rythme de prise (3-5 s typique)."
    ),
    "burst_mode_auto": (
        "Seuil calculé automatiquement à partir des écarts du dossier : "
        "moyenne(Δ) − écart-type. Plus précis sur dossiers hétérogènes. "
        "Fallback manuel si moins de 3 photos datées."
    ),
    "burst_threshold": "Écart maximum entre 2 photos pour les considérer dans la même rafale.",
    "burst_min_count": "Nombre minimum de photos pour qu'une série soit considérée comme rafale.",
    "export_index_csv":  "Génère un fichier CSV listant toutes les opérations effectuées.",
    "export_index_json": "Génère un fichier JSON listant toutes les opérations effectuées.",

    # ---- Renommage (template) ----
    "rename_template": (
        "Modèle de renommage des fichiers. Tokens : {original}, {ext}, "
        "{date:%Y%m%d}, {camera}, {counter:03d}. "
        "Vide = nom d'origine conservé. Ex. : {date:%Y%m%d}_{counter:04d}."
    ),
    "rename_preview": "Aperçu du résultat avec une date et un nom factices.",

    # ---- Presets ----
    "preset_menu": "Charge un preset de configuration sauvegardé.",
    "preset_save": "Enregistre la configuration courante comme nouveau preset.",
    "preset_delete": "Supprime le preset actuellement sélectionné.",

    # ---- Boutons d'action ----
    "btn_analyze": (
        "Analyse les fichiers (EXIF, dates, appareils, GPS) sans rien copier. "
        "Affiche des stats : 1000 fichiers ≈ 10–30 s."
    ),
    "btn_preview": (
        "Aperçu de l'arborescence cible (100 premiers fichiers) sans copier. "
        "Permet de valider la config avant l'organisation réelle."
    ),
    "btn_organize": (
        "Lance la copie ou le déplacement vers la destination selon les "
        "critères choisis. Peut prendre plusieurs minutes (1000 fichiers ≈ 30 s)."
    ),
    "btn_cancel": (
        "Annule l'opération coopérativement : le worker s'arrête entre 2 fichiers "
        "(latence ≤ 1 s en général). Les fichiers déjà traités ne sont pas "
        "restaurés (utiliser Historique). Patientez quelques secondes avant de relancer."
    ),

    # ---- Toggle Avancé ----
    "advanced_toggle": (
        "Affiche/masque les options avancées (filtres, comportements, "
        "bursts, mode incrémental, index)."
    ),
}


# =============================================================================
# DuplicatesFrame
# =============================================================================

DUPLICATES = {
    "source_entry": (
        "Dossier à analyser pour rechercher les doublons. "
        "Ex. : D:\\Photos2024."
    ),
    "browse_source": "Parcourir et sélectionner le dossier à scanner.",

    "load_config": "Charge une configuration depuis un fichier YAML.",
    "save_config": "Sauvegarde la configuration courante dans un fichier YAML.",
    "browse_dest": (
        "Parcourir et sélectionner le dossier de destination "
        "(mode Déplacer uniquement)."
    ),

    # Modes
    "mode_dry_run": (
        "Simulation : analyse + propose des actions, mais NE TOUCHE À RIEN. "
        "Recommandé pour la première exécution."
    ),
    "mode_delete": (
        "Supprime définitivement les doublons. ⚠️ IRRÉVERSIBLE — "
        "préférer Corbeille pour rester safe."
    ),
    "mode_move": (
        "Déplace les doublons vers un dossier dédié (utile pour archivage)."
    ),
    "mode_trash": (
        "Envoie les doublons à la corbeille système. Récupérable depuis "
        "la corbeille Windows."
    ),

    # Hashing
    "algorithm": (
        "Algorithme de hash. SHA-256 par défaut (plus sûr). "
        "BLAKE3 plus rapide si dispo. MD5/SHA1 acceptables pour de la dedup non-cryptographique."
    ),
    "chunk_size": (
        "Taille des blocs lus à chaque itération du hash. "
        "Plus grand = plus rapide sur SSD, plus de RAM. 4 MB raisonnable."
    ),
    "quick_mode": (
        "Hash partiel (début + fin du fichier seulement) pour un pré-filtrage rapide. "
        "Suivi d'un hash complet sur les candidats pour fiabilité."
    ),
    "use_cache": (
        "Réutilise les hash calculés lors des sessions précédentes. "
        "Cache persistant SQLite. Accélère ×10+ les re-scans."
    ),

    # Filtres
    "include_images": (
        "Inclut JPG/JPEG, PNG, GIF, BMP, TIFF/TIF, WebP, JFIF, JP2, "
        "AVIF, HEIC/HEIF."
    ),
    "include_raw": (
        "Inclut tous les RAW grand public : ARW, CR2, CR3, NEF, DNG, ORF, "
        "RW2, RAF, PEF, SRW, K25, KDC, MRW, ERF, NRW, etc."
    ),
    "include_videos": "Inclut MP4, MOV, AVI, MKV, WMV, M4V, MPG, etc.",
    "recursive":      "Inclut les sous-dossiers de la source.",
    "min_size": (
        "Taille min des fichiers analysés. Ex. : '100KB' évite de doubler "
        "des miniatures. Format : '1KB', '5MB', '500B'."
    ),
    "max_size": (
        "Taille max. Vide = pas de limite. Ex. : '500MB' pour ignorer les vidéos."
    ),

    # Conservation
    "use_priority_folder": (
        "Active le critère 'dossier prioritaire' : si un doublon est dans "
        "un dossier déclaré prioritaire, c'est lui qu'on garde."
    ),
    "use_preferred_ext": (
        "Active le critère 'extension préférée' : on garde RAW > TIFF > JPEG "
        "(pour conserver la plus grande qualité)."
    ),
    "date_criterion": (
        "Si plusieurs doublons restent en compétition, on choisit le plus "
        "ancien (oldest) ou le plus récent (newest). 'none' = pas de critère date."
    ),
    "path_criterion": (
        "Si égalité, on choisit le chemin le plus court (souvent racine "
        "principale) ou le plus long (souvent sous-dossier précis). "
        "'none' = pas de critère chemin."
    ),
    "priority_dirs": (
        "Liste de dossiers prioritaires séparés par ;. Ex. : "
        "D:\\Photos_principal;C:\\Backups. Ces fichiers sont gardés en priorité."
    ),
    "add_priority_dir": "Ajoute un dossier prioritaire via le sélecteur.",

    # Performance
    "workers": (
        "Nombre de threads parallèles pour le hashing. "
        "0 = auto (~ nb cœurs CPU). Plus = plus rapide mais plus chaud."
    ),
    "verify_before_delete": (
        "Recalcule le hash avant chaque suppression pour éviter de perdre "
        "un fichier modifié entre le scan et l'exécution. Plus lent mais sûr."
    ),

    # Rapports
    "generate_csv":  "Génère un rapport tabulaire (Excel-compatible).",
    "generate_json": "Génère un rapport structuré (intégration outils).",
    "generate_txt":  "Génère un rapport lisible humain (résumé + détails).",
    "report_dir":    "Dossier où écrire les rapports. Vide = à côté de la source.",
    "browse_report_dir": "Parcourir et sélectionner le dossier de rapports.",

    # Boutons
    "btn_search":  (
        "Lance le scan et l'analyse. Phase 1 : indexation + hashing. "
        "Phase 2 : détection des groupes. 1000 fichiers ≈ 20–60 s."
    ),
    "btn_execute": (
        "Exécute les actions planifiées (selon le Mode choisi). "
        "Toujours simulation d'abord pour vérifier."
    ),
    "btn_cancel":  (
        "Annule le scan ou l'exécution coopérativement : le worker s'arrête "
        "entre 2 fichiers (latence ≤ 1 s en général). Patientez avant de relancer."
    ),
    "btn_empty_quarantine": (
        "Vide la quarantaine interne en envoyant les fichiers vers la corbeille "
        "du système. Avant cette action, les fichiers placés en quarantaine via "
        "le mode « Corbeille (récupérable) » peuvent être restaurés par "
        "« ↩️ Annuler dernière » dans l'onglet Historique. Après vidage, ils "
        "passent en corbeille Windows : récupérables uniquement via l'Explorateur."
    ),
}


# =============================================================================
# HistoryFrame
# =============================================================================

HISTORY = {
    "history_textbox": (
        "Liste des opérations effectuées dans la session courante. "
        "Format : [✓/✗] type De → Vers. Effacé à la fermeture de l'app."
    ),
    "rollback_one":  (
        "Annule la dernière opération réussie : restaure le fichier à son "
        "emplacement d'origine (ou supprime la copie créée)."
    ),
    "rollback_all":  (
        "Annule TOUTES les opérations de la session, en ordre inverse. "
        "Affiche un récap (success/failed/skipped)."
    ),
    "refresh":   "Recharge la liste depuis l'historique du FileManager.",
    "btn_clear": (
        "Efface l'historique sans toucher aux fichiers. "
        "Les rollbacks ne seront plus possibles après."
    ),
}


# =============================================================================
# SettingsFrame
# =============================================================================

SETTINGS = {
    "theme_dark":   "Thème sombre — fond noir, texte clair. Réduit la fatigue oculaire.",
    "theme_light":  "Thème clair grisé — fond gris, texte foncé.",
    "theme_system": "Suit automatiquement le thème Windows.",

    "default_action_copy": "Copier sera proposé par défaut au démarrage suivant.",
    "default_action_move": "Déplacer sera proposé par défaut au démarrage suivant.",
    "recursive_default": "Active 'Parcourir sous-dossiers' par défaut au démarrage.",

    "cache_enabled": (
        "Active le cache local des métadonnées EXIF (SQLite). "
        "Accélère les re-scans (×10) — lecture EXIF coûteuse."
    ),
    "btn_clear_cache": (
        "Vide le cache des métadonnées. Le prochain scan relira tout l'EXIF."
    ),

    "geocoding_enabled": (
        "Active le géocodage inverse (GPS → nom de lieu). "
        "Nécessite une connexion internet (OpenStreetMap)."
    ),
    "api_key": (
        "Clé API PositionStack pour un géocodage prioritaire. "
        "Optionnel — sans clé, fallback sur OpenStreetMap (gratuit, limité 1 req/s)."
    ),

    "log_level": (
        "Niveau de verbosité des logs. INFO par défaut. "
        "DEBUG = tout (gros fichiers). ERROR = uniquement les pannes. "
        "Effet immédiat — pas besoin de redémarrer."
    ),
    "btn_view_logs": (
        "Ouvre le dossier des logs dans l'explorateur. "
        "Chemin : %LOCALAPPDATA%\\PhotoOrganizer\\logs (Windows)."
    ),
    "btn_clear_recent": "Vide la liste des dossiers source/destination récents.",

    "schedule_enabled": (
        "Active une organisation automatique quotidienne. "
        "Tant que l'application est ouverte, déclenche à l'heure indiquée."
    ),
    "schedule_time": (
        "Heure de déclenchement quotidien au format HH:MM. Ex. : 23:00, 02:30."
    ),

    "btn_save":  "Enregistre tous les paramètres dans le fichier de config utilisateur.",
    "btn_reset": (
        "Réinitialise tous les paramètres aux valeurs par défaut. "
        "Confirmation requise."
    ),
}


# =============================================================================
# App root (header)
# =============================================================================

APP = {
    "btn_theme": "Bascule entre thème clair et sombre.",
    "btn_help":  "À propos de PhotoOrganizer (version, fonctionnalités, licence).",
}
