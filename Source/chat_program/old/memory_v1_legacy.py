from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from config import (
    MEMORY_BRIDGE_EVERY_NTH,
    MEMORY_BRIDGE_LOOKBACK_MESSAGES,
    MEMORY_FIRST_MESSAGES,
    MEMORY_INCLUDE_ASSISTANT_MESSAGES,
    MEMORY_LAST_MESSAGES,
    MEMORY_MAX_MESSAGE_CHARS,
)


MEMORY_DIR = Path.home() / "Documents" / "MiddAI"
MEMORY_FILE = MEMORY_DIR / "memory.json"
PREVIOUS_CHAT_LIMIT = 5
PREVIOUS_CHAT_MESSAGE_LIMIT = 10
PROFILE_LIST_LIMIT = 30
PROFILE_ITEM_MAX_CHARS = 180
IGNORED_NAME_WORDS = {
    "about",
    "asking",
    "awake",
    "back",
    "based",
    "busy",
    "currently",
    "doing",
    "downloading",
    "drunk",
    "from",
    "getting",
    "going",
    "happy",
    "having",
    "here",
    "home",
    "in",
    "just",
    "learning",
    "located",
    "looking",
    "making",
    "not",
    "on",
    "open",
    "putting",
    "ready",
    "running",
    "sat",
    "setting",
    "sitting",
    "sorry",
    "still",
    "sure",
    "thinking",
    "trying",
    "using",
    "wondering",
    "working",
}


DEFAULT_MEMORY = {
    "profile": {
        "name": None,
        "places": [],
        "preferences": [],
        "important_facts": [],
        "current_context": [],
    },
    "current_chat": [],
    "previous_chats": [],
}


def blank_memory():
    return deepcopy(DEFAULT_MEMORY)


def ensure_memory_file():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if not MEMORY_FILE.exists():
        save_memory(blank_memory())


def normalize_memory(memory):
    normalized = blank_memory()

    if isinstance(memory, dict):
        profile = memory.get("profile")

        if isinstance(profile, dict):
            normalized["profile"].update(profile)
            normalized_profile = normalized["profile"]

            if normalized_profile.get("name") is not None:
                normalized_profile["name"] = str(normalized_profile["name"])

            for key in ("places", "preferences", "important_facts", "current_context"):
                if not isinstance(normalized_profile.get(key), list):
                    normalized_profile[key] = []

        current_chat = memory.get("current_chat")

        if isinstance(current_chat, list):
            normalized["current_chat"] = current_chat

        previous_chats = memory.get("previous_chats")

        if isinstance(previous_chats, list):
            normalized["previous_chats"] = previous_chats

    return normalized


def load_memory():
    ensure_memory_file()

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            memory = normalize_memory(json.load(file))
            memory_changed = repair_profile_name(memory)
            memory_changed = refresh_profile_from_messages(memory) or memory_changed

            if memory_changed:
                save_memory(memory)

            return memory
    except (json.JSONDecodeError, OSError):
        memory = blank_memory()
        save_memory(memory)
        return memory


def save_memory(memory):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    with MEMORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(normalize_memory(memory), file, indent=2)


def trim_memory_content(content):
    if len(content) <= MEMORY_MAX_MESSAGE_CHARS:
        return content

    return content[:MEMORY_MAX_MESSAGE_CHARS].rstrip() + "..."


def clean_message(role, content):
    cleaned_content = (content or "").strip()

    if not cleaned_content:
        return None

    return {
        "role": role,
        "content": cleaned_content,
    }


def extract_name_from_message(content):
    explicit_patterns = [
        r"\bmy name is\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bmy names\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bmy name's\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bname is\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bname's\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bcall me\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\byou can call me\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bi am called\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bi'm called\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bim called\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
    ]
    intro_patterns = [
        r"^\s*(?:hi|hello|hey|ello|hiya)[,!.\s]+(?:i am|i'm|im)\s+([a-zA-Z][a-zA-Z'-]{1,30})\s*[.!?]*\s*$",
        r"^\s*(?:i am|i'm|im)\s+([a-zA-Z][a-zA-Z'-]{1,30})\s*[.!?]*\s*$",
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)

        if match:
            name = match.group(1).strip(".,!?:;\"'")

            if is_usable_name(name):
                return name, True

    for pattern in intro_patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)

        if match:
            name = match.group(1).strip(".,!?:;\"'")

            if is_usable_name(name):
                return name, False

    return None, False


