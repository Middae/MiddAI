from copy import deepcopy
from pathlib import Path
import tomllib


MIDDAI_DIR = Path.home() / "Documents" / "MiddAI"
SETTINGS_FILE = MIDDAI_DIR / "settings.toml"
PHI_WORKDESK_DIR = MIDDAI_DIR / "Phi-4 Workdesk"
PHI_WORKDESK_FILE = PHI_WORKDESK_DIR / "README.txt"
PHI_MEMORY_POLICY_FILE = PHI_WORKDESK_DIR / "memory_policy.txt"
LOG_DIR = MIDDAI_DIR / "logs"
ERROR_LOG_FILE = LOG_DIR / "error_log.txt"


DEFAULT_SETTINGS = {
    "app": {
        "host": "127.0.0.1",
        "port": 5000,
        "debug": False,
    },
    "lm_studio": {
        "base_url": "http://127.0.0.1:1234/v1",
        "api_key": "lm-studio",
        "model": "local-model",
    },
    "memory": {
        "first_messages": 3,
        "last_messages": 15,
        "bridge_lookback_messages": 12,
        "bridge_every_nth": 3,
        "max_message_chars": 700,
        "include_assistant_messages": False,
        "current_memory_visible_minutes": 720,
        "current_memory_expire_hours": 12,
        "mid_memory_expire_days": 7,
        "long_memory_decay_days": 30,
        "long_memory_decay_step": 10,
        "long_memory_delete_confidence": 30,
        "use_ai_memory_judge": True,
        "memory_judge_timeout_seconds": 120,
        "memory_judge_max_existing_items": 20,
        "memory_judge_fallback_to_rules": True,
    },
    "search": {
        "min_keyword_length": 4,
    },
    "depth": {
        "default": "quick",
        "instant": {
            "max_results": 4,
            "max_good_sources": 1,
            "max_text_per_source": 420,
            "max_answer_tokens": 180,
            "style_instruction": "Instant mode: answer in one short paragraph, maximum 90 words. Be direct, avoid lists, and keep assistant personality brief unless the user asks for more detail.",
        },
        "quick": {
            "max_results": 8,
            "max_good_sources": 2,
            "max_text_per_source": 600,
            "max_answer_tokens": 180,
            "style_instruction": "Quick mode: answer in one short paragraph, maximum 90 words. Be direct, avoid lists, and keep assistant personality brief unless the user asks for more detail.",
        },
        "balanced": {
            "max_results": 20,
            "max_good_sources": 3,
            "max_text_per_source": 900,
            "max_answer_tokens": 450,
            "style_instruction": "Balanced mode: answer clearly in up to three short paragraphs. Include useful detail, but keep it easy to scan and avoid padding.",
        },
        "deep": {
            "max_results": 35,
            "max_good_sources": 5,
            "max_text_per_source": 1200,
            "max_answer_tokens": 900,
            "style_instruction": "Answer with clear structure. Use short sections, bullet points, or numbered steps when they make the answer easier to understand.",
        },
    },
    "search_filter": {
        "blocked_domains": [
            "youtube.com",
            "youtu.be",
            "tiktok.com",
            "pinterest.com",
            "quora.com",
        ],
        "blocked_url_parts": [
            "wikipedia.org/wiki/Wikipedia:",
        ],
    },
}


LEGACY_DEPTH_STYLE_UPGRADES = {
    "Answer briefly and directly.": DEFAULT_SETTINGS["depth"]["quick"][
        "style_instruction"
    ],
    "Answer clearly with useful detail.": DEFAULT_SETTINGS["depth"]["balanced"][
        "style_instruction"
    ],
    "Answer thoroughly, include useful nuance, and organize the response clearly.": DEFAULT_SETTINGS[
        "depth"
    ]["deep"]["style_instruction"],
    "Answer in one direct sentence or one very short paragraph. Do not add extra sections, examples, or follow-up questions unless the user asks for them.": DEFAULT_SETTINGS[
        "depth"
    ]["instant"]["style_instruction"],
    "Instant mode: answer in one complete sentence, maximum 35 words. No intro, no examples, no sections, and no follow-up question unless the user asks for one. Any assistant personality must fit inside that one sentence.": DEFAULT_SETTINGS[
        "depth"
    ]["instant"]["style_instruction"],
    "Answer in one small paragraph. Be direct and avoid lists unless the user asks for them.": DEFAULT_SETTINGS[
        "depth"
    ]["quick"]["style_instruction"],
    "Answer clearly in up to three short paragraphs. Include the useful detail, but keep it easy to scan.": DEFAULT_SETTINGS[
        "depth"
    ]["balanced"]["style_instruction"],
}


