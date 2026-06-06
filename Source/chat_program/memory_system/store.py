from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import json
import re

from config import MEMORY_CURRENT_EXPIRE_HOURS


USER_DIR = Path.home() / "Documents" / "MiddAI"
OLD_MEMORY_FILE = USER_DIR / "memory.json"
OLD_MEMORY_BACKUP_FILE = USER_DIR / "memory_old_backup.json"
MEMORY_DIR = USER_DIR / "memory"
CHAT_EXPORT_DIR = USER_DIR / "chats"

CHAT_MEMORY_FILE = MEMORY_DIR / "chat_memory.json"
CURRENT_MEMORY_FILE = MEMORY_DIR / "current_memory.json"
MID_MEMORY_FILE = MEMORY_DIR / "mid_memory.json"
LONG_MEMORY_FILE = MEMORY_DIR / "long_memory.json"
MEMORY_EVENTS_FILE = MEMORY_DIR / "memory_events.json"

PREVIOUS_CHAT_LIMIT = None
MEMORY_EVENT_LIMIT = 1000

DEFAULT_CHAT_MEMORY = {
    "version": 1,
    "current_chat_id": None,
    "current_chat_started_at": None,
    "current_chat_origin_id": None,
    "current_chat": [],
    "previous_chats": [],
}

DEFAULT_ITEM_MEMORY = {
    "version": 1,
    "items": [],
}

DEFAULT_EVENT_MEMORY = {
    "version": 1,
    "events": [],
}


def utc_now():
    return datetime.now(timezone.utc)


def iso_now():
    return utc_now().isoformat()


def parse_time(value):
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def normalize_key(value):
    normalized = re.sub(r"\s+", " ", value or "").strip().casefold()
    return normalized


def memory_terms(value):
    words = re.findall(r"[a-zA-Z0-9]+", (value or "").casefold())
    ignored = {
        "user",
        "mentioned",
        "this",
        "place",
        "object",
        "important",
        "fact",
        "context",
        "currently",
        "current",
        "preference",
    }
    return {word for word in words if len(word) >= 4 and word not in ignored}


def similar_text(left, right):
    left_key = normalize_key(left)
    right_key = normalize_key(right)

    if left_key == right_key:
        return True

    left_terms = memory_terms(left)
    right_terms = memory_terms(right)

    if not left_terms or not right_terms:
        return False

    overlap = len(left_terms & right_terms)
    smaller = min(len(left_terms), len(right_terms))
    larger = max(len(left_terms), len(right_terms))

    if smaller <= 3:
        return overlap == smaller and overlap / larger >= 0.5

    return overlap >= 3 and overlap / smaller >= 0.75 and overlap / larger >= 0.5


def ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path, default):
    if not path.exists():
        return deepcopy(default)

    try:
        with path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (json.JSONDecodeError, OSError):
        return deepcopy(default)

    if not isinstance(loaded, dict):
        return deepcopy(default)

    data = deepcopy(default)
    data.update(loaded)
    return data


def write_json(path, data):
    ensure_memory_dir()

    temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    temp_path.replace(path)


def ensure_split_files():
    ensure_memory_dir()

    if not CHAT_MEMORY_FILE.exists():
        write_json(CHAT_MEMORY_FILE, deepcopy(DEFAULT_CHAT_MEMORY))

    for path in (CURRENT_MEMORY_FILE, MID_MEMORY_FILE, LONG_MEMORY_FILE):
        if not path.exists():
            write_json(path, deepcopy(DEFAULT_ITEM_MEMORY))

    if not MEMORY_EVENTS_FILE.exists():
        write_json(MEMORY_EVENTS_FILE, deepcopy(DEFAULT_EVENT_MEMORY))


def load_chat_memory():
    memory = read_json(CHAT_MEMORY_FILE, DEFAULT_CHAT_MEMORY)

    if not isinstance(memory.get("current_chat"), list):
        memory["current_chat"] = []

    if not isinstance(memory.get("previous_chats"), list):
        memory["previous_chats"] = []

    return memory


def save_chat_memory(memory):
    normalized = deepcopy(DEFAULT_CHAT_MEMORY)
    current_chat = memory.get("current_chat", [])
    normalized["current_chat"] = current_chat

    if current_chat or memory.get("current_chat_id"):
        normalized["current_chat_id"] = memory.get("current_chat_id")
        normalized["current_chat_started_at"] = memory.get("current_chat_started_at")
        normalized["current_chat_origin_id"] = memory.get("current_chat_origin_id")

    previous_chats = memory.get("previous_chats", [])

    if PREVIOUS_CHAT_LIMIT:
        previous_chats = previous_chats[-PREVIOUS_CHAT_LIMIT:]

    normalized["previous_chats"] = previous_chats
    write_json(CHAT_MEMORY_FILE, normalized)


