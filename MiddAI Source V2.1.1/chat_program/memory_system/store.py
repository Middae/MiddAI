from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import re
import shutil
import threading

from config import (
    MEMORY_CURRENT_EXPIRE_HOURS,
    MEMORY_LONG_DECAY_DAYS,
    MEMORY_LONG_DECAY_STEP,
    MEMORY_LONG_DELETE_CONFIDENCE,
    MEMORY_MID_EXPIRE_DAYS,
)
from .continuity import ensure_chat_continuity
from .extractor import (
    ENTITY_MEMORY_TYPES,
    FURNITURE_TERMS,
    canonical_location_memory_details,
    normalize_entity_aliases,
    normalize_entity_name,
    normalize_relationships,
    object_detail_relationships,
    orient_location_relationships,
)


USER_DIR = Path.home() / "Documents" / "MiddAI"
OLD_MEMORY_FILE = USER_DIR / "memory.json"
OLD_MEMORY_BACKUP_FILE = USER_DIR / "memory_old_backup.json"
MEMORY_DIR = USER_DIR / "memory"
CHAT_EXPORT_DIR = USER_DIR / "chats"
ASSISTANT_DATA_DIR = MEMORY_DIR / "assistant_data"
LEGACY_SCOPED_MIGRATION_FILE = ASSISTANT_DATA_DIR / ".legacy_scoped_v2.json"

CHAT_MEMORY_FILE = MEMORY_DIR / "chat_memory.json"
CURRENT_MEMORY_FILE = MEMORY_DIR / "current_memory.json"
MID_MEMORY_FILE = MEMORY_DIR / "mid_memory.json"
LONG_MEMORY_FILE = MEMORY_DIR / "long_memory.json"
MEMORY_EVENTS_FILE = MEMORY_DIR / "memory_events.json"

SCOPED_MEMORY_FILENAMES = {
    CHAT_MEMORY_FILE.name,
    CURRENT_MEMORY_FILE.name,
    MID_MEMORY_FILE.name,
    LONG_MEMORY_FILE.name,
    MEMORY_EVENTS_FILE.name,
}

PREVIOUS_CHAT_LIMIT = None
MEMORY_EVENT_LIMIT = 1000
ASSISTANT_CONTEXT = threading.local()

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

