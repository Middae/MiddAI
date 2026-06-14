from config import get_depth_settings
from persona import get_assistant_persona


DEPTH_PRIORITY_RULE = """
Response speed priority:
- The selected response speed instruction overrides assistant personality, sarcasm, memory, examples, and formatting habits.
- Keep the answer within the selected speed even if the active assistant persona would normally be more talkative.
- Finish cleanly in a complete sentence. Do not trail off mid-sentence.
""".strip()


PLANT_SAFETY_RULE = """
Plant, mushroom, foraging, and survival safety note:
- If the user asks whether a plant, fungus, berry, leaf, root, seed, or wild food is edible, poisonous, medicinal, safe to eat, safe to touch, or safe for survival use, answer the question normally first using the available evidence or visible features.
- Do not refuse or weaken the main answer only because the topic involves edible, poisonous, medicinal, or survival use.
- After the main answer, finish with a brief safety warning that identification can be uncertain, some species have dangerous lookalikes, and the user should verify with a trusted field guide, local expert, or professional before consuming, touching, or using it medicinally.
"""

APP_CAPABILITIES = """
MiddAI app capabilities:
- You are MiddAI, the assistant inside this self-hosted app.
- MiddAI can chat locally through the selected LM Studio model.
- MiddAI can search the web when Search mode is selected or when the app has routed a direct search request.
- MiddAI can display web image thumbnails when image search results are supplied by the app.
- MiddAI can analyse attached documents when their extracted text is supplied in the prompt.
- MiddAI can analyse attached images and screenshots only when an image-analysis model is active and the image is supplied in the prompt.
- MiddAI has local memory, but memory is background context only. Use it only when relevant.
- You cannot see the user's screen, the MiddAI UI, files, photos, or the outside world unless the user attaches or supplies them in the current message.
- If the user asks whether you want to see the UI, a photo, or a screenshot, explain that they can attach it and you can analyse it if image analysis is active.
"""


def format_messages(messages):
    if not messages:
        return "None."

    lines = []

    for number, message in enumerate(messages, start=1):
        role = message["role"].title()
        content = message["content"]
        lines.append(f"{number}. {role}: {content}")

    return "\n".join(lines)


def format_profile(profile):
    if not profile:
        return "None."

    lines = []
    name = profile.get("name")

    if name:
        lines.append(f"- Name: {name}")

    for place in profile.get("places", []):
        lines.append(f"- Place: {place}")

    for preference in profile.get("preferences", []):
        lines.append(f"- Preference: {preference}")

    for fact in profile.get("important_facts", []):
        lines.append(f"- Important fact: {fact}")

    for item in profile.get("objects", []):
        lines.append(f"- Object: {item}")

    for person in profile.get("people", []):
        lines.append(f"- Person: {person}")

    for profession in profile.get("professions", []):
        lines.append(f"- Profession: {profession}")

    for project in profile.get("projects", []):
        lines.append(f"- Project: {project}")

    for context in profile.get("current_context", []):
        lines.append(f"- Current context: {context}")

    return "\n".join(lines) if lines else "None."


def format_previous_chats(previous_chats):
    if not previous_chats:
        return "Not included for this message."

    sections = []

    for number, chat in enumerate(previous_chats, start=1):
        ended_at = chat.get("ended_at") or "unknown time"
        title = chat.get("title") or "Past chat"
        summary = chat.get("summary") or "No summary available."
        tags = ", ".join(chat.get("tags") or []) or "None"
        sections.append(
            f"""Past-chat continuity summary {number}
Title: {title}
Ended: {ended_at}
Tags: {tags}
Summary: {summary}"""
        )

    return "\n\n".join(sections)


def format_memory_items(items):
    if not items:
        return "None."

    lines = []

    for number, item in enumerate(items, start=1):
        item_type = item.get("type", "memory").replace("_", " ")
        text = item.get("text", "")
        lines.append(f"{number}. {item_type}: {text}")

    return "\n".join(lines)


def format_memory(memory):
    profile = memory.get("profile", {}) if isinstance(memory, dict) else {}
    current_messages = memory.get("current_messages", []) if isinstance(memory, dict) else []
    previous_chats = memory.get("previous_chats", []) if isinstance(memory, dict) else []
    current_memories = memory.get("current_memories", []) if isinstance(memory, dict) else []
    mid_memories = memory.get("mid_memories", []) if isinstance(memory, dict) else []
    long_memories = memory.get("long_memories", []) if isinstance(memory, dict) else []

    return f"""
Known user profile:
{format_profile(profile)}

Current chat context:
{format_messages(current_messages)}

Current temporary memory:
{format_memory_items(current_memories)}

Relevant mid-term memory:
{format_memory_items(mid_memories)}

Relevant long-term memory:
{format_memory_items(long_memories)}

Previous chat context:
{format_previous_chats(previous_chats)}
"""


