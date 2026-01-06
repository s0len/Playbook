from __future__ import annotations

import pytest
import requests

from playbook.cache import MetadataHttpCache
from playbook.config import MetadataConfig, Settings
from playbook.metadata import MetadataFetchStatistics, MetadataNormalizer, fetch_metadata


class DummyResponse:
    status_code = 200

    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        source_dir=tmp_path / "source",
        destination_dir=tmp_path / "dest",
        cache_dir=tmp_path / "cache",
    )


def test_fetch_metadata_uses_cache(monkeypatch, settings) -> None:
    payload = """
    metadata:
      demo:
        title: Demo Series
    """

    requests_called: list[str] = []

    def fake_get(url, headers=None, timeout=None):
        requests_called.append(url)
        return DummyResponse(payload)

    monkeypatch.setattr("playbook.metadata.requests.get", fake_get)

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml")

    first = fetch_metadata(metadata_cfg, settings)
    assert first["metadata"]["demo"]["title"] == "Demo Series"
    assert requests_called == ["https://example.com/demo.yaml"]

    second = fetch_metadata(metadata_cfg, settings)
    assert second == first
    assert requests_called == ["https://example.com/demo.yaml"]


def test_fetch_metadata_respects_conditional_requests(monkeypatch, settings) -> None:
    payload = """
    metadata:
      demo:
        title: Demo Series
    """

    http_cache = MetadataHttpCache(settings.cache_dir)
    stats = MetadataFetchStatistics()
    call_count = {"value": 0}

    def fake_get(url, headers=None, timeout=None):
        call_count["value"] += 1
        if call_count["value"] == 1:
            response = DummyResponse(payload)
            response.status_code = 200
            response.headers = {"ETag": '"abc"', "Last-Modified": "Wed, 21 Oct 2015 07:28:00 GMT"}
            return response
        assert headers is not None
        assert headers.get("If-None-Match") == '"abc"'
        response = DummyResponse("")
        response.status_code = 304
        response.headers = {"ETag": '"abc"'}
        return response

    monkeypatch.setattr("playbook.metadata.requests.get", fake_get)

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", ttl_hours=0)
    first = fetch_metadata(metadata_cfg, settings, http_cache=http_cache, stats=stats)
    second = fetch_metadata(metadata_cfg, settings, http_cache=http_cache, stats=stats)

    assert first["metadata"]["demo"]["title"] == "Demo Series"
    assert second == first
    snapshot = stats.snapshot()
    assert snapshot["cache_hits"] == 0
    assert snapshot["cache_misses"] == 2
    assert snapshot["network_requests"] == 2
    assert snapshot["not_modified"] == 1
    assert snapshot["stale_used"] == 0
    assert snapshot["failures"] == 0


def test_fetch_metadata_uses_stale_on_failure(monkeypatch, settings) -> None:
    payload = """
    metadata:
      demo:
        title: Demo Series
    """

    http_cache = MetadataHttpCache(settings.cache_dir)
    stats = MetadataFetchStatistics()
    call_count = {"value": 0}

    def flaky_get(url, headers=None, timeout=None):
        call_count["value"] += 1
        if call_count["value"] == 1:
            response = DummyResponse(payload)
            response.status_code = 200
            response.headers = {}
            return response
        raise requests.RequestException("boom")

    monkeypatch.setattr("playbook.metadata.requests.get", flaky_get)

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", ttl_hours=0)
    first = fetch_metadata(metadata_cfg, settings, http_cache=http_cache, stats=stats)
    second = fetch_metadata(metadata_cfg, settings, http_cache=http_cache, stats=stats)

    assert first == second
    assert call_count["value"] == 4
    snapshot = stats.snapshot()
    assert snapshot["stale_used"] == 1
    assert snapshot["failures"] == 0


def test_fetch_metadata_parses_json_content(monkeypatch, settings) -> None:
    # JSON content should be parsed directly without YAML parser
    json_payload = """
    {
        "metadata": {
            "demo": {
                "title": "Demo Series from JSON"
            }
        }
    }
    """

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(json_payload)

    monkeypatch.setattr("playbook.metadata.requests.get", fake_get)

    metadata_cfg = MetadataConfig(url="https://example.com/demo.json")
    result = fetch_metadata(metadata_cfg, settings)
    assert result["metadata"]["demo"]["title"] == "Demo Series from JSON"


