PAGE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MiddAI - Self-Hosted AI from Middae</title>
  <link rel="icon" href="/assets/favicon.ico?v=3" sizes="any">
  <link rel="shortcut icon" href="/assets/favicon.ico?v=3">
  <style>
    *,
    *::before,
    *::after {
      box-sizing: border-box;
    }

    :root {
      --bg: #0b1117;
      --panel: #111827;
      --panel-soft: #0f172a;
      --panel-raised: #172033;
      --text: #e5e7eb;
      --muted: #94a3b8;
      --line: #243244;
      --user: #2563eb;
      --user-soft: #1d4ed8;
      --assistant: #111827;
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.14);
      --danger: #ef4444;
      --shadow: 0 22px 60px rgba(0, 0, 0, 0.35);
    }

    * {
      box-sizing: border-box;
    }

    html,
    body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
    }

    body {
      min-height: 100%;
      background:
        radial-gradient(circle at 16% 0%, rgba(56, 189, 248, 0.10), transparent 30rem),
        radial-gradient(circle at 86% 12%, rgba(37, 99, 235, 0.08), transparent 28rem),
        linear-gradient(180deg, #0b1117 0%, #081018 100%);
      color: var(--text);
      font-family: Inter, "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    }

    .side-frame {
      position: fixed;
      top: 0;
      bottom: 0;
      z-index: 0;
      width: min(170px, 12vw);
      height: 100vh;
      object-fit: fill;
      pointer-events: none;
      user-select: none;
      display: none;
      opacity: 0.06;
      filter: saturate(0.85);
    }

    .side-frame.left {
      left: 0;
      object-position: left center;
    }

    .side-frame.right {
      right: 0;
      object-position: right center;
    }

    .shell {
      --sidebar-width: clamp(210px, 15vw, 300px);
      position: relative;
      z-index: 1;
      height: 100vh;
      max-height: 100vh;
      display: grid;
      grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
      grid-template-rows: minmax(0, 1fr) auto auto;
      width: 100%;
      max-width: none;
      margin: 0;
      padding: clamp(12px, 1.15vw, 24px);
      gap: 12px;
      overflow: hidden;
    }

    .status {
      min-height: 32px;
      display: inline-flex;
      align-items: center;
      border: 1px solid rgba(56, 189, 248, 0.18);
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.74);
      color: var(--text);
      font-size: 14px;
      white-space: nowrap;
      padding: 6px 11px;
    }

    .controls {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      min-width: 0;
      justify-content: flex-start;
    }

    .button-group + .button-group {
      margin-left: 14px;
    }

    .button-group {
      display: flex;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.82);
      overflow: hidden;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }

    .toggle-button {
      min-width: 72px;
      border: 0;
      border-radius: 0;
      border-right: 1px solid var(--line);
      background: transparent;
      color: var(--text);
      font: inherit;
      font-size: 14px;
      font-weight: 650;
      cursor: pointer;
      padding: 9px 13px;
      transition: background 140ms ease, color 140ms ease;
    }

    .toggle-button:last-child {
      border-right: 0;
    }

    .toggle-button.active {
      background: var(--user);
      color: #ffffff;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }

    .toggle-button:hover:not(.active) {
      background: rgba(56, 189, 248, 0.09);
      color: #ffffff;
    }

    .toggle-button:focus {
      outline: 2px solid rgba(56, 189, 248, 0.36);
      outline-offset: -2px;
    }

    .footer-row {
      grid-column: 2;
      grid-row: 3;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 12px;
      min-height: 38px;
      min-width: 0;
      width: min(calc(100% - clamp(56px, 10vw, 240px)), 1260px);
      justify-self: center;
      margin-right: 0;
    }

    .footer-left,
    .footer-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .footer-left {
      min-width: 0;
      flex: 1 1 auto;
    }

    .footer-right {
      flex: 0 0 auto;
      justify-content: flex-end;
    }

    .workspace {
      min-height: 0;
      min-width: 0;
      display: contents;
    }

    .side-panel {
      grid-column: 1;
      grid-row: 1 / 4;
      min-height: 0;
      min-width: 0;
      display: grid;
      grid-template-rows: auto auto auto auto minmax(0, 1fr);
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: rgba(15, 23, 42, 0.82);
      box-shadow: 0 18px 46px rgba(0, 0, 0, 0.28);
    }

    .sidebar-brand {
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px 8px;
    }

    .sidebar-brand-mark {
      width: 28px;
      height: 28px;
      object-fit: contain;
      flex: 0 0 auto;
    }

    .sidebar-brand-name {
      min-width: 0;
      color: var(--text);
      font-size: 18px;
      font-weight: 800;
      line-height: 1;
    }

    .sidebar-new-chat {
      min-height: 34px;
      margin: 0 10px 8px;
      display: grid;
      grid-template-columns: 20px 1fr;
      align-items: center;
      gap: 7px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel-soft);
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
      text-align: left;
      padding: 0 10px;
    }

    .sidebar-new-chat:hover,
    .sidebar-new-chat:focus {
      border-color: var(--accent);
      background: var(--accent-soft);
      outline: 0;
    }

    .sidebar-tabs {
      display: grid;
      grid-template-columns: 1fr;
      gap: 3px;
      padding: 0 9px 8px;
      border-bottom: 1px solid var(--line);
    }

    .sidebar-tab {
      min-width: 0;
      min-height: 31px;
      display: grid;
      grid-template-columns: 20px 1fr;
      align-items: center;
      gap: 7px;
      border: 1px solid transparent;
      border-radius: 10px;
      background: transparent;
      color: var(--text);
      font-size: 13px;
      font-weight: 700;
      padding: 0 8px;
      text-align: left;
    }

    .sidebar-tab:hover,
    .sidebar-tab:focus {
      border-color: var(--line);
      background: rgba(56, 189, 248, 0.09);
      outline: 0;
    }

    .sidebar-tab.active,
    .sidebar-tab.active:hover,
    .sidebar-tab.active:focus {
      background: var(--user);
      border-color: rgba(96, 165, 250, 0.68);
      color: #ffffff;
      outline: 0;
    }

    .sidebar-tab.active .sidebar-tab-icon {
      color: #ffffff;
    }

    .sidebar-quit {
      margin-top: 3px;
    }

    .sidebar-tab-icon {
      width: 19px;
      height: 19px;
      display: grid;
      place-items: center;
      color: var(--text);
      font-weight: 900;
    }

    .sidebar-tab-icon svg {
      width: 17px;
      height: 17px;
      display: block;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .sidebar-panel-header {
      min-width: 0;
      min-height: 30px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 28px 28px;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      border-bottom: 1px solid var(--line);
    }

    .sidebar-panel-title {
      min-width: 0;
      color: var(--text);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .sidebar-panel-add,
    .sidebar-panel-more {
      min-width: 0;
      width: 28px;
      height: 28px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 9px;
      background: var(--panel-soft);
      color: var(--text);
      font-size: 15px;
      font-weight: 900;
      line-height: 1;
      padding: 0;
    }

    .sidebar-panel-add:hover,
    .sidebar-panel-add:focus,
    .sidebar-panel-more:hover,
    .sidebar-panel-more:focus {
      border-color: var(--accent);
      background: var(--accent-soft);
      outline: 0;
    }

    .sidebar-panel-add[hidden],
    .sidebar-panel-more[hidden] {
      display: none;
    }

    .sidebar-body {
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 8px;
      scrollbar-color: #334155 transparent;
    }

    .sidebar-section {
      display: grid;
      gap: 6px;
      margin-bottom: 10px;
    }

    .sidebar-heading {
      margin: 0;
      color: var(--text);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .sidebar-list {
      display: grid;
      gap: 2px;
    }

    .sidebar-list-row {
      width: 100%;
      min-width: 0;
      min-height: 34px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 32px;
      align-items: center;
      gap: 4px;
      border: 1px solid transparent;
      border-radius: 9px;
      background: transparent;
      color: var(--text);
      overflow: visible;
      padding: 1px 3px 1px 8px;
    }

    .sidebar-list-row:hover,
    .sidebar-list-row:focus-within {
      border-color: var(--line);
      background: rgba(56, 189, 248, 0.09);
    }

    .sidebar-list-row.active,
    .sidebar-list-row.active:hover,
    .sidebar-list-row.active:focus-within {
      border-color: rgba(96, 165, 250, 0.78);
      background: var(--user);
      color: #ffffff;
    }

    .sidebar-list-main {
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      border: 0;
      background: transparent;
      color: inherit;
      font: inherit;
      text-align: left;
      cursor: pointer;
      padding: 0;
    }

    .sidebar-list-title {
      min-width: 0;
      flex: 1 1 auto;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--text);
      font-size: 12px;
      font-weight: 700;
    }

    .sidebar-list-meta {
      flex: 0 0 auto;
      max-width: 92px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--muted);
      font-size: 10px;
      font-weight: 700;
    }

    .sidebar-list-row.active .sidebar-list-title,
    .sidebar-list-row.active .sidebar-list-meta {
      color: #ffffff;
    }

    .sidebar-row-action {
      width: 32px;
      min-width: 32px;
      height: 32px;
      min-height: 32px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      position: relative;
      border: 0;
      border-radius: 8px;
      background: transparent;
      color: #d8e6ff;
      opacity: 1;
      visibility: visible;
      line-height: 1;
      padding: 0;
      cursor: pointer;
      z-index: 2;
    }

    .sidebar-panel-more svg,
    .sidebar-row-action svg {
      display: none !important;
    }

    .sidebar-panel-more::before,
    .sidebar-row-action::before {
      content: "";
      width: 18px;
      height: 4px;
      display: block;
      border-radius: 999px;
      background:
        radial-gradient(circle, currentColor 0 2px, transparent 2.2px) 0 0 / 4px 4px no-repeat,
        radial-gradient(circle, currentColor 0 2px, transparent 2.2px) 7px 0 / 4px 4px no-repeat,
        radial-gradient(circle, currentColor 0 2px, transparent 2.2px) 14px 0 / 4px 4px no-repeat;
    }

    .sidebar-action-popover {
      position: fixed;
      z-index: 60;
      min-width: 108px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(15, 23, 42, 0.98);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.35);
      padding: 6px;
    }

    .sidebar-action-popover[hidden] {
      display: none;
    }

    .sidebar-action-popover button {
      width: 100%;
      min-height: 30px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
      color: var(--text);
      font-size: 12px;
      font-weight: 900;
      padding: 0 10px;
    }

    .sidebar-action-popover button:hover,
    .sidebar-action-popover button:focus {
      background: var(--accent-soft);
      border-color: var(--accent);
      outline: 0;
    }

    .sidebar-action-popover button.danger {
      border-color: rgba(239, 68, 68, 0.45);
      background: rgba(239, 68, 68, 0.16);
      color: #fecaca;
    }

    .sidebar-action-popover button.danger:hover,
    .sidebar-action-popover button.danger:focus {
      background: rgba(239, 68, 68, 0.28);
      border-color: var(--danger);
    }

    .sidebar-row-action:hover,
    .sidebar-row-action:focus {
      background: rgba(56, 189, 248, 0.11);
      color: #ffffff;
      outline: 0;
    }

    .sidebar-list-row.active .sidebar-row-action {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.13);
    }

    .sidebar-list-row.active .sidebar-row-action:hover,
    .sidebar-list-row.active .sidebar-row-action:focus {
      background: rgba(255, 255, 255, 0.22);
    }

    .sidebar-item {
      width: 100%;
      min-width: 0;
      display: grid;
      gap: 5px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.72);
      color: var(--text);
      cursor: pointer;
      padding: 10px;
      text-align: left;
    }

    .sidebar-item:hover,
    .sidebar-item:focus {
      border-color: var(--accent);
      background: rgba(56, 189, 248, 0.11);
      outline: 0;
    }

    .sidebar-item.active,
    .sidebar-item.active:hover,
    .sidebar-item.active:focus {
      border-color: rgba(96, 165, 250, 0.78);
      background: var(--user);
      color: #ffffff;
      outline: 0;
    }

    .sidebar-item-title {
      color: var(--text);
      font-size: 13px;
      font-weight: 700;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }

    .sidebar-item-meta,
    .sidebar-item-preview {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }

    .sidebar-empty {
      border: 1px dashed var(--line);
      border-radius: 12px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      padding: 12px;
    }

    .settings-field {
      display: grid;
      gap: 7px;
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
    }

    .settings-control-panel {
      gap: 0;
    }

    .settings-control-panel > .sidebar-heading {
      margin-bottom: 7px;
    }

    .settings-runtime-summary {
      display: grid;
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      background: rgba(8, 15, 28, 0.42);
    }

    .settings-runtime-row {
      min-width: 0;
      display: grid;
      grid-template-columns: 54px minmax(0, 1fr);
      gap: 8px;
      padding: 7px 2px;
      font-size: 12px;
      line-height: 1.3;
    }

    .settings-runtime-row + .settings-runtime-row {
      border-top: 1px solid rgba(51, 65, 85, 0.55);
    }

    .settings-runtime-key {
      color: var(--muted);
      font-weight: 700;
    }

    .settings-runtime-value {
      min-width: 0;
      color: var(--text);
      font-weight: 700;
      overflow-wrap: anywhere;
    }

    .settings-control-panel > .settings-field,
    .settings-control-panel > .settings-toggle-field {
      padding: 10px 2px;
      border-bottom: 1px solid rgba(51, 65, 85, 0.64);
    }

    .settings-label-header {
      min-width: 0;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }

    .settings-help {
      position: relative;
      min-width: 15px;
      width: 15px;
      min-height: 15px;
      height: 15px;
      flex: 0 0 15px;
      border: 1px solid var(--line);
      border-radius: 2px;
      background: #111827;
      color: #cbd5e1;
      padding: 0;
      font-family: "Segoe UI", sans-serif;
      font-size: 10px;
      font-weight: 700;
      line-height: 13px;
      text-align: center;
      cursor: help;
    }

    .settings-help:hover,
    .settings-help:focus-visible {
      border-color: #64748b;
      background: #1e293b;
      color: #ffffff;
      outline: 0;
    }

    .settings-tooltip {
      position: fixed;
      z-index: 140;
      width: 210px;
      border: 1px solid var(--line);
      border-radius: 2px;
      background: #0b1220;
      color: var(--text);
      padding: 7px 8px;
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.42);
      font-size: 11px;
      font-weight: 600;
      line-height: 1.35;
      text-align: left;
      white-space: normal;
      pointer-events: none;
    }

    .settings-input {
      min-width: 0;
      width: 100%;
      min-height: 30px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: var(--panel-soft);
      color: var(--text);
      padding: 0 8px;
      font: inherit;
    }

    .settings-input:focus {
      border-color: var(--accent);
      outline: 0;
    }

    .settings-range-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 72px;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .settings-slider {
      width: 100%;
      accent-color: var(--user);
    }

    .settings-slider:disabled,
    .settings-input:disabled {
      cursor: not-allowed;
      opacity: 0.45;
    }

    .settings-range-meta {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      line-height: 1.35;
    }

    .settings-toggle-field {
      display: grid;
      gap: 5px;
    }

    .settings-toggle-row {
      min-width: 0;
      min-height: 30px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
    }

    .settings-switch {
      position: relative;
      width: 38px;
      height: 20px;
      flex: 0 0 38px;
    }

    .settings-switch input {
      position: absolute;
      width: 1px;
      height: 1px;
      opacity: 0;
      pointer-events: none;
    }

    .settings-switch-track {
      position: absolute;
      inset: 0;
      border: 1px solid var(--line);
      border-radius: 3px;
      background: var(--panel-soft);
      cursor: pointer;
      transition: background 160ms ease, border-color 160ms ease;
    }

    .settings-switch-track::after {
      content: "";
      position: absolute;
      top: 3px;
      left: 3px;
      width: 12px;
      height: 12px;
      border-radius: 2px;
      background: var(--muted);
      transition: transform 160ms ease, background 160ms ease;
    }

    .settings-switch input:checked + .settings-switch-track {
      border-color: rgba(56, 189, 248, 0.7);
      background: var(--user);
    }

    .settings-switch input:checked + .settings-switch-track::after {
      transform: translateX(18px);
      background: #ffffff;
    }

    .settings-switch input:focus-visible + .settings-switch-track {
      outline: 2px solid rgba(56, 189, 248, 0.38);
      outline-offset: 2px;
    }

    .settings-switch input:disabled + .settings-switch-track {
      cursor: default;
      opacity: 0.45;
    }

    .settings-save-button {
      min-width: 0;
      min-height: 34px;
      border: 1px solid rgba(56, 189, 248, 0.42);
      border-radius: 4px;
      background: var(--user);
      color: #ffffff;
      cursor: pointer;
      font: inherit;
      font-size: 13px;
      font-weight: 900;
      padding: 0 12px;
      margin-top: 10px;
    }

    .settings-save-button:hover:not(:disabled),
    .settings-save-button:focus:not(:disabled) {
      background: var(--user-soft);
      outline: 2px solid rgba(56, 189, 248, 0.34);
      outline-offset: 2px;
    }

    .settings-save-button:disabled {
      cursor: default;
      opacity: 0.52;
    }

    .settings-progress {
      display: none;
      gap: 7px;
    }

    .settings-progress.visible {
      display: grid;
    }

    .settings-progress-label {
      color: var(--text);
      font-size: 12px;
      font-weight: 900;
    }

    .settings-progress-track {
      width: 100%;
      height: 10px;
      overflow: hidden;
      border: 1px solid rgba(56, 189, 248, 0.28);
      border-radius: 3px;
      background: rgba(15, 23, 42, 0.92);
    }

    .settings-progress-fill {
      width: 0%;
      height: 100%;
      border-radius: 2px;
      background: linear-gradient(90deg, #2563eb, #38bdf8);
      transition: width 180ms ease;
    }

    .settings-warning {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }

    .settings-warning.danger {
      color: #f87171;
      font-weight: 800;
    }

    .sidebar-actions {
      display: none;
    }

    .sidebar-action {
      min-width: 0;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      color: var(--text);
      font-size: 13px;
      padding: 0 10px;
    }

    .sidebar-action:hover:not(:disabled),
    .sidebar-action:focus:not(:disabled) {
      border-color: var(--accent);
      background: var(--accent-soft);
      outline: 0;
    }

    .sidebar-action.danger:hover:not(:disabled),
    .sidebar-action.danger:focus:not(:disabled) {
      border-color: var(--danger);
      background: rgba(239, 68, 68, 0.13);
    }

    .sidebar-actions.memory-mode .chat-action,
    .sidebar-actions.chat-mode .memory-action {
      display: none;
    }

    main {
      grid-column: 2;
      grid-row: 1;
      min-height: 0;
      min-width: 0;
      overflow-y: auto;
      overflow-x: hidden;
      background: rgba(15, 23, 42, 0.74);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 18px 46px rgba(0, 0, 0, 0.25);
      padding: 20px;
      scrollbar-color: #334155 transparent;
    }

    .messages {
      display: flex;
      flex-direction: column;
      gap: 18px;
      min-width: 0;
    }

    .message-row {
      display: flex;
      align-items: flex-end;
      gap: 10px;
      width: 100%;
      min-width: 0;
    }

    .message-row.user {
      justify-content: flex-end;
    }

    .message-row.assistant {
      justify-content: flex-start;
      padding-left: 16px;
    }

    .message-row.user .message {
      order: 1;
    }

    .message-row.user .avatar {
      order: 2;
    }

    .avatar {
      width: 72px;
      height: 72px;
      flex: 0 0 72px;
      object-fit: contain;
      object-position: center bottom;
      align-self: flex-end;
      filter: drop-shadow(0 10px 14px rgba(0, 0, 0, 0.28));
    }

    .me-avatar {
      width: 42px;
      height: 42px;
      flex-basis: 42px;
      display: grid;
      place-items: center;
      border: 1px solid rgba(56, 189, 248, 0.34);
      border-radius: 999px;
      background: linear-gradient(180deg, #1e3a8a, #1d4ed8);
      color: #ffffff;
      font-size: 13px;
      font-weight: 800;
      filter: none;
    }

    .message {
      min-width: 0;
      max-width: min(920px, calc(100% - 72px));
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 14px 16px;
      line-height: 1.5;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      box-shadow: 0 10px 26px rgba(0, 0, 0, 0.14);
    }

    .message.user {
      align-self: flex-end;
      background: var(--user);
      border-color: rgba(96, 165, 250, 0.42);
      color: #ffffff;
    }

    .message.assistant {
      align-self: flex-start;
      background: rgba(17, 24, 39, 0.72);
      color: var(--text);
    }

    .sources {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid var(--line);
      display: grid;
      gap: 6px;
      font-size: 13px;
      white-space: normal;
    }

    .sources a {
      color: var(--text);
      text-decoration: underline;
      text-decoration-color: rgba(148, 163, 184, 0.58);
      text-underline-offset: 3px;
      overflow-wrap: anywhere;
    }

    .sources a:hover {
      text-decoration-color: #ffffff;
    }

    .image-results {
      margin-top: 12px;
      max-width: 720px;
      padding-top: 8px;
      border-top: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 5px;
      white-space: normal;
    }

    .image-thumb {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.78);
      color: var(--text);
      cursor: pointer;
      display: grid;
      overflow: hidden;
      padding: 0;
      text-align: left;
    }

    .image-thumb:hover,
    .image-thumb:focus {
      outline: 2px solid rgba(56, 189, 248, 0.55);
      outline-offset: -2px;
    }

    .image-thumb img {
      width: 100%;
      height: 92px;
      display: block;
      object-fit: cover;
      background: rgba(15, 23, 42, 0.9);
    }

    .image-thumb span {
      min-height: 30px;
      padding: 4px 6px;
      color: var(--text);
      font-size: 11px;
      font-weight: 700;
      line-height: 1.25;
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }

    .image-modal {
      position: fixed;
      inset: 0;
      z-index: 20;
      display: none;
      align-items: center;
      justify-content: center;
      background: rgba(2, 6, 23, 0.78);
      padding: 22px;
    }

    .image-modal.open {
      display: flex;
    }

    .image-modal-panel {
      width: min(820px, calc(100vw - 32px));
      max-height: calc(100vh - 32px);
      overflow: auto;
      border: 1px solid rgba(35, 183, 255, 0.42);
      border-radius: 16px;
      background: var(--panel);
      box-shadow: 0 24px 70px rgba(0, 0, 0, 0.38);
    }

    .image-modal-preview {
      width: 100%;
      max-height: 68vh;
      display: block;
      object-fit: contain;
      background: #020617;
    }

    .image-modal-body {
      display: grid;
      gap: 12px;
      padding: 14px;
    }

    .image-modal-title {
      margin: 0;
      color: var(--text);
      font-size: 16px;
      font-weight: 700;
      line-height: 1.3;
    }

    .image-modal-source {
      color: var(--muted);
      font-size: 13px;
      overflow-wrap: anywhere;
    }

    .image-modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }

    .image-modal-actions a,
    .image-modal-actions button {
      min-width: 92px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      color: var(--text);
      cursor: pointer;
      font: inherit;
      font-size: 14px;
      font-weight: 700;
      padding: 9px 12px;
      text-align: center;
      text-decoration: none;
    }

    .image-modal-actions a:hover,
    .image-modal-actions button:hover,
    .image-modal-actions a:focus,
    .image-modal-actions button:focus {
      outline: 2px solid rgba(56, 189, 248, 0.55);
      outline-offset: -2px;
    }

    .app-modal {
      position: fixed;
      inset: 0;
      z-index: 30;
      display: none;
      align-items: center;
      justify-content: center;
      background: rgba(2, 6, 23, 0.78);
      padding: 22px;
    }

    .app-modal.open {
      display: flex;
    }

    .app-modal-panel {
      width: min(460px, calc(100vw - 32px));
      border: 1px solid rgba(56, 189, 248, 0.34);
      border-radius: 16px;
      background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
      box-shadow: 0 24px 70px rgba(0, 0, 0, 0.45);
      padding: 18px;
    }

    .app-modal-title {
      margin: 0;
      color: var(--text);
      font-size: 18px;
      font-weight: 800;
      line-height: 1.25;
    }

    .app-modal-message {
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
      white-space: pre-line;
    }

    .app-modal-input {
      width: 100%;
      min-height: 110px;
      margin-top: 14px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #020617;
      color: var(--text);
      font: inherit;
      font-size: 14px;
      line-height: 1.45;
      padding: 11px 12px;
      outline: none;
    }

    .app-modal-input:focus {
      border-color: rgba(56, 189, 248, 0.72);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.14);
    }

    .assistant-editor-panel {
      width: min(760px, calc(100vw - 32px));
      max-height: calc(100vh - 48px);
      overflow-y: auto;
    }

    .assistant-form {
      display: grid;
      gap: 12px;
      margin-top: 12px;
    }

    .assistant-form-field {
      display: grid;
      gap: 6px;
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
    }

    .assistant-form-field input,
    .assistant-form-field textarea {
      width: 100%;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #020617;
      color: var(--text);
      font: inherit;
      font-size: 14px;
      font-weight: 500;
      line-height: 1.45;
      padding: 10px 12px;
      outline: none;
      overflow-wrap: anywhere;
      white-space: pre-wrap;
    }

    .assistant-form-field textarea {
      min-height: 104px;
      max-height: 220px;
      overflow-y: auto;
      resize: vertical;
    }

    .assistant-form-field input:focus,
    .assistant-form-field textarea:focus {
      border-color: rgba(56, 189, 248, 0.72);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.14);
    }

    .app-modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 16px;
      flex-wrap: wrap;
    }

    .app-modal-actions button {
      min-width: 94px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      color: var(--text);
      cursor: pointer;
      font: inherit;
      font-size: 14px;
      font-weight: 800;
      padding: 10px 13px;
    }

    .app-modal-actions button:hover,
    .app-modal-actions button:focus {
      outline: 2px solid rgba(56, 189, 248, 0.55);
      outline-offset: -2px;
    }

    .app-modal-actions .danger {
      border-color: rgba(239, 68, 68, 0.55);
      background: rgba(127, 29, 29, 0.72);
      color: #fecaca;
    }

    .app-modal-actions .primary {
      border-color: rgba(56, 189, 248, 0.56);
      background: var(--user);
      color: #ffffff;
    }

    .thinking-text {
      color: var(--muted);
      font-style: italic;
    }

    form {
      grid-column: 2;
      grid-row: 2;
      min-width: 0;
      width: min(calc(100% - clamp(56px, 10vw, 240px)), 1260px);
      justify-self: center;
      display: grid;
      grid-template-columns: auto 1fr auto auto auto auto;
      align-items: center;
      gap: 10px;
      background: rgba(15, 23, 42, 0.82);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 10px;
      margin-right: 0;
      box-shadow: 0 18px 46px rgba(0, 0, 0, 0.25);
    }

    textarea {
      width: 100%;
      min-height: 56px;
      max-height: 160px;
      resize: none;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 16px 18px;
      background: rgba(15, 23, 42, 0.9);
      color: var(--text);
      font: inherit;
      line-height: 1.4;
    }

    textarea::placeholder {
      color: var(--muted);
    }

    textarea:focus {
      outline: 2px solid rgba(56, 189, 248, 0.28);
      border-color: var(--accent);
    }

    .depth-select-button {
      min-width: 92px;
      height: 44px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(56, 189, 248, 0.30);
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.92);
      color: var(--text);
      cursor: pointer;
      font: inherit;
      font-size: 14px;
      font-weight: 800;
      padding: 0 15px;
      transition: background 140ms ease, border-color 140ms ease, color 140ms ease;
    }

    .depth-select-button:hover:not(:disabled),
    .depth-select-button:focus:not(:disabled),
    .depth-select-button.open {
      border-color: rgba(56, 189, 248, 0.62);
      background: rgba(56, 189, 248, 0.14);
      color: #ffffff;
      outline: none;
    }

    .depth-select-button:disabled {
      cursor: default;
      opacity: 0.52;
    }

    .depth-menu {
      position: fixed;
      z-index: 80;
      min-width: 150px;
      display: grid;
      gap: 4px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(15, 23, 42, 0.98);
      box-shadow: var(--shadow);
      padding: 6px;
    }

    .depth-menu[hidden] {
      display: none;
    }

    .depth-menu button {
      width: 100%;
      border: 0;
      border-radius: 10px;
      background: transparent;
      color: var(--text);
      cursor: pointer;
      font: inherit;
      font-size: 14px;
      font-weight: 800;
      padding: 9px 11px;
      text-align: left;
    }

    .depth-menu button:hover,
    .depth-menu button:focus {
      background: rgba(56, 189, 248, 0.12);
      color: #ffffff;
      outline: none;
    }

    .depth-menu button.active {
      background: var(--user);
      color: #ffffff;
    }

    .round-icon-button {
      min-width: 52px;
      width: 52px;
      height: 52px;
      display: grid;
      place-items: center;
      border: 1px solid rgba(255, 255, 255, 0.82);
      border-radius: 999px;
      background: #ffffff;
      color: #020617;
      padding: 0;
      line-height: 1;
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.20);
    }

    .round-icon-button svg {
      width: 21px;
      height: 21px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2.25;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .round-icon-button:hover:not(:disabled),
    .round-icon-button:focus:not(:disabled) {
      background: #e5e7eb;
      color: #020617;
      outline: 2px solid rgba(56, 189, 248, 0.34);
      outline-offset: 2px;
    }

    .round-icon-button:disabled {
      opacity: 0.52;
    }

    #send-button {
      min-width: 66px;
      width: 66px;
      height: 66px;
    }

    #send-button svg {
      width: 29px;
      height: 29px;
    }

    .search-mode-button {
      min-width: 66px;
      width: 66px;
      height: 66px;
      border-color: rgba(56, 189, 248, 0.42);
      background: rgba(15, 23, 42, 0.92);
      color: var(--text);
    }

    .search-mode-button:hover:not(:disabled),
    .search-mode-button:focus:not(:disabled) {
      border-color: rgba(56, 189, 248, 0.70);
      background: rgba(56, 189, 248, 0.14);
      color: #ffffff;
    }

    .search-mode-button.active {
      border-color: rgba(96, 165, 250, 0.82);
      background: var(--user);
      color: #ffffff;
      box-shadow: 0 10px 24px rgba(37, 99, 235, 0.34);
    }

    .search-mode-button.active:hover:not(:disabled),
    .search-mode-button.active:focus:not(:disabled) {
      background: var(--user-soft);
      color: #ffffff;
    }

    .attachment-strip {
      grid-column: 1 / -1;
      display: none;
      flex-wrap: wrap;
      gap: 8px;
      min-height: 0;
    }

    .attachment-strip.has-files {
      display: flex;
    }

    .attachment-chip {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      max-width: 280px;
      border: 1px solid rgba(56, 189, 248, 0.28);
      border-radius: 999px;
      background: rgba(56, 189, 248, 0.09);
      color: var(--text);
      font-size: 13px;
      font-weight: 700;
      padding: 6px 9px 6px 10px;
    }

    .attachment-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .attachment-remove {
      min-width: 22px;
      width: 22px;
      height: 22px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.9);
      color: var(--muted);
      font-size: 14px;
      padding: 0;
    }

    .message-attachments {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }

    .message-attachment {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      max-width: 280px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.72);
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      padding: 6px 9px;
    }

    .message-attachment.image {
      max-width: 220px;
      display: grid;
      grid-template-columns: 54px minmax(0, 1fr);
      align-items: center;
      border-radius: 14px;
      padding: 6px;
    }

    .message-attachment-thumb {
      width: 54px;
      height: 42px;
      object-fit: cover;
      border-radius: 10px;
      background: #020617;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .message-attachment-label {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    button {
      min-width: 86px;
      border: 0;
      border-radius: 12px;
      background: #1f2937;
      color: #ffffff;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      padding: 0 16px;
      transition: background 140ms ease, transform 140ms ease;
    }

    button:hover:not(:disabled) {
      background: #2563eb;
    }

    button:disabled {
      cursor: wait;
      opacity: 0.58;
    }

    @media (max-width: 1500px) {
      .shell {
        --sidebar-width: clamp(180px, 14vw, 240px);
        gap: 10px;
        padding: 14px;
      }

      .side-panel {
        border-radius: 18px;
      }

      .sidebar-brand {
        padding: 8px 10px 6px;
      }

      .sidebar-brand-mark {
        width: 24px;
        height: 24px;
      }

      .sidebar-brand-name {
        font-size: 16px;
      }

      .sidebar-new-chat {
        min-height: 30px;
        margin: 0 8px 6px;
        grid-template-columns: 18px 1fr;
        font-size: 12px;
        padding: 0 8px;
      }

      .sidebar-tabs {
        padding: 0 8px 6px;
      }

      .sidebar-tab {
        min-height: 28px;
        grid-template-columns: 18px 1fr;
        gap: 6px;
        font-size: 12px;
        padding: 0 7px;
      }

      .sidebar-tab-icon {
        width: 17px;
        height: 17px;
      }

      .sidebar-tab-icon svg {
        width: 15px;
        height: 15px;
      }

      .sidebar-panel-header {
        min-height: 28px;
        grid-template-columns: minmax(0, 1fr) 24px 24px;
        padding: 3px 7px;
      }

      .sidebar-panel-add,
      .sidebar-panel-more {
        width: 24px;
        height: 24px;
        font-size: 13px;
      }

      .sidebar-body {
        padding: 6px;
      }

      .sidebar-list-title {
        font-size: 11px;
      }

      .sidebar-list-meta {
        font-size: 9px;
      }

      .sidebar-row-action {
        width: 32px;
        min-width: 32px;
        height: 32px;
        min-height: 32px;
      }
    }

    @media (max-width: 640px) {
      .shell {
        --sidebar-width: 0px;
        grid-template-columns: 1fr;
        grid-template-rows: auto minmax(0, 1fr) auto auto;
        padding: 10px;
      }

      .status {
        white-space: normal;
      }

      main {
        grid-column: 1;
        grid-row: 2;
        padding: 12px;
      }

      .side-panel {
        grid-column: 1;
        grid-row: 1;
        max-height: 280px;
      }

      form {
        grid-column: 1;
        grid-row: 3;
        width: 100%;
        justify-self: stretch;
        margin-right: 0;
      }

      .footer-row {
        grid-column: 1;
        grid-row: 4;
        width: 100%;
        justify-self: stretch;
        margin-right: 0;
      }

      .avatar {
        width: 52px;
        height: 52px;
        flex-basis: 52px;
      }

      .me-avatar {
        width: 38px;
        height: 38px;
        flex-basis: 38px;
      }

      .message {
        max-width: calc(100% - 62px);
      }

      .image-results {
        grid-template-columns: 1fr;
      }

      form {
        grid-template-columns: auto 1fr auto auto auto auto;
      }

      textarea {
        grid-column: 1 / -1;
      }

      button {
        min-height: 44px;
      }
    }

    @media (max-width: 1180px) {
      .side-frame {
        display: none;
      }
    }
  </style>
