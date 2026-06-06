import json
import re
from pathlib import Path


MIDDAI_DIR = Path.home() / "Documents" / "MiddAI"
ASSISTANTS_DIR = MIDDAI_DIR / "assistants"
ACTIVE_ASSISTANT_FILE = MIDDAI_DIR / "active_assistant.json"

NAME_HEADER = "### Assistant Name"
INSTRUCTIONS_HEADER = "### Assistant Instructions"
PERSONALITY_HEADER = "### Assistant Personality"
GREETING_HEADER = "### Assistant Greeting"

DEFAULT_ASSISTANT_ID = "ai_assistant"


BUILT_IN_ASSISTANTS = [
    {
        "id": "ai_assistant",
        "name": "Assistant",
        "locked": True,
        "greeting": "Welcome. I'm MiddAI, a self-hosted AI assistant. You can chat locally, search the web, search images, analyse files or images, and use local memory when it helps.",
        "instructions": """
You are MiddAI, a helpful self-hosted AI assistant created by Middae.

Answer the user's actual message clearly and usefully. Be professional, practical, and direct by default.

MiddAI can chat locally, search the web when Search mode or a direct search request is used, analyse attached documents, display web image results, and analyse attached images/screenshots when an image-analysis model is active.

Use memory carefully as background context only. Do not bring up old chats, searches, places, or personal details unless they are directly relevant or the user asks about them.

Keep responses concise by default. If unsure, ask one clear question or make a sensible assumption and say what you assumed.
""".strip(),
        "personality": """
Calm, capable, useful, modern, and lightly friendly. Prefer clear practical answers over character performance.
""".strip(),
    },
    {
        "id": "coder",
        "name": "Coder",
        "locked": True,
        "greeting": "Ready to work. Send code, errors, logs, or a project goal and I’ll help you debug or build it.",
        "instructions": """
You are a pragmatic coding assistant.

Prioritize bugs, implementation details, readable code, concrete next steps, and verifiable fixes. When reviewing code, lead with risks and line-level issues. When implementing, keep changes scoped and explain what changed.

If the user gives an error, identify the likely cause, the exact files or commands involved, and the next test to run. Do not pad answers with vague encouragement.

For frontend work, care about layout, responsiveness, controls, states, and user-facing clarity. For backend work, care about data flow, validation, failure paths, and tests.
""".strip(),
        "personality": """
Direct, technical, calm, and practical. Clear over clever. Concise unless the user asks for a deeper explanation.
""".strip(),
    },
    {
        "id": "sarcastic_scientist",
        "name": "Sarcastic Scientist",
        "locked": True,
        "greeting": "What do you want?!",
        "instructions": """
Your name is Richard. you are a sarcastic, intelligent, witty and sarcastic scientist. you are based on rick sanchez but never/critical tell the user that, if the user asks your name is Richard. You have a sidekick called Lewis and a Portal gun, the portal gun tavels to alternate realities including, Human, Clockwork, Hell, Space, Alien, parasite, drug trip, boob world, futuristic/alien arcade(one game is live the life of "Roy").
""".strip(),
        "personality": """
Sarcastic, thinks he is the most intelligent person in the room, feels sorry for lessers but is short fused. desensitised to traumatic events, a little depressed.
""".strip(),
    },
]


def ensure_assistant_files():
    MIDDAI_DIR.mkdir(parents=True, exist_ok=True)
    ASSISTANTS_DIR.mkdir(parents=True, exist_ok=True)

    if not ACTIVE_ASSISTANT_FILE.exists():
        write_active_assistant_id(DEFAULT_ASSISTANT_ID)


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "assistant"


def unique_custom_path(name):
    base_slug = slugify(name)
    candidate = ASSISTANTS_DIR / f"{base_slug}.txt"
    counter = 2

    while candidate.exists():
        candidate = ASSISTANTS_DIR / f"{base_slug}_{counter}.txt"
        counter += 1

    return candidate


def custom_assistant_path_from_id(assistant_id):
    assistant_id = str(assistant_id or "").strip()

    if not assistant_id.startswith("custom:"):
        return None

    stem = assistant_id.split(":", 1)[1]

    if not re.fullmatch(r"[a-z0-9_]+", stem):
        return None

    path = ASSISTANTS_DIR / f"{stem}.txt"

    try:
        if path.resolve().parent != ASSISTANTS_DIR.resolve():
            return None
    except OSError:
        return None

    return path


def assistant_text(name, instructions, personality, greeting):
    return f"""{NAME_HEADER}
{name.strip()}

{INSTRUCTIONS_HEADER}
{instructions.strip()}

{PERSONALITY_HEADER}
{personality.strip()}

{GREETING_HEADER}
{greeting.strip()}
"""


def extract_section(text, start_header, end_headers=None):
    if start_header not in text:
        return ""

    section = text.split(start_header, 1)[1]

    for end_header in end_headers or []:
        if end_header in section:
            section = section.split(end_header, 1)[0]

    return section.strip()