INVERSE_RELATIONSHIPS = {
    "located_on": "has_on",
    "has_on": "located_on",
    "located_in": "contains",
    "contains": "located_in",
    "has_item": "owned_by",
    "owned_by": "has_item",
    "wears": "worn_by",
    "worn_by": "wears",
    "uses": "used_by",
    "used_by": "uses",
    "works_at": "employs",
    "employs": "works_at",
    "resides_in": "has_resident",
    "has_resident": "resides_in",
    "district_of": "has_district",
    "has_district": "district_of",
    "borough_of": "has_borough",
    "has_borough": "borough_of",
    "neighborhood_of": "has_neighborhood",
    "neighborhood_in": "has_neighborhood",
    "has_neighborhood": "neighborhood_of",
    "suburb_of": "has_suburb",
    "suburb_in": "has_suburb",
    "has_suburb": "suburb_of",
    "city_of": "has_city",
    "city_in": "has_city",
    "has_city": "city_in",
    "town_of": "has_town",
    "town_in": "has_town",
    "has_town": "town_in",
    "village_of": "has_village",
    "village_in": "has_village",
    "has_village": "village_in",
    "county_of": "has_county",
    "county_in": "has_county",
    "has_county": "county_in",
    "region_of": "has_region",
    "region_in": "has_region",
    "has_region": "region_in",
    "state_of": "has_state",
    "state_in": "has_state",
    "has_state": "state_in",
    "province_of": "has_province",
    "province_in": "has_province",
    "has_province": "province_in",
    "country_of": "has_country",
    "country_in": "has_country",
    "has_country": "country_in",
    "capital_of": "has_capital",
    "capital_in": "has_capital",
    "has_capital": "capital_of",
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


def active_assistant_id():
    context_assistant_id = getattr(ASSISTANT_CONTEXT, "assistant_id", None)

    if context_assistant_id:
        return context_assistant_id

    try:
        from assistants import get_active_assistant_id

        return get_active_assistant_id()
    except Exception:
        return "ai_assistant"


@contextmanager
def assistant_data_context(assistant_id):
    previous_assistant_id = getattr(ASSISTANT_CONTEXT, "assistant_id", None)
    resolved_assistant_id = assistant_id or active_assistant_id()
    ASSISTANT_CONTEXT.assistant_id = str(resolved_assistant_id or "ai_assistant")

    try:
        yield
    finally:
        if previous_assistant_id is None:
            try:
                del ASSISTANT_CONTEXT.assistant_id
            except AttributeError:
                pass
        else:
            ASSISTANT_CONTEXT.assistant_id = previous_assistant_id


def assistant_storage_key(assistant_id=None):
    assistant_id = str(assistant_id or active_assistant_id() or "ai_assistant").strip()
    safe_prefix = re.sub(r"[^a-zA-Z0-9_-]+", "_", assistant_id).strip("_")
    safe_prefix = safe_prefix[:48] or "assistant"
    digest = hashlib.sha256(assistant_id.encode("utf-8")).hexdigest()[:10]
    return f"{safe_prefix}_{digest}"


def assistant_memory_dir(assistant_id=None):
    return ASSISTANT_DATA_DIR / assistant_storage_key(assistant_id)


def assistant_export_dir(assistant_id=None):
    return CHAT_EXPORT_DIR / assistant_storage_key(assistant_id)


def scoped_memory_path(path, assistant_id=None):
    path = Path(path)

    if path.parent == MEMORY_DIR and path.name in SCOPED_MEMORY_FILENAMES:
        return assistant_memory_dir(assistant_id) / path.name

    return path


def assistant_memory_paths(assistant_id=None):
    return {
        "chat": scoped_memory_path(CHAT_MEMORY_FILE, assistant_id),
        "current": scoped_memory_path(CURRENT_MEMORY_FILE, assistant_id),
        "mid": scoped_memory_path(MID_MEMORY_FILE, assistant_id),
        "long": scoped_memory_path(LONG_MEMORY_FILE, assistant_id),
        "events": scoped_memory_path(MEMORY_EVENTS_FILE, assistant_id),
    }


def ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    ASSISTANT_DATA_DIR.mkdir(parents=True, exist_ok=True)


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
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    temp_path.replace(path)


def mark_legacy_chat_data(chat_memory):
    chat_memory = deepcopy(chat_memory)
    chat_memory["version"] = 2
    chat_memory["legacy_unscoped"] = True
    current_chat = chat_memory.get("current_chat", [])

    if current_chat:
        legacy_current = {
            "id": chat_memory.get("current_chat_id") or new_chat_id(),
            "title": clean_chat_title(current_chat),
            "started_at": chat_memory.get("current_chat_started_at"),
            "ended_at": iso_now(),
            "messages": current_chat,
            "legacy_unscoped": True,
        }
        ensure_chat_continuity(legacy_current)
        chat_memory.setdefault("previous_chats", []).append(legacy_current)
        chat_memory["current_chat"] = []
        chat_memory["current_chat_id"] = None
        chat_memory["current_chat_started_at"] = None
        chat_memory["current_chat_origin_id"] = None

    for chat in chat_memory.get("previous_chats", []):
        if isinstance(chat, dict):
            chat["legacy_unscoped"] = True
            ensure_chat_continuity(chat)

    return chat_memory


def mark_legacy_item_data(item_memory):
    item_memory = deepcopy(item_memory)
    item_memory["version"] = 2

    for item in item_memory.get("items", []):
        if not isinstance(item, dict):
            continue

        item["assistant_scope"] = "legacy_unscoped"
        item["review_required"] = True

    return item_memory


def migrate_legacy_split_files_if_needed():
    ensure_memory_dir()

    if LEGACY_SCOPED_MIGRATION_FILE.exists():
        return

    target_paths = assistant_memory_paths("ai_assistant")
    migrated_files = []
    source_defaults = {
        CHAT_MEMORY_FILE: DEFAULT_CHAT_MEMORY,
        CURRENT_MEMORY_FILE: DEFAULT_ITEM_MEMORY,
        MID_MEMORY_FILE: DEFAULT_ITEM_MEMORY,
        LONG_MEMORY_FILE: DEFAULT_ITEM_MEMORY,
        MEMORY_EVENTS_FILE: DEFAULT_EVENT_MEMORY,
    }

    for source_path, default in source_defaults.items():
        if not source_path.exists():
            continue

        data = read_json(source_path, default)

        if source_path == CHAT_MEMORY_FILE:
            data = mark_legacy_chat_data(data)
            target_path = target_paths["chat"]
        elif source_path == MEMORY_EVENTS_FILE:
            target_path = target_paths["events"]
        else:
            data = mark_legacy_item_data(data)
            target_path = {
                CURRENT_MEMORY_FILE: target_paths["current"],
                MID_MEMORY_FILE: target_paths["mid"],
                LONG_MEMORY_FILE: target_paths["long"],
            }[source_path]

        if not target_path.exists():
            write_json(target_path, data)
            migrated_files.append(source_path.name)

    write_json(
        LEGACY_SCOPED_MIGRATION_FILE,
        {
            "version": 2,
            "migrated_at": iso_now(),
            "destination_assistant_id": "ai_assistant",
            "source_files_preserved": True,
            "files": migrated_files,
        },
    )


def ensure_split_files(assistant_id=None):
    ensure_memory_dir()
    migrate_legacy_split_files_if_needed()
    paths = assistant_memory_paths(assistant_id)

    if not paths["chat"].exists():
        write_json(paths["chat"], deepcopy(DEFAULT_CHAT_MEMORY))

    for path in (paths["current"], paths["mid"], paths["long"]):
        if not path.exists():
            write_json(path, deepcopy(DEFAULT_ITEM_MEMORY))

    if not paths["events"].exists():
        write_json(paths["events"], deepcopy(DEFAULT_EVENT_MEMORY))


def load_chat_memory(assistant_id=None):
    path = scoped_memory_path(CHAT_MEMORY_FILE, assistant_id)
    memory = read_json(path, DEFAULT_CHAT_MEMORY)
    changed = False

    if not isinstance(memory.get("current_chat"), list):
        memory["current_chat"] = []

    if not isinstance(memory.get("previous_chats"), list):
        memory["previous_chats"] = []

    for chat in memory["previous_chats"]:
        changed = ensure_chat_continuity(chat) or changed

    if changed:
        write_json(path, memory)

    return memory


def save_chat_memory(memory, assistant_id=None):
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
    write_json(scoped_memory_path(CHAT_MEMORY_FILE, assistant_id), normalized)


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
    origin_id = chat_memory.get("current_chat_origin_id")

    if origin_id:
        previous_chats = chat_memory.get("previous_chats", [])
        resumed_chat = None

        for index, chat in enumerate(previous_chats):
            if str(chat.get("id") or "") == str(origin_id):
                resumed_chat = previous_chats.pop(index)
                break

        chat_memory["previous_chats"] = previous_chats
        chat_memory["current_chat_origin_id"] = None
        chat_memory["current_chat_id"] = (
            resumed_chat.get("id") if resumed_chat else str(origin_id)
        )
        chat_memory["current_chat_started_at"] = (
            resumed_chat.get("started_at") if resumed_chat else None
        ) or iso_now()
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

    export_dir = assistant_export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    title = clean_chat_title(messages)
    path = export_dir / safe_chat_filename(title, chat_record.get("ended_at"))

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


def load_item_memory(path, assistant_id=None):
    path = scoped_memory_path(path, assistant_id)
    memory = read_json(path, DEFAULT_ITEM_MEMORY)

    if not isinstance(memory.get("items"), list):
        memory["items"] = []

    repaired_items = consolidate_memory_items(memory["items"])

    if repaired_items != memory["items"]:
        memory["items"] = repaired_items
        write_json(path, memory)

    return memory


def save_item_memory(path, memory, assistant_id=None):
    normalized = deepcopy(DEFAULT_ITEM_MEMORY)
    normalized["items"] = memory.get("items", [])
    write_json(scoped_memory_path(path, assistant_id), normalized)


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
    event_path = scoped_memory_path(MEMORY_EVENTS_FILE)
    memory = read_json(event_path, DEFAULT_EVENT_MEMORY)
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
    write_json(event_path, memory)


def load_all_memory():
    ensure_split_files()
    cleanup_current_memory()
    cleanup_mid_memory()
    cleanup_long_memory()

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
        "title": clean_chat_title(current_chat),
        "started_at": chat_memory.get("current_chat_started_at"),
        "ended_at": iso_now(),
        "messages": current_chat,
    }
    ensure_chat_continuity(chat_record)
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
    export_dir = assistant_export_dir()

    if not export_dir.exists():
        return

    for path in export_dir.glob("*.txt"):
        try:
            path.unlink()
        except OSError:
            pass


