from datetime import timedelta
import re

from config import (
    MEMORY_BRIDGE_EVERY_NTH,
    MEMORY_BRIDGE_LOOKBACK_MESSAGES,
    MEMORY_CURRENT_VISIBLE_MINUTES,
    MEMORY_FIRST_MESSAGES,
    MEMORY_LAST_MESSAGES,
    MEMORY_MAX_MESSAGE_CHARS,
)
from .store import parse_time, utc_now


PHI_WORKDESK_LAST_USER_MESSAGES = 8
PHI_WORKDESK_MAX_MESSAGE_CHARS = 360

STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "can",
    "could",
    "does",
    "for",
    "from",
    "have",
    "how",
    "into",
    "is",
    "its",
    "latest",
    "more",
    "new",
    "news",
    "of",
    "on",
    "or",
    "please",
    "should",
    "show",
    "tell",
    "than",
    "that",
    "the",
    "their",
    "there",
    "they",
    "this",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "would",
    "you",
}


def trim_content(content, max_chars=MEMORY_MAX_MESSAGE_CHARS):
    if len(content) <= max_chars:
        return content

    return content[:max_chars].rstrip() + "..."


def keywords(text):
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return {word for word in words if len(word) >= 4 and word not in STOP_WORDS}


def should_include_previous_chats(message):
    normalized_message = (message or "").lower()
    trigger_phrases = [
        "last chat",
        "last conversation",
        "previous chat",
        "previous conversation",
        "past chat",
        "past conversation",
        "from our last chat",
        "from our last conversation",
        "from a previous chat",
        "from a previous conversation",
        "remember when",
        "do you remember",
        "what did i ask",
        "what did i say",
        "what were we talking about",
        "what did we talk about",
    ]

    return any(phrase in normalized_message for phrase in trigger_phrases)


def should_include_personal_memory(message):
    normalized_message = (message or "").lower()
    trigger_phrases = [
        "who am i",
        "who i am",
        "do you know me",
        "do you know who i am",
        "what do you know about me",
        "what do you remember about me",
        "what have you remembered",
        "what is my name",
        "what's my name",
        "where do i live",
        "where am i from",
        "my location",
        "my places",
        "my preferences",
        "my objects",
        "my stuff",
    ]

    return any(phrase in normalized_message for phrase in trigger_phrases)


def select_chat_messages(messages):
    total_messages = len(messages)

    if total_messages == 0:
        return []

    selected_indexes = set()
    first_end = min(MEMORY_FIRST_MESSAGES, total_messages)
    selected_indexes.update(range(first_end))

    recent_start = max(0, total_messages - MEMORY_LAST_MESSAGES)
    selected_indexes.update(range(recent_start, total_messages))

    bridge_start = max(0, recent_start - MEMORY_BRIDGE_LOOKBACK_MESSAGES)

    for index in range(bridge_start, recent_start, MEMORY_BRIDGE_EVERY_NTH):
        selected_indexes.add(index)

    selected_messages = []

    for index in sorted(selected_indexes):
        message = messages[index]
        role = message.get("role")
        content = message.get("content")

        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue

        selected_messages.append(
            {
                "role": role,
                "content": trim_content(content.strip()),
            }
        )

    return selected_messages


def select_phi_workdesk_messages(messages):
    selected_messages = []

    for message in reversed(messages):
        role = message.get("role")
        content = message.get("content")

        # Phi can echo older assistant replies, so its compact desk keeps
        # recent user turns only.
        if role != "user" or not isinstance(content, str):
            continue

        selected_messages.append(
            {
                "role": role,
                "content": trim_content(
                    content.strip(),
                    max_chars=PHI_WORKDESK_MAX_MESSAGE_CHARS,
                ),
            }
        )

        if len(selected_messages) >= PHI_WORKDESK_LAST_USER_MESSAGES:
            break

    return list(reversed(selected_messages))


def select_previous_chats(previous_chats):
    selected_chats = []

    for chat in previous_chats[-5:]:
        messages = chat.get("messages", [])
        selected_messages = []

        for message in messages[-10:]:
            role = message.get("role")
            content = message.get("content")

            if role in {"user", "assistant"} and isinstance(content, str):
                selected_messages.append(
                    {
                        "role": role,
                        "content": trim_content(content.strip()),
                    }
                )

        selected_chats.append(
            {
                "ended_at": chat.get("ended_at"),
                "messages": selected_messages,
            }
        )

    return selected_chats


