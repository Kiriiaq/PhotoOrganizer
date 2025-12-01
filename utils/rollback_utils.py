"""
Rollback and undo functionality for file operations
Allows reversing file organization operations
"""

import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages rollback operations for file movements"""

    def __init__(self, history_dir: Optional[str] = None):
        """
        Initialize rollback manager

        Args:
            history_dir: Directory to store rollback history (default: user data dir)
        """
        if history_dir is None:
            # Use standard data directory
            if os.name == 'nt':
                base = Path(os.environ.get('APPDATA', ''))
            else:
                base = Path.home() / '.local' / 'share'

            self.history_dir = base / 'PhotoOrganizer' / 'rollback_history'
        else:
            self.history_dir = Path(history_dir)

        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_file = None
        self.current_session_operations = []

        logger.info(f"Rollback manager initialized at {self.history_dir}")

    def start_session(self, session_name: Optional[str] = None) -> str:
        """
        Start a new rollback session

        Args:
            session_name: Optional name for the session

        Returns:
            Session ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"{timestamp}_{session_name}" if session_name else timestamp

        self.current_session_file = self.history_dir / f"session_{session_id}.json"
        self.current_session_operations = []

        session_data = {
            'session_id': session_id,
            'session_name': session_name,
            'started_at': datetime.now().isoformat(),
            'operations': []
        }

        self._save_session(session_data)
        logger.info(f"Started rollback session: {session_id}")

        return session_id

    def record_operation(self, operation_type: str, source: str, destination: str,
                        metadata: Optional[Dict] = None) -> None:
        """
        Record a file operation for potential rollback

        Args:
            operation_type: Type of operation ('copy', 'move', 'rename')
            source: Original file path
            destination: New file path
            metadata: Optional metadata about the operation
        """
        if self.current_session_file is None:
            logger.warning("No active session. Starting new session.")
            self.start_session()

        operation = {
            'type': operation_type,
            'source': source,
            'destination': destination,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {},
            'rolled_back': False
        }

        # For move operations, store file backup info
        if operation_type == 'move' and os.path.exists(destination):
            operation['file_size'] = os.path.getsize(destination)
            operation['file_mtime'] = os.path.getmtime(destination)

        self.current_session_operations.append(operation)

        # Save to disk
        self._append_operation(operation)

        logger.debug(f"Recorded operation: {operation_type} {source} -> {destination}")

    def end_session(self) -> Optional[str]:
        """
        End the current rollback session

        Returns:
            Session ID or None if no active session
        """
        if self.current_session_file is None:
            return None

        session_data = self._load_session(self.current_session_file)
        if session_data:
            session_data['ended_at'] = datetime.now().isoformat()
            session_data['total_operations'] = len(self.current_session_operations)
            self._save_session(session_data)

        session_id = session_data.get('session_id') if session_data else None

        self.current_session_file = None
        self.current_session_operations = []

        logger.info(f"Ended rollback session: {session_id}")
        return session_id

    def rollback_session(self, session_id: Optional[str] = None,
                        dry_run: bool = False) -> Dict:
        """
        Rollback operations from a session

        Args:
            session_id: Session to rollback (default: current session)
            dry_run: If True, only simulate rollback without executing

        Returns:
            Dictionary with rollback results
        """
        # Determine which session to rollback
        if session_id is None:
            session_file = self.current_session_file
            if session_file is None:
                return {'error': 'No active session'}
        else:
            session_file = self._find_session_file(session_id)
            if session_file is None:
                return {'error': f'Session not found: {session_id}'}

        # Load session data
        session_data = self._load_session(session_file)
        if not session_data:
            return {'error': 'Failed to load session data'}

        operations = session_data.get('operations', [])

        results = {
            'session_id': session_data.get('session_id'),
            'total_operations': len(operations),
            'rolled_back': 0,
            'skipped': 0,
            'failed': 0,
            'errors': [],
            'dry_run': dry_run
        }

        # Rollback operations in reverse order
        for operation in reversed(operations):
            if operation.get('rolled_back'):
                results['skipped'] += 1
                continue

            success = self._rollback_single_operation(operation, dry_run)

            if success:
                results['rolled_back'] += 1
                if not dry_run:
                    operation['rolled_back'] = True
            else:
                results['failed'] += 1
                results['errors'].append({
                    'operation': operation,
                    'error': 'Rollback failed'
                })

        # Save updated session data
        if not dry_run:
            session_data['rolled_back_at'] = datetime.now().isoformat()
            self._save_session(session_data)

        logger.info(f"Rollback session {session_data.get('session_id')}: "
                   f"{results['rolled_back']} succeeded, {results['failed']} failed")

        return results

    def _rollback_single_operation(self, operation: Dict, dry_run: bool = False) -> bool:
        """
        Rollback a single file operation

        Args:
            operation: Operation dictionary
            dry_run: If True, don't actually perform rollback

        Returns:
            True if successful, False otherwise
        """
        op_type = operation['type']
        source = operation['source']
        destination = operation['destination']

        try:
            if op_type == 'move':
                # Move file back to original location
                if not os.path.exists(destination):
                    logger.warning(f"Destination file not found: {destination}")
                    return False

                if os.path.exists(source):
                    logger.warning(f"Source location already occupied: {source}")
                    return False

                if not dry_run:
                    # Ensure source directory exists
                    os.makedirs(os.path.dirname(source), exist_ok=True)
                    shutil.move(destination, source)
                    logger.info(f"Rolled back move: {destination} -> {source}")

                return True

            elif op_type == 'copy':
                # Delete the copied file
                if not os.path.exists(destination):
                    logger.warning(f"Copied file not found: {destination}")
                    return False

                if not dry_run:
                    os.remove(destination)
                    logger.info(f"Rolled back copy: deleted {destination}")

                return True

            elif op_type == 'rename':
                # Rename file back to original name
                if not os.path.exists(destination):
                    logger.warning(f"Renamed file not found: {destination}")
                    return False

                if os.path.exists(source):
                    logger.warning(f"Original name already exists: {source}")
                    return False

                if not dry_run:
                    os.rename(destination, source)
                    logger.info(f"Rolled back rename: {destination} -> {source}")

                return True

            else:
                logger.error(f"Unknown operation type: {op_type}")
                return False

        except Exception as e:
            logger.error(f"Error rolling back operation: {e}")
            return False

    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """
        List available rollback sessions

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        sessions = []

        try:
            session_files = sorted(
                self.history_dir.glob("session_*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            for session_file in session_files[:limit]:
                session_data = self._load_session(session_file)
                if session_data:
                    summary = {
                        'session_id': session_data.get('session_id'),
                        'session_name': session_data.get('session_name'),
                        'started_at': session_data.get('started_at'),
                        'ended_at': session_data.get('ended_at'),
                        'total_operations': len(session_data.get('operations', [])),
                        'rolled_back': session_data.get('rolled_back_at') is not None
                    }
                    sessions.append(summary)

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")

        return sessions

    def get_session_details(self, session_id: str) -> Optional[Dict]:
        """
        Get detailed information about a session

        Args:
            session_id: Session ID

        Returns:
            Session data or None if not found
        """
        session_file = self._find_session_file(session_id)
        if session_file:
            return self._load_session(session_file)
        return None

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from history

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        session_file = self._find_session_file(session_id)
        if session_file and session_file.exists():
            try:
                session_file.unlink()
                logger.info(f"Deleted session: {session_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting session: {e}")
                return False
        return False

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Delete sessions older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of sessions deleted
        """
        import time
        threshold = time.time() - (days * 24 * 60 * 60)
        count = 0

        try:
            for session_file in self.history_dir.glob("session_*.json"):
                if session_file.stat().st_mtime < threshold:
                    session_file.unlink()
                    count += 1

            logger.info(f"Cleaned up {count} old sessions")

        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")

        return count

    def _save_session(self, session_data: Dict) -> bool:
        """Save session data to file"""
        try:
            with open(self.current_session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False

    def _load_session(self, session_file: Path) -> Optional[Dict]:
        """Load session data from file"""
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session {session_file}: {e}")
            return None

    def _append_operation(self, operation: Dict) -> bool:
        """Append operation to current session file"""
        try:
            session_data = self._load_session(self.current_session_file)
            if session_data:
                session_data['operations'].append(operation)
                return self._save_session(session_data)
            return False
        except Exception as e:
            logger.error(f"Error appending operation: {e}")
            return False

    def _find_session_file(self, session_id: str) -> Optional[Path]:
        """Find session file by session ID"""
        session_file = self.history_dir / f"session_{session_id}.json"
        if session_file.exists():
            return session_file

        # Try to find by partial match
        for f in self.history_dir.glob(f"session_*{session_id}*.json"):
            return f

        return None


# Global rollback manager instance
_rollback_instance = None


def get_rollback_manager() -> RollbackManager:
    """Get the global rollback manager instance"""
    global _rollback_instance
    if _rollback_instance is None:
        _rollback_instance = RollbackManager()
    return _rollback_instance
