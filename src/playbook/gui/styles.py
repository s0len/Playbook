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
.text-3xl.font-bold:not(.stat-value) {
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
    transition: background-color 0.15s ease, box-shadow 0.15s ease;
}

.episode-row:hover {
    background: rgba(148, 163, 184, 0.1);
}

.episode-row-matched {
    border-left: 3px solid #4ade80;
}

.episode-row-missing {
    border-left: 3px solid #94a3b8;
}

.episode-row-error {
    border-left: 3px solid #ef4444;
}

.episode-row .q-btn.episode-row-action-btn.bg-primary {
    background: transparent !important;
    background-color: transparent !important;
}

.episode-row .q-btn.episode-row-action-btn.text-primary,
.episode-row .q-btn.episode-row-action-btn .text-primary,
.episode-row .q-btn.episode-row-action-btn .q-icon {
    color: inherit !important;
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
    background: var(--accent-soft);
}

/* Table header styling */
.q-table thead th {
    background: transparent;
    color: var(--text-muted);
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-color);
}

body.body--dark .q-table thead th {
    background: transparent;
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
    background: var(--accent-soft);
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

/* ===== Enhanced Log Viewer ===== */
.log-container {
    background: rgba(0, 0, 0, 0.18) !important;
    border-radius: 10px;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}

/* Log entry row — colored left border per level */
.log-entry {
    padding: 4px 12px 4px 0 !important;
    border-left: 2px solid transparent;
    transition: background-color 0.12s ease, opacity 0.12s ease;
    gap: 10px !important;
    align-items: flex-start !important;
}

.log-entry:hover {
    background: rgba(148, 163, 184, 0.05);
}

/* Info: accent-colored border (changes with theme) */
.log-entry-info {
    border-left-color: var(--accent-color);
}

/* Warning: amber tint */
.log-entry-warning {
    border-left-color: #fbbf24;
    background: rgba(251, 191, 36, 0.03);
}

.log-entry-warning:hover {
    background: rgba(251, 191, 36, 0.07);
}

/* Error: red tint */
.log-entry-error {
    border-left-color: #f87171;
    background: rgba(248, 113, 113, 0.04);
}

.log-entry-error:hover {
    background: rgba(248, 113, 113, 0.08);
}

/* Debug: dimmed */
.log-entry-debug {
    border-left-color: rgba(148, 163, 184, 0.25);
    opacity: 0.55;
}

.log-entry-debug:hover {
    opacity: 0.8;
}

/* Run Recap / Summary — prominent accent band */
.log-entry-recap {
    border-left-width: 3px !important;
    border-left-color: var(--accent-color) !important;
    background: var(--accent-soft) !important;
    padding-top: 6px !important;
    padding-bottom: 6px !important;
    margin: 2px 0;
    border-radius: 0 4px 4px 0;
}

.log-entry-recap:hover {
    filter: brightness(1.08);
}

.log-entry-recap .log-msg {
    color: var(--text-primary) !important;
    font-weight: 500;
}

/* Timestamp */
.log-timestamp {
    color: var(--text-muted);
    font-size: 11px;
    flex-shrink: 0;
    min-width: 56px;
    line-height: 20px;
    user-select: none;
    padding-left: 10px;
}

/* Level badge pill */
.log-badge {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 1px 6px;
    border-radius: 3px;
    flex-shrink: 0;
    min-width: 38px;
    text-align: center;
    line-height: 18px;
}

.log-badge-info {
    color: var(--accent-color);
    background: var(--accent-soft);
}

.log-badge-warning {
    color: #fbbf24;
    background: rgba(251, 191, 36, 0.14);
}

.log-badge-error {
    color: #f87171;
    background: rgba(248, 113, 113, 0.14);
}

.log-badge-debug {
    color: var(--text-muted);
    background: rgba(148, 163, 184, 0.1);
}

/* Message text */
.log-msg {
    font-size: 12px;
    line-height: 20px;
    color: var(--text-secondary);
    white-space: nowrap;
    min-width: 0;
}

.log-msg-info {
    color: var(--text-primary);
}

.log-msg-warning {
    color: #fcd34d;
}

.log-msg-error {
    color: #fca5a5;
}

.log-msg-debug {
    color: var(--text-muted);
}

.log-empty {
    color: var(--text-muted);
}

.log-footer {
    color: var(--text-muted);
}

/* ===== Structured Log Blocks ===== */

/* Block content container (used by recap, processing, summary) */
.log-block-content {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
    padding: 2px 0;
}

.log-block-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: 0.02em;
}

/* Stat pills row (Run Recap) */
.log-stats-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    align-items: center;
}

