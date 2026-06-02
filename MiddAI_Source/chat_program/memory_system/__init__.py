from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import threading
from uuid import uuid4

from .extractor import extract_memories_from_user_message, make_search_context
from .judge import judge_memories_from_user_message
from .migration import migrate_old_memory_if_needed
from .selector import select_memory
from .store import (
    LONG_MEMORY_FILE,
    USER_DIR,
    add_chat_message,
    add_memory_candidate,
    archive_current_chat as archive_chat_memory,
    clean_chat_title,
    ensure_split_files,
    iso_now,
    load_all_memory,
    load_chat_memory,
    load_item_memory,
    parse_time,
    reset_all_memory,
    reset_item_memory,
    save_chat_memory,
    save_item_memory,
    utc_now,
)


PENDING_AI_MEMORY_STATUS = "pending_ai"
PENDING_RULES_MEMORY_STATUS = "pending_rules"
PROCESSING_AI_MEMORY_STATUS = "processing_ai"
PROCESSING_RULES_MEMORY_STATUS = "processing_rules"
DONE_MEMORY_STATUS = "done"
FAILED_MEMORY_STATUS = "failed"
SKIPPED_MEMORY_STATUS = "skipped"
MEMORY_WORKER_LOCK = threading.Lock()

MEMORY_MODE_RULES = "rules"
MEMORY_MODE_AI_JUDGE = "ai_judge"
MEMORY_MODE_OFF = "off"
RULE_SAFETY_TYPES = {"identity", "location", "important_fact"}

PENDING_TO_PROCESSING_STATUS = {
    PENDING_AI_MEMORY_STATUS: PROCESSING_AI_MEMORY_STATUS,
    PENDING_RULES_MEMORY_STATUS: PROCESSING_RULES_MEMORY_STATUS,
}

PROCESSING_TO_PENDING_STATUS = {
    PROCESSING_AI_MEMORY_STATUS: PENDING_AI_MEMORY_STATUS,
    PROCESSING_RULES_MEMORY_STATUS: PENDING_RULES_MEMORY_STATUS,
}


def ensure_memory_file():
    migrate_old_memory_if_needed()
    ensure_split_files()
    recover_stalled_memory_extractions()
    backfill_unprocessed_chat_messages()
    backfill_rule_safety_memories()


def rule_safety_memories(content):
    memories = []

    for memory in extract_memories_from_user_message(content):
        if memory.get("type") not in RULE_SAFETY_TYPES:
            continue

        if memory.get("scope") != "long":
            continue

        memories.append(memory)

    return memories


def memory_key(memory):
    return (
        memory.get("type", ""),
        " ".join((memory.get("text") or "").casefold().split()),
    )


def merge_rule_safety(primary_memories, safety_memories):
    merged = list(primary_memories)
    seen = {memory_key(memory) for memory in merged}

    for memory in safety_memories:
        key = memory_key(memory)

        if key in seen:
            continue

        merged.append(memory)
        seen.add(key)

    return merged


def add_candidates_from_user_content(content, use_ai_judge=True):
    if use_ai_judge:
        memories = merge_rule_safety(
            judge_memories_from_user_message(content),
            rule_safety_memories(content),
        )
    else:
        memories = extract_memories_from_user_message(content)

    for memory in memories:
        add_memory_candidate(memory)


def backfill_rule_safety_memories():
    chat_memory = load_chat_memory()
    changed = False

    for messages in chat_message_groups(chat_memory):
        for message in messages:
            if message.get("role") != "user":
                continue

            if message.get("rule_memory_safety_at"):
                continue

            for memory in rule_safety_memories(message.get("content", "")):
                add_memory_candidate(memory)

            message["rule_memory_safety_at"] = iso_now()
            changed = True

    if changed:
        save_chat_memory(chat_memory)


def backfill_unprocessed_chat_messages():
    chat_memory = load_chat_memory()
    changed = False

    for messages in chat_message_groups(chat_memory):
        for message in messages:
            if message.get("role") != "user":
                continue

            if message.get("memory_extraction_status"):
                continue

            if message.get("memory_extracted_at"):
                continue

            add_candidates_from_user_content(
                message.get("content", ""),
                use_ai_judge=False,
            )
            message["memory_extracted_at"] = iso_now()
            changed = True

    if changed:
        save_chat_memory(chat_memory)


