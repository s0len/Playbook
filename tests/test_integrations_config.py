"""Tests for the new integrations config structure."""

from __future__ import annotations

import logging

from playbook.config import (
    AutoscanIntegration,
    IntegrationsSettings,
    PlexIntegration,
    PlexMetadataSyncSettings,
    PlexScanOnActivitySettings,
    _build_autoscan_integration,
    _build_integrations,
    _build_plex_integration,
    load_config,
)


class TestIntegrationsDataclasses:
    """Test the new integrations dataclass structure."""

    def test_plex_scan_on_activity_defaults(self):
        settings = PlexScanOnActivitySettings()
        assert settings.enabled is False
        assert settings.rewrite == []

    def test_plex_metadata_sync_defaults(self):
        settings = PlexMetadataSyncSettings()
        assert settings.enabled is False
        assert settings.timeout == 15.0
        assert settings.force is False
        assert settings.dry_run is False
        assert settings.sports == []
        assert settings.scan_wait == 5.0

    def test_plex_integration_defaults(self):
        plex = PlexIntegration()
        assert plex.url is None
        assert plex.token is None
        assert plex.library_id is None
        assert plex.library_name is None
        assert isinstance(plex.metadata_sync, PlexMetadataSyncSettings)
        assert isinstance(plex.scan_on_activity, PlexScanOnActivitySettings)

    def test_autoscan_integration_defaults(self):
        autoscan = AutoscanIntegration()
        assert autoscan.enabled is False
        assert autoscan.url is None
        assert autoscan.trigger == "manual"
        assert autoscan.username is None
        assert autoscan.password is None
        assert autoscan.verify_ssl is True
        assert autoscan.timeout == 10.0
        assert autoscan.rewrite == []

    def test_integrations_settings_defaults(self):
        integrations = IntegrationsSettings()
        assert isinstance(integrations.plex, PlexIntegration)
        assert isinstance(integrations.autoscan, AutoscanIntegration)


class TestBuildPlexIntegration:
    """Test _build_plex_integration parsing."""

    def test_empty_data_returns_defaults(self):
        plex = _build_plex_integration({})
        assert plex.url is None
        assert plex.token is None

    def test_parses_connection_settings(self):
        data = {
            "url": "http://plex:32400",
            "token": "my-token",
            "library_id": "15",
            "library_name": "Sports",
        }
        plex = _build_plex_integration(data)
        assert plex.url == "http://plex:32400"
        assert plex.token == "my-token"
        assert plex.library_id == "15"
        assert plex.library_name == "Sports"

    def test_parses_metadata_sync_settings(self):
        data = {
            "url": "http://plex:32400",
            "token": "token",
            "metadata_sync": {
                "enabled": True,
                "timeout": 30,
                "force": True,
                "sports": ["formula1", "motogp"],
            },
        }
        plex = _build_plex_integration(data)
        assert plex.metadata_sync.enabled is True
        assert plex.metadata_sync.timeout == 30
        assert plex.metadata_sync.force is True
        assert plex.metadata_sync.sports == ["formula1", "motogp"]

    def test_parses_scan_on_activity_settings(self):
        data = {
            "url": "http://plex:32400",
            "token": "token",
            "scan_on_activity": {
                "enabled": True,
                "rewrite": [
                    {"from": "/data/dest", "to": "/mnt/plex"},
                ],
            },
        }
        plex = _build_plex_integration(data)
        assert plex.scan_on_activity.enabled is True
        assert plex.scan_on_activity.rewrite == [{"from": "/data/dest", "to": "/mnt/plex"}]

    def test_legacy_plex_sync_converted_to_new_structure(self, caplog):
        """Test backwards compatibility: plex_metadata_sync is converted."""
        legacy_data = {
            "enabled": True,
            "url": "http://legacy:32400",
            "token": "legacy-token",
            "library_id": "10",
            "timeout": 20,
            "force": True,
        }
        with caplog.at_level(logging.WARNING):
            plex = _build_plex_integration({}, legacy_plex_sync=legacy_data)

        # Connection settings migrated
        assert plex.url == "http://legacy:32400"
        assert plex.token == "legacy-token"
        assert plex.library_id == "10"

        # Metadata sync settings migrated
        assert plex.metadata_sync.enabled is True
        assert plex.metadata_sync.timeout == 20
        assert plex.metadata_sync.force is True

        # Deprecation warning logged
        assert "DEPRECATED" in caplog.text

    def test_new_structure_preferred_over_legacy(self, caplog):
        """Test that new integrations.plex is used if present."""
        legacy_data = {
            "url": "http://legacy:32400",
            "token": "legacy-token",
        }
        new_data = {
            "url": "http://new:32400",
            "token": "new-token",
        }
        with caplog.at_level(logging.WARNING):
            plex = _build_plex_integration(new_data, legacy_plex_sync=legacy_data)

        # New structure used, legacy ignored
        assert plex.url == "http://new:32400"
        assert plex.token == "new-token"
        # No deprecation warning because new structure is used
        assert "DEPRECATED" not in caplog.text


