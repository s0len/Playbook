"""
Notification system for Playbook.

This package provides notification delivery functionality across multiple targets
(Discord, Slack, Email, Webhooks, Autoscan) with support for throttling and templating.

Public API:
    - NotificationEvent: Dataclass representing a notification event
    - NotificationService: Main service orchestrating notification delivery
    - NotificationTarget: Base class for notification targets
    - DiscordTarget: Discord webhook notification target
    - SlackTarget: Slack webhook notification target
    - GenericWebhookTarget: Generic HTTP webhook target
    - AutoscanTarget: Autoscan webhook notification target
    - EmailTarget: Email notification target
"""

from __future__ import annotations

# Notification targets
from .autoscan import AutoscanTarget
from .discord import DiscordTarget
from .email import EmailTarget

# Main service
from .service import NotificationService
from .slack import SlackTarget

# Core types and base classes
from .types import NotificationEvent, NotificationTarget
from .webhook import GenericWebhookTarget

__all__ = [
    # Core types
    "NotificationEvent",
    "NotificationTarget",
    # Targets
    "DiscordTarget",
    "SlackTarget",
    "GenericWebhookTarget",
    "AutoscanTarget",
    "EmailTarget",
    # Service
    "NotificationService",
]
