"""
Theme configuration for the Playbook GUI.

Provides color palette definitions and theme preference management
with dark mode support.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nicegui import app, ui

ThemeMode = Literal["light", "dark", "auto"]


@dataclass(frozen=True)
class ColorPalette:
    """Color palette for a theme mode."""

    # Background colors
    bg_primary: str
    bg_card: str
    bg_input: str

    # Text colors
    text_primary: str
    text_secondary: str
    text_muted: str

    # Accent colors
    accent: str
    accent_hover: str

    # Status colors
    success: str
    warning: str
    error: str
    info: str

    # Border colors
    border: str
    border_light: str


# Light mode palette (slate-based)
LIGHT_PALETTE = ColorPalette(
    bg_primary="#f8fafc",  # slate-50
    bg_card="#ffffff",
    bg_input="#f1f5f9",  # slate-100
    text_primary="#0f172a",  # slate-900
    text_secondary="#334155",  # slate-700
    text_muted="#64748b",  # slate-500
    accent="#3b82f6",  # blue-500
    accent_hover="#2563eb",  # blue-600
    success="#22c55e",  # green-500
    warning="#f59e0b",  # amber-500
    error="#ef4444",  # red-500
    info="#06b6d4",  # cyan-500
    border="#e2e8f0",  # slate-200
    border_light="#f1f5f9",  # slate-100
)

# Dark mode palette (slate-based)
DARK_PALETTE = ColorPalette(
    bg_primary="#0f172a",  # slate-900
    bg_card="rgba(30, 41, 59, 0.8)",  # slate-800 with transparency for glassmorphism
    bg_input="#1e293b",  # slate-800
    text_primary="#f8fafc",  # slate-50
    text_secondary="#cbd5e1",  # slate-300
    text_muted="#94a3b8",  # slate-400
    accent="#60a5fa",  # blue-400
    accent_hover="#3b82f6",  # blue-500
    success="#4ade80",  # green-400
    warning="#fbbf24",  # amber-400
    error="#f87171",  # red-400
    info="#22d3ee",  # cyan-400
    border="#334155",  # slate-700
    border_light="#1e293b",  # slate-800
)


def get_palette(dark: bool = False) -> ColorPalette:
    """Get the color palette for the current theme mode.

    Args:
        dark: Whether to return dark mode palette

    Returns:
        The appropriate ColorPalette
    """
    return DARK_PALETTE if dark else LIGHT_PALETTE


def get_theme_preference() -> ThemeMode:
    """Get the user's stored theme preference.

    Returns:
        The stored theme mode, or 'auto' if not set
    """
    try:
        return app.storage.user.get("theme", "auto")
    except Exception:
        return "auto"


def set_theme_preference(mode: ThemeMode) -> None:
    """Store the user's theme preference.

    Args:
        mode: The theme mode to store
    """
    try:
        app.storage.user["theme"] = mode
    except Exception:
        pass


def is_dark_mode() -> bool:
    """Check if dark mode is currently active.

    Returns:
        True if dark mode is active
    """
    preference = get_theme_preference()
    if preference == "auto":
        # Default to light mode for auto
        return False
    return preference == "dark"


def toggle_dark_mode() -> bool:
    """Toggle between light and dark mode.

    Returns:
        True if now in dark mode, False if in light mode
    """
    current = get_theme_preference()
    if current == "dark":
        new_mode: ThemeMode = "light"
    else:
        new_mode = "dark"

    set_theme_preference(new_mode)
    return new_mode == "dark"


def apply_theme(dark_mode_element: ui.dark_mode | None = None) -> None:
    """Apply the stored theme preference.

    Args:
        dark_mode_element: Optional dark_mode element to control
    """
    is_dark = is_dark_mode()
    if dark_mode_element is not None:
        if is_dark:
            dark_mode_element.enable()
        else:
            dark_mode_element.disable()


# Tailwind-compatible color classes
class ThemeClasses:
    """Tailwind CSS class mappings for theming."""

    # Background classes
    BG_PRIMARY = "bg-slate-50 dark:bg-slate-900"
    BG_CARD = "bg-white dark:bg-slate-800/80"
    BG_INPUT = "bg-slate-100 dark:bg-slate-800"
    BG_HEADER = "bg-slate-900"

    # Text classes
    TEXT_PRIMARY = "text-slate-900 dark:text-slate-50"
    TEXT_SECONDARY = "text-slate-700 dark:text-slate-300"
    TEXT_MUTED = "text-slate-500 dark:text-slate-400"

    # Border classes
    BORDER = "border-slate-200 dark:border-slate-700"
    BORDER_LIGHT = "border-slate-100 dark:border-slate-800"

    # Card styling with glassmorphism
    GLASS_CARD = "glass-card"

    # Status colors
    STATUS_SUCCESS = "text-green-600 dark:text-green-400"
    STATUS_WARNING = "text-amber-600 dark:text-amber-400"
    STATUS_ERROR = "text-red-600 dark:text-red-400"
    STATUS_INFO = "text-cyan-600 dark:text-cyan-400"

    # Badge colors
    BADGE_SUCCESS = "bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300"
    BADGE_WARNING = "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300"
    BADGE_ERROR = "bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300"
    BADGE_INFO = "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/50 dark:text-cyan-300"
    BADGE_NEUTRAL = "bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300"

    # Link colors
    LINK = "text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"


# Export theme classes for easy import
TC = ThemeClasses