def is_usable_name(name):
    cleaned = (name or "").strip(".,!?:;\"'")
    return bool(cleaned) and cleaned.casefold() not in IGNORED_NAME_WORDS


def iter_user_memory_messages(memory):
    for chat in memory.get("previous_chats", []):
        for message in chat.get("messages", []):
            if message.get("role") == "user":
                yield message.get("content", "")

    for message in memory.get("current_chat", []):
        if message.get("role") == "user":
            yield message.get("content", "")


def find_name_in_memory_messages(memory):
    found_name = None

    for content in iter_user_memory_messages(memory):
        name, _is_explicit = extract_name_from_message(content)

        if name:
            found_name = name

    return found_name


def repair_profile_name(memory):
    profile = memory["profile"]
    current_name = profile.get("name")

    if current_name and is_usable_name(str(current_name)):
        return False

    repaired_name = find_name_in_memory_messages(memory)

    if current_name == repaired_name:
        return False

    profile["name"] = repaired_name
    return True


def refresh_profile_from_messages(memory):
    before = json.dumps(memory["profile"], sort_keys=True)

    for content in iter_user_memory_messages(memory):
        update_profile_from_user_message(memory, content)

    after = json.dumps(memory["profile"], sort_keys=True)
    return before != after


def clean_profile_value(value, max_chars=PROFILE_ITEM_MAX_CHARS):
    cleaned = re.sub(r"\s+", " ", value or "").strip(" \t\r\n.,;:!?\"'")

    if not cleaned:
        return None

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "..."

    return cleaned


def clean_profile_clause(value):
    cleaned = clean_profile_value(value)

    if not cleaned:
        return None

    split_match = re.split(r"\s+\b(?:and|but|because|so|while)\b\s+", cleaned, maxsplit=1)
    return clean_profile_value(split_match[0])


