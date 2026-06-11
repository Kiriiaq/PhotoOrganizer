# -*- coding: utf-8 -*-
"""
Advanced duplicate management system.

This module provides a complete system for detecting, analyzing, and managing
duplicate files with configurable conservation rules and execution modes.
"""

import fnmatch
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from src.config.duplicate_config import (
    ConservationCriterion,
    DuplicateGroupDecision,
    DuplicateManagerConfig,
    ExecutionMode,
    ExecutionResult,
    FileAction,
    FileDecision,
)
from src.core.operations.duplicate_finder import (
    DuplicateFinder,
    DuplicateGroup,
    DuplicateResult,
)
from src.core.operations.file_manager import FileManager
from src.core.operations.quarantine import QuarantineManager

# Try to import send2trash for trash support
try:
    from send2trash import send2trash  # noqa: F401  (availability sentinel)
    TRASH_AVAILABLE = True
except ImportError:
    TRASH_AVAILABLE = False

logger = logging.getLogger(__name__)


class DuplicateManager:
    """
    Advanced duplicate management system.

    Features:
    - Configurable conservation rules (priority folders, extensions, dates, paths)
    - Multiple execution modes (dry-run, delete, move, trash, interactive)
    - Verification before deletion
    - Progress callbacks and cancellation support
    - Detailed result reporting
    """

    def __init__(self, config: DuplicateManagerConfig, file_manager: Optional[FileManager] = None):
        """
        Initialize the duplicate manager.

        Args:
            config: Configuration for the manager
            file_manager: FileManager partagé pour historiser les opérations
                (trash/move/delete) dans l'onglet Historique. Lot D (audit
                2026-06-11) : avant, les opérations étaient enregistrées dans
                un singleton module-level jamais affiché par l'UI — le
                « FileManager partagé » documenté ne l'était pas réellement.
                Si None (CLI, tests), une instance privée est créée.
        """
        self.config = config
        self.file_manager = file_manager or FileManager()
        self._cancel_requested = False
        self._finder = None
        # Quarantaine interne pour le mode TRASH — assure la réversibilité
        # via le panneau Historique. Une instance par DuplicateManager =
        # une session unique horodatée. L'utilisateur peut ensuite vider
        # définitivement via la méthode ``empty_quarantine`` (qui appelle
        # send2trash). Voir src/core/operations/quarantine.py.
        self.quarantine: QuarantineManager = QuarantineManager()

    def _get_finder(self) -> DuplicateFinder:
        """Get or create the duplicate finder instance."""
        if self._finder is None:
            self._finder = DuplicateFinder(
                algorithm=self.config.hashing.algorithm.value,
                quick_mode=self.config.hashing.use_quick_mode,
                min_size=self.config.min_file_size,
                chunk_size=self.config.hashing.chunk_size_bytes,
                quick_chunk_size=self.config.hashing.quick_chunk_size,
                use_cache=self.config.hashing.use_cache,
                max_workers=self.config.performance.max_workers
            )
        return self._finder

    def scan(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[List[str], DuplicateResult]:
        """
        Phase 1: Scan directories and find duplicates.

        Args:
            progress_callback: Progress callback (current, total, message)

        Returns:
            Tuple of (file_paths, DuplicateResult)
        """
        self._cancel_requested = False

        # Collect all files
        all_files = self._collect_files(progress_callback)

        if self._cancel_requested:
            return [], DuplicateResult()

        # Find duplicates
        finder = self._get_finder()
        result = finder.find_duplicates(all_files, progress_callback)

        return all_files, result

    def analyze(
        self,
        duplicate_result: DuplicateResult,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ExecutionResult:
        """
        Phase 2: Analyze duplicates and determine actions.

        Applies conservation rules to decide which files to keep and remove.

        Args:
            duplicate_result: Result from scan phase
            progress_callback: Progress callback

        Returns:
            ExecutionResult with decisions for each group
        """
        self._cancel_requested = False

        result = ExecutionResult(
            total_files_scanned=duplicate_result.total_files,
            duplicate_groups=len(duplicate_result.duplicate_groups),
            execution_mode=self.config.execution_mode,
            start_time=datetime.now()
        )

        total_groups = len(duplicate_result.duplicate_groups)

        for i, group in enumerate(duplicate_result.duplicate_groups):
            if self._cancel_requested:
                break

            if progress_callback:
                progress_callback(i + 1, total_groups, "Analyse des groupes...")

            # Analyze group and determine decisions
            group_decision = self._analyze_group(group, i + 1)
            result.group_decisions.append(group_decision)

            # Update counters
            for decision in group_decision.decisions:
                if decision.action == FileAction.KEEP:
                    result.files_kept += 1
                elif decision.action in (FileAction.DELETE, FileAction.MOVE, FileAction.TRASH):
                    result.total_duplicates += 1
                    result.space_duplicates += decision.file_size

        result.space_recovered = result.space_duplicates
        result.end_time = datetime.now()

        return result

    def execute(
        self,
        analysis_result: ExecutionResult,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        interactive_callback: Optional[Callable[[DuplicateGroupDecision], bool]] = None
    ) -> ExecutionResult:
        """
        Phase 3: Execute the planned actions.

        Args:
            analysis_result: Result from analyze phase
            progress_callback: Progress callback
            interactive_callback: Callback for interactive mode (returns True to proceed)

        Returns:
            Updated ExecutionResult with actual execution results
        """
        self._cancel_requested = False

        if self.config.execution_mode == ExecutionMode.DRY_RUN:
            logger.info("Dry-run mode: no changes will be made")
            return analysis_result

        # Reset execution counters
        analysis_result.files_deleted = 0
        analysis_result.files_moved = 0
        analysis_result.files_trashed = 0
        analysis_result.files_errored = 0
        analysis_result.space_recovered = 0
        analysis_result.errors = []
        analysis_result.start_time = datetime.now()

        total_actions = sum(
            len([d for d in g.decisions if d.action != FileAction.KEEP])
            for g in analysis_result.group_decisions
        )
        processed = 0

        for group_decision in analysis_result.group_decisions:
            if self._cancel_requested:
                break

            # Interactive mode: ask user for each group
            if self.config.execution_mode == ExecutionMode.INTERACTIVE:
                if interactive_callback and not interactive_callback(group_decision):
                    # User skipped this group
                    for decision in group_decision.decisions:
                        if decision.action != FileAction.KEEP:
                            decision.action = FileAction.IGNORE
                            decision.reason = "Skipped by user"
                    continue

            # Execute actions for this group
            for decision in group_decision.decisions:
                if self._cancel_requested:
                    break

                if decision.action == FileAction.KEEP:
                    continue

                if progress_callback:
                    processed += 1
                    progress_callback(processed, total_actions, "Traitement des fichiers...")

                # Verify hash before action if configured
                if self.config.verify_before_delete and decision.action in (FileAction.DELETE, FileAction.TRASH):
                    finder = self._get_finder()
                    if not finder.verify_hash(decision.file_path, group_decision.hash_value):
                        decision.action = FileAction.ERROR
                        decision.reason = "Hash verification failed"
                        analysis_result.files_errored += 1
                        analysis_result.errors.append(
                            f"Hash mismatch for {decision.file_path}"
                        )
                        continue

                # Execute the action
                success, error = self._execute_action(decision)

                if success:
                    if decision.action == FileAction.DELETE:
                        analysis_result.files_deleted += 1
                        analysis_result.space_recovered += decision.file_size
                    elif decision.action == FileAction.MOVE:
                        analysis_result.files_moved += 1
                        analysis_result.space_recovered += decision.file_size
                    elif decision.action == FileAction.TRASH:
                        analysis_result.files_trashed += 1
                        analysis_result.space_recovered += decision.file_size
                else:
                    decision.action = FileAction.ERROR
                    decision.reason = error
                    analysis_result.files_errored += 1
                    analysis_result.errors.append(f"{decision.file_path}: {error}")

        analysis_result.end_time = datetime.now()
        return analysis_result

    def run(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        interactive_callback: Optional[Callable[[DuplicateGroupDecision], bool]] = None
    ) -> ExecutionResult:
        """
        Run the complete pipeline: scan -> analyze -> execute.

        Args:
            progress_callback: Progress callback
            interactive_callback: Callback for interactive mode

        Returns:
            ExecutionResult with complete results
        """
        self._cancel_requested = False

        # Validate configuration
        errors = self.config.validate()
        if errors:
            result = ExecutionResult(execution_mode=self.config.execution_mode)
            result.errors = errors
            return result

        # Phase 1: Scan
        all_files, duplicate_result = self.scan(progress_callback)

        if self._cancel_requested:
            return ExecutionResult(execution_mode=self.config.execution_mode)

        # Phase 2: Analyze
        analysis_result = self.analyze(duplicate_result, progress_callback)

        if self._cancel_requested:
            return analysis_result

        # Phase 3: Execute
        final_result = self.execute(analysis_result, progress_callback, interactive_callback)

        return final_result

    def cancel(self):
        """Cancel the current operation."""
        self._cancel_requested = True
        if self._finder:
            self._finder.cancel()

    def _collect_files(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[str]:
        """Collect all files from source directories."""
        all_files = []
        dirs_to_scan = list(self.config.source_directories)
        scanned_count = 0

        while dirs_to_scan:
            if self._cancel_requested:
                break

            current_dir = dirs_to_scan.pop(0)

            if progress_callback:
                scanned_count += 1
                progress_callback(scanned_count, scanned_count + len(dirs_to_scan),
                                  f"Scan: {Path(current_dir).name}")

            try:
                for entry in os.scandir(current_dir):
                    if self._cancel_requested:
                        break

                    full_path = entry.path

                    if entry.is_dir(follow_symlinks=False):
                        # Check if directory should be scanned
                        if self.config.recursive and self._should_include_folder(full_path):
                            dirs_to_scan.append(full_path)

                    elif entry.is_file(follow_symlinks=False):
                        # Check if file should be included
                        if self._should_include_file(full_path):
                            all_files.append(full_path)

            except PermissionError:
                logger.debug(f"Permission denied: {current_dir}")
            except OSError as e:
                logger.debug(f"Error scanning {current_dir}: {e}")

        return all_files

    # Dossiers système à exclure du scan : corbeilles Windows / Linux / macOS
    # et marqueurs de système de fichiers internes. La comparaison est
    # case-insensitive et s'effectue sur le composant final ET sur l'ensemble
    # des composants du chemin pour bloquer aussi `C:\$Recycle.Bin\S-1-...`.
    _SYSTEM_EXCLUDED_FOLDER_NAMES = frozenset([
        "$recycle.bin",                # Windows (NTFS, par utilisateur)
        "recycler",                    # Windows (FAT/anciennes)
        "system volume information",   # Windows volume metadata
        ".trash", ".trashes",          # macOS / Linux
        "$trash",                      # variante observée
        ".spotlight-v100", ".fseventsd", ".tempitems",  # macOS
    ])

    def _is_system_folder(self, folder_path: str) -> bool:
        """Retourne True si un quelconque composant du chemin est un dossier
        système (corbeille, métadonnées de volume…) ou suit le pattern
        ``.Trash-<uid>`` (XDG)."""
        parts_lower = {p.lower() for p in Path(folder_path).parts}
        if parts_lower & self._SYSTEM_EXCLUDED_FOLDER_NAMES:
            return True
        if any(p.startswith(".trash-") for p in parts_lower):
            return True
        return False

    def _should_include_folder(self, folder_path: str) -> bool:
        """Check if a folder should be included in scan."""
        # 1) Exclusion automatique des dossiers système (corbeilles…)
        if self._is_system_folder(folder_path):
            logger.debug(f"Dossier systeme ignore: {folder_path}")
            return False

        folder_path_normalized = folder_path.replace('\\', '/')

        # 2) Patterns exclude utilisateur
        for pattern in self.config.folders.exclude:
            if fnmatch.fnmatch(folder_path_normalized, pattern):
                return False
            if fnmatch.fnmatch(Path(folder_path).name, pattern.split('/')[-1]):
                return False

        # 3) Patterns include (si renseignés)
        if self.config.folders.include:
            for pattern in self.config.folders.include:
                if fnmatch.fnmatch(folder_path_normalized, pattern):
                    return True
            return False

        return True

    def _should_include_file(self, file_path: str) -> bool:
        """Check if a file should be included in scan."""
        # Garde-fou : un fichier dans un dossier système ne doit jamais
        # être inclus, même si la traversée a contourné le filtre dossier.
        if self._is_system_folder(file_path):
            return False

        ext = Path(file_path).suffix.lower()

        if self.config.extensions.exclude and ext in self.config.extensions.exclude:
            return False

        if self.config.extensions.include and ext not in self.config.extensions.include:
            return False

        try:
            size = os.path.getsize(file_path)
            if size < self.config.min_file_size:
                return False
            if self.config.max_file_size and size > self.config.max_file_size:
                return False
        except OSError:
            return False

        return True

    def _analyze_group(self, group: DuplicateGroup, group_id: int) -> DuplicateGroupDecision:
        """
        Analyze a duplicate group and determine which file to keep.

        Applies conservation criteria in order until one produces a clear winner.
        """
        group_decision = DuplicateGroupDecision(
            group_id=group_id,
            hash_value=group.hash_value,
            file_size=group.file_size
        )

        # Get file metadata for decision making
        file_infos = []
        for file_path in group.files:
            info = self._get_file_info(file_path, group.file_size)
            file_infos.append(info)

        # Determine the file to keep based on conservation criteria
        keeper_index = self._select_keeper(file_infos)

        # Create decisions for all files
        for i, info in enumerate(file_infos):
            if i == keeper_index:
                decision = FileDecision(
                    file_path=info['path'],
                    action=FileAction.KEEP,
                    reason=info.get('keep_reason', 'Selected by conservation rules'),
                    file_size=info['size'],
                    creation_time=info.get('creation_time'),
                    modification_time=info.get('modification_time')
                )
            else:
                # Determine action based on execution mode
                action = self._get_action_for_mode()
                target_path = None

                if action == FileAction.MOVE:
                    target_path = self._get_move_target(info['path'])

                decision = FileDecision(
                    file_path=info['path'],
                    action=action,
                    reason="Duplicate",
                    target_path=target_path,
                    file_size=info['size'],
                    creation_time=info.get('creation_time'),
                    modification_time=info.get('modification_time')
                )

            group_decision.decisions.append(decision)

        return group_decision

    def _get_file_info(self, file_path: str, file_size: int) -> Dict:
        """Get file metadata for conservation decision making."""
        info = {
            'path': file_path,
            'size': file_size,
            'extension': Path(file_path).suffix.lower(),
            'path_length': len(file_path),
            'folder': str(Path(file_path).parent),
        }

        try:
            stat = os.stat(file_path)
            info['modification_time'] = datetime.fromtimestamp(stat.st_mtime)

            # Try to get creation time (Windows) or use mtime as fallback
            if hasattr(stat, 'st_birthtime'):
                info['creation_time'] = datetime.fromtimestamp(stat.st_birthtime)
            elif hasattr(stat, 'st_ctime'):
                # On Windows, st_ctime is creation time; on Unix, it's metadata change time
                if os.name == 'nt':
                    info['creation_time'] = datetime.fromtimestamp(stat.st_ctime)
                else:
                    info['creation_time'] = info['modification_time']
            else:
                info['creation_time'] = info['modification_time']

        except OSError:
            info['creation_time'] = None
            info['modification_time'] = None

        return info

    def _select_keeper(self, file_infos: List[Dict]) -> int:
        """
        Select which file to keep based on conservation criteria.

        Returns the index of the file to keep.
        """
        candidates = list(range(len(file_infos)))

        for criterion in self.config.conservation.criteria_order:
            if len(candidates) == 1:
                break

            new_candidates = self._apply_criterion(criterion, file_infos, candidates)

            if new_candidates:
                candidates = new_candidates

        # Update keep_reason for the winner
        keeper_idx = candidates[0]
        file_infos[keeper_idx]['keep_reason'] = self._get_keep_reason(
            self.config.conservation.criteria_order[0] if self.config.conservation.criteria_order
            else ConservationCriterion.SHORTEST_PATH
        )

        return keeper_idx

    def _apply_criterion(
        self,
        criterion: ConservationCriterion,
        file_infos: List[Dict],
        candidates: List[int]
    ) -> List[int]:
        """Apply a single conservation criterion to filter candidates."""

        if criterion == ConservationCriterion.PRIORITY_FOLDER:
            # Check if any file is in a priority folder
            for priority_folder in self.config.folders.priority:
                priority_path = Path(priority_folder).resolve()
                matching = []
                for idx in candidates:
                    file_folder = Path(file_infos[idx]['folder']).resolve()
                    try:
                        file_folder.relative_to(priority_path)
                        matching.append(idx)
                        file_infos[idx]['keep_reason'] = f"Priority folder: {priority_folder}"
                    except ValueError:
                        pass
                if matching:
                    return matching

        elif criterion == ConservationCriterion.PREFERRED_EXTENSION:
            # Prefer files with earlier extensions in the preference list
            for ext in self.config.extensions.preferred_order:
                matching = [
                    idx for idx in candidates
                    if file_infos[idx]['extension'] == ext.lower()
                ]
                if matching:
                    for idx in matching:
                        file_infos[idx]['keep_reason'] = f"Preferred extension: {ext}"
                    return matching

        elif criterion == ConservationCriterion.OLDEST_DATE:
            # Keep the oldest file
            dated_candidates = [
                (idx, file_infos[idx].get('creation_time') or file_infos[idx].get('modification_time'))
                for idx in candidates
                if file_infos[idx].get('creation_time') or file_infos[idx].get('modification_time')
            ]
            if dated_candidates:
                dated_candidates.sort(key=lambda x: x[1])
                oldest_idx = dated_candidates[0][0]
                file_infos[oldest_idx]['keep_reason'] = "Oldest file"
                return [oldest_idx]

        elif criterion == ConservationCriterion.NEWEST_DATE:
            # Keep the newest file
            dated_candidates = [
                (idx, file_infos[idx].get('modification_time') or file_infos[idx].get('creation_time'))
                for idx in candidates
                if file_infos[idx].get('modification_time') or file_infos[idx].get('creation_time')
            ]
            if dated_candidates:
                dated_candidates.sort(key=lambda x: x[1], reverse=True)
                newest_idx = dated_candidates[0][0]
                file_infos[newest_idx]['keep_reason'] = "Newest file"
                return [newest_idx]

        elif criterion == ConservationCriterion.SHORTEST_PATH:
            # Keep the file with the shortest path
            min_length = min(file_infos[idx]['path_length'] for idx in candidates)
            matching = [idx for idx in candidates if file_infos[idx]['path_length'] == min_length]
            if matching:
                file_infos[matching[0]]['keep_reason'] = "Shortest path"
            return matching

        elif criterion == ConservationCriterion.LONGEST_PATH:
            # Keep the file with the longest path
            max_length = max(file_infos[idx]['path_length'] for idx in candidates)
            matching = [idx for idx in candidates if file_infos[idx]['path_length'] == max_length]
            if matching:
                file_infos[matching[0]]['keep_reason'] = "Longest path"
            return matching

        return candidates

    def _get_keep_reason(self, criterion: ConservationCriterion) -> str:
        """Get a human-readable reason for keeping a file."""
        reasons = {
            ConservationCriterion.PRIORITY_FOLDER: "Priority folder",
            ConservationCriterion.PREFERRED_EXTENSION: "Preferred extension",
            ConservationCriterion.OLDEST_DATE: "Oldest file",
            ConservationCriterion.NEWEST_DATE: "Newest file",
            ConservationCriterion.SHORTEST_PATH: "Shortest path",
            ConservationCriterion.LONGEST_PATH: "Longest path",
            ConservationCriterion.LARGEST_FILE: "Largest file",
            ConservationCriterion.SMALLEST_FILE: "Smallest file",
        }
        return reasons.get(criterion, "Conservation rules")

    def _get_action_for_mode(self) -> FileAction:
        """Get the file action based on execution mode."""
        mode_actions = {
            ExecutionMode.DRY_RUN: FileAction.DELETE,  # Will be simulated
            ExecutionMode.DELETE: FileAction.DELETE,
            ExecutionMode.MOVE: FileAction.MOVE,
            ExecutionMode.TRASH: FileAction.TRASH,
            ExecutionMode.INTERACTIVE: FileAction.DELETE,  # Default for interactive
        }
        return mode_actions.get(self.config.execution_mode, FileAction.DELETE)

    def _get_move_target(self, source_path: str) -> str:
        """Generate the target path for moving a file."""
        if not self.config.move_destination:
            return source_path

        source = Path(source_path)
        dest_base = Path(self.config.move_destination)

        # Preserve relative structure from source directories
        for src_dir in self.config.source_directories:
            src_path = Path(src_dir)
            try:
                relative = source.relative_to(src_path)
                target = dest_base / relative
                return str(target)
            except ValueError:
                continue

        # Fallback: just use the filename
        return str(dest_base / source.name)

    def _execute_action(self, decision: FileDecision) -> Tuple[bool, Optional[str]]:
        """
        Execute a file action.

        Returns:
            Tuple of (success, error_message)
        """
        file_path = decision.file_path

        # Check file exists and is accessible
        if not os.path.exists(file_path):
            return False, "File not found"

        if not os.access(file_path, os.W_OK):
            return False, "Permission denied"

        # FileManager (injecté par l'UI, partagé entre onglets) pour
        # enregistrer chaque opération dans l'historique unifié (visible
        # dans le panneau Historique + « Annuler dernière / tout »).
        # Lot D (audit 2026-06-11) : remplace le singleton module-level
        # _get_file_manager() qui n'était jamais celui affiché par l'UI.
        fm = self.file_manager

        try:
            if decision.action == FileAction.DELETE:
                # Suppression DEFINITIVE — on enregistre quand même pour
                # traçabilité, mais le rollback de file_manager renvoie
                # explicitement False sur ce type d'opération.
                os.remove(file_path)
                fm.record_operation(
                    operation_type="delete",
                    source=file_path,
                    destination="",
                    success=True,
                )
                logger.info(f"Deleted (definitive): {file_path}")
                return True, None

            elif decision.action == FileAction.MOVE:
                if not decision.target_path:
                    return False, "No target path specified"

                # Create target directory if needed
                target_dir = Path(decision.target_path).parent
                target_dir.mkdir(parents=True, exist_ok=True)

                # Handle name conflicts
                target = Path(decision.target_path)
                if target.exists():
                    target = self._get_unique_path(target)

                shutil.move(file_path, str(target))
                decision.target_path = str(target)
                fm.record_operation(
                    operation_type="move",
                    source=file_path,
                    destination=str(target),
                    success=True,
                )
                logger.info(f"Moved: {file_path} -> {target}")
                return True, None

            elif decision.action == FileAction.TRASH:
                # Refonte 2026-05-19 : remplacer l'envoi direct en corbeille
                # système (irréversible côté Python) par un déplacement vers
                # la quarantaine interne (récupérable via « Annuler »).
                # L'utilisateur vide définitivement plus tard via le bouton
                # « 🗑 Vider quarantaine ».
                entry = self.quarantine.quarantine_file(
                    file_path, reason="duplicate"
                )
                fm.record_operation(
                    operation_type="trash",
                    source=entry.source,
                    destination=entry.destination,
                    success=True,
                )
                logger.info(
                    f"Trashed (quarantine): {file_path} -> {entry.destination}"
                )
                return True, None

            else:
                return False, f"Unknown action: {decision.action}"

        except PermissionError:
            return False, "Permission denied"
        except OSError as e:
            return False, str(e)

    # ------------------------------------------------------------------
    # Gestion de la quarantaine (refonte 2026-05-19)
    # ------------------------------------------------------------------
    def empty_quarantine(self) -> Dict[str, int]:
        """Vide la quarantaine interne en envoyant tout en corbeille système.

        L'utilisateur appelle cette méthode via le bouton « 🗑 Vider
        quarantaine » de l'IHM quand il est sûr de ne plus vouloir
        restaurer les doublons. Une fois cette action exécutée, les
        fichiers passent de la quarantaine interne (récupérable depuis
        l'app) à la corbeille système (récupérable depuis l'Explorateur
        Windows uniquement, jusqu'au vidage manuel).

        Returns:
            dict détaillé : voir ``QuarantineManager.empty_to_system_trash``.
        """
        return self.quarantine.empty_to_system_trash()

    def quarantine_size_bytes(self) -> int:
        """Taille totale occupée par la quarantaine de cette session."""
        return self.quarantine.total_size_bytes()

    def quarantine_count(self) -> int:
        """Nombre de fichiers actuellement en quarantaine."""
        return len(self.quarantine.list_entries())

    def _get_unique_path(self, path: Path) -> Path:
        """Generate a unique path if target already exists."""
        if not path.exists():
            return path

        counter = 1
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1


# Global instance
_manager: Optional[DuplicateManager] = None


def get_manager(config: Optional[DuplicateManagerConfig] = None) -> DuplicateManager:
    """
    Get the global duplicate manager instance.

    Args:
        config: Configuration (required on first call)

    Returns:
        DuplicateManager instance
    """
    global _manager
    if _manager is None:
        if config is None:
            config = DuplicateManagerConfig()
        _manager = DuplicateManager(config)
    return _manager


def reset_manager():
    """Reset the global manager instance."""
    global _manager
    _manager = None
