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
    --accent-color: #34d399;
    --accent-hover: #2cb783;
    --accent-soft: rgba(52, 211, 153, 0.2);
}

body.body--dark {
    --bg-primary: #141416;
    --bg-card: #2a2a2d;
    --bg-card-solid: #252528;
    --text-primary: #e7e7ea;
    --text-secondary: #b5b5bc;
    --text-muted: #8f8f98;
    --border-color: rgba(255, 255, 255, 0.07);
    --shadow-color: rgba(0, 0, 0, 0.5);
    --accent-color: #34d399;
    --accent-hover: #2cb783;
    --accent-soft: rgba(52, 211, 153, 0.2);
}

body.body--dark.theme-swizzin {
    --accent-color: #34d399;
    --accent-hover: #2cb783;
    --accent-soft: rgba(52, 211, 153, 0.2);
}

body.body--dark.theme-catppuccin {
    --accent-color: #cba6f7;
    --accent-hover: #b78de8;
    --accent-soft: rgba(203, 166, 247, 0.24);
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
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
    border-radius: 12px;
}

body.body--dark .glass-card {
    background: #2a2a2d !important;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.24);
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
    background: linear-gradient(90deg, var(--accent-color), var(--accent-hover));
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

/* ===== Left Sidebar ===== */
.playbook-sidebar .q-drawer__content {
    background: #0e0e16 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    box-shadow: none !important;
}

/* Nav item base */
.sidebar-nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    border-radius: 8px;
    width: 100%;
    transition: all 0.15s ease;
    color: rgba(255, 255, 255, 0.3);
}

.sidebar-nav-item:hover {
    background: rgba(255, 255, 255, 0.07);
    color: rgba(255, 255, 255, 0.7);
}

.sidebar-nav-item-active {
    background: var(--accent-soft) !important;
    color: var(--accent-color) !important;
}

/* Sidebar separator */
.sidebar-separator {
    width: 100%;
    height: 1px;
    background: rgba(255, 255, 255, 0.06);
}

/* Sidebar icon buttons (dark mode toggle, etc.) */
.sidebar-icon-btn {
    color: rgba(255, 255, 255, 0.3);
}

.sidebar-icon-btn:hover {
    background: rgba(255, 255, 255, 0.07);
    color: rgba(255, 255, 255, 0.7);
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
    background: rgba(0, 212, 212, 0.08);
}

/* Table header styling */
.q-table thead th {
    background: rgba(148, 163, 184, 0.08);
    color: var(--text-muted);
    font-weight: 600;
    font-size: 0.75rem;
    letter-spacing: 0.02em;
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
    background: rgba(0, 212, 212, 0.12);
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
    background: #1a1f2e !important;
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
    outline: 2px solid var(--accent-color);
    outline-offset: 2px;
}

body.body--dark *:focus-visible {
    outline-color: var(--accent-color);
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
a {
    color: var(--accent-color);
}

a:hover {
    color: var(--accent-hover);
}

/* ===== Settings Page Styles ===== */
.settings-page-shell {
    min-height: calc(100vh - 32px);
}

.settings-main-layout {
    align-items: flex-start;
}

.settings-sidebar {
    border-right: 1px solid var(--border-color);
    padding-right: 14px;
    min-height: 70vh;
    align-items: stretch;
}

.settings-sidebar .q-btn .q-btn__content {
    justify-content: flex-start;
}

.settings-sidebar .q-btn {
    width: 100%;
    text-align: left;
}

.settings-subnav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    transition: all 0.15s ease;
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.62) !important;
    background: transparent !important;
    border: 1px solid transparent;
}

.settings-subnav-item .q-btn__content,
.settings-subnav-item .q-icon,
.settings-subnav-item .q-badge,
.settings-subnav-item .q-focus-helper,
.settings-subnav-item .q-btn__content span {
    color: inherit !important;
}

.settings-subnav-item .q-btn__content {
    width: 100%;
    justify-content: flex-start !important;
    text-align: left;
}