LEGACY_DEPTH_TOKEN_UPGRADES = {
    "instant": (
        {90, 130},
        DEFAULT_SETTINGS["depth"]["instant"]["max_answer_tokens"],
    ),
}


DEFAULT_SETTINGS_TEXT = """# MiddAI V2 user settings
# This file is created automatically in Documents\\MiddAI if it is missing.
# You can edit it in Notepad.
# Restart MiddAI after changing these settings.
#
# What this file controls:
# - the local MiddAI web app address
# - the LM Studio API connection
# - chat memory window sizes
# - search/source limits
# - answer length/detail presets
# - blocked search domains
#
# What this file does NOT choose:
# - which LM Studio model is loaded
# - whether the active model is a normal chat model or an image-analysis model
# - the model context length, GPU offload, or memory mode selected in the launcher
#
# Those launcher choices are saved separately in active_model.json.
# Leave most settings alone unless you are tuning performance.

[app]
# Address MiddAI listens on.
# 127.0.0.1 means this computer only, which is safest for normal users.
host = "127.0.0.1"

# MiddAI chat runs at http://127.0.0.1:5000 by default.
port = 5000

# Leave false unless you are debugging the Flask app.
debug = false


[lm_studio]
# LM Studio OpenAI-compatible server URL.
base_url = "http://127.0.0.1:1234/v1"

# LM Studio usually accepts any placeholder API key locally.
api_key = "lm-studio"

# Keep this as local-model.
# MiddAI's launcher loads the selected model into LM Studio with this identifier.
# Custom loaded models may override this at runtime through active_model.json.
model = "local-model"


[memory]
# MiddAI V2 memory is split into:
# - current memory: short-lived context and recent searches/image summaries
# - mid-term memory: useful repeated or medium-importance facts
# - long-term memory: names, stable places, explicit saved facts, preferences
# - chat history: saved conversations shown in the sidebar
#
# The AI Judge memory system is used by most models.
# The lightest models may use faster rule-based memory from the launcher.
#
# These values control how much chat text is placed into the model prompt.

# How many messages from the start of the current chat MiddAI can include.
first_messages = 3

# How many recent messages from the current chat MiddAI can include.
last_messages = 15

# How far back to sample bridge memory before the recent messages.
# This helps the model keep light continuity without loading the whole chat.
bridge_lookback_messages = 12

# Pick every Nth bridge message.
bridge_every_nth = 3

# Maximum characters from any one remembered message.
max_message_chars = 700

# false is safer because old assistant replies can cause echoing.
include_assistant_messages = false

# Current memory is eligible for relevant retrieval for this many minutes.
# Examples: a recent web search summary, image-analysis summary, or temporary context.
current_memory_visible_minutes = 720

# Current memory is kept quietly for this many hours before cleanup.
current_memory_expire_hours = 12

# Mid-term memory expires after this many days without being mentioned or retrieved.
mid_memory_expire_days = 7

# Decayable long-term memory loses confidence after this many unseen days.
long_memory_decay_days = 30

# Confidence removed during each long-term decay interval.
long_memory_decay_step = 10

# Decayable long-term memory is deleted at or below this confidence.
long_memory_delete_confidence = 30

# Let the local model judge what is worth remembering.
# Slower, but better for mid/long-term memory than simple keyword rules.
use_ai_memory_judge = true

# Maximum seconds to wait for the memory judge.
# Bigger local models can be slow when deciding what is worth remembering.
memory_judge_timeout_seconds = 120

# How many existing memories to show the judge for duplicate checking.
memory_judge_max_existing_items = 20

# If the AI judge fails or returns bad JSON, use the simple rule extractor.
memory_judge_fallback_to_rules = true


[search]
# Minimum keyword length when choosing relevant webpage paragraphs.
min_keyword_length = 4


[depth]
# Starting response speed/detail in the UI.
# Choices: instant, quick, balanced, deep.
default = "quick"


[depth.instant]
# Fastest mode.
# Chat: one short paragraph.
# Search: minimal source reading.
# Web image thumbnails: off.
max_results = 4
max_good_sources = 1
max_text_per_source = 420
max_answer_tokens = 180
style_instruction = "Instant mode: answer in one short paragraph, maximum 90 words. Be direct, avoid lists, and keep assistant personality brief unless the user asks for more detail."


[depth.quick]
# Short mode.
# Chat: one small paragraph.
# Search: light source reading.
# Web image thumbnails: on when Search mode/image search uses them.
max_results = 8
max_good_sources = 2
max_text_per_source = 600
max_answer_tokens = 180
style_instruction = "Quick mode: answer in one short paragraph, maximum 90 words. Be direct, avoid lists, and keep assistant personality brief unless the user asks for more detail."


[depth.balanced]
# Normal mode.
# Chat: up to three short paragraphs.
# Search: moderate source reading.
# Normal middle option.
max_results = 20
max_good_sources = 3
max_text_per_source = 900
max_answer_tokens = 450
style_instruction = "Balanced mode: answer clearly in up to three short paragraphs. Include useful detail, but keep it easy to scan and avoid padding."


[depth.deep]
# Slower mode.
# Chat: more structured answers.
# Search: deeper source reading.
# Use this when detail matters more than speed.
max_results = 35
max_good_sources = 5
max_text_per_source = 1200
max_answer_tokens = 900
style_instruction = "Answer with clear structure. Use short sections, bullet points, or numbered steps when they make the answer easier to understand."


[search_filter]
# Domains MiddAI should skip before trying to read pages.
# This keeps extraction cleaner and avoids pages that often block text scraping.
blocked_domains = [
  "youtube.com",
  "youtu.be",
  "tiktok.com",
  "pinterest.com",
  "quora.com",
]

# URL fragments MiddAI should skip.
blocked_url_parts = [
  "wikipedia.org/wiki/Wikipedia:",
]


# V2 feature notes
# ================
#
# Chat mode:
# - normal local chat
# - can still trigger web search if the user directly asks MiddAI to search
#
# Search mode:
# - forces web search for the current message
# - can show web image thumbnails for quick/balanced/deep responses
#
# File analysis:
# - handled automatically by the + button in the chat UI
# - supports text/code files, DOCX, and readable PDFs
# - large files are trimmed before being sent to the model
#
# Image analysis:
# - handled automatically by the + button when an image is attached
# - requires choosing an Image Analysis Mode model in the launcher
# - supports JPG, PNG, and WebP uploads
# - image bytes are not saved into memory; MiddAI saves only a compact visual summary
#
# Plant and foraging safety:
# - MiddAI has a hardcoded safety rule for plants, fungi, berries, roots, seeds,
#   wild foods, medicinal use, poisonous plants, and edible/safe-to-touch questions.
# - It should describe visible features and uncertainty, not give a final yes/no
#   survival decision.
"""