def clean_chat_title(messages):
    for message in messages:
        if message.get("role") != "user":
            continue

        content = re.sub(r"\s+", " ", message.get("content", "")).strip()

        if content:
            title = content[:58].strip()
            return title.rstrip(".,!?") or "Saved chat"

    return "Saved chat"


def safe_chat_filename(title, ended_at):
    timestamp = re.sub(r"[^0-9]", "", ended_at or iso_now())[:14] or uuid4().hex[:14]
    safe_title = re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_").lower()

    if not safe_title:
        safe_title = "saved_chat"

    return f"{timestamp}_{safe_title[:42]}.txt"


def new_chat_id():
    return f"chat_{utc_now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"


def ensure_current_chat_metadata(chat_memory):
    if chat_memory.get("current_chat_origin_id"):
        chat_memory["current_chat_origin_id"] = None
        chat_memory["current_chat_id"] = new_chat_id()
        chat_memory["current_chat_started_at"] = iso_now()
        return chat_memory

    if not chat_memory.get("current_chat_id"):
        chat_memory["current_chat_id"] = new_chat_id()

    if not chat_memory.get("current_chat_started_at"):
        chat_memory["current_chat_started_at"] = iso_now()

    return chat_memory


def export_chat_text(chat_record):
    messages = chat_record.get("messages", [])

    if not messages:
        return None

    CHAT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    title = clean_chat_title(messages)
    path = CHAT_EXPORT_DIR / safe_chat_filename(title, chat_record.get("ended_at"))

    lines = [
        f"Title: {title}",
        f"Ended: {chat_record.get('ended_at', '')}",
        "",
    ]

    for message in messages:
        role = message.get("role")
        content = (message.get("content") or "").strip()

        if role not in {"user", "assistant"} or not content:
            continue

        label = "User" if role == "user" else "MiddAI"
        lines.append(f"{label}:")
        lines.append(content)

        sources = message.get("sources")
        if role == "assistant" and isinstance(sources, list) and sources:
            lines.append("Sources:")
            for source in sources:
                url = source.get("url")
                title = source.get("title") or url

                if url:
                    lines.append(f"- {title}: {url}")

        images = message.get("images")
        if role == "assistant" and isinstance(images, list) and images:
            lines.append("Images:")
            for image in images:
                image_url = image.get("image_url") or image.get("thumbnail_url")
                title = image.get("title") or image.get("source_name") or image_url

                if image_url:
                    lines.append(f"- {title}: {image_url}")

        lines.append("")

    with path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines).strip() + "\n")

    return str(path)


def load_item_memory(path):
    memory = read_json(path, DEFAULT_ITEM_MEMORY)

    if not isinstance(memory.get("items"), list):
        memory["items"] = []

    return memory


def save_item_memory(path, memory):
    normalized = deepcopy(DEFAULT_ITEM_MEMORY)
    normalized["items"] = memory.get("items", [])
    write_json(path, normalized)


def summarize_memory_record(record):
    if not isinstance(record, dict):
        return None

    return {
        "id": record.get("id"),
        "type": record.get("type"),
        "scope": record.get("scope"),
        "text": record.get("text"),
        "importance": record.get("importance"),
        "confidence": record.get("confidence"),
        "source": record.get("source"),
    }


def append_memory_event(
    event_type,
    content=None,
    candidate=None,
    result=None,
    status=None,
    metadata=None,
):
    ensure_split_files()
    memory = read_json(MEMORY_EVENTS_FILE, DEFAULT_EVENT_MEMORY)
    events = memory.get("events", [])

    if not isinstance(events, list):
        events = []

    event = {
        "id": f"event_{utc_now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
        "type": event_type,
        "status": status or "recorded",
        "created_at": iso_now(),
    }

    if content:
        event["content_preview"] = re.sub(r"\s+", " ", content).strip()[:320]

    if isinstance(metadata, dict):
        event["metadata"] = metadata

    candidate_summary = summarize_memory_record(candidate)
    if candidate_summary:
        event["candidate"] = candidate_summary

    result_summary = summarize_memory_record(result)
    if result_summary:
        event["result"] = result_summary

    events.append(event)
    memory["events"] = events[-MEMORY_EVENT_LIMIT:]
    write_json(MEMORY_EVENTS_FILE, memory)


def load_all_memory():
    ensure_split_files()
    cleanup_current_memory()

    return {
        "chat": load_chat_memory(),
        "current": load_item_memory(CURRENT_MEMORY_FILE),
        "mid": load_item_memory(MID_MEMORY_FILE),
        "long": load_item_memory(LONG_MEMORY_FILE),
    }


