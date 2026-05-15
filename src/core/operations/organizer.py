"""
Module d'organisation intelligente des fichiers média.
Organisation par date, appareil photo, localisation.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..metadata import extract_date, get_camera_info, get_exif_data, get_gps_coordinates
from ..metadata.gps_processor import get_processor as get_gps_processor
from .file_manager import FileManager

logger = logging.getLogger(__name__)


@dataclass
class OrganizationOptions:
    """Options d'organisation des fichiers.

    Sections :
        - Critères d'organisation (date, camera, location)
        - Action (copy / move) et conflits (auto_rename, skip_existing)
        - Filtres pré-traitement (date, taille, rating, mots-clés)
        - Comportements avancés (skip_if_identical, keep_raw_jpeg_pairs,
          cleanup_empty_source, validate_disk_space)
        - Renommage par template
        - Index export (CSV / JSON)
    """

    # ---- Critères ----
    organize_by_date: bool = True
    organize_by_camera: bool = False
    organize_by_location: bool = False
    multilayer: bool = False
    criteria_order: List[str] = field(default_factory=lambda: ["date", "camera", "location"])
    date_format: str = "year/month/day"
    max_distance_km: float = 1.0
    use_geocoding: bool = True

    # ---- Action / conflits ----
    copy_not_move: bool = True
    auto_rename: bool = True
    skip_existing: bool = False

    # ---- Filtres pré-traitement (R1) ----
    # Une valeur None / 0 / [] désactive le filtre.
    date_min: Optional[datetime] = None
    date_max: Optional[datetime] = None
    size_min_bytes: int = 0
    size_max_bytes: Optional[int] = None
    rating_min: int = 0  # 0..5, 0 = pas de filtre
    keywords_filter: List[str] = field(default_factory=list)  # OR : un seul match suffit

    # ---- Comportements avancés ----
    skip_if_identical: bool = False  # R2 : si dest existe ET hash identique → skip
    keep_raw_jpeg_pairs: bool = False  # R3 : co-localiser les paires *.RAW + *.JPG
    cleanup_empty_source: bool = False  # R5 : supprimer dossiers vides du source post-MOVE
    validate_disk_space: bool = True  # R6 : check espace dispo avant exécution

    # ---- Renommage (Q4) ----
    # Template de nom de fichier final. Si None → nom d'origine conservé.
    # Tokens supportés : {original}, {ext}, {date:%Y%m%d}, {camera}, {counter:03d}
    rename_template: Optional[str] = None

    # ---- Index export (R7) ----
    export_index_csv: bool = False
    export_index_json: bool = False

    # ---- Détection de bursts / rafales (S1) ----
    # Si actif, les photos prises à moins de ``burst_threshold_seconds``
    # d'écart sont regroupées dans un sous-dossier ``Burst_NN/`` à
    # l'intérieur de leur dossier de destination habituel. Seuils par
    # défaut : 3 photos minimum, dans une fenêtre de 3 secondes.
    #
    # Mode (audit 2026-05-15) :
    #   "manual" : seuil fixe = ``burst_threshold_seconds`` (défaut)
    #   "auto"   : seuil calculé = max(1, mean(deltas) - stddev(deltas))
    #              sur les écarts entre photos consécutives du dossier.
    detect_bursts: bool = False
    burst_mode: str = "manual"  # "manual" | "auto"
    burst_threshold_seconds: int = 3
    burst_min_count: int = 3

    # ---- Mode incrémental (S5) ----
    # Persiste un index ``.photoorganizer_index.json`` dans la destination,
    # indexé par hash partiel (head+tail BLAKE2). Au lancement suivant,
    # tout fichier source dont le hash est déjà dans l'index est ignoré.
    incremental_mode: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrganizationOptions":
        """Crée une instance depuis un dictionnaire (utilisé par les presets)."""
        return cls(**{k: data[k] for k in data if k in cls.__dataclass_fields__})


@dataclass
class OrganizationResult:
    """Résultat d'une organisation."""

    total: int = 0
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)
    operations: List[Dict] = field(default_factory=list)
    # ---- Statistiques GPS pour la modale résultat ----
    files_with_gps: int = 0
    files_without_gps: int = 0
    files_geocoded: int = 0  # nom de lieu résolu (Nominatim/PositionStack)
    files_raw_coords: int = 0  # fallback Lat_x_Lon_y


