from ddgs import DDGS
import re
import requests
import sys
import trafilatura
from urllib.parse import urlparse

from config import (
    BLOCKED_DOMAINS,
    BLOCKED_URL_PARTS,
    MIN_KEYWORD_LENGTH,
    get_depth_settings,
)
from runtime_state import get_runtime_context_length


REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}
SEARCH_BACKENDS = ("auto", "brave", "bing", "mojeek")
IMAGE_SEARCH_BACKENDS = ("auto", "bing", "brave", "mojeek")
PHI_WORKDESK_PROFILE = "phi_workdesk"
QWEN4_LIGHT_PROFILE = "qwen4_light"
QWEN8_MEDIUM_PROFILE = "qwen8_medium"
LARGE_MODEL_PROFILE = "large_model"
EXTREME_MODEL_PROFILE = "extreme_model"
RESTRICTED_MODEL_PROFILE = "restricted_model"
STANDARD_PROFILE = "standard"
IMAGE_CANDIDATE_LIMIT = 24
IMAGE_RESULT_LIMIT = 9
MIN_IMAGE_WIDTH = 180
MIN_IMAGE_HEIGHT = 120
SUPPORTED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
REJECTED_IMAGE_EXTENSIONS = {"bmp", "gif", "ico", "svg"}
JUNK_IMAGE_WORDS = (
    "avatar",
    "button",
    "favicon",
    "icon",
    "logo",
    "pixel",
    "placeholder",
    "sprite",
)
IMAGE_QUERY_STOPWORDS = {
    "image",
    "images",
    "photo",
    "photos",
    "picture",
    "pictures",
    "pic",
    "pics",
    "show",
    "search",
    "find",
    "look",
    "online",
    "web",
    "internet",
    "for",
    "the",
    "and",
    "what",
    "does",
    "like",
}
CONTEXT_PROMPT_RESERVE_TOKENS = 1100
CONTEXT_COMPLETION_SAFETY_TOKENS = 180
MIN_CONTEXT_SOURCE_CHARS = 320
MIN_CONTEXT_SOURCE_COUNT = 1
SEARCH_BUDGETS = {
    PHI_WORKDESK_PROFILE: {
        "instant": {"max_results": 4, "max_good_sources": 1, "include_images": False},
        "quick": {"max_results": 8, "max_good_sources": 2, "include_images": True},
        "balanced": {"max_results": 12, "max_good_sources": 3, "include_images": True},
        "deep": {"max_results": 16, "max_good_sources": 3, "include_images": True},
    },
    QWEN4_LIGHT_PROFILE: {
        "instant": {"max_results": 4, "max_good_sources": 1, "include_images": False},
        "quick": {"max_results": 8, "max_good_sources": 2, "include_images": True},
        "balanced": {"max_results": 14, "max_good_sources": 3, "include_images": True},
        "deep": {"max_results": 20, "max_good_sources": 4, "include_images": True},
    },
    QWEN8_MEDIUM_PROFILE: {
        "instant": {"max_results": 6, "max_good_sources": 2, "include_images": False},
        "quick": {"max_results": 14, "max_good_sources": 3, "include_images": True},
        "balanced": {"max_results": 24, "max_good_sources": 5, "include_images": True},
        "deep": {"max_results": 40, "max_good_sources": 8, "include_images": True},
    },
    STANDARD_PROFILE: {
        "instant": {"max_results": 6, "max_good_sources": 2, "include_images": False},
        "quick": {"max_results": 14, "max_good_sources": 3, "include_images": True},
        "balanced": {"max_results": 24, "max_good_sources": 5, "include_images": True},
        "deep": {"max_results": 40, "max_good_sources": 8, "include_images": True},
    },
    LARGE_MODEL_PROFILE: {
        "instant": {"max_results": 6, "max_good_sources": 2, "include_images": False},
        "quick": {"max_results": 16, "max_good_sources": 3, "include_images": True},
        "balanced": {"max_results": 30, "max_good_sources": 6, "include_images": True},
        "deep": {"max_results": 40, "max_good_sources": 8, "include_images": True},
    },
    EXTREME_MODEL_PROFILE: {
        "instant": {"max_results": 6, "max_good_sources": 2, "include_images": False},
        "quick": {"max_results": 16, "max_good_sources": 3, "include_images": True},
        "balanced": {"max_results": 30, "max_good_sources": 6, "include_images": True},
        "deep": {"max_results": 40, "max_good_sources": 8, "include_images": True},
    },
    RESTRICTED_MODEL_PROFILE: {
        "instant": {"max_results": 4, "max_good_sources": 1, "include_images": False},
        "quick": {"max_results": 8, "max_good_sources": 2, "include_images": True},
        "balanced": {"max_results": 12, "max_good_sources": 3, "include_images": True},
        "deep": {"max_results": 16, "max_good_sources": 4, "include_images": True},
    },
}


