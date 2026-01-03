from __future__ import annotations

import os

import pytest

from playbook.utils import (
    env_bool,
    env_list,
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