.settings-subnav-item .q-btn__content .nicegui-row {
    width: 100%;
    justify-content: flex-start !important;
}

.settings-subnav-item.text-primary,
.settings-subnav-item .text-primary {
    color: inherit !important;
}

.settings-sidebar .q-btn.settings-subnav-item.text-primary,
.settings-sidebar .q-btn.settings-subnav-item .text-primary {
    color: inherit !important;
}

.settings-subnav-item:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    color: rgba(255, 255, 255, 0.9) !important;
}

.settings-subnav-item-active {
    background: rgba(255, 255, 255, 0.14) !important;
    color: #f8fafc !important;
    border: 1px solid rgba(255, 255, 255, 0.24) !important;
}

body.body--dark .settings-subnav-item-active {
    background: rgba(255, 255, 255, 0.14) !important;
    color: #f8fafc !important;
}

.settings-content {
    gap: 14px;
    max-width: none;
}

.settings-surface {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.06)) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.25) !important;
}

.view-shell {
    min-height: calc(100vh - 24px);
}

.settings-surface .q-expansion-item,
.settings-surface .q-expansion-item__container {
    border-radius: 8px;
}

.settings-inline-card {
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

.settings-modal-card {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.11), rgba(255, 255, 255, 0.08)) !important;
}

.settings-theme-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    box-shadow: none;
}

.settings-theme-card-active {
    border-color: var(--accent-color) !important;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06), 0 0 0 1px var(--accent-soft) !important;
}

/* Settings form inputs */
.settings-input .q-field__control {
    min-height: 40px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
}

.settings-input .q-field__label {
    font-size: 0.875rem;
}

body.body--dark .settings-input .q-field__control::before {
    border-color: rgba(255, 255, 255, 0.16) !important;
}

body.body--dark .settings-input.q-field--focused .q-field__control::before,
body.body--dark .settings-input.q-field--focused .q-field__control::after {
    border-color: var(--accent-color) !important;
}

body.body--dark .settings-input .q-field__native,
body.body--dark .settings-input .q-field__input,
body.body--dark .settings-input .q-field__label,
body.body--dark .settings-input .q-select__dropdown-icon {
    color: rgba(255, 255, 255, 0.82) !important;
}

/* Settings toggle */
.settings-toggle .q-toggle__label {
    font-size: 0.875rem;
}

body.body--dark .settings-toggle .q-toggle__inner {
    color: var(--accent-color);
}

/* Buttons scoped to settings header actions */
.settings-action-primary {
    background: var(--accent-color) !important;
    color: #f8fafc !important;
    border: 1px solid var(--accent-color) !important;
}

.settings-action-primary.bg-primary {
    background: var(--accent-color) !important;
}

.settings-action-primary .q-btn__content,
.settings-action-primary .q-icon {
    color: #f8fafc !important;
}

.settings-action-primary:hover {
    background: var(--accent-hover) !important;
    border-color: var(--accent-hover) !important;
}

.settings-action-secondary {
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    color: rgba(255, 255, 255, 0.85) !important;
    background: transparent !important;
}

.settings-action-secondary.bg-primary {
    background: transparent !important;
}

.settings-action-secondary .q-btn__content,
.settings-action-secondary .q-icon {
    color: rgba(255, 255, 255, 0.85) !important;
}

.settings-action-secondary:hover {
    background: rgba(255, 255, 255, 0.08) !important;
}

/* App-wide semantic button system */
.app-btn {
    border-radius: 8px;
    font-weight: 600;
    letter-spacing: 0.01em;
}

/* Neutralize Quasar default primary utility classes on semantic buttons. */
.app-btn.bg-primary {
    background: transparent !important;
}

.app-btn.text-white,
.app-btn .text-white {
    color: inherit !important;
}

.app-btn-primary {
    background: var(--accent-color) !important;
    border: 1px solid var(--accent-color) !important;
    color: #f8fafc !important;
}

.app-btn-primary.bg-primary {
    background: var(--accent-color) !important;
}

.app-btn-primary .q-btn__content,
.app-btn-primary .q-icon {
    color: #f8fafc !important;
}