def reset_all_memory():
    paths = assistant_memory_paths()
    write_json(paths["chat"], deepcopy(DEFAULT_CHAT_MEMORY))
    write_json(paths["current"], deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(paths["mid"], deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(paths["long"], deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(paths["events"], deepcopy(DEFAULT_EVENT_MEMORY))
    delete_all_chat_exports()


def reset_item_memory():
    paths = assistant_memory_paths()
    write_json(paths["current"], deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(paths["mid"], deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(paths["long"], deepcopy(DEFAULT_ITEM_MEMORY))
    write_json(paths["events"], deepcopy(DEFAULT_EVENT_MEMORY))


def delete_assistant_data(assistant_id):
    data_dir = assistant_memory_dir(assistant_id)
    export_dir = assistant_export_dir(assistant_id)

    for path in (data_dir, export_dir):
        if not path.exists():
            continue

        try:
            path.resolve().relative_to(USER_DIR.resolve())
        except (OSError, ValueError):
            raise ValueError("Refusing to delete assistant data outside MiddAI.")

        shutil.rmtree(path)


def memory_file_for_scope(scope):
    if scope == "long":
        return LONG_MEMORY_FILE

    if scope == "mid":
        return MID_MEMORY_FILE

    return CURRENT_MEMORY_FILE


def candidate_with_entity_id(candidate):
    candidate = normalize_entity_candidate(candidate)
    entity_name = str(candidate.get("entity_name") or "").strip()
    item_type = str(candidate.get("type") or "").strip()

    if entity_name and not candidate.get("entity_id"):
        entity_key = f"{item_type.casefold()}:{normalize_key(entity_name)}"
        return {
            **candidate,
            "entity_id": f"entity_{hashlib.sha256(entity_key.encode('utf-8')).hexdigest()[:16]}",
        }

    return candidate


def normalize_entity_candidate(candidate):
    normalized = deepcopy(candidate)
    item_type = str(normalized.get("type") or "").strip()

    if item_type == "object":
        entity_source = str(
            normalized.get("entity_name")
            or normalized.get("text")
            or ""
        )
        is_legacy_furniture = (
            str(normalized.get("entity_type") or "").casefold() == "furniture"
            or bool(
                re.search(
                    rf"\b(?:{FURNITURE_TERMS})\b$",
                    normalize_entity_name("object", entity_source, text=normalized.get("text"))
                    or "",
                    flags=re.IGNORECASE,
                )
            )
        )

        if is_legacy_furniture:
            normalized["type"] = "furniture"
            normalized["entity_type"] = "furniture"
            item_type = "furniture"

    if item_type not in ENTITY_MEMORY_TYPES:
        return normalized

    location_source = normalized.get("entity_name") or normalized.get("text")
    canonical_location, location_kind, location_relationships = (
        canonical_location_memory_details(
            location_source,
            text=normalized.get("text"),
            location_relation=normalized.get("location_relation"),
        )
        if item_type == "location"
        else (None, None, [])
    )
    if item_type == "location" and canonical_location:
        normalized["entity_name"] = canonical_location
    entity_name = normalize_entity_name(
        item_type,
        normalized.get("entity_name"),
        text=normalized.get("text"),
    )

    if not entity_name:
        return normalized

    normalized["entity_name"] = entity_name
    normalized["aliases"] = normalize_entity_aliases(
        item_type,
        normalized.get("aliases") or [],
        entity_name,
        text=normalized.get("text"),
    )
    relationships = normalize_relationships(normalized.get("relationships") or [])

    if item_type in {"object", "furniture"}:
        relationships = normalize_relationships(
            relationships
            + object_detail_relationships(str(normalized.get("text") or ""))
        )
    elif item_type == "location" and location_relationships:
        relationships = orient_location_relationships(
            relationships,
            location_source,
            canonical_location,
            location_relationships,
        )
        normalized["entity_type"] = location_kind or "place"

    if relationships:
        normalized["relationships"] = relationships
    else:
        normalized.pop("relationships", None)

    normalized.pop("entity_id", None)
    entity_key = f"{item_type.casefold()}:{normalize_key(entity_name)}"
    normalized["entity_id"] = (
        f"entity_{hashlib.sha256(entity_key.encode('utf-8')).hexdigest()[:16]}"
    )
    return normalized


def memory_text_score(item):
    text = str(item.get("text") or "")
    generic_markers = (
        "user mentioned this object",
        "user mentioned this place",
        "user associated this place",
        "user mentioned",
    )
    generic_penalty = 1000 if any(
        marker in text.casefold() for marker in generic_markers
    ) else 0
    return (
        len(item.get("relationships") or []) * 200
        + len(text)
        - generic_penalty
    )


def merge_memory_records(existing, candidate):
    if memory_text_score(candidate) > memory_text_score(existing):
        existing["text"] = candidate.get("text", existing.get("text", ""))

    for list_key in ("aliases", "relationships", "source_message_hashes"):
        merged_values = []

        for value in list(existing.get(list_key) or []) + list(
            candidate.get(list_key) or []
        ):
            if value not in merged_values:
                merged_values.append(value)

        if merged_values:
            existing[list_key] = merged_values

    for record in (existing, candidate):
        source_hash = record.get("source_message_hash")

        if source_hash:
            hashes = existing.setdefault("source_message_hashes", [])

            if source_hash not in hashes:
                hashes.append(source_hash)

    existing["importance"] = max(
        safe_int(existing.get("importance")),
        safe_int(candidate.get("importance")),
    )
    existing["confidence"] = max(
        safe_int(existing.get("confidence")),
        safe_int(candidate.get("confidence")),
    )
    existing["times_seen"] = max(
        safe_int(existing.get("times_seen"), 1),
        safe_int(candidate.get("times_seen"), 1),
        len(existing.get("source_message_hashes") or []),
    )

    existing_created = parse_time(existing.get("created_at"))
    candidate_created = parse_time(candidate.get("created_at"))

    if candidate_created and (
        not existing_created or candidate_created < existing_created
    ):
        existing["created_at"] = candidate.get("created_at")

    existing_seen = parse_time(existing.get("last_seen"))
    candidate_seen = parse_time(candidate.get("last_seen"))

    if candidate_seen and (not existing_seen or candidate_seen > existing_seen):
        existing["last_seen"] = candidate.get("last_seen")

    for value_key in (
        "entity_id",
        "entity_name",
        "entity_type",
        "location_relation",
    ):
        if candidate.get(value_key):
            existing[value_key] = candidate[value_key]

    return existing


def consolidate_memory_items(items):
    consolidated = []
    by_key = {}

    for raw_item in items or []:
        if not isinstance(raw_item, dict):
            continue

        item = normalize_entity_candidate(raw_item)
        key = (
            item.get("type"),
            item.get("entity_id")
            or normalize_key(item.get("text")),
        )

        if key in by_key:
            merge_memory_records(by_key[key], item)
            continue

        by_key[key] = item
        consolidated.append(item)

    source_items = deepcopy(consolidated)

    for source_item in source_items:
        add_reciprocal_relationship_to_items(consolidated, source_item)

    return consolidated


def relationship_entity_key(value):
    cleaned = re.sub(
        r"^(?:a|an|the|my|his|her|their|its)\s+",
        "",
        str(value or "").strip(),
        flags=re.IGNORECASE,
    )
    return normalize_key(cleaned)


def memory_entity_keys(item):
    return {
        relationship_entity_key(value)
        for value in [
            item.get("entity_name"),
            *(item.get("aliases") or []),
        ]
        if relationship_entity_key(value)
    }


def add_reciprocal_relationship_to_items(items, source_item):
    source_name = str(source_item.get("entity_name") or "").strip()

    if not source_name:
        return False

    changed = False
    source_keys = memory_entity_keys(source_item)

    for relationship in source_item.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue

        inverse_type = INVERSE_RELATIONSHIPS.get(
            str(relationship.get("type") or "").casefold()
        )
        target_key = relationship_entity_key(relationship.get("target"))

        if not inverse_type or not target_key or target_key in source_keys:
            continue

        for item in items:
            if target_key not in memory_entity_keys(item):
                continue

            reciprocal = {
                "type": inverse_type,
                "target": source_name,
            }
            relationships = normalize_relationships(
                list(item.get("relationships") or []) + [reciprocal]
            )

            if relationships != list(item.get("relationships") or []):
                item["relationships"] = relationships
                item["last_seen"] = iso_now()
                changed = True

    return changed


def synchronize_reciprocal_relationships(source_item):
    if not source_item.get("relationships") or not source_item.get("entity_name"):
        return

    for path in (CURRENT_MEMORY_FILE, MID_MEMORY_FILE, LONG_MEMORY_FILE):
        memory = load_item_memory(path)

        if add_reciprocal_relationship_to_items(memory.get("items", []), source_item):
            save_item_memory(path, memory)


def make_memory_item(candidate):
    candidate = candidate_with_entity_id(candidate)
    now = iso_now()
    text = candidate.get("text", "")

    item = {
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

    memory_class = memory_class_for_candidate(candidate)

    if memory_class:
        item["memory_class"] = memory_class

    for key in (
        "aliases",
        "entity_id",
        "entity_name",
        "entity_type",
        "location_relation",
        "relationships",
        "assistant_scope",
        "review_required",
        "source_message_hash",
        "source_message_hashes",
        "temporary_observation",
    ):
        if key in candidate:
            item[key] = deepcopy(candidate[key])

    return item


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def same_memory(existing, candidate):
    existing = normalize_entity_candidate(existing)
    candidate = normalize_entity_candidate(candidate)
    existing_entity_id = existing.get("entity_id")
    candidate_entity_id = candidate.get("entity_id")

    if existing_entity_id and candidate_entity_id:
        return existing_entity_id == candidate_entity_id

    if existing.get("type") != candidate.get("type"):
        return False

    return similar_text(existing.get("text"), candidate.get("text"))


def same_singleton_memory(existing, candidate):
    return existing.get("type") == candidate.get("type") == "identity"


def should_upgrade_location_text(existing, candidate):
    if existing.get("type") != candidate.get("type") or candidate.get("type") != "location":
        return False

    if not same_memory(existing, candidate):
        return False

    existing_text = str(existing.get("text") or "").casefold()
    candidate_relation = str(candidate.get("location_relation") or "").strip()
    vague_existing = (
        "user mentioned this place" in existing_text
        or "user associated this place" in existing_text
    )
    return vague_existing and bool(candidate_relation)


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


def is_explicit_protected_candidate(candidate):
    item_type = candidate.get("type")
    source = candidate.get("source")
    importance = safe_int(candidate.get("importance"))
    confidence = safe_int(candidate.get("confidence"))

    if candidate.get("protected") or candidate.get("memory_class") == "protected":
        return True

    if source == "user_defined_memory" or item_type == "custom_memory":
        return True

    if item_type in {"identity", "profession"}:
        return True

    if item_type == "location" and stable_location_text(candidate.get("text")):
        return importance >= 70 and confidence >= 75

    if item_type == "important_fact":
        return importance >= 80 and confidence >= 80

    return False


def memory_class_for_candidate(candidate):
    if candidate.get("scope") != "long":
        return None

    return "protected" if is_explicit_protected_candidate(candidate) else "decayable"


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
            and importance >= 70
            and confidence >= 75
        ) or (times_seen >= 3 and importance >= 65 and confidence >= 70)

    if item_type == "important_fact":
        return (importance >= 80 and confidence >= 80) or (
            times_seen >= 3 and importance >= 65 and confidence >= 70
        )

    if item_type == "preference":
        return times_seen >= 3 and importance >= 60 and confidence >= 65

    if item_type in {"object", "furniture", "person", "project"}:
        return times_seen >= 3 and importance >= 60 and confidence >= 65

    return False


def stable_scope_for_candidate(candidate):
    scope = candidate.get("scope", "current")

    if candidate.get("temporary_observation"):
        return scope

    if is_explicit_protected_candidate(candidate):
        return "long"

    if candidate.get("type") == "person" and scope == "current":
        return "mid"

    if scope == "long" and safe_int(candidate.get("times_seen"), 1) < 3:
        return "mid"

    if scope == "mid" and should_promote_to_long(candidate):
        return "long"

    return scope


def stable_memory_covering_candidate(candidate):
    candidate = candidate_with_entity_id(candidate)
    candidate_relationships = {
        (
            normalize_key(relationship.get("type")),
            normalize_key(relationship.get("target")),
        )
        for relationship in candidate.get("relationships", [])
        if isinstance(relationship, dict)
    }

    for scope in ("long", "mid"):
        memory = load_item_memory(memory_file_for_scope(scope))

        for existing in memory.get("items", []):
            if not same_memory(existing, candidate):
                continue

            existing_relationships = {
                (
                    normalize_key(relationship.get("type")),
                    normalize_key(relationship.get("target")),
                )
                for relationship in existing.get("relationships", [])
                if isinstance(relationship, dict)
            }

            if candidate_relationships:
                covered = candidate_relationships.issubset(
                    existing_relationships
                )
            else:
                covered = similar_text(
                    existing.get("text"),
                    candidate.get("text"),
                )

            if covered:
                return scope, existing

    return None


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
    candidate = candidate_with_entity_id(candidate)
    path = memory_file_for_scope(scope)
    memory = load_item_memory(path)

    for existing in memory["items"]:
        singleton_match = same_singleton_memory(
            existing,
            candidate,
        )
        entity_match = same_memory(existing, candidate)

        if not singleton_match and not entity_match:
            continue

        replace_text = singleton_match or should_upgrade_location_text(
            existing,
            candidate,
        ) or memory_text_score(candidate) > memory_text_score(existing)

        existing["last_seen"] = iso_now()
        candidate_hash = candidate.get("source_message_hash")
        existing_hashes = list(existing.get("source_message_hashes") or [])
        existing_single_hash = existing.get("source_message_hash")

        if existing_single_hash and existing_single_hash not in existing_hashes:
            existing_hashes.append(existing_single_hash)

        repeated_observation = bool(
            candidate_hash and candidate_hash in existing_hashes
        )

        if not repeated_observation:
            existing["times_seen"] = int(existing.get("times_seen", 1)) + 1

        if candidate_hash and candidate_hash not in existing_hashes:
            existing_hashes.append(candidate_hash)

        if existing_hashes:
            existing["source_message_hashes"] = existing_hashes[-20:]
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

        merge_memory_records(existing, candidate)

        for value_key in (
            "entity_id",
            "entity_name",
            "entity_type",
            "location_relation",
            "temporary_observation",
        ):
            if candidate.get(value_key):
                existing[value_key] = candidate[value_key]

        if scope == "long" and is_explicit_protected_candidate(candidate):
            existing["memory_class"] = "protected"

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

    if scope == "current" and candidate.get("temporary_observation"):
        stable_match = stable_memory_covering_candidate(candidate)

        if stable_match:
            _, existing = stable_match
            return existing

    scope = stable_scope_for_candidate(candidate)
    result = upsert_memory_item(scope, {**candidate, "scope": scope})
    synchronize_reciprocal_relationships(result)
    return result


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

    if item_type in {"search_context", "recent_mention"}:
        return

    if times_seen >= 3 and importance >= 45:
        promoted = deepcopy(item)
        promoted["source"] = "promoted_current_memory"
        promoted["scope"] = "mid"
        promoted.pop("temporary_observation", None)

        if item_type in {"current_context", "short_term"}:
            promoted["type"] = "important_fact"
            promoted["text"] = re.sub(
                r"^(?:Short-term user context|Current context):\s*",
                "",
                str(promoted.get("text") or ""),
                flags=re.IGNORECASE,
            ).rstrip(".")

        add_memory_candidate({**promoted, "scope": "mid"})
        remove_memory_item("current", item.get("id"))


def maybe_promote_mid_item(item):
    if not should_promote_to_long(item):
        return

    promoted = deepcopy(item)
    promoted["source"] = "promoted_mid_memory"
    upsert_memory_item("long", {**promoted, "scope": "long"})
    remove_memory_item("mid", item.get("id"))


def cleanup_current_memory():
    current_path = scoped_memory_path(CURRENT_MEMORY_FILE)

    if not current_path.exists():
        return

    memory = load_item_memory(CURRENT_MEMORY_FILE)
    cutoff = utc_now() - timedelta(hours=MEMORY_CURRENT_EXPIRE_HOURS)
    kept_items = []

    for item in memory.get("items", []):
        if item.get("type") == "person":
            repaired = deepcopy(item)
            repaired["scope"] = "mid"
            repaired["source"] = "repaired_current_person_memory"
            add_memory_candidate(repaired)
            continue

        if item.get("review_required"):
            kept_items.append(item)
            continue

        last_seen = parse_time(item.get("last_seen")) or parse_time(item.get("created_at"))

        if last_seen is None or last_seen >= cutoff:
            kept_items.append(item)
            continue

        maybe_promote_current_item(item)

    if len(kept_items) != len(memory.get("items", [])):
        memory["items"] = kept_items
        save_item_memory(current_path, memory)


def memory_activity_time(item):
    return (
        parse_time(item.get("last_retrieved_at"))
        or parse_time(item.get("last_seen"))
        or parse_time(item.get("created_at"))
    )


def cleanup_mid_memory():
    mid_path = scoped_memory_path(MID_MEMORY_FILE)

    if not mid_path.exists():
        return

    memory = load_item_memory(mid_path)
    cutoff = utc_now() - timedelta(days=MEMORY_MID_EXPIRE_DAYS)
    kept_items = []

    for item in memory.get("items", []):
        if item.get("review_required"):
            kept_items.append(item)
            continue

        last_activity = memory_activity_time(item)

        if last_activity is None or last_activity >= cutoff:
            kept_items.append(item)

    if len(kept_items) != len(memory.get("items", [])):
        memory["items"] = kept_items
        save_item_memory(mid_path, memory)


def cleanup_long_memory():
    long_path = scoped_memory_path(LONG_MEMORY_FILE)

    if not long_path.exists():
        return

    memory = load_item_memory(long_path)
    now = utc_now()
    decay_interval = timedelta(days=MEMORY_LONG_DECAY_DAYS)
    changed = False
    kept_items = []

    for item in memory.get("items", []):
        if item.get("review_required"):
            kept_items.append(item)
            continue

        if item.get("memory_class") == "protected" or is_explicit_protected_candidate(item):
            if item.get("memory_class") != "protected":
                item["memory_class"] = "protected"
                changed = True

            kept_items.append(item)
            continue

        if item.get("memory_class") != "decayable":
            item["memory_class"] = "decayable"
            changed = True

        last_activity = memory_activity_time(item)
        last_decay = parse_time(item.get("last_decay_at"))
        decay_anchor = max(
            (value for value in (last_activity, last_decay) if value),
            default=None,
        )

        if decay_anchor is None or now - decay_anchor < decay_interval:
            kept_items.append(item)
            continue

        elapsed_intervals = max(1, int((now - decay_anchor) / decay_interval))
        confidence = safe_int(item.get("confidence"), 70)
        item["confidence"] = max(
            0,
            confidence - (MEMORY_LONG_DECAY_STEP * elapsed_intervals),
        )
        item["last_decay_at"] = iso_now()
        changed = True

        if item["confidence"] > MEMORY_LONG_DELETE_CONFIDENCE:
            kept_items.append(item)

    if changed or len(kept_items) != len(memory.get("items", [])):
        memory["items"] = kept_items
        save_item_memory(long_path, memory)


def mark_memory_items_retrieved(scoped_items):
    retrieved_at = iso_now()

    for scope, selected_items in scoped_items.items():
        selected_ids = {
            str(item.get("id"))
            for item in selected_items or []
            if item.get("id")
        }

        if not selected_ids:
            continue

        path = memory_file_for_scope(scope)
        memory = load_item_memory(path)
        changed = False

        for item in memory.get("items", []):
            if str(item.get("id")) not in selected_ids:
                continue

            item["last_retrieved_at"] = retrieved_at
            item["last_seen"] = retrieved_at
            changed = True

        if changed:
            save_item_memory(path, memory)
