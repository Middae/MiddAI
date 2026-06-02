import re


SENSITIVE_PATTERNS = [
    r"\bpassword\b",
    r"\bapi\s*key\b",
    r"\bsecret\b",
    r"\bprivate\s*key\b",
    r"\btoken\b",
]

IGNORED_NAME_WORDS = {
    "asking",
    "busy",
    "currently",
    "doing",
    "downloading",
    "from",
    "going",
    "having",
    "here",
    "home",
    "in",
    "just",
    "learning",
    "located",
    "not",
    "open",
    "ready",
    "running",
    "sat",
    "sitting",
    "standing",
    "still",
    "stood",
    "sure",
    "thinking",
    "travelling",
    "traveling",
    "trying",
    "using",
    "walking",
    "wandering",
    "wondering",
    "working",
}


def has_sensitive_content(content):
    return any(re.search(pattern, content, flags=re.IGNORECASE) for pattern in SENSITIVE_PATTERNS)


def clean_value(value, max_chars=220):
    cleaned = re.sub(r"\s+", " ", value or "").strip(" \t\r\n.,;:!?\"'")

    if not cleaned:
        return None

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "..."

    return cleaned


def clean_clause(value):
    cleaned = clean_value(value)

    if not cleaned:
        return None

    split_match = re.split(r"\s+\b(?:and|but|because|so|while)\b\s+", cleaned, maxsplit=1)
    return clean_value(split_match[0])


