from openai import OpenAI

from config import (
    LM_STUDIO_API_KEY,
    LM_STUDIO_BASE_URL,
    LM_STUDIO_MODEL,
    MEMORY_JUDGE_TIMEOUT_SECONDS,
    get_depth_settings,
)
from prompts import build_image_prompt, build_local_prompt, build_web_prompt
from runtime_state import get_runtime_chat_model_id, get_runtime_supports_image_analysis


client = OpenAI(
    base_url=LM_STUDIO_BASE_URL,
    api_key=LM_STUDIO_API_KEY,
)


def active_chat_model_id():
    return get_runtime_chat_model_id(LM_STUDIO_MODEL)


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
        max_tokens=depth_settings["max_answer_tokens"],
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
            "Image analysis requires an image-analysis model. Restart MiddAI and choose Image Analysis Mode in the model launcher."
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
        max_tokens=depth_settings["max_answer_tokens"],
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
        max_tokens=depth_settings["max_answer_tokens"],
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
        max_tokens=depth_settings["max_answer_tokens"],
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
        max_tokens=depth_settings["max_answer_tokens"],
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
