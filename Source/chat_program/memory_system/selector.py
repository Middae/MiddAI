from datetime import timedelta
import re

from config import (
    MEMORY_BRIDGE_EVERY_NTH,
    MEMORY_BRIDGE_LOOKBACK_MESSAGES,
    MEMORY_CURRENT_VISIBLE_MINUTES,
    MEMORY_FIRST_MESSAGES,
    MEMORY_INCLUDE_ASSISTANT_MESSAGES,
    MEMORY_LAST_MESSAGES,
    MEMORY_MAX_MESSAGE_CHARS,
)
from .store import append_memory_event, parse_time, utc_now


PHI_WORKDESK_LAST_USER_MESSAGES = 8
PHI_WORKDESK_MAX_MESSAGE_CHARS = 360

INTENT_NONE = "none"
INTENT_PROFILE = "profile"
INTENT_IDENTITY = "identity"
INTENT_LOCATION = "location"
INTENT_PREFERENCE = "preference"
INTENT_OBJECT = "object"
INTENT_PROJECT = "project"
INTENT_IMPORTANT_FACT = "important_fact"
INTENT_RECENT_CONTEXT = "recent_context"
INTENT_SEARCH_CONTEXT = "search_context"
INTENT_IMAGE_CONTEXT = "image_context"

PROFILE_MEMORY_TYPES = {
    "identity",
    "location",
    "preference",
    "important_fact",
    "object",
    "project",
    "custom_memory",
}
TEMPORARY_MEMORY_TYPES = {
    "short_term",
    "recent_mention",
    "current_context",
    "search_context",
}
PROFILE_INTENT_TYPES = {
    INTENT_PROFILE: PROFILE_MEMORY_TYPES,
    INTENT_IDENTITY: {"identity"},
    INTENT_LOCATION: {"location"},
    INTENT_PREFERENCE: {"preference"},
    INTENT_OBJECT: {"object"},
    INTENT_PROJECT: {"project"},
    INTENT_IMPORTANT_FACT: {"important_fact", "custom_memory"},
    INTENT_RECENT_CONTEXT: TEMPORARY_MEMORY_TYPES,
    INTENT_SEARCH_CONTEXT: {"search_context", "current_context", "short_term"},
    INTENT_IMAGE_CONTEXT: {"current_context", "object", "short_term"},
}
CURRENT_INTENT_TYPES = {
    INTENT_PROFILE: PROFILE_MEMORY_TYPES | {"short_term", "current_context"},
    INTENT_IDENTITY: {"identity", "short_term", "current_context"},
    INTENT_LOCATION: {"location", "short_term", "current_context"},
    INTENT_PREFERENCE: {"preference", "short_term", "current_context"},
    INTENT_OBJECT: {"object", "short_term", "current_context"},
    INTENT_PROJECT: {"project", "short_term", "current_context"},
    INTENT_IMPORTANT_FACT: {"important_fact", "custom_memory", "short_term", "current_context"},
    INTENT_RECENT_CONTEXT: TEMPORARY_MEMORY_TYPES,
    INTENT_SEARCH_CONTEXT: {"search_context", "current_context", "short_term"},
    INTENT_IMAGE_CONTEXT: {"current_context", "object", "short_term"},
}
IMAGE_CONTEXT_SOURCES = {"image_analysis"}
RETRIEVAL_BUDGETS = {
    "phi_workdesk": {
        "current": 3,
        "mid": 4,
        "long": 5,
        "previous_chats": 1,
        "profile": 6,
    },
    "qwen4_light": {
        "current": 4,
        "mid": 6,
        "long": 8,
        "previous_chats": 3,
        "profile": 10,
    },
    "qwen8_medium": {
        "current": 5,
        "mid": 8,
        "long": 10,
        "previous_chats": 4,
        "profile": 12,
    },
    "large_model": {
        "current": 6,
        "mid": 10,
        "long": 12,
        "previous_chats": 5,
        "profile": 14,
    },
    "extreme_model": {
        "current": 8,
        "mid": 12,
        "long": 16,
        "previous_chats": 5,
        "profile": 18,
    },
    "restricted_model": {
        "current": 0,
        "mid": 0,
        "long": 0,
        "previous_chats": 0,
        "profile": 0,
    },
    "standard": {
        "current": 5,
        "mid": 8,
        "long": 10,
        "previous_chats": 5,
        "profile": 12,
    },
}

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