DEFAULT_PHI_WORKDESK_TEXT = """Phi-4 Workdesk
================

This folder is created automatically by MiddAI when it is missing.

Phi-4-mini is MiddAI's laptop/light-system model. It is useful, but it is still a small local model, so MiddAI gives it a cleaner desk than the larger models.

Built-in Phi-4-mini settings:
- LM Studio context length: 6000 tokens.
- Memory mode: fast rules-based memory.
- Prompt style: compact.

Files in this folder:
- README.txt explains what the Phi-4 Workdesk is.
- assistant_instructions.txt is the simpler persona/instruction file used when Phi-4-mini is active.
- memory_policy.txt explains what memory Phi sees.

When Phi-4-mini is active, MiddAI gives the model:
- the simpler Phi assistant instructions and personality
- important user facts such as name, useful locations, preferences, objects, and saved facts
- a short recent-chat window
- the current user message
- relevant recent search/context memory only when it appears useful

When Phi-4-mini is active, MiddAI avoids:
- loading lots of older chat history
- loading previous chats unless the user directly asks about them
- handing the model long old assistant replies that can cause echoing
- using the slower AI Judge memory system

Why this exists:
Small models can become confused if the prompt contains too much personality, memory, chat history, and old search context. The Phi-4 Workdesk keeps the prompt smaller so responses should be faster and less likely to repeat old messages.
"""


