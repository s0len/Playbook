from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import UTC
from pathlib import Path
from typing import Any

from ..config import IntegrationsSettings, NotificationSettings
from .autoscan import AutoscanTarget
from .discord import DiscordTarget
from .email import EmailTarget
from .plex_scan import PlexScanTarget
from .slack import SlackTarget
from .types import NotificationEvent, NotificationTarget
from .utils import _normalize_mentions_map, resolve_sport_match
from .webhook import GenericWebhookTarget

LOGGER = logging.getLogger(__name__)


class ScanSummary:
    """Aggregates events from a scan for summary notification."""

    def __init__(self) -> None:
        self.events: list[NotificationEvent] = []
        self.by_sport: dict[str, list[NotificationEvent]] = defaultdict(list)

    def add(self, event: NotificationEvent) -> None:
        self.events.append(event)
        self.by_sport[event.sport_id].append(event)

    def clear(self) -> None:
        self.events.clear()
        self.by_sport.clear()

    def __len__(self) -> int:
        return len(self.events)

    def format_discord_embed(self) -> dict[str, Any]:
        """Format summary as a Discord embed."""
        if not self.events:
            return {}

        lines = []
        total_new = 0
        total_replaced = 0
        total_errors = 0

        for sport_id in sorted(self.by_sport.keys()):
            sport_events = self.by_sport[sport_id]
            sport_name = sport_events[0].sport_name if sport_events else sport_id

            new_count = sum(1 for e in sport_events if not e.replaced and e.event_type in ("new", "changed"))
            upgrade_count = sum(
                1 for e in sport_events if e.replaced and e.replace_reason in ("quality_upgrade", "legacy")
            )
            proper_count = sum(1 for e in sport_events if e.replaced and e.replace_reason == "proper_repack")
            fix_count = sum(1 for e in sport_events if e.replaced and e.replace_reason == "mismatch_correction")
            error_count = sum(1 for e in sport_events if e.event_type == "error")

            total_new += new_count
            total_replaced += upgrade_count + proper_count + fix_count
            total_errors += error_count

            parts = []
            if new_count:
                parts.append(f"{new_count} new")
            if upgrade_count:
                parts.append(f"{upgrade_count} upgraded")
            if proper_count:
                parts.append(f"{proper_count} proper/repack")
            if fix_count:
                parts.append(f"{fix_count} fixed")
            if error_count:
                parts.append(f"{error_count} errors")

            if parts:
                lines.append(f"**{sport_name}**: {', '.join(parts)}")

        description = "\n".join(lines) if lines else "No files processed"
        footer_parts = []
        if total_new:
            footer_parts.append(f"{total_new} new")
        if total_replaced:
            footer_parts.append(f"{total_replaced} replaced")
        if total_errors:
            footer_parts.append(f"{total_errors} errors")

        return {
            "title": "Playbook Scan Complete",
            "description": description,
            "color": 0x5865F2,
            "footer": {"text": f"Total: {', '.join(footer_parts)}" if footer_parts else "No activity"},
        }

    def format_text_summary(self) -> str:
        """Format summary as plain text for non-Discord targets (Slack, Email, Webhook)."""
        if not self.events:
            return "Playbook Scan Complete — No files processed"

        lines = ["Playbook Scan Complete", ""]
        for sport_id in sorted(self.by_sport.keys()):
            sport_events = self.by_sport[sport_id]
            sport_name = sport_events[0].sport_name if sport_events else sport_id

            new_count = sum(1 for e in sport_events if not e.replaced and e.event_type in ("new", "changed"))
            replaced_count = sum(1 for e in sport_events if e.replaced)
            error_count = sum(1 for e in sport_events if e.event_type == "error")

            parts = []
            if new_count:
                parts.append(f"{new_count} new")
            if replaced_count:
                parts.append(f"{replaced_count} replaced")
            if error_count:
                parts.append(f"{error_count} errors")
            if parts:
                lines.append(f"  {sport_name}: {', '.join(parts)}")

        return "\n".join(lines)