</head>
<body>
  <img class="side-frame left" src="/assets/left.png" alt="">
  <img class="side-frame right" src="/assets/right.png" alt="">

  <div class="shell">
    <div class="workspace">
      <aside class="side-panel" aria-label="MiddAI sidebar">
        <div class="sidebar-brand">
          <img class="sidebar-brand-mark" src="/assets/middai_icon.png" alt="">
          <div class="sidebar-brand-name">MiddAI</div>
        </div>
        <button class="sidebar-new-chat" id="new-chat-button" type="button" title="Save the current chat to history and start fresh.">
          <span class="sidebar-tab-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/><path d="M15 5l3 3"/></svg>
          </span>
          <span>New Chat</span>
        </button>
        <div class="sidebar-tabs" role="group" aria-label="Sidebar view">
          <button class="sidebar-tab active" id="sidebar-chats-tab" type="button" data-sidebar-tab="chats">
            <span class="sidebar-tab-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg>
            </span>
            <span>Previous Chats</span>
          </button>
          <button class="sidebar-tab" id="sidebar-memories-tab" type="button" data-sidebar-tab="memories">
            <span class="sidebar-tab-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M8 6a3 3 0 0 1 6-1 3 3 0 0 1 5 2.5 3 3 0 0 1-1 5.7 3 3 0 0 1-4 4.2 3 3 0 0 1-6 0 3 3 0 0 1-4-4.2A3 3 0 0 1 3 7.5 3 3 0 0 1 8 6Z"/><path d="M9 9h6"/><path d="M8 13h8"/></svg>
            </span>
            <span>Memories</span>
          </button>
          <button class="sidebar-tab" id="sidebar-assistants-tab" type="button" data-sidebar-tab="assistants">
            <span class="sidebar-tab-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><path d="M3 20a5 5 0 0 1 10 0"/><path d="M11 20a5 5 0 0 1 10 0"/></svg>
            </span>
            <span>Assistants</span>
          </button>
          <button class="sidebar-tab" id="sidebar-settings-tab" type="button" data-sidebar-tab="settings">
            <span class="sidebar-tab-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 0 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1A2 2 0 0 1 4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1A2 2 0 0 1 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.6V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1A2 2 0 0 1 19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.1a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.6 1Z"/></svg>
            </span>
            <span>Settings</span>
          </button>
          <button class="sidebar-tab sidebar-quit" id="quit-button" type="button" title="Quit MiddAI and stop LM Studio.">
            <span class="sidebar-tab-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M12 3v9"/><path d="M7 5.5a8 8 0 1 0 10 0"/></svg>
            </span>
            <span>Quit</span>
          </button>
        </div>
        <div class="sidebar-panel-header">
          <div class="sidebar-panel-title" id="sidebar-panel-title">Previous Chats</div>
          <button class="sidebar-panel-add" id="sidebar-panel-add-button" type="button" title="Create">+</button>
          <button class="sidebar-panel-more" id="sidebar-panel-more-button" type="button" title="More options" aria-label="More options">
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <circle cx="5" cy="12" r="2.05" fill="currentColor"></circle>
              <circle cx="12" cy="12" r="2.05" fill="currentColor"></circle>
              <circle cx="19" cy="12" r="2.05" fill="currentColor"></circle>
            </svg>
          </button>
        </div>
        <div class="sidebar-body" id="sidebar-body"></div>
        <div class="sidebar-actions chat-mode" id="sidebar-actions">
          <button class="sidebar-action danger chat-action" id="delete-chat-button" type="button" title="Delete the selected saved chat permanently.">Delete Chat</button>
          <button class="sidebar-action danger chat-action" id="delete-history-button" type="button" title="Delete all saved chats and clear the current chat permanently.">Delete All Chats</button>
          <button class="sidebar-action memory-action" id="add-memory-button" type="button" title="Add a custom memory MiddAI can use later.">Add Memory</button>
          <button class="sidebar-action danger memory-action" id="delete-memory-item-button" type="button" title="Delete the selected memory permanently.">Delete Memory</button>
          <button class="sidebar-action danger memory-action" id="delete-memory-button" type="button" title="DANGER: This permanently deletes MiddAI memory.">Delete All Memory</button>
        </div>
      </aside>

      <main id="chat">
        <div class="messages" id="messages"></div>
      </main>
    </div>

    <form id="chat-form">
      <button class="round-icon-button search-mode-button" id="search-mode-button" type="button" aria-pressed="false" title="Search online with the next message">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg>
      </button>
      <textarea id="question" name="question" placeholder="Type your message..." autocomplete="off"></textarea>
      <button class="depth-select-button" id="depth-select-button" type="button" aria-haspopup="menu" aria-expanded="false" title="Response speed and detail">Quick</button>
      <button class="round-icon-button image-attach-button" id="image-attach-button" type="button" title="Attach image files">
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><circle cx="8.5" cy="10.5" r="1.7"/><path d="m5 18 5.2-5.2a2 2 0 0 1 2.8 0L18 18"/><path d="m14 15 1.2-1.2a2 2 0 0 1 2.8 0L21 17"/></svg>
      </button>
      <button class="round-icon-button attach-button" id="attach-button" type="button" title="Attach documents or text files">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21.4 11.6-8.7 8.7a6 6 0 0 1-8.5-8.5l9.4-9.4a4 4 0 0 1 5.7 5.7L9.8 17.5a2 2 0 1 1-2.8-2.8l8.7-8.7"/></svg>
      </button>
      <button class="round-icon-button" id="send-button" type="submit" title="Send message">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>
      </button>
      <input id="attachment-input" type="file" multiple hidden accept=".txt,.md,.markdown,.log,.csv,.json,.toml,.ini,.yaml,.yml,.xml,.html,.htm,.css,.js,.ts,.py,.bat,.ps1,.sql,.docx,.pdf">
      <input id="image-attachment-input" type="file" multiple hidden accept=".jpg,.jpeg,.png,.webp">
      <div class="attachment-strip" id="attachment-strip" aria-live="polite"></div>
    </form>

    <div class="footer-row">
      <div class="footer-right">
        <div class="status" id="status">Ready</div>
      </div>
    </div>
  </div>

  <div class="image-modal" id="image-modal" aria-hidden="true">
    <div class="image-modal-panel" role="dialog" aria-modal="true" aria-labelledby="image-modal-title">
      <img class="image-modal-preview" id="image-modal-preview" src="" alt="">
      <div class="image-modal-body">
        <h2 class="image-modal-title" id="image-modal-title">Image preview</h2>
        <div class="image-modal-source" id="image-modal-source"></div>
        <div class="image-modal-actions">
          <a id="image-modal-open" href="#" target="_blank" rel="noreferrer">Open original</a>
          <a id="image-modal-download" href="#" target="_blank" rel="noreferrer" download>Download</a>
          <button id="image-modal-close" type="button">Close</button>
        </div>
      </div>
    </div>
  </div>

  <div class="sidebar-action-popover" id="sidebar-action-popover" hidden>
    <button id="sidebar-action-popover-delete" type="button">Delete</button>
  </div>

  <div class="settings-tooltip" id="settings-tooltip" role="tooltip" hidden></div>

  <div class="depth-menu" id="depth-menu" role="menu" hidden>
    <button type="button" role="menuitemradio" data-depth-option="instant" title="Fastest: tiny chat answer, tiny search, no image thumbnails.">Instant</button>
    <button class="active" type="button" role="menuitemradio" data-depth-option="quick" title="Short: one small paragraph with light search.">Quick</button>
    <button type="button" role="menuitemradio" data-depth-option="balanced" title="Normal: up to three short paragraphs and moderate search.">Balanced</button>
    <button type="button" role="menuitemradio" data-depth-option="deep" title="Detailed: structured answers with the deepest search for this model.">Deep</button>
  </div>

  <div class="app-modal" id="app-modal" aria-hidden="true">
    <div class="app-modal-panel" role="dialog" aria-modal="true" aria-labelledby="app-modal-title" aria-describedby="app-modal-message">
      <h2 class="app-modal-title" id="app-modal-title"></h2>
      <p class="app-modal-message" id="app-modal-message"></p>
      <textarea class="app-modal-input" id="app-modal-input"></textarea>
      <div class="app-modal-actions">
        <button id="app-modal-cancel" type="button">Cancel</button>
        <button id="app-modal-confirm" type="button">OK</button>
      </div>
    </div>
  </div>

  <div class="app-modal" id="assistant-modal" aria-hidden="true">
    <div class="app-modal-panel assistant-editor-panel" role="dialog" aria-modal="true" aria-labelledby="assistant-modal-title" aria-describedby="assistant-modal-message">
      <h2 class="app-modal-title" id="assistant-modal-title">New Assistant</h2>
      <p class="app-modal-message" id="assistant-modal-message">Create a custom assistant profile. It will be saved as a text file in Documents/MiddAI/assistants.</p>
      <div class="assistant-form">
        <label class="assistant-form-field">
          <span>Assistant Name</span>
          <input id="assistant-name-input" type="text" autocomplete="off" placeholder="Example: Foraging Helper">
        </label>
        <label class="assistant-form-field">
          <span>Assistant Instructions</span>
          <textarea id="assistant-instructions-input" placeholder="What should this assistant do? What rules should it follow?"></textarea>
        </label>
        <label class="assistant-form-field">
          <span>Assistant Personality</span>
          <textarea id="assistant-personality-input" placeholder="What should this assistant sound like?"></textarea>
        </label>
        <label class="assistant-form-field">
          <span>Assistant Greeting</span>
          <textarea id="assistant-greeting-input" placeholder="The first message shown when a new chat starts with this assistant."></textarea>
        </label>
      </div>
      <div class="app-modal-actions">
        <button id="assistant-modal-cancel" type="button">Cancel</button>
        <button id="assistant-modal-confirm" class="primary" type="button">Save Assistant</button>
      </div>
    </div>
  </div>

  <script>
    function showClientStartupError(message) {
      window.setTimeout(() => {
        const statusElement = document.getElementById("status");
        const messagesElement = document.getElementById("messages");

        if (statusElement) {
          statusElement.textContent = "Interface error";
        }

        if (messagesElement && !messagesElement.dataset.startupErrorShown) {
          messagesElement.dataset.startupErrorShown = "true";
          const row = document.createElement("div");
          row.className = "message-row assistant";
          const avatar = document.createElement("img");
          avatar.className = "avatar assistant-avatar";
          avatar.src = "/assets/assistant.png";
          avatar.alt = "MiddAI";
          const bubble = document.createElement("div");
          bubble.className = "message assistant";
          bubble.textContent = `MiddAI interface failed to start: ${message}`;
          row.appendChild(avatar);
          row.appendChild(bubble);
          messagesElement.appendChild(row);
        }
      }, 0);
    }

    window.addEventListener("error", (event) => {
      showClientStartupError(event.message || "Unknown script error.");
    });

    window.addEventListener("unhandledrejection", (event) => {
      const reason = event.reason && event.reason.message ? event.reason.message : String(event.reason || "Unknown promise error.");
      showClientStartupError(reason);
    });

    const form = document.getElementById("chat-form");
    const questionInput = document.getElementById("question");
    const settingsTooltip = document.getElementById("settings-tooltip");
    const attachButton = document.getElementById("attach-button");
    const imageAttachButton = document.getElementById("image-attach-button");
    const attachmentInput = document.getElementById("attachment-input");
    const imageAttachmentInput = document.getElementById("image-attachment-input");
    const attachmentStrip = document.getElementById("attachment-strip");
    const sendButton = document.getElementById("send-button");
    const searchModeButton = document.getElementById("search-mode-button");
    const depthSelectButton = document.getElementById("depth-select-button");
    const depthMenu = document.getElementById("depth-menu");
    const depthMenuButtons = document.querySelectorAll("[data-depth-option]");
    const messages = document.getElementById("messages");
    const chat = document.getElementById("chat");
    const status = document.getElementById("status");
    const sidebarBody = document.getElementById("sidebar-body");
    const sidebarActions = document.getElementById("sidebar-actions");
    const sidebarPanelTitle = document.getElementById("sidebar-panel-title");
    const sidebarPanelAddButton = document.getElementById("sidebar-panel-add-button");
    const sidebarPanelMoreButton = document.getElementById("sidebar-panel-more-button");
    const sidebarActionPopover = document.getElementById("sidebar-action-popover");
    const sidebarTabs = document.querySelectorAll(".sidebar-tab[data-sidebar-tab]");
    const newChatButton = document.getElementById("new-chat-button");
    const deleteChatButton = document.getElementById("delete-chat-button");
    const deleteHistoryButton = document.getElementById("delete-history-button");
    const addMemoryButton = document.getElementById("add-memory-button");
    const deleteMemoryItemButton = document.getElementById("delete-memory-item-button");
    const quitButton = document.getElementById("quit-button");
    const deleteMemoryButton = document.getElementById("delete-memory-button");
    const imageModal = document.getElementById("image-modal");
    const imageModalPreview = document.getElementById("image-modal-preview");
    const imageModalTitle = document.getElementById("image-modal-title");
    const imageModalSource = document.getElementById("image-modal-source");
    const imageModalOpen = document.getElementById("image-modal-open");
    const imageModalDownload = document.getElementById("image-modal-download");
    const imageModalClose = document.getElementById("image-modal-close");
    const appModal = document.getElementById("app-modal");
    const appModalTitle = document.getElementById("app-modal-title");
    const appModalMessage = document.getElementById("app-modal-message");
    const appModalInput = document.getElementById("app-modal-input");
    const appModalCancel = document.getElementById("app-modal-cancel");
    const appModalConfirm = document.getElementById("app-modal-confirm");
    const assistantModal = document.getElementById("assistant-modal");
    const assistantModalTitle = document.getElementById("assistant-modal-title");
    const assistantModalMessage = document.getElementById("assistant-modal-message");
    const assistantNameInput = document.getElementById("assistant-name-input");
    const assistantInstructionsInput = document.getElementById("assistant-instructions-input");
    const assistantPersonalityInput = document.getElementById("assistant-personality-input");
    const assistantGreetingInput = document.getElementById("assistant-greeting-input");
    const assistantModalCancel = document.getElementById("assistant-modal-cancel");
    const assistantModalConfirm = document.getElementById("assistant-modal-confirm");
    let greetingText = "Welcome. I'm MiddAI, a self-hosted AI assistant. You can chat locally, search the web, search images, analyse files or images, and use local memory when it helps.";
    let sidebarMode = "chats";
    let selectedChatId = null;
    let selectedMemoryId = null;
    let selectedMemoryScope = null;
    let selectedMemoryIsCustom = false;
    let activeAssistantId = null;
    let activeAssistantName = "AI Assistant";
    let searchModeSelected = false;
    let selectedDepth = "quick";
    let statusTimer = null;
    let statusFrame = 0;
    const statusFrames = [".", "..", "...", ".", "..", "..."];
    let pendingAttachments = [];
    const maxAttachmentCount = 5;
    const maxAttachmentBytes = 8 * 1024 * 1024;
    const acceptedAttachmentTypesText = "Accepted file types: .txt, .md, .markdown, .log, .csv, .json, .toml, .ini, .yaml, .yml, .xml, .html, .htm, .css, .js, .ts, .py, .bat, .ps1, .sql, .docx, .pdf, .jpg, .jpeg, .png, .webp.";
    const supportedAttachmentExtensions = new Set([
      ".txt",
      ".md",
      ".markdown",
      ".log",
      ".csv",
      ".json",
      ".toml",
      ".ini",
      ".yaml",
      ".yml",
      ".xml",
      ".html",
      ".htm",
      ".css",
      ".js",
      ".ts",
      ".py",
      ".bat",
      ".ps1",
      ".sql",
      ".docx",
      ".pdf",
      ".jpg",
      ".jpeg",
      ".png",
      ".webp",
    ]);
    const imageAttachmentExtensions = new Set([".jpg", ".jpeg", ".png", ".webp"]);
    const depthLabels = {
      instant: "Instant",
      quick: "Quick",
      balanced: "Balanced",
      deep: "Deep",
    };
    let thinkingTimer = null;
    let thinkingFrame = 0;
    const localThinkingPhrases = [
      "Making strange symbols in the sand",
      "Making pictures out of sticks and mud",
      "Listening to roots under the floorboards",
      "Counting blue sparks on river stones",
      "Sorting thoughts into little leaf piles",
      "Whispering to old moss for advice",
      "Drawing circles around a stubborn idea",
      "Turning a question over like a shiny pebble",
      "Reading the wind between the branches",
      "Untangling moonlit thread",
      "Asking the mushrooms to be reasonable",
      "Stacking tiny runes into a useful shape",
    ];

    function getSelectedValue(group) {
      if (group === "mode") {
        return searchModeSelected ? "search" : "chat";
      }

      if (group === "depth") {
        return selectedDepth;
      }

      const activeButton = document.querySelector(`.toggle-button.active[data-group="${group}"]`);
      if (activeButton) {
        return activeButton.dataset.value;
      }

      return group === "mode" ? "chat" : "quick";
    }

    function setSearchModeSelected(active) {
      searchModeSelected = Boolean(active);
      searchModeButton.classList.toggle("active", searchModeSelected);
      searchModeButton.setAttribute("aria-pressed", searchModeSelected ? "true" : "false");
      searchModeButton.title = searchModeSelected
        ? "Search is on for the next message"
        : "Search online with the next message";
      questionInput.placeholder = searchModeSelected
        ? "Ask a question..."
        : "Type your message...";
    }

    function normalizeDepth(depth) {
      return Object.prototype.hasOwnProperty.call(depthLabels, depth) ? depth : "quick";
    }

    function setSelectedDepth(depth) {
      selectedDepth = normalizeDepth(depth);
      depthSelectButton.textContent = depthLabels[selectedDepth];

      for (const button of depthMenuButtons) {
        const isActive = button.dataset.depthOption === selectedDepth;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-checked", isActive ? "true" : "false");
      }
    }

    function hideDepthMenu() {
      depthMenu.hidden = true;
      depthSelectButton.classList.remove("open");
      depthSelectButton.setAttribute("aria-expanded", "false");
    }

    function showDepthMenu() {
      hideSidebarActionMenu();
      depthMenu.style.visibility = "hidden";
      depthMenu.hidden = false;
      depthSelectButton.classList.add("open");
      depthSelectButton.setAttribute("aria-expanded", "true");

      const anchorRect = depthSelectButton.getBoundingClientRect();
      const menuRect = depthMenu.getBoundingClientRect();
      const viewportPadding = 8;
      const left = Math.min(
        Math.max(viewportPadding, anchorRect.right - menuRect.width),
        window.innerWidth - menuRect.width - viewportPadding,
      );
      const topAbove = anchorRect.top - menuRect.height - 6;
      const topBelow = anchorRect.bottom + 6;
      const top = topAbove >= viewportPadding
        ? topAbove
        : Math.min(
            Math.max(viewportPadding, topBelow),
            window.innerHeight - menuRect.height - viewportPadding,
          );

      depthMenu.style.left = `${left}px`;
      depthMenu.style.top = `${top}px`;
      depthMenu.style.visibility = "";
    }

    function openAppModal({
      title,
      message,
      confirmText = "OK",
      cancelText = "Cancel",
      danger = false,
      prompt = false,
      placeholder = "",
      initialValue = "",
      showCancel = true,
    }) {
      return new Promise((resolve) => {
        const previousFocus = document.activeElement;

        appModalTitle.textContent = title;
        appModalMessage.textContent = message;
        appModalConfirm.textContent = confirmText;
        appModalCancel.textContent = cancelText;
        appModalConfirm.classList.toggle("danger", danger);
        appModalConfirm.classList.toggle("primary", !danger);
        appModalCancel.style.display = showCancel ? "" : "none";
        appModalInput.value = initialValue;
        appModalInput.placeholder = placeholder;
        appModalInput.style.display = prompt ? "block" : "none";

        function cleanup(result) {
          appModal.classList.remove("open");
          appModal.setAttribute("aria-hidden", "true");
          appModalConfirm.removeEventListener("click", onConfirm);
          appModalCancel.removeEventListener("click", onCancel);
          appModal.removeEventListener("click", onBackdrop);
          document.removeEventListener("keydown", onKeydown);

          if (previousFocus && typeof previousFocus.focus === "function") {
            previousFocus.focus();
          }

          resolve(result);
        }

        function onConfirm() {
          cleanup(prompt ? appModalInput.value : true);
        }

        function onCancel() {
          cleanup(prompt ? null : false);
        }

        function onBackdrop(event) {
          if (event.target === appModal) {
            onCancel();
          }
        }

        function onKeydown(event) {
          if (event.key === "Escape") {
            event.preventDefault();
            onCancel();
            return;
          }

          if (event.key === "Enter" && !prompt) {
            event.preventDefault();
            onConfirm();
          }
        }

        appModalConfirm.addEventListener("click", onConfirm);
        appModalCancel.addEventListener("click", onCancel);
        appModal.addEventListener("click", onBackdrop);
        document.addEventListener("keydown", onKeydown);
        appModal.classList.add("open");
        appModal.setAttribute("aria-hidden", "false");

        if (prompt) {
          appModalInput.focus();
          appModalInput.select();
        } else if (!showCancel) {
          appModalConfirm.focus();
        } else {
          appModalCancel.focus();
        }
      });
    }

    function confirmAction(options) {
      return openAppModal(options);
    }

    function promptAction(options) {
      return openAppModal({ ...options, prompt: true });
    }

    function openAssistantEditor(assistant = null) {
      return new Promise((resolve) => {
        const previousFocus = document.activeElement;
        const editing = Boolean(assistant && assistant.id);

        assistantModalTitle.textContent = editing ? "Edit Assistant" : "New Assistant";
        assistantModalMessage.textContent = editing
          ? "Update this custom assistant profile. Built-in assistants cannot be edited."
          : "Create a custom assistant profile. It will be saved as a text file in Documents/MiddAI/assistants.";
        assistantModalConfirm.textContent = editing ? "Save Changes" : "Save Assistant";
        assistantNameInput.value = editing ? (assistant.name || "") : "";
        assistantInstructionsInput.value = editing ? (assistant.instructions || "") : "";
        assistantPersonalityInput.value = editing ? (assistant.personality || "") : "";
        assistantGreetingInput.value = editing ? (assistant.greeting || "") : "";

        function cleanup(result) {
          assistantModal.classList.remove("open");
          assistantModal.setAttribute("aria-hidden", "true");
          assistantModalConfirm.removeEventListener("click", onConfirm);
          assistantModalCancel.removeEventListener("click", onCancel);
          assistantModal.removeEventListener("click", onBackdrop);
          document.removeEventListener("keydown", onKeydown);

          if (previousFocus && typeof previousFocus.focus === "function") {
            previousFocus.focus();
          }

          resolve(result);
        }

        function onConfirm() {
          cleanup({
            assistant_id: editing ? assistant.id : null,
            name: assistantNameInput.value.trim(),
            instructions: assistantInstructionsInput.value.trim(),
            personality: assistantPersonalityInput.value.trim(),
            greeting: assistantGreetingInput.value.trim(),
          });
        }

        function onCancel() {
          cleanup(null);
        }

        function onBackdrop(event) {
          if (event.target === assistantModal) {
            onCancel();
          }
        }

        function onKeydown(event) {
          if (event.key === "Escape") {
            event.preventDefault();
            onCancel();
          }
        }

        assistantModalConfirm.addEventListener("click", onConfirm);
        assistantModalCancel.addEventListener("click", onCancel);
        assistantModal.addEventListener("click", onBackdrop);
        document.addEventListener("keydown", onKeydown);
        assistantModal.classList.add("open");
        assistantModal.setAttribute("aria-hidden", "false");
        assistantNameInput.focus();
      });
    }

    function isExplicitSearchRequest(question) {
      const normalizedQuestion = question.toLowerCase();
      const searchPatterns = [
        /^\\s*(?:please\\s+)?(?:can|could|would|will)\\s+you\\s+(?:please\\s+)?(?:search|look\\s+up|look\\s+for|find)\\s+(?:for\\s+)?(?:an?\\s+|some\\s+)?(?:image|images|picture|pictures|photo(?:s|['’]s)?|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?(?:search|google)\\s+(?:for\\s+)?\\S/,
        /^\\s*(?:please\\s+)?(?:look\\s+up)\\s+\\S/,
        /^\\s*(?:please\\s+)?(?:can|could|would|will)\\s+you\\s+(?:please\\s+)?(?:search|look\\s+up|google)\\b/,
        /^\\s*(?:please\\s+)?(?:can|could|would|will)\\s+you\\s+(?:please\\s+)?look\\s+(?:it|that|this|them|those|these)\\s+up\\b/,
        /^\\s*(?:please\\s+)?look\\s+(?:it|that|this|them|those|these)\\s+up\\b/,
        /\\b(?:search|look\\s+up|google|check)\\s+(?:for|up|online|the\\s+web|the\\s+internet|on\\s+the\\s+web|on\\s+the\\s+internet)\\b/,
        /\\blook\\s+(?:it|that|this|them|those|these)\\s+up\\s+(?:online|on\\s+the\\s+web|on\\s+the\\s+internet)\\b/,
        /\\b(?:check|verify|fact[-\\s]?check)\\s+(?:it|that|this|them|those|these|.+?)\\s+(?:online|on\\s+the\\s+web|on\\s+the\\s+internet)\\b/,
        /\\b(?:use|do|run)\\s+(?:an?\\s+)?(?:web|internet|online)\\s+search\\b/,
        /\\b(?:use|go\\s+on|go\\s+online\\s+and\\s+use)\\s+(?:the\\s+)?(?:web|internet)\\s+to\\s+(?:search|find|look\\s+up|check)\\b/,
        /\\b(?:go\\s+online|use\\s+online\\s+sources)\\s+(?:and\\s+)?(?:search|find|look\\s+up|check)\\b/,
        /\\b(?:find|look\\s+for)\\s+(?:information|info|details|sources)\\s+(?:on|about|for)\\s+.+?\\s+(?:online|on\\s+the\\s+web|on\\s+the\\s+internet)\\b/,
        /^\\s*(?:what\\s+does|what\\s+do)\\s+(?:the\\s+)?(?:internet|web|online\\s+sources)\\s+say\\s+about\\b/,
        /^\\s*(?:according\\s+to|using)\\s+(?:the\\s+)?(?:internet|web|online\\s+sources)\\b/,
        /^\\s*(?:please\\s+)?i\\s+(?:would\\s+like|want|need|wanted|was\\s+looking\\s+for|am\\s+looking\\s+for)\\s+(?:to\\s+see\\s+|to\\s+find\\s+|to\\s+search\\s+for\\s+|to\\s+look\\s+up\\s+)?(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo(?:s|['’]s)?|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?i\\s+(?:wanted|want|would\\s+like|meant|asked)\\s+(?:you\\s+)?(?:to\\s+)?(?:search|look\\s+up|find|show|get)\\s+(?:for\\s+)?(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo(?:s|['’]s)?|pic|pics)\\b/,
        /^\\s*(?:please\\s+)?(?:find|show|get)\\s+(?:me\\s+)?(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo(?:s|['’]s)?|pic|pics)\\b/,
        /^\\s*(?:please\\s+)?(?:search|look\\s+up)\\s+(?:for\\s+)?(?:image|images|picture|pictures|photo(?:s|['’]s)?|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?(?:image|picture|photo)\\s+search\\s+(?:for|of)\\b/,
        /^\\s*(?:please\\s+)?(?:do|run)\\s+(?:an?\\s+)?image\\s+search\\s+(?:for|of)\\b/,
        /^\\s*(?:please\\s+)?(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo(?:s|['’]s)?|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?(?:what\\s+does|what\\s+do)\\s+.+?\\s+looks?\\s+like\\b/,
        /^\\s*(?:please\\s+)?show\\s+(?:me\\s+)?what\\s+.+?\\s+looks?\\s+like\\b/,
        /^\\s*(?:please\\s+)?(?:can|could|may)\\s+i\\s+see\\s+(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo(?:s|['’]s)?|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?visual\\s+examples?\\s+(?:of|for)\\b/,
      ];

      return searchPatterns.some((pattern) => pattern.test(normalizedQuestion));
    }

    setSearchModeSelected(searchModeSelected);
    setSelectedDepth(selectedDepth);

    searchModeButton.addEventListener("click", () => {
      setSearchModeSelected(!searchModeSelected);
    });

    depthSelectButton.addEventListener("click", (event) => {
      event.stopPropagation();

      if (depthMenu.hidden) {
        showDepthMenu();
      } else {
        hideDepthMenu();
      }
    });

    depthMenu.addEventListener("click", (event) => {
      event.stopPropagation();
    });

    for (const button of depthMenuButtons) {
      button.addEventListener("click", () => {
        setSelectedDepth(button.dataset.depthOption);
        hideDepthMenu();
        depthSelectButton.focus();
      });
    }

    for (const tab of sidebarTabs) {
      tab.setAttribute("aria-pressed", tab.classList.contains("active") ? "true" : "false");
      tab.addEventListener("click", () => {
        setSidebarMode(tab.dataset.sidebarTab).catch((error) => {
          setIdleStatus("Sidebar error");
          addMessage("assistant", error.message || "Could not switch sidebar view.");
        });
      });
    }

    function hideSidebarActionMenu() {
      sidebarActionPopover.hidden = true;
      sidebarActionPopover.replaceChildren();
    }

    function showSidebarActionMenuItems(anchor, actions) {
      sidebarActionPopover.replaceChildren();

      for (const action of actions) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = action.label || "Action";
        button.classList.toggle("danger", Boolean(action.danger));
        button.addEventListener("click", () => {
          hideSidebarActionMenu();

          if (action.callback) {
            action.callback();
          }
        });
        sidebarActionPopover.appendChild(button);
      }

      sidebarActionPopover.hidden = false;

      const anchorRect = anchor.getBoundingClientRect();
      const popoverRect = sidebarActionPopover.getBoundingClientRect();
      const viewportPadding = 8;
      const left = Math.min(
        Math.max(viewportPadding, anchorRect.right - popoverRect.width),
        window.innerWidth - popoverRect.width - viewportPadding,
      );
      const top = Math.min(
        Math.max(viewportPadding, anchorRect.bottom + 6),
        window.innerHeight - popoverRect.height - viewportPadding,
      );

      sidebarActionPopover.style.left = `${left}px`;
      sidebarActionPopover.style.top = `${top}px`;
    }

    function showSidebarActionMenu(anchor, label, callback, danger = /delete/i.test(label || "")) {
      showSidebarActionMenuItems(anchor, [
        {
          label: label || "Delete",
          callback,
          danger,
        },
      ]);
    }

    sidebarActionPopover.addEventListener("click", (event) => {
      event.stopPropagation();
    });

    document.addEventListener("click", hideSidebarActionMenu);
    document.addEventListener("click", hideDepthMenu);
    window.addEventListener("resize", hideSidebarActionMenu);
    window.addEventListener("resize", hideDepthMenu);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        hideDepthMenu();
      }
    });

    sidebarPanelAddButton.addEventListener("click", () => {
      if (sidebarMode === "chats") {
        newChatButton.click();
      } else if (sidebarMode === "memories") {
        addMemoryButton.click();
      } else if (sidebarMode === "assistants") {
        createAssistantFlow();
      }
    });

    sidebarPanelMoreButton.addEventListener("click", (event) => {
      event.stopPropagation();

      if (sidebarMode === "chats") {
        showSidebarActionMenu(sidebarPanelMoreButton, "Delete All", () => deleteHistoryButton.click());
      } else if (sidebarMode === "memories") {
        showSidebarActionMenu(sidebarPanelMoreButton, "Delete All", () => deleteMemoryButton.click());
      }
    });

    async function resetServerChat() {
      const response = await fetch("/api/new-chat", {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Could not reset the chat.");
      }

      return response.json();
    }

    async function deleteServerMemory() {
      const response = await fetch("/api/delete-memory", {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Could not delete memory.");
      }
    }

    async function quitServer() {
      const response = await fetch("/api/quit", {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Could not quit MiddAI cleanly.");
      }
    }

    async function loadServerChat() {
      const response = await fetch("/api/current-chat");

      if (!response.ok) {
        throw new Error("Could not load saved chat.");
      }

      return response.json();
    }

    async function loadSavedChats() {
      const response = await fetch("/api/saved-chats");

      if (!response.ok) {
        throw new Error("Could not load saved chats.");
      }

      return response.json();
    }

    async function loadReadableMemories() {
      const response = await fetch("/api/readable-memories");

      if (!response.ok) {
        throw new Error("Could not load memories.");
      }

      return response.json();
    }

    async function loadRuntimeSettings() {
      const response = await fetch("/api/runtime-settings");

      if (!response.ok) {
        throw new Error("Could not load settings.");
      }

      return response.json();
    }

    async function saveRuntimeContextLength(contextLength) {
      const response = await fetch("/api/runtime-settings/context", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ context_length: contextLength }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not update context length.");
      }

      return data;
    }

    async function saveRuntimeTemperature(temperature) {
      const response = await fetch("/api/runtime-settings/temperature", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ temperature }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not update temperature.");
      }

      return data;
    }

    async function saveRuntimeSettings(settings) {
      const response = await fetch("/api/runtime-settings/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(settings),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not update runtime settings.");
      }

      return data;
    }

    async function loadAssistants() {
      const response = await fetch("/api/assistants");

      if (!response.ok) {
        throw new Error("Could not load assistants.");
      }

      return response.json();
    }

    async function selectServerAssistant(assistantId) {
      const response = await fetch("/api/assistants/select", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ assistant_id: assistantId }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not select that assistant.");
      }

      return data;
    }

    async function createServerAssistant(profile) {
      const response = await fetch("/api/assistants/create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(profile),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not save that assistant.");
      }

      return data;
    }

    async function updateServerAssistant(profile) {
      const response = await fetch("/api/assistants/update", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(profile),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not update that assistant.");
      }

      return data;
    }

    async function deleteServerAssistant(assistantId, deleteData = false) {
      const response = await fetch("/api/assistants/delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          assistant_id: assistantId,
          delete_data: Boolean(deleteData),
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not delete that assistant.");
      }

      return data;
    }

    function applyAssistantState(data) {
      activeAssistantId = data.active_assistant_id || (data.assistant && data.assistant.id) || activeAssistantId;
      greetingText = data.greeting || data.assistant_greeting || greetingText;

      if (data.assistant && data.assistant.name) {
        activeAssistantName = data.assistant.name;
      } else if (data.assistants && activeAssistantId) {
        const activeAssistant = data.assistants.find(
          (assistant) => String(assistant.id) === String(activeAssistantId) || assistant.active,
        );

        if (activeAssistant && activeAssistant.name) {
          activeAssistantName = activeAssistant.name;
        }
      }
    }

    async function refreshAssistantState() {
      const data = await loadAssistants();
      applyAssistantState(data);
      return data;
    }

    async function deleteSelectedServerChat(chatId) {
      const response = await fetch("/api/delete-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_id: chatId }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not delete that chat.");
      }

      return data;
    }

    async function openSavedServerChat(chatId) {
      const response = await fetch("/api/open-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_id: chatId }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not open that chat.");
      }

      return data;
    }

    async function deleteServerHistory() {
      const response = await fetch("/api/delete-history", {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Could not delete chats.");
      }
    }

    async function addServerMemory(text) {
      const response = await fetch("/api/add-memory", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not save that memory.");
      }
    }

    async function deleteServerMemoryItem(memoryId, memoryScope) {
      const response = await fetch("/api/delete-memory-item", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ memory_id: memoryId, memory_scope: memoryScope }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not delete that memory.");
      }
    }

    function renderSavedChat(savedMessages) {
      messages.innerHTML = "";

      if (!savedMessages || savedMessages.length === 0) {
        addMessage("assistant", greetingText);
        setIdleStatus("Ready");
        return;
      }

      for (const message of savedMessages) {
        const hasMessageExtras =
          (Array.isArray(message.sources) && message.sources.length > 0) ||
          (Array.isArray(message.images) && message.images.length > 0) ||
          (Array.isArray(message.attachments) && message.attachments.length > 0);

        if (
          (message.role === "user" || message.role === "assistant") &&
          (message.content || hasMessageExtras)
        ) {
          addMessage(
            message.role,
            message.content || "",
            message.sources || [],
            message.images || [],
            message.attachments || [],
          );
        }
      }

      setIdleStatus("Loaded saved chat");
    }

    function resetVisibleChat() {
      stopThinkingAnimation();
      setIdleStatus("New chat");
      messages.innerHTML = "";
      addMessage("assistant", greetingText);
      questionInput.value = "";
      pendingAttachments = [];
      renderPendingAttachments();
      questionInput.focus();
    }

    function refreshVisibleGreetingIfEmpty() {
      if (messages.querySelector(".message-row.user")) {
        return;
      }

      const assistantRows = messages.querySelectorAll(".message-row.assistant");

      if (assistantRows.length > 1) {
        return;
      }

      messages.innerHTML = "";
      addMessage("assistant", greetingText);
    }

    function applyFreshChatFromServer(data) {
      if (!data) {
        return false;
      }

      selectedChatId = data.current_chat_id || null;

      if (Array.isArray(data.messages) && data.messages.length > 0) {
        renderSavedChat(data.messages);
        return true;
      }

      if (!data.current_chat_id) {
        return false;
      }

      resetVisibleChat();
      return true;
    }

    function friendlyDate(value) {
      if (!value) {
        return "No date";
      }

      const parsed = new Date(value);

      if (Number.isNaN(parsed.getTime())) {
        return value;
      }

      return parsed.toLocaleString([], {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    }

    function compactAge(value) {
      if (!value) {
        return "";
      }

      const parsed = new Date(value);

      if (Number.isNaN(parsed.getTime())) {
        return "";
      }

      const diffMs = Math.max(0, Date.now() - parsed.getTime());
      const minute = 60 * 1000;
      const hour = 60 * minute;
      const day = 24 * hour;
      const week = 7 * day;
      const month = 30 * day;
      const year = 365 * day;

      if (diffMs < minute) {
        return "now";
      }

      if (diffMs < hour) {
        return `${Math.floor(diffMs / minute)}m`;
      }

      if (diffMs < day) {
        return `${Math.floor(diffMs / hour)}h`;
      }

      if (diffMs < week) {
        return `${Math.floor(diffMs / day)}d`;
      }

      if (diffMs < month) {
        return `${Math.floor(diffMs / week)}w`;
      }

      if (diffMs < year) {
        return `${Math.floor(diffMs / month)}mo`;
      }

      return `${Math.floor(diffMs / year)}y`;
    }

    function titleCase(value) {
      return (value || "memory")
        .replace(/_/g, " ")
        .replace(/\\b\\w/g, (letter) => letter.toUpperCase());
    }

    function makeSidebarHeading(text) {
      const heading = document.createElement("h2");
      heading.className = "sidebar-heading";
      heading.textContent = text;
      return heading;
    }

    function makeEmptySidebarMessage(text) {
      const empty = document.createElement("div");
      empty.className = "sidebar-empty";
      empty.textContent = text;
      return empty;
    }

    function makeSidebarSection(title) {
      const section = document.createElement("section");
      section.className = "sidebar-section";
      section.appendChild(makeSidebarHeading(title));
      return section;
    }

    function makeSidebarListRow(options) {
      const row = document.createElement("div");
      row.className = "sidebar-list-row";
      row.title = options.tooltip || options.title || "";

      if (options.active) {
        row.classList.add("active");
      }

      const mainButton = document.createElement("button");
      mainButton.className = "sidebar-list-main";
      mainButton.type = "button";

      const title = document.createElement("span");
      title.className = "sidebar-list-title";
      title.textContent = options.title || "Untitled";
      mainButton.appendChild(title);

      if (options.meta) {
        const meta = document.createElement("span");
        meta.className = "sidebar-list-meta";
        meta.textContent = options.meta;
        mainButton.appendChild(meta);
      }

      mainButton.addEventListener("click", options.onOpen || (() => {}));
      row.appendChild(mainButton);

      const actionButton = document.createElement("button");
      actionButton.className = "sidebar-row-action";
      actionButton.type = "button";
      actionButton.title = options.actionTitle || "Options";
      actionButton.setAttribute("aria-label", actionButton.title);

      if (options.onAction) {
        actionButton.addEventListener("click", (event) => {
          event.stopPropagation();
          options.onAction(actionButton);
        });
      } else {
        actionButton.disabled = true;
        actionButton.style.visibility = "hidden";
      }

      row.appendChild(actionButton);
      return row;
    }

    function setActiveSidebarRow(row) {
      for (const sibling of sidebarBody.querySelectorAll(".sidebar-list-row, .sidebar-item")) {
        sibling.classList.remove("active");
      }

      row.classList.add("active");
    }

    function renderSavedChats(chats, activeChatId = selectedChatId) {
      sidebarBody.innerHTML = "";
      let chatList = chats || [];
      const hasActivePlaceholder = Boolean(activeChatId) && chatList.some(
        (chatItem) => String(chatItem.id) === String(activeChatId),
      );

      if (activeChatId && !hasActivePlaceholder) {
        chatList = [
          {
            id: activeChatId,
            title: "New chat",
            preview: "No messages yet.",
            ended_at: new Date().toISOString(),
            message_count: 0,
            current: true,
            active: true,
          },
          ...chatList,
        ];
      }

      const requestedChat = chatList.find(
        (chatItem) => activeChatId && String(chatItem.id) === String(activeChatId),
      );
      const activeChat = chatList.find((chatItem) => chatItem.current || chatItem.active);
      selectedChatId = requestedChat ? requestedChat.id : (activeChat ? activeChat.id : null);

      if (chatList.length === 0) {
        sidebarBody.appendChild(makeEmptySidebarMessage("Saved chats will appear here when you start a new chat."));
        return;
      }

      const list = document.createElement("div");
      list.className = "sidebar-list";

      for (const chatItem of chatList) {
        const age = compactAge(chatItem.ended_at);
        const messageCount = chatItem.message_count || 0;
        const messageLabel = `${messageCount} msg`;
        const metaText = chatItem.current
          ? `Current · ${messageLabel}`
          : `${messageLabel}${age ? ` · ${age}` : ""}`;

        const row = makeSidebarListRow({
          title: chatItem.title || "Saved chat",
          meta: metaText,
          tooltip: chatItem.preview || "No preview available.",
          active: Boolean(selectedChatId) && String(selectedChatId) === String(chatItem.id),
          actionTitle: "Delete this chat",
          onOpen: async () => {
            selectedChatId = chatItem.id;
            setActiveSidebarRow(row);

            try {
              const data = await openSavedServerChat(chatItem.id);
              renderSavedChat(data.messages || []);
              if (sidebarMode === "chats" && data.chats) {
                renderSavedChats(data.chats || [], chatItem.id);
              } else {
                await refreshSidebar();
              }
              setIdleStatus("Opened saved chat");
            } catch (error) {
              setIdleStatus("Error");
              addMessage("assistant", error.message);
            }
          },
          onAction: (actionButton) => {
            selectedChatId = chatItem.id;
            setActiveSidebarRow(row);
            showSidebarActionMenu(actionButton, "Delete", () => deleteChatButton.click());
          },
        });

        list.appendChild(row);
      }

      sidebarBody.appendChild(list);
    }

    function renderMemoryItem(section, item) {
      const customLabel = item.custom ? " - custom" : "";
      const reviewLabel = item.review_required ? " - review required" : "";
      const displayTitle = item.display_title || item.text || "Untitled memory";
      const detailLines = Array.isArray(item.detail_sentences)
        ? item.detail_sentences
        : [];
      const tooltip = [
        `${titleCase(item.scope)} - ${titleCase(item.type)}${customLabel}${reviewLabel}`,
        `Seen ${item.times_seen || 1} time(s).`,
        `Last seen: ${friendlyDate(item.last_seen || item.created_at)}`,
      ].join(" ");

      function showMemoryDetails() {
        const details = [
          displayTitle,
          "",
          `Scope: ${titleCase(item.scope || "memory")}`,
          `Type: ${titleCase(item.type || "memory")}${customLabel}`,
          `Importance: ${item.importance ?? "unknown"}`,
          `Seen: ${item.times_seen || 1} time(s)`,
          `Created: ${friendlyDate(item.created_at)}`,
          `Last seen: ${friendlyDate(item.last_seen || item.created_at)}`,
          item.last_retrieved_at ? `Last retrieved: ${friendlyDate(item.last_retrieved_at)}` : "",
          item.memory_class ? `Class: ${titleCase(item.memory_class)}` : "",
          item.entity_name ? `Entity: ${item.entity_name}` : "",
          item.aliases && item.aliases.length ? `Aliases: ${item.aliases.join(", ")}` : "",
          detailLines.length ? "Details:" : "",
          ...detailLines.map((line) => `- ${line}`),
          item.review_required ? "Legacy record: review required before automatic use." : "",
          item.source ? `Source: ${titleCase(item.source)}` : "",
          item.id ? `ID: ${item.id}` : "",
        ].filter((line) => line !== "").join(String.fromCharCode(10));

        confirmAction({
          title: "Memory Details",
          message: details,
          confirmText: "Close",
          showCancel: false,
        });
      }

      const row = makeSidebarListRow({
        title: displayTitle,
        meta: item.review_required ? "Review" : titleCase(item.scope),
        tooltip,
        active: selectedMemoryId && String(selectedMemoryId) === String(item.id),
        actionTitle: "Delete this memory",
        onOpen: () => {
          selectedMemoryId = item.id;
          selectedMemoryScope = item.scope || null;
          selectedMemoryIsCustom = Boolean(item.custom);
          setActiveSidebarRow(row);
          showMemoryDetails();
        },
        onAction: (actionButton) => {
          selectedMemoryId = item.id;
          selectedMemoryScope = item.scope || null;
          selectedMemoryIsCustom = Boolean(item.custom);
          setActiveSidebarRow(row);
          showSidebarActionMenu(actionButton, "Delete", () => deleteMemoryItemButton.click());
        },
      });

      section.appendChild(row);
    }

    function renderMemorySection(title, items, emptyText) {
      const section = makeSidebarSection(title);

      if (!items || items.length === 0) {
        section.appendChild(makeEmptySidebarMessage(emptyText));
        sidebarBody.appendChild(section);
        return;
      }

      const list = document.createElement("div");
      list.className = "sidebar-list";

      for (const item of items) {
        renderMemoryItem(list, item);
      }

      section.appendChild(list);
      sidebarBody.appendChild(section);
    }

    function renderReadableMemories(data) {
      sidebarBody.innerHTML = "";
      selectedMemoryId = null;
      selectedMemoryScope = null;
      selectedMemoryIsCustom = false;

      const custom = data.custom || [];
      const longTerm = (data.long || []).filter((item) => !item.custom);
      const midTerm = data.mid || [];
      const current = data.current || [];

      renderMemorySection("User memories", custom, "Custom memories you add will appear here.");
      renderMemorySection("Long term", longTerm, "No long term memories yet.");
      renderMemorySection("Mid term", midTerm, "No mid term memories yet.");
      renderMemorySection("Short Term", current, "Short term memories are empty.");
    }

    function renderAssistants(data) {
      sidebarBody.innerHTML = "";

      const assistants = data.assistants || [];
      activeAssistantId = data.active_assistant_id || activeAssistantId;
      greetingText = data.greeting || greetingText;
      const activeAssistant = assistants.find(
        (assistant) => String(assistant.id) === String(activeAssistantId) || assistant.active,
      );

      if (activeAssistant && activeAssistant.name) {
        activeAssistantName = activeAssistant.name;
      }

      if (assistants.length === 0) {
        sidebarBody.appendChild(makeEmptySidebarMessage("No assistants found."));
        return;
      }

      const list = document.createElement("div");
      list.className = "sidebar-list";

      for (const assistant of assistants) {
        const meta = assistant.active
          ? "Active"
          : assistant.locked
            ? "Locked"
            : "Custom";

        const row = makeSidebarListRow({
          title: assistant.name || "Assistant",
          meta,
          tooltip: assistant.locked
            ? "Built-in assistant. Locked from editing."
            : `Custom assistant file: ${assistant.file || "Documents/MiddAI/assistants"}`,
          active: Boolean(assistant.active) || (
            Boolean(activeAssistantId) && String(activeAssistantId) === String(assistant.id)
          ),
          actionTitle: assistant.locked ? "Locked assistant" : "Custom assistant",
          onOpen: async () => {
            activeAssistantId = assistant.id;
            setActiveSidebarRow(row);

            try {
              const result = await selectServerAssistant(assistant.id);
              applyAssistantState(result);
              renderAssistants(result);
              if (!applyFreshChatFromServer(result)) {
                refreshVisibleGreetingIfEmpty();
              }
              setIdleStatus(`${assistant.name} active`);
            } catch (error) {
              setIdleStatus("Error");
              addMessage("assistant", error.message);
            }
          },
          onAction: assistant.locked
            ? null
            : (actionButton) => {
                activeAssistantId = assistant.id;
                setActiveSidebarRow(row);
                showSidebarActionMenuItems(actionButton, [
                  {
                    label: "Edit",
                    callback: () => editAssistantFlow(assistant),
                    danger: false,
                  },
                  {
                    label: "Delete",
                    callback: () => deleteAssistantFlow(assistant),
                    danger: true,
                  },
                ]);
              },
        });

        list.appendChild(row);
      }

      sidebarBody.appendChild(list);
    }

    function assistantProfileIsIncomplete(profile) {
      return !profile || !profile.name || !profile.instructions || !profile.personality;
    }

    async function createAssistantFlow() {
      const profile = await openAssistantEditor();

      if (!profile) {
        return;
      }

      if (assistantProfileIsIncomplete(profile)) {
        await openAppModal({
          title: "Assistant Incomplete",
          message: "Assistant Name, Assistant Instructions, and Assistant Personality are required.",
          confirmText: "OK",
          showCancel: false,
        });
        return;
      }

      sidebarPanelAddButton.disabled = true;

      try {
        const result = await createServerAssistant(profile);
        applyAssistantState(result);
        renderAssistants(result);
        refreshVisibleGreetingIfEmpty();
        setIdleStatus(`${result.assistant.name} active`);
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      } finally {
        sidebarPanelAddButton.disabled = false;
      }
    }

    async function editAssistantFlow(assistant) {
      if (!assistant || assistant.locked) {
        return;
      }

      const profile = await openAssistantEditor(assistant);

      if (!profile) {
        return;
      }

      if (assistantProfileIsIncomplete(profile)) {
        await openAppModal({
          title: "Assistant Incomplete",
          message: "Assistant Name, Assistant Instructions, and Assistant Personality are required.",
          confirmText: "OK",
          showCancel: false,
        });
        return;
      }

      try {
        const result = await updateServerAssistant(profile);
        applyAssistantState(result);
        renderAssistants(result);
        refreshVisibleGreetingIfEmpty();
        setIdleStatus(`${result.assistant.name} updated`);
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      }
    }

    async function deleteAssistantFlow(assistant) {
      if (!assistant || assistant.locked) {
        return;
      }

      const confirmed = await confirmAction({
        title: "Delete Assistant",
        message: (
          `Delete "${assistant.name || "this assistant"}" permanently?\\n\\n` +
          "You will choose whether its chats and memories are kept or deleted next."
        ),
        confirmText: "Continue",
        danger: true,
      });

      if (!confirmed) {
        return;
      }

      const deleteData = await confirmAction({
        title: "Delete Assistant Data Too?",
        message: (
          `Should MiddAI also permanently delete all chats, memories, ` +
          `continuity summaries, and exported chats belonging to ` +
          `"${assistant.name || "this assistant"}"?`
        ),
        confirmText: "Delete Data Too",
        cancelText: "Keep Data",
        danger: true,
      });

      try {
        const result = await deleteServerAssistant(assistant.id, deleteData);
        applyAssistantState(result);
        renderAssistants(result);
        if (!applyFreshChatFromServer(result)) {
          refreshVisibleGreetingIfEmpty();
        }
        setIdleStatus(deleteData ? "Assistant and data deleted" : "Assistant deleted; data kept");
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      }
    }

    async function maybeShowAssistantsNotice() {
      if (localStorage.getItem("middaiAssistantsNoticeSeen") === "1") {
        return;
      }

      await confirmAction({
        title: "Assistants",
        message: "Assistants are reusable instruction profiles. Built-in assistants are locked. Custom assistants are saved as text files in Documents/MiddAI/assistants.",
        confirmText: "OK",
      });
      localStorage.setItem("middaiAssistantsNoticeSeen", "1");
    }

    function renderSettings(data) {
      sidebarBody.innerHTML = "";
      settingsTooltip.hidden = true;

      const activeModel = data.active_model || {};
      const modelLabel = data.model_label || activeModel.label || activeModel.model_name || "Unknown model";
      const minContext = Number(data.min_context_length || 2000);
      const maxContext = Math.max(
        minContext,
        Number(data.max_context_length || activeModel.max_context_length || activeModel.context_length || 12000),
      );
      const initialContextValue = Math.min(
        maxContext,
        Math.max(minContext, Number(data.context_length || activeModel.context_length || minContext)),
      );
      const memoryMode = data.memory_mode || activeModel.memory_mode || "rules";
      const memoryAvailable = data.memory_available !== false && memoryMode !== "off";
      const initialAiJudgeEnabled = memoryAvailable && Boolean(data.ai_judge_enabled);
      const initialSeparateAiJudge = initialAiJudgeEnabled
        && Boolean(data.ai_judge_separate_model);
      const canUpdateContext = Boolean(data.can_update_context);
      const canUpdateGpu = Boolean(data.can_update_gpu);
      const initialGpuOffloadEnabled = Boolean(data.gpu_offload_enabled);
      const initialGpuOffloadPercent = Math.min(
        90,
        Math.max(10, Number(data.gpu_offload_percent ?? 50)),
      );
      const initialTemperature = Math.min(
        2,
        Math.max(0, Number(data.temperature ?? 0.7)),
      );

      const section = makeSidebarSection("Runtime");
      section.classList.add("settings-control-panel");

      function makeSettingsHeading(label, tooltip) {
        const heading = document.createElement("span");
        heading.className = "settings-label-header";

        const text = document.createElement("span");
        text.textContent = label;

        const help = document.createElement("button");
        help.className = "settings-help";
        help.type = "button";
        help.textContent = "?";
        help.setAttribute("aria-label", `About ${label}`);
        help.dataset.tooltip = tooltip;
        help.addEventListener("mouseenter", () => {
          settingsTooltip.textContent = tooltip;
          settingsTooltip.hidden = false;
          settingsTooltip.style.visibility = "hidden";

          const buttonRect = help.getBoundingClientRect();
          const tooltipRect = settingsTooltip.getBoundingClientRect();
          const left = Math.min(
            window.innerWidth - tooltipRect.width - 12,
            Math.max(12, buttonRect.left),
          );
          let top = buttonRect.bottom + 6;

          if (top + tooltipRect.height > window.innerHeight - 12) {
            top = Math.max(12, buttonRect.top - tooltipRect.height - 6);
          }

          settingsTooltip.style.left = `${left}px`;
          settingsTooltip.style.top = `${top}px`;
          settingsTooltip.style.visibility = "";
        });
        help.addEventListener("mouseleave", () => {
          settingsTooltip.hidden = true;
        });
        help.addEventListener("focus", () => {
          help.dispatchEvent(new MouseEvent("mouseenter"));
        });
        help.addEventListener("blur", () => {
          settingsTooltip.hidden = true;
        });
        help.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
        });

        heading.appendChild(text);
        heading.appendChild(help);
        return heading;
      }

      const runtimeSummary = document.createElement("div");
      runtimeSummary.className = "settings-runtime-summary";

      function appendRuntimeRow(label, value) {
        const row = document.createElement("div");
        row.className = "settings-runtime-row";

        const key = document.createElement("span");
        key.className = "settings-runtime-key";
        key.textContent = label;

        const content = document.createElement("span");
        content.className = "settings-runtime-value";
        content.textContent = value;

        row.appendChild(key);
        row.appendChild(content);
        runtimeSummary.appendChild(row);
      }

      appendRuntimeRow("Model", modelLabel);
      appendRuntimeRow("Memory", titleCase(memoryMode));
      section.appendChild(runtimeSummary);

      const contextLabel = document.createElement("label");
      contextLabel.className = "settings-field";
      contextLabel.appendChild(makeSettingsHeading(
        "Context length",
        "Sets how much text the model can consider at once. Higher values preserve more conversation but use more RAM and can slow the model.",
      ));

      const rangeRow = document.createElement("div");
      rangeRow.className = "settings-range-row";

      const contextSlider = document.createElement("input");
      contextSlider.className = "settings-slider";
      contextSlider.type = "range";
      contextSlider.min = String(minContext);
      contextSlider.max = String(maxContext);
      contextSlider.step = "100";
      contextSlider.value = String(initialContextValue);
      contextSlider.disabled = !canUpdateContext;

      const contextInput = document.createElement("input");
      contextInput.className = "settings-input";
      contextInput.type = "number";
      contextInput.min = String(minContext);
      contextInput.max = String(maxContext);
      contextInput.step = "100";
      contextInput.value = String(initialContextValue);
      contextInput.disabled = !canUpdateContext;
      contextInput.title = `Allowed range: ${minContext}-${maxContext} tokens.`;

      rangeRow.appendChild(contextSlider);
      rangeRow.appendChild(contextInput);
      contextLabel.appendChild(rangeRow);

      const rangeMeta = document.createElement("div");
      rangeMeta.className = "settings-range-meta";
      rangeMeta.textContent = `Range: ${minContext.toLocaleString()}-${maxContext.toLocaleString()} tokens`;
      contextLabel.appendChild(rangeMeta);

      const temperatureLabel = document.createElement("label");
      temperatureLabel.className = "settings-field";
      temperatureLabel.appendChild(makeSettingsHeading(
        "Request temperature",
        "Controls response randomness. Lower values are more predictable and focused; higher values are more varied and creative.",
      ));

      const temperatureRow = document.createElement("div");
      temperatureRow.className = "settings-range-row";

      const temperatureSlider = document.createElement("input");
      temperatureSlider.className = "settings-slider";
      temperatureSlider.type = "range";
      temperatureSlider.min = "0";
      temperatureSlider.max = "2";
      temperatureSlider.step = "0.1";
      temperatureSlider.value = String(initialTemperature);

      const temperatureInput = document.createElement("input");
      temperatureInput.className = "settings-input";
      temperatureInput.type = "number";
      temperatureInput.min = "0";
      temperatureInput.max = "2";
      temperatureInput.step = "0.1";
      temperatureInput.value = initialTemperature.toFixed(1);

      temperatureRow.appendChild(temperatureSlider);
      temperatureRow.appendChild(temperatureInput);
      temperatureLabel.appendChild(temperatureRow);

      const temperatureMeta = document.createElement("div");
      temperatureMeta.className = "settings-range-meta";
      temperatureMeta.textContent = "Range: 0.0-2.0";
      temperatureLabel.appendChild(temperatureMeta);

      const judgeField = document.createElement("div");
      judgeField.className = "settings-toggle-field";

      const judgeRow = document.createElement("label");
      judgeRow.className = "settings-toggle-row";
      judgeRow.appendChild(makeSettingsHeading(
        "AI Judge memory",
        "Lets a model review uncertain memory candidates, classify them, and decide whether to save, merge, keep temporarily, or discard them. Rules-based memory still works when this is off.",
      ));

      const judgeSwitch = document.createElement("span");
      judgeSwitch.className = "settings-switch";

      const judgeInput = document.createElement("input");
      judgeInput.type = "checkbox";
      judgeInput.checked = initialAiJudgeEnabled;
      judgeInput.disabled = !memoryAvailable;

      const judgeTrack = document.createElement("span");
      judgeTrack.className = "settings-switch-track";

      judgeSwitch.appendChild(judgeInput);
      judgeSwitch.appendChild(judgeTrack);
      judgeRow.appendChild(judgeSwitch);
      judgeField.appendChild(judgeRow);

      const judgeMeta = document.createElement("div");
      judgeMeta.className = "settings-range-meta";
      judgeMeta.textContent = memoryAvailable
        ? "AI Judge improves ambiguous memory decisions but is slower. It works better with a GPU or plenty of system RAM."
        : "Memory is disabled by this model preset.";
      judgeField.appendChild(judgeMeta);

      const separateJudgeField = document.createElement("div");
      separateJudgeField.className = "settings-toggle-field";

      const separateJudgeRow = document.createElement("label");
      separateJudgeRow.className = "settings-toggle-row";
      separateJudgeRow.appendChild(makeSettingsHeading(
        "Separate AI Judge model",
        "Loads a second, low-context Qwen3-4B model for memory review so the main chat model does not handle Judge work. This uses substantially more RAM.",
      ));

      const separateJudgeSwitch = document.createElement("span");
      separateJudgeSwitch.className = "settings-switch";

      const separateJudgeInput = document.createElement("input");
      separateJudgeInput.type = "checkbox";
      separateJudgeInput.checked = initialSeparateAiJudge;
      separateJudgeInput.disabled = !memoryAvailable || !initialAiJudgeEnabled;

      const separateJudgeTrack = document.createElement("span");
      separateJudgeTrack.className = "settings-switch-track";

      separateJudgeSwitch.appendChild(separateJudgeInput);
      separateJudgeSwitch.appendChild(separateJudgeTrack);
      separateJudgeRow.appendChild(separateJudgeSwitch);
      separateJudgeField.appendChild(separateJudgeRow);

      const separateJudgeMeta = document.createElement("div");
      separateJudgeMeta.className = "settings-warning danger";
      separateJudgeMeta.textContent = "Requires at least 16 GB system RAM.";
      separateJudgeField.appendChild(separateJudgeMeta);

      const gpuField = document.createElement("div");
      gpuField.className = "settings-toggle-field";

      const gpuRow = document.createElement("label");
      gpuRow.className = "settings-toggle-row";
      gpuRow.appendChild(makeSettingsHeading(
        "GPU scaling",
        "Moves the selected percentage of model work to a compatible GPU. This can improve speed, but unsupported hardware or excessive offload can prevent the model loading.",
      ));

      const gpuSwitch = document.createElement("span");
      gpuSwitch.className = "settings-switch";

      const gpuInput = document.createElement("input");
      gpuInput.type = "checkbox";
      gpuInput.checked = initialGpuOffloadEnabled;
      gpuInput.disabled = !canUpdateGpu;

      const gpuTrack = document.createElement("span");
      gpuTrack.className = "settings-switch-track";

      gpuSwitch.appendChild(gpuInput);
      gpuSwitch.appendChild(gpuTrack);
      gpuRow.appendChild(gpuSwitch);
      gpuField.appendChild(gpuRow);

      const gpuRangeRow = document.createElement("div");
      gpuRangeRow.className = "settings-range-row";

      const gpuSlider = document.createElement("input");
      gpuSlider.className = "settings-slider";
      gpuSlider.type = "range";
      gpuSlider.min = "10";
      gpuSlider.max = "90";
      gpuSlider.step = "10";
      gpuSlider.value = String(initialGpuOffloadPercent);
      gpuSlider.disabled = !canUpdateGpu || !initialGpuOffloadEnabled;

      const gpuPercentInput = document.createElement("input");
      gpuPercentInput.className = "settings-input";
      gpuPercentInput.type = "number";
      gpuPercentInput.min = "10";
      gpuPercentInput.max = "90";
      gpuPercentInput.step = "10";
      gpuPercentInput.value = String(initialGpuOffloadPercent);
      gpuPercentInput.disabled = !canUpdateGpu || !initialGpuOffloadEnabled;
      gpuPercentInput.title = "GPU scaling percentage";

      gpuRangeRow.appendChild(gpuSlider);
      gpuRangeRow.appendChild(gpuPercentInput);
      gpuField.appendChild(gpuRangeRow);

      const gpuRangeMeta = document.createElement("div");
      gpuRangeMeta.className = "settings-range-meta";
      gpuRangeMeta.textContent = "Range: 10%-90%";
      gpuField.appendChild(gpuRangeMeta);

      const gpuMeta = document.createElement("div");
      gpuMeta.className = "settings-warning danger";

      if (!canUpdateGpu) {
        gpuMeta.classList.remove("danger");
        gpuMeta.textContent = "GPU offload is managed directly in LM Studio for this model.";
      } else {
        gpuMeta.textContent = "Requires a compatible GPU. Enabling GPU scaling without one may make LM Studio fail to load or crash.";
      }

      gpuField.appendChild(gpuMeta);

      const saveButton = document.createElement("button");
      saveButton.className = "settings-save-button";
      saveButton.type = "button";
      saveButton.textContent = "Save";
      saveButton.disabled = true;

      const progress = document.createElement("div");
      progress.className = "settings-progress";

      const progressLabel = document.createElement("div");
      progressLabel.className = "settings-progress-label";
      progressLabel.textContent = "Saving and updating 0%";

      const progressTrack = document.createElement("div");
      progressTrack.className = "settings-progress-track";

      const progressFill = document.createElement("div");
      progressFill.className = "settings-progress-fill";

      progressTrack.appendChild(progressFill);
      progress.appendChild(progressLabel);
      progress.appendChild(progressTrack);

      const warning = document.createElement("div");
      warning.className = "settings-warning";

      if (canUpdateContext) {
        warning.textContent = `Current setting: ${initialContextValue.toLocaleString()} tokens.`;
      } else {
        warning.classList.add("danger");
        warning.textContent = "Context is managed directly in LM Studio. Temperature can still be saved.";
      }

      function clampContextValue(value) {
        const numericValue = Number(value);

        if (!Number.isFinite(numericValue)) {
          return initialContextValue;
        }

        return Math.min(maxContext, Math.max(minContext, Math.round(numericValue / 100) * 100));
      }

      function syncContextInputs(value, source) {
        const clampedValue = clampContextValue(value);

        if (source !== "slider") {
          contextSlider.value = String(clampedValue);
        }

        if (source !== "number") {
          contextInput.value = String(clampedValue);
        }

        updateSaveState();
      }

      function clampTemperature(value) {
        const numericValue = Number(value);

        if (!Number.isFinite(numericValue)) {
          return initialTemperature;
        }

        return Math.min(2, Math.max(0, Math.round(numericValue * 10) / 10));
      }

      function syncTemperatureInputs(value, source) {
        const clampedValue = clampTemperature(value);

        if (source !== "slider") {
          temperatureSlider.value = String(clampedValue);
        }

        if (source !== "number") {
          temperatureInput.value = clampedValue.toFixed(1);
        }

        updateSaveState();
      }

      function clampGpuPercent(value) {
        const numericValue = Number(value);

        if (!Number.isFinite(numericValue)) {
          return initialGpuOffloadPercent;
        }

        return Math.min(90, Math.max(10, Math.round(numericValue / 10) * 10));
      }

      function syncGpuInputs(value, source) {
        const clampedValue = clampGpuPercent(value);

        if (source !== "slider") {
          gpuSlider.value = String(clampedValue);
        }

        if (source !== "number") {
          gpuPercentInput.value = String(clampedValue);
        }

        updateSaveState();
      }

      function updateGpuInputState() {
        const disabled = !canUpdateGpu || !gpuInput.checked;
        gpuSlider.disabled = disabled;
        gpuPercentInput.disabled = disabled;
      }

      function updateJudgeDependentState() {
        separateJudgeInput.disabled = !memoryAvailable || !judgeInput.checked;
      }

      function updateSaveState() {
        const contextChanged = clampContextValue(contextInput.value) !== initialContextValue;
        const temperatureChanged = clampTemperature(temperatureInput.value) !== initialTemperature;
        const judgeChanged = memoryAvailable && judgeInput.checked !== initialAiJudgeEnabled;
        const separateJudgeEnabled = memoryAvailable
          && judgeInput.checked
          && separateJudgeInput.checked;
        const separateJudgeChanged = separateJudgeEnabled !== initialSeparateAiJudge;
        const gpuEnabledChanged = canUpdateGpu && gpuInput.checked !== initialGpuOffloadEnabled;
        const gpuPercentChanged = canUpdateGpu
          && gpuInput.checked
          && clampGpuPercent(gpuPercentInput.value) !== initialGpuOffloadPercent;
        const gpuChanged = gpuEnabledChanged || gpuPercentChanged;
        const reloadRequired = (canUpdateContext && contextChanged) || gpuChanged;
        saveButton.disabled = !temperatureChanged
          && !judgeChanged
          && !separateJudgeChanged
          && !gpuChanged
          && (!canUpdateContext || !contextChanged);
        warning.classList.toggle("danger", reloadRequired);
        warning.textContent = reloadRequired
          ? "Save will unload and reload the model in LM Studio with the new context or GPU setting."
          : `Current setting: ${initialContextValue.toLocaleString()} tokens.`;
      }

      function setProgress(percent) {
        const safePercent = Math.min(100, Math.max(0, Math.round(percent)));
        progressFill.style.width = `${safePercent}%`;
        progressLabel.textContent = `Saving and updating ${safePercent}%`;
      }

      function startSaveProgress() {
        let percent = 0;
        setProgress(0);
        progress.classList.add("visible");

        return window.setInterval(() => {
          percent = Math.min(92, percent + 4);
          setProgress(percent);
        }, 450);
      }

      contextSlider.addEventListener("input", () => {
        syncContextInputs(contextSlider.value, "slider");
      });

      contextInput.addEventListener("input", () => {
        syncContextInputs(contextInput.value, "number");
      });

      contextInput.addEventListener("blur", () => {
        syncContextInputs(contextInput.value);
      });

      temperatureSlider.addEventListener("input", () => {
        syncTemperatureInputs(temperatureSlider.value, "slider");
      });

      temperatureInput.addEventListener("input", () => {
        syncTemperatureInputs(temperatureInput.value, "number");
      });

      temperatureInput.addEventListener("blur", () => {
        syncTemperatureInputs(temperatureInput.value);
      });

      judgeInput.addEventListener("change", () => {
        updateJudgeDependentState();
        updateSaveState();
      });
      separateJudgeInput.addEventListener("change", updateSaveState);
      gpuInput.addEventListener("change", () => {
        updateGpuInputState();
        updateSaveState();
      });

      gpuSlider.addEventListener("input", () => {
        syncGpuInputs(gpuSlider.value, "slider");
      });

      gpuPercentInput.addEventListener("input", () => {
        syncGpuInputs(gpuPercentInput.value, "number");
      });

      gpuPercentInput.addEventListener("blur", () => {
        syncGpuInputs(gpuPercentInput.value);
      });

      saveButton.addEventListener("click", async () => {
        const contextLength = clampContextValue(contextInput.value);
        const temperature = clampTemperature(temperatureInput.value);
        const gpuOffloadPercent = clampGpuPercent(gpuPercentInput.value);
        const separateAiJudgeEnabled = Boolean(
          judgeInput.checked && separateJudgeInput.checked
        );
        const hardwareWarnings = [];

        if (gpuInput.checked) {
          hardwareWarnings.push(
            "GPU scaling requires a compatible GPU. Without one, LM Studio may fail to load or crash.",
          );
        }

        if (separateAiJudgeEnabled) {
          hardwareWarnings.push(
            "The separate AI Judge model requires at least 16 GB system RAM.",
          );
        }

        if (hardwareWarnings.length > 0) {
          const confirmed = await confirmAction({
            title: "Hardware requirements",
            message: `${hardwareWarnings.join("\\n\\n")}\\n\\nAre you sure this computer meets these requirements?`,
            confirmText: "Save settings",
            cancelText: "Cancel",
            danger: true,
          });

          if (!confirmed) {
            return;
          }
        }

        contextSlider.disabled = true;
        contextInput.disabled = true;
        temperatureSlider.disabled = true;
        temperatureInput.disabled = true;
        judgeInput.disabled = true;
        separateJudgeInput.disabled = true;
        gpuInput.disabled = true;
        gpuSlider.disabled = true;
        gpuPercentInput.disabled = true;
        saveButton.disabled = true;
        setBusyStatus("Saving and updating");
        const progressTimer = startSaveProgress();

        try {
          const result = await saveRuntimeSettings({
            context_length: contextLength,
            temperature,
            ai_judge_enabled: judgeInput.checked,
            ai_judge_separate_model: separateAiJudgeEnabled,
            gpu_offload_enabled: gpuInput.checked,
            gpu_offload_percent: gpuOffloadPercent,
          });

          window.clearInterval(progressTimer);
          setProgress(100);
          setIdleStatus("Settings updated");
          window.setTimeout(() => {
            renderSettings(result);
          }, 450);
        } catch (error) {
          window.clearInterval(progressTimer);
          progress.classList.remove("visible");
          contextSlider.disabled = !canUpdateContext;
          contextInput.disabled = !canUpdateContext;
          temperatureSlider.disabled = false;
          temperatureInput.disabled = false;
          judgeInput.disabled = !memoryAvailable;
          updateJudgeDependentState();
          gpuInput.disabled = !canUpdateGpu;
          updateGpuInputState();
          syncContextInputs(contextInput.value);
          syncTemperatureInputs(temperatureInput.value);
          syncGpuInputs(gpuPercentInput.value);
          updateSaveState();
          setIdleStatus("Error");
          warning.classList.add("danger");
          warning.textContent = error.message || "Could not update context length.";
        }
      });

      section.appendChild(contextLabel);
      section.appendChild(temperatureLabel);
      section.appendChild(judgeField);
      section.appendChild(separateJudgeField);
      section.appendChild(gpuField);
      section.appendChild(saveButton);
      section.appendChild(progress);
      section.appendChild(warning);
      sidebarBody.appendChild(section);
    }

    function updateSidebarPanelChrome() {
      const titles = {
        chats: "Previous Chats",
        memories: "Memories",
        assistants: "Assistants",
        settings: "Settings",
      };
      sidebarPanelTitle.textContent = titles[sidebarMode] || "Previous Chats";
      sidebarPanelAddButton.hidden = !["memories", "assistants"].includes(sidebarMode);
      sidebarPanelMoreButton.hidden = !["chats", "memories"].includes(sidebarMode);

      if (sidebarMode === "memories") {
        sidebarPanelAddButton.title = "Add memory";
      } else if (sidebarMode === "assistants") {
        sidebarPanelAddButton.title = "Create assistant profile";
      }

      if (sidebarMode === "chats") {
        sidebarPanelMoreButton.title = "Delete all chats";
      } else if (sidebarMode === "memories") {
        sidebarPanelMoreButton.title = "Delete all memory";
      } else if (sidebarMode === "assistants") {
        sidebarPanelMoreButton.title = "Assistant options";
      }
    }

    async function refreshSidebar() {
      try {
        updateSidebarPanelChrome();

        if (sidebarMode === "chats") {
          const data = await loadSavedChats();
          renderSavedChats(data.chats || []);
          return;
        }

        if (sidebarMode === "memories") {
          const data = await loadReadableMemories();
          renderReadableMemories(data);
          return;
        }

        if (sidebarMode === "assistants") {
          const data = await loadAssistants();
          applyAssistantState(data);
          renderAssistants(data);
          return;
        }

        if (sidebarMode === "settings") {
          const data = await loadRuntimeSettings();
          renderSettings(data);
          return;
        }
      } catch (error) {
        sidebarBody.innerHTML = "";
        sidebarBody.appendChild(makeEmptySidebarMessage(error.message));
      }
    }

    async function setSidebarMode(mode) {
      if (!["chats", "memories", "assistants", "settings"].includes(mode)) {
        mode = "chats";
      }

      sidebarMode = mode;
      selectedChatId = null;
      selectedMemoryId = null;
      selectedMemoryScope = null;
      selectedMemoryIsCustom = false;

      for (const tab of sidebarTabs) {
        const isActive = tab.dataset.sidebarTab === mode;
        tab.classList.toggle("active", isActive);
        tab.setAttribute("aria-pressed", isActive ? "true" : "false");
      }

      sidebarActions.classList.toggle("chat-mode", mode === "chats");
      sidebarActions.classList.toggle("memory-mode", mode === "memories");
      updateSidebarPanelChrome();

      await refreshSidebar();

      if (mode === "assistants") {
        maybeShowAssistantsNotice().catch((error) => {
          setIdleStatus("Assistant notice error");
          addMessage("assistant", error.message || "Could not show the assistants notice.");
        });
      }
    }

    function setIdleStatus(text) {
      if (statusTimer) {
        clearInterval(statusTimer);
        statusTimer = null;
      }

      status.textContent = text;
    }

    function setBusyStatus(text) {
      if (statusTimer) {
        clearInterval(statusTimer);
      }

      statusFrame = 0;
      status.textContent = `${text} ${statusFrames[statusFrame]}`;

      statusTimer = setInterval(() => {
        statusFrame = (statusFrame + 1) % statusFrames.length;
        status.textContent = `${text} ${statusFrames[statusFrame]}`;
      }, 420);
    }

    function getFileExtension(name) {
      const index = String(name || "").lastIndexOf(".");
      return index >= 0 ? String(name).slice(index).toLowerCase() : "";
    }

    function formatFileSize(size) {
      if (!Number.isFinite(size)) {
        return "";
      }

      if (size < 1024) {
        return `${size} B`;
      }

      if (size < 1024 * 1024) {
        return `${(size / 1024).toFixed(1)} KB`;
      }

      return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    }

    function arrayBufferToBase64(buffer) {
      const bytes = new Uint8Array(buffer);
      const chunkSize = 0x8000;
      let binary = "";

      for (let index = 0; index < bytes.length; index += chunkSize) {
        const chunk = bytes.subarray(index, index + chunkSize);
        binary += String.fromCharCode.apply(null, chunk);
      }

      return btoa(binary);
    }

    function dataUrlToBase64(dataUrl) {
      const parts = String(dataUrl || "").split(",");
      return parts.length > 1 ? parts[1] : "";
    }

    function readFileAsDataUrl(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.addEventListener("load", () => resolve(String(reader.result || "")));
        reader.addEventListener("error", () => reject(new Error(`Could not read ${file.name}.`)));
        reader.readAsDataURL(file);
      });
    }

    function loadImageFromDataUrl(dataUrl) {
      return new Promise((resolve, reject) => {
        const image = new Image();
        image.addEventListener("load", () => resolve(image));
        image.addEventListener("error", () => reject(new Error("Could not decode the attached image.")));
        image.src = dataUrl;
      });
    }

    async function convertImageToJpegBase64(file) {
      const dataUrl = await readFileAsDataUrl(file);
      const image = await loadImageFromDataUrl(dataUrl);
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth || image.width;
      canvas.height = image.naturalHeight || image.height;

      if (!canvas.width || !canvas.height) {
        throw new Error("Could not read the attached image dimensions.");
      }

      const context = canvas.getContext("2d");
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0);

      return dataUrlToBase64(canvas.toDataURL("image/jpeg", 0.92));
    }

    async function createImageThumbnailDataUrl(file) {
      const dataUrl = await readFileAsDataUrl(file);
      const image = await loadImageFromDataUrl(dataUrl);
      const width = image.naturalWidth || image.width;
      const height = image.naturalHeight || image.height;

      if (!width || !height) {
        return "";
      }

      const maxSide = 180;
      const scale = Math.min(1, maxSide / Math.max(width, height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(width * scale));
      canvas.height = Math.max(1, Math.round(height * scale));

      const context = canvas.getContext("2d");
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);

      return canvas.toDataURL("image/jpeg", 0.76);
    }

    function renderPendingAttachments() {
      attachmentStrip.innerHTML = "";
      attachmentStrip.classList.toggle("has-files", pendingAttachments.length > 0);

      for (const [index, attachment] of pendingAttachments.entries()) {
        const chip = document.createElement("div");
        chip.className = "attachment-chip";

        const name = document.createElement("span");
        name.className = "attachment-name";
        name.textContent = `${attachment.name} (${formatFileSize(attachment.size)})`;

        const remove = document.createElement("button");
        remove.className = "attachment-remove";
        remove.type = "button";
        remove.title = `Remove ${attachment.name}`;
        remove.textContent = "x";
        remove.addEventListener("click", () => {
          pendingAttachments.splice(index, 1);
          renderPendingAttachments();
          setIdleStatus(
            pendingAttachments.length
              ? `${pendingAttachments.length} file(s) attached`
              : "Ready"
          );
        });

        chip.appendChild(name);
        chip.appendChild(remove);
        attachmentStrip.appendChild(chip);
      }
    }

    function publicAttachmentSummary(attachments) {
      return attachments.map((attachment) => ({
        name: attachment.name,
        extension: attachment.extension,
        size: attachment.size,
        kind: imageAttachmentExtensions.has(attachment.extension) ? "image" : "document",
        preview_url: attachment.preview_url || "",
      }));
    }

    function appendAttachments(bubble, attachments) {
      if (!attachments || attachments.length === 0) {
        return;
      }

      const attachmentBox = document.createElement("div");
      attachmentBox.className = "message-attachments";

      for (const attachment of attachments) {
        const item = document.createElement("div");
        item.className = "message-attachment";

        const label = document.createElement("span");
        label.className = "message-attachment-label";
        label.textContent = `${attachment.name || "attachment"}${attachment.size ? ` (${formatFileSize(attachment.size)})` : ""}`;

        if (attachment.kind === "image" && attachment.preview_url) {
          item.classList.add("image");
          const thumbnail = document.createElement("img");
          thumbnail.className = "message-attachment-thumb";
          thumbnail.src = attachment.preview_url;
          thumbnail.alt = attachment.name || "Attached image";
          item.appendChild(thumbnail);
          item.appendChild(label);
        } else {
          item.appendChild(label);
        }

        attachmentBox.appendChild(item);
      }

      bubble.appendChild(attachmentBox);
    }

    async function readAttachment(file) {
      const extension = getFileExtension(file.name);

      if (!supportedAttachmentExtensions.has(extension)) {
        throw new Error(`Unsupported file type: ${extension || file.name}.\\n\\n${acceptedAttachmentTypesText}`);
      }

      if (file.size > maxAttachmentBytes) {
        throw new Error(`${file.name} is too large. Maximum file size is 8 MB.`);
      }

      const base = {
        name: file.name,
        size: file.size,
        mime_type: file.type || "",
        extension,
      };

      if (imageAttachmentExtensions.has(extension)) {
        const previewUrl = await createImageThumbnailDataUrl(file);

        if (extension === ".webp") {
          return {
            ...base,
            mime_type: "image/jpeg",
            data_base64: await convertImageToJpegBase64(file),
            preview_url: previewUrl,
          };
        }

        const buffer = await file.arrayBuffer();
        return {
          ...base,
          data_base64: arrayBufferToBase64(buffer),
          preview_url: previewUrl,
        };
      }

      if (extension === ".pdf" || extension === ".docx") {
        const buffer = await file.arrayBuffer();
        return {
          ...base,
          data_base64: arrayBufferToBase64(buffer),
        };
      }

      return {
        ...base,
        text: await file.text(),
      };
    }

    async function handleSelectedAttachments(files, triggerButton) {
      files = Array.from(files || []);

      if (!files.length) {
        return;
      }

      attachButton.disabled = true;
      imageAttachButton.disabled = true;
      setBusyStatus("Reading attachment");

      try {
        for (const file of files) {
          if (pendingAttachments.length >= maxAttachmentCount) {
            throw new Error(`Attach up to ${maxAttachmentCount} files at once.`);
          }

          pendingAttachments.push(await readAttachment(file));
        }

        renderPendingAttachments();
        setIdleStatus(`${pendingAttachments.length} file(s) attached`);
      } catch (error) {
        setIdleStatus("Attachment error");
        addMessage("assistant", error.message);
      } finally {
        attachButton.disabled = false;
        imageAttachButton.disabled = false;
        if (triggerButton && typeof triggerButton.focus === "function") {
          triggerButton.focus();
        }
      }
    }

    attachButton.addEventListener("click", () => {
      attachmentInput.click();
    });

    imageAttachButton.addEventListener("click", () => {
      imageAttachmentInput.click();
    });

    attachmentInput.addEventListener("change", async () => {
      const files = Array.from(attachmentInput.files || []);
      attachmentInput.value = "";
      await handleSelectedAttachments(files, attachButton);
    });

    imageAttachmentInput.addEventListener("change", async () => {
      const files = Array.from(imageAttachmentInput.files || []);
      imageAttachmentInput.value = "";
      await handleSelectedAttachments(files, imageAttachButton);
    });

    function appendSources(bubble, sources) {
      if (!sources || sources.length === 0) {
        return;
      }

      const sourcesBox = document.createElement("div");
      sourcesBox.className = "sources";

      for (const source of sources) {
        const link = document.createElement("a");
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noreferrer";
        link.textContent = source.title || source.url;
        sourcesBox.appendChild(link);
      }

      bubble.appendChild(sourcesBox);
    }

    function appendImages(bubble, images) {
      if (!images || images.length === 0) {
        return;
      }

      const imageBox = document.createElement("div");
      imageBox.className = "image-results";

      for (const image of images.slice(0, 9)) {
        const button = document.createElement("button");
        button.className = "image-thumb";
        button.type = "button";

        const title = image.title || image.source_name || "Image result";
        button.setAttribute("aria-label", `Preview image: ${title}`);

        const thumbnail = document.createElement("img");
        thumbnail.src = image.thumbnail_url || image.image_url;
        thumbnail.alt = title;
        thumbnail.loading = "lazy";

        const label = document.createElement("span");
        label.textContent = title;

        button.appendChild(thumbnail);
        button.appendChild(label);
        button.addEventListener("click", () => openImagePreview(image));
        imageBox.appendChild(button);
      }

      bubble.appendChild(imageBox);
    }

    function openImagePreview(image) {
      const title = image.title || image.source_name || "Image preview";
      const imageUrl = image.image_url || image.thumbnail_url;
      const sourceUrl = image.source_url || imageUrl;

      imageModalPreview.src = imageUrl;
      imageModalPreview.alt = title;
      imageModalTitle.textContent = title;
      imageModalSource.textContent = image.source_name || sourceUrl;
      imageModalOpen.href = sourceUrl;
      imageModalDownload.href = imageUrl;
      imageModal.classList.add("open");
      imageModal.setAttribute("aria-hidden", "false");
      imageModalClose.focus();
    }

    function closeImagePreview() {
      imageModal.classList.remove("open");
      imageModal.setAttribute("aria-hidden", "true");
      imageModalPreview.removeAttribute("src");
    }

    imageModalClose.addEventListener("click", closeImagePreview);
    imageModal.addEventListener("click", (event) => {
      if (event.target === imageModal) {
        closeImagePreview();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && imageModal.classList.contains("open")) {
        closeImagePreview();
      }
    });

    function addMessage(role, text, sources = [], images = [], attachments = []) {
      const row = document.createElement("div");
      row.className = `message-row ${role}`;

      let avatar = null;

      if (role === "user") {
        avatar = document.createElement("div");
        avatar.className = "avatar me-avatar";
        avatar.textContent = "Me";
        avatar.setAttribute("aria-label", "User avatar");
      }

      const bubble = document.createElement("div");
      bubble.className = `message ${role}`;
      bubble.textContent = text;

      appendAttachments(bubble, attachments);
      appendSources(bubble, sources);
      appendImages(bubble, images);

      if (avatar) {
        row.appendChild(avatar);
      }
      row.appendChild(bubble);
      messages.appendChild(row);
      chat.scrollTop = chat.scrollHeight;
      return row;
    }

    function assistantTypingText() {
      const name = (activeAssistantName || "Assistant").trim() || "Assistant";
      return `${name} is typing a message`;
    }

    function startThinkingBubble() {
      stopThinkingAnimation();

      const text = assistantTypingText();
      const row = addMessage("assistant", `${text}.`);
      const bubble = row.querySelector(".message");

      bubble.classList.add("thinking-text");
      thinkingFrame = 0;

      thinkingTimer = setInterval(() => {
        thinkingFrame = (thinkingFrame + 1) % statusFrames.length;
        bubble.textContent = `${text}${statusFrames[thinkingFrame]}`;
        chat.scrollTop = chat.scrollHeight;
      }, 420);

      return row;
    }

    function getLocalThinkingPhrase() {
      const index = Math.floor(Math.random() * localThinkingPhrases.length);
      return localThinkingPhrases[index];
    }

    function stopThinkingAnimation() {
      if (thinkingTimer) {
        clearInterval(thinkingTimer);
        thinkingTimer = null;
      }
    }

    function replaceThinkingBubble(row, text, sources = [], images = []) {
      stopThinkingAnimation();

      const bubble = row.querySelector(".message");
      bubble.classList.remove("thinking-text");
      bubble.textContent = text;

      appendSources(bubble, sources);
      appendImages(bubble, images);

      chat.scrollTop = chat.scrollHeight;
    }

    newChatButton.addEventListener("click", async () => {
      newChatButton.disabled = true;

      try {
        const data = await resetServerChat();
        resetVisibleChat();
        selectedChatId = data.current_chat_id || null;
        if (sidebarMode !== "chats") {
          sidebarMode = "chats";
          for (const tab of sidebarTabs) {
            const isActive = tab.dataset.sidebarTab === "chats";
            tab.classList.toggle("active", isActive);
            tab.setAttribute("aria-pressed", isActive ? "true" : "false");
          }
          updateSidebarPanelChrome();
        }
        if (sidebarMode === "chats" && data.chats) {
          renderSavedChats(data.chats || [], data.current_chat_id);
        } else {
          await refreshSidebar();
        }
        setIdleStatus(data.archived ? "Chat saved" : "New chat");
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      } finally {
        newChatButton.disabled = false;
      }
    });

    deleteChatButton.addEventListener("click", async () => {
      if (!selectedChatId) {
        setIdleStatus("Choose a saved chat first");
        return;
      }

      const confirmed = await confirmAction({
        title: "Delete Saved Chat",
        message: "Delete this saved chat permanently?\\n\\nThis cannot be undone.",
        confirmText: "Delete",
        danger: true,
      });

      if (!confirmed) {
        return;
      }

      deleteChatButton.disabled = true;

      try {
        const data = await deleteSelectedServerChat(selectedChatId);
        selectedChatId = null;
        if (data.cleared_current) {
          resetVisibleChat();
        }
        if (sidebarMode === "chats" && data.chats) {
          renderSavedChats(data.chats || [], null);
        } else {
          await refreshSidebar();
        }
        setIdleStatus("Saved chat deleted");
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      } finally {
        deleteChatButton.disabled = false;
      }
    });

    deleteHistoryButton.addEventListener("click", async () => {
      const confirmed = await confirmAction({
        title: "Delete All Chats",
        message: "Delete all saved chats and clear the current chat?\\n\\nThis will not delete stored memories.",
        confirmText: "Delete Chats",
        danger: true,
      });

      if (!confirmed) {
        return;
      }

      deleteHistoryButton.disabled = true;

      try {
        await deleteServerHistory();
        selectedChatId = null;
        resetVisibleChat();
        await refreshSidebar();
        setIdleStatus("All chats deleted");
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      } finally {
        deleteHistoryButton.disabled = false;
      }
    });

    addMemoryButton.addEventListener("click", async () => {
      const text = await promptAction({
        title: "Add Custom Memory",
        message: "Write a custom memory for MiddAI to keep and use later.",
        placeholder: "Example: I prefer short practical answers.",
        confirmText: "Save Memory",
      });

      if (!text || !text.trim()) {
        return;
      }

      addMemoryButton.disabled = true;

      try {
        await addServerMemory(text.trim());
        await refreshSidebar();
        setIdleStatus("Memory added");
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      } finally {
        addMemoryButton.disabled = false;
      }
    });

    deleteMemoryItemButton.addEventListener("click", async () => {
      if (!selectedMemoryId) {
        setIdleStatus("Choose a memory first");
        return;
      }

      const confirmed = await confirmAction({
        title: "Delete Memory",
        message: "Delete this selected memory permanently?\\n\\nThis cannot be undone.",
        confirmText: "Delete",
        danger: true,
      });

      if (!confirmed) {
        return;
      }

      deleteMemoryItemButton.disabled = true;

      try {
        await deleteServerMemoryItem(selectedMemoryId, selectedMemoryScope);
        selectedMemoryId = null;
        selectedMemoryScope = null;
        selectedMemoryIsCustom = false;
        await refreshSidebar();
        setIdleStatus("Memory deleted");
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      } finally {
        deleteMemoryItemButton.disabled = false;
      }
    });

    quitButton.addEventListener("click", async () => {
      const confirmed = await confirmAction({
        title: "Quit MiddAI",
        message: "This will close the model, server and MiddAI. Are you sure?",
        confirmText: "Quit",
        cancelText: "Cancel",
        danger: true,
      });

      if (!confirmed) {
        return;
      }

      quitButton.disabled = true;
      newChatButton.disabled = true;
      deleteChatButton.disabled = true;
      deleteHistoryButton.disabled = true;
      addMemoryButton.disabled = true;
      deleteMemoryItemButton.disabled = true;
      deleteMemoryButton.disabled = true;
      sendButton.disabled = true;
      searchModeButton.disabled = true;
      attachButton.disabled = true;
      imageAttachButton.disabled = true;
      depthSelectButton.disabled = true;
      hideDepthMenu();
      questionInput.disabled = true;
      stopThinkingAnimation();
      setBusyStatus("Shutting down MiddAI and LM Studio");

      try {
        await quitServer();
        setIdleStatus("MiddAI has shut down");
        window.close();
        setTimeout(() => {
          document.body.innerHTML = "<div style='min-height: 100vh; display: grid; place-items: center; color: #e5e7eb; font: 700 20px Arial, sans-serif; background: #0b1117;'>MiddAI has shut down. You can close this window.</div>";
        }, 700);
      } catch (error) {
        setIdleStatus("Shutdown error");
        addMessage("assistant", error.message);
        quitButton.disabled = false;
        newChatButton.disabled = false;
        deleteChatButton.disabled = false;
        deleteHistoryButton.disabled = false;
        addMemoryButton.disabled = false;
        deleteMemoryItemButton.disabled = false;
        deleteMemoryButton.disabled = false;
        sendButton.disabled = false;
        searchModeButton.disabled = false;
        attachButton.disabled = false;
        imageAttachButton.disabled = false;
        depthSelectButton.disabled = false;
        questionInput.disabled = false;
      }
    });

    deleteMemoryButton.addEventListener("click", async () => {
      const confirmed = await confirmAction({
        title: "Delete All Memory",
        message: "Delete all stored MiddAI memories permanently?\\n\\nThis will keep your current chat and saved chats.",
        confirmText: "Delete Memory",
        danger: true,
      });

      if (!confirmed) {
        return;
      }

      deleteMemoryButton.disabled = true;

      try {
        await deleteServerMemory();
        selectedMemoryId = null;
        selectedMemoryScope = null;
        selectedMemoryIsCustom = false;
        await refreshSidebar();
        setIdleStatus("Memory deleted");
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      } finally {
        deleteMemoryButton.disabled = false;
      }
    });

    async function hydrateVisibleChat() {
      try {
        const data = await loadServerChat();
        selectedChatId = data.current_chat_id || selectedChatId;

        if (data.fresh || !data.messages || data.messages.length === 0) {
          resetVisibleChat();
          if (sidebarMode === "chats" && data.chats) {
            renderSavedChats(data.chats || [], selectedChatId);
          } else {
            await refreshSidebar();
          }
          return;
        }

        renderSavedChat(data.messages);
        if (sidebarMode === "chats" && data.chats) {
          renderSavedChats(data.chats || [], selectedChatId);
        } else {
          await refreshSidebar();
        }
      } catch (error) {
        messages.innerHTML = "";
        addMessage("assistant", greetingText);
        setIdleStatus("Could not load saved chat");
        await refreshSidebar();
      }
    }

    async function askQuestion(question, mode, depth, attachments = []) {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, mode, depth, attachments }),
      });

      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await response.json()
        : { error: "The chat server returned an unexpected response." };

      if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
      }

      return data;
    }

    function beginStreamingBubble(row) {
      stopThinkingAnimation();

      const bubble = row.querySelector(".message");
      bubble.classList.remove("thinking-text");
      bubble.textContent = "";
      chat.scrollTop = chat.scrollHeight;
    }

    function appendStreamingText(row, text) {
      const bubble = row.querySelector(".message");
      bubble.textContent += text;
      chat.scrollTop = chat.scrollHeight;
    }

    function finishStreamingBubble(row, data) {
      stopThinkingAnimation();

      const bubble = row.querySelector(".message");
      const wasThinking = bubble.classList.contains("thinking-text");
      bubble.classList.remove("thinking-text");

      if (wasThinking) {
        bubble.textContent = "";
      }

      if (!bubble.textContent.trim() && data.answer) {
        bubble.textContent = data.answer;
      }

      appendSources(bubble, data.sources || []);
      appendImages(bubble, data.images || []);
      chat.scrollTop = chat.scrollHeight;
    }

    async function askQuestionStream(question, mode, depth, thinkingBubble, attachments = []) {
      const response = await fetch("/api/chat-stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, mode, depth, attachments }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Something went wrong.");
      }

      if (!response.body) {
        const data = await askQuestion(question, mode, depth, attachments);
        replaceThinkingBubble(
          thinkingBubble,
          data.answer,
          data.sources || [],
          data.images || [],
        );
        return data;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalData = null;
      let hasStartedText = false;

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) {
            continue;
          }

          let eventData;

          try {
            eventData = JSON.parse(line);
          } catch (error) {
            continue;
          }

          if (eventData.type === "status" && eventData.message) {
            setBusyStatus(eventData.message);
            continue;
          }

          if (eventData.type === "token") {
            if (!hasStartedText) {
              beginStreamingBubble(thinkingBubble);
              hasStartedText = true;
            }

            appendStreamingText(thinkingBubble, eventData.token || "");
            continue;
          }

          if (eventData.type === "done") {
            finalData = eventData;
            finishStreamingBubble(thinkingBubble, finalData);
            continue;
          }

          if (eventData.type === "error") {
            throw new Error(eventData.error || "Something went wrong.");
          }
        }
      }

      if (buffer.trim()) {
        try {
          const eventData = JSON.parse(buffer);

          if (eventData.type === "done") {
            finalData = eventData;
            finishStreamingBubble(thinkingBubble, finalData);
          } else if (eventData.type === "error") {
            throw new Error(eventData.error || "Something went wrong.");
          }
        } catch (error) {
          if (!finalData) {
            throw error;
          }
        }
      }

      if (!finalData) {
        throw new Error("The streamed response ended before MiddAI finished.");
      }

      return finalData;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      let question = questionInput.value.trim();

      if (!question && pendingAttachments.length === 0) {
        return;
      }

      if (!question) {
        const hasImages = pendingAttachments.some((attachment) => imageAttachmentExtensions.has(attachment.extension));
        const hasDocuments = pendingAttachments.some((attachment) => !imageAttachmentExtensions.has(attachment.extension));

        if (hasImages && hasDocuments) {
          question = "Please analyse the attached files.";
        } else if (hasImages) {
          question = "Please analyse the attached image.";
        } else {
          question = "Please analyse the attached document.";
        }
      }

      const attachmentsForRequest = pendingAttachments;
      const attachmentSummary = publicAttachmentSummary(attachmentsForRequest);
      const hasImageAttachments = attachmentsForRequest.some((attachment) => imageAttachmentExtensions.has(attachment.extension));

      addMessage("user", question, [], [], attachmentSummary);
      questionInput.value = "";
      pendingAttachments = [];
      renderPendingAttachments();
      questionInput.focus();
      const mode = getSelectedValue("mode");
      setSearchModeSelected(false);
      sendButton.disabled = true;
      searchModeButton.disabled = true;
      attachButton.disabled = true;
      imageAttachButton.disabled = true;
      depthSelectButton.disabled = true;
      hideDepthMenu();
      const depth = getSelectedValue("depth");
      const usesWeb = mode === "search" || (mode === "chat" && isExplicitSearchRequest(question));
      setBusyStatus(
        attachmentsForRequest.length
          ? hasImageAttachments
            ? "Analysing attached image"
            : "Reading attached document"
          : usesWeb
            ? "Searching and reading sources"
            : "Thinking in chat"
      );
      const thinkingBubble = startThinkingBubble();

      try {
        const data = await askQuestionStream(
          question,
          mode,
          depth,
          thinkingBubble,
          attachmentsForRequest,
        );
        const responseSources = data.sources || [];
        const responseImages = data.images || [];

        if (data.mode === "image_search") {
          setIdleStatus(`Used ${responseImages.length} image(s) - ${data.depth}`);
        } else if (data.mode === "search") {
          const imageText = responseImages.length > 0 ? `, ${responseImages.length} image(s)` : "";
          setIdleStatus(`Used ${responseSources.length} source(s)${imageText} - ${data.depth}`);
        } else {
          setIdleStatus(`Chat answer - ${data.depth}`);
        }

        await refreshSidebar();
      } catch (error) {
        replaceThinkingBubble(thinkingBubble, error.message);
        setIdleStatus("Error");
      } finally {
        stopThinkingAnimation();
        sendButton.disabled = false;
        searchModeButton.disabled = false;
        attachButton.disabled = false;
        imageAttachButton.disabled = false;
        depthSelectButton.disabled = false;
      }
    });

    questionInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    setInterval(() => {
      if (sidebarMode === "memories") {
        refreshSidebar();
      }
    }, 15000);

    async function initializeApp() {
      try {
        await refreshAssistantState();
      } catch (error) {
        setIdleStatus("Could not load assistants");
      }

      await hydrateVisibleChat();
    }

    initializeApp().catch((error) => {
      setIdleStatus("Startup error");
      addMessage("assistant", error.message || "MiddAI could not finish loading the interface.");
    });
  </script>
</body>
</html>
"""
