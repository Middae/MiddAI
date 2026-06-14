from flask import Flask, Response, jsonify, render_template_string, request, stream_with_context
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

from config import (
    APP_DEBUG,
    APP_HOST,
    APP_PORT,
    DEFAULT_DEPTH,
    DEPTH_PRESETS,
    ERROR_LOG_FILE,
)
from assistants import (
    create_custom_assistant,
    delete_custom_assistant,
    get_active_assistant,
    get_active_assistant_id,
    get_assistant_by_id,
    list_public_assistants,
    public_assistant,
    set_active_assistant,
    update_custom_assistant,
)
from document_tools import (
    AttachmentError,
    prepare_uploaded_files,
    public_file_metadata,
)
from llm_client import (
    ask_model,
    ask_model_locally,
    ask_model_with_images,
    stream_model,
    stream_model_locally,
    stream_model_with_images,
)
from memory_system import (
    add_message,
    add_search_context,
    add_visual_context,
    add_user_defined_memory,
    archive_current_chat,
    delete_chat_history,
    delete_assistant_data,
    delete_all_memory,
    delete_memory_item as delete_stored_memory_item,
    delete_saved_chat,
    ensure_memory_file,
    get_current_chat_messages,
    get_selected_memory,
    list_readable_memories,
    list_saved_chats,
    open_saved_chat,
    process_pending_memory_judgements,
    start_new_current_chat,
)
from persona import ensure_persona_file, get_assistant_greeting
from runtime_state import (
    AI_JUDGE_MODEL_ID,
    GPU_OFFLOAD_OFF,
    MEMORY_MODE_AI_JUDGE,
    MEMORY_MODE_OFF,
    MEMORY_MODE_RULES,
    get_runtime_ai_judge_enabled,
    get_runtime_ai_judge_separate_model,
    get_runtime_gpu_offload,
    get_runtime_gpu_offload_percent,
    infer_min_context_length,
    infer_max_context_length,
    get_runtime_memory_mode,
    get_runtime_prompt_profile,
    get_runtime_supports_image_analysis,
    get_runtime_temperature,
    normalize_gpu_offload,
    normalize_gpu_offload_percent,
    read_active_model,
    set_runtime_temperature,
    write_active_model,
)
from search_tools import extract_evidence, search_images, search_web
from web_page import PAGE_HTML


MEMORY_WORKER_STATE_LOCK = threading.Lock()
RUNNING_MEMORY_WORKERS = set()
RERUN_MEMORY_WORKERS = set()
AI_JUDGE_MODEL_KEY = "qwen/qwen3-4b-2507"
AI_JUDGE_MODEL_CONTEXT_LENGTH = 4000


def resource_path(relative_path):
    relative_path = Path(relative_path)

    if hasattr(sys, "_MEIPASS"):
        exe_dir = Path(sys.executable).resolve().parent
        asset_dirs = (
            exe_dir / "Assets",
            exe_dir / "App" / "Assets",
            Path(sys._MEIPASS) / "assets",
        )

        if relative_path.parts and relative_path.parts[0].lower() == "assets":
            for asset_dir in asset_dirs:
                packaged_asset = asset_dir.joinpath(*relative_path.parts[1:])

                if packaged_asset.exists():
                    return str(packaged_asset)

            for asset_dir in asset_dirs:
                if asset_dir.exists():
                    return str(asset_dir)

            return str(exe_dir / "Assets")

        return str(Path(sys._MEIPASS) / relative_path)

    return str(Path(__file__).resolve().parent / relative_path)


app = Flask(
    __name__,
    static_folder=resource_path("assets"),
    static_url_path="/assets",
)


def bootstrap_user_files():
    ensure_memory_file()
    ensure_persona_file()


bootstrap_user_files()


# These are phrase-shaped on purpose. Avoid matching lone words such as
# "search" inside "binary search" or "image" inside casual chat.
EXPLICIT_SEARCH_PATTERNS = (
    r"^\s*(?:please\s+)?(?:search|google)\s+(?:for\s+)?\S",
    r"^\s*(?:please\s+)?(?:look\s+up)\s+\S",
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:search|look\s+up|google)\b",
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?look\s+(?:it|that|this|them|those|these)\s+up\b",
    r"^\s*(?:please\s+)?look\s+(?:it|that|this|them|those|these)\s+up\b",
    r"\b(?:search|look\s+up|google|check)\s+(?:for|up|online|the\s+web|the\s+internet|on\s+the\s+web|on\s+the\s+internet)\b",
    r"\blook\s+(?:it|that|this|them|those|these)\s+up\s+(?:online|on\s+the\s+web|on\s+the\s+internet)\b",
    r"\b(?:check|verify|fact[-\s]?check)\s+(?:it|that|this|them|those|these|.+?)\s+(?:online|on\s+the\s+web|on\s+the\s+internet)\b",
    r"\b(?:use|do|run)\s+(?:a\s+)?(?:web|internet|online)\s+search\b",
    r"\b(?:use|go\s+on|go\s+online\s+and\s+use)\s+(?:the\s+)?(?:web|internet)\s+to\s+(?:search|find|look\s+up|check)\b",
    r"\b(?:go\s+online|use\s+online\s+sources)\s+(?:and\s+)?(?:search|find|look\s+up|check)\b",
    r"\b(?:find|look\s+for)\s+(?:information|info|details|sources)\s+(?:on|about|for)\s+.+?\s+(?:online|on\s+the\s+web|on\s+the\s+internet)\b",
    r"^\s*(?:what\s+does|what\s+do)\s+(?:the\s+)?(?:internet|web|online\s+sources)\s+say\s+about\b",
    r"^\s*(?:according\s+to|using)\s+(?:the\s+)?(?:internet|web|online\s+sources)\b",
    r"^\s*(?:please\s+)?(?:find|show|get)\s+(?:me\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\b",
    r"^\s*(?:please\s+)?(?:search|look\s+up)\s+(?:for\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\b",
    r"^\s*(?:please\s+)?(?:image|picture|photo)\s+search\s+(?:for|of)\b",
    r"^\s*(?:please\s+)?(?:do|run)\s+(?:an?\s+)?image\s+search\s+(?:for|of)\b",
    r"^\s*(?:please\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\b",
    r"^\s*(?:please\s+)?(?:what\s+does|what\s+do)\s+.+?\s+looks?\s+like\b",
    r"^\s*(?:please\s+)?show\s+(?:me\s+)?what\s+.+?\s+looks?\s+like\b",
    r"^\s*(?:please\s+)?(?:can|could|may)\s+i\s+see\s+(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\b",
    r"^\s*(?:please\s+)?visual\s+examples?\s+(?:of|for)\b",
)
CONTEXTUAL_SEARCH_PATTERN = re.compile(
    r"\b(?:it|that|this|them|those|these)\b.*\b(?:search|online|internet|web)\b"
    r"|\blook\s+(?:it|that|this|them|those|these)\s+up\b"
)
SEARCH_QUERY_EXTRACTORS = (
    r"^\s*(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?(?:search|look\s+up)\s+(?:for\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:find|show|get)\s+(?:me\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:search|google|look\s+up)\s+(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:search|google)\s+(?:online\s+|the\s+web\s+|the\s+internet\s+)?(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?look\s+up\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?look\s+online\s+for\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:check|verify|fact[-\s]?check)\s+(?P<query>.+?)\s+(?:online|on\s+the\s+web|on\s+the\s+internet)$",
    r"^\s*(?:please\s+)?(?:use|do|run)\s+(?:an?\s+)?(?:web|internet|online)\s+search\s+(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:use|go\s+on|go\s+online\s+and\s+use)\s+(?:the\s+)?(?:web|internet)\s+to\s+(?:search|find|look\s+up|check)\s+(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:go\s+online|use\s+online\s+sources)\s+(?:and\s+)?(?:search|find|look\s+up|check)\s+(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:find|look\s+for)\s+(?:information|info|details|sources)\s+(?:on|about|for)\s+(?P<query>.+?)\s+(?:online|on\s+the\s+web|on\s+the\s+internet)$",
    r"^\s*(?:what\s+does|what\s+do)\s+(?:the\s+)?(?:internet|web|online\s+sources)\s+say\s+about\s+(?P<query>.+)$",
    r"^\s*(?:according\s+to|using)\s+(?:the\s+)?(?:internet|web|online\s+sources),?\s*(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:search|look\s+up)\s+(?:for\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:image|picture|photo)\s+search\s+(?:for|of)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:do|run)\s+(?:an?\s+)?image\s+search\s+(?:for|of)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:what\s+does|what\s+do)\s+(?P<query>.+?)\s+looks?\s+like\??$",
    r"^\s*(?:please\s+)?show\s+(?:me\s+)?what\s+(?P<query>.+?)\s+looks?\s+like\??$",
    r"^\s*(?:please\s+)?(?:can|could|may)\s+i\s+see\s+(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?visual\s+examples?\s+(?:of|for)\s+(?P<query>.+)$",
)