DEFAULT_PHI_MEMORY_POLICY_TEXT = """Phi-4 Workdesk memory policy
============================

This file explains the compact memory path MiddAI uses when Phi-4-mini is the active model.

Phi receives:
- important user facts from memory, such as name, useful locations, preferences, objects, and saved facts
- up to 8 recent user messages from the current chat
- relevant short-term search/context memory when it matches the current message
- previous chat context only when the user directly asks about previous chats
- the current user message separately as the thing to answer now

Phi does not receive:
- the full mid-term and long-term memory lists
- lots of older chat messages
- old assistant replies by default
- AI Judge memory extraction

Why:
Phi-4-mini can support a large context window, but laptop performance and small-model behaviour are usually better with a smaller, cleaner prompt. This helps reduce slow replies, repeated greetings, and accidental echoes of older assistant messages.
"""


def write_missing_text_file(path, text):
    if not path.exists():
        path.write_text(text, encoding="utf-8")


def ensure_phi_workdesk_file():
    PHI_WORKDESK_DIR.mkdir(parents=True, exist_ok=True)
    write_missing_text_file(PHI_WORKDESK_FILE, DEFAULT_PHI_WORKDESK_TEXT)
    write_missing_text_file(PHI_MEMORY_POLICY_FILE, DEFAULT_PHI_MEMORY_POLICY_TEXT)


def ensure_settings_file():
    MIDDAI_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ensure_phi_workdesk_file()

    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(DEFAULT_SETTINGS_TEXT, encoding="utf-8")


def deep_merge(defaults, overrides):
    merged = deepcopy(defaults)

    for key, value in overrides.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def upgrade_legacy_memory_settings(user_settings):
    memory_settings = user_settings.get("memory")

    if not isinstance(memory_settings, dict):
        return

    has_new_current_memory_settings = (
        "current_memory_visible_minutes" in memory_settings
        or "current_memory_expire_hours" in memory_settings
    )
    uses_old_generated_chat_window = (
        memory_settings.get("first_messages") == 4
        and memory_settings.get("last_messages") == 8
    )

    if uses_old_generated_chat_window and not has_new_current_memory_settings:
        memory_settings["first_messages"] = 3
        memory_settings["last_messages"] = 15

    if memory_settings.get("current_memory_visible_minutes") == 24:
        memory_settings["current_memory_visible_minutes"] = 720

    if memory_settings.get("current_memory_expire_hours") == 4:
        memory_settings["current_memory_expire_hours"] = 12


def upgrade_legacy_depth_settings(user_settings):
    depth_settings = user_settings.get("depth")

    if not isinstance(depth_settings, dict):
        return

    for preset_name, preset_settings in depth_settings.items():
        if not isinstance(preset_settings, dict):
            continue

        style_instruction = preset_settings.get("style_instruction")

        if style_instruction in LEGACY_DEPTH_STYLE_UPGRADES:
            preset_settings["style_instruction"] = LEGACY_DEPTH_STYLE_UPGRADES[
                style_instruction
            ]

        token_upgrade = LEGACY_DEPTH_TOKEN_UPGRADES.get(str(preset_name).lower())

        if token_upgrade and preset_settings.get("max_answer_tokens") in token_upgrade[0]:
            preset_settings["max_answer_tokens"] = token_upgrade[1]


