import json
import sys
from pathlib import Path

from config import MIDDAI_DIR


ACTIVE_MODEL_FILE = MIDDAI_DIR / "active_model.json"
RUNTIME_PREFERENCES_FILE = MIDDAI_DIR / "runtime_preferences.json"
LOCAL_ACTIVE_MODEL_FILE = (
    Path(sys.executable).resolve().parent / "active_model.json"
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[1] / "active_model.json"
)

MEMORY_MODE_AUTO = "auto"
MEMORY_MODE_RULES = "rules"
MEMORY_MODE_AI_JUDGE = "ai_judge"
MEMORY_MODE_OFF = "off"
AI_JUDGE_MODEL_ID = "middai-memory-judge"
GPU_OFFLOAD_OFF = "off"
DEFAULT_GPU_OFFLOAD_PERCENT = 50
MIN_GPU_OFFLOAD_PERCENT = 10
MAX_GPU_OFFLOAD_PERCENT = 90
DEFAULT_CONTEXT_LENGTH = 12000
DEFAULT_TEMPERATURE = 0.7
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
LOW_MIN_CONTEXT_LENGTH = 2000
LOW_MAX_CONTEXT_LENGTH = 30000
MID_HIGH_MIN_CONTEXT_LENGTH = 2000
MID_HIGH_MAX_CONTEXT_LENGTH = 70000
EXTREME_MIN_CONTEXT_LENGTH = 10000
EXTREME_MAX_CONTEXT_LENGTH = 200000
MIN_CONTEXT_LENGTH = LOW_MIN_CONTEXT_LENGTH
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
MODEL_CONTEXT_LIMITS = [
    (
        ("llama-3.3-70b", "mistral-large", "mistral large"),
        EXTREME_MIN_CONTEXT_LENGTH,
        EXTREME_MAX_CONTEXT_LENGTH,
    ),
    (
        (
            "qwen3-30b",
            "mistral-7b-instruct-v0.3",
            "mistral 7b instruct",
            "mistral-nemo",
            "mistral nemo",
            "qwen2.5-vl-7b",
            "qwen2_5-vl-7b",
            "qwen2.5-vl-32b",
            "qwen2_5-vl-32b",
            "dolphin-2.8-mistral-7b",
            "dolphin",
        ),
        MID_HIGH_MIN_CONTEXT_LENGTH,
        MID_HIGH_MAX_CONTEXT_LENGTH,
    ),
    (
        (
            "phi-4-mini",
            "phi4-mini",
            "qwen3-4b",
            "gemma-3-4b",
            "gemma 3 4b",
            "ministral-3-3b",
            "ministral 3 3b",
        ),
        LOW_MIN_CONTEXT_LENGTH,
        LOW_MAX_CONTEXT_LENGTH,
    ),
]


def read_active_model():
    for path in (ACTIVE_MODEL_FILE, LOCAL_ACTIVE_MODEL_FILE):
        data = read_active_model_file(path)

        if data:
            return data

    return {}


def write_active_model(data):
    write_active_model_file(ACTIVE_MODEL_FILE, data)
    write_active_model_file(LOCAL_ACTIVE_MODEL_FILE, data, required=False)


def write_active_model_file(path, data, required=True):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = path.with_name(f"{path.name}.tmp")

        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        temp_file.replace(path)
    except OSError:
        if required:
            raise


def read_active_model_file(path):
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def read_runtime_preferences():
    if not RUNTIME_PREFERENCES_FILE.exists():
        return {}

    try:
        with RUNTIME_PREFERENCES_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def write_runtime_preferences(data):
    RUNTIME_PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = RUNTIME_PREFERENCES_FILE.with_name(
        f"{RUNTIME_PREFERENCES_FILE.name}.tmp"
    )

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    temp_file.replace(RUNTIME_PREFERENCES_FILE)


def normalize_temperature(value, fallback=DEFAULT_TEMPERATURE):
    try:
        temperature = float(value)
    except (TypeError, ValueError):
        temperature = float(fallback)

    return round(min(MAX_TEMPERATURE, max(MIN_TEMPERATURE, temperature)), 1)


def get_runtime_temperature():
    preferences = read_runtime_preferences()

    if "temperature" in preferences:
        return normalize_temperature(preferences.get("temperature"))

    active_model = read_active_model()
    return normalize_temperature(active_model.get("temperature"))


def set_runtime_temperature(value):
    temperature = normalize_temperature(value)
    preferences = read_runtime_preferences()
    preferences["temperature"] = temperature
    write_runtime_preferences(preferences)

    active_model = read_active_model()

    if active_model:
        updated_model = dict(active_model)
        updated_model["temperature"] = temperature
        write_active_model(updated_model)

    return temperature


def is_phi_active_model(active_model):
    model_text = active_model_limit_text(active_model)
    return "phi-4-mini" in model_text or "phi4-mini" in model_text


def get_runtime_memory_mode():
    active_model = read_active_model()
    mode = str(active_model.get("memory_mode", MEMORY_MODE_AUTO)).strip().lower()

    if mode == MEMORY_MODE_OFF:
        return MEMORY_MODE_OFF

    if mode in {MEMORY_MODE_RULES, MEMORY_MODE_AI_JUDGE}:
        return mode

    if is_phi_active_model(active_model):
        return MEMORY_MODE_RULES

    return MEMORY_MODE_AI_JUDGE