def is_explicit_search_request(question):
    normalized_question = question.lower()
    return any(
        re.search(pattern, normalized_question)
        for pattern in EXPLICIT_SEARCH_PATTERNS
    )


def compact_search_context(text):
    compacted = re.sub(r"\s+", " ", text or "").strip()
    compacted = re.sub(r"^[\"'“”‘’]+|[\"'“”‘’]+$", "", compacted)

    if len(compacted) <= 160:
        return compacted

    sentence = re.split(r"(?<=[.!?])\s+", compacted, maxsplit=1)[0].strip()

    if 12 <= len(sentence) <= 160:
        return sentence

    return compacted[:160].rsplit(" ", 1)[0].strip()


def get_recent_search_context(messages):
    for message in reversed(messages or []):
        role = message.get("role")
        content = compact_search_context(message.get("content"))

        if role == "user" and content and not is_explicit_search_request(content):
            return content

    for message in reversed(messages or []):
        role = message.get("role")
        content = compact_search_context(message.get("content"))

        if role == "assistant" and content:
            return content

    return ""


def clean_direct_search_query(question):
    query = question.strip()

    for pattern in SEARCH_QUERY_EXTRACTORS:
        match = re.search(pattern, question, flags=re.IGNORECASE)

        if match:
            query = match.group("query")
            break

    query = re.sub(r"\s+(?:for\s+me|please)\s*[?.!]*$", "", query, flags=re.IGNORECASE)
    query = re.sub(
        r"^\s*(?:tell\s+me\s+(?:about\s+)?|show\s+me\s+|explain\s+|what\s+is\s+|who\s+is\s+|where\s+is\s+)",
        "",
        query,
        flags=re.IGNORECASE,
    )
    query = query.strip(" \t\r\n?.!")

    return query or question


def build_search_query(question, recent_messages=None):
    if CONTEXTUAL_SEARCH_PATTERN.search(question.lower()):
        context = get_recent_search_context(
            get_current_chat_messages() if recent_messages is None else recent_messages
        )

        if context:
            return context

    return clean_direct_search_query(question)


SEARCH_INTENT_NONE = "none"
SEARCH_INTENT_WEB = "web"
SEARCH_INTENT_IMAGE = "image"
RECENT_TOPIC_MESSAGE_LIMIT = 3
REFERENCE_WORDS = {"he", "her", "him", "it", "she", "that", "them", "these", "they", "this", "those"}
QUERY_FILLER_WORDS = {
    "about",
    "again",
    "for",
    "internet",
    "me",
    "online",
    "please",
    "search",
    "the",
    "up",
    "web",
}
VAGUE_TOPIC_MESSAGES = {
    "carry on",
    "continue",
    "go on",
    "keep going",
    "more",
    "search",
    "search it",
    "search that",
    "search this",
    "search them",
    "tell me more",
}
MATH_TOPIC_PATTERN = re.compile(r"^[\d\s+\-*/().=xX]+$")


@dataclass(frozen=True)
class SearchRoute:
    intent: str = SEARCH_INTENT_NONE
    query: str = ""
    needs_context: bool = False
    needs_clarification: bool = False


IMAGE_NOUN_PATTERN = r"(?:image|images|picture|pictures|photo(?:s|['’]s)?|pic|pics)"

