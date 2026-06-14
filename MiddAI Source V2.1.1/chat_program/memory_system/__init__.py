from copy import deepcopy
from datetime import timedelta
import hashlib
from pathlib import Path
import re
import threading
from uuid import uuid4

from .extractor import (
    deduplicate_structured_memories,
    extract_known_entity_details,
    extract_follow_up_memories,
    extract_memories_from_user_message,
    make_search_context,
)
from .judge import judge_memory_decision
from .migration import migrate_old_memory_if_needed
from .selector import select_memory
from .store import (
    CURRENT_MEMORY_FILE,
    LONG_MEMORY_FILE,
    MID_MEMORY_FILE,
    USER_DIR,
    add_chat_message,
    add_memory_candidate,
    append_memory_event,
    assistant_data_context,
    archive_current_chat as archive_chat_memory,
    clean_chat_title,
    delete_assistant_data,
    ensure_split_files,
    iso_now,
    load_all_memory,
    load_chat_memory,
    load_item_memory,
    mark_memory_items_retrieved,
    merge_memory_records,
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
RULE_SAFETY_TYPES = {"identity", "location", "important_fact", "profession"}
AI_PREPASS_TYPES = {
    "identity",
    "location",
    "important_fact",
    "object",
    "furniture",
    "person",
    "profession",
    "current_context",
    "short_term",
    "search_context",
}

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
    entity_name = str(memory.get("entity_name") or "").strip()

    if entity_name:
        return (
            memory.get("type", ""),
            entity_name.casefold(),
        )

    return (
        memory.get("type", ""),
        " ".join((memory.get("text") or "").casefold().split()),
    )


def source_message_hash(content):
    normalized = " ".join(str(content or "").casefold().split())

    if not normalized:
        return None

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def attach_source_message_hash(memory, content):
    message_hash = source_message_hash(content)

    if not message_hash:
        return memory

    return {**memory, "source_message_hash": message_hash}


def merge_rule_safety(primary_memories, safety_memories):
    merged = list(primary_memories)
    seen = {memory_key(memory): memory for memory in merged}

    for memory in safety_memories:
        key = memory_key(memory)

        if key in seen:
            merge_memory_records(seen[key], memory)
            continue

        merged.append(memory)
        seen[key] = memory

    return merged


def known_entity_memories():
    memory = load_all_memory()
    known = []

    for scope in ("current", "mid", "long"):
        for item in memory[scope].get("items", []):
            if not item.get("entity_name") or item.get("review_required"):
                continue

            known.append({**item, "scope": scope})

    return known


def rule_and_entity_detail_memories(content):
    extracted = extract_memories_from_user_message(content)
    details = extract_known_entity_details(content, known_entity_memories())
    return deduplicate_structured_memories(
        merge_rule_safety(extracted, details)
    )


def add_memory_candidate_with_event(memory, event_type, metadata=None):
    result = add_memory_candidate(memory)
    append_memory_event(
        event_type,
        candidate=memory,
        result=result,
        status="saved" if result else "skipped",
        metadata=metadata,
    )
    return result


def capture_rule_memories(content, event_type="rule_capture", metadata=None):
    memories = [
        attach_source_message_hash(memory, content)
        for memory in rule_and_entity_detail_memories(content)
    ]

    if not memories:
        append_memory_event(
            event_type,
            content=content,
            status="no_candidates",
            metadata=metadata,
        )
        return []

    for memory in memories:
        add_memory_candidate_with_event(memory, event_type, metadata=metadata)

    return memories


def apply_ai_memory_refinement(content, metadata=None, previous_user_messages=None):
    follow_up_memories = extract_follow_up_memories(
        content,
        previous_user_messages or [],
    )
    judge_result = judge_memory_decision(content, allow_fallback=True)
    judged_memories = judge_result["memories"]
    judge_metadata = {
        **(metadata or {}),
        "decision": judge_result["decision"],
        "trusted": judge_result["trusted"],
        "reason": judge_result["reason"],
    }
    append_memory_event(
        "ai_judge_decision",
        content=content,
        status=(
            judge_result["decision"]
            if judge_result["trusted"]
            else "untrusted_fallback"
        ),
        metadata=judge_metadata,
    )
    entity_detail_memories = extract_known_entity_details(
        content,
        known_entity_memories(),
    )

    if follow_up_memories:
        judged_memories = [
            memory
            for memory in judged_memories
            if memory.get("type") not in {"short_term", "current_context"}
        ]

    memories = [
        attach_source_message_hash(memory, content)
        for memory in merge_rule_safety(
            merge_rule_safety(judged_memories, follow_up_memories),
            entity_detail_memories,
        )
    ]

    if not memories:
        append_memory_event(
            "ai_judge_refinement",
            content=content,
            status=(
                "discarded"
                if judge_result["decision"] == "discard"
                else "no_refinements"
            ),
            metadata=judge_metadata,
        )
        return []

    for memory in memories:
        add_memory_candidate_with_event(
            memory,
            "ai_judge_refinement",
            metadata=judge_metadata,
        )

    return memories


def capture_ai_prepass_memories(content, metadata=None):
    candidates = rule_and_entity_detail_memories(content)
    prepass_memories = [
        attach_source_message_hash(memory, content)
        for memory in candidates
        if memory.get("type") in AI_PREPASS_TYPES
    ]

    for memory in prepass_memories:
        add_memory_candidate_with_event(
            memory,
            "ai_prepass_capture",
            metadata=metadata,
        )

    ignored_named_entity_hints = {
        "Also",
        "Can",
        "Could",
        "Currently",
        "Hello",
        "Hey",
        "I",
        "I'd",
        "I'll",
        "I'm",
        "I've",
        "Just",
        "My",
        "Now",
        "Okay",
        "Please",
        "Remember",
        "Right",
        "Thanks",
        "The",
        "This",
        "Today",
        "Tomorrow",
        "Tonight",
        "Wanted",
        "What",
        "Yesterday",
    }
    named_entity_hints = {
        name.casefold()
        for name in re.findall(
            r"\b[A-Z][A-Za-z0-9'_-]{2,}\b",
            str(content or ""),
        )
        if name not in ignored_named_entity_hints
    }
    covered_named_entity_hints = set()

    for memory in candidates:
        if memory.get("type") not in AI_PREPASS_TYPES:
            continue

        entity_values = [
            memory.get("entity_name"),
            *(memory.get("aliases") or []),
        ]

        for value in entity_values:
            covered_named_entity_hints.update(
                part.casefold()
                for part in re.findall(
                    r"[A-Za-z0-9'_-]{2,}",
                    str(value or ""),
                )
            )

    needs_judge = (
        not candidates
        or bool(named_entity_hints - covered_named_entity_hints)
        or any(
            memory.get("type") not in AI_PREPASS_TYPES
            for memory in candidates
        )
    )
    return prepass_memories, needs_judge


def add_candidates_from_user_content(
    content,
    use_ai_judge=True,
    event_type=None,
    metadata=None,
):
    event_metadata = metadata

    if use_ai_judge:
        judge_result = judge_memory_decision(content)
        judged_memories = judge_result["memories"]
        memories = merge_rule_safety(
            judged_memories,
            rule_safety_memories(content),
        )
        event_type = event_type or "ai_judge_capture"
        judge_metadata = {
            **(metadata or {}),
            "decision": judge_result["decision"],
            "trusted": judge_result["trusted"],
            "reason": judge_result["reason"],
        }
        event_metadata = judge_metadata
        append_memory_event(
            "ai_judge_decision",
            content=content,
            status=(
                judge_result["decision"]
                if judge_result["trusted"]
                else "untrusted_fallback"
            ),
            metadata=judge_metadata,
        )

        if not judged_memories:
            append_memory_event(
                "ai_judge_no_candidates",
                content=content,
                status=(
                    "discarded"
                    if judge_result["decision"] == "discard"
                    else "no_candidates"
                ),
                metadata=judge_metadata,
            )
    else:
        memories = rule_and_entity_detail_memories(content)
        event_type = event_type or "rule_capture"

    if not memories:
        append_memory_event(
            event_type,
            content=content,
            status=(
                "discarded"
                if use_ai_judge and judge_result["decision"] == "discard"
                else "no_candidates"
            ),
            metadata=event_metadata,
        )
        return

    for memory in memories:
        add_memory_candidate_with_event(
            memory,
            event_type,
            metadata=event_metadata,
        )


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
                add_memory_candidate_with_event(
                    memory,
                    "rule_safety_backfill",
                    metadata={"message_id": message.get("id")},
                )

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
                event_type="legacy_rule_backfill",
                metadata={"message_id": message.get("id")},
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


def chat_message_groups(chat_memory, include_archived=False):
    groups = [chat_memory.get("current_chat", [])]

    if include_archived:
        groups.extend(
            chat.get("messages", []) for chat in chat_memory.get("previous_chats", [])
        )

    return groups


def find_message(chat_memory, target_message):
    target_id = target_message.get("id")

    for messages in chat_message_groups(chat_memory, include_archived=True):
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


def previous_user_messages_for(target_message, limit=3):
    chat_memory = load_chat_memory()
    target_id = target_message.get("id")

    for messages in chat_message_groups(chat_memory):
        for index, message in enumerate(messages):
            if target_id and message.get("id") != target_id:
                continue

            if not target_id and (
                message.get("created_at") != target_message.get("created_at")
                or message.get("content") != target_message.get("content")
            ):
                continue

            previous = [
                str(item.get("content") or "")
                for item in messages[:index]
                if item.get("role") == "user"
                and str(item.get("content") or "").strip()
            ]
            return previous[-limit:]

    return []


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
            append_memory_event(
                "memory_worker_started",
                content=message.get("content", ""),
                status="started",
                metadata={
                    "message_id": message.get("id"),
                    "from_status": current_status,
                    "to_status": message.get("memory_extraction_status"),
                },
            )
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
    append_memory_event(
        "memory_worker_finished",
        content=message.get("content", ""),
        status=status,
        metadata={
            "message_id": message.get("id"),
            "final_status": status,
        },
    )


def process_pending_memory_judgements(assistant_id=None):
    with assistant_data_context(assistant_id):
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
                    if use_ai_judge:
                        apply_ai_memory_refinement(
                            message.get("content", ""),
                            metadata={"message_id": message.get("id")},
                            previous_user_messages=previous_user_messages_for(message),
                        )
                    else:
                        capture_rule_memories(
                            message.get("content", ""),
                            event_type="pending_rule_capture",
                            metadata={"message_id": message.get("id")},
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
        elif memory_mode == MEMORY_MODE_RULES:
            capture_rule_memories(
                content,
                event_type="immediate_rule_capture",
                metadata={
                    "memory_mode": memory_mode,
                    "extract_memory": extract_memory,
                    "phase": "immediate",
                },
            )
            extra_fields = {
                "memory_extraction_status": DONE_MEMORY_STATUS,
                "memory_extracted_at": iso_now(),
                "rule_memory_captured_at": iso_now(),
            }
        else:
            _prepass_memories, needs_judge = capture_ai_prepass_memories(
                content,
                metadata={
                    "memory_mode": memory_mode,
                    "extract_memory": extract_memory,
                    "phase": "immediate",
                },
            )

            extra_fields = {
                "memory_extraction_status": (
                    pending_status_for_memory_mode(memory_mode)
                    if needs_judge
                    else DONE_MEMORY_STATUS
                ),
                "rule_memory_captured_at": iso_now(),
                "rule_memory_safety_at": iso_now(),
            }

            if extract_memory and needs_judge:
                extra_fields["memory_extraction_requested_at"] = iso_now()

    if metadata:
        if extra_fields is None:
            extra_fields = {}

        extra_fields.update(metadata)

    add_chat_message(role, content, extra_fields=extra_fields)


def add_search_context(question, answer, sources):
    ensure_memory_file()
    memory = make_search_context(question, answer, sources)

    if memory:
        add_memory_candidate_with_event(
            memory,
            "search_context_capture",
            metadata={"phase": "search_context"},
        )


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

    add_memory_candidate_with_event(
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
        },
        "visual_context_capture",
        metadata={"phase": "image_analysis"},
    )


def clear_current_chat(chat_memory):
    chat_memory["current_chat"] = []
    chat_memory["current_chat_id"] = None
    chat_memory["current_chat_started_at"] = None
    chat_memory["current_chat_origin_id"] = None
    save_chat_memory(chat_memory)


def archive_current_chat():
    ensure_memory_file()

    chat_memory = load_chat_memory()
    current_chat = chat_memory.get("current_chat", [])

    if not current_chat:
        if chat_memory.get("current_chat_id") or chat_memory.get("current_chat_origin_id"):
            clear_current_chat(chat_memory)

        return None

    if current_chat and chat_memory.get("current_chat_origin_id") and not chat_memory.get("current_chat_id"):
        clear_current_chat(chat_memory)
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

    for messages in chat_message_groups(chat_memory, include_archived=True):
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

    previous_chats = chat_memory.get("previous_chats", [])
    index = find_saved_chat_index(previous_chats, chat_id)

    if index is None:
        return None

    selected_chat = previous_chats.pop(index)
    selected_id = selected_chat.get("id") or str(chat_id)
    selected_started_at = (
        selected_chat.get("started_at")
        or selected_chat.get("ended_at")
        or iso_now()
    )

    chat_memory["previous_chats"] = previous_chats
    chat_memory["current_chat"] = deepcopy(selected_messages)
    chat_memory["current_chat_id"] = selected_id
    chat_memory["current_chat_started_at"] = selected_started_at
    chat_memory["current_chat_origin_id"] = None
    delete_export_file(selected_chat.get("export_file"))
    save_chat_memory(chat_memory)
    return get_current_chat_messages()


def memory_display_title(item):
    entity_name = str(item.get("entity_name") or "").strip()

    if entity_name:
        item_type = str(item.get("type") or "memory").replace("_", " ").title()
        display_name = (
            entity_name.title()
            if entity_name == entity_name.casefold()
            else entity_name
        )
        return f"{item_type}\\{display_name}"

    return item.get("text", "") or "Untitled memory"


def memory_detail_sentences(item):
    grouped = {}

    for relationship in item.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue

        relation_type = str(relationship.get("type") or "").strip().casefold()
        target = str(relationship.get("target") or "").strip()

        if not relation_type or not target:
            continue

        targets = grouped.setdefault(relation_type, [])

        if target.casefold() not in {value.casefold() for value in targets}:
            targets.append(target)

    templates = {
        "made_of": "Is made of {targets}",
        "filled_with": "Is filled with {targets}",
        "located_on": "Is on {targets}",
        "has_on": "Has {targets} on it",
        "located_in": "Is in {targets}",
        "contains": "Contains {targets}",
        "has_item": "Has {targets}",
        "owned_by": "Is owned by {targets}",
        "model_year": "Model year: {targets}",
        "driven_by": "Is driven by {targets}",
        "wears": "Wears {targets}",
        "worn_by": "Is worn by {targets}",
        "uses": "Uses {targets}",
        "used_by": "Is used by {targets}",
        "prefers": "Prefers {targets}",
        "resides_in": "Lives in {targets}",
        "has_resident": "{targets} lives/resides here",
        "works_at": "Works at {targets}",
        "employs": "Employs {targets}",
        "district_of": "Is a district of {targets}",
        "has_district": "Has district {targets}",
        "borough_of": "Is a borough of {targets}",
        "has_borough": "Has borough {targets}",
        "neighborhood_of": "Is a neighborhood of {targets}",
        "neighborhood_in": "Is a neighborhood in {targets}",
        "has_neighborhood": "Has neighborhood {targets}",
        "suburb_of": "Is a suburb of {targets}",
        "suburb_in": "Is a suburb in {targets}",
        "has_suburb": "Has suburb {targets}",
        "city_of": "Is a city of {targets}",
        "city_in": "Is a city in {targets}",
        "has_city": "Has city {targets}",
        "town_of": "Is a town of {targets}",
        "town_in": "Is a town in {targets}",
        "has_town": "Has town {targets}",
        "village_of": "Is a village of {targets}",
        "village_in": "Is a village in {targets}",
        "has_village": "Has village {targets}",
        "county_of": "Is a county of {targets}",
        "county_in": "Is a county in {targets}",
        "has_county": "Has county {targets}",
        "region_of": "Is a region of {targets}",
        "region_in": "Is a region in {targets}",
        "has_region": "Has region {targets}",
        "state_of": "Is a state of {targets}",
        "state_in": "Is a state in {targets}",
        "has_state": "Has state {targets}",
        "province_of": "Is a province of {targets}",
        "province_in": "Is a province in {targets}",
        "has_province": "Has province {targets}",
        "country_of": "Is a country of {targets}",
        "country_in": "Is a country in {targets}",
        "has_country": "Has country {targets}",
        "capital_of": "Is the capital of {targets}",
        "capital_in": "Is a capital in {targets}",
        "has_capital": "Has capital {targets}",
    }
    details = []

    for relation_type, targets in grouped.items():
        readable_targets = ", ".join(
            target.title()
            if target == target.casefold()
            else target[:1].upper() + target[1:]
            for target in targets
        )
        template = templates.get(relation_type)

        if template:
            details.append(template.format(targets=readable_targets))
            continue

        label = relation_type.replace("_", " ").capitalize()
        details.append(f"{label}: {readable_targets}")

    return details


def format_memory_item(scope, item):
    return {
        "id": item.get("id"),
        "scope": scope,
        "type": item.get("type", "note"),
        "text": item.get("text", ""),
        "display_title": memory_display_title(item),
        "detail_sentences": memory_detail_sentences(item),
        "importance": item.get("importance"),
        "confidence": item.get("confidence"),
        "times_seen": item.get("times_seen"),
        "created_at": item.get("created_at"),
        "last_seen": item.get("last_seen"),
        "last_retrieved_at": item.get("last_retrieved_at"),
        "source": item.get("source", "chat"),
        "memory_class": item.get("memory_class"),
        "entity_name": item.get("entity_name"),
        "entity_type": item.get("entity_type"),
        "aliases": item.get("aliases", []),
        "relationships": item.get("relationships", []),
        "review_required": bool(item.get("review_required")),
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


def memory_files_for_delete(scope=None):
    normalized_scope = str(scope or "").strip().lower()
    scoped_files = {
        "current": CURRENT_MEMORY_FILE,
        "short": CURRENT_MEMORY_FILE,
        "short_term": CURRENT_MEMORY_FILE,
        "mid": MID_MEMORY_FILE,
        "mid_term": MID_MEMORY_FILE,
        "long": LONG_MEMORY_FILE,
        "long_term": LONG_MEMORY_FILE,
    }

    scoped_file = scoped_files.get(normalized_scope)

    if scoped_file:
        return [scoped_file] + [
            memory_file
            for memory_file in (CURRENT_MEMORY_FILE, MID_MEMORY_FILE, LONG_MEMORY_FILE)
            if memory_file != scoped_file
        ]

    return [CURRENT_MEMORY_FILE, MID_MEMORY_FILE, LONG_MEMORY_FILE]


def delete_memory_item(memory_id, scope=None):
    ensure_memory_file()
    normalized_memory_id = str(memory_id or "").strip()

    if not normalized_memory_id:
        return False

    deleted = False

    for memory_file in memory_files_for_delete(scope):
        memory = load_item_memory(memory_file)
        items = memory.get("items", [])
        kept_items = [
            item for item in items
            if str(item.get("id") or "").strip() != normalized_memory_id
        ]

        if len(kept_items) != len(items):
            deleted = True
            memory["items"] = kept_items
            save_item_memory(memory_file, memory)

    return deleted


def delete_user_defined_memory(memory_id):
    return delete_memory_item(memory_id)


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
    selected = select_memory(load_all_memory(), current_message, prompt_profile)
    mark_memory_items_retrieved(
        {
            "current": selected.get("current_memories", []),
            "mid": selected.get("mid_memories", []),
            "long": selected.get("long_memories", []),
        }
    )
    return selected