class NotificationService:
    """Orchestrates notification delivery across multiple targets with throttling support."""

    def __init__(
        self,
        settings: NotificationSettings,
        *,
        cache_dir: Path,
        destination_dir: Path,
        enabled: bool = True,
        integrations: IntegrationsSettings | None = None,
    ) -> None:
        self._settings = settings
        self._enabled = enabled
        self._integrations = integrations or IntegrationsSettings()
        self._targets = self._build_targets(
            settings.targets,
            cache_dir,
            destination_dir,
        )
        self._throttle_map = settings.throttle
        self._daily_sent: dict[tuple[str, str], int] = {}
        self._scan_summary = ScanSummary()
        self._scan_summary_enabled = getattr(settings, "scan_summary", True)

    @property
    def enabled(self) -> bool:
        return self._enabled and any(target.enabled() for target in self._targets)

    def notify(self, event: NotificationEvent) -> None:
        if not self.enabled:
            return
        allowed_types = {"new", "changed", "error"}
        event_type = (event.event_type or "unknown").lower()
        if event_type not in allowed_types:
            LOGGER.debug(
                "Skipping notification for %s because event_type is %s",
                event.sport_id,
                event.event_type,
            )
            return

        # Always collect for scan summary
        self._scan_summary.add(event)

        # Separate infrastructure targets (plex_scan, autoscan) from user-facing ones.
        # Infrastructure targets always fire — they should never be rate-limited.
        _INFRA_TARGETS = {"plex_scan", "autoscan"}

        daily_limit = self._resolve_throttle(event.sport_id)
        day_key = self._notification_day_key(event)
        sent_today = self._daily_sent.get((event.sport_id, day_key), 0)
        throttled = daily_limit > 0 and sent_today >= daily_limit

        if throttled:
            LOGGER.debug(
                "Rate limit reached for %s (%s/%s for %s) — only infrastructure targets will fire",
                event.sport_id,
                sent_today,
                daily_limit,
                day_key,
            )

        successes: list[str] = []
        for target in self._targets:
            if not target.enabled():
                continue
            is_infra = target.name in _INFRA_TARGETS
            if throttled and not is_infra:
                continue
            try:
                target.send(event)
            except Exception as exc:  # pragma: no cover - defensive logging
                LOGGER.warning("Notification target %s failed: %s", target.name, exc)
            else:
                successes.append(target.name)

        # Only count user-facing dispatches toward the daily limit
        user_successes = [s for s in successes if s not in _INFRA_TARGETS]
        if user_successes:
            self._daily_sent[(event.sport_id, day_key)] = sent_today + 1
            LOGGER.debug(
                "Notification dispatched | sport=%s episode=%s event=%s targets=%s",
                event.sport_id,
                event.episode,
                event.event_type,
                ", ".join(successes),
            )
        else:
            LOGGER.debug(
                "Notification skipped or failed for %s (%s) - no targets succeeded",
                event.sport_id,
                event.event_type,
            )

    def send_summary(self) -> None:
        """Send a scan summary notification if there were any events.

        Called at the end of each scan. Only sends if scan_summary is enabled
        and there were actual events during the scan.
        """
        if not self._scan_summary_enabled:
            self._scan_summary.clear()
            return

        if not self._scan_summary:
            LOGGER.debug("No events to summarize")
            return

        LOGGER.info(
            "Sending scan summary notification for %d events across %d sports",
            len(self._scan_summary),
            len(self._scan_summary.by_sport),
        )

        embed = self._scan_summary.format_discord_embed()
        text_summary = self._scan_summary.format_text_summary()

        # Infrastructure targets (plex_scan, autoscan) don't need summaries
        _INFRA_TARGETS = {"plex_scan", "autoscan"}

        successes: list[str] = []
        for target in self._targets:
            if not target.enabled() or target.name in _INFRA_TARGETS:
                continue
            try:
                if hasattr(target, "send_embed"):
                    # Discord — send rich embed
                    target.send_embed(embed)
                else:
                    # Slack, Email, Webhook — send as a simple text event
                    summary_event = NotificationEvent(
                        sport_id="playbook",
                        sport_name="Playbook",
                        show_title="Scan Summary",
                        season="",
                        session="",
                        episode=text_summary,
                        summary=text_summary,
                        destination="",
                        source="",
                        action="summary",
                        link_mode="",
                        event_type="summary",
                    )
                    target.send(summary_event)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Summary notification to %s failed: %s", target.name, exc)
            else:
                successes.append(target.name)

        self._scan_summary.clear()

        if successes:
            LOGGER.debug("Summary notification sent to: %s", ", ".join(successes))

    def _build_targets(
        self,
        targets_raw: list[dict[str, Any]],
        cache_dir: Path,
        destination_dir: Path,
    ) -> list[NotificationTarget]:
        targets: list[NotificationTarget] = []
        configs = list(targets_raw)

        # Track if we've created Plex/Autoscan targets from explicit config
        has_explicit_plex = False
        has_explicit_autoscan = False

        for entry in configs:
            target_type = entry.get("type", "").lower()
            is_enabled = entry.get("enabled", True)
            target: NotificationTarget | None = None

            if target_type == "discord":
                webhook = self._discord_webhook_from(entry)
                if webhook:
                    mentions_override = _normalize_mentions_map(entry.get("mentions"))
                    target = DiscordTarget(
                        webhook,
                        settings=self._settings,
                        mentions=mentions_override if mentions_override else None,
                    )
                else:
                    LOGGER.warning("Skipped Discord target because webhook_url was not provided.")
            elif target_type == "slack":
                url = entry.get("webhook_url") or entry.get("url")
                if url:
                    target = SlackTarget(url, template=entry.get("template"))
                else:
                    LOGGER.warning("Skipped Slack target because webhook_url/url was not provided.")
            elif target_type == "webhook":
                url = entry.get("url")
                if url:
                    target = GenericWebhookTarget(
                        url,
                        method=entry.get("method", "POST"),
                        headers=entry.get("headers"),
                        template=entry.get("template"),
                    )
                else:
                    LOGGER.warning("Skipped webhook target because url was not provided.")
            elif target_type == "autoscan":
                has_explicit_autoscan = True
                # Merge integrations.autoscan settings as defaults
                merged_config = self._merge_autoscan_config(entry)
                url = merged_config.get("url")
                if url:
                    target = AutoscanTarget(merged_config, destination_dir=destination_dir)
                else:
                    LOGGER.warning("Skipped Autoscan target because url was not provided.")
            elif target_type in ("plex_scan", "plex"):
                has_explicit_plex = True
                # Merge integrations.plex settings as defaults
                merged_config = self._merge_plex_scan_config(entry)
                target = PlexScanTarget(merged_config, destination_dir=destination_dir)
                if not target.enabled():
                    LOGGER.warning(
                        "Plex scan target disabled: url/token not found in config or env vars (PLEX_URL, PLEX_TOKEN)"
                    )
                    target = None
            elif target_type == "email":
                target = EmailTarget(entry)
            else:
                LOGGER.warning("Unknown notification target type '%s'", target_type or "<missing>")

            # Set enabled state and add to list
            if target is not None:
                target.set_enabled(is_enabled)
                targets.append(target)

        # Auto-create targets from integrations if not explicitly configured
        targets.extend(
            self._auto_create_integration_targets(
                cache_dir,
                destination_dir,
                has_explicit_plex,
                has_explicit_autoscan,
            )
        )

        return targets

    def _merge_plex_scan_config(self, target_config: dict[str, Any]) -> dict[str, Any]:
        """Merge integrations.plex settings as defaults for plex_scan target."""
        plex = self._integrations.plex
        merged: dict[str, Any] = {}

        if plex.url:
            merged["url"] = plex.url
        if plex.token:
            merged["token"] = plex.token
        if plex.library_id:
            merged["library_id"] = plex.library_id
        if plex.library_name:
            merged["library_name"] = plex.library_name
        if plex.scan_on_activity.rewrite:
            merged["rewrite"] = plex.scan_on_activity.rewrite

        merged.update(target_config)
        return merged

    def _merge_autoscan_config(self, target_config: dict[str, Any]) -> dict[str, Any]:
        """Merge integrations.autoscan settings as defaults for autoscan target."""
        autoscan = self._integrations.autoscan
        merged: dict[str, Any] = {}

        if autoscan.url:
            merged["url"] = autoscan.url
        if autoscan.trigger:
            merged["trigger"] = autoscan.trigger
        if autoscan.username:
            merged["username"] = autoscan.username
        if autoscan.password:
            merged["password"] = autoscan.password
        merged["verify_ssl"] = autoscan.verify_ssl
        merged["timeout"] = autoscan.timeout
        if autoscan.rewrite:
            merged["rewrite"] = autoscan.rewrite

        merged.update(target_config)
        return merged

    def _auto_create_integration_targets(
        self,
        cache_dir: Path,
        destination_dir: Path,
        has_explicit_plex: bool,
        has_explicit_autoscan: bool,
    ) -> list[NotificationTarget]:
        """Auto-create targets from integrations when scan_on_activity/enabled is true."""
        auto_targets: list[NotificationTarget] = []

        plex = self._integrations.plex
        if plex.scan_on_activity.enabled and not has_explicit_plex:
            config = {
                "type": "plex_scan",
                "url": plex.url,
                "token": plex.token,
                "library_id": plex.library_id,
                "library_name": plex.library_name,
                "rewrite": plex.scan_on_activity.rewrite,
            }
            target = PlexScanTarget(config, destination_dir=destination_dir)
            if target.enabled():
                auto_targets.append(target)
                LOGGER.debug("Auto-created Plex scan target from integrations.plex.scan_on_activity")
            else:
                LOGGER.debug("Plex scan_on_activity enabled but target not functional (missing url/token/library)")

        autoscan = self._integrations.autoscan
        if autoscan.enabled and not has_explicit_autoscan:
            if autoscan.url:
                config = {
                    "type": "autoscan",
                    "url": autoscan.url,
                    "trigger": autoscan.trigger,
                    "username": autoscan.username,
                    "password": autoscan.password,
                    "verify_ssl": autoscan.verify_ssl,
                    "timeout": autoscan.timeout,
                    "rewrite": autoscan.rewrite,
                }
                target = AutoscanTarget(config, destination_dir=destination_dir)
                auto_targets.append(target)
                LOGGER.debug("Auto-created Autoscan target from integrations.autoscan")
            else:
                LOGGER.debug("Autoscan enabled but url not configured")

        return auto_targets

    def _discord_webhook_from(self, entry: dict[str, Any]) -> str | None:
        webhook = entry.get("webhook_url")
        if isinstance(webhook, str):
            webhook = webhook.strip()
        if webhook:
            return webhook

        env_name = entry.get("webhook_env") or entry.get("webhook_url_env")
        if env_name is None:
            return None

        value: str | None = None
        env_key = str(env_name).strip()
        if env_key:
            raw_value = os.environ.get(env_key)
            if raw_value:
                value = raw_value.strip()
            else:
                LOGGER.warning(
                    "Discord target env var '%s' is not set; skipping target.",
                    env_key,
                )
        return value

    def _resolve_throttle(self, sport_id: str) -> int:
        if not self._throttle_map:
            return 0

        default = self._throttle_map.get("default")
        default_limit = max(0, int(default)) if default is not None else None

        # Use shared sport matching (exact -> prefix -> wildcard)
        match = resolve_sport_match(sport_id, {k: v for k, v in self._throttle_map.items() if k != "default"})
        if match is not None:
            sport_limit = max(0, int(match))
            if default_limit is None:
                return sport_limit
            return min(sport_limit, default_limit)

        return default_limit if default_limit is not None else 0

    @staticmethod
    def _notification_day_key(event: NotificationEvent) -> str:
        timestamp = event.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return timestamp.astimezone(UTC).date().isoformat()
