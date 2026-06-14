import json
import re

from config import (
    MEMORY_JUDGE_FALLBACK_TO_RULES,
    MEMORY_JUDGE_MAX_EXISTING_ITEMS,
)
from llm_client import ask_memory_judge
from .extractor import (
    ENTITY_MEMORY_TYPES,
    canonical_location_memory_details,
    clean_value,
    extract_memories_from_user_message,
    has_sensitive_content,
    is_usable_name,
    normalize_entity_aliases,
    normalize_entity_name,
    normalize_person_name,
    normalize_relationships,
    object_detail_relationships,
    orient_location_relationships,
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
    "furniture",
    "person",
    "profession",
    "short_term",
}
ALLOWED_SCOPES = {"current", "mid", "long"}
ALLOWED_DECISIONS = {"save", "temporary", "discard"}
TYPE_ALIASES = {
    "objects": "object",
    "item": "object",
    "items": "object",
    "tool": "object",
    "tools": "object",
    "furnishings": "furniture",
    "job": "profession",
    "occupation": "profession",
    "place": "location",
    "places": "location",
    "fact": "important_fact",
    "important": "important_fact",
}


def fallback_memories(content):
    if not MEMORY_JUDGE_FALLBACK_TO_RULES:
        return []

    return extract_memories_from_user_message(content)


def judge_terms(value):
    ignored = {
        "about",
        "and",
        "are",
        "for",
        "from",
        "have",
        "that",
        "the",
        "this",
        "user",
        "with",
        "you",
        "your",
    }
    return {
        word
        for word in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'_-]*", str(value or "").casefold())
        if len(word) >= 3 and word not in ignored
    }


def memory_summary_items(content):
    try:
        memory = load_all_memory()
    except Exception:
        return []

    items = []
    content_terms = judge_terms(content)

    for scope in ("long", "mid", "current"):
        for item in memory[scope].get("items", []):
            if item.get("review_required"):
                continue

            search_text = " ".join(
                [
                    str(item.get("text") or ""),
                    str(item.get("entity_name") or ""),
                    str(item.get("entity_type") or ""),
                    " ".join(str(alias) for alias in item.get("aliases", []) if alias),
                ]
            )
            overlap = len(content_terms & judge_terms(search_text))

            if overlap == 0:
                continue

            items.append(
                {
                    "id": item.get("id"),
                    "type": item.get("type", "memory"),
                    "scope": scope,
                    "text": item.get("text", ""),
                    "entity_name": item.get("entity_name", ""),
                    "aliases": item.get("aliases", []),
                    "importance": item.get("importance", 0),
                    "last_seen": item.get("last_seen", ""),
                    "overlap": overlap,
                }
            )

    items.sort(
        key=lambda item: (
            int(item.get("overlap") or 0),
            int(item.get("importance") or 0),
            str(item.get("last_seen") or ""),
        ),
        reverse=True,
    )
    return items[: min(8, MEMORY_JUDGE_MAX_EXISTING_ITEMS)]