def clean_location_value(value):
    cleaned = clean_profile_clause(value)

    if not cleaned:
        return None

    cleaned = re.sub(
        r"\b(?:right now|currently|at the moment|today|tonight)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return clean_profile_value(cleaned)


def split_profile_list(value):
    cleaned = clean_profile_value(value)

    if not cleaned:
        return []

    items = []

    for item in re.split(r"\s*,\s*|\s+\band\b\s+", cleaned):
        cleaned_item = clean_profile_value(item)

        if cleaned_item:
            items.append(cleaned_item)

    return items


def add_unique_profile_item(profile, key, value):
    cleaned = clean_profile_value(value)

    if not cleaned:
        return

    items = profile.setdefault(key, [])

    if not isinstance(items, list):
        items = []
        profile[key] = items

    existing_items = {str(item).casefold() for item in items}

    if cleaned.casefold() not in existing_items:
        items.append(cleaned)
        del items[:-PROFILE_LIST_LIMIT]


def extract_profile_values(content, patterns, clean_value=clean_profile_value):
    values = []

    for pattern in patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            value = clean_value(match.group(1))

            if value:
                values.append(value)

    return values


def extract_labeled_list_values(content, labels):
    label_pattern = "|".join(labels)
    values = []
    patterns = [
        rf"\b(?:{label_pattern})\s*:\s*([^.!?;]+)",
        rf"\bmy\s+(?:{label_pattern})\s+(?:are|include)\s+([^.!?;]+)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            values.extend(split_profile_list(match.group(1)))

    return values


def extract_locations_from_message(content):
    values = extract_labeled_list_values(
        content,
        [
            r"places?",
            r"locations?",
            r"where i live",
            r"where i am",
        ],
    )
    patterns = [
        r"\bi live in\s+([^.!?;]+)",
        r"\bi live near\s+([^.!?;]+)",
        r"\bi am at\s+([^.!?;]+)",
        r"\bi'm at\s+([^.!?;]+)",
        r"\bim at\s+([^.!?;]+)",
        r"\bi am from\s+([^.!?;]+)",
        r"\bi'm from\s+([^.!?;]+)",
        r"\bim from\s+([^.!?;]+)",
        r"\bi am based in\s+([^.!?;]+)",
        r"\bi'm based in\s+([^.!?;]+)",
        r"\bim based in\s+([^.!?;]+)",
        r"\bi am located in\s+([^.!?;]+)",
        r"\bi'm located in\s+([^.!?;]+)",
        r"\bmy location is\s+([^.!?;]+)",
        r"\bmy town is\s+([^.!?;]+)",
        r"\bmy city is\s+([^.!?;]+)",
        r"\bmy country is\s+([^.!?;]+)",
        r"\bi work in\s+([^.!?;]+)",
        r"\bi'm in\s+([^.!?;]+)",
        r"\bi am in\s+([^.!?;]+)",
        r"\bi am sat in\s+([^.!?;]+)",
        r"\bi'm sat in\s+([^.!?;]+)",
        r"\bim sat in\s+([^.!?;]+)",
        r"\bi am sitting in\s+([^.!?;]+)",
        r"\bi'm sitting in\s+([^.!?;]+)",
        r"\bim sitting in\s+([^.!?;]+)",
        r"\bi am sat at\s+([^.!?;]+)",
        r"\bi'm sat at\s+([^.!?;]+)",
        r"\bim sat at\s+([^.!?;]+)",
        r"\bi am sitting at\s+([^.!?;]+)",
        r"\bi'm sitting at\s+([^.!?;]+)",
        r"\bim sitting at\s+([^.!?;]+)",
        r"\bi am staying in\s+([^.!?;]+)",
        r"\bi'm staying in\s+([^.!?;]+)",
        r"\bim staying in\s+([^.!?;]+)",
        r"\bin\s+(my\s+[^.!?;,]*(?:bedroom|room|house|home|flat|apartment|garden|office|workshop|camp)[^.!?;,]*)",
        r"\bi(?: do)?(?: also)? have\s+(?:a|an|the|my)?\s*([^.!?;]*(?:camp|house|home|cabin|bedroom|room|flat|apartment|garden|office|workshop)[^.!?;]*)",
    ]
    values.extend(extract_profile_values(content, patterns, clean_location_value))

    return values


def extract_preferences_from_message(content):
    patterns = [
        r"\bi really like\s+([^.!?;]+)",
        r"\bi like\s+([^.!?;]+)",
        r"\bi love\s+([^.!?;]+)",
        r"\bi enjoy\s+([^.!?;]+)",
        r"\bi prefer\s+([^.!?;]+)",
        r"\bi don't like\s+([^.!?;]+)",
        r"\bi do not like\s+([^.!?;]+)",
        r"\bi hate\s+([^.!?;]+)",
        r"\bmy favourite\s+([^.!?;]+)",
        r"\bmy favorite\s+([^.!?;]+)",
    ]

    return extract_profile_values(content, patterns, clean_profile_clause)


def extract_important_facts_from_message(content):
    explicit_patterns = [
        r"\bremember that\s+(.+)",
        r"\bremember this\s*:?\s*(.+)",
        r"\bsave this\s*:?\s*(.+)",
        r"\bsave that\s+(.+)",
        r"\bimportant\s*:\s*(.+)",
        r"\bimportant detail about me\s*,?\s*(.+)",
        r"\bimportant details about me\s*,?\s*(.+)",
        r"\bimportant info about me\s*,?\s*(.+)",
        r"\bimportant information about me\s*,?\s*(.+)",
        r"\bfacts about me\s*:?\s*(.+)",
        r"\bdetails about me\s*:?\s*(.+)",
        r"\bfor future reference\s*,?\s*(.+)",
        r"\bnote that\s+(.+)",
    ]
    personal_patterns = [
        r"\bmy (?!name\b)([^.!?;]{2,80}?\s+(?:is|are)\s+[^.!?;]+)",
        r"\bi have\s+([^.!?;]+)",
        r"\bi work as\s+([^.!?;]+)",
        r"\bi study\s+([^.!?;]+)",
        r"\bi use\s+([^.!?;]+)",
        r"\bi am using\s+([^.!?;]+)",
        r"\bi'm using\s+([^.!?;]+)",
        r"\bim using\s+([^.!?;]+)",
        r"\bi am running\s+([^.!?;]+)",
        r"\bi'm running\s+([^.!?;]+)",
        r"\bim running\s+([^.!?;]+)",
        r"\bi own\s+([^.!?;]+)",
    ]
    facts = extract_profile_values(content, explicit_patterns)
    facts.extend(extract_profile_values(content, personal_patterns, clean_profile_clause))

    return facts


def extract_current_context_from_message(content):
    context_markers = [
        "right now",
        "currently",
        "at the moment",
        "at home",
        "today",
        "tonight",
        "this morning",
        "this afternoon",
        "this evening",
        "currently happening",
    ]
    context_patterns = [
        r"\bi am sat\b",
        r"\bi'm sat\b",
        r"\bim sat\b",
        r"\bi am sitting\b",
        r"\bi'm sitting\b",
        r"\bim sitting\b",
        r"\bi am staying\b",
        r"\bi'm staying\b",
        r"\bim staying\b",
        r"\bi am watching\b",
        r"\bi'm watching\b",
        r"\bim watching\b",
        r"\bi am listening\b",
        r"\bi'm listening\b",
        r"\bim listening\b",
        r"\bi am drinking\b",
        r"\bi'm drinking\b",
        r"\bim drinking\b",
    ]
    lowered = content.lower()

    has_marker = any(marker in lowered for marker in context_markers)
    has_pattern = any(
        re.search(pattern, content, flags=re.IGNORECASE) for pattern in context_patterns
    )

    if not has_marker and not has_pattern:
        return []

    return [clean_profile_value(content)]


def update_profile_from_user_message(memory, content):
    profile = memory["profile"]
    name, is_explicit_name = extract_name_from_message(content)

    if name and (is_explicit_name or not is_usable_name(str(profile.get("name") or ""))):
        profile["name"] = name

    for location in extract_locations_from_message(content):
        add_unique_profile_item(profile, "places", location)

    for preference in extract_preferences_from_message(content):
        add_unique_profile_item(profile, "preferences", preference)

    for fact in extract_important_facts_from_message(content):
        add_unique_profile_item(profile, "important_facts", fact)

    for context in extract_current_context_from_message(content):
        add_unique_profile_item(profile, "current_context", context)


def add_message(role, content):
    message = clean_message(role, content)

    if message is None:
        return

    memory = load_memory()

    if role == "user":
        update_profile_from_user_message(memory, message["content"])

    memory["current_chat"].append(message)
    save_memory(memory)


def archive_current_chat():
    memory = load_memory()
    current_chat = memory["current_chat"]

    if current_chat:
        memory["previous_chats"].append(
            {
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "messages": current_chat,
            }
        )
        memory["previous_chats"] = memory["previous_chats"][-PREVIOUS_CHAT_LIMIT:]
        memory["current_chat"] = []
        save_memory(memory)


def delete_all_memory():
    save_memory(blank_memory())


def get_current_chat_messages():
    memory = load_memory()
    messages = []

    for message in memory["current_chat"]:
        role = message.get("role")
        content = message.get("content")

        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append(
                {
                    "role": role,
                    "content": content.strip(),
                }
            )

    return messages


def should_include_previous_chats(message):
    normalized_message = message.lower()
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


def select_messages(messages, include_assistant=False):
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

        is_recent_message = index >= recent_start

        if (
            message["role"] == "assistant"
            and not include_assistant
            and not is_recent_message
        ):
            continue

        selected_messages.append(
            {
                "role": message["role"],
                "content": trim_memory_content(message["content"]),
            }
        )

    return selected_messages


def select_previous_chats(previous_chats):
    selected_chats = []

    for chat in previous_chats[-PREVIOUS_CHAT_LIMIT:]:
        messages = chat.get("messages", [])
        selected_chats.append(
            {
                "ended_at": chat.get("ended_at"),
                "messages": [
                    {
                        "role": message["role"],
                        "content": trim_memory_content(message["content"]),
                    }
                    for message in messages[-PREVIOUS_CHAT_MESSAGE_LIMIT:]
                    if message.get("role") in {"user", "assistant"}
                ],
            }
        )

    return selected_chats


def get_selected_memory(current_message=""):
    memory = load_memory()
    include_assistant = MEMORY_INCLUDE_ASSISTANT_MESSAGES
    include_previous = should_include_previous_chats(current_message)

    return {
        "profile": memory["profile"],
        "current_messages": select_messages(
            memory["current_chat"],
            include_assistant=include_assistant,
        ),
        "previous_chats": select_previous_chats(memory["previous_chats"])
        if include_previous
        else [],
    }