def normalize_message(message):
    return re.sub(r"\s+", " ", (message or "").casefold()).strip()


def has_any_phrase(text, phrases):
    return any(phrase in text for phrase in phrases)


def detect_memory_intent(message):
    normalized_message = normalize_message(message)

    if not normalized_message:
        return INTENT_NONE

    identity_phrases = [
        "what is my name",
        "what's my name",
        "who am i",
        "who i am",
        "do you know my name",
        "do you know who i am",
        "remember my name",
        "my name again",
    ]
    location_phrases = [
        "where do i live",
        "where i live",
        "where am i from",
        "where do you think i am",
        "where am i again",
        "my location",
        "my place",
        "my places",
        "where was i",
        "where did i say i was",
        "where did i say i live",
    ]
    preference_phrases = [
        "what do i like",
        "what i like",
        "what are my preferences",
        "my preferences",
        "what do i prefer",
        "what i prefer",
        "what am i into",
        "things i like",
        "things i prefer",
    ]
    object_phrases = [
        "what objects",
        "my objects",
        "what items",
        "my items",
        "what stuff",
        "my stuff",
        "what gear",
        "my gear",
        "what tools",
        "my tools",
        "what equipment",
        "my equipment",
        "what do i own",
        "what have i got",
        "what am i using",
        "what laptop",
        "my laptop",
        "what pc",
        "my pc",
        "what computer",
        "my computer",
        "what phone",
        "my phone",
        "what model",
        "my model",
    ]
    project_phrases = [
        "what project",
        "my project",
        "what am i working on",
        "what are we working on",
        "what were we building",
        "what are we building",
        "what app",
        "what program",
        "what feature",
        "what update",
    ]
    important_fact_phrases = [
        "what important",
        "important facts",
        "what facts",
        "what did i ask you to remember",
        "what have you remembered",
        "saved facts",
        "permanent memory",
        "long term memory",
        "long-term memory",
        "what did you save",
    ]
    search_phrases = [
        "what did you search",
        "what did we search",
        "what did i search",
        "search summary",
        "search context",
        "search results",
        "the thing you searched",
        "the last search",
        "that search",
        "from the search",
        "from search",
        "web result",
        "web results",
    ]
    image_phrases = [
        "image analysis",
        "image i sent",
        "image i uploaded",
        "picture i sent",
        "picture i uploaded",
        "photo i sent",
        "photo i uploaded",
        "attached image",
        "uploaded image",
        "what was in the image",
        "what did you see",
        "visual analysis",
        "the plant image",
        "the photo",
        "the picture",
    ]
    recent_context_phrases = [
        "what did i just say",
        "what did you just say",
        "what was i just talking about",
        "what were we just talking about",
        "what was that",
        "what did i mention",
        "what did we mention",
        "what did we talk about",
        "what were we talking about",
        "continue that",
        "same topic",
        "what was the last thing",
        "what did i say earlier",
        "what did we say earlier",
    ]
    profile_phrases = [
        "what do you know about me",
        "what do you remember about me",
        "tell me what you know about me",
        "tell me what you remember about me",
        "do you know me",
        "my profile",
        "profile memory",
        "personal memory",
    ]

    if has_any_phrase(normalized_message, image_phrases):
        return INTENT_IMAGE_CONTEXT

    if has_any_phrase(normalized_message, search_phrases):
        return INTENT_SEARCH_CONTEXT

    if has_any_phrase(normalized_message, recent_context_phrases):
        return INTENT_RECENT_CONTEXT

    if has_any_phrase(normalized_message, profile_phrases):
        return INTENT_PROFILE

    if has_any_phrase(normalized_message, identity_phrases):
        return INTENT_IDENTITY

    if has_any_phrase(normalized_message, location_phrases):
        return INTENT_LOCATION

    if has_any_phrase(normalized_message, preference_phrases):
        return INTENT_PREFERENCE

    if has_any_phrase(normalized_message, object_phrases):
        return INTENT_OBJECT

    if has_any_phrase(normalized_message, project_phrases):
        return INTENT_PROJECT

    if has_any_phrase(normalized_message, important_fact_phrases):
        return INTENT_IMPORTANT_FACT

    return INTENT_NONE