def load_user_settings():
    ensure_settings_file()

    try:
        with SETTINGS_FILE.open("rb") as file:
            user_settings = tomllib.load(file)
    except (tomllib.TOMLDecodeError, OSError):
        user_settings = {}

    upgrade_legacy_memory_settings(user_settings)
    upgrade_legacy_depth_settings(user_settings)
    return deep_merge(DEFAULT_SETTINGS, user_settings)


SETTINGS = load_user_settings()

MIN_KEYWORD_LENGTH = SETTINGS["search"]["min_keyword_length"]

MEMORY_FIRST_MESSAGES = SETTINGS["memory"]["first_messages"]
MEMORY_LAST_MESSAGES = SETTINGS["memory"]["last_messages"]
MEMORY_BRIDGE_LOOKBACK_MESSAGES = SETTINGS["memory"]["bridge_lookback_messages"]
MEMORY_BRIDGE_EVERY_NTH = SETTINGS["memory"]["bridge_every_nth"]
MEMORY_MAX_MESSAGE_CHARS = SETTINGS["memory"]["max_message_chars"]
MEMORY_INCLUDE_ASSISTANT_MESSAGES = SETTINGS["memory"]["include_assistant_messages"]
MEMORY_CURRENT_VISIBLE_MINUTES = SETTINGS["memory"].get(
    "current_memory_visible_minutes", 24
)
MEMORY_CURRENT_EXPIRE_HOURS = SETTINGS["memory"].get("current_memory_expire_hours", 12)
MEMORY_MID_EXPIRE_DAYS = SETTINGS["memory"].get("mid_memory_expire_days", 7)
MEMORY_LONG_DECAY_DAYS = SETTINGS["memory"].get("long_memory_decay_days", 30)
MEMORY_LONG_DECAY_STEP = SETTINGS["memory"].get("long_memory_decay_step", 10)
MEMORY_LONG_DELETE_CONFIDENCE = SETTINGS["memory"].get(
    "long_memory_delete_confidence",
    30,
)
MEMORY_USE_AI_MEMORY_JUDGE = SETTINGS["memory"].get("use_ai_memory_judge", True)
MEMORY_JUDGE_TIMEOUT_SECONDS = SETTINGS["memory"].get(
    "memory_judge_timeout_seconds", 120
)
MEMORY_JUDGE_MAX_EXISTING_ITEMS = SETTINGS["memory"].get(
    "memory_judge_max_existing_items", 20
)
MEMORY_JUDGE_FALLBACK_TO_RULES = SETTINGS["memory"].get(
    "memory_judge_fallback_to_rules", True
)

DEPTH_PRESETS = {
    "instant": SETTINGS["depth"]["instant"],
    "quick": SETTINGS["depth"]["quick"],
    "balanced": SETTINGS["depth"]["balanced"],
    "deep": SETTINGS["depth"]["deep"],
}

RAW_DEFAULT_DEPTH = str(SETTINGS["depth"]["default"]).lower()
DEFAULT_DEPTH = RAW_DEFAULT_DEPTH if RAW_DEFAULT_DEPTH in DEPTH_PRESETS else "quick"

BLOCKED_DOMAINS = SETTINGS["search_filter"]["blocked_domains"]
BLOCKED_URL_PARTS = SETTINGS["search_filter"]["blocked_url_parts"]

LM_STUDIO_BASE_URL = SETTINGS["lm_studio"]["base_url"]
LM_STUDIO_API_KEY = SETTINGS["lm_studio"]["api_key"]
LM_STUDIO_MODEL = SETTINGS["lm_studio"]["model"]

APP_HOST = SETTINGS["app"]["host"]
APP_PORT = SETTINGS["app"]["port"]
APP_DEBUG = SETTINGS["app"]["debug"]


def get_depth_settings(depth):
    normalized_depth = (depth or DEFAULT_DEPTH).lower()
    return DEPTH_PRESETS.get(normalized_depth, DEPTH_PRESETS[DEFAULT_DEPTH])
