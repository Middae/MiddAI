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
    delete_all_memory,
    delete_saved_chat,
    delete_user_defined_memory,
    ensure_memory_file,
    get_current_chat_messages,
    get_selected_memory,
    list_readable_memories,
    list_saved_chats,
    open_saved_chat,
    process_pending_memory_judgements,
    start_new_current_chat,
)
from persona import ensure_persona_file
from runtime_state import (
    MEMORY_MODE_OFF,
    get_runtime_memory_mode,
    get_runtime_prompt_profile,
)
from search_tools import extract_evidence, search_images, search_web, should_search_images
from web_page import PAGE_HTML


def resource_path(relative_path):
    relative_path = Path(relative_path)

    if hasattr(sys, "_MEIPASS"):
        external_assets = Path(sys.executable).resolve().parent / "Assets"

        if relative_path.parts and relative_path.parts[0].lower() == "assets":
            packaged_asset = external_assets.joinpath(*relative_path.parts[1:])

            if packaged_asset.exists():
                return str(packaged_asset)

            return str(external_assets)

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


DIRECT_IMAGE_QUERY_PATTERNS = (
    r"^\s*(?:please\s+)?(?:search|look\s+up|find|show|get)\s+(?:for\s+)?(?:similar|related)\s+(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for|to)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?i\s+(?:would\s+like|want|need|wanted|was\s+looking\s+for|am\s+looking\s+for)\s+(?:to\s+see\s+|to\s+find\s+|to\s+search\s+for\s+|to\s+look\s+up\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?i\s+(?:wanted|want|would\s+like|meant|asked)\s+(?:you\s+)?(?:to\s+)?(?:search|look\s+up|find|show|get)\s+(?:for\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?(?:search|look\s+up)\s+(?:for\s+)?(?:an?\s+|some\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:find|show|get)\s+(?:me\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:image|picture|photo)\s+search\s+(?:for|of)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:do|run)\s+(?:an?\s+)?image\s+search\s+(?:for|of)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?(?:what\s+does|what\s+do)\s+(?P<query>.+?)\s+looks?\s+like\??$",
    r"^\s*(?:please\s+)?show\s+(?:me\s+)?what\s+(?P<query>.+?)\s+looks?\s+like\??$",
    r"^\s*(?:please\s+)?(?:can|could|may)\s+i\s+see\s+(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s+(?:of|for)\s+(?P<query>.+)$",
    r"^\s*(?:please\s+)?visual\s+examples?\s+(?:of|for)\s+(?P<query>.+)$",
)
CONTEXTUAL_IMAGE_PATTERNS = (
    r"^\s*(?:please\s+)?(?:search|look\s+up|find|show|get)\s+(?:for\s+)?(?:similar|related)\s+(?:image|images|picture|pictures|photo|photos|pic|pics)\s*$",
    r"^\s*(?:please\s+)?i\s+(?:wanted|want|would\s+like|meant|asked)\s+(?:you\s+)?(?:to\s+)?(?:search|look\s+up|find|show|get)\s+(?:for\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s*$",
    r"^\s*(?:please\s+)?(?:find|show|get)\s+(?:me\s+)?(?:an?\s+|some\s+|the\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s*$",
    r"^\s*(?:please\s+)?(?:search|look\s+up)\s+(?:for\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s*$",
    r"^\s*(?:please\s+)?(?:image|picture|photo)\s+search\s*$",
    r"^\s*(?:please\s+)?(?:do|run)\s+(?:an?\s+)?image\s+search\s*$",
    r"^\s*(?:please\s+)?(?:what\s+does|what\s+do)\s+(?:it|that|this|them|those|these)\s+looks?\s+like\??$",
    r"^\s*(?:please\s+)?show\s+(?:me\s+)?what\s+(?:it|that|this|them|those|these)\s+looks?\s+like\??$",
    r"^\s*(?:please\s+)?(?:can|could|may)\s+i\s+see\s+(?:an?\s+|some\s+)?(?:image|images|picture|pictures|photo|photos|pic|pics)\s*$",
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


def shutdown_lm_studio():
    run_lms_command(["unload", "local-model"])
    run_lms_command(["server", "stop"])


def exit_middai_soon():
    time.sleep(0.8)
    os._exit(0)


def queue_memory_extraction(memory_mode):
    if memory_mode == MEMORY_MODE_OFF:
        return

    worker = threading.Thread(
        target=process_pending_memory_judgements,
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
    if memory_mode == MEMORY_MODE_OFF:
        return

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

    if not delete_user_defined_memory(memory_id):
        return jsonify({"error": "Choose a custom memory to delete."}), 404

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

    return jsonify(
        {
            "messages": messages,
            "fresh": not messages and not saved_chats,
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
            images = []
            include_images = should_search_images(requested_depth, prompt_profile)

            if include_images:
                print("Searching for images...")
                yield stream_event("status", message="Searching for images")

                try:
                    images = search_images(search_query)
                except Exception as error:
                    log_error("Image search error", error)
                    images = []

            if images:
                print(f"Found {len(images)} image result(s).")
            elif not include_images:
                print("Image search skipped for this response speed.")
            else:
                print("No usable image results found.")

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
    images = []
    include_images = should_search_images(requested_depth, prompt_profile)

    if include_images:
        print("Searching for images...")

        try:
            images = search_images(search_query)
        except Exception as error:
            log_error("Image search error", error)
            images = []

    if images:
        print(f"Found {len(images)} image result(s).")
    elif not include_images:
        print("Image search skipped for this response speed.")
    else:
        print("No usable image results found.")

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