DIRECT_IMAGE_QUERY_PATTERNS = (
    rf"^\s*(?:please\s+)?(?:search|look\s+up|find|show|get)\s+(?:for\s+)?(?:similar|related)\s+{IMAGE_NOUN_PATTERN}\s+(?:of|for|to)\s+(?P<query>.+)$",
    rf"^\s*(?:please\s+)?i\s+(?:would\s+like|want|need|wanted|was\s+looking\s+for|am\s+looking\s+for)\s+(?:to\s+see\s+|to\s+find\s+|to\s+search\s+for\s+|to\s+look\s+up\s+)?(?:an?\s+|some\s+|the\s+)?{IMAGE_NOUN_PATTERN}\s+(?:of|for)\s+(?P<query>.+)$",
    rf"^\s*(?:please\s+)?i\s+(?:wanted|want|would\s+like|meant|asked)\s+(?:you\s+)?(?:to\s+)?(?:search|look\s+up|find|show|get)\s+(?:for\s+)?(?:an?\s+|some\s+|the\s+)?{IMAGE_NOUN_PATTERN}\s+(?:of|for)\s+(?P<query>.+)$",
    rf"^\s*(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?(?:search|look\s+up|look\s+for|find)\s+(?:for\s+)?(?:an?\s+|some\s+)?{IMAGE_NOUN_PATTERN}\s+(?:of|for)\s+(?P<query>.+)$",
    rf"^\s*(?:please\s+)?(?:find|show|get)\s+(?:me\s+)?(?:an?\s+|some\s+|the\s+)?{IMAGE_NOUN_PATTERN}\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:image|picture|photo)\s+search\s+(?:for|of)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:do|run)\s+(?:an?\s+)?image\s+search\s+(?:for|of)\s+(?P<query>.+)$",
    rf"^\s*(?:please\s+)?(?:an?\s+|some\s+|the\s+)?{IMAGE_NOUN_PATTERN}\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:what\s+does|what\s+do)\s+(?P<query>.+?)\s+looks?\s+like\??$",
    r"^\s*(?:please\s+)?show\s+(?:me\s+)?what\s+(?P<query>.+?)\s+looks?\s+like\??$",
    rf"^\s*(?:please\s+)?(?:can|could|may)\s+i\s+see\s+(?:an?\s+|some\s+|the\s+)?{IMAGE_NOUN_PATTERN}\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?visual\s+examples?\s+(?:of|for)\s+(?P<query>.+)$",
)
CONTEXTUAL_IMAGE_PATTERNS = (
    rf"^\s*(?:please\s+)?(?:search|look\s+up|find|show|get)\s+(?:for\s+)?(?:similar|related)\s+{IMAGE_NOUN_PATTERN}\s*$",
    rf"^\s*(?:please\s+)?i\s+(?:wanted|want|would\s+like|meant|asked)\s+(?:you\s+)?(?:to\s+)?(?:search|look\s+up|find|show|get)\s+(?:for\s+)?(?:an?\s+|some\s+|the\s+)?{IMAGE_NOUN_PATTERN}\s*$",
    rf"^\s*(?:please\s+)?(?:find|show|get)\s+(?:me\s+)?(?:an?\s+|some\s+|the\s+)?{IMAGE_NOUN_PATTERN}\s*$",
    rf"^\s*(?:please\s+)?(?:search|look\s+up|look\s+for)\s+(?:for\s+)?{IMAGE_NOUN_PATTERN}\s*$",
    r"^\s*(?:please\s+)?(?:image|picture|photo)\s+search\s*$",
    r"^\s*(?:please\s+)?(?:do|run)\s+(?:an?\s+)?image\s+search\s*$",
    r"^\s*(?:please\s+)?(?:what\s+does|what\s+do)\s+(?:it|that|this|them|those|these)\s+looks?\s+like\??$",
    r"^\s*(?:please\s+)?show\s+(?:me\s+)?what\s+(?:it|that|this|them|those|these)\s+looks?\s+like\??$",
    rf"^\s*(?:please\s+)?(?:can|could|may)\s+i\s+see\s+(?:an?\s+|some\s+)?{IMAGE_NOUN_PATTERN}\s*$",
    r"^\s*(?:please\s+)?visual\s+examples?\s*$",
)
DIRECT_WEB_QUERY_PATTERNS = (
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:search|google|look\s+up)\s+(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:search|google)\s+(?:online\s+|the\s+web\s+|the\s+internet\s+)?(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?look\s+up\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?look\s+online\s+for\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:check|verify|fact[-\s]?check)\s+(?P<query>.+?)\s+(?:online|on\s+the\s+web|on\s+the\s+internet)$",
    r"^\s*(?:please\s+)?(?:use|do|run)\s+(?:an?\s+)?(?:web|internet|online)\s+search\s+(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:use|go\s+on|go\s+online\s+and\s+use)\s+(?:the\s+)?(?:web|internet)\s+to\s+(?:search|find|look\s+up|check)\s+(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:go\s+online|use\s+online\s+sources)\s+(?:and\s+)?(?:search|find|look\s+up|check)\s+(?:for\s+)?(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:find|look\s+for)\s+(?:information|info|details|sources)\s+(?:on|about|for)\s+(?P<query>.+?)\s+(?:online|on\s+the\s+web|on\s+the\s+internet)$",
    r"^\s*(?:what\s+does|what\s+do)\s+(?:the\s+)?(?:internet|web|online\s+sources)\s+say\s+about\s+(?P<query>.+)$",
    r"^\s*(?:according\s+to|using)\s+(?:the\s+)?(?:internet|web|online\s+sources),?\s*(?P<query>.+)$",
)
CONTEXTUAL_WEB_PATTERNS = (
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:search|google)\s+(?:for\s+)?(?:it|that|this|them|those|these)\b",
    r"^\s*(?:please\s+)?(?:search|google)\s+(?:for\s+)?(?:it|that|this|them|those|these)\b",
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?look\s+(?:it|that|this|them|those|these)\s+up\b",
    r"^\s*(?:please\s+)?look\s+(?:it|that|this|them|those|these)\s+up\b",
    r"^\s*(?:please\s+)?(?:check|verify|fact[-\s]?check)\s+(?:it|that|this|them|those|these)\s+(?:online|on\s+the\s+web|on\s+the\s+internet)\b",
    r"^\s*(?:please\s+)?(?:search|google|look\s+up|check|verify)\s+(?:online|the\s+web|the\s+internet)\s*$",
    r"^\s*(?:please\s+)?(?:use|do|run)\s+(?:an?\s+)?(?:web|internet|online)\s+search\s*$",
)
TOPIC_PREFIX_PATTERNS = (
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:tell\s+me\s+about|explain|describe|define)\s+",
    r"^\s*(?:please\s+)?(?:tell\s+me\s+about|explain|describe|define)\s+",
    r"^\s*(?:please\s+)?(?:what\s+is|what\s+are|what\s+was|what\s+were|what's|whats)\s+",
    r"^\s*(?:please\s+)?(?:who\s+is|who\s+was|where\s+is|where\s+are|where\s+was|where\s+were)\s+",
    r"^\s*(?:please\s+)?(?:do\s+you\s+know\s+about|do\s+you\s+know\s+what|do\s+you\s+know\s+who)\s+",
    r"^\s*(?:please\s+)?(?:i\s+want\s+to\s+know\s+about|i\s+was\s+wondering\s+about)\s+",
)
TOPIC_SUFFIX_PATTERNS = (
    r"\s+(?:please|for\s+me)\s*$",
    r"\s+(?:is|are|was|were)\s*$",
)


def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def clean_query_text(text):
    query = normalize_text(text)
    query = re.sub(r"^[\"']+|[\"']+$", "", query)
    query = re.sub(r"\s+(?:for\s+me|please)\s*[?.!]*$", "", query, flags=re.IGNORECASE)
    query = re.sub(
        r"^\s*(?:tell\s+me\s+(?:about\s+)?|show\s+me\s+|explain\s+|describe\s+|what\s+is\s+|what\s+are\s+|who\s+is\s+|where\s+is\s+)",
        "",
        query,
        flags=re.IGNORECASE,
    )
    return query.strip(" \t\r\n?.!,")


def match_query(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            return clean_query_text(match.group("query"))

    return ""


def is_reference_query(query):
    words = re.findall(r"[a-zA-Z0-9]+", query.lower())

    if not words:
        return False

    meaningful_words = [
        word
        for word in words
        if word not in REFERENCE_WORDS and word not in QUERY_FILLER_WORDS
    ]
    return not meaningful_words and any(word in REFERENCE_WORDS for word in words)


def classify_search_request(question):
    text = normalize_text(question)
    image_query = match_query(DIRECT_IMAGE_QUERY_PATTERNS, text)

    if image_query:
        return SearchRoute(
            intent=SEARCH_INTENT_IMAGE,
            query=image_query,
            needs_context=is_reference_query(image_query),
        )

    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in CONTEXTUAL_IMAGE_PATTERNS):
        return SearchRoute(intent=SEARCH_INTENT_IMAGE, needs_context=True)

    web_query = match_query(DIRECT_WEB_QUERY_PATTERNS, text)

    if web_query:
        return SearchRoute(
            intent=SEARCH_INTENT_WEB,
            query=web_query,
            needs_context=is_reference_query(web_query),
        )

    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in CONTEXTUAL_WEB_PATTERNS):
        return SearchRoute(intent=SEARCH_INTENT_WEB, needs_context=True)

    return SearchRoute()


def is_explicit_search_request(question):
    return classify_search_request(question).intent != SEARCH_INTENT_NONE


def looks_like_math_topic(topic):
    compacted = topic.replace(" ", "")
    return bool(compacted) and bool(MATH_TOPIC_PATTERN.fullmatch(topic)) and any(
        character.isdigit() for character in topic
    )


def is_vague_topic_message(text):
    normalized = normalize_text(text).lower().strip("?.! ")
    return normalized in VAGUE_TOPIC_MESSAGES or is_explicit_search_request(normalized)


def clean_topic_from_message(text):
    topic = normalize_text(text)
    topic = re.split(r"(?<=[.!?])\s+", topic, maxsplit=1)[0]

    for pattern in TOPIC_PREFIX_PATTERNS:
        topic = re.sub(pattern, "", topic, flags=re.IGNORECASE)

    for pattern in TOPIC_SUFFIX_PATTERNS:
        topic = re.sub(pattern, "", topic, flags=re.IGNORECASE)

    topic = clean_query_text(topic)
    lowered_topic = topic.lower()

    if (
        not topic
        or lowered_topic in VAGUE_TOPIC_MESSAGES
        or lowered_topic in REFERENCE_WORDS
        or looks_like_math_topic(topic)
    ):
        return ""

    if len(topic) > 120:
        topic = topic[:120].rsplit(" ", 1)[0].strip()

    return topic


def topic_from_assistant_message(text):
    first_sentence = re.split(r"(?<=[.!?])\s+", normalize_text(text), maxsplit=1)[0]
    match = re.search(
        r"^\s*(?:an?\s+|the\s+)?(?P<topic>[A-Za-z][A-Za-z0-9\s'/-]{2,60}?)\s+(?:is|are|was|were)\b",
        first_sentence,
    )

    if not match:
        return ""

    return clean_topic_from_message(match.group("topic"))