def build_existing_memory_text(content):
    items = memory_summary_items(content)

    if not items:
        return "None."

    lines = []

    for number, item in enumerate(items, start=1):
        lines.append(
            (
                f"{number}. type={item['type']} scope={item['scope']} "
                f"id={item['id']} importance={item['importance']} "
                f"entity={item['entity_name']} aliases={item['aliases']} "
                f"text={item['text']}"
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
{build_existing_memory_text(content)}

Return JSON only. No markdown. No explanation.

Return this exact shape:
{{
  "decision": "temporary",
  "memories": [
    {{
      "type": "location",
      "scope": "current",
      "text": "User is currently in their room in their flat.",
      "importance": 40,
      "confidence": 85,
      "entity_name": "London",
      "entity_type": "place",
      "aliases": ["London"],
      "relationships": [
        {{"type": "resides_in", "target": "London"}}
      ],
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
- furniture: beds, tables, chairs, desks, shelves, sofas, cabinets, and other furniture connected to the user or current scene.
- person: a named person connected to the user, including their relationship.
- profession: the user's explicitly stated job, profession, or occupation.
- search_context: only for recent search summaries, usually not from ordinary chat.
- short_term: useful immediate context for follow-up questions that should not become permanent by itself.

Allowed scope values:
- current: temporary or immediate, visible briefly.
- mid: useful recent/repeated/project memory, not permanent.
- long: stable or explicitly permanent memory.

Rules:
- Always return one decision: "save", "temporary", or "discard".
- Use "save" for useful durable facts. Save memories must use scope "mid" or "long".
- Use "temporary" for useful immediate or uncertain observations. Temporary memories must use scope "current" and will expire after 12 hours unless repeated.
- Use "discard" when the message contains no useful memory. For discard, return an empty memories list.
- Never return an empty memories list with "save" or "temporary".
- Prefer fewer duplicate or vague memories, but never omit a distinct explicitly mentioned entity.
- If one message explicitly mentions several objects, furniture items, people, places, or other useful entities, return one structured memory for every distinct entity.
- Preserve shared placement relationships for every item. Example: "My mug, vape and keys are on the coffee table" must return mug, vape, and keys with located_on "coffee table", plus the coffee table furniture memory with reciprocal has_on details.
- For temporary observations, prefer a structured entity type such as object, furniture, person, location, project, or preference when the entity is known. Use current_context or short_term only when no useful entity can be identified.
- Obvious durable facts may already have been captured by deterministic rules before this review. Do not create a temporary duplicate when an existing mid/long memory already covers the fact.
- A question does not cancel a durable fact elsewhere in the same message. Extract the useful fact and ignore only the question itself.
- Example: "I drive a 2006 Ford Transit. What is there to do in Soho?" must save an object with entity_name "Ford Transit", entity_type "vehicle", relationship {{"type":"model_year","target":"2006"}}, and relationship {{"type":"driven_by","target":"user"}}.
- Explicit identity and stable location statements are worth saving.
- Explicit introductions such as "My name is Gary", "I'm called Gary", "call me Gary", "this is Gary", "Hi, I'm Gary", or standalone "I'm Gary" must produce an identity memory with scope "long".
- "I live in...", "I live near...", "I'm from...", "I'm based in...", "I reside in...", "I'm living in...", "my home is in...", or "my location is..." must produce a location memory with scope "long".
- Do not downgrade "I live in..." to a temporary/current location.
- Do not save passwords, API keys, private keys, bank details, or secrets.
- Do not save vague emotional commentary unless it helps future conversation.
- Do not turn random mentioned places into permanent locations.
- Current locations and current activities usually use scope "current".
- Recurring places, projects, and near-future plans usually use scope "mid".
- Names and explicit "remember this" facts usually use scope "long".
- Save identity only when the user explicitly says their name or asks to be called a name.
- Identity text must use exactly this form: "User's name is Name."
- Never infer a name from a state or activity such as "I'm tired", "I'm happy", "I'm sat", "I'm working", "I'm in", or "I'm at".
- Object memories should only be saved when the object matters for future help.
- Entity names must identify the underlying thing, person, place, job, preference, or project. Do not put a whole sentence, temporary action, material description, or ownership phrase in entity_name.
- Remove leading ownership words and articles from object, furniture, profession, and project entity names. Examples: "a mechanical keyboard" becomes "mechanical keyboard"; "the coffee table" becomes "coffee table"; "my weather station" becomes "weather station".
- Keep useful details in text. Examples: use entity_name "coffee table" with text "User's coffee table is made of oak."; use entity_name "vape" rather than "vape with vape liquid".
- Vehicle make/model belongs in entity_name, while the model year belongs in relationships. Example: entity_name "Ford Transit", not "2006 Ford Transit".
- Add relationships for useful details about any entity type, not only objects. Examples: Lewis with a red coat uses entity_name "Lewis" and relationship {{"type":"has_item","target":"red coat"}}; a vape on a coffee table uses {{"type":"located_on","target":"coffee table"}}.
- When the message adds a detail to an existing entity, return that existing entity with the new relationship instead of creating a sentence-shaped duplicate entity.
- Furniture must use type "furniture", not "object". Include a concise entity name such as "bed", "coffee table", or "office chair".
- Furniture can carry relationships to people or objects. Examples: a user sitting on a bed gives the bed relationship {{"type":"has_on","target":"user"}}; a vape on a coffee table gives the vape {{"type":"located_on","target":"coffee table"}} and the table may receive the reciprocal has_on detail.
- A person's name, the user's name, or an assistant name must never be classified as a project.
- Greetings, direct address, and capability questions about MiddAI are not project memories.
- MiddAI is a project only when the user explicitly discusses developing, testing, debugging, fixing, compiling, releasing, or maintaining the MiddAI software.
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

        name = normalize_person_name(match.group(1))
        text = f"User's name is {name}."

    canonical_location, location_kind, location_relationships = (
        canonical_location_memory_details(
            item.get("entity_name") or text,
            text=text,
            location_relation=item.get("location_relation"),
        )
        if item_type == "location"
        else (None, None, [])
    )
    entity_name = normalize_entity_name(
        item_type,
        canonical_location or item.get("entity_name"),
        text=text,
    )
    aliases = normalize_entity_aliases(
        item_type,
        item.get("aliases") if isinstance(item.get("aliases"), list) else [],
        entity_name,
        text=text,
    )

    if (
        item_type == "project"
        and str(entity_name or "").casefold() == "middai"
        and not re.search(
            r"\b(?:testing|debugging|fixing|building|developing|coding|"
            r"compiling|releasing|updating|maintaining|working\s+on|"
            r"source\s+code|codebase|installer|release\s+build|"
            r"memory\s+system)\b",
            text,
            flags=re.IGNORECASE,
        )
    ):
        return None

    result = {
        "type": item_type,
        "scope": scope,
        "text": text,
        "importance": clamp_score(item.get("importance"), 40),
        "confidence": clamp_score(item.get("confidence"), 70),
        "created_at": normalize_timestamp(item.get("created_at"), now),
        "last_seen": normalize_timestamp(item.get("last_seen"), now),
        "source": "ai_memory_judge",
    }

    if item_type in ENTITY_MEMORY_TYPES and entity_name:
        result["entity_name"] = entity_name
        result["entity_type"] = (
            location_kind
            or clean_value(item.get("entity_type"), max_chars=40)
        )
        result["aliases"] = aliases
        relationships = normalize_relationships(
            item.get("relationships")
            if isinstance(item.get("relationships"), list)
            else []
        )

        if item_type in {"object", "furniture"}:
            relationships = normalize_relationships(
                relationships + object_detail_relationships(text)
            )
        elif item_type == "location" and location_relationships:
            relationships = orient_location_relationships(
                relationships,
                item.get("entity_name") or text,
                canonical_location,
                location_relationships,
            )

        if relationships:
            result["relationships"] = relationships

    return result


def validate_judge_result(response_text, now):
    data = extract_json_object(response_text)

    if not isinstance(data, dict):
        return {
            "decision": "invalid",
            "memories": [],
            "trusted": False,
            "reason": "not_an_object",
        }

    raw_memories = data.get("memories")

    if not isinstance(raw_memories, list):
        return {
            "decision": "invalid",
            "memories": [],
            "trusted": False,
            "reason": "missing_memories",
        }

    memories = []

    for item in raw_memories:
        memory = validate_memory_item(item, now)

        if memory:
            memories.append(memory)

    decision = (
        clean_value(data.get("decision"), max_chars=20) or ""
    ).casefold()

    if decision not in ALLOWED_DECISIONS:
        if memories:
            decision = (
                "temporary"
                if all(memory.get("scope") == "current" for memory in memories)
                else "save"
            )
        else:
            return {
                "decision": "invalid",
                "memories": [],
                "trusted": False,
                "reason": "empty_without_decision",
            }

    if decision == "discard":
        return {
            "decision": "discard",
            "memories": [],
            "trusted": True,
            "reason": None,
        }

    if not memories:
        return {
            "decision": "invalid",
            "memories": [],
            "trusted": False,
            "reason": f"empty_{decision}",
        }

    if decision == "temporary":
        memories = [
            {
                **memory,
                "scope": "current",
                "temporary_observation": True,
            }
            for memory in memories
        ]
    else:
        memories = [
            {
                **memory,
                "scope": (
                    memory.get("scope")
                    if memory.get("scope") in {"mid", "long"}
                    else "mid"
                ),
            }
            for memory in memories
        ]

    return {
        "decision": decision,
        "memories": memories,
        "trusted": True,
        "reason": None,
    }


def validate_judge_response(response_text, now):
    return validate_judge_result(response_text, now)["memories"]


def judge_memory_decision(content, allow_fallback=True):
    if not content or has_sensitive_content(content):
        return {
            "decision": "discard",
            "memories": [],
            "trusted": True,
            "reason": "empty_or_sensitive",
        }

    now = iso_now()
    prompt = build_judge_prompt(content, now)

    try:
        response = ask_memory_judge(prompt)
        result = validate_judge_result(response, now)
    except Exception as error:
        if allow_fallback:
            print(f"Memory judge failed, using fallback rules: {error}")
            return {
                "decision": "fallback",
                "memories": fallback_memories(content),
                "trusted": False,
                "reason": "judge_error",
            }

        print(f"Memory judge refinement failed: {error}")
        return {
            "decision": "invalid",
            "memories": [],
            "trusted": False,
            "reason": "judge_error",
        }

    if not result["trusted"] and allow_fallback:
        result["memories"] = fallback_memories(content)
        result["decision"] = "fallback"

    return result


def judge_memories_from_user_message(content, allow_fallback=True):
    return judge_memory_decision(content, allow_fallback=allow_fallback)["memories"]