def format_image_results(image_results):
    if not image_results:
        return "No image thumbnails selected."

    lines = []

    for number, image in enumerate(image_results, start=1):
        title = image.get("title") or "Image result"
        source_name = image.get("source_name") or "Unknown source"
        source_url = image.get("source_url") or image.get("image_url") or ""
        lines.append(f"{number}. {title} - {source_name} - {source_url}")

    return "\n".join(lines)


def format_attached_documents(attached_documents):
    if not attached_documents:
        return "No attached documents."

    sections = []

    for number, document in enumerate(attached_documents, start=1):
        truncated_note = " yes" if document.get("truncated") else " no"
        sections.append(
            f"""Attached document {number}
File name: {document.get("name", "attachment")}
Characters included: {document.get("chars", 0)}
Truncated: {truncated_note}
Text:
{document.get("text", "")}
"""
        )

    return "\n\n".join(sections)


def format_attached_images(attached_images):
    if not attached_images:
        return "No attached images."

    lines = []

    for number, image in enumerate(attached_images, start=1):
        lines.append(
            (
                f"{number}. {image.get('name', 'image')} "
                f"({image.get('mime_type', 'image')}, {image.get('size', 0)} bytes)"
            )
        )

    return "\n".join(lines)


def build_web_prompt(
    question,
    evidence,
    depth,
    memory_messages,
    image_results=None,
    attached_documents=None,
):
    depth_settings = get_depth_settings(depth)
    max_text_per_source = depth_settings["max_text_per_source"]
    style_instruction = depth_settings["style_instruction"]
    persona = get_assistant_persona()
    memory_text = format_memory(memory_messages)
    image_results_text = format_image_results(image_results)
    attached_documents_text = format_attached_documents(attached_documents)
    sources_text = ""

    for number, source in enumerate(evidence, start=1):
        sources_text += f"""
Source {number}
Title: {source["title"]}
URL: {source["url"]}
Text:
{source["text"][:max_text_per_source]}
"""

    return f"""
You are answering the current user question using web evidence collected by a Python program.

Assistant behavior instructions:
{persona["instructions"]}

Assistant personality:
{persona["personality"]}

{APP_CAPABILITIES}

Conversation context for continuity only:
{memory_text}

Evidence:
{sources_text}

Image thumbnails selected by the app:
{image_results_text}

User-attached documents for this message:
{attached_documents_text}

Current user question to answer now:
{question}

Instructions:
- The current user question is the only thing to answer.
- If user-attached documents are provided, treat them as local files supplied by the user for this message.
- When the user asks you to analyse, summarize, explain, compare, extract, rewrite, or answer from an attached document, prioritize the attached document text.
- Do not claim to have read parts of an attached file that are not included above.
- Use current chat context mainly to understand follow-ups, pronouns, and what was just said.
- Use current temporary memory for recent search/context follow-ups, but do not treat it as permanent truth.
- Use selected past-chat summaries only for conversation continuity.
- Only use memory details that are directly relevant to the current user question.
- Do not bring up profile details, current context, or previous chats unless the user asks about them or they are necessary for the answer.
- Past-chat continuity contains compact relevant summaries, never complete archived chats. Use a supplied summary only when it helps answer the current request.
- If memory contains the user's name, remember it quietly. Do not greet or re-introduce them unless the current message is a greeting or introduction.
- If the current user message corrects memory, such as "I am not called..." or "that is not my name", obey the current correction for this reply and do not use the contradicted memory detail.
- Do not answer an older memory message.
- Do not merely repeat or closely paraphrase the current user message. Respond to what it means.
- Do not repeat an older assistant message unless the user directly asks you to.
- Answer only using the evidence above.
- For current or factual claims, the web evidence is more important than chat memory.
- If the evidence does not support an answer, say that the evidence I found is not enough.
- Do not pretend you verified anything that is not supported by the evidence.
- If image thumbnails are listed above, MiddAI will display them below your answer. Do not say you cannot provide or show images. Briefly answer and refer to the thumbnails below.
- If no image thumbnails are listed, do not mention images unless the user asked about them.
- {PLANT_SAFETY_RULE.strip()}
- {DEPTH_PRIORITY_RULE}
- {style_instruction}
- Include a short "Sources" section listing the URLs you used.
"""