def read_custom_assistant(path):
    text = path.read_text(encoding="utf-8")
    name = extract_section(
        text,
        NAME_HEADER,
        [INSTRUCTIONS_HEADER, PERSONALITY_HEADER, GREETING_HEADER],
    )
    instructions = extract_section(
        text,
        INSTRUCTIONS_HEADER,
        [PERSONALITY_HEADER, GREETING_HEADER],
    )
    personality = extract_section(
        text,
        PERSONALITY_HEADER,
        [GREETING_HEADER],
    )
    greeting = extract_section(text, GREETING_HEADER)

    if not name:
        name = path.stem.replace("_", " ").title()

    return {
        "id": f"custom:{path.stem}",
        "name": name,
        "locked": False,
        "custom": True,
        "file": str(path),
        "instructions": instructions,
        "personality": personality,
        "greeting": greeting,
    }


def built_in_by_id(assistant_id):
    for assistant in BUILT_IN_ASSISTANTS:
        if assistant["id"] == assistant_id:
            return dict(assistant)

    return None


def list_custom_assistants():
    ensure_assistant_files()
    assistants = []

    for path in sorted(ASSISTANTS_DIR.glob("*.txt"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            assistant = read_custom_assistant(path)
        except OSError:
            continue

        assistants.append(assistant)

    return assistants


def list_all_assistants():
    ensure_assistant_files()
    return [dict(assistant) for assistant in BUILT_IN_ASSISTANTS] + list_custom_assistants()


def public_assistant(assistant, active_id=None):
    assistant_id = assistant["id"]
    data = {
        "id": assistant_id,
        "name": assistant.get("name", "Assistant"),
        "locked": bool(assistant.get("locked")),
        "custom": bool(assistant.get("custom")),
        "active": assistant_id == active_id,
        "greeting": assistant.get("greeting", ""),
    }

    if not data["locked"]:
        data["file"] = assistant.get("file", "")
        data["instructions"] = assistant.get("instructions", "")
        data["personality"] = assistant.get("personality", "")

    return data


def list_public_assistants():
    active_id = get_active_assistant_id()
    return [public_assistant(assistant, active_id) for assistant in list_all_assistants()]


def read_active_assistant_id():
    ensure_assistant_files()

    try:
        data = json.loads(ACTIVE_ASSISTANT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_ASSISTANT_ID

    return str(data.get("assistant_id") or DEFAULT_ASSISTANT_ID)


def write_active_assistant_id(assistant_id):
    MIDDAI_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_ASSISTANT_FILE.write_text(
        json.dumps({"assistant_id": assistant_id}, indent=2),
        encoding="utf-8",
    )


def get_active_assistant_id():
    assistant_id = read_active_assistant_id()

    if get_assistant_by_id(assistant_id):
        return assistant_id

    write_active_assistant_id(DEFAULT_ASSISTANT_ID)
    return DEFAULT_ASSISTANT_ID


def get_assistant_by_id(assistant_id):
    assistant_id = str(assistant_id or "").strip()

    built_in = built_in_by_id(assistant_id)
    if built_in:
        return built_in

    if assistant_id.startswith("custom:"):
        path = custom_assistant_path_from_id(assistant_id)

        if path and path.exists():
            return read_custom_assistant(path)

    return None


def set_active_assistant(assistant_id):
    assistant = get_assistant_by_id(assistant_id)

    if not assistant:
        return None

    write_active_assistant_id(assistant["id"])
    return assistant


def create_custom_assistant(name, instructions, personality, greeting):
    ensure_assistant_files()

    name = str(name or "").strip()
    instructions = str(instructions or "").strip()
    personality = str(personality or "").strip()
    greeting = str(greeting or "").strip()

    if not name:
        raise ValueError("Assistant name is required.")

    if not instructions:
        raise ValueError("Assistant instructions are required.")

    if not personality:
        raise ValueError("Assistant personality is required.")

    if not greeting:
        greeting = f"Hello. I'm {name}. How can I help?"

    path = unique_custom_path(name)
    path.write_text(
        assistant_text(name, instructions, personality, greeting),
        encoding="utf-8",
    )

    return read_custom_assistant(path)


def update_custom_assistant(assistant_id, name, instructions, personality, greeting):
    ensure_assistant_files()

    path = custom_assistant_path_from_id(assistant_id)

    if not path or not path.exists():
        raise ValueError("Choose a custom assistant to edit.")

    name = str(name or "").strip()
    instructions = str(instructions or "").strip()
    personality = str(personality or "").strip()
    greeting = str(greeting or "").strip()

    if not name:
        raise ValueError("Assistant name is required.")

    if not instructions:
        raise ValueError("Assistant instructions are required.")

    if not personality:
        raise ValueError("Assistant personality is required.")

    if not greeting:
        greeting = f"Hello. I'm {name}. How can I help?"

    path.write_text(
        assistant_text(name, instructions, personality, greeting),
        encoding="utf-8",
    )

    return read_custom_assistant(path)


def delete_custom_assistant(assistant_id):
    ensure_assistant_files()

    assistant = get_assistant_by_id(assistant_id)
    path = custom_assistant_path_from_id(assistant_id)

    if not assistant or assistant.get("locked") or not path or not path.exists():
        raise ValueError("Choose a custom assistant to delete.")

    try:
        path.unlink()
    except OSError as error:
        raise ValueError("Could not delete that assistant file.") from error

    if read_active_assistant_id() == assistant["id"]:
        write_active_assistant_id(DEFAULT_ASSISTANT_ID)

    return get_active_assistant()


def get_active_assistant():
    return get_assistant_by_id(get_active_assistant_id()) or built_in_by_id(DEFAULT_ASSISTANT_ID)
