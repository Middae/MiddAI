import base64
import io
import re
import zipfile
from pathlib import PurePath
from xml.etree import ElementTree


MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_CHARS_PER_ATTACHMENT = 9000
MAX_TOTAL_ATTACHMENT_CHARS = 24000
MAX_IMAGE_ATTACHMENTS = 3
MAX_IMAGE_PREVIEW_URL_CHARS = 120000

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".log",
    ".csv",
    ".json",
    ".toml",
    ".ini",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".py",
    ".bat",
    ".ps1",
    ".sql",
}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | PDF_EXTENSIONS | DOCX_EXTENSIONS | IMAGE_EXTENSIONS
ACCEPTED_ATTACHMENT_TYPES_TEXT = (
    "Accepted file types: .txt, .md, .markdown, .log, .csv, .json, .toml, .ini, "
    ".yaml, .yml, .xml, .html, .htm, .css, .js, .ts, .py, .bat, .ps1, .sql, "
    ".docx, .pdf, .jpg, .jpeg, .png, .webp."
)

IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class AttachmentError(ValueError):
    pass


def clean_filename(name):
    filename = PurePath(str(name or "")).name.strip()
    return filename or "attachment"


def attachment_extension(name):
    return PurePath(clean_filename(name)).suffix.lower()


def normalize_text(text):
    text = (text or "").replace("\x00", "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def truncate_text(text, limit):
    text = normalize_text(text)

    if len(text) <= limit:
        return text, False

    truncated = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{truncated}\n\n[Text truncated by MiddAI for context size.]", True


def decode_base64_data(data_base64):
    try:
        return base64.b64decode(data_base64 or "", validate=True)
    except (ValueError, TypeError) as error:
        raise AttachmentError("Could not read one attached file.") from error


def extract_text_file(raw_attachment):
    text = raw_attachment.get("text")

    if not isinstance(text, str):
        raise AttachmentError("Attached text file did not contain readable text.")

    return normalize_text(text)


def extract_docx_text(file_bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as error:
        raise AttachmentError("Could not extract text from the attached DOCX file.") from error

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as error:
        raise AttachmentError("Could not read the attached DOCX file.") from error

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []

    for paragraph in root.iter(f"{namespace}p"):
        pieces = [
            node.text
            for node in paragraph.iter(f"{namespace}t")
            if node.text
        ]

        if pieces:
            paragraphs.append("".join(pieces))

    return normalize_text("\n".join(paragraphs))


def extract_pdf_text(file_bytes):
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise AttachmentError(
            "PDF support is not installed in this build yet. Text, code, and DOCX files still work."
        ) from error

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as error:
        raise AttachmentError("Could not open the attached PDF file.") from error

    pages = []

    for page in reader.pages[:60]:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")

    text = normalize_text("\n\n".join(page for page in pages if page.strip()))

    if not text:
        raise AttachmentError(
            "Could not extract readable text from the attached PDF. It may be scanned images."
        )

    return text


def extract_attachment_text(raw_attachment):
    name = clean_filename(raw_attachment.get("name"))
    extension = attachment_extension(name)

    if extension not in SUPPORTED_EXTENSIONS:
        raise AttachmentError(
            f"Unsupported attachment type: {extension or name}. {ACCEPTED_ATTACHMENT_TYPES_TEXT}"
        )

    if extension in TEXT_EXTENSIONS:
        return extract_text_file(raw_attachment)

    file_bytes = decode_base64_data(raw_attachment.get("data_base64"))

    if len(file_bytes) > MAX_ATTACHMENT_BYTES:
        raise AttachmentError(f"{name} is too large. Maximum file size is 8 MB.")

    if extension in DOCX_EXTENSIONS:
        return extract_docx_text(file_bytes)

    if extension in PDF_EXTENSIONS:
        return extract_pdf_text(file_bytes)

    raise AttachmentError(
        f"Unsupported attachment type: {extension}. {ACCEPTED_ATTACHMENT_TYPES_TEXT}"
    )


def prepare_attachments(raw_attachments):
    if not raw_attachments:
        return []

    if not isinstance(raw_attachments, list):
        raise AttachmentError("Attachments were not sent in a readable format.")

    if len(raw_attachments) > MAX_ATTACHMENTS:
        raise AttachmentError(f"Attach up to {MAX_ATTACHMENTS} files at once.")

    prepared = []
    remaining_chars = MAX_TOTAL_ATTACHMENT_CHARS

    for raw_attachment in raw_attachments:
        if not isinstance(raw_attachment, dict):
            raise AttachmentError("One attachment was not readable.")

        name = clean_filename(raw_attachment.get("name"))
        size = int(raw_attachment.get("size") or 0)

        if size > MAX_ATTACHMENT_BYTES:
            raise AttachmentError(f"{name} is too large. Maximum file size is 8 MB.")

        if remaining_chars <= 0:
            break

        text = extract_attachment_text(raw_attachment)

        if not text:
            raise AttachmentError(f"No readable text was found in {name}.")

        limit = min(MAX_CHARS_PER_ATTACHMENT, remaining_chars)
        text, was_truncated = truncate_text(text, limit)
        remaining_chars -= len(text)

        prepared.append(
            {
                "name": name,
                "extension": attachment_extension(name),
                "size": size,
                "text": text,
                "chars": len(text),
                "truncated": was_truncated,
            }
        )

    return prepared


def prepare_image_attachment(raw_attachment):
    name = clean_filename(raw_attachment.get("name"))
    extension = attachment_extension(name)

    if extension not in IMAGE_EXTENSIONS:
        raise AttachmentError(f"Unsupported image type: {extension or name}.")

    file_bytes = decode_base64_data(raw_attachment.get("data_base64"))

    if len(file_bytes) > MAX_ATTACHMENT_BYTES:
        raise AttachmentError(f"{name} is too large. Maximum file size is 8 MB.")

    mime_type = str(raw_attachment.get("mime_type") or "").strip().lower()

    if mime_type not in set(IMAGE_MIME_TYPES.values()):
        mime_type = IMAGE_MIME_TYPES.get(extension, "image/png")

    preview_url = str(raw_attachment.get("preview_url") or "")

    if len(preview_url) > MAX_IMAGE_PREVIEW_URL_CHARS:
        preview_url = ""

    return {
        "name": name,
        "extension": extension,
        "size": int(raw_attachment.get("size") or len(file_bytes)),
        "mime_type": mime_type,
        "data_base64": raw_attachment.get("data_base64") or "",
        "preview_url": preview_url,
    }


def prepare_uploaded_files(raw_attachments):
    if not raw_attachments:
        return [], []

    if not isinstance(raw_attachments, list):
        raise AttachmentError("Attachments were not sent in a readable format.")

    if len(raw_attachments) > MAX_ATTACHMENTS:
        raise AttachmentError(f"Attach up to {MAX_ATTACHMENTS} files at once.")

    documents = []
    images = []
    document_inputs = []

    for raw_attachment in raw_attachments:
        if not isinstance(raw_attachment, dict):
            raise AttachmentError("One attachment was not readable.")

        name = clean_filename(raw_attachment.get("name"))
        extension = attachment_extension(name)

        if extension not in SUPPORTED_EXTENSIONS:
            raise AttachmentError(
                f"Unsupported attachment type: {extension or name}. {ACCEPTED_ATTACHMENT_TYPES_TEXT}"
            )

        if extension in IMAGE_EXTENSIONS:
            if len(images) >= MAX_IMAGE_ATTACHMENTS:
                raise AttachmentError(f"Attach up to {MAX_IMAGE_ATTACHMENTS} images at once.")

            images.append(prepare_image_attachment(raw_attachment))
        else:
            document_inputs.append(raw_attachment)

    if document_inputs:
        documents = prepare_attachments(document_inputs)

    return documents, images


def public_attachment_metadata(attachments):
    return [
        {
            "name": attachment["name"],
            "extension": attachment["extension"],
            "size": attachment["size"],
            "chars": attachment["chars"],
            "truncated": attachment["truncated"],
        }
        for attachment in attachments
    ]


def public_file_metadata(documents, images):
    metadata = public_attachment_metadata(documents)

    for image in images:
        metadata.append(
            {
                "name": image["name"],
                "extension": image["extension"],
                "size": image["size"],
                "mime_type": image["mime_type"],
                "kind": "image",
                "preview_url": image.get("preview_url", ""),
            }
        )

    return metadata
