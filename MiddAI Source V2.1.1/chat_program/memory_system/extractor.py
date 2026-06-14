import re


SENSITIVE_PATTERNS = [
    r"\bpassword\b",
    r"\bapi\s*key\b",
    r"\bsecret\b",
    r"\bprivate\s*key\b",
    r"\btoken\b",
]

IGNORED_NAME_WORDS = {
    "afraid",
    "alive",
    "alone",
    "angry",
    "asking",
    "available",
    "awake",
    "back",
    "bad",
    "better",
    "bored",
    "busy",
    "cold",
    "confused",
    "currently",
    "dead",
    "depressed",
    "doing",
    "downloading",
    "drinking",
    "driving",
    "excited",
    "fine",
    "from",
    "good",
    "going",
    "great",
    "having",
    "happy",
    "here",
    "home",
    "hungry",
    "ill",
    "in",
    "into",
    "just",
    "learning",
    "listening",
    "located",
    "lost",
    "on",
    "okay",
    "ok",
    "not",
    "open",
    "over",
    "ready",
    "running",
    "sad",
    "safe",
    "sat",
    "sick",
    "sitting",
    "sorry",
    "standing",
    "still",
    "stood",
    "sure",
    "testing",
    "tired",
    "thinking",
    "travelling",
    "traveling",
    "trying",
    "under",
    "using",
    "very",
    "watching",
    "walking",
    "well",
    "wandering",
    "wondering",
    "working",
    "with",
    "without",
}