.app-btn-primary:hover {
    background: var(--accent-hover) !important;
    border-color: var(--accent-hover) !important;
}

.app-btn-danger {
    background: rgba(239, 68, 68, 0.12) !important;
    border: 1px solid rgba(239, 68, 68, 0.35) !important;
    color: #fca5a5 !important;
}

.app-btn-danger.bg-primary {
    background: rgba(239, 68, 68, 0.12) !important;
}

.app-btn-danger .q-btn__content,
.app-btn-danger .q-icon {
    color: #fca5a5 !important;
}

.app-btn-danger:hover {
    background: rgba(239, 68, 68, 0.18) !important;
}

.app-btn-outline {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.16) !important;
    color: rgba(255, 255, 255, 0.88) !important;
}

.app-btn-outline.bg-primary {
    background: rgba(255, 255, 255, 0.03) !important;
}

.app-btn-outline .q-btn__content,
.app-btn-outline .q-icon {
    color: rgba(255, 255, 255, 0.88) !important;
}

.app-btn-outline:hover {
    background: rgba(255, 255, 255, 0.09) !important;
    border-color: rgba(255, 255, 255, 0.24) !important;
}

.q-btn .q-btn__content {
    text-transform: none !important;
    letter-spacing: normal !important;
}

body.body--dark .q-btn--outline,
body.body--dark .q-btn--flat {
    color: var(--text-primary);
}

/* App-wide chips and badges */
.app-chip {
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.72) !important;
    background: transparent !important;
    padding: 4px 8px;
}

/* Quasar may inject text/bg utility classes on chip-like buttons. */
@layer quasar_importants {
    .q-btn.app-chip.text-primary,
    .q-btn.app-chip .text-primary,
    .q-chip.app-chip.text-primary,
    .q-chip.app-chip .text-primary {
        color: inherit !important;
    }

    .q-btn.app-chip.bg-primary,
    .q-chip.app-chip.bg-primary {
        background: transparent !important;
        background-color: transparent !important;
    }
}

.app-chip .q-btn__content,
.app-chip .q-icon {
    color: inherit !important;
}

.app-chip:hover {
    background: rgba(255, 255, 255, 0.07) !important;
    color: rgba(255, 255, 255, 0.9) !important;
}

.app-chip-active {
    background: var(--accent-soft) !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
    color: var(--accent-color) !important;
}

.app-badge {
    border-radius: 6px;
    border: 1px solid transparent;
}

/* Quasar adds bg/text utility classes to badges by default; neutralize them. */
.q-badge.app-badge.bg-primary {
    background-color: transparent !important;
}

.q-badge.app-badge.text-white,
.q-badge.app-badge .text-white,
.q-badge.app-badge.text-dark,
.q-badge.app-badge .text-dark,
.q-badge.app-badge.text-primary,
.q-badge.app-badge .text-primary {
    color: inherit !important;
}

.app-badge-muted {
    background: rgba(255, 255, 255, 0.12) !important;
    background-color: rgba(255, 255, 255, 0.12) !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
    color: rgba(255, 255, 255, 0.86) !important;
}

.app-badge-warning {
    background: rgba(251, 191, 36, 0.14) !important;
    background-color: rgba(251, 191, 36, 0.14) !important;
    border-color: rgba(251, 191, 36, 0.28) !important;
    color: #fcd34d !important;
    min-width: 8px;
    min-height: 8px;
    padding: 0 !important;
}

.app-badge-success {
    background: rgba(74, 222, 128, 0.14) !important;
    background-color: rgba(74, 222, 128, 0.14) !important;
    border-color: rgba(74, 222, 128, 0.3) !important;
    color: #86efac !important;
}

.app-badge-danger {
    background: rgba(248, 113, 113, 0.14) !important;
    background-color: rgba(248, 113, 113, 0.14) !important;
    border-color: rgba(248, 113, 113, 0.3) !important;
    color: #fca5a5 !important;
}

/* Semantic icon tones */
.app-stat-icon-accent {
    color: var(--accent-color);
}