def should_include_profile_for_intent(intent):
    return intent in {
        INTENT_PROFILE,
        INTENT_IDENTITY,
        INTENT_LOCATION,
        INTENT_PREFERENCE,
        INTENT_OBJECT,
        INTENT_PROJECT,
        INTENT_IMPORTANT_FACT,
    }


def budget_for_profile(prompt_profile):
    return RETRIEVAL_BUDGETS.get(prompt_profile, RETRIEVAL_BUDGETS["standard"])


def allowed_types_for_intent(intent):
    if intent == INTENT_NONE:
        return None

    return PROFILE_INTENT_TYPES.get(intent)


def current_allowed_types_for_intent(intent):
    if intent == INTENT_NONE:
        return None

    return CURRENT_INTENT_TYPES.get(intent)


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
    return should_include_profile_for_intent(detect_memory_intent(message))


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

        if role == "assistant" and not MEMORY_INCLUDE_ASSISTANT_MESSAGES:
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


def select_previous_chats(previous_chats, limit=5):
    if limit <= 0:
        return []

    selected_chats = []

    for chat in previous_chats[-limit:]:
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


def keyword_overlap_count(item, message_keywords):
    return len(message_keywords & keywords(item.get("text", "")))


def item_time_score(item):
    timestamp = parse_time(item.get("last_seen")) or parse_time(item.get("created_at"))

    if timestamp is None:
        return 0

    return timestamp.timestamp()


def scope_rank(scope):
    return {"long": 3, "mid": 2, "current": 1}.get(scope, 0)


def memory_sort_key(item, message_keywords=None, scope="current"):
    message_keywords = set(message_keywords or [])
    return (
        scope_rank(scope),
        relevant_score(item, message_keywords),
        int(item.get("importance", 0)),
        int(item.get("confidence", 0)),
        int(item.get("times_seen", 1)),
        item_time_score(item),
    )


def normalized_memory_text(text):
    cleaned = re.sub(r"\s+", " ", text or "").strip().casefold()
    prefixes = [
        "short-term user context:",
        "recent user mention:",
        "user mentioned this place:",
        "user preference:",
        "important user fact:",
        "project context:",
        "current context:",
        "user searched:",
        "user attached image(s):",
    ]

    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    return cleaned


def dedupe_memory_items(scoped_items, message=""):
    message_keywords = keywords(message)
    best_by_key = {}

    for scope, item in scoped_items:
        item_type = item.get("type", "memory")
        key = (item_type, normalized_memory_text(item.get("text", "")))

        if not key[1]:
            continue

        existing = best_by_key.get(key)

        if existing is None:
            best_by_key[key] = (scope, item)
            continue

        existing_score = memory_sort_key(
            existing[1],
            message_keywords,
            scope=existing[0],
        )
        new_score = memory_sort_key(item, message_keywords, scope=scope)

        if new_score > existing_score:
            best_by_key[key] = (scope, item)

    return list(best_by_key.values())


def item_matches_intent(item, allowed_types=None, intent=INTENT_NONE):
    if allowed_types and item.get("type") not in allowed_types:
        return False

    if intent == INTENT_IMAGE_CONTEXT:
        return item.get("source") in IMAGE_CONTEXT_SOURCES or item.get("type") in {
            "object",
            "short_term",
        }

    return True


def filter_items_for_intent(items, allowed_types=None, intent=INTENT_NONE):
    return [
        item for item in items
        if item_matches_intent(item, allowed_types=allowed_types, intent=intent)
    ]