class TestBuildAutoscanIntegration:
    """Test _build_autoscan_integration parsing."""

    def test_empty_data_returns_defaults(self):
        autoscan = _build_autoscan_integration({})
        assert autoscan.enabled is False
        assert autoscan.url is None

    def test_parses_all_settings(self):
        data = {
            "enabled": True,
            "url": "http://autoscan:3030",
            "trigger": "sonarr",
            "username": "admin",
            "password": "secret",
            "verify_ssl": False,
            "timeout": 15,
            "rewrite": [{"from": "/data", "to": "/mnt"}],
        }
        autoscan = _build_autoscan_integration(data)
        assert autoscan.enabled is True
        assert autoscan.url == "http://autoscan:3030"
        assert autoscan.trigger == "sonarr"
        assert autoscan.username == "admin"
        assert autoscan.password == "secret"
        assert autoscan.verify_ssl is False
        assert autoscan.timeout == 15
        assert autoscan.rewrite == [{"from": "/data", "to": "/mnt"}]


class TestBuildIntegrations:
    """Test _build_integrations parsing."""

    def test_empty_data_returns_defaults(self):
        integrations = _build_integrations({})
        assert integrations.plex.url is None
        assert integrations.autoscan.url is None

    def test_parses_both_plex_and_autoscan(self):
        data = {
            "plex": {
                "url": "http://plex:32400",
                "token": "token",
            },
            "autoscan": {
                "enabled": True,
                "url": "http://autoscan:3030",
            },
        }
        integrations = _build_integrations(data)
        assert integrations.plex.url == "http://plex:32400"
        assert integrations.autoscan.url == "http://autoscan:3030"
        assert integrations.autoscan.enabled is True


class TestLoadConfigIntegrations:
    """Test that load_config properly parses the integrations section."""

    def test_loads_new_integrations_structure(self, tmp_path):
        config_content = """
settings:
  source_dir: /data/source
  destination_dir: /data/dest
  cache_dir: /data/cache
  integrations:
    plex:
      url: http://plex:32400
      token: my-token
      library_name: Sports
      metadata_sync:
        enabled: true
        timeout: 30
      scan_on_activity:
        enabled: true
        rewrite:
          - from: /data/dest
            to: /mnt/plex
    autoscan:
      enabled: true
      url: http://autoscan:3030
sports: []
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        # Verify integrations parsed correctly
        plex = config.settings.integrations.plex
        assert plex.url == "http://plex:32400"
        assert plex.token == "my-token"
        assert plex.library_name == "Sports"
        assert plex.metadata_sync.enabled is True
        assert plex.metadata_sync.timeout == 30
        assert plex.scan_on_activity.enabled is True
        assert plex.scan_on_activity.rewrite == [{"from": "/data/dest", "to": "/mnt/plex"}]

        autoscan = config.settings.integrations.autoscan
        assert autoscan.enabled is True
        assert autoscan.url == "http://autoscan:3030"

    def test_legacy_plex_metadata_sync_still_works(self, tmp_path, caplog):
        """Test backwards compatibility with legacy plex_metadata_sync."""
        config_content = """
settings:
  source_dir: /data/source
  destination_dir: /data/dest
  cache_dir: /data/cache
  plex_metadata_sync:
    enabled: true
    url: http://legacy-plex:32400
    token: legacy-token
    library_id: "15"
    timeout: 20