def get_runtime_ai_judge_enabled():
    return get_runtime_memory_mode() == MEMORY_MODE_AI_JUDGE


def get_runtime_ai_judge_separate_model():
    if not get_runtime_ai_judge_enabled():
        return False

    active_model = read_active_model()
    return bool(active_model.get("ai_judge_separate_model", False))


def get_runtime_memory_judge_model_id(default_model_id="local-model"):
    if get_runtime_ai_judge_separate_model():
        return AI_JUDGE_MODEL_ID

    return get_runtime_chat_model_id(default_model_id)


def normalize_gpu_offload_percent(value, fallback=DEFAULT_GPU_OFFLOAD_PERCENT):
    try:
        percent = int(round(float(value)))
    except (TypeError, ValueError):
        percent = int(fallback)

    return min(
        MAX_GPU_OFFLOAD_PERCENT,
        max(MIN_GPU_OFFLOAD_PERCENT, percent),
    )


def normalize_gpu_offload(value):
    normalized = str(value or "").strip().casefold()

    if normalized in {"", "off", "false", "none", "0", "0%"}:
        return GPU_OFFLOAD_OFF

    try:
        numeric_value = float(normalized.rstrip("%"))
    except ValueError:
        return GPU_OFFLOAD_OFF

    percent = numeric_value * 100 if numeric_value <= 1 else numeric_value

    if not MIN_GPU_OFFLOAD_PERCENT <= percent <= MAX_GPU_OFFLOAD_PERCENT:
        return GPU_OFFLOAD_OFF

    return f"{round(percent / 100, 2):g}"


def get_runtime_gpu_offload():
    active_model = read_active_model()

    if not active_model.get("gpu_offload_user_override"):
        return GPU_OFFLOAD_OFF

    return normalize_gpu_offload(active_model.get("gpu_offload"))


def get_runtime_gpu_offload_percent():
    active_model = read_active_model()

    if "gpu_offload_percent" in active_model:
        return normalize_gpu_offload_percent(
            active_model.get("gpu_offload_percent")
        )

    gpu_offload = normalize_gpu_offload(active_model.get("gpu_offload"))

    if gpu_offload == GPU_OFFLOAD_OFF:
        return DEFAULT_GPU_OFFLOAD_PERCENT

    return normalize_gpu_offload_percent(float(gpu_offload) * 100)


def get_active_model_label():
    active_model = read_active_model()
    return str(active_model.get("label") or active_model.get("model_name") or "").strip()


def normalize_context_length(value, fallback=DEFAULT_CONTEXT_LENGTH, minimum=LOW_MIN_CONTEXT_LENGTH):
    try:
        context_length = int(value)
    except (TypeError, ValueError):
        context_length = int(fallback)

    return max(minimum, context_length)


def active_model_limit_text(active_model):
    return " ".join(
        str(active_model.get(key, ""))
        for key in ("label", "model_name", "download_query", "model_key", "chat_model_id")
    ).casefold()


def infer_context_range(active_model):
    model_text = active_model_limit_text(active_model)

    for terms, min_context_length, max_context_length in MODEL_CONTEXT_LIMITS:
        if any(term in model_text for term in terms):
            return min_context_length, max_context_length

    return None


def infer_min_context_length(active_model):
    context_range = infer_context_range(active_model)

    if context_range:
        return context_range[0]

    explicit_min = active_model.get("min_context_length")

    if explicit_min is not None:
        return normalize_context_length(explicit_min, fallback=LOW_MIN_CONTEXT_LENGTH)

    return LOW_MIN_CONTEXT_LENGTH


def infer_max_context_length(active_model):
    context_range = infer_context_range(active_model)

    if context_range:
        return context_range[1]

    min_context_length = infer_min_context_length(active_model)
    explicit_max = active_model.get("max_context_length")

    if explicit_max is not None:
        return normalize_context_length(
            explicit_max,
            fallback=DEFAULT_CONTEXT_LENGTH,
            minimum=min_context_length,
        )

    return max(
        normalize_context_length(
            active_model.get("context_length"),
            minimum=min_context_length,
        ),
        DEFAULT_CONTEXT_LENGTH,
    )


def get_runtime_chat_model_id(default_model_id="local-model"):
    active_model = read_active_model()
    model_id = str(active_model.get("chat_model_id") or "").strip()

    return model_id or default_model_id


def get_runtime_context_length():
    active_model = read_active_model()

    if not active_model:
        return DEFAULT_CONTEXT_LENGTH

    min_context_length = infer_min_context_length(active_model)
    max_context_length = infer_max_context_length(active_model)
    context_length = normalize_context_length(
        active_model.get("context_length"),
        fallback=DEFAULT_CONTEXT_LENGTH,
        minimum=min_context_length,
    )

    return min(context_length, max_context_length)


def get_runtime_supports_image_analysis():
    active_model = read_active_model()

    if bool(active_model.get("image_analysis")):
        return True

    model_text = get_active_model_text()
    image_capable_terms = (
        "qwen2.5-vl",
        "qwen2_5-vl",
        "gemma-3-4b",
        "gemma 3 4b",
        "gemma-3-4b-it",
        "vision",
    )
    return any(term in model_text for term in image_capable_terms)


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