def resolve_recent_topic(messages, limit=RECENT_TOPIC_MESSAGE_LIMIT):
    recent_messages = list(messages or [])[-limit:]

    for message in reversed(recent_messages):
        if message.get("role") != "user":
            continue

        content = normalize_text(message.get("content"))

        if not content:
            continue

        previous_route = classify_search_request(content)

        if (
            previous_route.intent != SEARCH_INTENT_NONE
            and previous_route.query
            and not previous_route.needs_context
        ):
            return previous_route.query

        if is_vague_topic_message(content):
            continue

        topic = clean_topic_from_message(content)

        if topic:
            return topic

    for message in reversed(recent_messages):
        if message.get("role") != "assistant":
            continue

        topic = topic_from_assistant_message(message.get("content"))

        if topic:
            return topic

    return ""


def route_search_request(question, requested_mode, recent_messages=None):
    route = classify_search_request(question)
    forced_search = requested_mode == "search"

    if route.intent == SEARCH_INTENT_NONE and not forced_search:
        return route

    if recent_messages is None:
        recent_messages = get_current_chat_messages()

    if route.intent == SEARCH_INTENT_NONE and forced_search:
        query = clean_topic_from_message(question) or clean_query_text(question)
        return SearchRoute(intent=SEARCH_INTENT_WEB, query=query or question)

    if route.needs_context:
        topic = resolve_recent_topic(recent_messages)

        if not topic:
            return SearchRoute(
                intent=route.intent,
                needs_context=True,
                needs_clarification=True,
            )

        return SearchRoute(intent=route.intent, query=topic, needs_context=True)

    return route


def log_error(kind, error):
    timestamp = datetime.now(timezone.utc).isoformat()
    message = f"[{timestamp}] {kind}: {repr(error)}\n"

    try:
        ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with ERROR_LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(message)
    except OSError as log_error:
        print(f"Could not write error log: {log_error}")

    print(f"{kind}: {error}")


def get_combined_search_images(query):
    try:
        return search_images(query)
    except Exception as error:
        log_error("Combined image search error", error)
        return []


def model_error_response(error):
    log_error("Model error", error)
    error_text = str(error)

    if "Image analysis requires" in error_text:
        return jsonify({"error": error_text}), 400

    return (
        jsonify(
            {
                "error": (
                    "LM Studio server is not responding. Make sure LM Studio is open, "
                    "the local server is running, and the model is loaded."
                )
            }
        ),
        502,
    )


def search_error_response(error):
    log_error("Search error", error)
    return (
        jsonify(
            {
                "error": (
                    "Search failed. Check your internet connection or try again in "
                    "a moment. Details were saved to Documents\\MiddAI\\logs."
                ),
                "detail": str(error),
            }
        ),
        502,
    )


def stream_event(event_type, **payload):
    payload["type"] = event_type
    return json.dumps(payload, ensure_ascii=False) + "\n"


def public_sources(evidence):
    return [
        {
            "title": source["title"],
            "url": source["url"],
        }
        for source in evidence
    ]


def parse_chat_payload(data):
    question = (data.get("question") or "").strip()
    requested_mode = (data.get("mode") or "chat").strip().lower()
    requested_depth = (data.get("depth") or DEFAULT_DEPTH).strip().lower()
    attached_documents, attached_images = prepare_uploaded_files(data.get("attachments") or [])

    if (attached_documents or attached_images) and not question:
        if attached_documents and attached_images:
            question = "Please analyse the attached files."
        elif attached_images:
            question = "Please analyse the attached image."
        else:
            question = "Please analyse the attached document."

    return question, requested_mode, requested_depth, attached_documents, attached_images


def find_lms_command():
    command = shutil.which("lms") or shutil.which("lms.exe")

    if command:
        return command

    bundled_path = Path.home() / ".lmstudio" / "bin" / "lms.exe"

    if bundled_path.exists():
        return str(bundled_path)

    return None


def hidden_subprocess_kwargs():
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0

    return {
        "startupinfo": startupinfo,
        "creationflags": subprocess.CREATE_NO_WINDOW,
    }


def run_lms_command(args):
    lms_command = find_lms_command()

    if not lms_command:
        print("Could not find lms command during shutdown.")
        return False

    command = [lms_command, *args]
    print("Running shutdown command:")
    print(subprocess.list2cmdline(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=25,
            **hidden_subprocess_kwargs(),
        )
    except Exception as error:
        print(f"Shutdown command failed: {error}")
        return False

    if result.stdout:
        print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())

    return result.returncode == 0


def command_text(command):
    return subprocess.list2cmdline([str(part) for part in command])


def run_lms_process(args, timeout_seconds=300, check=True):
    lms_command = find_lms_command()

    if not lms_command:
        raise RuntimeError("Could not find the LM Studio lms command.")

    command = [lms_command, *args]
    print("Running LM Studio command:")
    print(command_text(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=timeout_seconds,
            **hidden_subprocess_kwargs(),
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"LM Studio command timed out:\n{command_text(command)}"
        ) from error
    except Exception as error:
        raise RuntimeError(f"LM Studio command failed: {error}") from error

    output = f"{result.stdout}\n{result.stderr}".strip()

    if output:
        print(output)

    if check and result.returncode != 0:
        raise RuntimeError(
            f"LM Studio command failed with exit code {result.returncode}:\n"
            f"{command_text(command)}\n\n{output}"
        )

    return result


def lms_identifier_conflict(result):
    output = f"{result.stdout}\n{result.stderr}".casefold()
    return "identifier" in output and "already exists" in output


def load_active_model_with_settings(
    active_model,
    context_length,
    gpu_offload,
):
    model_key = str(active_model.get("model_key") or "").strip()
    chat_model_id = str(active_model.get("chat_model_id") or "local-model").strip()
    gpu_offload = str(gpu_offload or GPU_OFFLOAD_OFF).strip()

    if not model_key:
        raise RuntimeError("The active model does not have a saved LM Studio model key.")

    if chat_model_id != "local-model":
        raise RuntimeError(
            "This model is managed directly in LM Studio, so MiddAI cannot reload it."
        )

    run_lms_process(["unload", chat_model_id], timeout_seconds=90, check=False)
    time.sleep(1.5)

    load_args = [
        "load",
        model_key,
        "--identifier",
        chat_model_id,
        "--context-length",
        str(context_length),
        "--gpu",
        gpu_offload,
        "--yes",
    ]
    result = run_lms_process(load_args, timeout_seconds=600, check=False)

    if result.returncode == 0:
        return

    if not lms_identifier_conflict(result):
        output = f"{result.stdout}\n{result.stderr}".strip()
        raise RuntimeError(
            f"LM Studio could not load the model with the new context length.\n\n{output}"
        )

    for attempt in range(1, 4):
        print(f"Retrying after local-model identifier conflict ({attempt}/3)...")
        run_lms_process(["unload", chat_model_id], timeout_seconds=90, check=False)
        time.sleep(1.5)
        result = run_lms_process(load_args, timeout_seconds=600, check=False)

        if result.returncode == 0:
            return

        if not lms_identifier_conflict(result):
            output = f"{result.stdout}\n{result.stderr}".strip()
            raise RuntimeError(
                "LM Studio could not load the model with the new context length."
                f"\n\n{output}"
            )

    output = f"{result.stdout}\n{result.stderr}".strip()
    raise RuntimeError(
        "LM Studio could not free the local-model slot for reloading."
        f"\n\n{output}"
    )


def load_active_model_with_context(active_model, context_length):
    load_active_model_with_settings(
        active_model,
        context_length,
        active_model.get("gpu_offload"),
    )


def set_separate_ai_judge_model_enabled(enabled):
    run_lms_process(
        ["unload", AI_JUDGE_MODEL_ID],
        timeout_seconds=90,
        check=False,
    )

    if not enabled:
        return

    time.sleep(1.5)
    load_args = [
        "load",
        AI_JUDGE_MODEL_KEY,
        "--identifier",
        AI_JUDGE_MODEL_ID,
        "--context-length",
        str(AI_JUDGE_MODEL_CONTEXT_LENGTH),
        "--gpu",
        GPU_OFFLOAD_OFF,
        "--yes",
    ]
    result = run_lms_process(load_args, timeout_seconds=600, check=False)

    if result.returncode == 0:
        return

    output = f"{result.stdout}\n{result.stderr}".strip()
    raise RuntimeError(
        "LM Studio could not load the separate Qwen3-4B AI Judge model. "
        "Make sure Qwen3-4B-Instruct-2507 is downloaded in LM Studio and "
        "that the system has at least 16 GB RAM."
        f"\n\n{output}"
    )


def close_lm_studio_app():
    if os.name != "nt":
        return False

    command = ["taskkill", "/IM", "LM Studio.exe", "/T"]
    print("Running LM Studio close command:")
    print(subprocess.list2cmdline(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=15,
            **hidden_subprocess_kwargs(),
        )
    except Exception as error:
        print(f"LM Studio close command failed: {error}")
        return False

    output = f"{result.stdout}\n{result.stderr}".strip()

    if output:
        print(output)

    return result.returncode == 0 or "not found" in output.lower()


def shutdown_lm_studio():
    run_lms_command(["unload", AI_JUDGE_MODEL_ID])
    run_lms_command(["unload", "local-model"])
    run_lms_command(["server", "stop"])
    close_lm_studio_app()


def exit_middai_soon():
    time.sleep(0.8)
    os._exit(0)


def queue_memory_extraction(memory_mode, assistant_id=None):
    if memory_mode == MEMORY_MODE_OFF:
        return

    assistant_id = assistant_id or get_active_assistant_id()

    with MEMORY_WORKER_STATE_LOCK:
        if assistant_id in RUNNING_MEMORY_WORKERS:
            RERUN_MEMORY_WORKERS.add(assistant_id)
            return

        RUNNING_MEMORY_WORKERS.add(assistant_id)

    def run_memory_worker():
        restart_worker = False

        try:
            process_pending_memory_judgements(assistant_id=assistant_id)
        finally:
            with MEMORY_WORKER_STATE_LOCK:
                restart_worker = assistant_id in RERUN_MEMORY_WORKERS
                RERUN_MEMORY_WORKERS.discard(assistant_id)
                RUNNING_MEMORY_WORKERS.discard(assistant_id)

            if restart_worker:
                queue_memory_extraction(memory_mode, assistant_id=assistant_id)

    worker = threading.Thread(
        target=run_memory_worker,
        daemon=True,
    )
    worker.start()


def save_chat_turn(
    question,
    answer,
    memory_mode,
    start_memory_worker=True,
    sources=None,
    images=None,
    attachments=None,
):
    user_metadata = {}

    if attachments:
        user_metadata["attachments"] = attachments

    add_message(
        "user",
        question,
        extract_memory=False,
        memory_mode=memory_mode,
        metadata=user_metadata,
    )

    assistant_metadata = {}

    if sources:
        assistant_metadata["sources"] = [
            {
                "title": source.get("title"),
                "url": source.get("url"),
            }
            for source in sources
            if source.get("url")
        ]

    if images:
        assistant_metadata["images"] = images

    add_message("assistant", answer, metadata=assistant_metadata)

    if start_memory_worker:
        queue_memory_extraction(memory_mode)


@app.get("/")
def home():
    return render_template_string(PAGE_HTML)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "app": "MiddAI", "port": APP_PORT})


