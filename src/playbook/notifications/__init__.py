"""
Notification system for Playbook.

This package provides notification delivery functionality across multiple targets
(Discord, Slack, Email, Webhooks, Autoscan) with support for batching and templating.

Public API:
    - NotificationEvent: Dataclass representing a notification event
    - NotificationService: Main service orchestrating notification delivery
    - NotificationTarget: Base class for notification targets
    - BatchRequest: Dataclass for batch notification requests
    - NotificationBatcher: Manages persisted per-sport batches
    - DiscordTarget: Discord webhook notification target
    - SlackTarget: Slack webhook notification target
    - GenericWebhookTarget: Generic HTTP webhook target
    - AutoscanTarget: Autoscan webhook notification target
    - EmailTarget: Email notification target
"""

from __future__ import annotations

# Core types and base classes
from .types import BatchRequest, NotificationEvent, NotificationTarget

# Notification targets
from .autoscan import AutoscanTarget
from .batcher import NotificationBatcher
from .discord import DiscordTarget
from .email import EmailTarget
from .slack import SlackTarget
from .webhook import GenericWebhookTarget

# Main service
from .service import NotificationService

__all__ = [
    # Core types
    "BatchRequest",
    "NotificationEvent",
    "NotificationTarget",
    # Batcher
    "NotificationBatcher",
    # Targets
    "DiscordTarget",
    "SlackTarget",
    "GenericWebhookTarget",
    "AutoscanTarget",
    "EmailTarget",
    # Service
    "NotificationService",
]