def select_ranked_items(
    items,
    message,
    limit=8,
    always_include_types=None,
    allowed_types=None,
    intent=INTENT_NONE,
    scope="current",
):
    always_include_types = set(always_include_types or [])
    filtered_items = filter_items_for_intent(
        items,
        allowed_types=allowed_types,
        intent=intent,
    )
    message_keywords = keywords(message)
    selected = []
    scored = []

    for item in filtered_items:
        item_type = item.get("type")
        overlap = keyword_overlap_count(item, message_keywords)

        if item_type in always_include_types:
            selected.append(item)
            continue

        if (
            intent == INTENT_NONE
            and item_type in PROFILE_MEMORY_TYPES
            and item_type != "identity"
            and overlap == 0
        ):
            continue

        score = relevant_score(item, message_keywords)

        if allowed_types:
            if (
                item_type in TEMPORARY_MEMORY_TYPES
                and intent
                not in {
                    INTENT_PROFILE,
                    INTENT_RECENT_CONTEXT,
                    INTENT_SEARCH_CONTEXT,
                    INTENT_IMAGE_CONTEXT,
                }
                and score < 55
            ):
                continue

            scored.append((score, item))
        elif score >= 70:
            scored.append((score, item))

    scored.sort(
        key=lambda pair: memory_sort_key(pair[1], message_keywords, scope=scope),
        reverse=True,
    )
    selected.extend(item for _score, item in scored)

    return selected[:limit]


def select_relevant_items(items, message, limit=8, always_include_types=None):
    return select_ranked_items(
        items,
        message,
        limit=limit,
        always_include_types=always_include_types,
    )


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
        "projects": [],
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

        if item_type in {"important_fact", "custom_memory"}:
            profile["important_facts"].append(text)

        if item_type == "object":
            profile["objects"].append(text)

        if item_type == "project":
            profile["projects"].append(text)

    return profile