def recover_stalled_memory_extractions():
    chat_memory = load_chat_memory()
    changed = False
    cutoff = utc_now() - timedelta(minutes=5)

    for messages in chat_message_groups(chat_memory):
        for message in messages:
            current_status = message.get("memory_extraction_status")

            if current_status not in PROCESSING_TO_PENDING_STATUS:
                continue

            started_at = parse_time(message.get("memory_extraction_started_at"))

            if started_at is not None and started_at > cutoff:
                continue

            message["memory_extraction_status"] = PROCESSING_TO_PENDING_STATUS[current_status]
            changed = True

    if changed:
        save_chat_memory(chat_memory)


def chat_message_groups(chat_memory):
    groups = [chat_memory.get("current_chat", [])]
    groups.extend(
        chat.get("messages", []) for chat in chat_memory.get("previous_chats", [])
    )
    return groups


def find_message(chat_memory, target_message):
    target_id = target_message.get("id")

    for messages in chat_message_groups(chat_memory):
        for message in messages:
            if target_id and message.get("id") == target_id:
                return message

            if (
                not target_id
                and message.get("role") == target_message.get("role")
                and message.get("created_at") == target_message.get("created_at")
                and message.get("content") == target_message.get("content")
            ):
                return message

    return None


def get_next_pending_memory_message():
    chat_memory = load_chat_memory()

    for messages in chat_message_groups(chat_memory):
        for message in messages:
            if message.get("role") != "user":
                continue

            current_status = message.get("memory_extraction_status")

            if current_status not in PENDING_TO_PROCESSING_STATUS:
                continue

            message["memory_extraction_status"] = PENDING_TO_PROCESSING_STATUS[current_status]
            message["memory_extraction_started_at"] = iso_now()
            save_chat_memory(chat_memory)
            return dict(message)

    return None


def finish_pending_memory_message(target_message, status=DONE_MEMORY_STATUS):
    chat_memory = load_chat_memory()
    message = find_message(chat_memory, target_message)

    if not message:
        return

    message["memory_extraction_status"] = status
    message["memory_extracted_at"] = iso_now()

    if status != DONE_MEMORY_STATUS:
        message["memory_extraction_error_at"] = iso_now()
    else:
        message["rule_memory_safety_at"] = iso_now()

    save_chat_memory(chat_memory)


def process_pending_memory_judgements():
    with MEMORY_WORKER_LOCK:
        ensure_split_files()

        while True:
            message = get_next_pending_memory_message()

            if not message:
                return

            use_ai_judge = (
                message.get("memory_extraction_status") == PROCESSING_AI_MEMORY_STATUS
            )

            try:
                add_candidates_from_user_content(
                    message.get("content", ""),
                    use_ai_judge=use_ai_judge,
                )
            except Exception as error:
                print(f"Memory extraction failed: {error}")
                finish_pending_memory_message(message, FAILED_MEMORY_STATUS)
                continue

            finish_pending_memory_message(message, DONE_MEMORY_STATUS)


def pending_status_for_memory_mode(memory_mode):
    if memory_mode == MEMORY_MODE_OFF:
        return SKIPPED_MEMORY_STATUS

    if memory_mode == MEMORY_MODE_RULES:
        return PENDING_RULES_MEMORY_STATUS

    return PENDING_AI_MEMORY_STATUS


def add_message(
    role,
    content,
    extract_memory=True,
    memory_mode=MEMORY_MODE_AI_JUDGE,
    metadata=None,
):
    ensure_memory_file()
    extra_fields = None

    if role == "user":
        if memory_mode == MEMORY_MODE_OFF:
            extra_fields = {
                "memory_extraction_status": SKIPPED_MEMORY_STATUS,
                "memory_extracted_at": iso_now(),
            }
        elif extract_memory:
            use_ai_judge = memory_mode != MEMORY_MODE_RULES
            add_candidates_from_user_content(content, use_ai_judge=use_ai_judge)
            extra_fields = {
                "memory_extraction_status": DONE_MEMORY_STATUS,
                "memory_extracted_at": iso_now(),
            }
        else:
            for memory in rule_safety_memories(content):
                add_memory_candidate(memory)

            extra_fields = {
                "memory_extraction_status": pending_status_for_memory_mode(memory_mode),
                "rule_memory_safety_at": iso_now(),
            }

    if metadata:
        if extra_fields is None:
            extra_fields = {}

        extra_fields.update(metadata)

    add_chat_message(role, content, extra_fields=extra_fields)


