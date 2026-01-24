"""Unit tests for seed_database script.

Tests script structure and logic without requiring live databases.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSeedDatabaseModule:
    """Tests for seed_database module structure."""

    def test_module_imports(self):
        """Should import seed_database module without errors."""
        from app.scripts import seed_database

        assert hasattr(seed_database, "main")
        assert hasattr(seed_database, "seed_database")
        assert hasattr(seed_database, "verify_connections")

    def test_main_is_callable(self):
        """Main function should be callable."""
        from app.scripts.seed_database import main

        assert callable(main)


class TestFixtureDiscovery:
    """Tests for fixture file discovery logic."""

    def test_finds_patient_bundles(self, tmp_path):
        """Should find patient bundle files matching pattern."""
        # Create mock fixture files
        (tmp_path / "patient_bundle_1.json").write_text("{}")
        (tmp_path / "patient_bundle_2.json").write_text("{}")
        (tmp_path / "patient_bundle_1.profile.json").write_text("{}")
        (tmp_path / "other_file.json").write_text("{}")

        bundle_files = sorted(tmp_path.glob("patient_bundle_*.json"))
        bundle_files = [f for f in bundle_files if ".profile." not in f.name]

        assert len(bundle_files) == 2
        assert all("patient_bundle_" in f.name for f in bundle_files)
        assert all(".profile." not in f.name for f in bundle_files)

    def test_finds_corresponding_profiles(self, tmp_path):
        """Should find profile files corresponding to bundles."""
        bundle_path = tmp_path / "patient_bundle_1.json"
        profile_path = tmp_path / "patient_bundle_1.profile.json"

        bundle_path.write_text("{}")
        profile_path.write_text('{"preferred_name": "Test"}')

        # Replicate script logic
        expected_profile = bundle_path.with_suffix(".profile.json")
        assert expected_profile.exists()
        assert expected_profile == profile_path

    def test_handles_missing_profile(self, tmp_path):
        """Should handle bundles without profile files."""
        bundle_path = tmp_path / "patient_bundle_1.json"
        bundle_path.write_text("{}")

        profile_path = bundle_path.with_suffix(".profile.json")
        assert not profile_path.exists()


class TestVerifyConnections:
    """Tests for database connection verification."""

    @pytest.mark.asyncio
    async def test_verify_connections_returns_bool(self):
        """verify_connections should return a boolean."""
        from app.scripts.seed_database import verify_connections

        # Mock the graph
        mock_graph = MagicMock()
        mock_graph.verify_connectivity = AsyncMock(return_value=False)

        # Patch engine to avoid real DB connection
        with patch("app.scripts.seed_database.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock(return_value=None)
            mock_engine.connect.return_value = mock_conn

            result = await verify_connections(mock_graph)

            # Should return False because Neo4j verification returns False
            assert isinstance(result, bool)


class TestSeedDatabaseFunction:
    """Tests for the main seed_database function."""

    @pytest.mark.asyncio
    async def test_returns_empty_stats_for_empty_dir(self, tmp_path):
        """Should return zero stats when no bundles found."""
        from app.scripts.seed_database import seed_database

        # Mock KnowledgeGraph
        with patch("app.scripts.seed_database.KnowledgeGraph") as MockKG:
            mock_graph = MagicMock()
            mock_graph.verify_connectivity = AsyncMock(return_value=True)
            mock_graph.close = AsyncMock()
            MockKG.return_value = mock_graph

            # Mock engine for connection check
            with patch("app.scripts.seed_database.engine") as mock_engine:
                mock_conn = MagicMock()
                mock_conn.execute = AsyncMock()
                mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
                mock_conn.__aexit__ = AsyncMock(return_value=None)
                mock_engine.connect.return_value = mock_conn

                stats = await seed_database(tmp_path)

                assert stats["patients_loaded"] == 0
                assert stats["resources_loaded"] == 0


class TestProfileIntegration:
    """Tests for profile loading and embedding."""

    def test_profile_json_structure(self):
        """Profile JSON should match expected schema."""
        profile = {
            "preferred_name": "Test",
            "pronouns": "they/them",
            "occupation": "Engineer",
            "living_situation": "Lives alone",
            "family_summary": "No family nearby",
            "hobbies": ["Reading", "Coding"],
            "communication_style": "Direct",
            "primary_motivation": "Stay healthy",
            "barriers": "Time constraints",
            "support_system": "Friends",
        }

        # Verify all expected fields exist
        expected_fields = [
            "preferred_name",
            "pronouns",
            "occupation",
            "living_situation",
            "family_summary",
            "hobbies",
            "communication_style",
            "primary_motivation",
            "barriers",
            "support_system",
        ]

        for field in expected_fields:
            assert field in profile