@app.post("/api/new-chat")
def new_chat():
    archived = archive_current_chat()
    current_chat_id = start_new_current_chat()
    return jsonify(
        {
            "ok": True,
            "archived": bool(archived),
            "current_chat_id": current_chat_id,
            "chats": list_saved_chats(),
        }
    )


@app.get("/api/saved-chats")
def saved_chats():
    return jsonify({"chats": list_saved_chats()})


@app.post("/api/delete-chat")
def delete_chat():
    data = request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")
    result = delete_saved_chat(chat_id)

    if not result.get("deleted"):
        return jsonify({"error": "Choose a saved chat to delete."}), 404

    return jsonify(
        {
            "ok": True,
            "cleared_current": result.get("cleared_current", False),
            "chats": list_saved_chats(),
        }
    )


@app.post("/api/open-chat")
def open_chat():
    data = request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")
    messages = open_saved_chat(chat_id)

    if messages is None:
        return jsonify({"error": "Choose a saved chat to open."}), 404

    return jsonify({"ok": True, "messages": messages, "chats": list_saved_chats()})


@app.post("/api/delete-history")
def delete_history():
    delete_chat_history()
    return jsonify({"ok": True})


@app.get("/api/readable-memories")
def readable_memories():
    return jsonify(list_readable_memories())


@app.get("/api/runtime-settings")
def runtime_settings():
    return jsonify(runtime_settings_payload())


def runtime_settings_payload():
    active_model = read_active_model()
    context_length = active_model.get("context_length")
    min_context_length = infer_min_context_length(active_model)
    max_context_length = infer_max_context_length(active_model)
    active_assistant = get_active_assistant()
    managed_model = bool(active_model.get("model_key")) and str(
        active_model.get("chat_model_id") or "local-model"
    ) == "local-model"
    memory_mode = get_runtime_memory_mode()
    gpu_offload = get_runtime_gpu_offload()

    return {
        "active_model": active_model,
        "model_label": active_model.get("label")
        or active_model.get("model_name")
        or "Unknown model",
        "context_length": context_length,
        "min_context_length": min_context_length,
        "max_context_length": max_context_length,
        "temperature": get_runtime_temperature(),
        "can_update_context": managed_model,
        "memory_mode": memory_mode,
        "memory_available": memory_mode != MEMORY_MODE_OFF,
        "ai_judge_enabled": get_runtime_ai_judge_enabled(),
        "ai_judge_separate_model": get_runtime_ai_judge_separate_model(),
        "gpu_offload": gpu_offload,
        "gpu_offload_enabled": gpu_offload != GPU_OFFLOAD_OFF,
        "gpu_offload_percent": get_runtime_gpu_offload_percent(),
        "can_update_gpu": managed_model,
        "prompt_profile": active_model.get("prompt_profile", ""),
        "image_analysis": get_runtime_supports_image_analysis(),
        "assistant": public_assistant(active_assistant, get_active_assistant_id()),
        "assistant_greeting": get_assistant_greeting(),
    }


