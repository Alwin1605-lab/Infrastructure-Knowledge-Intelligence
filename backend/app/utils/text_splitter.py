"""Text chunking strategies for document processing.

Splits extracted text into overlapping chunks suitable for embedding
and retrieval. Preserves source metadata (document ID, page number,
section) with each chunk for citation tracking.
"""

from dataclasses import dataclass, field
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """A chunk of text with source metadata for citation tracking.

    Attributes:
        text: The chunk text content.
        document_id: ID of the source document.
        document_name: Filename of the source document.
        page_number: Page number in the source document (1-indexed).
        section: Section heading this chunk belongs to, if detected.
        chunk_index: Sequential index of this chunk within the document.
        start_char: Starting character offset in the full document text.
        end_char: Ending character offset in the full document text.
    """

    text: str
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    metadata: dict = field(default_factory=dict)


def chunk_text(
    text: str,
    document_id: str,
    document_name: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    page_boundaries: Optional[list[dict]] = None,
) -> list[TextChunk]:
    """Split text into overlapping chunks with source metadata.

    Uses a sliding window approach with configurable size and overlap.
    If page boundaries are provided, each chunk is annotated with its
    source page number and section heading.

    Args:
        text: The full text to split.
        document_id: ID of the source document.
        document_name: Filename of the source document.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between consecutive chunks in characters.
        page_boundaries: Optional list of dicts with keys:
            - start_char (int): Starting character offset of the page.
            - page_number (int): Page number (1-indexed).
            - sections (list[str]): Section headings on this page.

    Returns:
        List of TextChunk objects with source metadata.
    """
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be non-negative, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
        )

    chunks: list[TextChunk] = []
    text_length = len(text)
    step = chunk_size - chunk_overlap
    chunk_index = 0
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Try to break at a sentence boundary (look back up to 100 chars)
        if end < text_length:
            end = _find_sentence_boundary(text, end, lookback=100)

        chunk_text_content = text[start:end].strip()

        if chunk_text_content:
            # Resolve page number and section from boundaries
            page_num, section = _resolve_page_info(start, page_boundaries)

            chunk = TextChunk(
                text=chunk_text_content,
                document_id=document_id,
                document_name=document_name,
                page_number=page_num,
                section=section,
                chunk_index=chunk_index,
                start_char=start,
                end_char=end,
            )
            chunks.append(chunk)
            chunk_index += 1

        start += step

        # Prevent infinite loop
        if start >= end and end >= text_length:
            break

    logger.info(
        "text_chunked",
        document_id=document_id,
        total_chunks=len(chunks),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        text_length=text_length,
    )

    return chunks


def _find_sentence_boundary(text: str, position: int, lookback: int = 100) -> int:
    """Find the nearest sentence boundary before the given position.

    Looks for sentence-ending punctuation (. ! ?) followed by whitespace
    within the lookback window. Falls back to the original position if
    no boundary is found.

    Args:
        text: The full text.
        position: The initial split position.
        lookback: How many characters to look back.

    Returns:
        Adjusted position at a sentence boundary.
    """
    search_start = max(0, position - lookback)
    search_text = text[search_start:position]

    # Look for sentence-ending punctuation
    for punct in [". ", ".\n", "! ", "!\n", "? ", "?\n"]:
        last_idx = search_text.rfind(punct)
        if last_idx != -1:
            return search_start + last_idx + len(punct)

    # Fallback: try to break at any whitespace
    last_space = search_text.rfind(" ")
    if last_space != -1:
        return search_start + last_space + 1

    return position


def _resolve_page_info(
    char_offset: int,
    page_boundaries: Optional[list[dict]],
) -> tuple[Optional[int], Optional[str]]:
    """Resolve page number and section from character offset.

    Args:
        char_offset: Character offset in the full text.
        page_boundaries: Page boundary data.

    Returns:
        Tuple of (page_number, section_heading) or (None, None).
    """
    if not page_boundaries:
        return None, None

    current_page = None
    current_sections: list[str] = []

    for boundary in page_boundaries:
        if boundary["start_char"] <= char_offset:
            current_page = boundary.get("page_number")
            current_sections = boundary.get("sections", [])
        else:
            break

    section = current_sections[0] if current_sections else None
    return current_page, section


def build_page_boundaries(
    pages: list[dict],
) -> list[dict]:
    """Build page boundary data from extracted pages.

    Creates a list of boundary markers used by chunk_text to annotate
    chunks with their source page and section.

    Args:
        pages: List of dicts with keys: page_number, text, sections.

    Returns:
        List of boundary dicts with keys: start_char, page_number, sections.
    """
    boundaries: list[dict] = []
    offset = 0

    for page in pages:
        boundaries.append({
            "start_char": offset,
            "page_number": page.get("page_number", 0),
            "sections": page.get("sections", []),
        })
        # +2 for the "\n\n" separator between pages
        offset += len(page.get("text", "")) + 2

    return boundaries