def clean_message(role, content, extra_fields=None):
    cleaned_content = (content or "").strip()
    has_metadata_content = False

    if role == "assistant" and isinstance(extra_fields, dict):
        has_metadata_content = any(
            isinstance(extra_fields.get(key), list) and bool(extra_fields.get(key))
            for key in ("sources", "images", "attachments")
        )

    if role not in {"user", "assistant"} or (
        not cleaned_content and not has_metadata_content
    ):
        return None

    message = {
        "id": f"msg_{utc_now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
        "role": role,
        "content": cleaned_content,
        "created_at": iso_now(),
    }

    if extra_fields:
        message.update(extra_fields)

    return message


def add_chat_message(role, content, extra_fields=None):
    message = clean_message(role, content, extra_fields=extra_fields)

    if message is None:
        return None

    chat_memory = load_chat_memory()
    ensure_current_chat_metadata(chat_memory)
    chat_memory["current_chat"].append(message)
    save_chat_memory(chat_memory)
    return message


def archive_current_chat():
    chat_memory = load_chat_memory()
    current_chat = chat_memory.get("current_chat", [])

    if not current_chat:
        return None

    chat_record = {
        "id": chat_memory.get("current_chat_id") or new_chat_id(),
        "started_at": chat_memory.get("current_chat_started_at"),
        "ended_at": iso_now(),
        "messages": current_chat,
    }
    export_file = export_chat_text(chat_record)

    if export_file:
        chat_record["export_file"] = export_file

    chat_memory["previous_chats"].append(chat_record)
    dropped_chats = []

    if PREVIOUS_CHAT_LIMIT:
        dropped_chats = chat_memory["previous_chats"][:-PREVIOUS_CHAT_LIMIT]

    for dropped_chat in dropped_chats:
        export_file = dropped_chat.get("export_file")

        if export_file:
            try:
                Path(export_file).unlink(missing_ok=True)
            except OSError:
                pass

    if PREVIOUS_CHAT_LIMIT:
        chat_memory["previous_chats"] = chat_memory["previous_chats"][-PREVIOUS_CHAT_LIMIT:]

    chat_memory["current_chat"] = []
    chat_memory["current_chat_id"] = None
    chat_memory["current_chat_started_at"] = None
    chat_memory["current_chat_origin_id"] = None
    save_chat_memory(chat_memory)
    return chat_record


def delete_all_chat_exports():
    if not CHAT_EXPORT_DIR.exists():
        return

    for path in CHAT_EXPORT_DIR.glob("*.txt"):
        try:
            path.unlink()
        except OSError:
            pass


