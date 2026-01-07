from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from playbook.trace_writer import TraceOptions, persist_trace


class TestTraceOptions:
    def test_default_values(self) -> None:
        """Test that TraceOptions has correct default values."""
        options = TraceOptions()
        assert options.enabled is False
        assert options.output_dir is None

    def test_enabled_true(self) -> None:
        """Test creating TraceOptions with enabled=True."""
        options = TraceOptions(enabled=True)
        assert options.enabled is True
        assert options.output_dir is None

    def test_custom_output_dir(self) -> None:
        """Test creating TraceOptions with custom output_dir."""
        custom_dir = Path("/tmp/custom_traces")
        options = TraceOptions(enabled=True, output_dir=custom_dir)
        assert options.enabled is True
        assert options.output_dir == custom_dir

    def test_all_parameters(self) -> None:
        """Test creating TraceOptions with all parameters."""
        custom_dir = Path("/tmp/traces")
        options = TraceOptions(enabled=True, output_dir=custom_dir)
        assert options.enabled is True
        assert options.output_dir == custom_dir


class TestPersistTrace:
    def test_returns_none_when_trace_is_none(self, tmp_path) -> None:
        """Test that persist_trace returns None when trace is None."""
        options = TraceOptions(enabled=True)
        result = persist_trace(None, options, tmp_path)
        assert result is None

    def test_returns_none_when_disabled(self, tmp_path) -> None:
        """Test that persist_trace returns None when trace persistence is disabled."""
        options = TraceOptions(enabled=False)
        trace = {"filename": "test.mkv", "sport_id": "nba"}
        result = persist_trace(trace, options, tmp_path)
        assert result is None

    def test_returns_none_when_trace_empty_dict(self, tmp_path) -> None:
        """Test that persist_trace returns None when trace is an empty dict."""
        options = TraceOptions(enabled=True)
        result = persist_trace({}, options, tmp_path)
        assert result is None

    def test_creates_trace_file_with_default_output_dir(self, tmp_path) -> None:
        """Test that persist_trace creates a trace file in cache_dir/traces when no output_dir is specified."""
        options = TraceOptions(enabled=True)
        trace = {
            "filename": "test.mkv",
            "sport_id": "nba",
            "pattern": "test_pattern",
            "match": True,
        }

        result = persist_trace(trace, options, tmp_path)

        # Verify the result is a Path
        assert result is not None
        assert isinstance(result, Path)

        # Verify the file was created in cache_dir/traces
        assert result.parent == tmp_path / "traces"
        assert result.exists()

        # Verify the file extension
        assert result.suffix == ".json"

    def test_creates_trace_file_with_custom_output_dir(self, tmp_path) -> None:
        """Test that persist_trace creates a trace file in custom output_dir."""
        custom_dir = tmp_path / "custom_traces"
        options = TraceOptions(enabled=True, output_dir=custom_dir)
        trace = {
            "filename": "test.mkv",
            "sport_id": "nba",
        }

        result = persist_trace(trace, options, tmp_path)

        # Verify the file was created in custom_dir
        assert result is not None
        assert result.parent == custom_dir
        assert result.exists()

    def test_writes_valid_json(self, tmp_path) -> None:
        """Test that persist_trace writes valid JSON content."""
        options = TraceOptions(enabled=True)
        trace = {
            "filename": "test.mkv",
            "sport_id": "nba",
            "pattern": "test_pattern",
            "matched": True,
            "groups": {"season": "2024", "episode": "01"},
        }

        result = persist_trace(trace, options, tmp_path)

        # Read the JSON file
        assert result is not None
        with result.open("r", encoding="utf-8") as f:
            written_data = json.load(f)

        # Verify all original trace data is present
        assert written_data["filename"] == "test.mkv"
        assert written_data["sport_id"] == "nba"
        assert written_data["pattern"] == "test_pattern"
        assert written_data["matched"] is True
        assert written_data["groups"]["season"] == "2024"

        # Verify trace_path was added
        assert "trace_path" in written_data
        assert written_data["trace_path"] == str(result)

    def test_generates_consistent_filename_for_same_trace_key(self, tmp_path) -> None:
        """Test that the same filename/sport_id combination generates the same trace filename."""
        options = TraceOptions(enabled=True)

        trace1 = {"filename": "test.mkv", "sport_id": "nba", "data": "first"}
        result1 = persist_trace(trace1, options, tmp_path)

        trace2 = {"filename": "test.mkv", "sport_id": "nba", "data": "second"}
        result2 = persist_trace(trace2, options, tmp_path)

        # Same filename and sport_id should generate the same trace file path
        assert result1 == result2

        # Verify the file was overwritten with the second trace's data
        assert result2 is not None
        with result2.open("r", encoding="utf-8") as f:
            written_data = json.load(f)
        assert written_data["data"] == "second"

    def test_generates_different_filenames_for_different_keys(self, tmp_path) -> None:
        """Test that different filename/sport_id combinations generate different trace files."""
        options = TraceOptions(enabled=True)

        trace1 = {"filename": "test1.mkv", "sport_id": "nba"}
        result1 = persist_trace(trace1, options, tmp_path)

        trace2 = {"filename": "test2.mkv", "sport_id": "nba"}
        result2 = persist_trace(trace2, options, tmp_path)

        trace3 = {"filename": "test1.mkv", "sport_id": "nfl"}
        result3 = persist_trace(trace3, options, tmp_path)

        # All should generate different filenames
        assert result1 != result2
        assert result1 != result3
        assert result2 != result3

        # All files should exist
        assert result1 is not None and result1.exists()
        assert result2 is not None and result2.exists()
        assert result3 is not None and result3.exists()

    def test_handles_missing_filename_in_trace(self, tmp_path) -> None:
        """Test that persist_trace handles traces without filename key."""
        options = TraceOptions(enabled=True)
        trace = {"sport_id": "nba", "pattern": "test"}

        result = persist_trace(trace, options, tmp_path)

        # Should still create a trace file (using empty string for filename in key)
        assert result is not None
        assert result.exists()

    def test_handles_missing_sport_id_in_trace(self, tmp_path) -> None:
        """Test that persist_trace handles traces without sport_id key."""
        options = TraceOptions(enabled=True)
        trace = {"filename": "test.mkv", "pattern": "test"}

        result = persist_trace(trace, options, tmp_path)

        # Should still create a trace file (using empty string for sport_id in key)
        assert result is not None
        assert result.exists()

    def test_adds_trace_path_to_original_dict(self, tmp_path) -> None:
        """Test that persist_trace modifies the original trace dict to add trace_path."""
        options = TraceOptions(enabled=True)
        trace = {"filename": "test.mkv", "sport_id": "nba"}

        # Verify trace_path is not in original dict
        assert "trace_path" not in trace

        result = persist_trace(trace, options, tmp_path)

        # Verify trace_path was added to the original dict
        assert "trace_path" in trace
        assert trace["trace_path"] == str(result)

    def test_handles_write_error_gracefully(self, tmp_path) -> None:
        """Test that persist_trace handles write errors gracefully and returns None."""
        options = TraceOptions(enabled=True)
        trace = {"filename": "test.mkv", "sport_id": "nba"}

        # Mock the file open to raise an exception
        with patch("pathlib.Path.open", side_effect=OSError("Disk full")):
            result = persist_trace(trace, options, tmp_path)

            # Should return None on error
            assert result is None

    def test_handles_json_dump_error_gracefully(self, tmp_path) -> None:
        """Test that persist_trace handles JSON serialization errors gracefully."""
        options = TraceOptions(enabled=True)
        trace = {"filename": "test.mkv", "sport_id": "nba"}

        # Mock json.dump to raise an exception
        with patch("json.dump", side_effect=TypeError("Cannot serialize")):
            result = persist_trace(trace, options, tmp_path)

            # Should return None on error
            assert result is None

    def test_preserves_unicode_in_json(self, tmp_path) -> None:
        """Test that persist_trace preserves Unicode characters in JSON output."""
        options = TraceOptions(enabled=True)
        trace = {
            "filename": "テスト.mkv",  # Japanese characters
            "sport_id": "nba",
            "title": "Tëst Spörtś",  # Accented characters
        }

        result = persist_trace(trace, options, tmp_path)

        # Read the JSON file
        assert result is not None
        with result.open("r", encoding="utf-8") as f:
            written_data = json.load(f)

        # Verify Unicode was preserved
        assert written_data["filename"] == "テスト.mkv"
        assert written_data["title"] == "Tëst Spörtś"

    def test_creates_output_directory_if_not_exists(self, tmp_path) -> None:
        """Test that persist_trace creates the output directory if it doesn't exist."""
        custom_dir = tmp_path / "nested" / "trace" / "directory"
        options = TraceOptions(enabled=True, output_dir=custom_dir)
        trace = {"filename": "test.mkv", "sport_id": "nba"}

        # Verify directory doesn't exist
        assert not custom_dir.exists()

        result = persist_trace(trace, options, tmp_path)

        # Verify directory was created
        assert custom_dir.exists()
        assert custom_dir.is_dir()

        # Verify file was created in the directory
        assert result is not None
        assert result.parent == custom_dir
        assert result.exists()

    def test_json_output_is_formatted_with_indentation(self, tmp_path) -> None:
        """Test that persist_trace writes JSON with proper indentation for readability."""
        options = TraceOptions(enabled=True)
        trace = {
            "filename": "test.mkv",
            "sport_id": "nba",
            "nested": {"key": "value"},
        }

        result = persist_trace(trace, options, tmp_path)

        # Read the raw JSON text
        assert result is not None
        with result.open("r", encoding="utf-8") as f:
            content = f.read()

        # Verify the JSON is indented (contains newlines and spaces)
        assert "\n" in content
        assert "  " in content  # 2-space indentation

        # Verify it's still valid JSON
        parsed = json.loads(content)
        assert parsed["filename"] == "test.mkv"
