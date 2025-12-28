#!/usr/bin/env python3
"""
Session Manager for Interactive Web Agent MCP
Manages debug sessions with automatic timeout and file-based tracking.
"""

import os
import json
import uuid
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import threading


# Platform-specific file locking
if platform.system() == "Windows":
    import msvcrt

    def lock_file(file_handle):
        """Lock file on Windows"""
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)

    def unlock_file(file_handle):
        """Unlock file on Windows"""
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def lock_file(file_handle):
        """Lock file on Unix/Linux/Mac"""
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def unlock_file(file_handle):
        """Unlock file on Unix/Linux/Mac"""
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)


class SessionManager:
    """
    Manages debug sessions for the Interactive Web Agent MCP.

    A session is a series of operations where consecutive operations
    have less than SESSION_TIMEOUT_SECONDS interval.
    """

    def __init__(self, base_dir: str, timeout_seconds: int = 60):
        """
        Initialize SessionManager

        Args:
            base_dir: Base directory for session storage (e.g., DOWNLOADS_DIR)
            timeout_seconds: Seconds between operations to consider same session
        """
        self.base_dir = Path(base_dir)
        self.sessions_dir = self.base_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.manager_file = self.sessions_dir / "session_manager.json"
        self.timeout_seconds = timeout_seconds

        self._current_session_id: Optional[str] = None
        self._current_session_dir: Optional[Path] = None
        self._lock = threading.Lock()

    def get_or_create_session(self) -> tuple[str, Path]:
        """
        Get current session or create new one based on timeout

        Returns:
            Tuple of (session_id, session_directory_path)
        """
        with self._lock:
            manager_data = self._load_manager_file()

            # Check if we should reuse existing session
            if manager_data.get("current_session_id"):
                last_op_time = manager_data.get("last_operation_time")
                if last_op_time:
                    try:
                        last_time = datetime.fromisoformat(last_op_time)
                        time_diff = datetime.now() - last_time

                        # Reuse session if within timeout
                        if time_diff.total_seconds() < self.timeout_seconds:
                            session_id = manager_data["current_session_id"]
                            session_dir = self.sessions_dir / session_id

                            if session_dir.exists():
                                self._current_session_id = session_id
                                self._current_session_dir = session_dir

                                # Update last operation time
                                self._update_manager_file(session_id, increment_count=False)

                                return session_id, session_dir
                    except (ValueError, KeyError):
                        pass

            # Create new session
            session_id = self._generate_session_id()
            session_dir = self.sessions_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            (session_dir / "html").mkdir(exist_ok=True)
            (session_dir / "screenshots").mkdir(exist_ok=True)

            # Initialize session metadata
            self._init_session_metadata(session_id, session_dir)

            # Update manager file
            self._update_manager_file(session_id, increment_count=False)

            self._current_session_id = session_id
            self._current_session_dir = session_dir

            return session_id, session_dir

    def update_operation_time(self):
        """Update the last operation time for current session"""
        with self._lock:
            if self._current_session_id:
                self._update_manager_file(self._current_session_id, increment_count=True)
                self._update_session_metadata()

    def _generate_session_id(self) -> str:
        """
        Generate session ID: {8-char-uuid}_{YYYYMMDDHHmmss}

        Returns:
            Session ID string
        """
        uuid_part = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{uuid_part}_{timestamp}"

    def _load_manager_file(self) -> Dict[str, Any]:
        """
        Load session manager file with file locking

        Returns:
            Manager data dict
        """
        if not self.manager_file.exists():
            return {
                "current_session_id": None,
                "last_operation_time": None,
                "sessions": {}
            }

        try:
            with open(self.manager_file, 'r', encoding='utf-8') as f:
                try:
                    lock_file(f)
                    data = json.load(f)
                    unlock_file(f)
                    return data
                except:
                    # Fallback if locking fails
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {
                "current_session_id": None,
                "last_operation_time": None,
                "sessions": {}
            }

    def _save_manager_file(self, data: Dict[str, Any]):
        """
        Save session manager file with file locking

        Args:
            data: Manager data dict
        """
        try:
            with open(self.manager_file, 'w', encoding='utf-8') as f:
                try:
                    lock_file(f)
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    unlock_file(f)
                except:
                    # Fallback if locking fails
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save session manager file: {e}")

    def _update_manager_file(self, session_id: str, increment_count: bool = True):
        """
        Update manager file with current session info

        Args:
            session_id: Current session ID
            increment_count: Whether to increment operation count
        """
        data = self._load_manager_file()

        now = datetime.now().isoformat()
        data["current_session_id"] = session_id
        data["last_operation_time"] = now

        if session_id not in data["sessions"]:
            data["sessions"][session_id] = {
                "created_at": now,
                "last_operation_at": now,
                "operation_count": 0,
                "status": "active"
            }

        session_info = data["sessions"][session_id]
        session_info["last_operation_at"] = now

        if increment_count:
            session_info["operation_count"] = session_info.get("operation_count", 0) + 1

        self._save_manager_file(data)

    def _init_session_metadata(self, session_id: str, session_dir: Path):
        """
        Initialize session metadata file

        Args:
            session_id: Session ID
            session_dir: Session directory path
        """
        metadata = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_operation_at": datetime.now().isoformat(),
            "operation_count": 0,
            "status": "active",
            "initial_url": None,
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.system(),
                "platform_release": platform.release()
            }
        }

        metadata_file = session_dir / "session.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Create empty operations.jsonl
        operations_file = session_dir / "operations.jsonl"
        operations_file.touch()

    def _update_session_metadata(self):
        """Update session metadata with latest operation time"""
        if not self._current_session_dir:
            return

        metadata_file = self._current_session_dir / "session.json"

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            metadata["last_operation_at"] = datetime.now().isoformat()
            metadata["operation_count"] = metadata.get("operation_count", 0) + 1

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to update session metadata: {e}")

    def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current session information

        Returns:
            Session info dict or None
        """
        if not self._current_session_id or not self._current_session_dir:
            return None

        return {
            "session_id": self._current_session_id,
            "session_dir": str(self._current_session_dir),
            "timeout_seconds": self.timeout_seconds
        }

    def close_session(self):
        """Mark current session as closed"""
        with self._lock:
            if self._current_session_id and self._current_session_dir:
                try:
                    metadata_file = self._current_session_dir / "session.json"
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    metadata["status"] = "closed"
                    metadata["closed_at"] = datetime.now().isoformat()

                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Warning: Failed to close session: {e}")

                self._current_session_id = None
                self._current_session_dir = None