def select_phi_workdesk_profile_items(long_items, mid_items, current_message):
    intent = detect_memory_intent(current_message)
    allowed_types = allowed_types_for_intent(intent)
    asking_about_self = should_include_profile_for_intent(intent)
    personal_types = PROFILE_MEMORY_TYPES
    selected = []
    scored = []
    message_keywords = keywords(current_message)
    scoped_pool = [("long", item) for item in long_items]
    scoped_pool.extend(("mid", item) for item in mid_items)

    for scope, item in scoped_pool:
        item_type = item.get("type")

        if allowed_types and item_type not in allowed_types:
            continue

        if item_type == "identity":
            selected.append((scope, item))
            continue

        if item_type not in personal_types:
            continue

        score = relevant_score(item, message_keywords)

        if asking_about_self or score >= 80:
            scored.append((score, scope, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected.extend((scope, item) for _score, scope, item in scored)
    scoped_items = dedupe_memory_items(
        selected,
        message=current_message,
    )
    scoped_items.sort(
        key=lambda pair: memory_sort_key(pair[1], message_keywords, scope=pair[0]),
        reverse=True,
    )
    return [item for _scope, item in scoped_items[:8]]


def select_phi_workdesk_memory(memory, current_message=""):
    chat_memory = memory["chat"]
    intent = detect_memory_intent(current_message)
    budget = budget_for_profile("phi_workdesk")
    current_allowed_types = current_allowed_types_for_intent(intent)
    long_items = memory["long"].get("items", [])
    mid_items = memory["mid"].get("items", [])
    profile_items = select_phi_workdesk_profile_items(
        long_items,
        mid_items,
        current_message,
    )
    current_items = select_ranked_items(
        select_current_items(memory["current"]),
        current_message,
        limit=budget["current"],
        allowed_types=current_allowed_types,
        intent=intent,
        scope="current",
    )
    previous_chats = (
        select_previous_chats(
            chat_memory.get("previous_chats", []),
            limit=budget["previous_chats"],
        )
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


def selected_type_counts(items):
    counts = {}

    for item in items:
        item_type = item.get("type", "memory")
        counts[item_type] = counts.get(item_type, 0) + 1

    return counts


def split_scoped_items(scoped_items, budgets):
    current_items = []
    mid_items = []
    long_items = []

    for scope, item in scoped_items:
        if scope == "long" and len(long_items) < budgets["long"]:
            long_items.append(item)
        elif scope == "mid" and len(mid_items) < budgets["mid"]:
            mid_items.append(item)
        elif scope == "current" and len(current_items) < budgets["current"]:
            current_items.append(item)

    return current_items, mid_items, long_items


def build_scoped_selection(memory, current_message, prompt_profile, intent):
    budgets = budget_for_profile(prompt_profile)
    profile_allowed_types = allowed_types_for_intent(intent)
    current_allowed_types = current_allowed_types_for_intent(intent)
    always_include_long_types = set()

    if intent == INTENT_NONE:
        always_include_long_types = {"identity"}

    visible_current = select_current_items(memory["current"])
    current_candidates = select_ranked_items(
        visible_current,
        current_message,
        limit=max(budgets["current"] * 2, budgets["current"]),
        allowed_types=current_allowed_types,
        intent=intent,
        scope="current",
    )
    mid_candidates = select_ranked_items(
        memory["mid"].get("items", []),
        current_message,
        limit=max(budgets["mid"] * 2, budgets["mid"]),
        allowed_types=profile_allowed_types,
        intent=intent,
        scope="mid",
    )
    long_candidates = select_ranked_items(
        memory["long"].get("items", []),
        current_message,
        limit=max(budgets["long"] * 2, budgets["long"]),
        always_include_types=always_include_long_types,
        allowed_types=profile_allowed_types,
        intent=intent,
        scope="long",
    )
    scoped_items = []
    scoped_items.extend(("long", item) for item in long_candidates)
    scoped_items.extend(("mid", item) for item in mid_candidates)
    scoped_items.extend(("current", item) for item in current_candidates)
    deduped = dedupe_memory_items(scoped_items, message=current_message)
    message_keywords = keywords(current_message)
    deduped.sort(
        key=lambda pair: memory_sort_key(pair[1], message_keywords, scope=pair[0]),
        reverse=True,
    )

    return split_scoped_items(deduped, budgets)


def log_retrieval_event(
    current_message,
    prompt_profile,
    intent,
    current_items,
    mid_items,
    long_items,
    previous_chats,
):
    append_memory_event(
        "memory_retrieval",
        content=current_message,
        status="selected",
        metadata={
            "prompt_profile": prompt_profile,
            "intent": intent,
            "current_count": len(current_items),
            "mid_count": len(mid_items),
            "long_count": len(long_items),
            "previous_chat_count": len(previous_chats),
            "current_types": selected_type_counts(current_items),
            "mid_types": selected_type_counts(mid_items),
            "long_types": selected_type_counts(long_items),
        },
    )


def select_memory(memory, current_message="", prompt_profile="standard"):
    if prompt_profile == "phi_workdesk":
        selected = select_phi_workdesk_memory(memory, current_message)
        log_retrieval_event(
            current_message,
            prompt_profile,
            detect_memory_intent(current_message),
            selected.get("current_memories", []),
            selected.get("mid_memories", []),
            selected.get("long_memories", []),
            selected.get("previous_chats", []),
        )
        return selected

    chat_memory = memory["chat"]
    intent = detect_memory_intent(current_message)
    budgets = budget_for_profile(prompt_profile)
    current_items, mid_items, long_items = build_scoped_selection(
        memory,
        current_message,
        prompt_profile,
        intent,
    )
    previous_chats = (
        select_previous_chats(
            chat_memory.get("previous_chats", []),
            limit=budgets["previous_chats"],
        )
        if should_include_previous_chats(current_message)
        else []
    )
    log_retrieval_event(
        current_message,
        prompt_profile,
        intent,
        current_items,
        mid_items,
        long_items,
        previous_chats,
    )

    return {
        "profile": build_profile(long_items, mid_items),
        "current_messages": select_chat_messages(chat_memory.get("current_chat", [])),
        "previous_chats": previous_chats,
        "current_memories": current_items,
        "mid_memories": mid_items,
        "long_memories": long_items,
    }