def safe_log(message):
    output = getattr(sys, "stdout", None)
    encoding = getattr(output, "encoding", None) or "utf-8"
    safe_message = str(message).encode(encoding, errors="replace").decode(encoding)

    if output is not None:
        print(safe_message)


def search_limits(depth, prompt_profile="standard"):
    depth_settings = get_depth_settings(depth)
    limits = dict(depth_settings)
    normalized_depth = (depth or "balanced").lower()
    profile_budgets = SEARCH_BUDGETS.get(prompt_profile, SEARCH_BUDGETS[STANDARD_PROFILE])
    budget = profile_budgets.get(normalized_depth, profile_budgets["balanced"])

    limits.update(budget)
    apply_context_budget(limits)

    return limits


def safe_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def apply_context_budget(limits):
    context_length = get_runtime_context_length()
    max_answer_tokens = safe_int(limits.get("max_answer_tokens"), 180)
    max_good_sources = max(
        MIN_CONTEXT_SOURCE_COUNT,
        safe_int(limits.get("max_good_sources"), MIN_CONTEXT_SOURCE_COUNT),
    )
    max_text_per_source = max(
        MIN_CONTEXT_SOURCE_CHARS,
        safe_int(limits.get("max_text_per_source"), MIN_CONTEXT_SOURCE_CHARS),
    )
    available_source_tokens = (
        context_length
        - max_answer_tokens
        - CONTEXT_PROMPT_RESERVE_TOKENS
        - CONTEXT_COMPLETION_SAFETY_TOKENS
    )
    source_char_budget = max(
        MIN_CONTEXT_SOURCE_CHARS,
        available_source_tokens * 4,
    )
    requested_source_chars = max_good_sources * max_text_per_source

    if requested_source_chars <= source_char_budget:
        return

    adjusted_source_count = max(
        MIN_CONTEXT_SOURCE_COUNT,
        min(max_good_sources, source_char_budget // MIN_CONTEXT_SOURCE_CHARS),
    )
    adjusted_text_per_source = max(
        MIN_CONTEXT_SOURCE_CHARS,
        source_char_budget // adjusted_source_count,
    )

    limits["max_good_sources"] = int(adjusted_source_count)
    limits["max_text_per_source"] = int(min(max_text_per_source, adjusted_text_per_source))
    limits["max_results"] = int(
        min(
            safe_int(limits.get("max_results"), limits["max_good_sources"]),
            max(limits["max_good_sources"], limits["max_good_sources"] * 4),
        )
    )


def should_search_images(depth, prompt_profile="standard"):
    return bool(search_limits(depth, prompt_profile).get("include_images", True))


def search_web(query, depth, prompt_profile="standard"):
    search_settings = search_limits(depth, prompt_profile)
    max_results = search_settings["max_results"]
    errors = []

    for backend in SEARCH_BACKENDS:
        try:
            with DDGS(timeout=20) as ddgs:
                results = list(
                    ddgs.text(
                        query,
                        max_results=max_results,
                        backend=backend,
                    )
                )
        except Exception as error:
            errors.append(f"{backend}: {error}")
            safe_log(f"Search backend failed ({backend}): {error}")
            continue

        if results:
            if backend != "auto":
                safe_log(f"Search fallback backend used: {backend}")

            return results

        errors.append(f"{backend}: no results")

    raise RuntimeError("Search backends failed. " + " | ".join(errors))


def is_http_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def clean_whitespace(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_int(value):
    try:
        return int(str(value).split(".")[0])
    except (TypeError, ValueError):
        return 0


def get_domain(url):
    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def get_image_extension(url):
    path = urlparse(url).path.lower()

    if "." not in path:
        return ""

    return path.rsplit(".", 1)[-1]


def looks_like_junk_image(title, image_url, source_url):
    combined = " ".join((title, image_url, source_url)).lower()
    return any(word in combined for word in JUNK_IMAGE_WORDS)


def singular_image_terms(word):
    terms = {word}

    if word.endswith("ies") and len(word) > 4:
        terms.add(f"{word[:-3]}y")
    elif word.endswith("es") and len(word) > 4:
        terms.add(word[:-2])
    elif word.endswith("s") and len(word) > 3:
        terms.add(word[:-1])

    return terms


def get_image_query_terms(query):
    terms = set()

    for word in re.findall(r"[a-zA-Z0-9]+", (query or "").lower()):
        if len(word) < 3 or word in IMAGE_QUERY_STOPWORDS:
            continue

        terms.update(singular_image_terms(word))

    return terms


def count_image_query_matches(text, query_terms):
    normalized_text = (text or "").lower()
    return sum(1 for term in query_terms if term in normalized_text)


def normalize_image_result(result, query_terms=None):
    title = clean_whitespace(result.get("title"))
    image_url = clean_whitespace(
        result.get("image")
        or result.get("image_url")
        or result.get("content")
    )
    thumbnail_url = clean_whitespace(
        result.get("thumbnail")
        or result.get("thumbnail_url")
        or result.get("image")
    )
    source_url = clean_whitespace(
        result.get("url")
        or result.get("source_url")
        or result.get("href")
    )
    width = parse_int(result.get("width"))
    height = parse_int(result.get("height"))

    if not image_url or not source_url:
        return None

    if not is_http_url(image_url) or not is_http_url(source_url):
        return None

    if thumbnail_url and not is_http_url(thumbnail_url):
        thumbnail_url = image_url

    extension = get_image_extension(image_url)

    if extension in REJECTED_IMAGE_EXTENSIONS:
        return None

    if extension and extension not in SUPPORTED_IMAGE_EXTENSIONS:
        return None

    if width and width < MIN_IMAGE_WIDTH:
        return None

    if height and height < MIN_IMAGE_HEIGHT:
        return None

    if looks_like_junk_image(title, image_url, source_url):
        return None

    source_name = clean_whitespace(result.get("source")) or get_domain(source_url)

    if not title:
        title = source_name or "Image result"

    searchable_text = " ".join((title, image_url, source_url, source_name))
    query_match_count = count_image_query_matches(searchable_text, query_terms or set())

    if query_terms and query_match_count == 0:
        return None

    score = 0

    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        score += 20

    if width and height:
        area = width * height
        score += min(area // 50000, 30)

    if thumbnail_url:
        score += 6

    if title:
        score += 6

    if source_name:
        score += 4

    score += query_match_count * 18

    return {
        "title": title,
        "image_url": image_url,
        "thumbnail_url": thumbnail_url or image_url,
        "source_url": source_url,
        "source_name": source_name,
        "width": width,
        "height": height,
        "_score": score,
        "_source_domain": get_domain(source_url),
    }


def select_best_images(results, max_images=IMAGE_RESULT_LIMIT):
    return select_best_images_for_query("", results, max_images=max_images)


def select_best_images_for_query(query, results, max_images=IMAGE_RESULT_LIMIT):
    query_terms = get_image_query_terms(query)
    seen_images = set()
    seen_sources = set()
    candidates = []

    for result in results:
        candidate = normalize_image_result(result, query_terms=query_terms)

        if not candidate:
            continue

        image_key = candidate["image_url"].lower()
        source_key = candidate["source_url"].lower()

        if image_key in seen_images or source_key in seen_sources:
            continue

        seen_images.add(image_key)
        seen_sources.add(source_key)
        candidates.append(candidate)

    candidates.sort(key=lambda item: item["_score"], reverse=True)

    selected = []
    delayed = []
    selected_domains = set()

    for candidate in candidates:
        source_domain = candidate["_source_domain"]

        if source_domain in selected_domains:
            delayed.append(candidate)
            continue

        selected.append(candidate)
        selected_domains.add(source_domain)

        if len(selected) >= max_images:
            break

    if len(selected) < max_images:
        for candidate in delayed:
            selected.append(candidate)

            if len(selected) >= max_images:
                break

    public_fields = (
        "title",
        "image_url",
        "thumbnail_url",
        "source_url",
        "source_name",
        "width",
        "height",
    )
    return [
        {field: candidate[field] for field in public_fields}
        for candidate in selected[:max_images]
    ]


def search_images(query, max_images=IMAGE_RESULT_LIMIT):
    errors = []

    for backend in IMAGE_SEARCH_BACKENDS:
        try:
            with DDGS(timeout=12) as ddgs:
                results = list(
                    ddgs.images(
                        query,
                        max_results=IMAGE_CANDIDATE_LIMIT,
                        backend=backend,
                    )
                )
        except Exception as error:
            errors.append(f"{backend}: {error}")
            safe_log(f"Image search backend failed ({backend}): {error}")
            continue

        images = select_best_images_for_query(query, results, max_images=max_images)

        if images:
            if backend != "auto":
                safe_log(f"Image search fallback backend used: {backend}")

            return images

        errors.append(f"{backend}: no usable images")

    if errors:
        safe_log("Image search returned no usable images. " + " | ".join(errors))

    return []


def is_blocked_url(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    normalized_url = url.lower()

    for blocked_domain in BLOCKED_DOMAINS:
        if domain == blocked_domain or domain.endswith(f".{blocked_domain}"):
            return True

    for blocked_part in BLOCKED_URL_PARTS:
        if blocked_part.lower() in normalized_url:
            return True

    return False


def get_keywords(question):
    words = re.findall(r"[a-zA-Z0-9]+", question.lower())
    ignored_words = {
        "about",
        "after",
        "also",
        "and",
        "are",
        "can",
        "could",
        "does",
        "for",
        "from",
        "have",
        "how",
        "into",
        "is",
        "it",
        "its",
        "latest",
        "more",
        "new",
        "news",
        "of",
        "on",
        "or",
        "please",
        "should",
        "show",
        "tell",
        "than",
        "that",
        "the",
        "their",
        "there",
        "they",
        "this",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "would",
        "you",
    }
    return [
        word
        for word in words
        if len(word) >= MIN_KEYWORD_LENGTH and word not in ignored_words
    ]


def get_result_summary(result):
    summary = (
        result.get("body")
        or result.get("description")
        or result.get("snippet")
        or ""
    )

    return re.sub(r"\s+", " ", summary).strip()


def download_page(url):
    downloaded = trafilatura.fetch_url(url)

    if downloaded:
        return downloaded

    response = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def pick_relevant_text(text, question, depth, prompt_profile="standard"):
    search_settings = search_limits(depth, prompt_profile)
    max_text_per_source = search_settings["max_text_per_source"]
    keywords = get_keywords(question)
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n+", text)
        if paragraph.strip()
    ]

    if not paragraphs:
        return text[:max_text_per_source]

    scored_paragraphs = []

    for index, paragraph in enumerate(paragraphs):
        paragraph_lower = paragraph.lower()
        score = sum(1 for keyword in keywords if keyword in paragraph_lower)

        if score > 0:
            scored_paragraphs.append((score, index, paragraph))

    if not scored_paragraphs:
        return text[:max_text_per_source]

    scored_paragraphs.sort(key=lambda item: (-item[0], item[1]))

    selected = []
    current_length = 0

    for score, index, paragraph in scored_paragraphs:
        extra_length = len(paragraph) + 2

        if current_length + extra_length > max_text_per_source:
            continue

        selected.append(paragraph)
        current_length += extra_length

        if current_length >= max_text_per_source:
            break

    return "\n\n".join(selected) or text[:max_text_per_source]


def extract_evidence(question, results, depth, prompt_profile="standard"):
    search_settings = search_limits(depth, prompt_profile)
    max_good_sources = search_settings["max_good_sources"]
    evidence = []

    for result in results:
        title = result.get("title")
        url = result.get("href")

        if not url:
            continue

        if is_blocked_url(url):
            safe_log(f"Skipping blocked source: {url}")
            continue

        safe_log(f"Fetching: {title}")

        downloaded = None
        text = None

        try:
            downloaded = download_page(url)
        except Exception as error:
            safe_log(f"  Could not download page: {error}")

        if downloaded is None:
            safe_log("  Could not download page.")
        else:
            try:
                text = trafilatura.extract(downloaded)
            except Exception as error:
                safe_log(f"  Could not extract readable text: {error}")

        if text is None:
            summary = get_result_summary(result)

            if not summary:
                safe_log("  Could not extract readable text.")
                continue

            safe_log("  Using search result summary as fallback evidence.")
            text = summary

        evidence.append(
            {
                "title": title,
                "url": url,
                "text": pick_relevant_text(
                    text,
                    question,
                    depth,
                    prompt_profile=prompt_profile,
                ),
            }
        )

        if len(evidence) >= max_good_sources:
            break

    return evidence
