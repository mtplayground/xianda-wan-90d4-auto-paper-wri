from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class ReferencePdfParseError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedReferenceText:
    text: str
    page_count: int


def extract_pdf_text(data: bytes) -> ExtractedReferenceText:
    try:
        reader = PdfReader(BytesIO(data))
        page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    except (PdfReadError, OSError, ValueError) as exc:
        raise ReferencePdfParseError("Could not parse PDF text") from exc

    text = "\n\n".join(text for text in page_text if text)
    if not text.strip():
        raise ReferencePdfParseError("PDF does not contain extractable text")
    return ExtractedReferenceText(text=text, page_count=len(reader.pages))


def chunk_reference_text(text: str, *, max_chars: int = 4_000) -> list[str]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for index in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[index : index + max_chars])
            continue

        separator = "\n\n" if current else ""
        candidate = f"{current}{separator}{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = paragraph

    if current:
        chunks.append(current)
    return chunks