def clean_location_clause(value):
    cleaned = clean_clause(value)

    if not cleaned:
        return None

    cleaned = re.split(
        r"\s+\b(?:tinkering|programming|programing|coding|working|also|getting ready|heading|going)\b\s+",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    cleaned = re.split(
        r"\s+\b(?:in a couple of days|in a few days|tomorrow|next week|later today|tonight)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return clean_value(cleaned)


def is_useful_location(value):
    cleaned = clean_value(value)

    if not cleaned:
        return False

    if "," in cleaned:
        return True

    words = re.findall(r"[a-zA-Z0-9]+", cleaned)

    if len(words) > 12:
        return False

    return True


def is_usable_name(name):
    cleaned = clean_value(name)
    return bool(cleaned) and cleaned.casefold() not in IGNORED_NAME_WORDS


def candidate(item_type, text, scope, importance, confidence, source="chat"):
    cleaned = clean_value(text, max_chars=300)

    if not cleaned:
        return None

    return {
        "type": item_type,
        "text": cleaned,
        "scope": scope,
        "importance": importance,
        "confidence": confidence,
        "source": source,
    }


def extract_name(content):
    patterns = [
        r"\bmy name is\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bmy names\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bmy name's\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bcall me\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\byou can call me\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bi am called\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bi'm called\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        r"\bim called\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)

        if match:
            name = clean_value(match.group(1))

            if is_usable_name(name):
                return candidate(
                    "identity",
                    f"User's name is {name}.",
                    "long",
                    90,
                    95,
                )

    return None


def extract_locations(content):
    location_patterns = [
        (r"\bi live in\s+([^.!?;]+)", "long", 85, 92),
        (r"\bi live near\s+([^.!?;]+)", "long", 80, 88),
        (r"\bi am from\s+([^.!?;]+)", "long", 82, 88),
        (r"\bi'm from\s+([^.!?;]+)", "long", 82, 88),
        (r"\bim from\s+([^.!?;]+)", "long", 82, 88),
        (r"\bi am based in\s+([^.!?;]+)", "long", 82, 88),
        (r"\bi'm based in\s+([^.!?;]+)", "long", 82, 88),
        (r"\bmy location is\s+([^.!?;]+)", "long", 80, 88),
        (r"\bplaces?\s*:\s*([^.!?;]+)", "long", 78, 82),
        (r"\blocations?\s*:\s*([^.!?;]+)", "long", 78, 82),
        (r"\bi am at\s+([^.!?;]+)", "current", 45, 80),
        (r"\bi'm at\s+([^.!?;]+)", "current", 45, 80),
        (r"\bim at\s+([^.!?;]+)", "current", 45, 80),
        (r"\bi am in\s+([^.!?;]+)", "current", 45, 75),
        (r"\bi'm in\s+([^.!?;]+)", "current", 45, 75),
        (r"\bim in\s+([^.!?;]+)", "current", 45, 75),
        (r"\bi am sat in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm sat in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim sat in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bjust sat in\s+([^.!?;]+)", "current", 40, 75),
        (r"\bsat in\s+([^.!?;]+)", "current", 35, 70),
        (r"\bi am sitting in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm sitting in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim sitting in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bsitting in\s+([^.!?;]+)", "current", 35, 70),
        (r"\bi am stood in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm stood in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim stood in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bstood in\s+([^.!?;]+)", "current", 35, 70),
        (r"\bi am standing in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm standing in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim standing in\s+([^.!?;]+)", "current", 40, 80),
        (r"\bstanding in\s+([^.!?;]+)", "current", 35, 70),
        (r"\bi am walking (?:in|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm walking (?:in|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim walking (?:in|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bwalking (?:in|through|around)\s+([^.!?;]+)", "current", 35, 70),
        (r"\bi am wandering (?:in|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm wandering (?:in|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim wandering (?:in|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bwandering (?:in|through|around)\s+([^.!?;]+)", "current", 35, 70),
        (r"\bi am travelling (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm travelling (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim travelling (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi am traveling (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm traveling (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim traveling (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi am driving (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bi'm driving (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bim driving (?:to|through|around)\s+([^.!?;]+)", "current", 40, 80),
        (r"\bon my way to\s+([^.!?;]+)", "current", 40, 80),
        (r"\b(?:heading|going|getting ready to head|getting ready to go)\s+to\s+(?:my\s+)?([^.!?;]*(?:hideout|camp|forest|woods|woodland|cabin)[^.!?;]*)", "mid", 55, 75),
        (r"\bmy\s+((?:hideout|forest camp|camp in the forest|camp in the woods)[^.!?;]*)", "mid", 50, 70),
        (
            r"\bi(?: do)?(?: also)? have\s+(?:a|an|the|my)?\s*([^.!?;]*(?:camp|house|home|cabin|bedroom|room|flat|apartment|garden|office|workshop)[^.!?;]*)",
            "mid",
            55,
            75,
        ),
    ]
    memories = []

    for pattern, scope, importance, confidence in location_patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            place = clean_location_clause(match.group(1))

            if place and is_useful_location(place):
                memories.append(
                    candidate(
                        "location",
                        f"User mentioned this place: {place}.",
                        scope,
                        importance,
                        confidence,
                    )
                )

    return [memory for memory in memories if memory]


def extract_preferences(content):
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
    memories = []

    for pattern in patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            preference = clean_clause(match.group(1))

            if preference:
                memories.append(
                    candidate(
                        "preference",
                        f"User preference: {preference}.",
                        "mid",
                        60,
                        75,
                    )
                )

    return [memory for memory in memories if memory]


def extract_important_facts(content):
    patterns = [
        (r"\bremember this permanently\s*:?\s*(.+)", "long", 95, 95),
        (r"\bremember this\s*:?\s*(.+)", "long", 85, 90),
        (r"\bremember that\s+(.+)", "long", 85, 90),
        (r"\bsave this\s*:?\s*(.+)", "long", 85, 90),
        (r"\bimportant\s*:\s*(.+)", "long", 80, 85),
        (r"\bimportant detail about me\s*,?\s*(.+)", "long", 80, 85),
        (r"\bimportant info about me\s*,?\s*(.+)", "long", 80, 85),
        (r"\bfor future reference\s*,?\s*(.+)", "long", 80, 85),
        (r"\bnote that\s+(.+)", "mid", 70, 80),
        (r"\bi have\s+([^.!?;]+)", "mid", 55, 70),
        (r"\bi work as\s+([^.!?;]+)", "mid", 60, 75),
        (r"\bi study\s+([^.!?;]+)", "mid", 55, 75),
        (r"\bi use\s+([^.!?;]+)", "mid", 50, 70),
        (r"\bi own\s+([^.!?;]+)", "mid", 55, 70),
    ]
    memories = []

    for pattern, scope, importance, confidence in patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            fact = clean_clause(match.group(1))

            if fact:
                memories.append(
                    candidate(
                        "important_fact",
                        f"Important user fact: {fact}.",
                        scope,
                        importance,
                        confidence,
                    )
                )

    return [memory for memory in memories if memory]


def extract_objects(content):
    object_terms = (
        r"laptop|pc|computer|phone|camera|sensor|sensors|tool|tools|tent|"
        r"backpack|rucksack|knife|flask|model|gpu|motherboard|ram|server|"
        r"workstation|program|app|script|exe|bot|robot|battery|charger"
    )
    patterns = [
        rf"\bi(?: have| own| use| am using|'m using|m using| carry| am carrying|'m carrying|m carrying)\s+([^.!?;]*(?:{object_terms})[^.!?;]*)",
        rf"\bmy\s+([^.!?;]*(?:{object_terms})[^.!?;]*)",
    ]
    memories = []

    for pattern in patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            object_text = clean_clause(match.group(1))

            if object_text:
                memories.append(
                    candidate(
                        "object",
                        f"User mentioned this object: {object_text}.",
                        "mid",
                        50,
                        70,
                    )
                )

    memories = [memory for memory in memories if memory]
    filtered = []

    for memory in memories:
        memory_key = (memory.get("text") or "").casefold()
        memory_detail = memory_key.split(":", 1)[-1].strip(" .")
        is_less_specific_duplicate = False

        for other in memories:
            if memory is other:
                continue

            other_key = (other.get("text") or "").casefold()
            other_detail = other_key.split(":", 1)[-1].strip(" .")

            if memory_detail in other_detail and len(memory_detail) < len(other_detail):
                is_less_specific_duplicate = True
                break

        if not is_less_specific_duplicate:
            filtered.append(memory)

    return filtered


def extract_current_context(content):
    context_markers = [
        "right now",
        "currently",
        "at the moment",
        "today",
        "tonight",
        "this morning",
        "this afternoon",
        "this evening",
        "testing",
        "debugging",
    ]
    context_patterns = [
        r"\bjust sat\b",
        r"\bsat in\b",
        r"\bsitting in\b",
        r"\bstood\b",
        r"\bstood in\b",
        r"\bstanding in\b",
        r"\bwalking\b",
        r"\bwalking (?:in|through|around|to)\b",
        r"\bwandering\b",
        r"\bwandering (?:in|through|around)\b",
        r"\btravelling\b",
        r"\btraveling\b",
        r"\bdriving\b",
        r"\bon my way to\b",
        r"\bheading to\b",
        r"\bgoing to\b",
        r"\bgetting ready to head\b",
        r"\bgetting ready to go\b",
        r"\bi am sat\b",
        r"\bi'm sat\b",
        r"\bim sat\b",
        r"\bi am sitting\b",
        r"\bi'm sitting\b",
        r"\bim sitting\b",
        r"\bi am stood\b",
        r"\bi'm stood\b",
        r"\bim stood\b",
        r"\bi am standing\b",
        r"\bi'm standing\b",
        r"\bim standing\b",
        r"\bi am walking\b",
        r"\bi'm walking\b",
        r"\bim walking\b",
        r"\bi am wandering\b",
        r"\bi'm wandering\b",
        r"\bim wandering\b",
        r"\bi am travelling\b",
        r"\bi'm travelling\b",
        r"\bim travelling\b",
        r"\bi am traveling\b",
        r"\bi'm traveling\b",
        r"\bim traveling\b",
        r"\bi am driving\b",
        r"\bi'm driving\b",
        r"\bim driving\b",
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

    memory = candidate(
        "current_context",
        f"Current context: {content}",
        "current",
        40,
        75,
    )
    return [memory] if memory else []


def is_low_value_recent_mention(content):
    cleaned = clean_value(content, max_chars=300)

    if not cleaned:
        return True

    lowered = cleaned.casefold()
    words = re.findall(r"[a-zA-Z0-9]+", lowered)

    if len(words) < 3 and len(cleaned) < 18:
        return True

    low_value_phrases = {
        "hello",
        "hi",
        "hey",
        "ok",
        "okay",
        "yes",
        "no",
        "thanks",
        "thank you",
        "lol",
        "haha",
        "how are you",
        "how are you today",
    }

    if lowered.strip(" .!?") in low_value_phrases:
        return True

    if re.fullmatch(r"[\d\s+\-*/xX=?.]+", cleaned):
        return True

    return False


def recent_mention_importance(content):
    lowered = content.casefold()
    importance = 35

    if re.search(r"\b(?:i|i'm|im|my|me|we|our)\b", lowered):
        importance += 8

    if re.search(
        r"\b(?:testing|debugging|working|building|fixing|trying|using|searching|checking|project|release|model|memory|chat|app|program)\b",
        lowered,
    ):
        importance += 10

    if "," in content or re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", content):
        importance += 7

    if re.search(r"\b(?:important|remember|prefer|need|want|live|from|location)\b", lowered):
        importance += 10

    return min(65, importance)


def extract_recent_mention(content):
    cleaned = clean_value(content, max_chars=260)

    if is_low_value_recent_mention(cleaned):
        return []

    memory = candidate(
        "recent_mention",
        f"Recent user mention: {cleaned}.",
        "current",
        recent_mention_importance(cleaned),
        65,
    )
    return [memory] if memory else []


def extract_project_mentions(content):
    lowered = content.lower()
    project_words = [
        "middai",
        "lm studio",
        "local ai",
        "project 2",
        "project two",
        "release build",
        "memory system",
        "chat app",
    ]

    if not any(word in lowered for word in project_words):
        return []

    memory = candidate(
        "project",
        f"Project context: {content}",
        "mid",
        65,
        70,
    )
    return [memory] if memory else []


def extract_memories_from_user_message(content):
    if not content or has_sensitive_content(content):
        return []

    memories = []
    name = extract_name(content)

    if name:
        memories.append(name)

    memories.extend(extract_locations(content))
    memories.extend(extract_preferences(content))
    memories.extend(extract_important_facts(content))
    memories.extend(extract_objects(content))
    memories.extend(extract_current_context(content))
    memories.extend(extract_project_mentions(content))
    memories.extend(extract_recent_mention(content))

    return memories


def make_search_context(question, answer, sources):
    summary = clean_value(answer, max_chars=260) or "No answer summary available."
    source_urls = []

    for source in sources[:3]:
        url = source.get("url")

        if url:
            source_urls.append(url)

    source_text = f" Sources: {', '.join(source_urls)}." if source_urls else ""

    return candidate(
        "search_context",
        f"User searched: {question}. Answer summary: {summary}.{source_text}",
        "current",
        45,
        85,
        source="search",
    )
