"""Persistent progress manager for tracking collected exploration markers."""

from __future__ import annotations
from datetime import datetime, timezone
import json
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ProgressStorageError(Exception):
    """Raised on unrecoverable progress file access errors."""
    pass


class ProgressManager:
    """Manages player marker collection progress with atomic writes, backups, and versioning."""

    STORAGE_VERSION = 2

    def __init__(self, filepath: Optional[str] = None) -> None:
        if filepath is None:
            base_dir = os.path.join(os.getcwd(), "userData")
            os.makedirs(base_dir, exist_ok=True)
            filepath = os.path.join(base_dir, "progress.json")

        self._filepath = os.path.abspath(filepath)
        self._backup_filepath = f"{self._filepath}.bak"
        # Map: marker_id -> {"collected_at": iso_str, "notes": str}
        self._collected_records: Dict[str, Dict[str, Any]] = {}
        self._last_saved_at: Optional[str] = None
        self._metadata: Dict[str, Any] = {}

        if os.path.exists(self._filepath):
            self.load()

    @property
    def filepath(self) -> str:
        return self._filepath

    @property
    def backup_filepath(self) -> str:
        return self._backup_filepath

    @property
    def collected_count(self) -> int:
        return len(self._collected_records)

    def is_collected(self, marker_id: str) -> bool:
        """Check if marker is marked as collected."""
        return marker_id in self._collected_records

    def get_collected_ids(self) -> Set[str]:
        """Return set of all collected marker IDs."""
        return set(self._collected_records.keys())

    def get_collection_record(self, marker_id: str) -> Optional[Dict[str, Any]]:
        """Get collection metadata (timestamp, notes) for a marker."""
        return self._collected_records.get(marker_id)

    def replace_record(self, marker_id: str, record: Optional[Dict[str, Any]]) -> None:
        """Restore or replace a complete record, including its original deadline."""
        if record is None:
            self._collected_records.pop(marker_id,None)
        else:
            self._collected_records[marker_id]=dict(record)

    @staticmethod
    def _clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
        result={"collected_at":str(record.get("collected_at","")),"notes":str(record.get("notes",""))}
        for key in ("ready_at","rule_id"):
            if isinstance(record.get(key),str): result[key]=record[key]
        return result

    def mark_collected(self, marker_id: str, notes: str = "") -> bool:
        """Mark marker as collected.

        Returns:
            True if marker was newly marked, False if it was already collected.
        """
        if marker_id in self._collected_records:
            return False
        timestamp = datetime.now(timezone.utc).isoformat()
        self._collected_records[marker_id] = {
            "collected_at": timestamp,
            "notes": notes,
        }
        return True

    def mark_uncollected(self, marker_id: str) -> bool:
        """Unmark marker as collected.

        Returns:
            True if marker was removed, False if it was not collected.
        """
        if marker_id in self._collected_records:
            del self._collected_records[marker_id]
            return True
        return False

    def toggle_collected(self, marker_id: str) -> bool:
        """Toggle collected state for marker.

        Returns:
            New collected state (True if now collected, False if uncollected).
        """
        if self.is_collected(marker_id):
            self.mark_uncollected(marker_id)
            return False
        else:
            self.mark_collected(marker_id)
            return True

    def save(self) -> None:
        """Atomically persist current progress to disk with a safety backup.

        Algorithm:
        1. Ensure target directory exists.
        2. If main file exists, copy it to backup file (.bak).
        3. Write JSON payload to temporary file in the same directory.
        4. Flush and sync temporary file.
        5. Atomically replace main file with temp file (os.replace).
        """
        target_dir = os.path.dirname(self._filepath)
        os.makedirs(target_dir, exist_ok=True)

        # 1. Create backup if current file exists
        if os.path.exists(self._filepath):
            # Keep the original pre-migration file forever, independently of .bak.
            try:
                try:
                    with open(self._filepath,encoding="utf-8") as current:
                        previous_version=json.load(current).get("version",1)
                except (ValueError,AttributeError):
                    previous_version=1
                migration=f"{self._filepath}.pre-v{self.STORAGE_VERSION}.bak"
                if previous_version<self.STORAGE_VERSION and not os.path.exists(migration):
                    shutil.copy2(self._filepath,migration)
            except (OSError,ValueError,TypeError) as exc:
                raise ProgressStorageError(f"Cannot back up progress before migration: {exc}") from exc
            try:
                shutil.copy2(self._filepath, self._backup_filepath)
            except Exception as e:
                logger.warning("Failed to create progress backup file: %s", e)

        payload = {
            "version": self.STORAGE_VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "collected_count": len(self._collected_records),
            "records": self._collected_records,
            "metadata": self._metadata,
        }

        # 2. Write to temp file in target_dir to guarantee atomic move across same filesystem
        temp_fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix="progress_tmp_", suffix=".json")
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # 3. Atomic rename/replace
            os.replace(temp_path, self._filepath)
            self._last_saved_at = payload["updated_at"]
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise ProgressStorageError(f"Failed to atomically save progress: {e}") from e

    def load(self) -> bool:
        """Load progress from disk. Falls back to .bak file on corruption.

        Returns:
            True if loaded successfully, False if neither main nor backup was loadable.
        """
        success = self._try_load_file(self._filepath)
        if success:
            return True

        # If primary failed or was corrupted, attempt backup recovery
        if os.path.exists(self._backup_filepath):
            logger.warning("Primary progress file failed to load; attempting recovery from backup.")
            backup_success = self._try_load_file(self._backup_filepath)
            if backup_success:
                # Restore primary file from valid backup
                try:
                    shutil.copy2(self._backup_filepath, self._filepath)
                except Exception as e:
                    logger.error("Failed to restore primary file from backup: %s", e)
                return True

        return False

    def _try_load_file(self, filepath: str) -> bool:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return False

            version = data.get("version", 1)
            records = data.get("records", {})
            if isinstance(records, dict):
                # Clean and validate records
                self._collected_records = {
                    str(k): self._clean_record(v)
                    if isinstance(v, dict)
                    else {"collected_at": "", "notes": ""}
                    for k, v in records.items()
                }
            elif isinstance(records, list):
                # Backward compatibility with simple list of IDs
                now_str = datetime.now(timezone.utc).isoformat()
                self._collected_records = {str(item): {"collected_at": now_str, "notes": ""} for item in records}

            self._last_saved_at = data.get("updated_at")
            self._metadata = data.get("metadata", {})
            return True
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            logger.error("Error reading progress file '%s': %s", filepath, e)
            return False

    def export_to_json(self, export_path: str) -> None:
        """Export progress records to an external JSON file."""
        export_dir = os.path.dirname(export_path)
        if export_dir:
            os.makedirs(export_dir, exist_ok=True)

        payload = {
            "version": self.STORAGE_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "collected_count": len(self._collected_records),
            "records": self._collected_records,
        }

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def import_from_json(self, import_path: str, merge: bool = True) -> int:
        """Import progress from an external JSON file.

        Args:
            import_path: Path to external file.
            merge: If True, merges with existing progress; if False, replaces existing progress.

        Returns:
            Number of imported/updated records.
        """
        with open(import_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get("records", {})
        if not isinstance(records, dict) and isinstance(records, list):
            now_str = datetime.now(timezone.utc).isoformat()
            records = {str(item): {"collected_at": now_str, "notes": ""} for item in records}

        if not merge:
            self._collected_records.clear()

        count = 0
        for marker_id, info in records.items():
            if isinstance(info, dict):
                self._collected_records[str(marker_id)] = self._clean_record(info)
            else:
                self._collected_records[str(marker_id)] = {
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "notes": "",
                }
            count += 1

        self.save()
        return count

    def reset(self, create_backup: bool = True) -> None:
        """Reset all collection progress."""
        if create_backup and len(self._collected_records) > 0:
            self.save()  # Ensure current state is in .bak
        self._collected_records.clear()
        self.save()