.app-stat-icon-warning {
    color: #fbbf24;
}

.app-stat-icon-muted {
    color: rgba(255, 255, 255, 0.56);
}

.app-text-accent {
    color: var(--accent-color);
}

.app-text-success {
    color: #4ade80;
}

.app-text-warning {
    color: #fbbf24;
}

.app-text-danger {
    color: #f87171;
}

.app-text-muted {
    color: rgba(255, 255, 255, 0.62);
}

.app-link {
    color: var(--accent-color);
}

.app-link:hover {
    color: var(--accent-hover);
}

.app-alert {
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 8px;
}

.app-alert-info {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.16);
}

.app-alert-success {
    background: rgba(74, 222, 128, 0.12);
    border-color: rgba(74, 222, 128, 0.28);
}

.app-alert-warning {
    background: rgba(251, 191, 36, 0.12);
    border-color: rgba(251, 191, 36, 0.28);
}

.app-alert-danger {
    background: rgba(248, 113, 113, 0.12);
    border-color: rgba(248, 113, 113, 0.28);
}

.app-stat-surface-accent {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.14);
}

.app-stat-surface-success {
    background: rgba(74, 222, 128, 0.12);
    border-color: rgba(74, 222, 128, 0.24);
}

.app-stat-surface-warning {
    background: rgba(251, 191, 36, 0.12);
    border-color: rgba(251, 191, 36, 0.24);
}

.app-stat-surface-danger {
    background: rgba(248, 113, 113, 0.12);
    border-color: rgba(248, 113, 113, 0.24);
}

.app-stat-surface-muted {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.12);
}

body.body--dark .q-toggle__inner,
body.body--dark .q-radio__inner,
body.body--dark .q-checkbox__inner {
    color: rgba(255, 255, 255, 0.6) !important;
}

body.body--dark .q-toggle__inner--truthy,
body.body--dark .q-radio__inner--truthy,
body.body--dark .q-checkbox__inner--truthy {
    color: var(--accent-color) !important;
}

/* Key-value editor */
.kv-editor-row {
    background: rgba(148, 163, 184, 0.05);
    border-radius: 6px;
    padding: 8px;
}

body.body--dark .kv-editor-row {
    background: rgba(148, 163, 184, 0.08);
}

/* List editor items */
.list-editor-item {
    background: rgba(148, 163, 184, 0.05);
    border-radius: 6px;
    transition: background-color 0.15s ease;
}

.list-editor-item:hover {
    background: rgba(148, 163, 184, 0.1);
}

body.body--dark .list-editor-item {
    background: rgba(148, 163, 184, 0.08);
}

body.body--dark .list-editor-item:hover {
    background: rgba(148, 163, 184, 0.12);
}
"""


def inject_styles() -> None:
    """Inject the Playbook CSS styles into the page head."""
    ui.add_head_html(f"<style>{PLAYBOOK_CSS}</style>")


# Script to apply dark mode immediately and prevent FOUC
THEME_INIT_SCRIPT = """
<script>
(function() {
    // Check localStorage for theme preference (default to dark)
    var theme = localStorage.getItem('playbook-theme');
    var colorTheme = localStorage.getItem('playbook-color-theme') || 'swizzin';
    if (theme !== 'light') {
        // Default to dark mode if no preference or preference is 'dark'
        document.body.classList.add('body--dark');
    }
    if (colorTheme === 'catppuccin') {
        document.body.classList.add('theme-catppuccin');
    } else {
        document.body.classList.add('theme-swizzin');
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


def apply_color_theme(theme_name: str) -> None:
    """Apply GUI color theme class to document body."""
    normalized = theme_name.strip().lower() if theme_name else "swizzin"
    if normalized not in {"swizzin", "catppuccin"}:
        normalized = "swizzin"
    ui.run_javascript(
        """
        document.body.classList.remove('theme-swizzin', 'theme-catppuccin');
        document.body.classList.add('theme-"""
        + normalized
        + """');
        localStorage.setItem('playbook-color-theme', '"""
        + normalized
        + """');
        """
    )