.log-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 1px 8px;
    border-radius: 4px;
    background: rgba(148, 163, 184, 0.08);
    border: 1px solid rgba(148, 163, 184, 0.1);
    line-height: 18px;
    white-space: nowrap;
}

.log-pill-value {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}

.log-pill-label {
    font-size: 9px;
    color: var(--text-muted);
}

.log-pill-accent {
    background: var(--accent-soft);
    border-color: transparent;
}

.log-pill-accent .log-pill-value {
    color: var(--accent-color);
}

.log-pill-warning {
    background: rgba(251, 191, 36, 0.1);
    border-color: rgba(251, 191, 36, 0.15);
}

.log-pill-warning .log-pill-value {
    color: #fbbf24;
}

.log-pill-error {
    background: rgba(248, 113, 113, 0.1);
    border-color: rgba(248, 113, 113, 0.15);
}

.log-pill-error .log-pill-value {
    color: #f87171;
}

/* Processing Details — source file + destination meta */
.log-processing-source {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-primary);
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.log-processing-meta {
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.log-detail-dest {
    color: var(--text-secondary);
}

.log-detail-tag {
    display: inline-block;
    padding: 0 5px;
    border-radius: 3px;
    background: rgba(148, 163, 184, 0.08);
    color: var(--text-muted);
    font-size: 10px;
}

.log-detail-upgrade {
    background: var(--accent-soft);
    color: var(--accent-color);
}

.log-detail-action {
    color: var(--text-muted);
    font-size: 10px;
}

/* Summary / generic block — inline title + stats */
.log-summary-content {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 20px;
}

.log-summary-stat {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    white-space: nowrap;
}

/* Separator dot / dash */
.log-sep {
    color: var(--text-muted);
    opacity: 0.4;
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

@layer quasar_importants {
    .settings-subnav-item.text-primary,
    .settings-subnav-item .text-primary,
    .settings-subnav-item .q-icon,
    .settings-subnav-item .q-btn__content,
    .settings-subnav-item .q-btn__content span {
        color: inherit !important;
    }
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
    align-items: flex-start !important;
}

.app-btn .q-btn__content {
    width: 100%;
    justify-content: flex-start !important;
    text-align: left;
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
    .q-btn.text-primary,
    .q-btn .text-primary {
        color: inherit !important;
    }

    .q-btn.bg-primary:not(.app-btn) {
        background: transparent !important;
        background-color: transparent !important;
    }

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

/* Force semantic badge variants in the same high-priority layer. */
@layer quasar_importants {
    .q-badge.app-badge.bg-primary {
        background: transparent !important;
        background-color: transparent !important;
    }

    .q-badge.app-badge.app-chip-active {
        background: var(--accent-soft) !important;
        background-color: var(--accent-soft) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        color: var(--accent-color) !important;
    }

    .q-badge.app-badge.app-badge-muted {
        background: rgba(255, 255, 255, 0.12) !important;
        background-color: rgba(255, 255, 255, 0.12) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        color: rgba(255, 255, 255, 0.86) !important;
    }

    .q-badge.app-badge.app-badge-warning {
        background: rgba(251, 191, 36, 0.14) !important;
        background-color: rgba(251, 191, 36, 0.14) !important;
        border-color: rgba(251, 191, 36, 0.28) !important;
        color: #fcd34d !important;
    }

    .q-badge.app-badge.app-badge-success {
        background: rgba(74, 222, 128, 0.14) !important;
        background-color: rgba(74, 222, 128, 0.14) !important;
        border-color: rgba(74, 222, 128, 0.3) !important;
        color: #86efac !important;
    }

    .q-badge.app-badge.app-badge-danger {
        background: rgba(248, 113, 113, 0.14) !important;
        background-color: rgba(248, 113, 113, 0.14) !important;
        border-color: rgba(248, 113, 113, 0.3) !important;
        color: #fca5a5 !important;
    }
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
    color: var(--text-muted);
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

/* ===== Global Text Color Overrides ===== */
/* Override hardcoded Tailwind text-slate-* inside page shells and dialogs
   so colors respond to light/dark mode via CSS variables. */
.view-shell .text-slate-800,
.view-shell .text-slate-700,
.settings-page-shell .text-slate-800,
.settings-page-shell .text-slate-700,
.q-dialog .text-slate-800,
.q-dialog .text-slate-700 {
    color: var(--text-primary) !important;
}

.view-shell .text-slate-600,
.settings-page-shell .text-slate-600,
.q-dialog .text-slate-600 {
    color: var(--text-secondary) !important;
}

.view-shell .text-slate-500,
.view-shell .text-slate-400,
.settings-page-shell .text-slate-500,
.settings-page-shell .text-slate-400,
.q-dialog .text-slate-500,
.q-dialog .text-slate-400 {
    color: var(--text-muted) !important;
}

.view-shell .text-slate-300,
.view-shell .text-slate-200,
.view-shell .text-slate-100,
.settings-page-shell .text-slate-300,
.settings-page-shell .text-slate-200,
.settings-page-shell .text-slate-100,
.q-dialog .text-slate-300,
.q-dialog .text-slate-200,
.q-dialog .text-slate-100 {
    color: var(--text-primary) !important;
}

/* Divider color override */
.view-shell .divide-slate-100 > :not(:first-child),
.view-shell .divide-slate-800 > :not(:first-child) {
    border-color: var(--border-color) !important;
}

/* ===== Stat Card Visual Hierarchy ===== */
/* Colored top border per semantic tone */
.stat-card.app-stat-surface-success { border-top: 3px solid #4ade80; }
.stat-card.app-stat-surface-warning { border-top: 3px solid #fbbf24; }
.stat-card.app-stat-surface-danger  { border-top: 3px solid #f87171; }
.stat-card.app-stat-surface-accent  { border-top: 3px solid var(--accent-color); }
.stat-card.app-stat-surface-muted   { border-top: 3px solid rgba(148, 163, 184, 0.4); }

/* Large stat number inherits semantic color */
.stat-card.app-stat-surface-success .stat-value { color: #4ade80 !important; }
.stat-card.app-stat-surface-warning .stat-value { color: #fbbf24 !important; }
.stat-card.app-stat-surface-danger  .stat-value { color: #f87171 !important; }
.stat-card.app-stat-surface-accent  .stat-value { color: var(--accent-color) !important; }
.stat-card.app-stat-surface-muted   .stat-value { color: var(--text-primary) !important; }

/* Icon gets a subtle background pill */
.stat-card .app-stat-icon-accent,
.stat-card .app-text-success,
.stat-card .app-text-warning,
.stat-card .app-text-danger,
.stat-card .app-stat-icon-muted {
    padding: 6px;
    border-radius: 8px;
    background: rgba(148, 163, 184, 0.08);
}

/* ===== Activity Feed Left Borders ===== */
.app-alert-success { border-left: 3px solid #4ade80; }
.app-alert-warning { border-left: 3px solid #fbbf24; }
.app-alert-danger  { border-left: 3px solid #f87171; }
.app-alert-info    { border-left: 3px solid var(--accent-color); }

/* ===== Episode Row Hover Enhancements ===== */
.episode-row-matched:hover {
    background: rgba(74, 222, 128, 0.06);
    box-shadow: inset 3px 0 0 #4ade80;
}

.episode-row-error:hover {
    background: rgba(248, 113, 113, 0.06);
    box-shadow: inset 3px 0 0 #f87171;
}

/* ===== Unmatched File Card Status Classes ===== */
.file-card-warning { border-left: 3px solid #fbbf24; }
.file-card-accent  { border-left: 3px solid var(--accent-color); }
.file-card-muted   { border-left: 3px solid rgba(148, 163, 184, 0.4); }

/* ===== Match Attempt Card Classes ===== */
.match-attempt-green {
    border-left: 4px solid #4ade80;
    background: rgba(74, 222, 128, 0.06);
    border-radius: 8px;
    padding: 8px;
}

.match-attempt-amber {
    border-left: 4px solid #fbbf24;
    background: rgba(251, 191, 36, 0.06);
    border-radius: 8px;
    padding: 8px;
}

.match-attempt-slate {
    border-left: 4px solid rgba(148, 163, 184, 0.4);
    background: rgba(148, 163, 184, 0.04);
    border-radius: 8px;
    padding: 8px;
}

.match-attempt-green .match-attempt-icon { color: #4ade80; }
.match-attempt-amber .match-attempt-icon { color: #fbbf24; }
.match-attempt-slate .match-attempt-icon { color: #94a3b8; }

/* ===== Global Hover / Transition Polish ===== */
/* Glass cards get hover shadow lift (preserve theme transitions from .theme-ready *) */
.glass-card {
    transition: background-color 0.3s ease, border-color 0.3s ease,
                color 0.2s ease, box-shadow 0.2s ease;
}

/* Expansion panel headers get subtle hover bg */
.q-expansion-item .q-item:hover {
    background: rgba(148, 163, 184, 0.06);
}

/* Badges/chips get transition */
.app-badge, .app-chip, .status-chip {
    transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

/* ===== Mobile Hamburger Button ===== */
.mobile-hamburger {
    position: fixed !important;
    top: 10px;
    left: 10px;
    z-index: 2000;
    display: none !important;
    background: rgba(14, 14, 22, 0.9) !important;
    color: rgba(255, 255, 255, 0.8) !important;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 10px !important;
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    min-height: 40px !important;
    padding: 0 !important;
}

.mobile-hamburger .q-btn__content,
.mobile-hamburger .q-icon {
    color: rgba(255, 255, 255, 0.8) !important;
}

/* ===== Responsive: Tablet and below (< 1024px) ===== */
@media (max-width: 1023px) {
    .mobile-hamburger {
        display: inline-flex !important;
    }

    /* Settings layout: stack sidebar and content */
    .settings-main-layout {
        flex-direction: column !important;
    }

    .settings-sidebar {
        width: 100% !important;
        min-height: auto !important;
        border-right: none !important;
        border-bottom: 1px solid var(--border-color) !important;
        padding-right: 0 !important;
        padding-bottom: 12px !important;
        flex-direction: row !important;
        overflow-x: auto !important;
        gap: 4px !important;
    }

    .settings-sidebar .settings-subnav-item {
        white-space: nowrap;
        min-width: auto;
    }

    /* Settings header: stack on tablet */
    .settings-header-row {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 12px !important;
    }
}

/* ===== Responsive: Phone (< 768px) ===== */
@media (max-width: 768px) {
    /* Reduce page padding and spacing */
    .view-shell {
        padding: 12px !important;
        padding-top: 56px !important;
        gap: 12px !important;
    }

    .settings-page-shell {
        padding: 12px !important;
        padding-top: 56px !important;
        gap: 12px !important;
    }

    /* Smaller page titles */
    .text-3xl.font-bold {
        font-size: 1.5rem !important;
    }

    .text-4xl.font-bold {
        font-size: 1.75rem !important;
    }

    /* Cards: tighter padding */
    .glass-card.q-card {
        padding: 10px !important;
    }

    /* Stats cards: 2-column grid */
    .stats-grid {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 8px !important;
        width: 100% !important;
    }

    .stats-grid .stat-card {
        width: 100% !important;
        min-width: 0 !important;
    }

    .stat-card .text-3xl {
        font-size: 1.5rem !important;
    }

    /* Dashboard: stack activity feed and quick actions */
    .dashboard-main {
        flex-direction: column !important;
    }

    .dashboard-main > * {
        width: 100% !important;
        min-width: 0 !important;
        flex: none !important;
    }

    /* Log messages: allow wrapping on mobile */
    .log-msg,
    .log-processing-source,
    .log-processing-meta {
        white-space: normal !important;
        word-break: break-word !important;
    }

    /* Log container: less padding */
    .log-container {
        padding: 8px !important;
    }

    /* Log toolbar: tighter layout */
    .log-toolbar {
        gap: 6px !important;
    }

    .log-toolbar .min-w-48 {
        min-width: 0 !important;
    }

    /* Log level/sport selects: full width on mobile */
    .log-toolbar .w-32,
    .log-toolbar .w-36 {
        width: 48% !important;
    }

    /* Unmatched file cards: stack layout */
    .file-card-row {
        flex-direction: column !important;
        align-items: flex-start !important;
    }

    .file-card-actions {
        flex-direction: row !important;
        flex-wrap: wrap !important;
        width: 100% !important;
        gap: 6px !important;
        padding-top: 8px !important;
        border-top: 1px solid var(--border-color);
        margin-top: 8px;
    }

    /* Unmatched stat cards: 2-column grid */
    .unmatched-stats-grid {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 8px !important;
        width: 100% !important;
    }

    .unmatched-stats-grid .glass-card {
        min-width: 0 !important;
    }

    /* Sport table: responsive */
    .modern-table {
        overflow-x: auto !important;
    }

    .modern-table .q-table {
        min-width: 500px;
    }

    /* Hide less important table columns on mobile */
    .sports-table td:nth-child(4),
    .sports-table th:nth-child(4),
    .sports-table td:nth-child(5),
    .sports-table th:nth-child(5),
    .sports-table td:nth-child(7),
    .sports-table th:nth-child(7) {
        display: none !important;
    }

    /* Hide toggle label text on mobile (keep just the switch) */
    .sports-table .q-toggle__label {
        display: none !important;
    }

    /* Hide checkbox column on small phones */
    .sports-table td:nth-child(1),
    .sports-table th:nth-child(1) {
        display: none !important;
    }

    /* Dialogs: full width on mobile */
    .q-dialog .q-card {
        max-width: 100vw !important;
        width: 100% !important;
        margin: 8px !important;
    }

    /* Filter sections: tighter spacing */
    .filter-row {
        gap: 8px !important;
    }

    .filter-row .w-48 {
        width: 100% !important;
    }

    .filter-row .min-w-48 {
        min-width: 0 !important;
    }

    /* Settings action buttons: wrap */
    .settings-header-actions {
        width: 100% !important;
        justify-content: flex-end !important;
    }
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