def test_fetch_metadata_falls_back_to_yaml(monkeypatch, settings) -> None:
    # YAML content with features not valid in JSON should still parse
    yaml_payload = """
    metadata:
      demo:
        title: Demo Series from YAML
        description: >
          This is a multi-line
          YAML string that uses
          folded scalar syntax
    """

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(yaml_payload)

    monkeypatch.setattr("playbook.metadata.requests.get", fake_get)

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml")
    result = fetch_metadata(metadata_cfg, settings)
    assert result["metadata"]["demo"]["title"] == "Demo Series from YAML"
    assert "This is a multi-line" in result["metadata"]["demo"]["description"]


def test_fetch_metadata_handles_yaml_specific_features(monkeypatch, settings) -> None:
    # YAML with anchors, aliases, and other YAML-specific features
    yaml_payload = """
    metadata:
      demo:
        title: Demo Series
        common_config: &defaults
          enabled: true
          priority: high
        feature_a:
          <<: *defaults
          name: Feature A
        feature_b:
          <<: *defaults
          name: Feature B
    """

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(yaml_payload)

    monkeypatch.setattr("playbook.metadata.requests.get", fake_get)

    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml")
    result = fetch_metadata(metadata_cfg, settings)
    assert result["metadata"]["demo"]["title"] == "Demo Series"
    assert result["metadata"]["demo"]["feature_a"]["enabled"] is True
    assert result["metadata"]["demo"]["feature_a"]["name"] == "Feature A"
    assert result["metadata"]["demo"]["feature_b"]["priority"] == "high"


def test_metadata_normalizer_loads_show_with_rounds() -> None:
    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="f1")
    normalizer = MetadataNormalizer(metadata_cfg)

    raw = {
        "metadata": {
            "f1": {
                "title": "Formula 1",
                "summary": "Season overview",
                "seasons": {
                    "01": {
                        "title": "01 Bahrain Grand Prix",
                        "sort_title": "01_bahrain",
                        "episodes": [
                            {
                                "title": "Free Practice 1",
                                "episode_number": 1,
                                "originally_available": "2024-03-01",
                                "aliases": ["FP1"],
                            },
                            {
                                "title": "Qualifying",
                                "aliases": ["Quali"],
                            },
                        ],
                    }
                },
            }
        }
    }

    show = normalizer.load_show(raw)

    assert show.key == "f1"
    assert show.title == "Formula 1"
    assert len(show.seasons) == 1

    season = show.seasons[0]
    assert season.round_number == 1
    assert season.display_number == 1

    episode = season.episodes[0]
    assert episode.title == "Free Practice 1"
    assert episode.display_number == 1
    assert episode.aliases == ["FP1"]
    assert episode.originally_available.isoformat() == "2024-03-01"


def test_metadata_normalizer_keeps_sequential_round_numbers_for_ufc() -> None:
    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="ufc_2025")
    normalizer = MetadataNormalizer(metadata_cfg)

    raw = {
        "metadata": {
            "ufc_2025": {
                "title": "UFC 2025",
                "seasons": {
                    "1": {
                        "title": "UFC Fight Night 249 Dern vs Ribas 2",
                        "sort_title": "001_UFC Fight Night 249 Dern vs Ribas 2",
                        "episodes": [{"title": "Main Card"}],
                    },
                    "2": {
                        "title": "UFC 311 Makhachev vs Moicano",
                        "sort_title": "002_UFC 311 Makhachev vs Moicano",
                        "episodes": [{"title": "Prelims"}],
                    },
                },
            }
        }
    }

    show = normalizer.load_show(raw)

    assert len(show.seasons) == 2
    first = show.seasons[0]
    second = show.seasons[1]

    assert first.round_number == 1
    assert first.display_number == 1
    assert second.round_number == 2
    assert second.display_number == 2


def test_metadata_normalizer_falls_back_to_index_when_no_numeric_hint() -> None:
    metadata_cfg = MetadataConfig(url="https://example.com/demo.yaml", show_key="demo")
    normalizer = MetadataNormalizer(metadata_cfg)

    raw = {
        "metadata": {
            "demo": {
                "title": "Demo Show",
                "seasons": {
                    "alpha": {
                        "title": "Showcase Alpha",
                        "episodes": [{"title": "Session"}],
                    },
                    "beta": {
                        "title": "Showcase Beta",
                        "episodes": [{"title": "Session"}],
                    },
                },
            }
        }
    }

    show = normalizer.load_show(raw)

    assert show.seasons[0].round_number == 1
    assert show.seasons[0].display_number == 1
    assert show.seasons[1].round_number == 2
    assert show.seasons[1].display_number == 2