def build_local_prompt(message, depth, memory_messages, attached_documents=None):
    depth_settings = get_depth_settings(depth)
    style_instruction = depth_settings["style_instruction"]
    persona = get_assistant_persona()
    memory_text = format_memory(memory_messages)
    attached_documents_text = format_attached_documents(attached_documents)

    return f"""
You are a helpful local assistant.

Assistant behavior instructions:
{persona["instructions"]}

Assistant personality:
{persona["personality"]}

{APP_CAPABILITIES}

Conversation context for continuity only:
{memory_text}

User-attached documents for this message:
{attached_documents_text}

Current user message to answer now:
{message}

Instructions:
- The current user message is the only thing to answer.
- If user-attached documents are provided, treat them as local files supplied by the user for this message.
- When the user asks you to analyse, summarize, explain, compare, extract, rewrite, or answer from an attached document, prioritize the attached document text.
- Do not claim to have read parts of an attached file that are not included above.
- Use current chat context mainly to understand follow-ups, pronouns, and what was just said.
- Use current temporary memory for recent search/context follow-ups, but do not treat it as permanent truth.
- Use selected past-chat summaries only for conversation continuity.
- Only use memory details that are directly relevant to the current user message.
- Do not bring up profile details, current context, or previous chats unless the user asks about them or they are necessary for the answer.
- Past-chat continuity contains compact relevant summaries, never complete archived chats. Use a supplied summary only when it helps answer the current request.
- If the current user message is just an introduction, greeting, correction, preference, or personal fact, acknowledge that message directly and do not continue an older topic.
- If memory contains the user's name, remember it quietly. Do not greet or re-introduce them unless the current message is a greeting or introduction.
- If the current user message corrects memory, such as "I am not called..." or "that is not my name", obey the current correction for this reply and do not use the contradicted memory detail.
- Do not answer an older memory message.
- Do not merely repeat or closely paraphrase the current user message. If it is a personal fact, acknowledge it naturally or ask one relevant follow-up.
- Do not repeat an older assistant message unless the user directly asks you to.
- Answer conversationally from your existing knowledge.
- Do not claim that you searched the web.
- {PLANT_SAFETY_RULE.strip()}
- {DEPTH_PRIORITY_RULE}
- {style_instruction}
"""


def build_image_prompt(
    message,
    depth,
    memory_messages,
    attached_documents=None,
    attached_images=None,
):
    depth_settings = get_depth_settings(depth)
    style_instruction = depth_settings["style_instruction"]
    persona = get_assistant_persona()
    memory_text = format_memory(memory_messages)
    attached_documents_text = format_attached_documents(attached_documents)
    attached_images_text = format_attached_images(attached_images)

    return f"""
You are a helpful local vision assistant. The user has attached image files for this current message.

Assistant behavior instructions:
{persona["instructions"]}

Assistant personality:
{persona["personality"]}

{APP_CAPABILITIES}

Conversation context for continuity only:
{memory_text}

Attached images:
{attached_images_text}

User-attached documents for this message:
{attached_documents_text}

Current user message to answer now:
{message}

Instructions:
- The current user message and attached images are the only things to answer.
- For image or screenshot analysis, do not start with a greeting. Answer the requested analysis directly.
- If the user requests a specific format, such as paragraphs and bullet points, follow that format closely.
- Analyse what is visible in the attached images. Do not claim certainty about anything that is not visible.
- If the attached image is a screenshot of MiddAI, another app, a website, or any user interface, treat it as a UI screenshot: read visible text, identify buttons, panels, layout, selected states, errors, and visual problems. Do not describe it as a generic forest, game, or nature scene unless that is the actual UI content.
- If the user asks what you think of MiddAI or the UI, answer as MiddAI analysing the supplied screenshot. You can discuss the visible UI because the user attached it.
- If the user asks for plant, fungus, wildlife, object, place, condition, or damage identification, describe the visible evidence before giving likely possibilities.
- For plants, break down visible parts when possible: leaves, leaf edge, veins, stem, flowers, petals, fruit, seeds, colour, growth habit, surrounding habitat, and any missing angles needed for a better ID.
- If user-attached documents are provided, use them as extra local context for this message.
- Use current chat context only for follow-ups, pronouns, and what was just said.
- Only use memory details that are directly relevant to the current request.
- Do not bring up profile details, current context, or previous chats unless necessary.
- If the current user message corrects memory, such as "I am not called..." or "that is not my name", obey the current correction for this reply and do not use the contradicted memory detail.
- Do not answer an older memory message.
- Do not merely repeat or closely paraphrase the current user message. Respond to what it means.
- Do not repeat an older assistant message unless the user directly asks you to.
- If you are unsure, say what is uncertain and what additional photo or information would help.
- {PLANT_SAFETY_RULE.strip()}
- {DEPTH_PRIORITY_RULE}
- {style_instruction}
"""
