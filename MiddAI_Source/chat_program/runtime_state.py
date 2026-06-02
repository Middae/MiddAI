import json
import sys
from pathlib import Path

from config import MIDDAI_DIR


ACTIVE_MODEL_FILE = MIDDAI_DIR / "active_model.json"
LOCAL_ACTIVE_MODEL_FILE = (
    Path(sys.executable).resolve().parent / "active_model.json"
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[1] / "active_model.json"
)

MEMORY_MODE_AUTO = "auto"
MEMORY_MODE_RULES = "rules"
MEMORY_MODE_AI_JUDGE = "ai_judge"
MEMORY_MODE_OFF = "off"
PROMPT_PROFILE_STANDARD = "standard"
PROMPT_PROFILE_PHI_WORKDESK = "phi_workdesk"
PROMPT_PROFILE_QWEN4_LIGHT = "qwen4_light"
PROMPT_PROFILE_QWEN8_MEDIUM = "qwen8_medium"
PROMPT_PROFILE_LARGE = "large_model"
PROMPT_PROFILE_EXTREME = "extreme_model"
PROMPT_PROFILE_RESTRICTED = "restricted_model"
MEMORY_MODES = {
    MEMORY_MODE_AUTO,
    MEMORY_MODE_RULES,
    MEMORY_MODE_AI_JUDGE,
    MEMORY_MODE_OFF,
}


def read_active_model():
    for path in (ACTIVE_MODEL_FILE, LOCAL_ACTIVE_MODEL_FILE):
        data = read_active_model_file(path)

        if data:
            return data

    return {}


def read_active_model_file(path):
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def get_runtime_memory_mode():
    active_model = read_active_model()
    mode = str(active_model.get("memory_mode", MEMORY_MODE_AUTO)).strip().lower()

    if mode == MEMORY_MODE_AUTO or mode not in MEMORY_MODES:
        return MEMORY_MODE_RULES

    return mode


def get_active_model_label():
    active_model = read_active_model()
    return str(active_model.get("label") or active_model.get("model_name") or "").strip()


def get_runtime_chat_model_id(default_model_id="local-model"):
    active_model = read_active_model()
    model_id = str(active_model.get("chat_model_id") or "").strip()

    return model_id or default_model_id


def get_runtime_supports_image_analysis():
    active_model = read_active_model()

    if bool(active_model.get("image_analysis")):
        return True

    model_text = get_active_model_text()
    return "qwen2.5-vl" in model_text or "vision" in model_text


def is_phi_workdesk_active():
    model_text = get_active_model_text()
    return "phi-4-mini" in model_text or "phi4-mini" in model_text


def get_active_model_text():
    active_model = read_active_model()
    return " ".join(
        str(active_model.get(key, ""))
        for key in ("label", "model_name", "download_query", "model_key", "chat_model_id")
    ).casefold()


def get_runtime_prompt_profile():
    model_text = get_active_model_text()

    if "phi-4-mini" in model_text or "phi4-mini" in model_text:
        return PROMPT_PROFILE_PHI_WORKDESK

    if "qwen3-4b" in model_text or "qwen/qwen3-4b" in model_text:
        return PROMPT_PROFILE_QWEN4_LIGHT

    if "qwen2.5-vl-3b" in model_text:
        return PROMPT_PROFILE_QWEN4_LIGHT

    if "qwen3-8b" in model_text or "qwen/qwen3-8b" in model_text:
        return PROMPT_PROFILE_QWEN8_MEDIUM

    if "qwen2.5-vl-7b" in model_text:
        return PROMPT_PROFILE_QWEN8_MEDIUM

    if "qwen3-30b" in model_text or "qwen/qwen3-30b" in model_text:
        return PROMPT_PROFILE_LARGE

    if "qwen2.5-vl-32b" in model_text:
        return PROMPT_PROFILE_LARGE

    if "llama-3.3-70b" in model_text or "mistral-large" in model_text:
        return PROMPT_PROFILE_EXTREME

    if "dolphin" in model_text:
        return PROMPT_PROFILE_RESTRICTED

    return PROMPT_PROFILE_STANDARD