@app.post("/api/runtime-settings/save")
def update_runtime_settings():
    data = request.get_json(silent=True) or {}
    active_model = read_active_model()

    if not active_model:
        return jsonify({"error": "No active model is saved yet."}), 400

    min_context_length = infer_min_context_length(active_model)
    max_context_length = infer_max_context_length(active_model)

    try:
        requested_context_length = int(
            data.get(
                "context_length",
                active_model.get("context_length", min_context_length),
            )
        )
        requested_temperature = float(
            data.get("temperature", get_runtime_temperature())
        )
    except (TypeError, ValueError):
        return jsonify({"error": "Choose valid runtime settings."}), 400

    if not min_context_length <= requested_context_length <= max_context_length:
        return jsonify(
            {
                "error": (
                    f"Context length must be between {min_context_length} and "
                    f"{max_context_length} tokens."
                )
            }
        ), 400

    if not 0 <= requested_temperature <= 2:
        return jsonify({"error": "Temperature must be between 0.0 and 2.0."}), 400

    current_memory_mode = get_runtime_memory_mode()
    memory_available = current_memory_mode != MEMORY_MODE_OFF
    requested_ai_judge = bool(
        data.get("ai_judge_enabled", get_runtime_ai_judge_enabled())
    )
    requested_memory_mode = (
        current_memory_mode
        if not memory_available
        else (
            MEMORY_MODE_AI_JUDGE
            if requested_ai_judge
            else MEMORY_MODE_RULES
        )
    )
    current_separate_ai_judge = get_runtime_ai_judge_separate_model()
    requested_separate_ai_judge = bool(
        requested_ai_judge
        and data.get(
            "ai_judge_separate_model",
            current_separate_ai_judge,
        )
    )
    requested_gpu_enabled = bool(
        data.get(
            "gpu_offload_enabled",
            get_runtime_gpu_offload() != GPU_OFFLOAD_OFF,
        )
    )
    requested_gpu_percent = normalize_gpu_offload_percent(
        data.get(
            "gpu_offload_percent",
            get_runtime_gpu_offload_percent(),
        )
    )
    requested_gpu_offload = (
        normalize_gpu_offload(requested_gpu_percent)
        if requested_gpu_enabled
        else GPU_OFFLOAD_OFF
    )
    current_context_length = int(
        active_model.get("context_length") or min_context_length
    )
    current_gpu_offload = normalize_gpu_offload(
        active_model.get("gpu_offload")
    )
    context_changed = requested_context_length != current_context_length
    gpu_changed = requested_gpu_offload != current_gpu_offload
    memory_changed = requested_memory_mode != current_memory_mode
    separate_ai_judge_changed = (
        requested_separate_ai_judge != current_separate_ai_judge
    )
    managed_model = bool(active_model.get("model_key")) and str(
        active_model.get("chat_model_id") or "local-model"
    ) == "local-model"

    if (context_changed or gpu_changed) and not managed_model:
        return jsonify(
            {
                "error": (
                    "This model is managed directly in LM Studio, so MiddAI "
                    "cannot change its context length or GPU offload."
                )
            }
        ), 400

    if context_changed or gpu_changed:
        try:
            load_active_model_with_settings(
                active_model,
                requested_context_length,
                requested_gpu_offload,
            )
        except RuntimeError as error:
            log_error("Runtime model settings update failed", error)
            return jsonify({"error": str(error)}), 500

    if separate_ai_judge_changed:
        try:
            set_separate_ai_judge_model_enabled(
                requested_separate_ai_judge
            )
        except RuntimeError as error:
            log_error("Separate AI Judge model update failed", error)
            return jsonify({"error": str(error)}), 500

    try:
        set_runtime_temperature(requested_temperature)
        updated_model = dict(read_active_model() or active_model)
        updated_model["context_length"] = requested_context_length
        updated_model["min_context_length"] = min_context_length
        updated_model["max_context_length"] = max_context_length
        updated_model["gpu_offload"] = requested_gpu_offload
        updated_model["gpu_offload_percent"] = requested_gpu_percent
        updated_model["memory_mode"] = requested_memory_mode
        updated_model["ai_judge_separate_model"] = (
            requested_separate_ai_judge
        )

        if (
            gpu_changed
            or requested_gpu_percent != get_runtime_gpu_offload_percent()
        ):
            updated_model["gpu_offload_user_override"] = True

        if memory_changed:
            updated_model["memory_mode_user_override"] = True

        updated_model.pop("gpu_detected", None)
        updated_model.pop("gpu_names", None)
        updated_model["temperature"] = round(requested_temperature, 1)
        updated_model["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_active_model(updated_model)
    except OSError as error:
        log_error("Runtime settings save failed", error)
        return jsonify({"error": "MiddAI could not save the runtime settings."}), 500

    return jsonify({"ok": True, **runtime_settings_payload()})


@app.post("/api/runtime-settings/context")
def update_runtime_context():
    data = request.get_json(silent=True) or {}
    active_model = read_active_model()

    if not active_model:
        return jsonify({"error": "No active model is saved yet."}), 400

    if not active_model.get("model_key"):
        return jsonify({"error": "The active model cannot be reloaded by MiddAI."}), 400

    if str(active_model.get("chat_model_id") or "local-model") != "local-model":
        return jsonify(
            {
                "error": (
                    "This model is managed directly in LM Studio, so MiddAI cannot "
                    "reload it with a new context length."
                )
            }
        ), 400

    try:
        requested_context_length = int(data.get("context_length"))
    except (TypeError, ValueError):
        return jsonify({"error": "Choose a valid context length."}), 400

    min_context_length = infer_min_context_length(active_model)
    max_context_length = infer_max_context_length(active_model)

    if requested_context_length < min_context_length:
        return jsonify(
            {"error": f"Context length must be at least {min_context_length} tokens."}
        ), 400

    if requested_context_length > max_context_length:
        return jsonify(
            {
                "error": (
                    f"Context length must be {max_context_length} tokens or lower "
                    "for this model."
                )
            }
        ), 400

    try:
        load_active_model_with_context(active_model, requested_context_length)
    except RuntimeError as error:
        log_error("Context length update failed", error)
        return jsonify({"error": str(error)}), 500

    updated_model = dict(active_model)
    updated_model["context_length"] = requested_context_length
    updated_model["min_context_length"] = min_context_length
    updated_model["max_context_length"] = max_context_length
    updated_model["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        write_active_model(updated_model)
    except OSError as error:
        log_error("Active model config update failed", error)
        return jsonify({"error": "The model reloaded, but MiddAI could not save the updated config."}), 500

    return jsonify({"ok": True, **runtime_settings_payload()})


@app.post("/api/runtime-settings/temperature")
def update_runtime_temperature():
    data = request.get_json(silent=True) or {}

    try:
        requested_temperature = float(data.get("temperature"))
    except (TypeError, ValueError):
        return jsonify({"error": "Choose a valid temperature."}), 400

    if requested_temperature < 0 or requested_temperature > 2:
        return jsonify({"error": "Temperature must be between 0.0 and 2.0."}), 400

    try:
        set_runtime_temperature(requested_temperature)
    except OSError as error:
        log_error("Temperature update failed", error)
        return jsonify({"error": "MiddAI could not save the temperature."}), 500

    return jsonify({"ok": True, **runtime_settings_payload()})


@app.get("/api/assistants")
def assistants():
    return jsonify(
        {
            "assistants": list_public_assistants(),
            "active_assistant_id": get_active_assistant_id(),
            "greeting": get_assistant_greeting(),
        }
    )


@app.post("/api/assistants/select")
def select_assistant():
    data = request.get_json(silent=True) or {}
    assistant_id = data.get("assistant_id")
    previous_assistant_id = get_active_assistant_id()
    assistant = get_assistant_by_id(assistant_id)

    if not assistant:
        return jsonify({"error": "Choose an assistant first."}), 404

    assistant_changed = str(previous_assistant_id or "") != str(assistant["id"])
    archived = None
    current_chat_id = None

    if assistant_changed:
        archived = archive_current_chat()
        assistant = set_active_assistant(assistant["id"])
        ensure_memory_file()

        chats = list_saved_chats()
        messages = get_current_chat_messages()

        for chat in chats:
            if chat.get("current") or chat.get("active"):
                current_chat_id = chat.get("id")
                break

        if current_chat_id is None:
            current_chat_id = start_new_current_chat()
            chats = list_saved_chats()
    else:
        chats = list_saved_chats()
        messages = get_current_chat_messages()

    return jsonify(
        {
            "ok": True,
            "assistant": public_assistant(assistant, assistant["id"]),
            "active_assistant_id": assistant["id"],
            "greeting": get_assistant_greeting(),
            "assistants": list_public_assistants(),
            "assistant_changed": assistant_changed,
            "archived": bool(archived),
            "current_chat_id": current_chat_id,
            "messages": messages,
            "chats": chats,
            "memories": list_readable_memories(),
        }
    )


@app.post("/api/assistants/create")
def create_assistant():
    data = request.get_json(silent=True) or {}

    try:
        assistant = create_custom_assistant(
            data.get("name"),
            data.get("instructions"),
            data.get("personality"),
            data.get("greeting"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    archive_current_chat()
    set_active_assistant(assistant["id"])
    ensure_memory_file()
    current_chat_id = start_new_current_chat()

    return jsonify(
        {
            "ok": True,
            "assistant": public_assistant(assistant, assistant["id"]),
            "active_assistant_id": assistant["id"],
            "greeting": get_assistant_greeting(),
            "assistants": list_public_assistants(),
            "current_chat_id": current_chat_id,
            "messages": [],
            "chats": list_saved_chats(),
            "memories": list_readable_memories(),
        }
    )


@app.post("/api/assistants/update")
def update_assistant():
    data = request.get_json(silent=True) or {}

    try:
        assistant = update_custom_assistant(
            data.get("assistant_id"),
            data.get("name"),
            data.get("instructions"),
            data.get("personality"),
            data.get("greeting"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    active_id = get_active_assistant_id()

    return jsonify(
        {
            "ok": True,
            "assistant": public_assistant(assistant, active_id),
            "active_assistant_id": active_id,
            "greeting": get_assistant_greeting(),
            "assistants": list_public_assistants(),
        }
    )


@app.post("/api/assistants/delete")
def delete_assistant():
    data = request.get_json(silent=True) or {}
    assistant_id = data.get("assistant_id")
    delete_data = bool(data.get("delete_data"))
    was_active = str(get_active_assistant_id()) == str(assistant_id or "")

    try:
        if was_active:
            archive_current_chat()

        active_assistant = delete_custom_assistant(assistant_id)

        if delete_data:
            delete_assistant_data(assistant_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    active_id = get_active_assistant_id()
    ensure_memory_file()
    chats = list_saved_chats()
    messages = get_current_chat_messages()
    current_chat_id = None

    for chat in chats:
        if chat.get("current") or chat.get("active"):
            current_chat_id = chat.get("id")
            break

    if current_chat_id is None:
        current_chat_id = start_new_current_chat()
        chats = list_saved_chats()

    return jsonify(
        {
            "ok": True,
            "assistant": public_assistant(active_assistant, active_id),
            "active_assistant_id": active_id,
            "greeting": get_assistant_greeting(),
            "assistants": list_public_assistants(),
            "data_deleted": delete_data,
            "current_chat_id": current_chat_id,
            "messages": messages,
            "chats": chats,
            "memories": list_readable_memories(),
        }
    )


@app.post("/api/add-memory")
def add_memory():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Write a memory first."}), 400

    memory = add_user_defined_memory(text)

    if not memory:
        return jsonify({"error": "Could not save that memory."}), 400

    return jsonify({"ok": True, "memory": memory})


@app.post("/api/delete-memory-item")
def delete_memory_item():
    data = request.get_json(silent=True) or {}
    memory_id = data.get("memory_id")
    memory_scope = data.get("memory_scope")

    if not delete_stored_memory_item(memory_id, memory_scope):
        return jsonify({"error": "Choose a memory to delete."}), 404

    return jsonify({"ok": True})


@app.post("/api/delete-memory")
def delete_memory():
    delete_all_memory()
    return jsonify({"ok": True})


@app.post("/api/quit")
def quit_middai():
    shutdown_lm_studio()
    threading.Thread(target=exit_middai_soon, daemon=True).start()
    return jsonify({"ok": True})


@app.get("/api/current-chat")
def current_chat():
    messages = get_current_chat_messages()
    saved_chats = list_saved_chats()

    if not messages and not saved_chats:
        current_chat_id = start_new_current_chat()
        saved_chats = list_saved_chats()
    else:
        current_chat_id = None

        for chat in saved_chats:
            if chat.get("current") or chat.get("active"):
                current_chat_id = chat.get("id")
                break

    return jsonify(
        {
            "messages": messages,
            "fresh": False,
            "current_chat_id": current_chat_id,
            "chats": saved_chats,
        }
    )


@app.post("/api/chat-stream")
def chat_stream():
    data = request.get_json(silent=True) or {}

    try:
        (
            question,
            requested_mode,
            requested_depth,
            attached_documents,
            attached_images,
        ) = parse_chat_payload(data)
    except AttachmentError as error:
        return jsonify({"error": str(error)}), 400

    attachment_metadata = public_file_metadata(attached_documents, attached_images)

    if requested_mode == "local":
        requested_mode = "chat"

    if not question:
        return jsonify({"error": "Ask a question first."}), 400

    if requested_mode not in {"chat", "search"}:
        return jsonify({"error": "Unknown chat mode."}), 400

    if requested_depth not in DEPTH_PRESETS:
        return jsonify({"error": "Unknown response depth."}), 400

    @stream_with_context
    def generate():
        print()
        print(f"Question: {question}")
        print(f"Mode: {requested_mode}")
        print(f"Depth: {requested_depth}")
        print(f"Document attachments: {len(attached_documents)}")
        print(f"Image attachments: {len(attached_images)}")
        print("Streaming: enabled")

        memory_mode = get_runtime_memory_mode()
        prompt_profile = get_runtime_prompt_profile()
        print(f"Memory mode: {memory_mode}")
        print(f"Prompt profile: {prompt_profile}")

        try:
            memory_messages = (
                []
                if memory_mode == MEMORY_MODE_OFF
                else get_selected_memory(question, prompt_profile=prompt_profile)
            )

            recent_chat_messages = get_current_chat_messages()
            search_route = route_search_request(
                question,
                requested_mode,
                recent_messages=recent_chat_messages,
            )
            use_web = search_route.intent != SEARCH_INTENT_NONE

            if requested_mode == "chat" and use_web:
                print("Explicit search request detected in Chat mode.")

            if attached_images:
                print("Answering with image analysis...")
                yield stream_event("status", message="Analysing attached image")

                answer_parts = []

                try:
                    for chunk in stream_model_with_images(
                        question,
                        requested_depth,
                        memory_messages,
                        attached_documents=attached_documents,
                        attached_images=attached_images,
                    ):
                        answer_parts.append(chunk)
                        yield stream_event("token", token=chunk)
                except Exception as error:
                    log_error("Image analysis stream error", error)
                    yield stream_event("error", error=str(error))
                    return

                answer = "".join(answer_parts).strip()

                if not answer:
                    yield stream_event("error", error="The image model did not return a response.")
                    return

                save_chat_turn(
                    question,
                    answer,
                    memory_mode,
                    attachments=attachment_metadata,
                )

                if memory_mode != MEMORY_MODE_OFF:
                    add_visual_context(question, answer, attached_images)

                yield stream_event(
                    "done",
                    answer=answer,
                    depth=requested_depth,
                    mode="chat",
                    sources=[],
                    images=[],
                )
                return

            if search_route.needs_clarification:
                answer = "What should I search for?"
                save_chat_turn(
                    question,
                    answer,
                    memory_mode,
                    attachments=attachment_metadata,
                )
                yield stream_event("token", token=answer)
                yield stream_event(
                    "done",
                    answer=answer,
                    depth=requested_depth,
                    mode="chat",
                    sources=[],
                    images=[],
                )
                return

            if not use_web:
                print("Answering in Chat mode without web search...")
                yield stream_event("status", message="Thinking in chat")

                answer_parts = []

                try:
                    for chunk in stream_model_locally(
                        question,
                        requested_depth,
                        memory_messages,
                        attached_documents=attached_documents,
                    ):
                        answer_parts.append(chunk)
                        yield stream_event("token", token=chunk)
                except Exception as error:
                    log_error("Model stream error", error)
                    yield stream_event(
                        "error",
                        error=(
                            "LM Studio server is not responding. Make sure LM Studio "
                            "is open, the local server is running, and the model is loaded."
                        ),
                    )
                    return

                answer = "".join(answer_parts).strip()

                if not answer:
                    yield stream_event("error", error="The model did not return a response.")
                    return

                save_chat_turn(
                    question,
                    answer,
                    memory_mode,
                    attachments=attachment_metadata,
                )

                yield stream_event(
                    "done",
                    answer=answer,
                    depth=requested_depth,
                    mode="chat",
                    sources=[],
                    images=[],
                )
                return

            search_query = search_route.query

            if search_query != question:
                print(f"Search query: {search_query}")

            print(f"Search intent: {search_route.intent}")
            print("Searching the web...")
            yield stream_event("status", message="Searching the web")

            try:
                results = search_web(
                    search_query,
                    requested_depth,
                    prompt_profile=prompt_profile,
                )
            except Exception as error:
                log_error("Search stream error", error)
                yield stream_event(
                    "error",
                    error=(
                        "Search failed. Check your internet connection or try again "
                        "in a moment. Details were saved to Documents\\MiddAI\\logs."
                    ),
                    detail=str(error),
                )
                return

            if not results:
                yield stream_event("error", error="No search results found.")
                return

            print(f"Found {len(results)} result(s).")
            print("Extracting evidence...")
            yield stream_event("status", message="Reading sources")

            try:
                evidence = extract_evidence(
                    search_query,
                    results,
                    requested_depth,
                    prompt_profile=prompt_profile,
                )
            except Exception as error:
                log_error("Search stream error", error)
                yield stream_event(
                    "error",
                    error=(
                        "Search failed. Check your internet connection or try again "
                        "in a moment. Details were saved to Documents\\MiddAI\\logs."
                    ),
                    detail=str(error),
                )
                return

            if not evidence:
                yield stream_event(
                    "error",
                    error="Could not extract readable evidence from the search results.",
                )
                return

            print(f"Extracted evidence from {len(evidence)} page(s).")
            print("Searching for images...")
            yield stream_event("status", message="Finding images")
            images = get_combined_search_images(search_query)
            print(f"Found {len(images)} image result(s).")

            print("Asking local model...")
            yield stream_event("status", message="Writing answer")

            model_question = question

            if search_route.needs_context:
                model_question = f"{question}\n\nResolved search topic: {search_query}"

            answer_parts = []

            try:
                for chunk in stream_model(
                    model_question,
                    evidence,
                    requested_depth,
                    memory_messages,
                    image_results=images,
                    attached_documents=attached_documents,
                ):
                    answer_parts.append(chunk)
                    yield stream_event("token", token=chunk)
            except Exception as error:
                log_error("Model stream error", error)
                yield stream_event(
                    "error",
                    error=(
                        "LM Studio server is not responding. Make sure LM Studio "
                        "is open, the local server is running, and the model is loaded."
                    ),
                )
                return

            answer = "".join(answer_parts).strip()

            if not answer:
                yield stream_event("error", error="The model did not return a response.")
                return

            save_chat_turn(
                question,
                answer,
                memory_mode,
                start_memory_worker=False,
                sources=evidence,
                images=images,
                attachments=attachment_metadata,
            )

            if memory_mode != MEMORY_MODE_OFF:
                add_search_context(question, answer, evidence)

            queue_memory_extraction(memory_mode)

            yield stream_event(
                "done",
                answer=answer,
                depth=requested_depth,
                mode="search",
                sources=public_sources(evidence),
                images=images,
            )
        except Exception as error:
            log_error("Chat stream error", error)
            yield stream_event("error", error="MiddAI hit an unexpected chat error.")

    return Response(
        generate(),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}

    try:
        (
            question,
            requested_mode,
            requested_depth,
            attached_documents,
            attached_images,
        ) = parse_chat_payload(data)
    except AttachmentError as error:
        return jsonify({"error": str(error)}), 400

    attachment_metadata = public_file_metadata(attached_documents, attached_images)

    if requested_mode == "local":
        requested_mode = "chat"

    if not question:
        return jsonify({"error": "Ask a question first."}), 400

    if requested_mode not in {"chat", "search"}:
        return jsonify({"error": "Unknown chat mode."}), 400

    if requested_depth not in DEPTH_PRESETS:
        return jsonify({"error": "Unknown response depth."}), 400

    print()
    print(f"Question: {question}")
    print(f"Mode: {requested_mode}")
    print(f"Depth: {requested_depth}")
    print(f"Document attachments: {len(attached_documents)}")
    print(f"Image attachments: {len(attached_images)}")

    memory_mode = get_runtime_memory_mode()
    prompt_profile = get_runtime_prompt_profile()
    print(f"Memory mode: {memory_mode}")
    print(f"Prompt profile: {prompt_profile}")

    memory_messages = (
        []
        if memory_mode == MEMORY_MODE_OFF
        else get_selected_memory(question, prompt_profile=prompt_profile)
    )

    recent_chat_messages = get_current_chat_messages()
    search_route = route_search_request(
        question,
        requested_mode,
        recent_messages=recent_chat_messages,
    )
    use_web = search_route.intent != SEARCH_INTENT_NONE

    if requested_mode == "chat" and use_web:
        print("Explicit search request detected in Chat mode.")

    if attached_images:
        print("Answering with image analysis...")

        try:
            answer = ask_model_with_images(
                question,
                requested_depth,
                memory_messages,
                attached_documents=attached_documents,
                attached_images=attached_images,
            )
        except Exception as error:
            return model_error_response(error)

        save_chat_turn(
            question,
            answer,
            memory_mode,
            attachments=attachment_metadata,
        )

        if memory_mode != MEMORY_MODE_OFF:
            add_visual_context(question, answer, attached_images)

        return jsonify(
            {
                "answer": answer,
                "depth": requested_depth,
                "sources": [],
                "images": [],
                "mode": "chat",
            }
        )

    if search_route.needs_clarification:
        answer = "What should I search for?"
        save_chat_turn(
            question,
            answer,
            memory_mode,
            attachments=attachment_metadata,
        )

        return jsonify(
            {
                "answer": answer,
                "depth": requested_depth,
                "sources": [],
                "images": [],
                "mode": "chat",
            }
        )

    if not use_web:
        print("Answering in Chat mode without web search...")
        try:
            answer = ask_model_locally(
                question,
                requested_depth,
                memory_messages,
                attached_documents=attached_documents,
            )
        except Exception as error:
            return model_error_response(error)

        save_chat_turn(
            question,
            answer,
            memory_mode,
            attachments=attachment_metadata,
        )

        return jsonify(
            {
                "answer": answer,
                "depth": requested_depth,
                "sources": [],
                "images": [],
                "mode": "chat",
            }
        )

    search_query = search_route.query

    if search_query != question:
        print(f"Search query: {search_query}")

    print(f"Search intent: {search_route.intent}")

    print("Searching the web...")

    try:
        results = search_web(
            search_query,
            requested_depth,
            prompt_profile=prompt_profile,
        )
    except Exception as error:
        return search_error_response(error)

    if not results:
        return jsonify({"error": "No search results found."}), 404

    print(f"Found {len(results)} result(s).")
    print("Extracting evidence...")

    try:
        evidence = extract_evidence(
            search_query,
            results,
            requested_depth,
            prompt_profile=prompt_profile,
        )
    except Exception as error:
        return search_error_response(error)

    if not evidence:
        return jsonify(
            {"error": "Could not extract readable evidence from the search results."}
        ), 502

    print(f"Extracted evidence from {len(evidence)} page(s).")
    print("Searching for images...")
    images = get_combined_search_images(search_query)
    print(f"Found {len(images)} image result(s).")

    print("Asking local model...")

    try:
        model_question = question

        if search_route.needs_context:
            model_question = f"{question}\n\nResolved search topic: {search_query}"

        answer = ask_model(
            model_question,
            evidence,
            requested_depth,
            memory_messages,
            image_results=images,
            attached_documents=attached_documents,
        )
    except Exception as error:
        return model_error_response(error)

    save_chat_turn(
        question,
        answer,
        memory_mode,
        start_memory_worker=False,
        sources=evidence,
        images=images,
        attachments=attachment_metadata,
    )
    if memory_mode != MEMORY_MODE_OFF:
        add_search_context(question, answer, evidence)
    queue_memory_extraction(memory_mode)

    return jsonify(
        {
            "answer": answer,
            "depth": requested_depth,
            "mode": "search",
            "sources": [
                {
                    "title": source["title"],
                    "url": source["url"],
                }
                for source in evidence
            ],
            "images": images,
        }
    )


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
