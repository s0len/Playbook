"""Opt-in authentication for the Playbook web GUI.

The GUI exposes configuration editing, secret retrieval, and privileged
actions (triggering runs, clearing databases). Authentication is therefore
gated behind a login page whenever credentials are configured.

Auth is *opt-in*: it activates only when a non-empty ``GUI_PASSWORD`` is set
in the environment. When no password is configured the GUI runs unauthenticated
exactly as before, but a prominent warning is logged. Credentials are read from
environment variables only (never persisted to the config file) so they can be
supplied via a Kubernetes/Docker secret:

    GUI_USERNAME         Login username (default: "admin")
    GUI_PASSWORD         Login password; empty/unset disables auth entirely
    GUI_STORAGE_SECRET   Session cookie signing key; a random one is generated
                         per start if unset (sessions then reset on restart)
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
from dataclasses import dataclass

from nicegui import app, ui
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from .styles import apply_color_theme, setup_page_styles

LOGGER = logging.getLogger(__name__)

LOGIN_PATH = "/login"

# Exact paths reachable without authentication.
_PUBLIC_PATHS = frozenset({LOGIN_PATH, "/healthz", "/icon.png", "/favicon.ico"})
# Path prefixes reachable without authentication: NiceGUI internal assets and
# the websocket used to render every page (including the login page itself).
_PUBLIC_PREFIXES = ("/_nicegui", "/static")

_AUTH: GuiAuthConfig | None = None


@dataclass(frozen=True)
class GuiAuthConfig:
    """Resolved GUI credentials. Auth is enabled iff ``password`` is non-empty."""

    username: str
    password: str

    @property
    def enabled(self) -> bool:
        return bool(self.password)


def resolve_auth_config() -> GuiAuthConfig:
    """Resolve credentials from the environment.

    Password is read from ``GUI_PASSWORD``; if empty or unset, auth is disabled.
    """
    username = os.getenv("GUI_USERNAME") or "admin"
    password = os.getenv("GUI_PASSWORD") or ""
    return GuiAuthConfig(username=username, password=password)


def resolve_storage_secret() -> str:
    """Return the NiceGUI session-signing secret.

    Prefer an operator-supplied ``GUI_STORAGE_SECRET`` (so sessions survive
    restarts); otherwise generate a random per-process secret. Never fall back
    to a hardcoded value — a published signing key lets anyone forge sessions.
    """
    return os.getenv("GUI_STORAGE_SECRET") or secrets.token_urlsafe(32)


def current_auth() -> GuiAuthConfig:
    """Return the configured auth (resolving lazily on first access)."""
    global _AUTH
    if _AUTH is None:
        _AUTH = resolve_auth_config()
    return _AUTH


def is_public_path(path: str) -> bool:
    """Whether ``path`` is reachable without authentication."""
    if path in _PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


def verify_credentials(auth: GuiAuthConfig, username: str, password: str) -> bool:
    """Constant-time credential check (both fields compared even on mismatch).

    Compares UTF-8 bytes so non-ASCII credentials work — ``hmac.compare_digest``
    raises ``TypeError`` on non-ASCII ``str`` inputs.
    """
    user_ok = hmac.compare_digest((username or "").encode("utf-8"), auth.username.encode("utf-8"))
    pass_ok = hmac.compare_digest((password or "").encode("utf-8"), auth.password.encode("utf-8"))
    return user_ok and pass_ok


class AuthMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated browsers to the login page; 401 for API calls."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if is_public_path(path) or app.storage.user.get("authenticated", False):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "authentication required"}, status_code=401)
        # Remember where the user was headed so login can send them back.
        app.storage.user["referrer_path"] = path
        return RedirectResponse(LOGIN_PATH)


def register_login_page() -> None:
    """Register the ``/login`` page. Safe to call when auth is disabled."""

    @ui.page(LOGIN_PATH)
    def login_page() -> RedirectResponse | None:
        auth = current_auth()
        # No auth configured, or already logged in: nothing to do here.
        if not auth.enabled or app.storage.user.get("authenticated", False):
            return RedirectResponse("/")

        setup_page_styles()
        ui.dark_mode(True)
        apply_color_theme("swizzin")

        def attempt_login() -> None:
            if verify_credentials(auth, username.value or "", password.value or ""):
                app.storage.user.update({"username": username.value, "authenticated": True})
                ui.navigate.to(app.storage.user.get("referrer_path", "/"))
            else:
                ui.notify("Invalid username or password", color="negative")

        with ui.card().classes("absolute-center items-stretch gap-4 p-8"):
            ui.label("Playbook").classes("text-2xl font-bold text-center")
            ui.label("Sign in to continue").classes("text-sm text-center opacity-70")
            username = ui.input("Username").on("keydown.enter", attempt_login)
            password = (
                ui.input("Password", password=True, password_toggle_button=True)
                .on("keydown.enter", attempt_login)
            )
            ui.button("Log in", on_click=attempt_login).classes("w-full")
        return None


def apply_auth() -> GuiAuthConfig:
    """Resolve auth config and install the middleware when enabled.

    Returns the resolved config. Must be called before ``ui.run``.
    """
    global _AUTH
    _AUTH = resolve_auth_config()
    if _AUTH.enabled:
        app.add_middleware(AuthMiddleware)
        LOGGER.info("GUI authentication enabled (user %r).", _AUTH.username)
    else:
        LOGGER.warning(
            "GUI authentication is DISABLED — no GUI_PASSWORD set. Anyone who can reach the "
            "GUI can read/modify config (including secrets) and trigger file operations. "
            "Set GUI_PASSWORD (and optionally GUI_USERNAME) to require login, and keep the "
            "GUI on a trusted network."
        )
    return _AUTH
