"""
Centralized theme definitions for the Playbook GUI.

Each theme provides Quasar brand colors (passed to ui.colors()) and
CSS extensions for things Quasar doesn't cover natively.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------
# Keys prefixed with q_ are passed to ui.colors() (Quasar brand colors).
# Keys prefixed with css_ are synced to --pb-* CSS custom properties via JS.
# Keys prefixed with meta_ are UI metadata (swatches, labels).
# ---------------------------------------------------------------------------

THEMES: dict[str, dict[str, Any]] = {
    "swizzin": {
        # --- Quasar brand colors (ui.colors() parameters) ---
        "primary": "#34d399",  # Emerald green — buttons, active nav, toggles, links
        "secondary": "#2dd4bf",  # Teal
        "accent": "#34d399",
        "dark": "#111114",  # Sidebar / card surface
        "dark_page": "#0a0a0c",  # Page background
        "positive": "#4ade80",  # Success states
        "negative": "#f87171",  # Error states
        "info": "#38bdf8",  # Info states
        "warning": "#fbbf24",  # Warning states
        # --- CSS extensions (--pb-* properties) ---
        "primary_soft": "rgba(52, 211, 153, 0.10)",
        "text_primary": "#e8e8ec",
        "text_secondary": "#9898a4",
        "text_muted": "#5c5c68",
        "border_color": "rgba(255, 255, 255, 0.07)",
        "surface": "#18181b",  # Slightly lighter than dark, for card interiors
        # --- UI metadata ---
        "label": "Swizzin",
        "description": "Crisp slate surfaces with a green action accent.",
        "swatches": ("#34d399", "#111114", "#e8e8ec"),
    },
    "catppuccin": {
        # --- Quasar brand colors ---
        "primary": "#cba6f7",  # Mauve
        "secondary": "#f5c2e7",  # Pink
        "accent": "#cba6f7",
        "dark": "#1e1e2e",  # Catppuccin base
        "dark_page": "#181825",  # Catppuccin mantle
        "positive": "#a6e3a1",  # Catppuccin green
        "negative": "#f38ba8",  # Catppuccin red
        "info": "#89b4fa",  # Catppuccin blue
        "warning": "#f9e2af",  # Catppuccin yellow
        # --- CSS extensions ---
        "primary_soft": "rgba(203, 166, 247, 0.12)",
        "text_primary": "#cdd6f4",  # Catppuccin text
        "text_secondary": "#a6adc8",  # Catppuccin subtext0
        "text_muted": "#6c7086",  # Catppuccin overlay0
        "border_color": "rgba(205, 214, 244, 0.07)",
        "surface": "#313244",  # Catppuccin surface0
        # --- UI metadata ---
        "label": "Catppuccin",
        "description": "Mocha-toned surfaces with a soft mauve accent.",
        "swatches": ("#cba6f7", "#1e1e2e", "#cdd6f4"),
    },
}

DEFAULT_THEME = "swizzin"

# Quasar color keys — these are extracted from the theme dict and passed to ui.colors()
QUASAR_KEYS = frozenset(
    {"primary", "secondary", "accent", "dark", "dark_page", "positive", "negative", "info", "warning"}
)

# CSS extension keys — these are synced to --pb-{key} custom properties
CSS_KEYS = frozenset({"primary_soft", "text_primary", "text_secondary", "text_muted", "border_color", "surface"})


def get_theme(name: str) -> dict[str, Any]:
    """Get a theme by name, falling back to default."""
    normalized = name.strip().lower() if name else DEFAULT_THEME
    return THEMES.get(normalized, THEMES[DEFAULT_THEME])


def get_quasar_colors(theme: dict[str, Any]) -> dict[str, str]:
    """Extract the Quasar color parameters from a theme dict."""
    return {k: v for k, v in theme.items() if k in QUASAR_KEYS}


def get_css_properties(theme: dict[str, Any]) -> dict[str, str]:
    """Extract CSS custom property values from a theme dict."""
    return {k: v for k, v in theme.items() if k in CSS_KEYS}