def is_current_memory_visible(item):
    last_seen = parse_time(item.get("last_seen")) or parse_time(item.get("created_at"))

    if last_seen is None:
        return True

    cutoff = utc_now() - timedelta(minutes=MEMORY_CURRENT_VISIBLE_MINUTES)
    return last_seen >= cutoff


def relevant_score(item, message_keywords):
    item_keywords = keywords(item.get("text", ""))
    overlap = len(message_keywords & item_keywords)
    importance = int(item.get("importance", 0))
    confidence = int(item.get("confidence", 0))
    times_seen = int(item.get("times_seen", 1))

    return importance + (confidence // 10) + (times_seen * 3) + (overlap * 25)


def select_relevant_items(items, message, limit=8, always_include_types=None):
    always_include_types = set(always_include_types or [])
    message_keywords = keywords(message)
    selected = []
    scored = []

    for item in items:
        item_type = item.get("type")

        if item_type in always_include_types:
            selected.append(item)
            continue

        score = relevant_score(item, message_keywords)

        if score >= 70:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected.extend(item for _score, item in scored)

    return selected[:limit]


def select_current_items(current_memory):
    items = current_memory.get("items", [])
    return [item for item in items if is_current_memory_visible(item)]


def build_profile(long_items, mid_items):
    profile = {
        "name": None,
        "places": [],
        "preferences": [],
        "important_facts": [],
        "current_context": [],
        "objects": [],
    }

    for item in long_items + mid_items:
        text = item.get("text", "")
        item_type = item.get("type")

        if item_type == "identity":
            match = re.search(r"User's name is\s+(.+?)\.", text)

            if match:
                profile["name"] = match.group(1)

        if item_type == "location":
            profile["places"].append(text)

        if item_type == "preference":
            profile["preferences"].append(text)

        if item_type == "important_fact":
            profile["important_facts"].append(text)

        if item_type == "object":
            profile["objects"].append(text)

    return profile


def select_phi_workdesk_profile_items(long_items, mid_items, current_message):
    asking_about_self = should_include_personal_memory(current_message)
    personal_types = {"identity", "location", "preference", "important_fact", "object"}
    selected = []
    scored = []
    message_keywords = keywords(current_message)

    for item in long_items + mid_items:
        item_type = item.get("type")

        if item_type == "identity":
            selected.append(item)
            continue

        if item_type not in personal_types:
            continue

        score = relevant_score(item, message_keywords)

        if asking_about_self or score >= 80:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected.extend(item for _score, item in scored)
    return selected[:8]


def select_phi_workdesk_memory(memory, current_message=""):
    chat_memory = memory["chat"]
    long_items = memory["long"].get("items", [])
    mid_items = memory["mid"].get("items", [])
    profile_items = select_phi_workdesk_profile_items(
        long_items,
        mid_items,
        current_message,
    )
    current_items = select_relevant_items(
        select_current_items(memory["current"]),
        current_message,
        limit=4,
    )
    previous_chats = (
        select_previous_chats(chat_memory.get("previous_chats", [])[-1:])
        if should_include_previous_chats(current_message)
        else []
    )

    return {
        "profile": build_profile(profile_items, []),
        "current_messages": select_phi_workdesk_messages(
            chat_memory.get("current_chat", [])
        ),
        "previous_chats": previous_chats,
        "current_memories": current_items,
        "mid_memories": [],
        "long_memories": [],
    }


def select_memory(memory, current_message="", prompt_profile="standard"):
    if prompt_profile == "phi_workdesk":
        return select_phi_workdesk_memory(memory, current_message)

    chat_memory = memory["chat"]
    current_items = select_current_items(memory["current"])
    mid_items = select_relevant_items(
        memory["mid"].get("items", []),
        current_message,
        limit=8,
        always_include_types={"project"},
    )
    long_items = select_relevant_items(
        memory["long"].get("items", []),
        current_message,
        limit=10,
        always_include_types={"identity", "preference"},
    )
    previous_chats = (
        select_previous_chats(chat_memory.get("previous_chats", []))
        if should_include_previous_chats(current_message)
        else []
    )

    return {
        "profile": build_profile(long_items, mid_items),
        "current_messages": select_chat_messages(chat_memory.get("current_chat", [])),
        "previous_chats": previous_chats,
        "current_memories": current_items,
        "mid_memories": mid_items,
        "long_memories": long_items,
    }
