import json
import re

from config import (
    MEMORY_JUDGE_FALLBACK_TO_RULES,
    MEMORY_JUDGE_MAX_EXISTING_ITEMS,
    MEMORY_USE_AI_MEMORY_JUDGE,
)
from llm_client import ask_memory_judge
from .extractor import (
    extract_memories_from_user_message,
    has_sensitive_content,
    clean_value,
    is_usable_name,
)
from .store import iso_now, load_all_memory, parse_time


ALLOWED_TYPES = {
    "identity",
    "location",
    "preference",
    "project",
    "current_context",
    "important_fact",
    "search_context",
    "object",
    "short_term",
}
ALLOWED_SCOPES = {"current", "mid", "long"}
TYPE_ALIASES = {
    "objects": "object",
    "item": "object",
    "items": "object",
    "tool": "object",
    "tools": "object",
    "place": "location",
    "places": "location",
    "fact": "important_fact",
    "important": "important_fact",
}


def fallback_memories(content):
    if not MEMORY_JUDGE_FALLBACK_TO_RULES:
        return []

    return extract_memories_from_user_message(content)


def memory_summary_items():
    try:
        memory = load_all_memory()
    except Exception:
        return []

    items = []

    for scope in ("long", "mid", "current"):
        for item in memory[scope].get("items", []):
            items.append(
                {
                    "type": item.get("type", "memory"),
                    "scope": scope,
                    "text": item.get("text", ""),
                    "importance": item.get("importance", 0),
                    "last_seen": item.get("last_seen", ""),
                }
            )

    items.sort(
        key=lambda item: (
            int(item.get("importance") or 0),
            str(item.get("last_seen") or ""),
        ),
        reverse=True,
    )
    return items[:MEMORY_JUDGE_MAX_EXISTING_ITEMS]


def build_existing_memory_text():
    items = memory_summary_items()

    if not items:
        return "None."

    lines = []

    for number, item in enumerate(items, start=1):
        lines.append(
            (
                f"{number}. type={item['type']} scope={item['scope']} "
                f"importance={item['importance']} text={item['text']}"
            )
        )

    return "\n".join(lines)


def build_judge_prompt(content, now):
    return f"""
You are MiddAI's memory extraction judge.

Your job is NOT to answer the user.
Your job is to decide whether the latest user message contains useful memories for future conversation.

Current UTC date/time:
{now}

Latest user message:
{content}

Existing memories for duplicate checking:
{build_existing_memory_text()}

Return JSON only. No markdown. No explanation.

Return this exact shape:
{{
  "memories": [
    {{
      "type": "location",
      "scope": "current",
      "text": "User is currently in their room in their flat.",
      "importance": 40,
      "confidence": 85,
      "created_at": "{now}",
      "last_seen": "{now}"
    }}
  ]
}}

Allowed type values:
- identity: stable identity facts, such as the user's name.
- location: places connected to the user, current location, regular places, or planned destinations.
- preference: likes, dislikes, preferred style, or recurring choices.
- project: projects the user is working on or planning.
- current_context: what is happening now, today, or in the immediate situation.
- important_fact: explicit facts the user asks you to remember.
- object: physical or digital things the user owns, uses, carries, is building, or is currently working with.
- search_context: only for recent search summaries, usually not from ordinary chat.
- short_term: useful immediate context for follow-up questions that should not become permanent by itself.

Allowed scope values:
- current: temporary or immediate, visible briefly.
- mid: useful recent/repeated/project memory, not permanent.
- long: stable or explicitly permanent memory.

Rules:
- If nothing should be saved, return {{"memories":[]}}.
- Prefer fewer, better memories.
- Explicit identity and stable location statements are worth saving.
- "My name is...", "I'm called...", or "call me..." must produce an identity memory with scope "long".
- "I live in...", "I live near...", "I'm from...", "I'm based in...", or "my location is..." must produce a location memory with scope "long".
- Do not downgrade "I live in..." to a temporary/current location.
- Do not save passwords, API keys, private keys, bank details, or secrets.
- Do not save vague emotional commentary unless it helps future conversation.
- Do not turn random mentioned places into permanent locations.
- Current locations and current activities usually use scope "current".
- Recurring places, projects, and near-future plans usually use scope "mid".
- Names and explicit "remember this" facts usually use scope "long".
- Save identity only when the user explicitly says their name or asks to be called a name.
- Identity text must use exactly this form: "User's name is Name."
- Never infer a name from phrases such as "I'm sat", "I'm in", or "I'm at".
- Object memories should only be saved when the object matters for future help.
- Avoid duplicates. If an existing memory already covers the same fact, repeat it only if the message clearly reinforces it.
- created_at and last_seen must be the current UTC date/time shown above for new memories.
- importance and confidence must be integers from 0 to 100.
""".strip()


def extract_json_object(text):
    cleaned = (text or "").strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("Memory judge did not return a JSON object.")

    return json.loads(cleaned[start : end + 1])


def clamp_score(value, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default

    return max(0, min(100, number))


def normalize_type(value):
    normalized = clean_value(str(value or "").lower().replace(" ", "_"))

    if not normalized:
        return None

    normalized = TYPE_ALIASES.get(normalized, normalized)
    return normalized if normalized in ALLOWED_TYPES else None


def normalize_scope(value):
    normalized = clean_value(str(value or "").lower())
    return normalized if normalized in ALLOWED_SCOPES else None


def normalize_timestamp(value, now):
    if parse_time(value):
        return value

    return now


def validate_memory_item(item, now):
    if not isinstance(item, dict):
        return None

    item_type = normalize_type(item.get("type"))
    scope = normalize_scope(item.get("scope"))
    text = clean_value(item.get("text"), max_chars=300)

    if not item_type or not scope or not text:
        return None

    if has_sensitive_content(text):
        return None

    if item_type == "identity":
        name_patterns = (
            r"\bUser's name is\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
            r"\bThe user's name is\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
            r"\bUser is called\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
            r"\bUser wants to be called\s+([a-zA-Z][a-zA-Z'-]{1,30})\b",
        )
        match = None

        for pattern in name_patterns:
            match = re.search(pattern, text)

            if match:
                break

        if not match or not is_usable_name(match.group(1)):
            return None

        text = f"User's name is {match.group(1)}."

    return {
        "type": item_type,
        "scope": scope,
        "text": text,
        "importance": clamp_score(item.get("importance"), 40),
        "confidence": clamp_score(item.get("confidence"), 70),
        "created_at": normalize_timestamp(item.get("created_at"), now),
        "last_seen": normalize_timestamp(item.get("last_seen"), now),
        "source": "ai_memory_judge",
    }


def validate_judge_response(response_text, now):
    data = extract_json_object(response_text)

    if not isinstance(data, dict):
        return []

    raw_memories = data.get("memories")

    if not isinstance(raw_memories, list):
        return []

    memories = []

    for item in raw_memories:
        memory = validate_memory_item(item, now)

        if memory:
            memories.append(memory)

    return memories


def judge_memories_from_user_message(content, allow_fallback=True):
    if not content or has_sensitive_content(content):
        return []

    if not MEMORY_USE_AI_MEMORY_JUDGE:
        return fallback_memories(content) if allow_fallback else []

    now = iso_now()
    prompt = build_judge_prompt(content, now)

    try:
        response = ask_memory_judge(prompt)
        memories = validate_judge_response(response, now)
    except Exception as error:
        if allow_fallback:
            print(f"Memory judge failed, using fallback rules: {error}")
            return fallback_memories(content)

        print(f"Memory judge refinement failed: {error}")
        return []

    return memories
