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
    accent="#34d399",  # emerald-400
    accent_hover="#2cb783",
    success="#22c55e",  # green-500
    warning="#f59e0b",  # amber-500
    error="#ef4444",  # red-500
    info="#34d399",
    border="#e2e8f0",  # slate-200
    border_light="#f1f5f9",  # slate-100
)

# Dark mode palette (near-black with emerald accents)
DARK_PALETTE = ColorPalette(
    bg_primary="#0b0b0f",  # Near-black
    bg_card="#12121a",  # Flat dark card
    bg_input="#1a1a24",  # Slightly lighter dark
    text_primary="#f0f0f8",  # Off-white
    text_secondary="#a0a0b8",  # Muted lavender
    text_muted="#60607a",  # Dimmed
    accent="#34d399",
    accent_hover="#2cb783",
    success="#4ade80",  # green-400
    warning="#fbbf24",  # amber-400
    error="#f87171",  # red-400
    info="#34d399",
    border="#1e1e2e",  # Subtle border
    border_light="#16161e",  # Very subtle border
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
        The stored theme mode, or 'dark' if not set
    """
    try:
        return app.storage.user.get("theme", "dark")
    except Exception:
        return "dark"


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
        # Default to dark mode for auto
        return True
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

    # Background classes (dark mode uses near-black)
    BG_PRIMARY = "bg-slate-50 dark:bg-[#0b0b0f]"
    BG_CARD = "bg-white dark:bg-[#12121a]"
    BG_INPUT = "bg-slate-100 dark:bg-[#1a1a24]"
    BG_HEADER = "bg-[#0e0e16]"

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
    STATUS_SUCCESS = "app-text-success"
    STATUS_WARNING = "app-text-warning"
    STATUS_ERROR = "app-text-danger"
    STATUS_INFO = "app-text-accent"

    # Badge colors
    BADGE_SUCCESS = "app-badge app-badge-success"
    BADGE_WARNING = "app-badge app-badge-warning"
    BADGE_ERROR = "app-badge app-badge-danger"
    BADGE_INFO = "app-badge app-badge-muted"
    BADGE_NEUTRAL = "app-badge app-badge-muted"

    # Link colors
    LINK = "app-link"


# Export theme classes for easy import
TC = ThemeClasses
