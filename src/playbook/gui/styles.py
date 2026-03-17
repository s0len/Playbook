"""
CSS styles for the Playbook GUI.

Provides glassmorphism effects, transitions, and modern styling.
Uses Quasar's dark mode class (body--dark) for theme switching.
"""

from __future__ import annotations

from nicegui import ui

# Main CSS stylesheet - uses body.body--dark for Quasar dark mode compatibility
PLAYBOOK_CSS = """
/* ===== Custom Fonts ===== */
/* Anybody: Bold condensed display — sporty, geometric, editorial */
/* DM Sans: Clean optical-size body — modern, sharp readability */

/* ===== CSS Variables ===== */
/* Quasar colors (--q-primary, --q-dark, etc.) are set by ui.colors() in Python.
   The --pb-* properties below are synced by apply_color_theme() JS. */
:root {
    --font-display: 'Anybody', 'DM Sans', system-ui, sans-serif;
    --font-body: 'DM Sans', system-ui, sans-serif;
    --radius: 6px;
    --radius-lg: 10px;
    /* Defaults overridden by apply_color_theme() JS */
    --pb-primary: #34d399;
    --pb-primary-soft: rgba(52, 211, 153, 0.10);
    --pb-text-primary: #e8e8ec;
    --pb-text-secondary: #9898a4;
    --pb-text-muted: #5c5c68;
    --pb-border-color: rgba(255, 255, 255, 0.07);
    --pb-surface: #18181b;
    --pb-positive: #4ade80;
    --pb-negative: #f87171;
    --pb-warning: #fbbf24;
    --pb-info: #38bdf8;
}

/* ===== Global Typography ===== */
body, .q-page, .q-page-container, .q-drawer, .q-card, .q-dialog {
    font-family: var(--font-body) !important;
    letter-spacing: -0.01em;
}

/* Protect Material Icons from any font overrides */
.q-icon, .material-icons, .notranslate,
[class*="material-icons"], [class*="material-symbols"] {
    font-family: 'Material Icons' !important;
}

/* Display font for headings — exclude icon elements */
.text-3xl:not(.q-icon):not(.material-icons),
.text-2xl:not(.q-icon):not(.material-icons),
.text-xl:not(.q-icon):not(.material-icons),
.text-lg:not(.q-icon):not(.material-icons),
.font-semibold:not(.q-icon):not(.material-icons),
.font-bold:not(.q-icon):not(.material-icons) {
    font-family: var(--font-display) !important;
}

/* Button text uses display font but button icons must stay Material Icons */
.q-btn .q-icon, .q-btn .material-icons {
    font-family: 'Material Icons' !important;
}

/* ===== Page Background ===== */
body {
    background: var(--q-dark-page) !important;
}

/* ===== Main Content Text ===== */
.q-page, .q-page-container {
    color: var(--pb-text-primary);
}

/* ===== Card System ===== */
.glass-card {
    background: var(--q-dark) !important;
    border: 1px solid var(--pb-border-color);
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    border-radius: var(--radius-lg);
}

.glass-card.q-card {
    background: var(--q-dark) !important;
}

/* ===== Card text colors ===== */
.glass-card .text-slate-800,
.glass-card .text-slate-700 {
    color: var(--pb-text-primary) !important;
}

.glass-card .text-slate-600,
.glass-card .text-slate-500 {
    color: var(--pb-text-muted) !important;
}

/* ===== Page titles ===== */
/* No !important on color — allows inline .style() on stat cards to win */
.text-3xl.font-bold {
    color: var(--pb-text-primary);
    letter-spacing: -0.025em;
    font-weight: 700 !important;
}

.text-xl.font-semibold {
    color: var(--pb-text-primary);
    letter-spacing: -0.015em;
    font-weight: 600 !important;
}

/* ===== Modern Progress Bar ===== */
.modern-progress {
    height: 6px;
    border-radius: 3px;
    background: rgba(148, 163, 184, 0.12);
    overflow: hidden;
}

.modern-progress .q-linear-progress__track {
    background: rgba(148, 163, 184, 0.08);
}

.modern-progress .q-linear-progress__model {
    border-radius: 4px;
}

/* Progress bar color variants */
.modern-progress.progress-success .q-linear-progress__model {
    background: linear-gradient(90deg, var(--pb-positive), var(--pb-positive));
}

.modern-progress.progress-warning .q-linear-progress__model {
    background: linear-gradient(90deg, var(--pb-warning), var(--pb-warning));
}

.modern-progress.progress-info .q-linear-progress__model {
    background: linear-gradient(90deg, var(--q-primary), var(--q-primary));
}

.modern-progress.progress-error .q-linear-progress__model {
    background: linear-gradient(90deg, var(--pb-negative), var(--pb-negative));
}

/* ===== Status Chips ===== */
.status-chip {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.status-chip-matched {
    background: rgba(34, 197, 94, 0.15);
    color: #16a34a;
}

body.body--dark .status-chip-matched {
    background: rgba(34, 197, 94, 0.25);
    color: var(--pb-positive);
}

.status-chip-missing {
    background: rgba(148, 163, 184, 0.15);
    color: #64748b;
}

body.body--dark .status-chip-missing {
    background: rgba(148, 163, 184, 0.2);
    color: var(--pb-text-muted);
}

.status-chip-error {
    background: rgba(239, 68, 68, 0.15);
    color: #dc2626;
}

body.body--dark .status-chip-error {
    background: rgba(239, 68, 68, 0.25);
    color: var(--pb-negative);
}

/* ===== Episode Row ===== */
.episode-row {
    padding: 8px 14px;
    border-radius: var(--radius);
    transition: background-color 0.12s ease;
    border-left: 3px solid transparent;
}

.episode-row:hover {
    background: rgba(148, 163, 184, 0.06);
}

/* Alternate row subtle tinting */
.episode-row:nth-child(even) {
    background: rgba(148, 163, 184, 0.02);
}

.episode-row:nth-child(even):hover {
    background: rgba(148, 163, 184, 0.07);
}

.episode-row-matched {
    border-left-color: var(--pb-positive);
}

.episode-row-missing {
    border-left-color: rgba(148, 163, 184, 0.2);
}

.episode-row-error {
    border-left-color: var(--pb-negative);
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
    border: 1px solid var(--pb-border-color);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 2px;
}

.season-section:hover {
    border-color: rgba(255, 255, 255, 0.12);
}

.season-header {
    background: rgba(148, 163, 184, 0.03);
    padding: 12px 16px;
}

/* ===== Left Sidebar ===== */
.playbook-sidebar .q-drawer__content {
    background: var(--q-dark-page) !important;
    border-right: 1px solid var(--pb-border-color) !important;
    box-shadow: none !important;
}

/* Nav item base */
.sidebar-nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 10px;
    border-radius: var(--radius);
    width: 100%;
    transition: color 0.12s ease, background 0.12s ease;
    color: var(--pb-text-muted);
    font-size: 0.8125rem;
}

.sidebar-nav-item:hover {
    background: rgba(255, 255, 255, 0.05);
    color: var(--pb-text-primary);
}

.sidebar-nav-item-active {
    background: var(--pb-primary-soft) !important;
    color: var(--q-primary) !important;
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
    border-radius: var(--radius-lg);
    padding: 16px;
    transition: border-color 0.15s ease;
}

.stat-card:hover {
    border-color: rgba(255, 255, 255, 0.12);
}

/* Stat value numbers — display font, tighter tracking */
.stat-card .text-3xl:not(.q-icon),
.stat-card .text-2xl:not(.q-icon) {
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em;
}

/* ===== Tables ===== */
.modern-table {
    border-radius: var(--radius-lg);
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
    background: var(--pb-primary-soft);
}

/* Table header styling */
.q-table thead th {
    background: transparent;
    color: var(--pb-text-muted);
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--pb-border-color);
}

body.body--dark .q-table thead th {
    background: transparent;
}

/* Table body text */
.q-table tbody td {
    color: var(--pb-text-primary);
    border-bottom: 1px solid var(--pb-border-color);
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
    background: var(--pb-primary-soft);
}

/* Table container in dark mode */
body.body--dark .q-table__container {
    background: transparent;
}

/* Remove default table borders */
.q-table--bordered thead th,
.q-table--bordered tbody td {
    border-color: var(--pb-border-color);
}

/* ===== Enhanced Log Viewer ===== */
.log-container {
    background: rgba(0, 0, 0, 0.2) !important;
    border-radius: var(--radius-lg);
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    border: 1px solid var(--pb-border-color);
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
    border-left-color: var(--q-primary);
}

/* Warning: amber tint */
.log-entry-warning {
    border-left-color: var(--pb-warning);
    background: rgba(251, 191, 36, 0.03);
}

.log-entry-warning:hover {
    background: rgba(251, 191, 36, 0.07);
}

/* Error: red tint */
.log-entry-error {
    border-left-color: var(--pb-negative);
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
    border-left-color: var(--q-primary) !important;
    background: var(--pb-primary-soft) !important;
    padding-top: 6px !important;
    padding-bottom: 6px !important;
    margin: 2px 0;
    border-radius: 0 4px 4px 0;
}

.log-entry-recap:hover {
    filter: brightness(1.08);
}

.log-entry-recap .log-msg {
    color: var(--pb-text-primary) !important;
    font-weight: 500;
}

/* Timestamp */
.log-timestamp {
    color: var(--pb-text-muted);
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
    color: var(--q-primary);
    background: var(--pb-primary-soft);
}

.log-badge-warning {
    color: var(--pb-warning);
    background: rgba(251, 191, 36, 0.14);
}

.log-badge-error {
    color: var(--pb-negative);
    background: rgba(248, 113, 113, 0.14);
}

.log-badge-debug {
    color: var(--pb-text-muted);
    background: rgba(148, 163, 184, 0.1);
}

/* Message text */
.log-msg {
    font-size: 12px;
    line-height: 20px;
    color: var(--pb-text-secondary);
    white-space: nowrap;
    min-width: 0;
}

.log-msg-info {
    color: var(--pb-text-primary);
}

.log-msg-warning {
    color: #fcd34d;
}

.log-msg-error {
    color: #fca5a5;
}

.log-msg-debug {
    color: var(--pb-text-muted);
}

.log-empty {
    color: var(--pb-text-muted);
}

.log-footer {
    color: var(--pb-text-muted);
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
    color: var(--pb-text-primary);
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
    color: var(--pb-text-primary);
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}

.log-pill-label {
    font-size: 9px;
    color: var(--pb-text-muted);
}

.log-pill-accent {
    background: var(--pb-primary-soft);
    border-color: transparent;
}

.log-pill-accent .log-pill-value {
    color: var(--q-primary);
}

.log-pill-warning {
    background: rgba(251, 191, 36, 0.1);
    border-color: rgba(251, 191, 36, 0.15);
}

.log-pill-warning .log-pill-value {
    color: var(--pb-warning);
}

.log-pill-error {
    background: rgba(248, 113, 113, 0.1);
    border-color: rgba(248, 113, 113, 0.15);
}

.log-pill-error .log-pill-value {
    color: var(--pb-negative);
}

/* Processing Details — source file + destination meta */
.log-processing-source {
    font-size: 12px;
    font-weight: 500;
    color: var(--pb-text-primary);
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.log-processing-meta {
    font-size: 11px;
    color: var(--pb-text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.log-detail-dest {
    color: var(--pb-text-secondary);
}

.log-detail-tag {
    display: inline-block;
    padding: 0 5px;
    border-radius: 3px;
    background: rgba(148, 163, 184, 0.08);
    color: var(--pb-text-muted);
    font-size: 10px;
}

.log-detail-upgrade {
    background: var(--pb-primary-soft);
    color: var(--q-primary);
}

.log-detail-action {
    color: var(--pb-text-muted);
    font-size: 10px;
}

/* Summary / generic block — inline title + stats */
.log-summary-content {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--pb-text-secondary);
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
    color: var(--pb-text-muted);
    opacity: 0.4;
}

/* ===== Expansion Panels ===== */
.q-expansion-item {
    border-radius: var(--radius);
    overflow: hidden;
}

.q-expansion-item__container {
    border-radius: var(--radius);
}

/* ===== Scrollbar Styling ===== */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
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
    outline: 2px solid var(--q-primary);
    outline-offset: 2px;
}

body.body--dark *:focus-visible {
    outline-color: var(--q-primary);
}

/* ===== Quasar Component Overrides for Dark Mode ===== */
body.body--dark .q-table {
    background: transparent;
}

body.body--dark .q-table th,
body.body--dark .q-table td {
    color: var(--pb-text-primary);
}

body.body--dark .q-field__label,
body.body--dark .q-field__native,
body.body--dark .q-select__dropdown-icon {
    color: var(--pb-text-primary);
}

body.body--dark .q-checkbox__label {
    color: var(--pb-text-primary);
}

body.body--dark .q-expansion-item__toggle-icon {
    color: var(--pb-text-muted);
}

/* ===== Link Colors ===== */
a {
    color: var(--q-primary);
}

a:hover {
    color: var(--q-primary);
}

/* ===== Settings Page Styles ===== */
.settings-page-shell {
    min-height: calc(100vh - 32px);
}

.settings-main-layout {
    align-items: flex-start;
}

.settings-sidebar {
    border-right: 1px solid var(--pb-border-color);
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
    gap: 10px;
    width: 100%;
    transition: color 0.12s ease, background 0.12s ease;
    border-radius: var(--radius);
    color: var(--pb-text-muted) !important;
    background: transparent !important;
    border: 1px solid transparent;
    font-size: 0.8125rem;
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
    background: var(--q-dark) !important;
    border: 1px solid var(--pb-border-color) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
}

.view-shell {
    min-height: calc(100vh - 24px);
}

.settings-surface .q-expansion-item,
.settings-surface .q-expansion-item__container {
    border-radius: 8px;
}

.settings-inline-card {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: var(--radius) !important;
    box-shadow: none !important;
}

.settings-modal-card {
    background: var(--q-dark) !important;
}

.settings-theme-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: var(--radius-lg);
    box-shadow: none;
}

.settings-theme-card-active {
    border-color: var(--q-primary) !important;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06), 0 0 0 1px var(--pb-primary-soft) !important;
}

/* Settings form inputs */
.settings-input .q-field__control {
    min-height: 36px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: var(--radius);
}

.settings-input .q-field__label {
    font-size: 0.875rem;
}

body.body--dark .settings-input .q-field__control::before {
    border-color: rgba(255, 255, 255, 0.16) !important;
}

body.body--dark .settings-input.q-field--focused .q-field__control::before,
body.body--dark .settings-input.q-field--focused .q-field__control::after {
    border-color: var(--q-primary) !important;
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
    color: var(--q-primary);
}

/* Buttons scoped to settings header actions */
.settings-action-primary {
    background: var(--q-primary) !important;
    color: #f8fafc !important;
    border: 1px solid var(--q-primary) !important;
}

.settings-action-primary.bg-primary {
    background: var(--q-primary) !important;
}

.settings-action-primary .q-btn__content,
.settings-action-primary .q-icon {
    color: #f8fafc !important;
}

.settings-action-primary:hover {
    background: var(--q-primary) !important;
    border-color: var(--q-primary) !important;
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
    border-radius: var(--radius) !important;
    font-family: var(--font-body) !important;
    font-weight: 500;
    letter-spacing: -0.01em;
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
    background: var(--q-primary) !important;
    border: 1px solid var(--q-primary) !important;
    color: #f8fafc !important;
}

.app-btn-primary.bg-primary {
    background: var(--q-primary) !important;
}

.app-btn-primary .q-btn__content,
.app-btn-primary .q-icon {
    color: #f8fafc !important;
}

.app-btn-primary:hover {
    background: var(--q-primary) !important;
    border-color: var(--q-primary) !important;
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
    letter-spacing: -0.005em !important;
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
}

/* App-wide chips and badges */
.app-chip {
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.10);
    color: var(--pb-text-secondary) !important;
    background: transparent !important;
    padding: 3px 8px;
    font-size: 0.8125rem;
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
    background: var(--pb-primary-soft) !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
    color: var(--q-primary) !important;
}

.app-badge {
    border-radius: 4px;
    border: 1px solid transparent;
    padding: 3px 8px !important;
    font-size: 0.75rem !important;
    line-height: 1.2 !important;
    font-weight: 500;
}

/* Reset Quasar's badge background for app-badge elements.
   Quasar sets background-color: var(--q-primary) on .q-badge and
   background: var(--q-primary) !important on .bg-primary.
   This single rule resets both, then variant classes below set the right colors. */
.q-badge.app-badge {
    background: transparent !important;
    color: var(--pb-text-primary);
}

.app-badge-muted {
    background: rgba(255, 255, 255, 0.10) !important;
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: rgba(255, 255, 255, 0.8) !important;
}

.app-badge-warning {
    background: rgba(251, 191, 36, 0.14) !important;
    border: 1px solid rgba(251, 191, 36, 0.25);
    color: #fcd34d !important;
}

.app-badge-success {
    background: rgba(74, 222, 128, 0.14) !important;
    border: 1px solid rgba(74, 222, 128, 0.25);
    color: #86efac !important;
}

.app-badge-danger {
    background: rgba(248, 113, 113, 0.14) !important;
    border: 1px solid rgba(248, 113, 113, 0.25);
    color: #fca5a5 !important;
}

/* Semantic icon tones */
.app-stat-icon-accent {
    color: var(--q-primary);
}

.app-stat-icon-warning {
    color: var(--pb-warning);
}

.app-stat-icon-muted {
    color: rgba(255, 255, 255, 0.56);
}

.app-text-accent {
    color: var(--q-primary);
}

.app-text-success {
    color: var(--pb-positive);
}

.app-text-warning {
    color: var(--pb-warning);
}

.app-text-danger {
    color: var(--pb-negative);
}

.app-text-muted {
    color: var(--pb-text-muted);
}

.app-link {
    color: var(--q-primary);
}

.app-link:hover {
    color: var(--q-primary);
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
    color: var(--pb-text-primary) !important;
}

.view-shell .text-slate-600,
.settings-page-shell .text-slate-600,
.q-dialog .text-slate-600 {
    color: var(--pb-text-secondary) !important;
}

.view-shell .text-slate-500,
.view-shell .text-slate-400,
.settings-page-shell .text-slate-500,
.settings-page-shell .text-slate-400,
.q-dialog .text-slate-500,
.q-dialog .text-slate-400 {
    color: var(--pb-text-muted) !important;
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
    color: var(--pb-text-primary) !important;
}

/* Divider color override */
.view-shell .divide-slate-100 > :not(:first-child),
.view-shell .divide-slate-800 > :not(:first-child) {
    border-color: var(--pb-border-color) !important;
}

/* ===== Stat Card Visual Hierarchy ===== */
/* Border-top and value colors are applied via inline .style() in Python
   to bypass Quasar/NiceGUI CSS specificity issues. */

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
.app-alert-success { border-left: 3px solid var(--pb-positive); }
.app-alert-warning { border-left: 3px solid var(--pb-warning); }
.app-alert-danger  { border-left: 3px solid var(--pb-negative); }
.app-alert-info    { border-left: 3px solid var(--q-primary); }

/* ===== Episode Row Hover Enhancements ===== */
.episode-row-matched:hover {
    background: rgba(74, 222, 128, 0.06);
    box-shadow: inset 3px 0 0 var(--pb-positive);
}

.episode-row-error:hover {
    background: rgba(248, 113, 113, 0.06);
    box-shadow: inset 3px 0 0 var(--pb-negative);
}

/* ===== Unmatched File Card Status Classes ===== */
.file-card-warning { border-left: 3px solid var(--pb-warning); }
.file-card-accent  { border-left: 3px solid var(--q-primary); }
.file-card-muted   { border-left: 3px solid rgba(148, 163, 184, 0.4); }

/* ===== Match Attempt Card Classes ===== */
.match-attempt-green {
    border-left: 3px solid var(--pb-positive);
    background: rgba(74, 222, 128, 0.05);
    border-radius: var(--radius);
    padding: 8px;
}

.match-attempt-amber {
    border-left: 3px solid var(--pb-warning);
    background: rgba(251, 191, 36, 0.05);
    border-radius: var(--radius);
    padding: 8px;
}

.match-attempt-slate {
    border-left: 3px solid rgba(148, 163, 184, 0.3);
    background: rgba(148, 163, 184, 0.03);
    border-radius: var(--radius);
    padding: 8px;
}

.match-attempt-green .match-attempt-icon { color: var(--pb-positive); }
.match-attempt-amber .match-attempt-icon { color: var(--pb-warning); }
.match-attempt-slate .match-attempt-icon { color: var(--pb-text-muted); }

/* ===== Global Hover / Transition Polish ===== */
.glass-card {
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.15s ease;
}

/* Expansion panel headers get subtle hover bg */
.q-expansion-item .q-item:hover {
    background: rgba(148, 163, 184, 0.06);
}

.season-section .q-expansion-item .q-item {
    padding: 8px 16px;
    min-height: 48px;
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
        border-bottom: 1px solid var(--pb-border-color) !important;
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
        border-top: 1px solid var(--pb-border-color);
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
    """Inject the Playbook CSS styles and custom fonts into the page head."""
    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300..700;1,9..40,300..700&family=Anybody:wght@600..900&display=swap" rel="stylesheet">'
        f"<style>{PLAYBOOK_CSS}</style>"
    )


# Script to apply dark mode and theme colors immediately to prevent FOUC.
# Sets --q-dark-page and --q-dark from localStorage BEFORE NiceGUI connects.
THEME_INIT_SCRIPT = """
<script>
(function() {
    // Strip bg-primary from app-badge elements — Quasar adds it automatically
    // and its !important background overrides our variant colors.
    new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            m.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) {
                    node.querySelectorAll && node.querySelectorAll('.app-badge.bg-primary').forEach(function(el) {
                        el.classList.remove('bg-primary');
                        el.classList.remove('text-white');
                    });
                    if (node.classList && node.classList.contains('app-badge') && node.classList.contains('bg-primary')) {
                        node.classList.remove('bg-primary');
                        node.classList.remove('text-white');
                    }
                }
            });
        });
    }).observe(document.body || document.documentElement, { childList: true, subtree: true });

    var theme = localStorage.getItem('playbook-color-theme') || 'swizzin';
    // Theme-specific Quasar dark colors (must match themes.py definitions)
    var themes = {
        'swizzin':    { darkPage: '#0a0a0c', dark: '#111114' },
        'catppuccin': { darkPage: '#181825', dark: '#1e1e2e' },
    };
    var c = themes[theme] || themes['swizzin'];
    document.body.classList.add('body--dark');
    document.documentElement.style.setProperty('--q-dark-page', c.darkPage);
    document.documentElement.style.setProperty('--q-dark', c.dark);
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
    """Apply a complete GUI theme using Quasar's color system + CSS extensions.

    This calls ui.colors() to set Quasar brand colors (--q-primary, --q-dark, etc.)
    so that ALL Quasar components (buttons, drawers, toggles, cards) automatically
    follow the theme. Then syncs --pb-* CSS custom properties for things Quasar
    doesn't cover natively (text colors, borders, soft backgrounds).
    """
    from .themes import CSS_KEYS, get_quasar_colors, get_theme

    theme = get_theme(theme_name)

    # 1. Set Quasar brand colors — this is what makes everything shift
    ui.colors(**get_quasar_colors(theme))

    # 2. Sync CSS custom properties for non-Quasar styling
    css_props = {k: v for k, v in theme.items() if k in CSS_KEYS}
    js_lines = []
    for key, value in css_props.items():
        prop_name = f"--pb-{key.replace('_', '-')}"
        js_lines.append(f"s.setProperty('{prop_name}', '{value}');")

    name = theme_name.strip().lower() if theme_name else "swizzin"
    js_lines.append(f"localStorage.setItem('playbook-color-theme', '{name}');")

    js_code = "const s = document.documentElement.style;\n" + "\n".join(js_lines)
    ui.run_javascript(js_code)
