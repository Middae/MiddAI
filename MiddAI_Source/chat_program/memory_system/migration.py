from copy import deepcopy
import json

from .store import (
    CHAT_MEMORY_FILE,
    CURRENT_MEMORY_FILE,
    LONG_MEMORY_FILE,
    MID_MEMORY_FILE,
    OLD_MEMORY_BACKUP_FILE,
    OLD_MEMORY_FILE,
    DEFAULT_CHAT_MEMORY,
    DEFAULT_ITEM_MEMORY,
    iso_now,
    write_json,
)


def split_files_exist():
    return any(
        path.exists()
        for path in (
            CHAT_MEMORY_FILE,
            CURRENT_MEMORY_FILE,
            MID_MEMORY_FILE,
            LONG_MEMORY_FILE,
        )
    )


def unique_backup_path():
    if not OLD_MEMORY_BACKUP_FILE.exists():
        return OLD_MEMORY_BACKUP_FILE

    timestamp = iso_now().replace(":", "").replace("+", "_")
    return OLD_MEMORY_BACKUP_FILE.with_name(f"memory_old_backup_{timestamp}.json")


def memory_item(item_type, text, scope, importance, confidence, source="old_memory"):
    now = iso_now()

    return {
        "id": f"migrated_{item_type}_{abs(hash((item_type, text))) % 100000000}",
        "type": item_type,
        "text": text,
        "importance": importance,
        "confidence": confidence,
        "times_seen": 1,
        "created_at": now,
        "last_seen": now,
        "source": source,
        "scope": scope,
    }


def clean_text(value):
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def migrate_profile(profile):
    current_items = []
    mid_items = []
    long_items = []

    name = clean_text(profile.get("name")) if isinstance(profile, dict) else None

    if name:
        long_items.append(
            memory_item(
                "identity",
                f"User's name is {name}.",
                "long",
                90,
                95,
            )
        )

    for place in profile.get("places", []) if isinstance(profile, dict) else []:
        cleaned = clean_text(place)

        if cleaned:
            mid_items.append(
                memory_item("location", f"User mentioned this place: {cleaned}.", "mid", 55, 75)
            )

    for preference in profile.get("preferences", []) if isinstance(profile, dict) else []:
        cleaned = clean_text(preference)

        if cleaned:
            long_items.append(
                memory_item("preference", f"User preference: {cleaned}.", "long", 70, 80)
            )

    for fact in profile.get("important_facts", []) if isinstance(profile, dict) else []:
        cleaned = clean_text(fact)

        if cleaned:
            long_items.append(
                memory_item("important_fact", f"Important user fact: {cleaned}.", "long", 80, 80)
            )

    for context in profile.get("current_context", []) if isinstance(profile, dict) else []:
        cleaned = clean_text(context)

        if cleaned:
            current_items.append(
                memory_item("current_context", cleaned, "current", 40, 70)
            )

    return current_items, mid_items, long_items


def migrate_old_memory_if_needed():
    if not OLD_MEMORY_FILE.exists() or split_files_exist():
        return False

    try:
        with OLD_MEMORY_FILE.open("r", encoding="utf-8") as file:
            old_memory = json.load(file)
    except (json.JSONDecodeError, OSError):
        old_memory = {}

    chat_memory = deepcopy(DEFAULT_CHAT_MEMORY)
    current_memory = deepcopy(DEFAULT_ITEM_MEMORY)
    mid_memory = deepcopy(DEFAULT_ITEM_MEMORY)
    long_memory = deepcopy(DEFAULT_ITEM_MEMORY)

    if isinstance(old_memory, dict):
        current_chat = old_memory.get("current_chat")
        previous_chats = old_memory.get("previous_chats")

        if isinstance(current_chat, list):
            chat_memory["current_chat"] = current_chat

        if isinstance(previous_chats, list):
            chat_memory["previous_chats"] = previous_chats

        profile = old_memory.get("profile", {})
        current_items, mid_items, long_items = migrate_profile(profile)
        current_memory["items"].extend(current_items)
        mid_memory["items"].extend(mid_items)
        long_memory["items"].extend(long_items)

    write_json(CHAT_MEMORY_FILE, chat_memory)
    write_json(CURRENT_MEMORY_FILE, current_memory)
    write_json(MID_MEMORY_FILE, mid_memory)
    write_json(LONG_MEMORY_FILE, long_memory)

    OLD_MEMORY_FILE.replace(unique_backup_path())
    return True
