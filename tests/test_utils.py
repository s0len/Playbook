from __future__ import annotations

import os

import pytest

from playbook.utils import (
    clear_normalize_cache,
    env_bool,
    env_list,
    get_normalize_cache_info,
    hash_file,
    hash_text,
    link_file,
    normalize_token,
    parse_env_bool,
    sanitize_component,
    slugify,
    validate_url,
)


def test_normalize_token_removes_non_alphanumerics() -> None:
    assert normalize_token("FP1 Warm-Up!") == "fp1warmup"


def test_slugify_handles_punctuation_and_case() -> None:
    assert slugify("Grand Prix #1") == "grand-prix-1"


def test_sanitize_component_replaces_disallowed_characters() -> None:
    assert sanitize_component("  weird*name?.mkv  ") == "weird_name_.mkv"
    assert sanitize_component("???") == "untitled"


def test_sanitize_component_rejects_dot_segments() -> None:
    assert sanitize_component(".") == "untitled"
    assert sanitize_component("..") == "untitled"
    assert sanitize_component(" .. ") == "untitled"


def test_link_file_creates_destination_and_detects_existing(tmp_path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("test-data", encoding="utf-8")

    destination = tmp_path / "nested" / "destination.txt"

    result = link_file(source, destination)
    assert result.created is True
    assert destination.exists()
    assert destination.read_text(encoding="utf-8") == "test-data"

    second = link_file(source, destination)
    assert second.created is False
    assert second.reason == "destination-exists"


class TestParseEnvBool:
    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"])
    def test_parses_truthy_values(self, value: str) -> None:
        assert parse_env_bool(value) is True

    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF"])
    def test_parses_falsy_values(self, value: str) -> None:
        assert parse_env_bool(value) is False

    def test_returns_none_for_none(self) -> None:
        assert parse_env_bool(None) is None

    def test_returns_none_for_unrecognized(self) -> None:
        assert parse_env_bool("maybe") is None
        assert parse_env_bool("") is None

    def test_strips_whitespace(self) -> None:
        assert parse_env_bool("  true  ") is True


class TestEnvBool:
    def test_reads_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_BOOL", "true")
        assert env_bool("TEST_BOOL") is True

        monkeypatch.setenv("TEST_BOOL", "false")
        assert env_bool("TEST_BOOL") is False

    def test_returns_none_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        assert env_bool("NONEXISTENT_VAR") is None


class TestEnvList:
    def test_parses_comma_separated(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_LIST", "a,b,c")
        assert env_list("TEST_LIST") == ["a", "b", "c"]

    def test_strips_whitespace(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_LIST", "  a , b , c  ")
        assert env_list("TEST_LIST") == ["a", "b", "c"]

    def test_filters_empty_parts(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_LIST", "a,,b,  ,c")
        assert env_list("TEST_LIST") == ["a", "b", "c"]

    def test_returns_empty_list_for_empty_value(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_LIST", "")
        assert env_list("TEST_LIST") == []

    def test_returns_none_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        assert env_list("NONEXISTENT_VAR") is None


class TestValidateUrl:
    def test_accepts_http(self) -> None:
        assert validate_url("http://localhost:32400") is True

    def test_accepts_https(self) -> None:
        assert validate_url("https://plex.example.com") is True

    def test_rejects_missing_scheme(self) -> None:
        assert validate_url("localhost:32400") is False

    def test_rejects_file_scheme(self) -> None:
        assert validate_url("file:///etc/passwd") is False

    def test_rejects_empty(self) -> None:
        assert validate_url("") is False

    def test_rejects_none(self) -> None:
        assert validate_url(None) is False

    def test_rejects_invalid_url(self) -> None:
        assert validate_url("http://") is False


class TestNormalizeCaching:
    def test_cache_returns_correct_results(self) -> None:
        """Verify that cached normalize_token returns the same results as non-cached."""
        clear_normalize_cache()

        test_cases = [
            ("FP1 Warm-Up!", "fp1warmup"),
            ("Grand Prix #1", "grandprix1"),
            ("Season 2024", "season2024"),
            ("Test@#$%String", "teststring"),
        ]

        for input_str, expected in test_cases:
            result = normalize_token(input_str)
            assert result == expected, f"normalize_token('{input_str}') should return '{expected}'"

            # Call again to ensure cache returns same result
            cached_result = normalize_token(input_str)
            assert cached_result == expected, f"Cached result for '{input_str}' should match"
            assert cached_result == result, "Cached result should equal first result"

    def test_clear_normalize_cache_works(self) -> None:
        """Verify that clear_normalize_cache() properly clears the cache."""
        clear_normalize_cache()

        # Make some calls to populate the cache
        normalize_token("Test String 1")
        normalize_token("Test String 2")
        normalize_token("Test String 3")

        # Verify cache has entries
        info_before = get_normalize_cache_info()
        assert info_before.currsize > 0, "Cache should have entries after normalize calls"

        # Clear the cache
        clear_normalize_cache()

        # Verify cache is empty
        info_after = get_normalize_cache_info()
        assert info_after.currsize == 0, "Cache should be empty after clear"
        assert info_after.hits == 0, "Hits should be reset after clear"
        assert info_after.misses == 0, "Misses should be reset after clear"

    def test_get_normalize_cache_info_returns_valid_info(self) -> None:
        """Verify that get_normalize_cache_info() returns valid cache statistics."""
        clear_normalize_cache()

        # Initial state should show empty cache
        info = get_normalize_cache_info()
        assert hasattr(info, "hits"), "Cache info should have 'hits' attribute"
        assert hasattr(info, "misses"), "Cache info should have 'misses' attribute"
        assert hasattr(info, "maxsize"), "Cache info should have 'maxsize' attribute"
        assert hasattr(info, "currsize"), "Cache info should have 'currsize' attribute"

        assert info.maxsize == 2048, "Max size should be 2048"
        assert info.currsize == 0, "Current size should start at 0"
        assert info.hits == 0, "Hits should start at 0"
        assert info.misses == 0, "Misses should start at 0"

        # Call normalize_token and verify cache stats update
        normalize_token("First Call")
        info_after_first = get_normalize_cache_info()
        assert info_after_first.misses == 1, "Should have 1 miss after first call"
        assert info_after_first.currsize == 1, "Should have 1 entry in cache"

        # Call same input again - should be a cache hit
        normalize_token("First Call")
        info_after_second = get_normalize_cache_info()
        assert info_after_second.hits == 1, "Should have 1 hit after second call with same input"
        assert info_after_second.misses == 1, "Misses should still be 1"
        assert info_after_second.currsize == 1, "Current size should still be 1"

        # Call with different input - should be another miss
        normalize_token("Second Call")
        info_after_third = get_normalize_cache_info()
        assert info_after_third.hits == 1, "Hits should still be 1"
        assert info_after_third.misses == 2, "Should have 2 misses after new input"
        assert info_after_third.currsize == 2, "Should have 2 entries in cache"


class TestHashText:
    def test_returns_sha256_hex_digest(self) -> None:
        """Verify hash_text returns a SHA-256 hex digest."""
        result = hash_text("hello world")
        # SHA-256 of "hello world" is known
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert result == expected

    def test_empty_string(self) -> None:
        """Verify hash_text handles empty strings."""
        result = hash_text("")
        # SHA-256 of empty string is known
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_unicode_string(self) -> None:
        """Verify hash_text handles unicode characters."""
        result = hash_text("Hello 世界 🌍")
        # SHA-256 of "Hello 世界 🌍" (UTF-8 encoded)
        expected = "61a0b9f1e77b8e86a88e8c7e4f4f2d3e3c2c3d3e3f3e4f5f6e7e8e9eaebeced"
        # Actually compute the expected value
        import hashlib

        expected = hashlib.sha256("Hello 世界 🌍".encode("utf-8")).hexdigest()
        assert result == expected

    def test_special_characters(self) -> None:
        """Verify hash_text handles special characters."""
        result = hash_text("!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`")
        import hashlib

        expected = hashlib.sha256("!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`".encode("utf-8")).hexdigest()
        assert result == expected

    def test_multiline_string(self) -> None:
        """Verify hash_text handles multiline strings."""
        text = "line 1\nline 2\nline 3"
        result = hash_text(text)
        import hashlib

        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert result == expected

    def test_same_input_same_hash(self) -> None:
        """Verify hash_text returns consistent results for same input."""
        text = "test consistency"
        result1 = hash_text(text)
        result2 = hash_text(text)
        assert result1 == result2

    def test_different_input_different_hash(self) -> None:
        """Verify hash_text returns different hashes for different inputs."""
        hash1 = hash_text("text1")
        hash2 = hash_text("text2")
        assert hash1 != hash2

    def test_returns_64_char_hex_string(self) -> None:
        """Verify hash_text returns a 64-character hex string (SHA-256 digest)."""
        result = hash_text("any text")
        assert len(result) == 64  # SHA-256 produces 256 bits = 64 hex chars
        assert all(c in "0123456789abcdef" for c in result)


class TestHashFile:
    def test_returns_sha256_hex_digest(self, tmp_path) -> None:
        """Verify hash_file returns a SHA-256 hex digest."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world", encoding="utf-8")

        result = hash_file(test_file)
        # SHA-256 of "hello world" (no newline)
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert result == expected

    def test_empty_file(self, tmp_path) -> None:
        """Verify hash_file handles empty files."""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        result = hash_file(test_file)
        # SHA-256 of empty file
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_unicode_content(self, tmp_path) -> None:
        """Verify hash_file handles files with unicode content."""
        test_file = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍"
        test_file.write_text(content, encoding="utf-8")

        result = hash_file(test_file)
        import hashlib

        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result == expected

    def test_binary_file(self, tmp_path) -> None:
        """Verify hash_file handles binary files."""
        test_file = tmp_path / "binary.bin"
        binary_data = bytes(range(256))  # All possible byte values
        test_file.write_bytes(binary_data)

        result = hash_file(test_file)
        import hashlib

        expected = hashlib.sha256(binary_data).hexdigest()
        assert result == expected

    def test_large_file(self, tmp_path) -> None:
        """Verify hash_file handles large files (tests chunking)."""
        test_file = tmp_path / "large.txt"
        # Create a file larger than the default chunk size (65536 bytes)
        large_content = "a" * 100000
        test_file.write_text(large_content, encoding="utf-8")

        result = hash_file(test_file)
        import hashlib

        expected = hashlib.sha256(large_content.encode("utf-8")).hexdigest()
        assert result == expected

    def test_same_file_same_hash(self, tmp_path) -> None:
        """Verify hash_file returns consistent results for same file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test consistency", encoding="utf-8")

        result1 = hash_file(test_file)
        result2 = hash_file(test_file)
        assert result1 == result2

    def test_different_files_different_hash(self, tmp_path) -> None:
        """Verify hash_file returns different hashes for different files."""
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding="utf-8")

        file2 = tmp_path / "file2.txt"
        file2.write_text("content2", encoding="utf-8")

        hash1 = hash_file(file1)
        hash2 = hash_file(file2)
        assert hash1 != hash2

    def test_returns_64_char_hex_string(self, tmp_path) -> None:
        """Verify hash_file returns a 64-character hex string (SHA-256 digest)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("any content", encoding="utf-8")

        result = hash_file(test_file)
        assert len(result) == 64  # SHA-256 produces 256 bits = 64 hex chars
        assert all(c in "0123456789abcdef" for c in result)

    def test_raises_error_for_nonexistent_file(self, tmp_path) -> None:
        """Verify hash_file raises an error for non-existent files."""
        nonexistent = tmp_path / "does_not_exist.txt"

        with pytest.raises(ValueError, match="Unable to hash"):
            hash_file(nonexistent)