def add_search_context(question, answer, sources):
    ensure_memory_file()
    memory = make_search_context(question, answer, sources)

    if memory:
        add_memory_candidate(memory)


def compact_memory_summary(text, max_chars=320):
    compacted = " ".join((text or "").split())

    if len(compacted) <= max_chars:
        return compacted

    return compacted[:max_chars].rsplit(" ", 1)[0].strip()


def add_visual_context(question, answer, images):
    ensure_memory_file()

    if not images:
        return

    image_names = [
        image.get("name")
        for image in images
        if image.get("name")
    ]
    names_text = ", ".join(image_names[:3]) or "uploaded image"
    summary = compact_memory_summary(answer)

    if not summary:
        return

    add_memory_candidate(
        {
            "type": "current_context",
            "text": (
                f"User attached image(s): {names_text}. "
                f"User asked: {question}. Visual analysis summary: {summary}"
            ),
            "scope": "current",
            "importance": 55,
            "confidence": 85,
            "source": "image_analysis",
        }
    )


def archive_current_chat():
    ensure_memory_file()

    chat_memory = load_chat_memory()
    current_chat = chat_memory.get("current_chat", [])

    if current_chat and chat_memory.get("current_chat_origin_id") and not chat_memory.get("current_chat_id"):
        chat_memory["current_chat"] = []
        chat_memory["current_chat_id"] = None
        chat_memory["current_chat_started_at"] = None
        chat_memory["current_chat_origin_id"] = None
        save_chat_memory(chat_memory)
        return None

    return archive_chat_memory()


