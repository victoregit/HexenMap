"""Unit tests for ProgressManager atomic persistence and backup recovery."""

import json
import os
import pytest
from src.progress.progress_manager import ProgressManager, ProgressStorageError


class TestProgressManager:
    def test_mark_and_toggle(self, progress_mgr):
        assert progress_mgr.collected_count == 0
        assert progress_mgr.is_collected("m1") is False

        # Mark collected
        newly_marked = progress_mgr.mark_collected("m1", notes="Found under rock")
        assert newly_marked is True
        assert progress_mgr.is_collected("m1") is True
        assert progress_mgr.collected_count == 1

        # Double mark returns False
        assert progress_mgr.mark_collected("m1") is False

        # Toggle uncollected
        state = progress_mgr.toggle_collected("m1")
        assert state is False
        assert progress_mgr.is_collected("m1") is False
        assert progress_mgr.collected_count == 0

        # Toggle collected again
        state2 = progress_mgr.toggle_collected("m1")
        assert state2 is True
        assert progress_mgr.is_collected("m1") is True

    def test_atomic_save_and_reload(self, progress_mgr, temp_progress_file):
        progress_mgr.mark_collected("m1")
        progress_mgr.mark_collected("m2")
        progress_mgr.save()

        assert os.path.exists(temp_progress_file)

        # Create new manager pointing to same file
        reloaded = ProgressManager(filepath=temp_progress_file)
        assert reloaded.collected_count == 2
        assert reloaded.is_collected("m1") is True
        assert reloaded.is_collected("m2") is True
        assert reloaded.is_collected("m3") is False

    def test_backup_creation_and_recovery(self, progress_mgr, temp_progress_file):
        # 1. Initial save creates file
        progress_mgr.mark_collected("m1")
        progress_mgr.save()

        # 2. Second save creates .bak of the previous state
        progress_mgr.mark_collected("m2")
        progress_mgr.save()

        bak_file = f"{temp_progress_file}.bak"
        assert os.path.exists(bak_file)

        # 3. Simulate corrupting the primary file
        with open(temp_progress_file, "w", encoding="utf-8") as f:
            f.write("{corrupted_json_syntax...")

        # 4. New manager should recover from .bak
        recovered = ProgressManager(filepath=temp_progress_file)
        assert recovered.is_collected("m1") is True
        # The primary file should have been restored from backup
        with open(temp_progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "records" in data

    def test_export_and_import(self, progress_mgr, tmp_path):
        progress_mgr.mark_collected("m1")
        progress_mgr.mark_collected("m2")

        export_file = str(tmp_path / "export.json")
        progress_mgr.export_to_json(export_file)
        assert os.path.exists(export_file)

        # Create new fresh manager
        fresh_file = str(tmp_path / "fresh.json")
        new_mgr = ProgressManager(filepath=fresh_file)
        assert new_mgr.collected_count == 0

        imported_count = new_mgr.import_from_json(export_file, merge=True)
        assert imported_count == 2
        assert new_mgr.is_collected("m1") is True
        assert new_mgr.is_collected("m2") is True

    def test_reset_with_backup(self, progress_mgr, temp_progress_file):
        progress_mgr.mark_collected("m1")
        progress_mgr.mark_collected("m2")
        progress_mgr.save()

        progress_mgr.reset(create_backup=True)
        assert progress_mgr.collected_count == 0

        # Backup file should retain previous entries
        bak_file = f"{temp_progress_file}.bak"
        assert os.path.exists(bak_file)
        with open(bak_file, "r", encoding="utf-8") as f:
            bak_data = json.load(f)
        assert "m1" in bak_data["records"]
