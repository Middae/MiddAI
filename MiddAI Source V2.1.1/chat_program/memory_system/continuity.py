from collections import Counter
import re

from .extractor import extract_memories_from_user_message


CONTINUITY_VERSION = 2
MAX_CONTINUITY_TAGS = 12
MAX_SUMMARY_CHARS = 720
MAX_EXCERPT_CHARS = 180

STOP_WORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "because",
    "been",
    "being",
    "but",
    "can",
    "could",
    "did",
    "does",
    "doing",
    "from",
    "have",
    "here",
    "into",
    "just",
    "like",
    "more",
    "need",
    "only",
    "other",
    "please",
    "really",
    "should",
    "some",
    "that",
    "their",
    "there",
    "these",
    "they",
    "thing",
    "this",
    "those",
    "through",
    "user",
    "want",
    "what",
    "when",
    "where",
    "which",
    "will",
    "with",
    "would",
    "you",
    "your",
}

GENERIC_PROPER_WORDS = {
    "Assistant",
    "Current",
    "Delete",
    "Hello",
    "Okay",
    "Please",
    "Thanks",
    "Thank",
    "The",
    "This",
    "User",
    "What",
    "When",
    "Where",
}

ENTITY_PATTERNS = (
    r"\bmy name is\s+([A-Za-z][A-Za-z0-9' -]{1,48})",
    r"\bi(?:'m| am) called\s+([A-Za-z][A-Za-z0-9' -]{1,48})",
    r"\bi live (?:in|near|at)\s+([A-Za-z0-9][A-Za-z0-9' .-]{1,64})",
    r"\bi(?:'m| am) (?:from|based in|at)\s+([A-Za-z0-9][A-Za-z0-9' .-]{1,64})",
    r"\b(?:project|program|app|software) (?:called|named)\s+([A-Za-z0-9][A-Za-z0-9' ._-]{1,64})",
    r"\b(?:working on|building|developing)\s+([A-Za-z0-9][A-Za-z0-9' ._-]{1,64})",
    r"\bmy (?:job|profession|occupation) is\s+([A-Za-z][A-Za-z0-9' -]{1,48})",
    r"\bi work as (?:an?\s+)?([A-Za-z][A-Za-z0-9' -]{1,48})",
    (
        r"\bmy\s+((?:car|van|bike|bicycle|motorbike|phone|computer|pc|laptop|"
        r"desk|chair|sofa|couch|table|bed|wardrobe|cabinet|shelf|furniture|"
        r"tool|device|model)\b(?:\s+[A-Za-z0-9'_-]+){0,4})"
    ),
)

PAST_CHAT_PHRASES = (
    "last chat",
    "last conversation",
    "previous chat",
    "previous conversation",
    "past chat",
    "past conversation",
    "remember when",
    "do you remember",
    "what did we decide",
    "what did we discuss",
    "what were we talking about",
)

STRONG_FOLLOW_UP_PHRASES = (
    "the other",
    "same one",
    "same thing",
    "what about",
    "continue",
    "go on",
    "tell me more",
    "expand on",
    "explain further",
)
FOLLOW_UP_PRONOUNS = {
    "that",
    "this",
    "those",
    "them",
    "they",
    "it",
}
FOLLOW_UP_QUESTION_WORDS = {
    "can",
    "could",
    "did",
    "do",
    "does",
    "how",
    "is",
    "should",
    "was",
    "were",
    "what",
    "when",
    "where",
    "why",
    "will",
    "would",
}
MAX_FOLLOW_UP_WORDS = 14