class SmartOrganizer:
    """Organiseur intelligent de fichiers média."""

    DATE_FORMATS = {
        "year/month/day": "{year}/{month}/{year}_{month}_{day}",
        "year/month": "{year}/{year}_{month}",
        "year": "{year}",
        "year_month_day": "{year}_{month}_{day}",
        "year_month": "{year}_{month}",
    }

    # Extensions RAW utilisées pour la détection des paires (Lot R3).
    # Lot F (audit 2026-05-15) : élargi avec .k25/.kdc/.mrw/.erf/.nrw —
    # synchro avec FileManager.EXTENSIONS pour cohérence des paires RAW+JPEG.
    RAW_EXTENSIONS = frozenset(
        {
            ".raw",
            ".arw",
            ".cr2",
            ".cr3",
            ".nef",
            ".orf",
            ".rw2",
            ".dng",
            ".3fr",
            ".raf",
            ".pef",
            ".srw",
            ".sr2",
            ".x3f",
            ".mef",
            ".iiq",
            ".rwl",
            ".k25",
            ".kdc",
            ".mrw",
            ".erf",
            ".nrw",
        }
    )
    # Compagnons JPEG des paires RAW.
    JPEG_EXTENSIONS = frozenset({".jpg", ".jpeg", ".jfif"})

    def __init__(self, file_manager: Optional[FileManager] = None):
        """
        Initialise l'organiseur.

        Args:
            file_manager: Gestionnaire de fichiers (créé si non fourni)
        """
        self.file_manager = file_manager or FileManager()
        self.gps_processor = get_gps_processor()
        self._cancel_requested = False
        # Ces deux structures sont initialisées par `organize()` et utilisées
        # pendant `_process_file`. Elles évitent de recalculer les paires et
        # permettent de tracer l'index post-traitement (R7).
        self._raw_jpeg_pairs: Dict[str, List[str]] = {}  # stem -> [paths]
        self._index_records: List[Dict[str, Any]] = []
        self._counter = 0  # pour les templates {counter:03d}
        # S1 : map file_path -> burst_id (str ou None si solo). Calculé
        # une fois par appel à organize() pour éviter de relire les EXIF.
        self._burst_membership: Dict[str, Optional[str]] = {}
        # S1 bis (audit 2026-05-15) : map file_path -> dossier-destination
        # pré-calculé. Sert à grouper les bursts PAR dossier-destination
        # final (au lieu du batch global) tout en évitant la double
        # résolution dans _process_file (qui réutilise le cache).
        self._destination_cache: Dict[str, str] = {}
        # S5 : set des hash deja organises (loade depuis l'index a
        # destination). Sert au pre-filtrage avant copy/move.
        self._known_hashes: set = set()

    def organize(
        self,
        file_paths: List[str],
        target_dir: str,
        options: OrganizationOptions,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> OrganizationResult:
        """
        Organise les fichiers selon les options spécifiées.

        Pipeline :
          1. Pré-filtrage (date / taille / rating / mots-clés) — pre-scan léger
          2. Détection des paires RAW+JPEG si l'option est active (Lot R3)
          3. Validation de l'espace disque (Lot R6, opt-in via flag)
          4. Démarrage session FileManager
          5. Traitement fichier par fichier via `_process_file`
          6. Cleanup post-MOVE (Lot R5)
          7. Export d'index CSV/JSON (Lot R7)

        Args:
            file_paths: Liste des fichiers à organiser
            target_dir: Répertoire de destination
            options: Options d'organisation
            progress_callback: Callback de progression (current, total, message)

        Returns:
            OrganizationResult avec les statistiques
        """
        self._cancel_requested = False
        # Reset des états de session
        self._raw_jpeg_pairs.clear()
        self._index_records.clear()
        self._counter = 0

        # 1) Pré-filtrage : on garde la liste originale comme `total` mais on
        # ne traite que `eligible_files`. Les rejetés comptent en `skipped`.
        eligible_files: List[str] = []
        rejected = 0
        for fp in file_paths:
            try:
                if self._passes_filters(fp, options):
                    eligible_files.append(fp)
                else:
                    rejected += 1
            except Exception as exc:
                logger.warning(f"Pré-filtre erreur sur {fp}: {exc}")
                eligible_files.append(fp)  # en cas de doute on garde

        result = OrganizationResult(total=len(file_paths))
        result.skipped = rejected  # compte les filtres immédiatement

        if not eligible_files:
            return result

        # 2) Détection paires RAW+JPEG (Lot R3) — uniquement si activé
        if options.keep_raw_jpeg_pairs:
            self._raw_jpeg_pairs = self._detect_raw_jpeg_pairs(eligible_files)

        # 2 bis) Détection des bursts / rafales (Lot S1)
        #
        # Audit 2026-05-15 : on regroupe les fichiers par dossier-
        # destination FINAL avant d'appeler ``_detect_bursts``. Avant ce
        # changement, le mean/stddev du mode auto était calculé sur tout
        # le batch — ce qui n'a pas de sens quand le batch couvre
        # plusieurs voyages / années (Δ inter-dossiers >> Δ intra-burst).
        # En groupant par dossier final, le calcul mean/stddev colle à
        # la demande utilisateur : « delta moyen entre photos du dossier ».
        # Bonus : la numérotation ``Burst_NN`` repart à 01 dans chaque
        # dossier puisqu'on rappelle ``_detect_bursts`` par groupe.
        self._burst_membership.clear()
        self._destination_cache.clear()
        if options.detect_bursts:
            by_folder: Dict[str, List[str]] = {}
            for fp in eligible_files:
                try:
                    folder = self._resolve_destination_folder(fp, target_dir, options, result=result)
                except Exception as exc:
                    logger.debug(f"Pre-calcul destination echoue pour {fp}: {exc}")
                    folder = target_dir
                self._destination_cache[fp] = folder
                by_folder.setdefault(folder, []).append(fp)
            for folder, paths_in_folder in by_folder.items():
                sub = self._detect_bursts(
                    paths_in_folder,
                    threshold_seconds=options.burst_threshold_seconds,
                    min_count=options.burst_min_count,
                    mode=getattr(options, "burst_mode", "manual"),
                )
                self._burst_membership.update(sub)

        # 2 ter) Mode incrémental (Lot S5) : on charge l'index existant
        # à destination et on filtre les fichiers déjà organisés.
        self._known_hashes.clear()
        if options.incremental_mode:
            self._known_hashes = self._load_incremental_index(target_dir)
            if self._known_hashes:
                before = len(eligible_files)
                eligible_files = [fp for fp in eligible_files if not self._is_already_indexed(fp)]
                already = before - len(eligible_files)
                if already:
                    logger.info(f"Mode incremental : {already} fichier(s) deja indexes, ignores")
                    result.skipped += already

        # 3) Validation espace disque (Lot R6)
        if options.validate_disk_space:
            ok, msg = self._validate_disk_space(eligible_files, target_dir)
            if not ok:
                # On loggue + on remonte une erreur dans result mais on ne
                # bloque pas (la décision de poursuivre revient à l'appelant
                # via une éventuelle case "ignorer cette validation"). Pour
                # simplifier ici, on enregistre comme une erreur globale.
                result.errors = 1
                result.error_messages.append(msg)
                logger.error(msg)
                # On poursuit malgré tout — copy/move échouera proprement
                # avec l'erreur OS standard.

        # Créer le répertoire de destination
        os.makedirs(target_dir, exist_ok=True)

        # 4) Démarrer une session FileManager
        self.file_manager.start_session()

        # 5) Traitement
        total = len(eligible_files)
        for i, file_path in enumerate(eligible_files):
            if self._cancel_requested:
                logger.info("Organisation annulée par l'utilisateur")
                break

            if progress_callback:
                progress_callback(i + 1, total, os.path.basename(file_path))

            try:
                success = self._process_file(file_path, target_dir, options, result=result)
                if success:
                    result.processed += 1
                else:
                    result.skipped += 1
            except Exception as e:
                result.errors += 1
                result.error_messages.append(f"{os.path.basename(file_path)}: {str(e)}")
                logger.error(f"Erreur traitement {file_path}: {e}")

        # 6) Cleanup des dossiers vides du source (Lot R5) — uniquement
        # après un MOVE réussi (en mode COPY rien ne disparaît).
        if options.cleanup_empty_source and not options.copy_not_move:
            self._cleanup_source_dirs(file_paths)

        # 7) Export index (Lot R7)
        if options.export_index_csv or options.export_index_json:
            self._export_index(target_dir, options)

        # 8) Mise à jour de l'index incrémental persistant (Lot S5).
        # Le fichier reste à destination entre les exécutions et permet
        # de skipper rapidement les fichiers déjà organisés au prochain run.
        if options.incremental_mode and self._index_records:
            self._save_incremental_index(target_dir)

        return result

    def _resolve_destination_folder(
        self,
        file_path: str,
        target_dir: str,
        options: OrganizationOptions,
        result: Optional["OrganizationResult"] = None,
    ) -> str:
        """Calcule le dossier-destination final (sans sous-dossier Burst_NN/).

        Méthode partagée par :
          * ``_process_file`` — calcul + comptage des stats GPS pour
            chaque fichier réellement traité.
          * ``organize()`` étape 2bis — pré-calcul pour grouper les
            fichiers par dossier final avant détection de bursts.

        Le résultat des deux appels est identique grâce au cache LRU
        de ``gps_processor`` (~aucun coût HTTP redondant).

        Quand ``result`` est ``None``, les compteurs GPS ne sont pas
        incrémentés — utile si l'appelant souhaite ne pas
        double-compter (par exemple lors d'un pré-calcul).
        """
        # Lire les métadonnées (EXIF + GPS) — ne lève pas si absent
        exif_data = get_exif_data(file_path)
        date_taken, _ = extract_date(file_path, exif_data, return_origin=True)
        make, model = get_camera_info(exif_data, file_path)
        gps_coords = get_gps_coordinates(file_path)

        # Déterminer l'ordre des critères (mode mono vs multilayer)
        if options.multilayer:
            criteria = options.criteria_order
        else:
            if options.organize_by_date:
                criteria = ["date"]
            elif options.organize_by_camera:
                criteria = ["camera"]
            elif options.organize_by_location:
                criteria = ["location"]
            else:
                criteria = []

        current_path = target_dir
        for criterion in criteria:
            if criterion == "date" and options.organize_by_date:
                current_path = self._apply_date_organization(current_path, date_taken, options.date_format)
            elif criterion == "camera" and options.organize_by_camera:
                current_path = self._apply_camera_organization(current_path, make, model)
            elif criterion == "location" and options.organize_by_location:
                current_path = self._apply_location_organization(
                    current_path,
                    gps_coords,
                    options.use_geocoding,
                    result=result,
                )
        return current_path

    def _process_file(
        self,
        file_path: str,
        target_dir: str,
        options: OrganizationOptions,
        result: Optional["OrganizationResult"] = None,
    ) -> bool:
        """Traite un seul fichier.

        ``result`` (optionnel) reçoit les compteurs de stats GPS via
        ``_apply_location_organization`` — sauf si le dossier de
        destination a déjà été pré-calculé pour la détection de bursts
        (auquel cas les compteurs ont déjà été incrémentés et on
        réutilise le cache pour éviter le double comptage).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier inexistant: {file_path}")

        # Métadonnées EXIF — nécessaires pour le renommage template et
        # les paires RAW/JPEG, donc relues même quand le dossier a été
        # pré-calculé. Coût négligeable (< 1 ms par fichier).
        exif_data = get_exif_data(file_path)
        date_taken, date_origin = extract_date(file_path, exif_data, return_origin=True)
        make, model = get_camera_info(exif_data, file_path)

        # Dossier-destination : réutilise le cache si il a été rempli
        # par l'étape 2bis (mode bursts). Sinon résolution standard avec
        # comptage des stats GPS.
        cached_dest = self._destination_cache.get(file_path)
        if cached_dest is not None:
            current_path = cached_dest
        else:
            current_path = self._resolve_destination_folder(file_path, target_dir, options, result=result)

        # S1 — Sous-dossier Burst_NN/ si le fichier appartient à une rafale.
        # On ne crée le sous-dossier QUE pour les vrais bursts (≥ min_count).
        burst_id = self._burst_membership.get(file_path) if options.detect_bursts else None
        if burst_id:
            current_path = os.path.join(current_path, burst_id)
            os.makedirs(current_path, exist_ok=True)

        # Déterminer le chemin final — appliquer le template de renommage
        # si configuré (Lot Q4), sinon garder le nom d'origine.
        original_name = os.path.basename(file_path)
        self._counter += 1
        if options.rename_template:
            try:
                final_name = self._apply_rename_template(
                    original_name,
                    options.rename_template,
                    date_taken,
                    make,
                    model,
                    self._counter,
                )
            except Exception as exc:
                logger.warning(f"Template de renommage echoue pour {original_name}: {exc}")
                final_name = original_name
        else:
            final_name = original_name

        dest_path = os.path.join(current_path, final_name)

        # Vérifier si on doit ignorer les existants
        if options.skip_existing and os.path.exists(dest_path):
            return False

        # Skip si fichier identique deja a destination (Lot R2). Compare via
        # un hash partiel (rapide, suffisant pour deduper la grande majorite
        # des cas — collision possible mais negligeable sur des photos).
        if options.skip_if_identical and os.path.exists(dest_path):
            try:
                if self._files_are_identical(file_path, dest_path):
                    logger.debug(f"Skip identique : {dest_path}")
                    return False
            except OSError as exc:
                logger.debug(f"Comparaison hash echouee : {exc}")

        # Copier ou déplacer
        if options.copy_not_move:
            operation = self.file_manager.copy_file(file_path, dest_path, auto_rename=options.auto_rename)
        else:
            operation = self.file_manager.move_file(file_path, dest_path, auto_rename=options.auto_rename)

        # Enregistrer dans l'index de session pour export ultérieur (R7)
        # ainsi que pour le mode incrémental (S5) qui réutilise l'index.
        if operation.success:
            try:
                size = os.path.getsize(operation.destination)
            except OSError:
                size = 0
            # Hash partiel (head+tail) pour le mode incrémental S5 — calculé
            # uniquement si demandé pour ne pas pénaliser les organisations
            # standard. C'est aussi la clé du cache .photoorganizer_index.json.
            h = ""
            if options.incremental_mode or options.export_index_csv or options.export_index_json:
                try:
                    h = _quick_hash(operation.destination)
                except OSError:
                    h = ""
            self._index_records.append(
                {
                    "source": file_path,
                    "destination": operation.destination,
                    "date": date_taken.isoformat() if date_taken else "",
                    "camera": f"{make} {model}".strip(),
                    "size_bytes": size,
                    "hash": h,
                    "action": operation.operation_type,
                    "burst_id": burst_id or "",
                }
            )

        # Companion RAW+JPEG (Lot R3) : si le fichier traité fait partie d'une
        # paire, on transfère aussi son partenaire dans le même dossier de
        # destination, avec le même comportement (copy/move).
        if operation.success and options.keep_raw_jpeg_pairs:
            self._handle_raw_jpeg_companion(file_path, current_path, options)

        return operation.success

    def _handle_raw_jpeg_companion(
        self,
        primary_path: str,
        target_dir: str,
        options: OrganizationOptions,
    ):
        """Transfère le compagnon RAW/JPEG dans le même dossier que le primaire."""
        from pathlib import Path

        stem = Path(primary_path).stem.lower()
        partners = self._raw_jpeg_pairs.get(stem, [])
        for partner in partners:
            if partner == primary_path:
                continue
            # Ne pas re-traiter si déjà fait
            if any(rec["source"] == partner for rec in self._index_records):
                continue
            partner_dest = os.path.join(target_dir, os.path.basename(partner))
            if os.path.exists(partner_dest) and options.skip_existing:
                continue
            try:
                if options.copy_not_move:
                    self.file_manager.copy_file(partner, partner_dest, auto_rename=options.auto_rename)
                else:
                    self.file_manager.move_file(partner, partner_dest, auto_rename=options.auto_rename)
                logger.debug(f"Companion RAW/JPEG copie : {partner}")
            except Exception as exc:
                logger.warning(f"Echec compagnon {partner}: {exc}")

    def _apply_date_organization(self, base_path: str, date_taken: Optional[datetime], date_format: str) -> str:
        """Applique l'organisation par date."""
        if not date_taken:
            return os.path.join(base_path, "Sans date")

        # Formater la date
        year = str(date_taken.year)
        month = f"{date_taken.month:02d}"
        day = f"{date_taken.day:02d}"

        # Construire le chemin selon le format
        if date_format == "year/month/day":
            path = os.path.join(base_path, year, month, f"{year}_{month}_{day}")
        elif date_format == "year/month":
            path = os.path.join(base_path, year, f"{year}_{month}")
        elif date_format == "year":
            path = os.path.join(base_path, year)
        elif date_format == "year_month_day":
            path = os.path.join(base_path, f"{year}_{month}_{day}")
        elif date_format == "year_month":
            path = os.path.join(base_path, f"{year}_{month}")
        else:
            path = os.path.join(base_path, year, month, f"{year}_{month}_{day}")

        os.makedirs(path, exist_ok=True)
        return path

    def _apply_camera_organization(self, base_path: str, make: str, model: str) -> str:
        """Applique l'organisation par appareil photo."""
        if make == "Unknown" and model == "Unknown":
            camera_name = "Appareil inconnu"
        else:
            camera_name = f"{make} {model}".strip()

        # Nettoyer le nom pour le système de fichiers
        camera_name = self._sanitize_dirname(camera_name)

        path = os.path.join(base_path, camera_name)
        os.makedirs(path, exist_ok=True)
        return path

    def _apply_location_organization(
        self,
        base_path: str,
        gps_coords: Tuple[Optional[float], Optional[float]],
        use_geocoding: bool,
        result: Optional["OrganizationResult"] = None,
    ) -> str:
        """Applique l'organisation par localisation.

        Mode hors-ligne intelligent (Lot E5+ amélioration GPS) : si le
        géocodage est demandé mais échoue (timeout, pas d'internet, API
        indisponible), on retombe automatiquement sur ``Lat_x_Lon_y`` au
        lieu de placer le fichier dans « Sans localisation GPS ».

        ``result`` est optionnel — si fourni, on incrémente les compteurs
        ``files_with_gps`` / ``files_without_gps`` / ``files_geocoded`` /
        ``files_raw_coords`` pour la modale stats.
        """
        lat, lon = gps_coords

        if lat is None or lon is None:
            location_name = "Sans localisation GPS"
            if result is not None:
                result.files_without_gps += 1
        else:
            if result is not None:
                result.files_with_gps += 1
            if use_geocoding:
                # Tentative de géocodage avec fallback automatique sur
                # les coordonnées brutes en cas d'erreur réseau ou API.
                try:
                    location_name = self.gps_processor.get_location_name(lat, lon)
                    # `get_location_name` peut renvoyer None ou une chaîne
                    # vide selon les implementations / pannes silencieuses.
                    if not location_name or location_name.strip() in {
                        "",
                        "Inconnu",
                        "Unknown",
                    }:
                        raise ValueError("nom de lieu vide")
                    if result is not None:
                        result.files_geocoded += 1
                except Exception as exc:
                    logger.debug(f"Geocodage indisponible pour ({lat:.4f}, {lon:.4f}) — fallback Lat_x_Lon_y : {exc}")
                    location_name = f"Lat_{lat:.4f}_Lon_{lon:.4f}"
                    if result is not None:
                        result.files_raw_coords += 1
            else:
                location_name = f"Lat_{lat:.4f}_Lon_{lon:.4f}"
                if result is not None:
                    result.files_raw_coords += 1

        # Nettoyer le nom pour le système de fichiers
        location_name = self._sanitize_dirname(location_name)

        path = os.path.join(base_path, location_name)
        os.makedirs(path, exist_ok=True)
        return path

    def _sanitize_dirname(self, name: str) -> str:
        """Nettoie un nom pour être utilisé comme nom de dossier."""
        # Caractères interdits sous Windows
        forbidden = '<>:"/\\|?*'
        for char in forbidden:
            name = name.replace(char, "_")

        # Limiter la longueur
        if len(name) > 80:
            name = name[:80]

        return name.strip()

    def cancel(self):
        """Demande l'annulation de l'organisation en cours."""
        self._cancel_requested = True

    def rollback(self) -> int:
        """Annule toutes les opérations de la session."""
        return self.file_manager.rollback_all()

    # =================================================================
    # Helpers Lot Q + R
    # =================================================================
    def _passes_filters(
        self,
        file_path: str,
        options: OrganizationOptions,
    ) -> bool:
        """Filtre pré-traitement (R1) : date, taille, rating, mots-clés.

        Renvoie True si le fichier doit être traité, False sinon. Les filtres
        désactivés (None / 0 / [] selon le type) passent toujours.
        """
        # Filtre taille — bon marché, on commence par lui
        if options.size_min_bytes or options.size_max_bytes:
            try:
                size = os.path.getsize(file_path)
            except OSError:
                return False
            if size < options.size_min_bytes:
                return False
            if options.size_max_bytes and size > options.size_max_bytes:
                return False

        # Filtres EXIF : on lit l'EXIF UNE seule fois si nécessaire
        needs_exif = (
            options.date_min is not None
            or options.date_max is not None
            or options.rating_min > 0
            or options.keywords_filter
        )
        if not needs_exif:
            return True

        try:
            exif = get_exif_data(file_path)
        except Exception:
            return True  # en cas d'erreur EXIF, on garde le fichier

        # Filtre date
        if options.date_min is not None or options.date_max is not None:
            try:
                file_date = extract_date(file_path, exif)
            except Exception:
                file_date = None
            if file_date is None:
                # Pas de date EXIF : si l'utilisateur a posé un filtre, on rejette
                return False
            if options.date_min is not None and file_date < options.date_min:
                return False
            if options.date_max is not None and file_date > options.date_max:
                return False

        # Filtre rating (sur 5)
        if options.rating_min > 0:
            rating = self._extract_rating(exif)
            if rating < options.rating_min:
                return False

        # Filtre mots-clés (OR : un seul match suffit)
        if options.keywords_filter:
            keywords_in_file = self._extract_keywords(exif)
            wanted = {kw.strip().lower() for kw in options.keywords_filter if kw.strip()}
            if not (wanted & keywords_in_file):
                return False

        return True

    @staticmethod
    def _extract_rating(exif: Dict[str, Any]) -> int:
        """Lit le rating EXIF/XMP (0..5). Retourne 0 si absent."""
        for key in ("Rating", "XMP:Rating", "EXIF:Rating"):
            v = exif.get(key)
            if v is None:
                continue
            try:
                r = int(float(v))
                return max(0, min(5, r))
            except (TypeError, ValueError):
                continue
        return 0

    @staticmethod
    def _extract_keywords(exif: Dict[str, Any]) -> set:
        """Lit les mots-clés EXIF/XMP/IPTC. Retourne un set en lowercase."""
        candidates: List[str] = []
        for key in ("Keywords", "XMP:Subject", "IPTC:Keywords"):
            v = exif.get(key)
            if not v:
                continue
            if isinstance(v, (list, tuple)):
                candidates.extend(str(x) for x in v)
            else:
                # Souvent une chaine séparée par ;
                candidates.extend(s.strip() for s in str(v).split(";"))
        return {k.lower() for k in candidates if k}

    def _detect_raw_jpeg_pairs(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """Détecte les paires RAW+JPEG (R3) en groupant par stem.

        Retourne ``{stem_lowercase: [paths]}`` uniquement pour les stems
        qui contiennent à la fois un RAW et un JPEG.
        """
        from collections import defaultdict
        from pathlib import Path

        groups: Dict[str, List[str]] = defaultdict(list)
        for fp in file_paths:
            stem = Path(fp).stem.lower()
            groups[stem].append(fp)

        # Ne garder que les groupes qui ont au moins un RAW ET un JPEG
        pairs: Dict[str, List[str]] = {}
        for stem, members in groups.items():
            has_raw = any(Path(m).suffix.lower() in self.RAW_EXTENSIONS for m in members)
            has_jpg = any(Path(m).suffix.lower() in self.JPEG_EXTENSIONS for m in members)
            if has_raw and has_jpg:
                pairs[stem] = members
        if pairs:
            logger.info(f"Detection paires RAW+JPEG: {len(pairs)} groupe(s)")
        return pairs

    @staticmethod
    def _files_are_identical(path_a: str, path_b: str) -> bool:
        """Comparaison rapide deux fichiers via hash partiel.

        Stratégie : on compare d'abord la taille (immédiat), puis un hash
        BLAKE2 sur les 64 premiers Ko + les 64 derniers Ko du fichier. Pour
        les photos, c'est suffisant en pratique pour distinguer deux
        contenus différents.
        """
        try:
            sa = os.path.getsize(path_a)
            sb = os.path.getsize(path_b)
        except OSError:
            return False
        if sa != sb:
            return False
        if sa == 0:
            return True
        return _quick_hash(path_a) == _quick_hash(path_b)

    @staticmethod
    def _apply_rename_template(
        original_name: str,
        template: str,
        date_taken: Optional[datetime],
        make: str,
        model: str,
        counter: int,
    ) -> str:
        """Applique un template Q4 sur le nom de fichier.

        Tokens supportés (str.format) :
          {original}     - nom sans extension (ex: 'IMG_0001')
          {ext}          - extension (avec point, ex: '.jpg')
          {date:fmt}     - date EXIF formatée (str.format date)
          {camera}       - 'make model' nettoyé
          {counter[:fmt]}- compteur (ex: {counter:03d} → '042')

        Si une clé est manquante (ex: pas de date EXIF), elle est remplacée
        par 'unknown'.
        """
        from pathlib import Path

        p = Path(original_name)
        stem = p.stem
        ext = p.suffix
        camera = " ".join(filter(None, [make, model])).strip() or "unknown"

        # Petite classe wrapper pour gérer date None gracieusement
        class _SafeDate:
            def __init__(self, d):
                self._d = d

            def __format__(self, fmt):
                if self._d is None:
                    return "unknown"
                if not fmt:
                    return self._d.isoformat()
                return self._d.strftime(fmt)

        rendered = template.format(
            original=stem,
            ext=ext,
            date=_SafeDate(date_taken),
            camera=camera,
            counter=counter,
        )
        # Si le template ne contient pas {ext}, on l'ajoute pour éviter
        # de produire un fichier sans extension.
        if not rendered.endswith(ext) and "." not in os.path.basename(rendered):
            rendered = f"{rendered}{ext}"
        # Sanitization basique des caractères interdits Windows
        for ch in '<>:"/\\|?*':
            rendered = rendered.replace(ch, "_")
        return rendered

    def _validate_disk_space(
        self,
        file_paths: List[str],
        target_dir: str,
    ) -> Tuple[bool, str]:
        """Vérifie qu'il y a assez d'espace libre sur le disque cible (R6)."""
        import shutil

        try:
            total_required = sum(os.path.getsize(fp) for fp in file_paths if os.path.exists(fp))
            os.makedirs(target_dir, exist_ok=True)
            free = shutil.disk_usage(target_dir).free
            if total_required > free:
                msg = (
                    f"Espace disque insuffisant : {total_required / 1e9:.2f} Go requis, {free / 1e9:.2f} Go disponibles"
                )
                return False, msg
            return True, ""
        except OSError as exc:
            return False, f"Validation espace disque echouee : {exc}"

    def _cleanup_source_dirs(self, file_paths: List[str]):
        """Supprime les dossiers source devenus vides après MOVE (R5)."""
        cleaned = 0
        # On itère depuis les chemins les plus profonds (ordre inverse) pour
        # que les parents soient nettoyés une fois leurs enfants vidés.
        seen_dirs = set()
        for fp in file_paths:
            d = os.path.dirname(fp)
            if d:
                seen_dirs.add(d)
        # Tri par profondeur décroissante
        for d in sorted(seen_dirs, key=lambda p: p.count(os.sep), reverse=True):
            try:
                if os.path.isdir(d) and not os.listdir(d):
                    os.rmdir(d)
                    cleaned += 1
            except OSError as exc:
                logger.debug(f"cleanup ignore : {exc}")
        if cleaned:
            logger.info(f"Cleanup : {cleaned} dossier(s) source vides supprime(s)")

    def _detect_bursts(
        self,
        file_paths: List[str],
        threshold_seconds: int = 3,
        min_count: int = 3,
        mode: str = "manual",
    ) -> Dict[str, Optional[str]]:
        """Détecte les rafales (Lot S1) en groupant par DateTimeOriginal.

        Algorithme : on extrait la date de prise de vue de chaque fichier,
        on trie chronologiquement, puis on glisse une fenêtre. Quand l'écart
        avec la photo précédente dépasse `threshold_seconds`, on clôt le
        groupe courant. Les groupes de moins de `min_count` photos sont
        considérés comme des prises uniques (membership = None).

        Mode (audit 2026-05-15) :
            - ``manual`` (défaut) : seuil = ``threshold_seconds`` (fixe)
            - ``auto``            : seuil = max(1, mean(Δ) − stddev(Δ))
              calculé sur les écarts entre photos consécutives du dossier.
              Heuristique : les Δ « courts » (en dessous de la moyenne)
              sont caractéristiques d'une rafale, alors que les Δ
              « longs » correspondent aux pauses entre prises de vue
              distinctes. Soustraire l'écart-type rend le seuil plus
              strict (ne capture que les Δ vraiment courts).

        Retourne : ``{file_path: burst_id_or_None}``. Les burst_id ont la
        forme ``Burst_01``, ``Burst_02``, … (numérotation chronologique).
        """
        # Récupérer (path, date) pour chaque fichier
        dated: List[Tuple[str, datetime]] = []
        for fp in file_paths:
            try:
                exif = get_exif_data(fp)
                d = extract_date(fp, exif)
            except Exception:
                d = None
            if d is not None:
                dated.append((fp, d))

        if not dated:
            return {}

        # Trier chronologiquement
        dated.sort(key=lambda t: t[1])

        # Mode auto : recalculer threshold à partir des deltas réels.
        # Si moins de 3 photos datées, on retombe sur le manuel.
        effective_threshold = threshold_seconds
        if mode == "auto" and len(dated) >= 3:
            deltas = []
            for i in range(1, len(dated)):
                delta = (dated[i][1] - dated[i - 1][1]).total_seconds()
                if delta >= 0:
                    deltas.append(delta)
            if deltas:
                import statistics

                mean = statistics.mean(deltas)
                stddev = statistics.pstdev(deltas) if len(deltas) > 1 else 0.0
                # Seuil = mean - stddev, clampé à [1 s ; 600 s]
                auto_thr = max(1.0, min(mean - stddev, 600.0))
                effective_threshold = int(round(auto_thr))
                logger.info(f"Bursts mode auto : mean={mean:.1f}s, stddev={stddev:.1f}s → seuil={effective_threshold}s")

        membership: Dict[str, Optional[str]] = {fp: None for fp in file_paths}
        groups: List[List[str]] = []
        current: List[str] = [dated[0][0]]
        prev_date = dated[0][1]
        for fp, d in dated[1:]:
            delta = (d - prev_date).total_seconds()
            if delta <= effective_threshold:
                current.append(fp)
            else:
                groups.append(current)
                current = [fp]
            prev_date = d
        groups.append(current)

        # Numéroter uniquement les groupes >= min_count
        burst_index = 0
        for grp in groups:
            if len(grp) >= min_count:
                burst_index += 1
                burst_id = f"Burst_{burst_index:02d}"
                for fp in grp:
                    membership[fp] = burst_id

        if burst_index:
            logger.info(
                f"Detection bursts : {burst_index} rafale(s) detectee(s) "
                f"(mode={mode}, seuil {effective_threshold}s, min {min_count} photos)"
            )
        return membership

    @staticmethod
    def _incremental_index_path(target_dir: str) -> str:
        """Emplacement canonique du cache incrémental (Lot S5)."""
        return os.path.join(target_dir, ".photoorganizer_index.json")

    def _load_incremental_index(self, target_dir: str) -> set:
        """Charge l'index incrémental précédent et retourne le set des hash."""
        path = self._incremental_index_path(target_dir)
        if not os.path.exists(path):
            return set()
        try:
            import json

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            hashes = {rec.get("hash") for rec in data if rec.get("hash")}
            logger.info(f"Index incremental charge : {len(hashes)} entree(s) connue(s)")
            return hashes
        except (OSError, ValueError) as exc:
            logger.warning(f"Index incremental illisible ({exc}) — ignore")
            return set()

    def _save_incremental_index(self, target_dir: str):
        """Persiste / met à jour l'index incrémental.

        Fusionne avec l'index existant (les anciennes entrées sont conservées)
        et déduplique sur le couple (hash, destination).
        """
        path = self._incremental_index_path(target_dir)
        try:
            import json

            existing: List[Dict[str, Any]] = []
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except (OSError, ValueError):
                    existing = []
            seen = {(rec.get("hash"), rec.get("destination")) for rec in existing}
            for rec in self._index_records:
                key = (rec.get("hash"), rec.get("destination"))
                if rec.get("hash") and key not in seen:
                    existing.append(rec)
                    seen.add(key)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            logger.info(f"Index incremental sauvegarde : {len(existing)} entree(s) au total")
        except OSError as exc:
            logger.warning(f"Echec sauvegarde index incremental : {exc}")

    def _is_already_indexed(self, file_path: str) -> bool:
        """Vrai si le hash partiel du fichier est déjà connu (S5)."""
        if not self._known_hashes:
            return False
        try:
            return _quick_hash(file_path) in self._known_hashes
        except OSError:
            return False

    def _export_index(self, target_dir: str, options: OrganizationOptions):
        """Écrit un fichier d'index CSV et/ou JSON dans target_dir (R7)."""
        if not self._index_records:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if options.export_index_csv:
            import csv

            csv_path = os.path.join(target_dir, f"_photoorganizer_index_{timestamp}.csv")
            try:
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=list(self._index_records[0].keys()))
                    writer.writeheader()
                    writer.writerows(self._index_records)
                logger.info(f"Index CSV ecrit : {csv_path}")
            except OSError as exc:
                logger.warning(f"Echec ecriture index CSV : {exc}")

        if options.export_index_json:
            import json

            json_path = os.path.join(target_dir, f"_photoorganizer_index_{timestamp}.json")
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(self._index_records, f, indent=2, ensure_ascii=False)
                logger.info(f"Index JSON ecrit : {json_path}")
            except OSError as exc:
                logger.warning(f"Echec ecriture index JSON : {exc}")


def _quick_hash(path: str, head_bytes: int = 64 * 1024) -> str:
    """Hash partiel (head + tail) d'un fichier pour comparaison rapide."""
    import hashlib

    h = hashlib.blake2b(digest_size=16)
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        h.update(f.read(head_bytes))
        if size > head_bytes * 2:
            f.seek(-head_bytes, os.SEEK_END)
            h.update(f.read(head_bytes))
    h.update(str(size).encode())
    return h.hexdigest()


# Instance globale
_organizer: Optional[SmartOrganizer] = None


def get_organizer() -> SmartOrganizer:
    """Retourne l'instance globale de l'organiseur."""
    global _organizer
    if _organizer is None:
        _organizer = SmartOrganizer()
    return _organizer


def organize_files(
    file_paths: List[str], target_dir: str, options: Dict[str, Any], progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour organiser des fichiers.

    Args:
        file_paths: Liste des fichiers
        target_dir: Répertoire de destination
        options: Options d'organisation (dictionnaire)
        progress_callback: Callback de progression

    Returns:
        Dictionnaire des résultats
    """
    organizer = get_organizer()
    opts = OrganizationOptions.from_dict(options)
    result = organizer.organize(file_paths, target_dir, opts, progress_callback)

    return {
        "total": result.total,
        "processed": result.processed,
        "skipped": result.skipped,
        "errors": result.errors,
        "error_messages": result.error_messages,
    }
