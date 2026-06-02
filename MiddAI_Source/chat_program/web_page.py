PAGE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MiddAI - Self-Hosted AI from Middae</title>
  <link rel="icon" href="/assets/favicon.ico?v=2" sizes="any">
  <link rel="shortcut icon" href="/assets/favicon.ico?v=2">
  <style>
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

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 50% -10%, rgba(56, 189, 248, 0.12), transparent 36%),
        linear-gradient(180deg, #0b1117 0%, #0a0f16 100%);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
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
      opacity: 0.18;
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
      position: relative;
      z-index: 1;
      height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr auto auto;
      max-width: 1240px;
      margin: 0 auto;
      padding: 18px;
      gap: 12px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      min-height: 56px;
    }

    h1 {
      margin: 0;
      color: var(--text);
      font-size: 21px;
      font-weight: 700;
    }

    .subtitle {
      margin-top: 4px;
      color: var(--muted);
      font-size: 15px;
      font-weight: 400;
    }

    .status {
      min-height: 32px;
      display: inline-flex;
      align-items: center;
      border: 1px solid rgba(56, 189, 248, 0.18);
      border-radius: 999px;
      background: var(--panel-soft);
      color: var(--accent);
      font-size: 14px;
      white-space: nowrap;
      padding: 6px 11px;
    }

    .controls {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .button-group + .button-group {
      margin-left: 14px;
    }

    .button-group {
      display: flex;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
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
      font-weight: 700;
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

    .danger-wrap {
      position: relative;
      display: inline-flex;
    }

    .new-chat-button {
      min-width: 86px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      color: var(--text);
      font: inherit;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      padding: 9px 13px;
      transition: border-color 140ms ease, background 140ms ease, color 140ms ease;
    }

    .new-chat-button:hover,
    .new-chat-button:focus {
      border-color: var(--accent);
      background: var(--accent-soft);
      outline: 0;
    }

    .danger-tooltip {
      position: absolute;
      left: 0;
      bottom: calc(100% + 8px);
      z-index: 5;
      width: max-content;
      max-width: 260px;
      border: 1px solid rgba(239, 68, 68, 0.48);
      border-radius: 10px;
      background: #1f1218;
      color: #fecaca;
      box-shadow: 0 14px 34px rgba(0, 0, 0, 0.34);
      font-size: 13px;
      font-weight: 700;
      line-height: 1.3;
      opacity: 0;
      padding: 8px 10px;
      pointer-events: none;
      transform: translateY(4px);
      transition: opacity 120ms ease, transform 120ms ease;
    }

    .danger-wrap:hover .danger-tooltip,
    .danger-wrap:focus-within .danger-tooltip {
      opacity: 1;
      transform: translateY(0);
    }

    .footer-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 38px;
    }

    .footer-left,
    .footer-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .workspace {
      min-height: 0;
      display: grid;
      grid-template-columns: 270px minmax(0, 1fr);
      gap: 12px;
    }

    .side-panel {
      min-height: 0;
      display: grid;
      grid-template-rows: auto 1fr auto;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(17, 24, 39, 0.92);
      box-shadow: var(--shadow);
    }

    .sidebar-tabs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      padding: 10px;
      border-bottom: 1px solid var(--line);
    }

    .sidebar-tab {
      min-width: 0;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      color: var(--text);
      font-size: 14px;
      padding: 0 10px;
    }

    .sidebar-tab.active {
      background: var(--user);
      border-color: rgba(96, 165, 250, 0.54);
      color: #ffffff;
    }

    .sidebar-body {
      min-height: 0;
      overflow-y: auto;
      padding: 10px;
      scrollbar-color: #334155 transparent;
    }

    .sidebar-section {
      display: grid;
      gap: 8px;
      margin-bottom: 14px;
    }

    .sidebar-heading {
      margin: 0;
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .sidebar-item {
      width: 100%;
      min-width: 0;
      display: grid;
      gap: 5px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel-soft);
      color: var(--text);
      cursor: pointer;
      padding: 10px;
      text-align: left;
    }

    .sidebar-item:hover,
    .sidebar-item:focus,
    .sidebar-item.active {
      border-color: var(--accent);
      background: rgba(56, 189, 248, 0.11);
      outline: 0;
    }

    .sidebar-item-title {
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
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

    .sidebar-actions {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      padding: 10px;
      border-top: 1px solid var(--line);
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
      min-height: 0;
      overflow-y: auto;
      background: rgba(17, 24, 39, 0.86);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      padding: 20px;
      scrollbar-color: #334155 transparent;
    }

    .messages {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .message-row {
      display: flex;
      align-items: flex-end;
      gap: 10px;
      width: 100%;
    }

    .message-row.user {
      justify-content: flex-end;
    }

    .message-row.assistant {
      justify-content: flex-start;
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
      max-width: min(760px, calc(100% - 92px));
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 13px 15px;
      line-height: 1.5;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.18);
    }

    .message.user {
      align-self: flex-end;
      background: var(--user);
      border-color: rgba(96, 165, 250, 0.42);
      color: #ffffff;
    }

    .message.assistant {
      align-self: flex-start;
      background: var(--assistant);
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
      color: var(--accent);
      text-decoration: none;
      overflow-wrap: anywhere;
    }

    .sources a:hover {
      text-decoration: underline;
    }

    .image-results {
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      white-space: normal;
    }

    .image-thumb {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel-soft);
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
      min-height: 36px;
      padding: 6px 7px;
      color: var(--text);
      font-size: 12px;
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
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 10px;
      background: rgba(17, 24, 39, 0.92);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 10px;
      box-shadow: var(--shadow);
    }

    textarea {
      width: 100%;
      min-height: 48px;
      max-height: 140px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      background: var(--panel-soft);
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

    .attach-button {
      min-width: 48px;
      width: 48px;
      padding: 0;
      font-size: 24px;
      line-height: 1;
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

    @media (max-width: 640px) {
      .shell {
        padding: 10px;
      }

      header {
        align-items: flex-start;
        flex-direction: column;
        gap: 4px;
      }

      .status {
        white-space: normal;
      }

      main {
        padding: 12px;
      }

      .workspace {
        grid-template-columns: 1fr;
      }

      .side-panel {
        max-height: 280px;
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
        grid-template-columns: 1fr auto;
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
    <header>
      <div>
        <h1>MiddAI - Self-Hosted AI from Middae</h1>
        <div class="subtitle">Offline AI with online capabilities. Search, memory, and image/file analysis.</div>
      </div>
      <div class="controls">
        <div class="button-group" role="group" aria-label="MiddAI function">
          <button class="toggle-button active" type="button" data-group="mode" data-value="chat" title="Chat normally. MiddAI can still search if you directly ask it to.">Chat</button>
          <button class="toggle-button" type="button" data-group="mode" data-value="search" title="Force MiddAI to search online for this message.">Search</button>
        </div>
        <div class="button-group" role="group" aria-label="Response speed and detail">
          <button class="toggle-button" type="button" data-group="depth" data-value="instant" title="Fastest: tiny chat answer, tiny search, no image thumbnails.">Instant</button>
          <button class="toggle-button" type="button" data-group="depth" data-value="quick" title="Short: one small paragraph with light search.">Quick</button>
          <button class="toggle-button active" type="button" data-group="depth" data-value="balanced" title="Normal: up to three short paragraphs and moderate search.">Balanced</button>
          <button class="toggle-button" type="button" data-group="depth" data-value="deep" title="Detailed: structured answers with the deepest search for this model.">Deep</button>
        </div>
      </div>
    </header>

    <div class="workspace">
      <aside class="side-panel" aria-label="Saved chats and memories">
        <div class="sidebar-tabs" role="group" aria-label="Sidebar view">
          <button class="sidebar-tab active" id="sidebar-chats-tab" type="button" data-sidebar-tab="chats">Chats</button>
          <button class="sidebar-tab" id="sidebar-memories-tab" type="button" data-sidebar-tab="memories">Memories</button>
        </div>
        <div class="sidebar-body" id="sidebar-body"></div>
        <div class="sidebar-actions chat-mode" id="sidebar-actions">
          <button class="sidebar-action chat-action" id="new-chat-button" type="button" title="Save the current chat to history and start fresh.">New Chat</button>
          <button class="sidebar-action danger chat-action" id="delete-chat-button" type="button" title="Delete the selected saved chat permanently.">Delete Chat</button>
          <button class="sidebar-action danger chat-action" id="delete-history-button" type="button" title="Delete all saved chats and clear the current chat permanently.">Delete All Chats</button>
          <button class="sidebar-action memory-action" id="add-memory-button" type="button" title="Add a custom memory MiddAI can use later.">Add Memory</button>
          <button class="sidebar-action danger memory-action" id="delete-memory-item-button" type="button" title="Delete the selected custom memory permanently.">Delete Memory</button>
          <button class="sidebar-action danger memory-action" id="delete-memory-button" type="button" title="DANGER: This permanently deletes MiddAI memory.">Delete All Memory</button>
        </div>
      </aside>

      <main id="chat">
        <div class="messages" id="messages"></div>
      </main>
    </div>

    <form id="chat-form">
      <textarea id="question" name="question" placeholder="Ask a question..." autocomplete="off"></textarea>
      <button class="attach-button" id="attach-button" type="button" title="Attach a text, DOCX, PDF, or image file">+</button>
      <button id="send-button" type="submit">Send</button>
      <input id="attachment-input" type="file" multiple hidden accept=".txt,.md,.markdown,.log,.csv,.json,.toml,.ini,.yaml,.yml,.xml,.html,.htm,.css,.js,.ts,.py,.bat,.ps1,.sql,.docx,.pdf,.jpg,.jpeg,.png,.webp">
      <div class="attachment-strip" id="attachment-strip" aria-live="polite"></div>
    </form>

    <div class="footer-row">
      <div class="footer-left">
        <div class="status" id="status">Ready</div>
      </div>
      <div class="footer-right">
        <div class="danger-wrap">
          <button class="new-chat-button" id="quit-button" type="button" aria-describedby="quit-warning">Quit</button>
          <div class="danger-tooltip" id="quit-warning">Quit MiddAI and stop LM Studio.</div>
        </div>
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

  <script>
    const form = document.getElementById("chat-form");
    const questionInput = document.getElementById("question");
    const attachButton = document.getElementById("attach-button");
    const attachmentInput = document.getElementById("attachment-input");
    const attachmentStrip = document.getElementById("attachment-strip");
    const sendButton = document.getElementById("send-button");
    const messages = document.getElementById("messages");
    const chat = document.getElementById("chat");
    const status = document.getElementById("status");
    const sidebarBody = document.getElementById("sidebar-body");
    const sidebarActions = document.getElementById("sidebar-actions");
    const sidebarTabs = document.querySelectorAll(".sidebar-tab");
    const newChatButton = document.getElementById("new-chat-button");
    const deleteChatButton = document.getElementById("delete-chat-button");
    const deleteHistoryButton = document.getElementById("delete-history-button");
    const addMemoryButton = document.getElementById("add-memory-button");
    const deleteMemoryItemButton = document.getElementById("delete-memory-item-button");
    const quitButton = document.getElementById("quit-button");
    const deleteMemoryButton = document.getElementById("delete-memory-button");
    const toggleButtons = document.querySelectorAll(".toggle-button");
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
    const greetingText = "Welcome. I'm Middae, your local assistant with online tools when needed. Local chat is ready, and web search or image search are available whenever you want them.";
    let sidebarMode = "chats";
    let selectedChatId = null;
    let selectedMemoryId = null;
    let selectedMemoryIsCustom = false;
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
      const activeButton = document.querySelector(`.toggle-button.active[data-group="${group}"]`);
      return activeButton.dataset.value;
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
    }) {
      return new Promise((resolve) => {
        const previousFocus = document.activeElement;

        appModalTitle.textContent = title;
        appModalMessage.textContent = message;
        appModalConfirm.textContent = confirmText;
        appModalCancel.textContent = cancelText;
        appModalConfirm.classList.toggle("danger", danger);
        appModalConfirm.classList.toggle("primary", !danger);
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

    function isExplicitSearchRequest(question) {
      const normalizedQuestion = question.toLowerCase();
      const searchPatterns = [
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
        /^\\s*(?:please\\s+)?i\\s+(?:would\\s+like|want|need|wanted|was\\s+looking\\s+for|am\\s+looking\\s+for)\\s+(?:to\\s+see\\s+|to\\s+find\\s+|to\\s+search\\s+for\\s+|to\\s+look\\s+up\\s+)?(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?i\\s+(?:wanted|want|would\\s+like|meant|asked)\\s+(?:you\\s+)?(?:to\\s+)?(?:search|look\\s+up|find|show|get)\\s+(?:for\\s+)?(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\\b/,
        /^\\s*(?:please\\s+)?(?:find|show|get)\\s+(?:me\\s+)?(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\\b/,
        /^\\s*(?:please\\s+)?(?:search|look\\s+up)\\s+(?:for\\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?(?:image|picture|photo)\\s+search\\s+(?:for|of)\\b/,
        /^\\s*(?:please\\s+)?(?:do|run)\\s+(?:an?\\s+)?image\\s+search\\s+(?:for|of)\\b/,
        /^\\s*(?:please\\s+)?(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?(?:what\\s+does|what\\s+do)\\s+.+?\\s+looks?\\s+like\\b/,
        /^\\s*(?:please\\s+)?show\\s+(?:me\\s+)?what\\s+.+?\\s+looks?\\s+like\\b/,
        /^\\s*(?:please\\s+)?(?:can|could|may)\\s+i\\s+see\\s+(?:an?\\s+|some\\s+|the\\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\\s+(?:of|for)\\b/,
        /^\\s*(?:please\\s+)?visual\\s+examples?\\s+(?:of|for)\\b/,
      ];

      return searchPatterns.some((pattern) => pattern.test(normalizedQuestion));
    }

    function selectButton(button) {
      const group = button.dataset.group;
      const groupButtons = document.querySelectorAll(`.toggle-button[data-group="${group}"]`);

      for (const groupButton of groupButtons) {
        groupButton.classList.remove("active");
        groupButton.setAttribute("aria-pressed", "false");
      }

      button.classList.add("active");
      button.setAttribute("aria-pressed", "true");
    }

    for (const button of toggleButtons) {
      button.setAttribute("aria-pressed", button.classList.contains("active") ? "true" : "false");
      button.addEventListener("click", () => selectButton(button));
    }

    for (const tab of sidebarTabs) {
      tab.setAttribute("aria-pressed", tab.classList.contains("active") ? "true" : "false");
      tab.addEventListener("click", () => setSidebarMode(tab.dataset.sidebarTab));
    }

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

    async function deleteServerMemoryItem(memoryId) {
      const response = await fetch("/api/delete-memory-item", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ memory_id: memoryId }),
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
        if ((message.role === "user" || message.role === "assistant") && message.content) {
          addMessage(
            message.role,
            message.content,
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

    function renderSavedChats(chats, activeChatId = selectedChatId) {
      sidebarBody.innerHTML = "";
      const chatList = chats || [];
      const activeChat = chatList.find((chatItem) => chatItem.current || chatItem.active);
      const hasRequestedActive = Boolean(activeChatId) && chatList.some(
        (chatItem) => String(chatItem.id) === String(activeChatId),
      );
      selectedChatId = hasRequestedActive ? activeChatId : (activeChat ? activeChat.id : null);

      const section = makeSidebarSection("Chats");

      if (chatList.length === 0) {
        section.appendChild(makeEmptySidebarMessage("Saved chats will appear here when you start a new chat."));
        sidebarBody.appendChild(section);
        return;
      }

      for (const chatItem of chatList) {
        const item = document.createElement("button");
        item.className = "sidebar-item";
        item.type = "button";

        const title = document.createElement("div");
        title.className = "sidebar-item-title";
        title.textContent = chatItem.title || "Saved chat";

        const meta = document.createElement("div");
        meta.className = "sidebar-item-meta";
        const metaPrefix = chatItem.current ? "Current" : friendlyDate(chatItem.ended_at);
        meta.textContent = `${metaPrefix} • ${chatItem.message_count || 0} message(s)`;

        const preview = document.createElement("div");
        preview.className = "sidebar-item-preview";
        preview.textContent = chatItem.preview || "No preview available.";

        item.appendChild(title);
        item.appendChild(meta);
        item.appendChild(preview);

        if (selectedChatId && String(selectedChatId) === String(chatItem.id)) {
          item.classList.add("active");
        }

        item.addEventListener("click", async () => {
          selectedChatId = chatItem.id;
          for (const sibling of sidebarBody.querySelectorAll(".sidebar-item")) {
            sibling.classList.remove("active");
          }
          item.classList.add("active");

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
        });

        section.appendChild(item);
      }

      sidebarBody.appendChild(section);
    }

    function renderMemoryItem(section, item) {
      const button = document.createElement("button");
      button.className = "sidebar-item";
      button.type = "button";

      const title = document.createElement("div");
      title.className = "sidebar-item-title";
      title.textContent = item.text || "Untitled memory";

      const meta = document.createElement("div");
      meta.className = "sidebar-item-meta";
      const customLabel = item.custom ? " • custom" : "";
      meta.textContent = `${titleCase(item.scope)} • ${titleCase(item.type)}${customLabel}`;

      const preview = document.createElement("div");
      preview.className = "sidebar-item-preview";
      preview.textContent = `Seen ${item.times_seen || 1} time(s). Last seen: ${friendlyDate(item.last_seen || item.created_at)}`;

      button.appendChild(title);
      button.appendChild(meta);
      button.appendChild(preview);

      button.addEventListener("click", () => {
        selectedMemoryId = item.id;
        selectedMemoryIsCustom = Boolean(item.custom);
        for (const sibling of sidebarBody.querySelectorAll(".sidebar-item")) {
          sibling.classList.remove("active");
        }
        button.classList.add("active");
      });

      section.appendChild(button);
    }

    function renderMemorySection(title, items, emptyText) {
      const section = makeSidebarSection(title);

      if (!items || items.length === 0) {
        section.appendChild(makeEmptySidebarMessage(emptyText));
        sidebarBody.appendChild(section);
        return;
      }

      for (const item of items) {
        renderMemoryItem(section, item);
      }

      sidebarBody.appendChild(section);
    }

    function renderReadableMemories(data) {
      sidebarBody.innerHTML = "";
      selectedMemoryId = null;
      selectedMemoryIsCustom = false;

      const custom = data.custom || [];
      const longTerm = (data.long || []).filter((item) => !item.custom);
      const midTerm = data.mid || [];
      const current = data.current || [];

      renderMemorySection("User memories", custom, "Custom memories you add will appear here.");
      renderMemorySection("Long term", longTerm, "No long term memories yet.");
      renderMemorySection("Mid term", midTerm, "No mid term memories yet.");
      renderMemorySection("Current", current, "Current memories are empty.");
    }

    async function refreshSidebar() {
      try {
        if (sidebarMode === "chats") {
          const data = await loadSavedChats();
          renderSavedChats(data.chats || []);
          return;
        }

        const data = await loadReadableMemories();
        renderReadableMemories(data);
      } catch (error) {
        sidebarBody.innerHTML = "";
        sidebarBody.appendChild(makeEmptySidebarMessage(error.message));
      }
    }

    function setSidebarMode(mode) {
      sidebarMode = mode;
      selectedChatId = null;
      selectedMemoryId = null;
      selectedMemoryIsCustom = false;

      for (const tab of sidebarTabs) {
        const isActive = tab.dataset.sidebarTab === mode;
        tab.classList.toggle("active", isActive);
        tab.setAttribute("aria-pressed", isActive ? "true" : "false");
      }

      sidebarActions.classList.toggle("chat-mode", mode === "chats");
      sidebarActions.classList.toggle("memory-mode", mode === "memories");
      refreshSidebar();
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
        item.textContent = `${attachment.name || "attachment"}${attachment.size ? ` (${formatFileSize(attachment.size)})` : ""}`;
        attachmentBox.appendChild(item);
      }

      bubble.appendChild(attachmentBox);
    }

    async function readAttachment(file) {
      const extension = getFileExtension(file.name);

      if (!supportedAttachmentExtensions.has(extension)) {
        throw new Error(`Unsupported file type: ${extension || file.name}.\n\n${acceptedAttachmentTypesText}`);
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
        if (extension === ".webp") {
          return {
            ...base,
            mime_type: "image/jpeg",
            data_base64: await convertImageToJpegBase64(file),
          };
        }

        const buffer = await file.arrayBuffer();
        return {
          ...base,
          data_base64: arrayBufferToBase64(buffer),
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

    attachButton.addEventListener("click", () => {
      attachmentInput.click();
    });

    attachmentInput.addEventListener("change", async () => {
      const files = Array.from(attachmentInput.files || []);
      attachmentInput.value = "";

      if (!files.length) {
        return;
      }

      attachButton.disabled = true;
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
      }
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

      for (const image of images.slice(0, 3)) {
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

      let avatar;

      if (role === "user") {
        avatar = document.createElement("div");
        avatar.className = "avatar me-avatar";
        avatar.textContent = "Me";
        avatar.setAttribute("aria-label", "User avatar");
      } else {
        avatar = document.createElement("img");
        avatar.className = "avatar";
        avatar.src = "/assets/assistant.png";
        avatar.alt = "Assistant avatar";
      }

      const bubble = document.createElement("div");
      bubble.className = `message ${role}`;
      bubble.textContent = text;

      appendAttachments(bubble, attachments);
      appendSources(bubble, sources);
      appendImages(bubble, images);

      row.appendChild(avatar);
      row.appendChild(bubble);
      messages.appendChild(row);
      chat.scrollTop = chat.scrollHeight;
      return row;
    }

    function startThinkingBubble(text) {
      stopThinkingAnimation();

      const row = addMessage("assistant", `${text} .`);
      const bubble = row.querySelector(".message");

      bubble.classList.add("thinking-text");
      thinkingFrame = 0;

      thinkingTimer = setInterval(() => {
        thinkingFrame = (thinkingFrame + 1) % statusFrames.length;
        bubble.textContent = `${text} ${statusFrames[thinkingFrame]}`;
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
        if (sidebarMode === "chats" && data.chats) {
          renderSavedChats(data.chats || [], data.current_chat_id);
        } else {
          selectedChatId = data.current_chat_id || null;
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

      if (!selectedMemoryIsCustom) {
        setIdleStatus("Only custom memories can be deleted here");
        return;
      }

      const confirmed = await confirmAction({
        title: "Delete Custom Memory",
        message: "Delete this custom memory permanently?\\n\\nThis cannot be undone.",
        confirmText: "Delete",
        danger: true,
      });

      if (!confirmed) {
        return;
      }

      deleteMemoryItemButton.disabled = true;

      try {
        await deleteServerMemoryItem(selectedMemoryId);
        selectedMemoryId = null;
        selectedMemoryIsCustom = false;
        await refreshSidebar();
        setIdleStatus("Custom memory deleted");
      } catch (error) {
        setIdleStatus("Error");
        addMessage("assistant", error.message);
      } finally {
        deleteMemoryItemButton.disabled = false;
      }
    });

    quitButton.addEventListener("click", async () => {
      quitButton.disabled = true;
      newChatButton.disabled = true;
      deleteChatButton.disabled = true;
      deleteHistoryButton.disabled = true;
      addMemoryButton.disabled = true;
      deleteMemoryItemButton.disabled = true;
      deleteMemoryButton.disabled = true;
      sendButton.disabled = true;
      attachButton.disabled = true;
      questionInput.disabled = true;
      stopThinkingAnimation();
      setBusyStatus("Shutting down MiddAI and LM Studio");

      try {
        await quitServer();
        setIdleStatus("MiddAI has shut down");
        window.close();
        setTimeout(() => {
          document.body.innerHTML = "<div style='min-height: 100vh; display: grid; place-items: center; color: #38bdf8; font: 700 20px Arial, sans-serif; background: #0b1117;'>MiddAI has shut down. You can close this window.</div>";
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
        attachButton.disabled = false;
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

        if (data.fresh || !data.messages || data.messages.length === 0) {
          resetVisibleChat();
          await refreshSidebar();
          return;
        }

        renderSavedChat(data.messages);
        await refreshSidebar();
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
      bubble.classList.remove("thinking-text");

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
      sendButton.disabled = true;
      attachButton.disabled = true;
      const mode = getSelectedValue("mode");
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
      const thinkingBubble = startThinkingBubble(usesWeb ? "Searching the woods" : getLocalThinkingPhrase());

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

        if (data.mode === "search") {
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
        attachButton.disabled = false;
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

    hydrateVisibleChat();
  </script>
</body>
</html>
"""