def start_new_current_chat():
    ensure_memory_file()
    chat_memory = load_chat_memory()
    chat_memory["current_chat"] = []
    chat_memory["current_chat_id"] = (
        f"chat_{utc_now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    )
    chat_memory["current_chat_started_at"] = iso_now()
    chat_memory["current_chat_origin_id"] = None
    save_chat_memory(chat_memory)
    return chat_memory["current_chat_id"]


def delete_all_memory():
    ensure_memory_file()
    reset_item_memory()
    mark_existing_chat_messages_memory_deleted()


def mark_existing_chat_messages_memory_deleted():
    chat_memory = load_chat_memory()
    changed = False
    forgotten_at = iso_now()

    for messages in chat_message_groups(chat_memory):
        for message in messages:
            if message.get("role") != "user":
                continue

            message["memory_extraction_status"] = SKIPPED_MEMORY_STATUS
            message["memory_extracted_at"] = forgotten_at
            message["rule_memory_safety_at"] = forgotten_at
            message["memory_deleted_at"] = forgotten_at
            changed = True

    if changed:
        save_chat_memory(chat_memory)


def message_preview(messages, max_chars=110):
    for message in messages:
        content = (message.get("content") or "").strip()

        if message.get("role") == "user" and content:
            return content[:max_chars].strip()

    for message in messages:
        content = (message.get("content") or "").strip()

        if content:
            return content[:max_chars].strip()

    return ""


def list_saved_chats():
    ensure_memory_file()
    chat_memory = load_chat_memory()
    chats = []
    changed = False
    current_chat = chat_memory.get("current_chat", [])
    previous_chats = chat_memory.get("previous_chats", [])

    if (
        (current_chat or chat_memory.get("current_chat_id"))
        and not chat_memory.get("current_chat_origin_id")
    ):
        if not chat_memory.get("current_chat_id"):
            chat_memory["current_chat_id"] = (
                f"chat_{utc_now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
            )
            changed = True

        if not chat_memory.get("current_chat_started_at"):
            chat_memory["current_chat_started_at"] = iso_now()
            changed = True

        user_messages = sum(
            1 for message in current_chat if message.get("role") == "user"
        )
        assistant_messages = sum(
            1 for message in current_chat if message.get("role") == "assistant"
        )

        chats.append(
            {
                "id": chat_memory.get("current_chat_id"),
                "title": clean_chat_title(current_chat) if current_chat else "New chat",
                "preview": message_preview(current_chat) if current_chat else "No messages yet.",
                "ended_at": chat_memory.get("current_chat_started_at"),
                "message_count": len(current_chat),
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "export_file": None,
                "current": True,
                "active": True,
            }
        )

    for index, chat in enumerate(previous_chats):
        if not chat.get("id"):
            chat["id"] = f"legacy_{index}"
            changed = True

        messages = chat.get("messages", [])
        is_active_origin = (
            not chat_memory.get("current_chat_id")
            and str(chat_memory.get("current_chat_origin_id") or "") == str(chat.get("id"))
        )
        user_messages = sum(1 for message in messages if message.get("role") == "user")
        assistant_messages = sum(
            1 for message in messages if message.get("role") == "assistant"
        )

        chats.append(
            {
                "id": chat.get("id"),
                "title": clean_chat_title(messages),
                "preview": message_preview(messages),
                "ended_at": chat.get("ended_at"),
                "message_count": len(messages),
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "export_file": chat.get("export_file"),
                "current": False,
                "active": is_active_origin,
            }
        )

    if changed:
        save_chat_memory(chat_memory)

    current_items = [chat for chat in chats if chat.get("current")]
    saved_items = [chat for chat in chats if not chat.get("current")]
    return current_items + list(reversed(saved_items))


def delete_export_file(path_value):
    if not path_value:
        return

    try:
        path = Path(path_value).resolve()
        user_dir = USER_DIR.resolve()
    except OSError:
        return

    if user_dir != path and user_dir not in path.parents:
        return

    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def chat_message_signature(messages):
    signature = []

    for message in messages or []:
        role = message.get("role")
        content = (message.get("content") or "").strip()

        if role not in {"user", "assistant"} or not content:
            continue

        signature.append(
            {
                "role": role,
                "content": content,
                "sources": deepcopy(message.get("sources") or []),
                "images": deepcopy(message.get("images") or []),
                "attachments": deepcopy(message.get("attachments") or []),
            }
        )

    return signature


def same_chat_messages(left, right):
    return chat_message_signature(left) == chat_message_signature(right)


def current_matches_saved_chat(current_chat, previous_chats):
    if not current_chat:
        return False

    return any(
        same_chat_messages(current_chat, chat.get("messages", []))
        for chat in previous_chats
    )


def delete_saved_chat(chat_id):
    ensure_memory_file()
    chat_memory = load_chat_memory()
    chat_id = str(chat_id)
    current_chat_id = chat_memory.get("current_chat_id")

    if current_chat_id and str(current_chat_id) == chat_id:
        chat_memory["current_chat"] = []
        chat_memory["current_chat_id"] = None
        chat_memory["current_chat_started_at"] = None
        chat_memory["current_chat_origin_id"] = None
        save_chat_memory(chat_memory)
        return {"deleted": True, "cleared_current": True}

    previous_chats = chat_memory.get("previous_chats", [])
    index = find_saved_chat_index(previous_chats, chat_id)

    if index is None:
        return {"deleted": False, "cleared_current": False}

    chat = previous_chats.pop(index)
    deleted_messages = chat.get("messages", [])
    cleared_current = same_chat_messages(
        chat_memory.get("current_chat", []),
        deleted_messages,
    )

    if cleared_current:
        chat_memory["current_chat"] = []
        chat_memory["current_chat_id"] = None
        chat_memory["current_chat_started_at"] = None
        chat_memory["current_chat_origin_id"] = None

    if str(chat_memory.get("current_chat_origin_id") or "") == str(chat.get("id")):
        chat_memory["current_chat"] = []
        chat_memory["current_chat_id"] = None
        chat_memory["current_chat_started_at"] = None
        chat_memory["current_chat_origin_id"] = None
        cleared_current = True

    delete_export_file(chat.get("export_file"))
    chat_memory["previous_chats"] = previous_chats
    save_chat_memory(chat_memory)
    return {"deleted": True, "cleared_current": cleared_current}


def find_saved_chat_index(previous_chats, chat_id):
    chat_id = str(chat_id)

    for index, chat in enumerate(previous_chats):
        if str(chat.get("id")) == chat_id:
            return index

    try:
        index = int(chat_id)
    except (TypeError, ValueError):
        return None

    if index < 0 or index >= len(previous_chats):
        return None

    return index


def delete_chat_history():
    ensure_memory_file()
    chat_memory = load_chat_memory()

    for chat in chat_memory.get("previous_chats", []):
        delete_export_file(chat.get("export_file"))

    chat_memory["previous_chats"] = []
    chat_memory["current_chat"] = []
    chat_memory["current_chat_id"] = None
    chat_memory["current_chat_started_at"] = None
    chat_memory["current_chat_origin_id"] = None
    save_chat_memory(chat_memory)


def get_saved_chat_messages(chat_id):
    ensure_memory_file()
    chat_memory = load_chat_memory()

    if (
        chat_memory.get("current_chat_id")
        and str(chat_memory.get("current_chat_id")) == str(chat_id)
    ):
        return deepcopy(chat_memory.get("current_chat", []))

    previous_chats = chat_memory.get("previous_chats", [])
    index = find_saved_chat_index(previous_chats, chat_id)

    if index is None:
        return None

    messages = previous_chats[index].get("messages", [])

    if not isinstance(messages, list):
        return None

    return deepcopy(messages)


def open_saved_chat(chat_id):
    selected_messages = get_saved_chat_messages(chat_id)

    if selected_messages is None:
        return None

    chat_memory = load_chat_memory()
    if (
        chat_memory.get("current_chat_id")
        and str(chat_memory.get("current_chat_id")) == str(chat_id)
    ):
        return get_current_chat_messages()

    current_chat = chat_memory.get("current_chat", [])

    if (
        current_chat
        and chat_memory.get("current_chat_id")
        and current_chat != selected_messages
    ):
        archive_chat_memory()
        chat_memory = load_chat_memory()

    chat_memory["current_chat"] = deepcopy(selected_messages)
    chat_memory["current_chat_id"] = None
    chat_memory["current_chat_started_at"] = None
    chat_memory["current_chat_origin_id"] = str(chat_id)
    save_chat_memory(chat_memory)
    return get_current_chat_messages()


def format_memory_item(scope, item):
    return {
        "id": item.get("id"),
        "scope": scope,
        "type": item.get("type", "note"),
        "text": item.get("text", ""),
        "importance": item.get("importance"),
        "confidence": item.get("confidence"),
        "times_seen": item.get("times_seen"),
        "created_at": item.get("created_at"),
        "last_seen": item.get("last_seen"),
        "source": item.get("source", "chat"),
        "custom": item.get("source") == "user_defined_memory"
        or item.get("type") == "custom_memory",
    }


def list_readable_memories():
    ensure_memory_file()
    memory = load_all_memory()
    current_items = [
        format_memory_item("current", item)
        for item in memory["current"].get("items", [])
    ]
    mid_items = [
        format_memory_item("mid", item)
        for item in memory["mid"].get("items", [])
    ]
    long_items = [
        format_memory_item("long", item)
        for item in memory["long"].get("items", [])
    ]
    custom_items = [item for item in long_items if item["custom"]]

    return {
        "current": current_items,
        "mid": mid_items,
        "long": long_items,
        "custom": custom_items,
    }


def add_user_defined_memory(text):
    ensure_memory_file()
    cleaned_text = (text or "").strip()

    if not cleaned_text:
        return None

    return add_memory_candidate(
        {
            "scope": "long",
            "type": "custom_memory",
            "text": cleaned_text,
            "importance": 85,
            "confidence": 100,
            "source": "user_defined_memory",
        }
    )


def delete_user_defined_memory(memory_id):
    ensure_memory_file()
    memory = load_item_memory(LONG_MEMORY_FILE)
    kept_items = []
    deleted = False

    for item in memory.get("items", []):
        is_target = item.get("id") == memory_id
        is_custom = (
            item.get("source") == "user_defined_memory"
            or item.get("type") == "custom_memory"
        )

        if is_target and is_custom:
            deleted = True
            continue

        kept_items.append(item)

    if deleted:
        memory["items"] = kept_items
        save_item_memory(LONG_MEMORY_FILE, memory)

    return deleted


def get_current_chat_messages():
    ensure_memory_file()
    chat_memory = load_chat_memory()
    messages = []

    for message in chat_memory.get("current_chat", []):
        role = message.get("role")
        content = message.get("content")

        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            clean_message = {
                "role": role,
                "content": content.strip(),
            }

            sources = message.get("sources")
            images = message.get("images")
            attachments = message.get("attachments")

            if isinstance(sources, list):
                clean_message["sources"] = sources

            if isinstance(images, list):
                clean_message["images"] = images

            if isinstance(attachments, list):
                clean_message["attachments"] = attachments

            messages.append(clean_message)

    return messages


def get_selected_memory(current_message="", prompt_profile="standard"):
    ensure_memory_file()
    return select_memory(load_all_memory(), current_message, prompt_profile)