NAME_VALUE_PATTERN = r"[a-zA-Z][a-zA-Z'-]{1,30}(?:\s+[a-zA-Z][a-zA-Z'-]{1,30}){0,2}"
NAME_END_PATTERN = r"(?=\s*(?:[,.!?;]|$|\b(?:and|but|because|so|while)\b))"
OBJECT_TERMS = (
    r"laptop|pc|computer|phone|camera|sensor|sensors|tool|tools|tent|"
    r"backpack|rucksack|knife|flask|model|gpu|motherboard|ram|server|"
    r"workstation|program|app|script|exe|bot|robot|battery|charger|"
    r"monitor|screen|display|keyboard|mouse|headphones|headset|speaker|"
    r"microphone|printer|router|modem|tablet|smartwatch|console|controller|"
    r"car keys?|keys?|car|van|truck|bike|bicycle|motorbike|scooter|drone|"
    r"watch|television|tv|mug|cup|glass|bottle|vape|e-cigarette|ecigarette|"
    r"hammer|screwdriver|drill|saw|wrench|spanner|machine|device|"
    r"desk|chair|sofa|couch|table|bed|wardrobe|cabinet|shelf|bookcase|"
    r"drawer|drawers|stool|bench|cupboard|nightstand|bookshelf|furniture"
)
FURNITURE_TERMS = (
    r"desk|chair|sofa|couch|table|bed|wardrobe|cabinet|shelf|bookcase|"
    r"drawer|drawers|stool|bench|cupboard|nightstand|bookshelf|furniture"
)
VEHICLE_TERMS = (
    r"car|van|truck|bike|bicycle|motorbike|motorcycle|scooter|bus|coach|"
    r"taxi|cab|camper|motorhome|suv|pickup|vehicle"
)
ENTITY_MEMORY_TYPES = {
    "identity",
    "location",
    "preference",
    "project",
    "object",
    "furniture",
    "person",
    "profession",
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


def location_hierarchy_details(value):
    cleaned = clean_location_clause(value)

    if not cleaned:
        return None, None, None

    cleaned = re.sub(
        r"^(?:user\s+)?(?:lives?|resides)\s+(?:in|near)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(?:user\s+)?(?:is\s+)?(?:from|based\s+in|currently\s+(?:in|at))\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(?:user's\s+)?(?:home|stated\s+location|location)\s+is\s+(?:in\s+)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(?:user\s+)?(?:mentioned|associated)\s+this\s+place(?:\s+with\s+themselves)?\s*:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = clean_value(cleaned)

    hierarchy_kind = (
        r"district|borough|neighbourhood|neighborhood|suburb|city|town|"
        r"village|county|region|state|province|country|capital"
    )
    match = re.match(
        rf"^(.+?),\s+(?:a|an|the)\s+({hierarchy_kind})\s+(of|in)\s+(.+)$",
        cleaned,
        flags=re.IGNORECASE,
    )

    if not match:
        match = re.match(
            rf"^(.+?)\s+(?:which|that)\s+is\s+(?:a|an|the)\s+"
            rf"({hierarchy_kind})\s+(of|in)\s+(.+)$",
            cleaned,
            flags=re.IGNORECASE,
        )

    if not match:
        relative_match = re.match(
            r"^(.+?)\s+(?:which|that)\s+is\s+(?:located\s+)?in\s+(.+)$",
            cleaned,
            flags=re.IGNORECASE,
        )

        if relative_match:
            place = clean_value(relative_match.group(1), max_chars=100)
            parent = clean_location_clause(relative_match.group(2))

            if place and parent:
                return (
                    place,
                    "district",
                    {
                        "type": "district_of",
                        "target": parent,
                    },
                )

    if not match:
        return cleaned, None, None

    place = clean_value(match.group(1), max_chars=100)
    place_kind = match.group(2).casefold()
    connector = match.group(3).casefold()
    parent = clean_location_clause(match.group(4))

    if not place or not parent:
        return cleaned, None, None

    if place_kind == "neighbourhood":
        place_kind = "neighborhood"

    return (
        place,
        place_kind,
        {
            "type": f"{place_kind}_{connector}",
            "target": parent,
        },
    )


def canonical_location_memory_details(
    value,
    text=None,
    location_relation=None,
):
    place, place_kind, hierarchy = location_hierarchy_details(value)

    if not place:
        return None, None, []

    relation = str(location_relation or "").strip().casefold()
    stable_text = str(text or "").casefold()
    parent_centered = bool(hierarchy) and (
        relation in {"residence", "origin", "base", "stated_location"}
        or any(
            marker in stable_text
            for marker in (
                "user lives in",
                "user resides in",
                "user is from",
                "user is based in",
                "user's home is in",
                "user's stated location is",
            )
        )
    )
    relationships = []

    if parent_centered:
        child_place = place
        parent_place = hierarchy["target"]
        inverse_types = {
            "district_of": "has_district",
            "district_in": "has_district",
            "borough_of": "has_borough",
            "borough_in": "has_borough",
            "neighborhood_of": "has_neighborhood",
            "neighborhood_in": "has_neighborhood",
            "suburb_of": "has_suburb",
            "suburb_in": "has_suburb",
            "city_of": "has_city",
            "city_in": "has_city",
            "town_of": "has_town",
            "town_in": "has_town",
            "village_of": "has_village",
            "village_in": "has_village",
            "county_of": "has_county",
            "county_in": "has_county",
            "region_of": "has_region",
            "region_in": "has_region",
            "state_of": "has_state",
            "state_in": "has_state",
            "province_of": "has_province",
            "province_in": "has_province",
            "country_of": "has_country",
            "country_in": "has_country",
            "capital_of": "has_capital",
            "capital_in": "has_capital",
        }
        inverse_type = inverse_types.get(hierarchy["type"], "contains")
        relationships.append(
            {
                "type": inverse_type,
                "target": child_place,
            }
        )
        place = parent_place
        place_kind = "place"
    elif hierarchy:
        relationships.append(hierarchy)

    if relation == "residence" or "user lives in" in stable_text:
        relationships.append({"type": "has_resident", "target": "user"})

    return place, place_kind, normalize_relationships(relationships)


def orient_location_relationships(
    relationships,
    source_value,
    canonical_location,
    canonical_relationships,
):
    source_place, _, source_hierarchy = location_hierarchy_details(source_value)
    merged = list(relationships or [])

    if (
        source_hierarchy
        and source_place
        and canonical_location
        and source_place.casefold() != canonical_location.casefold()
    ):
        merged = [
            relationship
            for relationship in merged
            if not (
                isinstance(relationship, dict)
                and str(relationship.get("type") or "").casefold()
                == source_hierarchy["type"].casefold()
                and str(relationship.get("target") or "").casefold()
                == source_hierarchy["target"].casefold()
            )
        ]

    return normalize_relationships(
        merged + list(canonical_relationships or [])
    )


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


def location_memory_details(pattern, scope, place):
    normalized_pattern = pattern.casefold()

    if "live near" in normalized_pattern or "home is near" in normalized_pattern:
        return f"User lives near {place}.", "residence"

    if any(
        marker in normalized_pattern
        for marker in (
            "live in",
            "reside in",
            "living in",
            "home is in",
        )
    ):
        return f"User lives in {place}.", "residence"

    if "from" in normalized_pattern:
        return f"User is from {place}.", "origin"

    if "based in" in normalized_pattern:
        return f"User is based in {place}.", "base"

    if "my location is" in normalized_pattern:
        return f"User's stated location is {place}.", "stated_location"

    if "places?" in normalized_pattern or "locations?" in normalized_pattern:
        return f"User associated this place with themselves: {place}.", "associated"

    if scope == "current":
        if any(
            marker in normalized_pattern
            for marker in (
                "travelling",
                "traveling",
                "driving",
                "on my way",
            )
        ):
            return f"User is currently travelling to or around {place}.", "travel"

        if any(marker in normalized_pattern for marker in ("walking", "wandering")):
            return f"User is currently walking in or around {place}.", "current"

        if " at" in normalized_pattern:
            return f"User is currently at {place}.", "current"

        return f"User is currently in {place}.", "current"

    return f"User has or regularly uses this place: {place}.", "regular"


def is_usable_name(name):
    cleaned = clean_value(name)

    if not cleaned or not re.fullmatch(NAME_VALUE_PATTERN, cleaned):
        return False

    words = [word.casefold() for word in cleaned.split()]
    return not any(word in IGNORED_NAME_WORDS for word in words)


def normalize_person_name(name):
    cleaned = clean_value(name)

    if not cleaned:
        return None

    return cleaned.title() if cleaned == cleaned.casefold() else cleaned


def strip_entity_determiner(value, include_the=False):
    determiners = r"my|a|an|this|that"

    if include_the:
        determiners += r"|the"

    return clean_value(
        re.sub(
            rf"^(?:(?:{determiners})\s+)+",
            "",
            value or "",
            flags=re.IGNORECASE,
        )
    )


def object_entity_name(value):
    cleaned = clean_value(value, max_chars=160)

    if not cleaned:
        return None

    object_term = re.search(
        rf"\b(?:{OBJECT_TERMS})\b",
        cleaned,
        flags=re.IGNORECASE,
    )

    if not object_term:
        return strip_entity_determiner(cleaned, include_the=True)

    prefix_words = re.findall(r"[A-Za-z0-9'-]+", cleaned[: object_term.start()])
    boundary_words = {
        "and",
        "bought",
        "carry",
        "carrying",
        "got",
        "has",
        "have",
        "is",
        "are",
        "made",
        "mentioned",
        "near",
        "next",
        "object",
        "of",
        "on",
        "owns",
        "for",
        "refilled",
        "recently",
        "there",
        "there's",
        "this",
        "to",
        "uses",
        "using",
        "was",
        "were",
        "with",
    }
    modifiers = []

    for word in reversed(prefix_words):
        if word.casefold() in boundary_words or len(modifiers) >= 3:
            break

        modifiers.append(word)

    object_name = " ".join(
        [*reversed(modifiers), object_term.group(0)]
    )
    noise_words = {
        "a",
        "an",
        "the",
        "my",
        "this",
        "that",
        "their",
        "his",
        "her",
        "user",
        "users",
        "owns",
        "uses",
        "using",
        "has",
        "have",
        "mentioned",
        "object",
        "just",
        "recently",
        "bought",
        "got",
        "refilled",
    }
    words = object_name.split()

    while len(words) > 1 and words[0].casefold() in noise_words:
        words.pop(0)

    return clean_value(" ".join(words), max_chars=80)


def object_memory_type(value):
    object_name = object_entity_name(value)

    if object_name and re.search(
        rf"\b(?:{FURNITURE_TERMS})\b$",
        object_name,
        flags=re.IGNORECASE,
    ):
        return "furniture"

    return "object"


def explicit_object_mentions(value):
    mentions = []
    seen = set()
    matches = list(
        re.finditer(
        rf"\b(?:{OBJECT_TERMS})\b",
        value or "",
        flags=re.IGNORECASE,
        )
    )

    for index, match in enumerate(matches):
        clause_start = max(
            value.rfind(".", 0, match.start()),
            value.rfind("!", 0, match.start()),
            value.rfind("?", 0, match.start()),
            value.rfind(";", 0, match.start()),
            value.rfind(",", 0, match.start()),
        )
        previous_object_end = matches[index - 1].end() if index else 0
        local_start = max(
            clause_start + 1,
            previous_object_end,
            match.start() - 80,
        )
        object_name = object_entity_name(value[local_start : match.end()])

        if not object_name:
            continue

        key = object_name.casefold()

        if key in seen:
            continue

        mentions.append(
            {
                "name": object_name,
                "type": object_memory_type(object_name),
                "start": match.start(),
                "end": match.end(),
            }
        )
        seen.add(key)

    return mentions


def sentence_ranges(value):
    start = 0

    for match in re.finditer(r"[.!?;]+", value or ""):
        end = match.start()

        if value[start:end].strip():
            yield start, end

        start = match.end()

    if value[start:].strip():
        yield start, len(value)


def mention_is_on_target(sentence, mention_start):
    prefix = sentence[:mention_start]
    return bool(
        re.search(
            r"\bon\s+(?:(?:my|the|a|an)\s+)?"
            r"(?:[A-Za-z0-9'-]+\s+){0,3}$",
            prefix,
            flags=re.IGNORECASE,
        )
    )


def extract_all_explicit_object_mentions(content):
    ownership_or_scene = re.search(
        r"\b(?:i\s+(?:have|own|use|carry|put|left|placed|kept)|"
        r"i\s+am\s+(?:using|carrying|sat|sitting|lying)|"
        r"i'm\s+(?:using|carrying|sat|sitting|lying)|"
        r"im\s+(?:using|carrying|sat|sitting|lying)|"
        r"my|there(?:'s| is))\b",
        content,
        flags=re.IGNORECASE,
    )

    if not ownership_or_scene:
        return []

    memories = []

    for sentence_start, sentence_end in sentence_ranges(content):
        sentence = content[sentence_start:sentence_end]
        mentions = explicit_object_mentions(sentence)

        if not mentions:
            continue

        placement_targets = [
            mention
            for mention in mentions
            if mention["type"] == "furniture"
            and mention_is_on_target(sentence, mention["start"])
        ]
        placement_target = placement_targets[-1] if placement_targets else None
        placed_objects = [
            mention
            for mention in mentions
            if placement_target
            and mention["type"] == "object"
            and mention["name"].casefold()
            != placement_target["name"].casefold()
        ]

        for index, mention in enumerate(mentions):
            next_start = (
                mentions[index + 1]["start"]
                if index + 1 < len(mentions)
                else len(sentence)
            )
            detail_fragment = clean_value(
                sentence[mention["start"] : next_start],
                max_chars=180,
            )
            relationships = object_detail_relationships(detail_fragment or "")

            if (
                placement_target
                and mention["type"] == "object"
                and mention["name"].casefold()
                != placement_target["name"].casefold()
            ):
                relationships = normalize_relationships(
                    relationships
                    + [
                        {
                            "type": "located_on",
                            "target": placement_target["name"],
                        }
                    ]
                )

            if (
                placement_target
                and mention["name"].casefold()
                == placement_target["name"].casefold()
            ):
                relationships = normalize_relationships(
                    relationships
                    + [
                        {
                            "type": "has_on",
                            "target": placed["name"],
                        }
                        for placed in placed_objects
                    ]
                )

            memory_text = object_memory_text_from_relationships(
                mention["name"],
                relationships,
            )

            if not memory_text:
                memory_text = (
                    f"User mentioned this furniture: {mention['name']}."
                    if mention["type"] == "furniture"
                    else f"User mentioned this object: {mention['name']}."
                )

            memories.append(
                candidate(
                    mention["type"],
                    memory_text,
                    "mid",
                    50,
                    78,
                    entity_name=mention["name"],
                    entity_type=mention["type"],
                    aliases=[mention["name"]],
                    relationships=relationships,
                )
            )

    return deduplicate_structured_memories(
        [memory for memory in memories if memory]
    )


def driven_vehicle_details(value):
    cleaned = clean_clause(value)

    if not cleaned:
        return None, []

    cleaned = re.sub(
        r"^(?:a|an|the|my)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = clean_value(cleaned, max_chars=120)

    if not cleaned or re.match(
        r"^(?:to|through|around|into|from|home|work)\b",
        cleaned,
        flags=re.IGNORECASE,
    ):
        return None, []

    if cleaned.casefold() in {
        "hard bargain",
        "long way",
        "little",
        "lot",
        "people crazy",
    }:
        return None, []

    words = re.findall(r"[A-Za-z0-9'-]+", cleaned)

    if not words or len(words) > 7:
        return None, []

    year_match = re.match(r"^((?:19|20)\d{2})\s+(.+)$", cleaned)
    model_year = year_match.group(1) if year_match else None
    vehicle_name = clean_value(
        year_match.group(2) if year_match else cleaned,
        max_chars=80,
    )

    if not vehicle_name:
        return None, []

    if (
        not model_year
        and not re.search(
            rf"\b(?:{VEHICLE_TERMS})\b",
            vehicle_name,
            flags=re.IGNORECASE,
        )
        and len(re.findall(r"[A-Za-z0-9'-]+", vehicle_name)) < 2
    ):
        return None, []

    relationships = [{"type": "driven_by", "target": "user"}]

    if model_year:
        relationships.insert(0, {"type": "model_year", "target": model_year})

    return vehicle_name, relationships


def normalize_entity_name(item_type, value, text=None):
    if item_type not in ENTITY_MEMORY_TYPES:
        return None

    cleaned = clean_value(value, max_chars=160)
    source = cleaned or clean_value(text, max_chars=240)

    if not source:
        return None

    if item_type in {"identity", "person"}:
        if item_type == "identity":
            match = re.search(
                r"\bname is\s+([A-Za-z][A-Za-z'-]{1,30}(?:\s+[A-Za-z][A-Za-z'-]{1,30})?)",
                str(text or source),
                flags=re.IGNORECASE,
            )

            if match:
                cleaned = match.group(1)
        elif cleaned:
            cleaned = re.split(
                r"\s+(?:has|owns|wears|uses|lives|resides|works|is)\b",
                cleaned,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
        else:
            match = re.match(r"\s*([A-Za-z][A-Za-z'-]{1,30})\b", source)
            cleaned = match.group(1) if match else None

        return normalize_person_name(cleaned)

    if item_type in {"object", "furniture"}:
        object_name = object_entity_name(source)
        vehicle_context = f"{source} {text or ''}"

        if item_type == "object" and object_name and re.search(
            rf"\b(?:drive|drives|driven|vehicle|{VEHICLE_TERMS})\b",
            vehicle_context,
            flags=re.IGNORECASE,
        ):
            object_name = re.sub(
                r"^(?:19|20)\d{2}\s+",
                "",
                object_name,
            )

        return clean_value(object_name, max_chars=80)

    if item_type == "location":
        if not cleaned:
            match = re.search(
                r"\b(?:lives? (?:in|near)|is from|is based in|is currently "
                r"(?:in|at)|location is|mentioned this place\s*:|"
                r"associated this place\s*:)\s*(.+)$",
                source,
                flags=re.IGNORECASE,
            )
            cleaned = match.group(1) if match else source

        entity_name, _, _ = canonical_location_memory_details(
            cleaned,
            text=text,
        )
        return entity_name

    if item_type == "preference":
        cleaned = re.sub(
            r"^(?:user preference|the user (?:likes|loves|prefers|dislikes))\s*:?\s*",
            "",
            cleaned or source,
            flags=re.IGNORECASE,
        )
        return clean_clause(cleaned)

    if item_type == "profession":
        cleaned = re.sub(
            r"^(?:user'?s? (?:profession|job|occupation) is|"
            r"the user (?:works as|is employed as))\s+",
            "",
            cleaned or source,
            flags=re.IGNORECASE,
        )
        cleaned = clean_clause(cleaned)

        if not cleaned:
            return None

        cleaned = re.split(
            r"\s+(?:at|for)\s+(?:a|an|the)?\s*[A-Za-z0-9]",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        return strip_entity_determiner(cleaned, include_the=True)

    if item_type == "project":
        cleaned = re.sub(
            r"^(?:project context|user project|the user is (?:working on|"
            r"building|developing|creating))\s*:?\s*",
            "",
            cleaned or source,
            flags=re.IGNORECASE,
        )
        cleaned = clean_clause(cleaned)
        cleaned = re.split(
            r"\s+(?:uses|has|runs|depends|is built|is hosted|is stored)\b",
            cleaned or "",
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        return strip_entity_determiner(cleaned)

    return cleaned


def normalize_entity_aliases(item_type, aliases, entity_name, text=None):
    normalized = []

    for value in [entity_name, *(aliases or [])]:
        alias = normalize_entity_name(item_type, value, text=text)

        if alias and alias.casefold() not in {
            existing.casefold() for existing in normalized
        }:
            normalized.append(alias)

    return normalized[:8]


def candidate(
    item_type,
    text,
    scope,
    importance,
    confidence,
    source="chat",
    **metadata,
):
    cleaned = clean_value(text, max_chars=300)

    if not cleaned:
        return None

    result = {
        "type": item_type,
        "text": cleaned,
        "scope": scope,
        "importance": importance,
        "confidence": confidence,
        "source": source,
    }

    result.update(metadata)

    if item_type in ENTITY_MEMORY_TYPES:
        location_source = result.get("entity_name") or cleaned
        canonical_location, location_kind, location_relationships = (
            canonical_location_memory_details(
                location_source,
                text=cleaned,
                location_relation=result.get("location_relation"),
            )
            if item_type == "location"
            else (None, None, [])
        )
        if item_type == "location" and canonical_location:
            result["entity_name"] = canonical_location
        entity_name = normalize_entity_name(
            item_type,
            result.get("entity_name"),
            text=cleaned,
        )

        if entity_name:
            result["entity_name"] = entity_name
            result["aliases"] = normalize_entity_aliases(
                item_type,
                result.get("aliases"),
                entity_name,
                text=cleaned,
            )
            if location_kind:
                result["entity_type"] = location_kind
            if location_relationships:
                result["relationships"] = orient_location_relationships(
                    result.get("relationships"),
                    location_source,
                    canonical_location,
                    location_relationships,
                )
        else:
            result.pop("entity_name", None)
            result.pop("aliases", None)
    else:
        result.pop("entity_name", None)
        result.pop("entity_type", None)
        result.pop("aliases", None)

    return result


def extract_name(content):
    patterns = [
        rf"\bmy name is\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\bmy names\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\bmy name's\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\bcall me\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\byou can call me\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\bi am called\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\bi'm called\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\bim called\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\b(?:hi|hello|hey)[,! ]+\s*this is\s+({NAME_VALUE_PATTERN}){NAME_END_PATTERN}",
        rf"\bthis is\s+({NAME_VALUE_PATTERN})\s+speaking\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)

        if match:
            name = normalize_person_name(match.group(1))

            if is_usable_name(name):
                return candidate(
                    "identity",
                    f"User's name is {name}.",
                    "long",
                    90,
                    95,
                    entity_name=name,
                    entity_type="user_identity",
                    aliases=[name],
                    protected=True,
                )

    bare_patterns = (
        rf"\b(?:i am|i'm|im)\s+({NAME_VALUE_PATTERN})(?=\s*(?:[,.!?;]|$))",
        rf"\b({NAME_VALUE_PATTERN})\s+here(?=\s*(?:[,.!?;]|$))",
    )
    introduction_hint = bool(
        re.search(
            r"\b(?:hi|hello|hey|introducing myself|wanted to introduce myself)\b",
            content,
            flags=re.IGNORECASE,
        )
    )

    for pattern in bare_patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)

        if not match:
            continue

        name = normalize_person_name(match.group(1))
        original_name = match.group(1).strip()
        is_standalone = bool(
            re.fullmatch(
                rf"\s*(?:(?:i am|i'm|im)\s+{NAME_VALUE_PATTERN}|"
                rf"{NAME_VALUE_PATTERN}\s+here)\s*[.!?]?\s*",
                content,
                flags=re.IGNORECASE,
            )
        )
        looks_named = original_name[:1].isupper()
        is_single_word = len(original_name.split()) == 1

        if not (
            introduction_hint
            or looks_named
            or (is_standalone and is_single_word)
        ):
            continue

        if is_usable_name(name):
            return candidate(
                "identity",
                f"User's name is {name}.",
                "long",
                90,
                93,
                entity_name=name,
                entity_type="user_identity",
                aliases=[name],
                protected=True,
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
        (r"\bim based in\s+([^.!?;]+)", "long", 82, 88),
        (r"\bi reside in\s+([^.!?;]+)", "long", 82, 88),
        (r"\bi am living in\s+([^.!?;]+)", "long", 82, 86),
        (r"\bi'm living in\s+([^.!?;]+)", "long", 82, 86),
        (r"\bim living in\s+([^.!?;]+)", "long", 82, 86),
        (r"\bmy home is in\s+([^.!?;]+)", "long", 84, 90),
        (r"\bmy home is near\s+([^.!?;]+)", "long", 82, 88),
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
            place, place_kind, hierarchy = location_hierarchy_details(
                match.group(1)
            )

            if place and is_useful_location(place):
                memory_text, location_relation = location_memory_details(
                    pattern,
                    scope,
                    place,
                )
                memories.append(
                    candidate(
                        "location",
                        memory_text,
                        scope,
                        importance,
                        confidence,
                        entity_name=match.group(1),
                        entity_type=place_kind or "place",
                        aliases=[match.group(1)],
                        relationships=[],
                        location_relation=location_relation,
                        protected=(
                            scope == "long"
                            and "places?" not in pattern
                            and "locations?" not in pattern
                        ),
                    )
                )

    return [memory for memory in memories if memory]


PREFERENCE_CATEGORY_PATTERN = (
    r"drink|beverage|food|meal|snack|colour|color|music|song|film|movie|"
    r"book|game|hobby|activity"
)


def preference_from_previous_clause(content, fragment_start):
    previous_content = content[:fragment_start].rstrip()

    if not previous_content:
        return None

    clauses = [
        clean_value(clause)
        for clause in re.split(r"[.!?;]+", previous_content)
        if clean_value(clause)
    ]

    if not clauses:
        return None

    previous_clause = clauses[-1]
    match = re.search(
        (
            r"\b(?:make|making|brew|brewing|drink|drinking|eat|eating|cook|"
            r"cooking|watch|watching|read|reading|play|playing|have|having|"
            r"order|ordering|listen(?:ing)?\s+to)\s+"
            r"(?:myself\s+)?(?:a|an|some|the\s+)?([^.!?;]+)$"
        ),
        previous_clause,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    preference = clean_clause(match.group(1))

    if not preference or len(preference.split()) > 8:
        return None

    return preference


def extract_preferences(content):
    patterns = [
        r"\bi really like\s+([^.!?;]+)",
        r"\bi like\s+([^.!?;]+)",
        r"\bi love\s+([^.!?;]+)",
        r"\bi enjoy\s+([^.!?;]+)",
        r"\bi prefer\s+([^.!?;]+)",
        r"\bi don't like\s+([^.!?;]+)",
        r"\bi do not like\s+([^.!?;]+)",
        r"\bi dislike\s+([^.!?;]+)",
        r"\bi hate\s+([^.!?;]+)",
        r"\bi can't stand\s+([^.!?;]+)",
        r"\bi cannot stand\s+([^.!?;]+)",
        r"\bi'm into\s+([^.!?;]+)",
        r"\bim into\s+([^.!?;]+)",
        r"\bi would rather\s+([^.!?;]+)",
        r"\bi'd rather\s+([^.!?;]+)",
    ]
    memories = []
    explicit_patterns = [
        (
            rf"\bmy\s+(?:favourite|favorite|preferred)\s+"
            rf"(?:{PREFERENCE_CATEGORY_PATTERN})\s+is\s+([^.!?;]+)",
            1,
        ),
        (
            rf"(?:^|[.!?;]\s*)([^.!?;]+?)\s+is\s+my\s+"
            rf"(?:favourite|favorite|preferred)\s+"
            rf"(?:{PREFERENCE_CATEGORY_PATTERN})\b",
            1,
        ),
    ]

    for pattern, group_number in explicit_patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            preference = clean_clause(match.group(group_number))

            if preference:
                memories.append(
                    candidate(
                        "preference",
                        f"User preference: {preference}.",
                        "mid",
                        60,
                        82,
                        entity_name=preference,
                        entity_type="preference",
                        aliases=[preference],
                    )
                )

    fragment_pattern = (
        rf"\bmy\s+(?:favourite|favorite|preferred)\s+"
        rf"(?:{PREFERENCE_CATEGORY_PATTERN})\s*(?=[.!?;]|$)"
    )

    for match in re.finditer(fragment_pattern, content, flags=re.IGNORECASE):
        preference = preference_from_previous_clause(content, match.start())

        if preference:
            memories.append(
                candidate(
                    "preference",
                    f"User preference: {preference}.",
                    "mid",
                    60,
                    80,
                    entity_name=preference,
                    entity_type="preference",
                    aliases=[preference],
                )
            )

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
                        entity_name=preference,
                        entity_type="preference",
                        aliases=[preference],
                    )
                )

    generic_pattern = r"\bmy\s+(?:favourite|favorite|preferred)\s+([^.!?;]+)"

    for match in re.finditer(generic_pattern, content, flags=re.IGNORECASE):
        preference = clean_clause(match.group(1))

        if not preference:
            continue

        if re.match(
            rf"^(?:{PREFERENCE_CATEGORY_PATTERN})(?:\s+is\b|$)",
            preference,
            flags=re.IGNORECASE,
        ):
            continue

        memories.append(
            candidate(
                "preference",
                f"User preference: {preference}.",
                "mid",
                60,
                75,
                entity_name=preference,
                entity_type="preference",
                aliases=[preference],
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


def object_detail_relationships(object_text):
    relationships = []
    made_of = re.search(
        r"\b(?:is\s+)?made\s+(?:of|from)\s+"
        r"(.+?)(?=\s+(?:next\s+to|beside|near)\b|[.!?;]|$)",
        object_text,
        flags=re.IGNORECASE,
    )

    if made_of:
        material = clean_value(made_of.group(1), max_chars=60)

        if material:
            relationships.append({"type": "made_of", "target": material})

    filled_with = re.search(
        r"\bwith\s+([^.!?;]+?)(?=\s+and\s+(?:left|placed|put|kept)\b|$)",
        object_text,
        flags=re.IGNORECASE,
    )

    if filled_with:
        contents = clean_value(filled_with.group(1), max_chars=60)

        if contents and re.search(
            r"\b(?:liquid|fluid|fuel|water|coffee|tea|ink|oil)\b",
            contents,
            flags=re.IGNORECASE,
        ):
            relationships.append({"type": "filled_with", "target": contents})

    located_on = re.search(
        rf"\b(?:left|placed|put|kept)\s+(?:it\s+)?on\s+(?:the\s+)?"
        rf"([^.!?;]*(?:{OBJECT_TERMS})[^.!?;]*)$",
        object_text,
        flags=re.IGNORECASE,
    )

    if located_on:
        target = object_entity_name(located_on.group(1))

        if target:
            relationships.append({"type": "located_on", "target": target})

    vehicle_context = re.search(
        rf"\b(?:drive|drives|driven|vehicle|{VEHICLE_TERMS})\b",
        object_text,
        flags=re.IGNORECASE,
    )
    model_year = re.search(r"\b((?:19|20)\d{2})\b", object_text)

    if vehicle_context and model_year:
        relationships.append(
            {"type": "model_year", "target": model_year.group(1)}
        )

    if re.search(r"\buser drives\b", object_text, flags=re.IGNORECASE):
        relationships.append({"type": "driven_by", "target": "user"})

    return normalize_relationships(relationships)


def normalize_relationships(relationships):
    normalized = []
    seen = set()

    for relationship in relationships or []:
        if not isinstance(relationship, dict):
            continue

        relation_type = clean_value(
            str(relationship.get("type") or "").replace(" ", "_"),
            max_chars=40,
        )
        target = clean_value(relationship.get("target"), max_chars=100)

        if not relation_type or not target:
            continue

        relation = {
            "type": relation_type.casefold(),
            "target": target,
        }
        key = (relation["type"], relation["target"].casefold())

        if key not in seen:
            normalized.append(relation)
            seen.add(key)

    return normalized[:12]


def clean_relationship_target(value):
    target = clean_clause(value)

    if not target:
        return None

    target = re.sub(
        r"^(?:a|an|the|my|his|her|their|its)\s+",
        "",
        target,
        flags=re.IGNORECASE,
    )
    return clean_value(target, max_chars=100)


def extract_known_entity_details(content, known_entities):
    memories = []

    for known in known_entities or []:
        if not isinstance(known, dict):
            continue

        item_type = str(known.get("type") or "").strip()
        entity_name = clean_value(known.get("entity_name"), max_chars=100)

        if item_type not in ENTITY_MEMORY_TYPES or not entity_name:
            continue

        aliases = [
            clean_value(value, max_chars=100)
            for value in [entity_name, *(known.get("aliases") or [])]
        ]
        aliases = sorted(
            {value for value in aliases if value},
            key=len,
            reverse=True,
        )
        matched_relationships = []
        matched_text = None

        for alias in aliases:
            escaped_alias = re.escape(alias)
            patterns = (
                (
                    rf"\b{escaped_alias}\s+has\s+(?:a|an|the)?\s*"
                    r"(.+?)\s+on\s+(?:it|them)\b",
                    "has_on",
                ),
                (
                    rf"\b{escaped_alias}\s+(?:has|owns)\s+([^.!?;]+)",
                    "has_item",
                ),
                (
                    rf"\b{escaped_alias}\s+(?:wears|is wearing)\s+([^.!?;]+)",
                    "wears",
                ),
                (
                    rf"\b{escaped_alias}\s+(?:uses|is using)\s+([^.!?;]+)",
                    "uses",
                ),
                (
                    rf"\b{escaped_alias}\s+(?:likes|loves|prefers)\s+([^.!?;]+)",
                    "prefers",
                ),
                (
                    rf"\b{escaped_alias}\s+(?:lives|resides)\s+in\s+([^.!?;]+)",
                    "resides_in",
                ),
                (
                    rf"\b{escaped_alias}\s+works\s+(?:at|for)\s+([^.!?;]+)",
                    "works_at",
                ),
                (
                    rf"\b{escaped_alias}\s+is\s+(?:located\s+)?on\s+([^.!?;]+)",
                    "located_on",
                ),
                (
                    rf"\b{escaped_alias}\s+is\s+(?:located\s+)?"
                    r"(?:in|inside)\s+([^.!?;]+)",
                    "located_in",
                ),
                (
                    rf"\b{escaped_alias}\s+is\s+made\s+(?:of|from)\s+([^.!?;]+)",
                    "made_of",
                ),
                (
                    rf"\b(?:i\s+)?(?:put|left|placed|kept)\s+(?:my|the)?\s*"
                    rf"{escaped_alias}\s+on\s+([^.!?;]+)",
                    "located_on",
                ),
                (
                    rf"\b(?:i\s+)?(?:put|left|placed|kept)\s+(?:my|the)?\s*"
                    rf"{escaped_alias}\s+(?:in|inside)\s+([^.!?;]+)",
                    "located_in",
                ),
            )

            for pattern, relation_type in patterns:
                match = re.search(pattern, content, flags=re.IGNORECASE)

                if not match:
                    continue

                target = clean_relationship_target(match.group(1))

                if not target:
                    continue

                if relation_type == "has_on":
                    target = re.sub(
                        r"\s+on\s+(?:it|them)$",
                        "",
                        target,
                        flags=re.IGNORECASE,
                    )
                    target = clean_relationship_target(target)

                if not target:
                    continue

                matched_relationships.append(
                    {"type": relation_type, "target": target}
                )
                matched_text = clean_value(match.group(0), max_chars=260)

            if matched_relationships:
                break

        matched_relationships = normalize_relationships(matched_relationships)

        if not matched_relationships:
            continue

        memories.append(
            candidate(
                item_type,
                matched_text or f"User provided another detail about {entity_name}.",
                known.get("scope") or "mid",
                max(50, int(known.get("importance") or 0)),
                max(75, int(known.get("confidence") or 0)),
                entity_name=entity_name,
                entity_type=known.get("entity_type") or item_type,
                aliases=aliases,
                relationships=matched_relationships,
            )
        )

    return deduplicate_structured_memories(
        [memory for memory in memories if memory]
    )


def object_memory_text_from_relationships(object_name, relationships):
    plural_object = re.search(
        r"\b(?:keys|sensors|tools|headphones|drawers)\s*$",
        object_name,
        flags=re.IGNORECASE,
    )
    past_copula = "were" if plural_object else "was"
    relation_targets = {
        relationship["type"]: relationship["target"]
        for relationship in normalize_relationships(relationships)
    }

    if relation_targets.get("made_of"):
        return (
            f"User's {object_name} is made of "
            f"{relation_targets['made_of']}."
        )

    if relation_targets.get("filled_with") and relation_targets.get("located_on"):
        return (
            f"User's {object_name} {past_copula} filled with "
            f"{relation_targets['filled_with']} and left on the "
            f"{relation_targets['located_on']}."
        )

    if relation_targets.get("filled_with"):
        return (
            f"User's {object_name} {past_copula} filled with "
            f"{relation_targets['filled_with']}."
        )

    if relation_targets.get("located_on"):
        return (
            f"User's {object_name} {past_copula} left on the "
            f"{relation_targets['located_on']}."
        )

    return None


def object_memory_text(object_text, object_name):
    relationships = object_detail_relationships(object_text)
    relationship_text = object_memory_text_from_relationships(
        object_name,
        relationships,
    )

    if relationship_text:
        return relationship_text

    described_as = re.search(
        r"\bis\s+([^.!?;]+)$",
        object_text,
        flags=re.IGNORECASE,
    )

    if described_as:
        description = clean_value(described_as.group(1), max_chars=80)

        if description:
            return f"User's {object_name} is {description}."

    return f"User mentioned this object: {object_name}."


def last_object_entity(value):
    matches = list(
        re.finditer(
            rf"\b((?:[A-Za-z0-9'-]+\s+){{0,3}}(?:{OBJECT_TERMS}))\b",
            value or "",
            flags=re.IGNORECASE,
        )
    )

    if not matches:
        return None

    return object_entity_name(matches[-1].group(1))


def add_object_placement_memory(memories, object_name, target):
    object_name = object_entity_name(object_name)
    target = object_entity_name(target)

    if not object_name or not target or object_name.casefold() == target.casefold():
        return

    placement = {"type": "located_on", "target": target}

    for memory in reversed(memories):
        if (
            memory.get("type") in {"object", "furniture"}
            and str(memory.get("entity_name") or "").casefold()
            == object_name.casefold()
        ):
            relationships = normalize_relationships(
                list(memory.get("relationships") or []) + [placement]
            )
            memory["relationships"] = relationships
            relationship_text = object_memory_text_from_relationships(
                object_name,
                relationships,
            )

            if relationship_text:
                memory["text"] = clean_value(relationship_text, max_chars=300)

            return

    memory_type = object_memory_type(object_name)
    memories.append(
        candidate(
            memory_type,
            object_memory_text_from_relationships(
                object_name,
                [placement],
            ),
            "mid",
            50,
            78,
            entity_name=object_name,
            entity_type=memory_type,
            aliases=[object_name],
            relationships=[placement],
        )
    )


def extract_objects(content):
    patterns = [
        rf"\bi(?: have| own| use| am using|'m using|m using| carry| am carrying|'m carrying|m carrying)\s+([^.!?;]*(?:{OBJECT_TERMS})[^.!?;]*)",
        rf"\bmy\s+([^.!?;]*(?:{OBJECT_TERMS})[^.!?;]*)",
    ]
    memories = []

    driven_vehicle_pattern = (
        r"\bi\s+(?:currently\s+)?drive\s+"
        r"((?:a|an|the|my)\s+[^.!?;]+)"
    )

    for match in re.finditer(
        driven_vehicle_pattern,
        content,
        flags=re.IGNORECASE,
    ):
        vehicle_phrase = clean_clause(match.group(1))
        vehicle_name, relationships = driven_vehicle_details(vehicle_phrase)

        if not vehicle_name:
            continue

        year = next(
            (
                relationship["target"]
                for relationship in relationships
                if relationship["type"] == "model_year"
            ),
            None,
        )
        described_vehicle = (
            f"{year} {vehicle_name}"
            if year
            else vehicle_name
        )
        memories.append(
            candidate(
                "object",
                f"User drives a {described_vehicle}.",
                "mid",
                65,
                88,
                entity_name=vehicle_name,
                entity_type="vehicle",
                aliases=[vehicle_name, described_vehicle],
                relationships=relationships,
            )
        )

    for pattern in patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            raw_object_text = clean_value(match.group(1))
            object_text = clean_clause(raw_object_text)
            object_name = object_entity_name(object_text)

            if object_text and object_name:
                detail_text = object_text
                action_continuation = re.search(
                    r"\s+and\s+(?:left|placed|put|kept)\b.+$",
                    raw_object_text or "",
                    flags=re.IGNORECASE,
                )

                if action_continuation:
                    detail_text = clean_value(
                        f"{object_text}{action_continuation.group(0)}"
                    )

                memory_type = object_memory_type(object_name)
                memories.append(
                    candidate(
                        memory_type,
                        object_memory_text(detail_text, object_name),
                        "mid",
                        50,
                        70,
                        entity_name=object_name,
                        entity_type=memory_type,
                        aliases=[object_name],
                        relationships=object_detail_relationships(detail_text),
                    )
                )

    furniture_phrase = (
        rf"((?:[A-Za-z0-9'-]+\s+){{0,3}}(?:{FURNITURE_TERMS})"
        rf"(?:\s+made\s+(?:of|from)\s+[^.!?;]+)?)"
    )
    furniture_presence_patterns = (
        rf"\bthere(?:'s| is)\s+(?:a|an|the)?\s*{furniture_phrase}",
        rf"\b(?:i am|i'm|im)\s+(?:sat|sitting|lying)\s+on\s+"
        rf"(?:my|a|an|the)?\s*{furniture_phrase}",
    )

    for pattern_index, pattern in enumerate(furniture_presence_patterns):
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            furniture_text = clean_clause(match.group(1))
            furniture_name = object_entity_name(furniture_text)

            if not furniture_name:
                continue

            relationships = object_detail_relationships(furniture_text)
            scope = "mid" if relationships else "current"

            if pattern_index == 1:
                relationships = normalize_relationships(
                    relationships + [{"type": "has_on", "target": "user"}]
                )
                scope = "current"

            text = object_memory_text(furniture_text, furniture_name)

            if pattern_index == 1:
                text = f"User is currently sitting on the {furniture_name}."

            memories.append(
                candidate(
                    "furniture",
                    text,
                    scope,
                    50 if scope == "mid" else 40,
                    78,
                    entity_name=furniture_name,
                    entity_type="furniture",
                    aliases=[furniture_name],
                    relationships=relationships,
                    temporary_observation=scope == "current",
                )
            )

    object_phrase = rf"((?:[A-Za-z0-9'-]+\s+){{0,3}}(?:{OBJECT_TERMS}))"
    pronoun_placement_pattern = (
        rf"\b(?:i\s+)?(?:left|placed|put|kept)\s+it\s+on\s+"
        rf"(?:the\s+)?{object_phrase}"
    )

    for match in re.finditer(
        pronoun_placement_pattern,
        content,
        flags=re.IGNORECASE,
    ):
        antecedent = last_object_entity(content[: match.start()])

        if antecedent:
            add_object_placement_memory(memories, antecedent, match.group(1))

    direct_placement_pattern = (
        rf"\b(?:i\s+)?(?:left|placed|put|kept)\s+"
        rf"(?:my|the|a|an)?\s*{object_phrase}\s+on\s+"
        rf"(?:the\s+)?{object_phrase}"
    )

    for match in re.finditer(
        direct_placement_pattern,
        content,
        flags=re.IGNORECASE,
    ):
        add_object_placement_memory(memories, match.group(1), match.group(2))

    antecedent_pattern = (
        rf"\bmy\s+([^.!?;]*(?:{OBJECT_TERMS})[^.!?;]*?)"
        rf"\.\s*it has\s+([^.!?;]+)"
    )

    for match in re.finditer(antecedent_pattern, content, flags=re.IGNORECASE):
        antecedent_clause = clean_value(match.group(1))
        contents_clause = clean_value(match.group(2))

        if not antecedent_clause or not contents_clause:
            continue

        antecedent_matches = list(
            re.finditer(
                rf"\b((?:[A-Za-z0-9'-]+\s+){{0,3}}(?:{OBJECT_TERMS}))\b",
                antecedent_clause,
                flags=re.IGNORECASE,
            )
        )

        if not antecedent_matches:
            continue

        antecedent = object_entity_name(antecedent_matches[-1].group(1))

        if not antecedent:
            continue
        location_match = re.match(
            r"(.+?)\s+on\s+it(?:\s+and\s+(.+))?$",
            contents_clause,
            flags=re.IGNORECASE,
        )

        if not location_match:
            continue

        contained_parts = [location_match.group(1)]

        if location_match.group(2):
            contained_parts.extend(
                re.split(
                    r"\s*(?:,|\band\b)\s*",
                    location_match.group(2),
                    flags=re.IGNORECASE,
                )
            )

        for part in contained_parts:
            object_text = clean_value(part)

            if not object_text or not re.search(
                rf"\b(?:{OBJECT_TERMS})\b",
                object_text,
                flags=re.IGNORECASE,
            ):
                continue

            object_name = object_entity_name(object_text)

            if not object_name:
                continue

            memory_text = (
                f"User has {object_text} on the {antecedent}."
                if re.match(r"^(?:a|an)\s+", object_text, flags=re.IGNORECASE)
                else f"User's {object_text} is on the {antecedent}."
            )
            memories.append(
                candidate(
                    "object",
                    memory_text,
                    "mid",
                    55,
                    82,
                    entity_name=object_name,
                    entity_type="object",
                    aliases=[object_name],
                    relationships=object_detail_relationships(object_text) + [
                        {
                            "type": "located_on",
                            "target": antecedent,
                        },
                        {
                            "type": "owned_by",
                            "target": "user",
                        },
                    ],
                )
            )

    memories.extend(extract_all_explicit_object_mentions(content))
    return [memory for memory in memories if memory]


def extract_people(content):
    relationship_terms = (
        r"friend|partner|wife|husband|girlfriend|boyfriend|mother|mum|mom|"
        r"father|dad|brother|sister|son|daughter|manager|boss|colleague|"
        r"coworker|sidekick|fiance|fiancee|aunt|uncle|cousin|niece|nephew|"
        r"grandmother|grandma|grandfather|grandad|grandpa|neighbour|neighbor|"
        r"roommate|housemate|teammate|assistant"
    )
    relationship_patterns = (
        (
            rf"\bmy\s+({relationship_terms})\s+(?:is called|is named|"
            rf"called|named|is)\s+([A-Za-z][A-Za-z'-]{{1,30}})\b"
        ),
        (
            rf"\b([A-Za-z][A-Za-z'-]{{1,30}})\s+is my\s+({relationship_terms})\b"
        ),
        (
            rf"\bi have (?:a|an)\s+({relationship_terms})\s+(?:called|named)\s+"
            rf"([A-Za-z][A-Za-z'-]{{1,30}})\b"
        ),
    )
    memories = []

    for pattern_index, pattern in enumerate(relationship_patterns):
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            if pattern_index in {0, 2}:
                relationship = clean_value(match.group(1), max_chars=30)
                name = normalize_person_name(match.group(2))
            else:
                name = normalize_person_name(match.group(1))
                relationship = clean_value(match.group(2), max_chars=30)

            if not name or not relationship or not is_usable_name(name):
                continue

            memories.append(
                candidate(
                    "person",
                    f"{name} is the user's {relationship}.",
                    "mid",
                    65,
                    88,
                    entity_name=name,
                    entity_type="person",
                    aliases=[name],
                    relationships=[
                        {
                            "type": relationship.casefold(),
                            "target": "user",
                        }
                    ],
                )
            )

    for match in re.finditer(
        rf"\bmy\s+({relationship_terms})\s+([A-Z][A-Za-z'-]{{1,30}})\b",
        content,
        flags=re.IGNORECASE,
    ):
        relationship = clean_value(match.group(1), max_chars=30)
        name = normalize_person_name(match.group(2))

        if (
            not name
            or not relationship
            or name.casefold() in {"called", "is", "named"}
            or not is_usable_name(name)
        ):
            continue

        memories.append(
            candidate(
                "person",
                f"{name} is the user's {relationship}.",
                "mid",
                65,
                85,
                entity_name=name,
                entity_type="person",
                aliases=[name],
                relationships=[
                    {
                        "type": relationship.casefold(),
                        "target": "user",
                    }
                ],
            )
        )

    return [memory for memory in memories if memory]


def extract_profession(content):
    patterns = (
        r"\bi work as (?:an?\s+)?([^.!?;]+)",
        r"\bi am employed as (?:an?\s+)?([^.!?;]+)",
        r"\bi'm employed as (?:an?\s+)?([^.!?;]+)",
        r"\bim employed as (?:an?\s+)?([^.!?;]+)",
        r"\bmy (?:job|profession|occupation) is\s+([^.!?;]+)",
        r"\bmy career is in\s+([^.!?;]+)",
        r"\bmy field is\s+([^.!?;]+)",
        r"\bi work in (?:the\s+)?([^.!?;]+?\s+(?:industry|sector|field))\b",
        r"\bi do\s+([^.!?;]+?)\s+for work\b",
        r"\bi am (?:an?\s+)([A-Za-z][A-Za-z0-9' /-]{2,60})",
        r"\bi'm (?:an?\s+)([A-Za-z][A-Za-z0-9' /-]{2,60})",
        r"\bim (?:an?\s+)([A-Za-z][A-Za-z0-9' /-]{2,60})",
    )
    memories = []

    for pattern in patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            profession = clean_clause(match.group(1))

            if not profession or len(profession.split()) > 8:
                continue

            memories.append(
                candidate(
                    "profession",
                    f"User's profession is {profession}.",
                    "long",
                    82,
                    90,
                    entity_name=profession,
                    entity_type="profession",
                    aliases=[profession, "job", "profession", "occupation"],
                    protected=True,
                )
            )

    return [memory for memory in memories if memory]


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
        "about to",
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
    original_words = re.findall(r"[A-Za-z0-9]+", cleaned)

    has_named_term = any(
        word[:1].isupper() and len(word) >= 4
        for word in original_words
    )
    has_place_hint = "," in cleaned or any(
        marker in lowered
        for marker in (
            "beach",
            "castle",
            "city",
            "forest",
            "garden",
            "london",
            "park",
            "river",
            "road",
            "street",
            "town",
            "woods",
        )
    )

    if len(words) < 3 and len(cleaned) < 18 and not has_named_term and not has_place_hint:
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
        "short_term",
        f"Short-term user context: {cleaned}.",
        "current",
        recent_mention_importance(cleaned),
        65,
    )
    return [memory] if memory else []


def extract_project_mentions(content):
    lowered = content.lower()
    project_names = (
        ("middai", "MiddAI"),
        ("lm studio", "LM Studio"),
        ("local ai", "local AI"),
        ("project 2", "Project 2"),
        ("project two", "Project 2"),
        ("release build", "release build"),
        ("memory system", "memory system"),
        ("chat app", "chat app"),
    )

    memories = []

    project_activity = bool(
        re.search(
            r"\b(?:testing|debugging|fixing|building|developing|coding|"
            r"compiling|releasing|updating|maintaining|working\s+on|"
            r"my\s+project|our\s+project|source\s+code|codebase|installer|"
            r"release\s+build|memory\s+system)\b",
            lowered,
        )
    )
    matched_project = (
        next(
            (name for phrase, name in project_names if phrase in lowered),
            None,
        )
        if project_activity
        else None
    )

    if matched_project:
        memory = candidate(
            "project",
            f"Project context: {content}",
            "mid",
            65,
            70,
            entity_name=matched_project,
            entity_type="project",
            aliases=[matched_project],
        )

        if memory:
            memories.append(memory)

    project_patterns = (
        r"\bmy project (?:is|is called|is named)\s+([^.!?;]+)",
        r"\b(?:the )?project (?:i am|i'm|im) working on is\s+([^.!?;]+)",
        r"\b(?:i am|i'm|im) (?:working on|building|developing|creating)\s+([^.!?;]+)",
        r"\bi(?:'ve| have) started (?:a|an|the)?\s*(?:project\s+)?(?:called|named)\s+([^.!?;]+)",
    )

    for pattern in project_patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            project = clean_clause(match.group(1))

            if not project:
                continue

            memories.append(
                candidate(
                    "project",
                    f"User project: {project}.",
                    "mid",
                    68,
                    78,
                    entity_name=project,
                    entity_type="project",
                    aliases=[project],
                )
            )

    return [memory for memory in memories if memory]


def extract_follow_up_memories(content, previous_user_messages):
    work_reference_patterns = (
        r"\b(?:it(?:'s| is)|that(?:'s| is))\s+what i do (?:at|for)\s+work\b",
        r"\bi do (?:it|that) for work\b",
        r"\b(?:it|that)(?:'s| is) my (?:job|profession|occupation)\b",
    )

    if not any(
        re.search(pattern, content, flags=re.IGNORECASE)
        for pattern in work_reference_patterns
    ):
        return []

    for previous_message in reversed(previous_user_messages or []):
        previous_candidates = extract_memories_from_user_message(previous_message)

        for previous in previous_candidates:
            if previous.get("type") not in {"preference", "object", "project"}:
                continue

            subject = clean_value(previous.get("entity_name"), max_chars=80)

            if not subject:
                continue

            memory = candidate(
                "profession",
                f"User does {subject} professionally.",
                "long",
                82,
                88,
                entity_name=subject,
                entity_type="profession",
                aliases=[subject, "job", "profession", "occupation"],
                protected=True,
            )
            return [memory] if memory else []

    return []


def deduplicate_structured_memories(memories):
    filtered = []
    by_key = {}
    specific_entities = [
        clean_value(memory.get("entity_name"), max_chars=120)
        for memory in memories
        if memory.get("type") != "important_fact"
    ]
    specific_entities = [value.casefold() for value in specific_entities if value]

    for memory in memories:
        item_type = memory.get("type")
        normalized_text = " ".join((memory.get("text") or "").casefold().split())
        entity_name = clean_value(memory.get("entity_name"), max_chars=120)
        key = (item_type, (entity_name or normalized_text).casefold())

        if key in by_key:
            existing = by_key[key]

            for list_key in ("aliases", "relationships"):
                merged = []

                for value in list(existing.get(list_key) or []) + list(
                    memory.get(list_key) or []
                ):
                    if value not in merged:
                        merged.append(value)

                if merged:
                    existing[list_key] = merged

            if len(memory.get("text", "")) > len(existing.get("text", "")):
                existing["text"] = memory["text"]

            existing["importance"] = max(
                int(existing.get("importance", 0)),
                int(memory.get("importance", 0)),
            )
            existing["confidence"] = max(
                int(existing.get("confidence", 0)),
                int(memory.get("confidence", 0)),
            )
            continue

        if item_type == "important_fact":
            fact_text = normalized_text.split(":", 1)[-1].strip(" .")

            if any(
                entity == fact_text
                or entity in fact_text
                or fact_text in entity
                for entity in specific_entities
            ):
                continue

        by_key[key] = memory
        filtered.append(memory)

    return filtered


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
    memories.extend(extract_people(content))
    memories.extend(extract_profession(content))
    memories.extend(extract_objects(content))
    memories.extend(extract_current_context(content))
    memories.extend(extract_project_mentions(content))
    memories = deduplicate_structured_memories(
        [memory for memory in memories if memory]
    )

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
