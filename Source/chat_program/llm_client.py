from openai import OpenAI

from config import (
    LM_STUDIO_API_KEY,
    LM_STUDIO_BASE_URL,
    LM_STUDIO_MODEL,
    MEMORY_JUDGE_TIMEOUT_SECONDS,
    get_depth_settings,
)
from prompts import build_image_prompt, build_local_prompt, build_web_prompt
from runtime_state import (
    get_runtime_chat_model_id,
    get_runtime_context_length,
    get_runtime_supports_image_analysis,
)


client = OpenAI(
    base_url=LM_STUDIO_BASE_URL,
    api_key=LM_STUDIO_API_KEY,
)


PROMPT_CHARS_PER_TOKEN = 4
COMPLETION_CONTEXT_SAFETY_TOKENS = 160
MIN_COMPLETION_TOKENS = 32


def active_chat_model_id():
    return get_runtime_chat_model_id(LM_STUDIO_MODEL)


def estimate_prompt_tokens(prompt):
    if isinstance(prompt, str):
        return max(1, (len(prompt) + PROMPT_CHARS_PER_TOKEN - 1) // PROMPT_CHARS_PER_TOKEN)

    return 1


def effective_max_tokens(prompt, depth_settings):
    preset_max_tokens = int(depth_settings["max_answer_tokens"])
    context_length = get_runtime_context_length()
    available_tokens = (
        context_length
        - estimate_prompt_tokens(prompt)
        - COMPLETION_CONTEXT_SAFETY_TOKENS
    )

    if available_tokens <= MIN_COMPLETION_TOKENS:
        return min(preset_max_tokens, MIN_COMPLETION_TOKENS)

    return max(MIN_COMPLETION_TOKENS, min(preset_max_tokens, available_tokens))


def stream_completion(prompt, depth):
    depth_settings = get_depth_settings(depth)

    response = client.chat.completions.create(
        model=active_chat_model_id(),
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=effective_max_tokens(prompt, depth_settings),
        stream=True,
    )

    for chunk in response:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        content = getattr(delta, "content", None)

        if content:
            yield content


def image_content_blocks(prompt, attached_images):
    blocks = [{"type": "text", "text": prompt}]

    for image in attached_images or []:
        mime_type = image.get("mime_type") or "image/png"
        data_base64 = image.get("data_base64") or ""

        if not data_base64:
            continue

        blocks.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{data_base64}",
                },
            }
        )

    return blocks


def ensure_image_analysis_model():
    if not get_runtime_supports_image_analysis():
        raise RuntimeError(
            "Image analysis requires an image-capable model. Restart MiddAI and choose Gemma 3 4B or an Image Analysis model in the launcher."
        )


def stream_image_completion(prompt, depth, attached_images):
    ensure_image_analysis_model()
    depth_settings = get_depth_settings(depth)

    response = client.chat.completions.create(
        model=active_chat_model_id(),
        messages=[
            {
                "role": "user",
                "content": image_content_blocks(prompt, attached_images),
            }
        ],
        max_tokens=effective_max_tokens(prompt, depth_settings),
        stream=True,
    )

    for chunk in response:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        content = getattr(delta, "content", None)

        if content:
            yield content


def ask_model(
    question,
    evidence,
    depth,
    memory_messages,
    image_results=None,
    attached_documents=None,
):
    prompt = build_web_prompt(
        question,
        evidence,
        depth,
        memory_messages,
        image_results=image_results,
        attached_documents=attached_documents,
    )
    depth_settings = get_depth_settings(depth)

    response = client.chat.completions.create(
        model=active_chat_model_id(),
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=effective_max_tokens(prompt, depth_settings),
    )

    return response.choices[0].message.content


def stream_model(
    question,
    evidence,
    depth,
    memory_messages,
    image_results=None,
    attached_documents=None,
):
    prompt = build_web_prompt(
        question,
        evidence,
        depth,
        memory_messages,
        image_results=image_results,
        attached_documents=attached_documents,
    )

    yield from stream_completion(prompt, depth)


def ask_model_locally(message, depth, memory_messages, attached_documents=None):
    prompt = build_local_prompt(
        message,
        depth,
        memory_messages,
        attached_documents=attached_documents,
    )
    depth_settings = get_depth_settings(depth)

    response = client.chat.completions.create(
        model=active_chat_model_id(),
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=effective_max_tokens(prompt, depth_settings),
    )

    return response.choices[0].message.content


def stream_model_locally(message, depth, memory_messages, attached_documents=None):
    prompt = build_local_prompt(
        message,
        depth,
        memory_messages,
        attached_documents=attached_documents,
    )
    yield from stream_completion(prompt, depth)


def ask_model_with_images(
    message,
    depth,
    memory_messages,
    attached_documents=None,
    attached_images=None,
):
    ensure_image_analysis_model()
    prompt = build_image_prompt(
        message,
        depth,
        memory_messages,
        attached_documents=attached_documents,
        attached_images=attached_images,
    )
    depth_settings = get_depth_settings(depth)

    response = client.chat.completions.create(
        model=active_chat_model_id(),
        messages=[
            {
                "role": "user",
                "content": image_content_blocks(prompt, attached_images),
            }
        ],
        max_tokens=effective_max_tokens(prompt, depth_settings),
    )

    return response.choices[0].message.content


def stream_model_with_images(
    message,
    depth,
    memory_messages,
    attached_documents=None,
    attached_images=None,
):
    prompt = build_image_prompt(
        message,
        depth,
        memory_messages,
        attached_documents=attached_documents,
        attached_images=attached_images,
    )
    yield from stream_image_completion(prompt, depth, attached_images)


def ask_memory_judge(prompt):
    response = client.chat.completions.create(
        model=active_chat_model_id(),
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0,
        max_tokens=900,
        timeout=MEMORY_JUDGE_TIMEOUT_SECONDS,
    )

    return response.choices[0].message.content