def reset_all_memory():
    write_json(CHAT_MEMORY_FILE, deepcopy(DEFAULT_CHAT_MEMORY))
    write_json(CURRENT_MEMORY_FILE, deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(MID_MEMORY_FILE, deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(LONG_MEMORY_FILE, deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(MEMORY_EVENTS_FILE, deepcopy(DEFAULT_EVENT_MEMORY))
    delete_all_chat_exports()


def reset_item_memory():
    write_json(CURRENT_MEMORY_FILE, deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(MID_MEMORY_FILE, deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(LONG_MEMORY_FILE, deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(MEMORY_EVENTS_FILE, deepcopy(DEFAULT_EVENT_MEMORY))


def memory_file_for_scope(scope):
    if scope == "long":
        return LONG_MEMORY_FILE

    if scope == "mid":
        return MID_MEMORY_FILE

    return CURRENT_MEMORY_FILE


def make_memory_item(candidate):
    now = iso_now()
    text = candidate.get("text", "")

    return {
        "id": f"mem_{utc_now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
        "type": candidate.get("type", "note"),
        "text": text,
        "importance": int(candidate.get("importance", 40)),
        "confidence": int(candidate.get("confidence", 70)),
        "times_seen": int(candidate.get("times_seen", 1)),
        "created_at": candidate.get("created_at") or now,
        "last_seen": candidate.get("last_seen") or now,
        "source": candidate.get("source", "chat"),
    }


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def same_memory(existing, candidate):
    if existing.get("type") != candidate.get("type"):
        return False

    return similar_text(existing.get("text"), candidate.get("text"))


def same_singleton_memory(existing, candidate):
    return existing.get("type") == candidate.get("type") == "identity"


def stable_location_text(text):
    lowered = (text or "").casefold()
    stable_markers = (
        "user lives in",
        "user lives near",
        "user is from",
        "user is based in",
        "user's home",
        "user has a",
        "regular place",
    )
    return any(marker in lowered for marker in stable_markers)


def should_promote_to_long(item):
    item_type = item.get("type")

    if item_type in {"current_context", "search_context", "short_term", "recent_mention"}:
        return False

    importance = safe_int(item.get("importance"))
    confidence = safe_int(item.get("confidence"))
    times_seen = safe_int(item.get("times_seen"), 1)

    if item_type == "identity":
        return True

    if item_type == "location":
        return (
            stable_location_text(item.get("text"))
            and importance >= 60
            and confidence >= 70
        ) or (importance >= 80 and confidence >= 75) or (
            times_seen >= 2 and importance >= 65 and confidence >= 70
        )

    if item_type == "important_fact":
        return (importance >= 80 and confidence >= 75) or (
            times_seen >= 2 and importance >= 65 and confidence >= 70
        )

    if item_type == "preference":
        return (importance >= 75 and confidence >= 70) or (
            times_seen >= 2 and importance >= 60 and confidence >= 65
        )

    if item_type in {"object", "project"}:
        return (importance >= 85 and confidence >= 70) or (
            times_seen >= 3 and importance >= 60 and confidence >= 65
        )

    return False


def stable_scope_for_candidate(candidate):
    scope = candidate.get("scope", "current")

    if candidate.get("type") == "identity":
        return "long"

    if scope == "mid" and should_promote_to_long(candidate):
        return "long"

    return scope


def remove_memory_item(scope, item_id):
    if not item_id:
        return

    path = memory_file_for_scope(scope)
    memory = load_item_memory(path)
    kept_items = [item for item in memory.get("items", []) if item.get("id") != item_id]

    if len(kept_items) != len(memory.get("items", [])):
        memory["items"] = kept_items
        save_item_memory(path, memory)


def upsert_memory_item(scope, candidate):
    path = memory_file_for_scope(scope)
    memory = load_item_memory(path)

    for existing in memory["items"]:
        replace_text = same_singleton_memory(existing, candidate)

        if replace_text or same_memory(existing, candidate):
            existing["last_seen"] = iso_now()
            existing["times_seen"] = int(existing.get("times_seen", 1)) + 1
            existing["importance"] = max(
                int(existing.get("importance", 0)),
                int(candidate.get("importance", 0)),
            )
            existing["confidence"] = max(
                int(existing.get("confidence", 0)),
                int(candidate.get("confidence", 0)),
            )
            if replace_text:
                existing["text"] = candidate.get("text", existing.get("text", ""))
            save_item_memory(path, memory)
            maybe_promote_item(scope, existing)
            return existing

    item = make_memory_item(candidate)
    memory["items"].append(item)
    save_item_memory(path, memory)

    maybe_promote_item(scope, item)

    return item


def add_memory_candidate(candidate):
    scope = candidate.get("scope", "current")

    if scope not in {"current", "mid", "long"}:
        scope = "current"

    candidate = {**candidate, "scope": scope}
    scope = stable_scope_for_candidate(candidate)
    return upsert_memory_item(scope, {**candidate, "scope": scope})


def maybe_promote_item(scope, item):
    if scope == "current":
        maybe_promote_current_item(item)
        return

    if scope == "mid":
        maybe_promote_mid_item(item)


def maybe_promote_current_item(item):
    item_type = item.get("type")
    importance = int(item.get("importance", 0))
    times_seen = int(item.get("times_seen", 1))

    if item_type in {"current_context", "search_context", "short_term", "recent_mention"}:
        return

    if importance >= 70 or (times_seen >= 2 and importance >= 45):
        promoted = deepcopy(item)
        promoted["source"] = "promoted_current_memory"
        add_memory_candidate({**promoted, "scope": "mid"})


def maybe_promote_mid_item(item):
    if not should_promote_to_long(item):
        return

    promoted = deepcopy(item)
    promoted["source"] = "promoted_mid_memory"
    upsert_memory_item("long", {**promoted, "scope": "long"})
    remove_memory_item("mid", item.get("id"))


def cleanup_current_memory():
    if not CURRENT_MEMORY_FILE.exists():
        return

    memory = load_item_memory(CURRENT_MEMORY_FILE)
    cutoff = utc_now() - timedelta(hours=MEMORY_CURRENT_EXPIRE_HOURS)
    kept_items = []

    for item in memory.get("items", []):
        last_seen = parse_time(item.get("last_seen")) or parse_time(item.get("created_at"))

        if last_seen is None or last_seen >= cutoff:
            kept_items.append(item)
            continue

        maybe_promote_current_item(item)

    if len(kept_items) != len(memory.get("items", [])):
        memory["items"] = kept_items
        save_item_memory(CURRENT_MEMORY_FILE, memory)