def compact_text(value, max_chars):
    text = re.sub(r"\s+", " ", str(value or "")).strip()

    if len(text) <= max_chars:
        return text

    shortened = text[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{shortened}..." if shortened else text[:max_chars]


def searchable_terms(value):
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*", str(value or "").casefold())
    return {
        word
        for word in words
        if len(word) >= 3 and word not in STOP_WORDS and not word.isdigit()
    }


def continuity_source_messages(messages):
    usable = [
        message
        for message in messages or []
        if message.get("role") in {"user", "assistant"}
        and str(message.get("content") or "").strip()
    ]

    if len(usable) <= 35:
        return usable

    return usable[:10] + usable[-25:]


def clean_tag(value):
    tag = compact_text(value, 72).strip(" .,:;!?\"'()[]{}")
    tag = re.sub(r"\b(?:and|but|because|then|when|where)\b.*$", "", tag, flags=re.I)
    return tag.strip(" .,:;!?\"'()[]{}")


def add_tag_candidate(candidates, value, score):
    tag = clean_tag(value)

    if len(tag) < 3:
        return

    normalized = tag.casefold()

    if normalized in STOP_WORDS or normalized.isdigit():
        return

    existing = candidates.get(normalized)

    if existing is None or score > existing[0]:
        candidates[normalized] = (score, tag)


def extract_continuity_tags(messages):
    candidates = {}
    term_counts = Counter()
    source_messages = continuity_source_messages(messages)
    user_messages = [
        message
        for message in source_messages
        if message.get("role") == "user"
    ]
    combined_text = "\n".join(
        str(message.get("content") or "")
        for message in user_messages
    )

    for message in user_messages:
        for memory in extract_memories_from_user_message(
            str(message.get("content") or "")
        ):
            add_tag_candidate(candidates, memory.get("entity_name"), 110)

            for alias in memory.get("aliases", []):
                add_tag_candidate(candidates, alias, 105)

    for pattern in ENTITY_PATTERNS:
        for match in re.finditer(pattern, combined_text, flags=re.I):
            add_tag_candidate(candidates, match.group(1), 100)

    for quoted in re.findall(r"[\"']([^\"'\r\n]{3,64})[\"']", combined_text):
        add_tag_candidate(candidates, quoted, 80)

    for proper_phrase in re.findall(
        r"\b[A-Z][A-Za-z0-9'_-]*(?:\s+[A-Z][A-Za-z0-9'_-]*){0,3}\b",
        combined_text,
    ):
        if proper_phrase in GENERIC_PROPER_WORDS:
            continue

        add_tag_candidate(candidates, proper_phrase, 70)

    for term in searchable_terms(combined_text):
        term_counts[term] += len(
            re.findall(rf"\b{re.escape(term)}\b", combined_text, flags=re.I)
        )

    for term, count in term_counts.most_common(24):
        add_tag_candidate(candidates, term, 30 + min(count, 10))

    ranked = sorted(
        candidates.values(),
        key=lambda item: (item[0], len(item[1])),
        reverse=True,
    )
    return [tag for _score, tag in ranked[:MAX_CONTINUITY_TAGS]]


def unique_message_excerpts(messages, role, reverse=False, limit=3):
    source = list(reversed(messages)) if reverse else list(messages)
    excerpts = []
    seen = set()

    for message in source:
        if message.get("role") != role:
            continue

        excerpt = compact_text(message.get("content"), MAX_EXCERPT_CHARS)
        normalized = excerpt.casefold()

        if not excerpt or normalized in seen:
            continue

        seen.add(normalized)
        excerpts.append(excerpt)

        if len(excerpts) >= limit:
            break

    if reverse:
        excerpts.reverse()

    return excerpts


def build_continuity_summary(messages):
    source_messages = continuity_source_messages(messages)

    if not source_messages:
        return ""

    first_user = unique_message_excerpts(source_messages, "user", limit=1)
    recent_users = unique_message_excerpts(
        source_messages,
        "user",
        reverse=True,
        limit=3,
    )
    parts = []

    if first_user:
        parts.append(f"Started with: {first_user[0]}")

    later_users = [
        excerpt
        for excerpt in recent_users
        if not first_user or excerpt.casefold() != first_user[0].casefold()
    ]

    if later_users:
        parts.append(f"Later user topics: {' | '.join(later_users)}")

    return compact_text(" ".join(parts), MAX_SUMMARY_CHARS)


def build_continuity_record(chat):
    messages = chat.get("messages", []) if isinstance(chat, dict) else []
    return {
        "version": CONTINUITY_VERSION,
        "summary": build_continuity_summary(messages),
        "tags": extract_continuity_tags(messages),
    }


def ensure_chat_continuity(chat):
    if not isinstance(chat, dict):
        return False

    continuity = chat.get("continuity")

    if (
        isinstance(continuity, dict)
        and continuity.get("version") == CONTINUITY_VERSION
        and isinstance(continuity.get("summary"), str)
        and isinstance(continuity.get("tags"), list)
    ):
        return False

    chat["continuity"] = build_continuity_record(chat)
    return True


def query_has_past_chat_intent(query):
    normalized = compact_text(query, 1000).casefold()
    return any(phrase in normalized for phrase in PAST_CHAT_PHRASES)


def query_is_simple_greeting(query):
    normalized = compact_text(query, 200).strip(" .,!?:;").casefold()
    return bool(
        re.fullmatch(
            r"(?:hi|hello|hey|good morning|good afternoon|good evening)"
            r"(?:\s+[a-z][a-z0-9'_-]{1,40})?",
            normalized,
        )
    )


def query_states_personal_fact(query):
    if "?" in str(query or ""):
        return False

    return bool(extract_memories_from_user_message(str(query or "")))


def query_uses_recent_context(query):
    normalized = compact_text(query, 1000).casefold()

    if any(phrase in normalized for phrase in STRONG_FOLLOW_UP_PHRASES):
        return True

    words = re.findall(r"[a-z0-9]+", normalized)

    if not words or len(words) > MAX_FOLLOW_UP_WORDS:
        return False

    pronoun_positions = [
        index
        for index, word in enumerate(words)
        if word in FOLLOW_UP_PRONOUNS
    ]

    if not pronoun_positions:
        return "again" in words

    return (
        min(pronoun_positions) <= 2
        or words[0] in FOLLOW_UP_QUESTION_WORDS
    )


def matching_message_sentences(chat, query_terms, include_assistant=False, limit=4):
    excerpts = []
    seen = set()

    for message in chat.get("messages", []) if isinstance(chat, dict) else []:
        role = message.get("role")

        if role != "user" and not (include_assistant and role == "assistant"):
            continue

        content = compact_text(message.get("content"), MAX_SUMMARY_CHARS)

        for sentence in re.split(r"(?<=[.!?])\s+|\s*\|\s*", content):
            excerpt = compact_text(sentence, MAX_EXCERPT_CHARS)

            if not excerpt or not (query_terms & searchable_terms(excerpt)):
                continue

            normalized = excerpt.casefold()

            if normalized in seen:
                continue

            seen.add(normalized)
            label = "User" if role == "user" else "Assistant"
            excerpts.append(f"{label}: {excerpt}")

            if len(excerpts) >= limit:
                return excerpts

    return excerpts


def selected_continuity_summary(chat, query, query_terms, fallback_summary):
    normalized_query = compact_text(query, 1000).casefold()
    include_assistant = query_uses_recent_context(query) or any(
        phrase in normalized_query
        for phrase in (
            "what did you say",
            "what you said",
            "you said",
            "your answer",
            "your response",
        )
    )
    excerpts = matching_message_sentences(
        chat,
        query_terms,
        include_assistant=include_assistant,
    )

    if excerpts:
        return compact_text(" | ".join(excerpts), MAX_SUMMARY_CHARS)

    return fallback_summary


def selected_continuity_tags(tags, query_terms, include_all=False):
    if include_all:
        return list(tags or [])

    return [
        tag
        for tag in tags or []
        if query_terms & searchable_terms(tag)
    ]


def select_continuity_summaries(previous_chats, query, recent_messages=None, limit=2):
    if limit <= 0:
        return []

    explicit_past_intent = query_has_past_chat_intent(query)
    uses_recent_context = query_uses_recent_context(query)

    if (
        not explicit_past_intent
        and not uses_recent_context
        and (
            query_is_simple_greeting(query)
            or query_states_personal_fact(query)
        )
    ):
        return []

    recent_text = ""

    if uses_recent_context:
        recent_text = " ".join(
            str(message.get("content") or "")
            for message in (recent_messages or [])[-3:]
            if message.get("role") in {"user", "assistant"}
        )
    query_context = f"{query} {recent_text}".strip()
    query_terms = searchable_terms(query_context)
    scored = []

    for recency_index, chat in enumerate(reversed(previous_chats or []), start=1):
        if chat.get("legacy_unscoped"):
            continue

        ensure_chat_continuity(chat)
        continuity = chat.get("continuity", {})
        summary = continuity.get("summary", "")
        tags = continuity.get("tags", [])

        if not summary:
            continue

        summary_overlap = len(query_terms & searchable_terms(summary))
        tag_overlap = 0
        exact_tag_matches = 0
        normalized_query = compact_text(query_context, 2000).casefold()

        for tag in tags:
            tag_terms = searchable_terms(tag)
            tag_overlap += len(query_terms & tag_terms)

            if compact_text(tag, 72).casefold() in normalized_query:
                exact_tag_matches += 1

        score = (exact_tag_matches * 45) + (tag_overlap * 18) + (summary_overlap * 8)

        if explicit_past_intent:
            score += max(1, 12 - recency_index)

        if score <= 0:
            continue

        scored.append(
            (
                score,
                recency_index,
                {
                    "chat_id": chat.get("id"),
                    "title": chat.get("title"),
                    "ended_at": chat.get("ended_at"),
                    "summary": selected_continuity_summary(
                        chat,
                        query,
                        query_terms,
                        summary,
                    ),
                    "tags": selected_continuity_tags(
                        tags,
                        query_terms,
                        include_all=explicit_past_intent and not query_terms,
                    ),
                },
            )
        )

    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)

    if not scored and explicit_past_intent:
        for chat in reversed(previous_chats or []):
            if chat.get("legacy_unscoped"):
                continue

            ensure_chat_continuity(chat)
            continuity = chat.get("continuity", {})

            if continuity.get("summary"):
                return [
                    {
                        "chat_id": chat.get("id"),
                        "title": chat.get("title"),
                        "ended_at": chat.get("ended_at"),
                        "summary": continuity.get("summary"),
                        "tags": continuity.get("tags", []),
                    }
                ]

    return [record for _score, _recency, record in scored[:limit]]
