"""
CSS styles for the Playbook GUI.

Provides glassmorphism effects, transitions, and modern styling.
"""

from __future__ import annotations

from nicegui import ui

# Main CSS stylesheet
PLAYBOOK_CSS = """
/* ===== Theme Transitions ===== */
*, *::before, *::after {
    transition: background-color 0.3s ease, border-color 0.3s ease, color 0.2s ease;
}

/* ===== Glassmorphism Cards ===== */
.glass-card {
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
    border-radius: 12px;
}

.dark .glass-card {
    background: rgba(30, 41, 59, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* Remove default card background when using glass-card */
.glass-card.q-card {
    background: transparent;
}

/* ===== Modern Progress Bar ===== */
.modern-progress {
    height: 8px;
    border-radius: 4px;
    background: rgba(148, 163, 184, 0.2);
    overflow: hidden;
}

.modern-progress .q-linear-progress__track {
    background: transparent;
}

.modern-progress .q-linear-progress__model {
    border-radius: 4px;
}

/* Progress bar color variants */
.modern-progress.progress-success .q-linear-progress__model {
    background: linear-gradient(90deg, #22c55e, #4ade80);
}

.modern-progress.progress-warning .q-linear-progress__model {
    background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.modern-progress.progress-info .q-linear-progress__model {
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
}

.modern-progress.progress-error .q-linear-progress__model {
    background: linear-gradient(90deg, #ef4444, #f87171);
}

/* ===== Status Chips ===== */
.status-chip {
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.status-chip-matched {
    background: rgba(34, 197, 94, 0.15);
    color: #16a34a;
}

.dark .status-chip-matched {
    background: rgba(34, 197, 94, 0.2);
    color: #4ade80;
}

.status-chip-missing {
    background: rgba(148, 163, 184, 0.15);
    color: #64748b;
}

.dark .status-chip-missing {
    background: rgba(148, 163, 184, 0.2);
    color: #94a3b8;
}

.status-chip-error {
    background: rgba(239, 68, 68, 0.15);
    color: #dc2626;
}

.dark .status-chip-error {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
}

/* ===== Episode Row ===== */
.episode-row {
    padding: 12px 16px;
    border-radius: 8px;
    transition: background-color 0.15s ease;
}

.episode-row:hover {
    background: rgba(148, 163, 184, 0.1);
}

.dark .episode-row:hover {
    background: rgba(148, 163, 184, 0.08);
}

.episode-row-matched {
    border-left: 3px solid #22c55e;
}

.episode-row-missing {
    border-left: 3px solid #94a3b8;
}

.episode-row-error {
    border-left: 3px solid #ef4444;
}

/* ===== Season Section ===== */
.season-section {
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 12px;
    overflow: hidden;
}

.dark .season-section {
    border-color: rgba(148, 163, 184, 0.1);
}

.season-header {
    background: rgba(148, 163, 184, 0.05);
    padding: 16px;
}

.dark .season-header {
    background: rgba(148, 163, 184, 0.03);
}

/* ===== Navigation Header ===== */
.nav-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.nav-link {
    padding: 8px 16px;
    border-radius: 8px;
    transition: all 0.2s ease;
}

.nav-link:hover {
    background: rgba(255, 255, 255, 0.1);
}

.nav-link.active {
    background: rgba(59, 130, 246, 0.2);
}

/* ===== Dark Mode Toggle ===== */
.dark-mode-toggle {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.dark-mode-toggle:hover {
    background: rgba(255, 255, 255, 0.1);
}

/* ===== Stats Card Enhancements ===== */
.stat-card {
    border-radius: 12px;
    padding: 20px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(31, 38, 135, 0.15);
}

.dark .stat-card:hover {
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
}

/* ===== Tables ===== */
.modern-table {
    border-radius: 12px;
    overflow: hidden;
}

.modern-table .q-table__top,
.modern-table .q-table__bottom {
    background: transparent;
}

.modern-table tbody tr:hover {
    background: rgba(148, 163, 184, 0.08);
}

.dark .modern-table tbody tr:hover {
    background: rgba(148, 163, 184, 0.05);
}

/* Clickable row styling */
.modern-table tbody tr.cursor-pointer:hover {
    background: rgba(59, 130, 246, 0.08);
}

.dark .modern-table tbody tr.cursor-pointer:hover {
    background: rgba(59, 130, 246, 0.12);
}

/* ===== Log Viewer ===== */
.log-container {
    background: #0f172a;
    border-radius: 12px;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}

.log-line {
    padding: 2px 8px;
    border-radius: 4px;
}

.log-line:hover {
    background: rgba(255, 255, 255, 0.05);
}

/* ===== Expansion Panels ===== */
.q-expansion-item {
    border-radius: 8px;
    overflow: hidden;
}

.q-expansion-item__container {
    border-radius: 8px;
}

/* ===== Buttons ===== */
.btn-glass {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.dark .btn-glass {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

/* ===== Scrollbar Styling ===== */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.3);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.5);
}

.dark ::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.2);
}

.dark ::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.4);
}

/* ===== Page Background ===== */
body {
    background: #f8fafc;
}

body.dark {
    background: #0f172a;
}

/* ===== Focus States ===== */
*:focus-visible {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
}

/* ===== Utility Classes ===== */
.text-gradient {
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.shadow-glow {
    box-shadow: 0 0 40px rgba(59, 130, 246, 0.15);
}

.dark .shadow-glow {
    box-shadow: 0 0 40px rgba(59, 130, 246, 0.1);
}
"""


def inject_styles() -> None:
    """Inject the Playbook CSS styles into the page head."""
    ui.add_head_html(f"<style>{PLAYBOOK_CSS}</style>")


def inject_dark_mode_script() -> None:
    """Inject JavaScript for dark mode class management on body."""
    script = """
    <script>
    // Observe dark mode changes and sync to body class
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class') {
                const html = document.documentElement;
                const body = document.body;
                if (html.classList.contains('dark')) {
                    body.classList.add('dark');
                } else {
                    body.classList.remove('dark');
                }
            }
        });
    });

    observer.observe(document.documentElement, { attributes: true });

    // Initial sync
    if (document.documentElement.classList.contains('dark')) {
        document.body.classList.add('dark');
    }
    </script>
    """
    ui.add_head_html(script)


def setup_page_styles() -> None:
    """Set up all page styles including CSS and dark mode script."""
    inject_styles()
    inject_dark_mode_script()