sports: []
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with caplog.at_level(logging.WARNING):
            config = load_config(config_file)

        # Legacy config should be migrated to integrations
        plex = config.settings.integrations.plex
        assert plex.url == "http://legacy-plex:32400"
        assert plex.token == "legacy-token"
        assert plex.library_id == "15"
        assert plex.metadata_sync.enabled is True
        assert plex.metadata_sync.timeout == 20

        # Legacy plex_sync should also be populated for backwards compat
        assert config.settings.plex_sync.enabled is True
        assert config.settings.plex_sync.url == "http://legacy-plex:32400"

    def test_new_integrations_preferred_over_legacy(self, tmp_path):
        """Test that new integrations.plex takes precedence over legacy."""
        config_content = """
settings:
  source_dir: /data/source
  destination_dir: /data/dest
  cache_dir: /data/cache
  plex_metadata_sync:
    enabled: true
    url: http://legacy:32400
    token: legacy-token
  integrations:
    plex:
      url: http://new:32400
      token: new-token
sports: []
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        # New integrations should be used
        plex = config.settings.integrations.plex
        assert plex.url == "http://new:32400"
        assert plex.token == "new-token"


class TestNotificationServiceIntegration:
    """Test that NotificationService uses integrations for Plex/Autoscan targets."""

    def test_plex_scan_target_inherits_from_integrations(self, tmp_path):
        """Test that plex_scan notification target inherits from integrations.plex."""
        from playbook.config import IntegrationsSettings, NotificationSettings
        from playbook.notifications.service import NotificationService

        integrations = IntegrationsSettings(
            plex=PlexIntegration(
                url="http://plex:32400",
                token="my-token",
                library_id="15",
                scan_on_activity=PlexScanOnActivitySettings(rewrite=[{"from": "/data", "to": "/mnt"}]),
            ),
        )

        # Notification target without url/token (should inherit from integrations)
        notifications = NotificationSettings(
            targets=[
                {"type": "plex_scan"},  # No url/token specified
            ]
        )

        service = NotificationService(
            notifications,
            cache_dir=tmp_path,
            destination_dir=tmp_path,
            integrations=integrations,
        )

        # Target should have inherited values from integrations
        assert len(service._targets) == 1
        target = service._targets[0]
        assert target._url == "http://plex:32400"
        assert target._token == "my-token"
        assert target._library_id == "15"

    def test_plex_scan_target_overrides_integrations(self, tmp_path):
        """Test that plex_scan target-specific values override integrations."""
        from playbook.config import IntegrationsSettings, NotificationSettings
        from playbook.notifications.service import NotificationService

        integrations = IntegrationsSettings(
            plex=PlexIntegration(
                url="http://integration-plex:32400",
                token="integration-token",
                library_id="10",
            ),
        )

        # Notification target with explicit values (should override)
        notifications = NotificationSettings(
            targets=[
                {
                    "type": "plex_scan",
                    "url": "http://override-plex:32400",
                    "token": "override-token",
                    "library_id": "99",
                },
            ]
        )

        service = NotificationService(
            notifications,
            cache_dir=tmp_path,
            destination_dir=tmp_path,
            integrations=integrations,
        )

        # Target should use overridden values
        assert len(service._targets) == 1
        target = service._targets[0]
        assert target._url == "http://override-plex:32400"
        assert target._token == "override-token"
        assert target._library_id == "99"

    def test_autoscan_target_inherits_from_integrations(self, tmp_path):
        """Test that autoscan notification target inherits from integrations.autoscan."""
        from playbook.config import IntegrationsSettings, NotificationSettings
        from playbook.notifications.service import NotificationService

        integrations = IntegrationsSettings(
            autoscan=AutoscanIntegration(
                url="http://autoscan:3030",
                trigger="manual",
                username="admin",
                password="secret",
            ),
        )

        # Notification target without values (should inherit from integrations)
        notifications = NotificationSettings(
            targets=[
                {"type": "autoscan"},  # No url specified
            ]
        )

        service = NotificationService(
            notifications,
            cache_dir=tmp_path,
            destination_dir=tmp_path,
            integrations=integrations,
        )

        # Target should have inherited values from integrations
        assert len(service._targets) == 1
        target = service._targets[0]
        assert "autoscan:3030" in target._endpoint

    def test_auto_creates_plex_target_from_scan_on_activity(self, tmp_path):
        """Test that enabling scan_on_activity auto-creates a Plex scan target."""
        from playbook.config import IntegrationsSettings, NotificationSettings
        from playbook.notifications.service import NotificationService

        integrations = IntegrationsSettings(
            plex=PlexIntegration(
                url="http://plex:32400",
                token="my-token",
                library_id="15",
                scan_on_activity=PlexScanOnActivitySettings(enabled=True),
            ),
        )

        # No explicit plex_scan target in notifications
        notifications = NotificationSettings(targets=[])

        service = NotificationService(
            notifications,
            cache_dir=tmp_path,
            destination_dir=tmp_path,
            integrations=integrations,
        )

        # Target should be auto-created from integrations
        assert len(service._targets) == 1
        target = service._targets[0]
        assert target.name == "plex_scan"

    def test_auto_creates_autoscan_target_when_enabled(self, tmp_path):
        """Test that enabling autoscan auto-creates an Autoscan target."""
        from playbook.config import IntegrationsSettings, NotificationSettings
        from playbook.notifications.service import NotificationService

        integrations = IntegrationsSettings(
            autoscan=AutoscanIntegration(
                enabled=True,
                url="http://autoscan:3030",
            ),
        )

        # No explicit autoscan target in notifications
        notifications = NotificationSettings(targets=[])

        service = NotificationService(
            notifications,
            cache_dir=tmp_path,
            destination_dir=tmp_path,
            integrations=integrations,
        )

        # Target should be auto-created from integrations
        assert len(service._targets) == 1
        target = service._targets[0]
        assert target.name == "autoscan"

    def test_no_duplicate_when_explicit_and_auto_enabled(self, tmp_path):
        """Test that explicit target prevents auto-creation."""
        from playbook.config import IntegrationsSettings, NotificationSettings
        from playbook.notifications.service import NotificationService

        integrations = IntegrationsSettings(
            plex=PlexIntegration(
                url="http://plex:32400",
                token="my-token",
                library_id="15",
                scan_on_activity=PlexScanOnActivitySettings(enabled=True),
            ),
        )

        # Explicit plex_scan target in notifications
        notifications = NotificationSettings(
            targets=[{"type": "plex_scan", "url": "http://plex:32400", "token": "my-token", "library_id": "15"}]
        )

        service = NotificationService(
            notifications,
            cache_dir=tmp_path,
            destination_dir=tmp_path,
            integrations=integrations,
        )

        # Should only have 1 target (explicit), not 2
        assert len(service._targets) == 1
