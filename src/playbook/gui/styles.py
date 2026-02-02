"""
CSS styles for the Playbook GUI.

Provides glassmorphism effects, transitions, and modern styling.
Uses Quasar's dark mode class (body--dark) for theme switching.
"""

from __future__ import annotations

from nicegui import ui

# Main CSS stylesheet - uses body.body--dark for Quasar dark mode compatibility
PLAYBOOK_CSS = """
/* ===== CSS Variables for Theming ===== */
:root {
    --bg-primary: #f8fafc;
    --bg-card: rgba(255, 255, 255, 0.85);
    --bg-card-solid: #ffffff;
    --text-primary: #0f172a;
    --text-secondary: #334155;
    --text-muted: #64748b;
    --border-color: rgba(148, 163, 184, 0.2);
    --shadow-color: rgba(31, 38, 135, 0.1);
}

body.body--dark {
    --bg-primary: #0f172a;
    --bg-card: rgba(30, 41, 59, 0.85);
    --bg-card-solid: #1e293b;
    --text-primary: #f8fafc;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --border-color: rgba(148, 163, 184, 0.1);
    --shadow-color: rgba(0, 0, 0, 0.3);
}

/* ===== Theme Transitions ===== */
/* Transitions are disabled initially to prevent FOUC, enabled via JS after load */
.theme-ready *, .theme-ready *::before, .theme-ready *::after {
    transition: background-color 0.3s ease, border-color 0.3s ease, color 0.2s ease;
}

/* ===== Page Background ===== */
body {
    background: var(--bg-primary) !important;
}

/* ===== Main Content Text ===== */
.q-page, .q-page-container {
    color: var(--text-primary);
}

/* ===== Glassmorphism Cards ===== */
.glass-card {
    background: var(--bg-card) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    box-shadow: 0 8px 32px var(--shadow-color);
    border-radius: 12px;
}

.glass-card.q-card {
    background: var(--bg-card) !important;
}

/* ===== Card text colors ===== */
.glass-card .text-slate-800,
.glass-card .text-slate-700 {
    color: var(--text-primary) !important;
}

.glass-card .text-slate-600,
.glass-card .text-slate-500 {
    color: var(--text-muted) !important;
}

/* ===== Page titles ===== */
.text-3xl.font-bold {
    color: var(--text-primary) !important;
}

.text-xl.font-semibold {
    color: var(--text-secondary) !important;
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

body.body--dark .status-chip-matched {
    background: rgba(34, 197, 94, 0.25);
    color: #4ade80;
}

.status-chip-missing {
    background: rgba(148, 163, 184, 0.15);
    color: #64748b;
}

body.body--dark .status-chip-missing {
    background: rgba(148, 163, 184, 0.2);
    color: #94a3b8;
}

.status-chip-error {
    background: rgba(239, 68, 68, 0.15);
    color: #dc2626;
}

body.body--dark .status-chip-error {
    background: rgba(239, 68, 68, 0.25);
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
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden;
}

.season-header {
    background: rgba(148, 163, 184, 0.05);
    padding: 16px;
}

/* ===== Navigation Header ===== */
.nav-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
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
    box-shadow: 0 12px 40px var(--shadow-color);
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

.modern-table tbody tr.cursor-pointer:hover {
    background: rgba(59, 130, 246, 0.1);
}

/* Table header styling */
.q-table thead th {
    background: rgba(148, 163, 184, 0.08);
    color: var(--text-muted);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

body.body--dark .q-table thead th {
    background: rgba(148, 163, 184, 0.05);
}

/* Table body text */
.q-table tbody td {
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-color);
}

/* Table row hover */
body.body--dark .q-table tbody tr:hover td {
    background: rgba(148, 163, 184, 0.08);
}

/* Clickable rows */
.q-table tbody tr.cursor-pointer {
    cursor: pointer;
}

body.body--dark .q-table tbody tr.cursor-pointer:hover td {
    background: rgba(59, 130, 246, 0.15);
}

/* Table container in dark mode */
body.body--dark .q-table__container {
    background: transparent;
}

/* Remove default table borders */
.q-table--bordered thead th,
.q-table--bordered tbody td {
    border-color: var(--border-color);
}

/* ===== Log Viewer ===== */
.log-container {
    background: #0f172a !important;
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

body.body--dark ::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.2);
}

/* ===== Focus States ===== */
*:focus-visible {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
}

/* ===== Quasar Component Overrides for Dark Mode ===== */
body.body--dark .q-card {
    background: var(--bg-card-solid);
}

body.body--dark .q-table {
    background: transparent;
}

body.body--dark .q-table th,
body.body--dark .q-table td {
    color: var(--text-primary);
}

body.body--dark .q-field__label,
body.body--dark .q-field__native,
body.body--dark .q-select__dropdown-icon {
    color: var(--text-primary);
}

body.body--dark .q-checkbox__label {
    color: var(--text-primary);
}

body.body--dark .q-expansion-item__toggle-icon {
    color: var(--text-muted);
}

/* ===== Link Colors ===== */
a.text-blue-600 {
    color: #3b82f6;
}

body.body--dark a.text-blue-600 {
    color: #60a5fa;
}
"""


def inject_styles() -> None:
    """Inject the Playbook CSS styles into the page head."""
    ui.add_head_html(f"<style>{PLAYBOOK_CSS}</style>")


# Script to apply dark mode immediately and prevent FOUC
THEME_INIT_SCRIPT = """
<script>
(function() {
    // Check localStorage for theme preference
    var theme = localStorage.getItem('playbook-theme');
    if (theme === 'dark') {
        document.body.classList.add('body--dark');
    }
    // Enable transitions after a brief delay to prevent FOUC
    setTimeout(function() {
        document.body.classList.add('theme-ready');
    }, 50);
})();
</script>
"""


def inject_theme_init_script() -> None:
    """Inject script to apply theme immediately on page load."""
    ui.add_body_html(THEME_INIT_SCRIPT)


def setup_page_styles() -> None:
    """Set up all page styles."""
    inject_styles()
    inject_theme_init_script()
