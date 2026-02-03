"""
Settings form components for the Playbook GUI.

Provides reusable form components for the Settings page including:
- SettingsCard: Collapsible section wrapper
- SettingsToggle: Boolean toggle with label
- SettingsInput: Text/number input with validation
- SettingsSelect: Dropdown selector
- KeyValueEditor: Dynamic key-value pair editor
- ListEditor: Dynamic list editor with add/remove
- NotificationTarget: Polymorphic notification target form
"""

from .key_value_editor import key_value_editor
from .list_editor import list_editor
from .notification_target import notification_target_editor
from .settings_card import settings_card
from .settings_input import settings_input, settings_path_input
from .settings_select import settings_select
from .settings_toggle import settings_toggle

__all__ = [
    "settings_card",
    "settings_toggle",
    "settings_input",
    "settings_path_input",
    "settings_select",
    "key_value_editor",
    "list_editor",
    "notification_target_editor",
]
