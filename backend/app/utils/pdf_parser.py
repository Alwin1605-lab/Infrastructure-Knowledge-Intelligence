"""PDF text extraction using PyMuPDF (fitz).

Extracts text content from PDF files with page-level metadata
including page numbers and detected section headings. This metadata
is critical for source attribution in RAG citations.
"""

import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF

from app.core.exceptions import DocumentExtractionError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedPageData:
    """Extracted content from a single PDF page.

    Attributes:
        page_number: 1-indexed page number.
        text: Raw text extracted from the page.
        sections: Section headings detected on this page.
        char_count: Number of characters in the extracted text.
    """

    page_number: int
    text: str
    sections: list[str] = field(default_factory=list)
    char_count: int = 0

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


@dataclass
class PDFExtractionResult:
    """Result of PDF text extraction.

    Attributes:
        pages: List of extracted page data.
        full_text: Concatenated text from all pages.
        total_pages: Total number of pages in the PDF.
        metadata: Document-level metadata (title, author, etc.).
    """

    pages: list[ExtractedPageData]
    full_text: str
    total_pages: int
    metadata: dict = field(default_factory=dict)


def extract_text_from_pdf(file_path: str) -> PDFExtractionResult:
    """Extract text from a PDF file with page-level metadata.

    Uses PyMuPDF for extraction. Detects section headings by analyzing
    font sizes — text blocks with larger-than-average fonts are treated
    as headings.

    Args:
        file_path: Absolute path to the PDF file.

    Returns:
        PDFExtractionResult with page data, full text, and metadata.

    Raises:
        DocumentExtractionError: If the PDF cannot be opened or parsed.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        logger.error("pdf_open_failed", file_path=file_path, error=str(exc))
        raise DocumentExtractionError(
            f"Failed to open PDF file: {file_path}. Error: {exc}"
        ) from exc

    pages: list[ExtractedPageData] = []
    all_text_parts: list[str] = []

    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Extract plain text
            page_text = page.get_text("text")

            # Detect section headings via font analysis
            sections = _detect_sections(page)

            page_data = ExtractedPageData(
                page_number=page_num + 1,  # 1-indexed
                text=page_text.strip(),
                sections=sections,
            )
            pages.append(page_data)
            all_text_parts.append(page_text)

        # Extract document metadata
        metadata = _extract_metadata(doc)

        full_text = "\n\n".join(all_text_parts).strip()

        logger.info(
            "pdf_extraction_completed",
            file_path=file_path,
            total_pages=len(doc),
            total_chars=len(full_text),
        )

        return PDFExtractionResult(
            pages=pages,
            full_text=full_text,
            total_pages=len(doc),
            metadata=metadata,
        )

    except DocumentExtractionError:
        raise
    except Exception as exc:
        logger.error("pdf_extraction_failed", file_path=file_path, error=str(exc))
        raise DocumentExtractionError(
            f"Failed to extract text from PDF: {file_path}. Error: {exc}"
        ) from exc
    finally:
        doc.close()


def _detect_sections(page: fitz.Page) -> list[str]:
    """Detect section headings on a PDF page using font size analysis.

    Text blocks with font sizes significantly larger than the page
    average are treated as section headings.

    Args:
        page: A PyMuPDF Page object.

    Returns:
        List of detected section heading strings.
    """
    sections: list[str] = []

    try:
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]
    except Exception:
        return sections

    # Collect all font sizes and text spans
    font_sizes: list[float] = []
    text_spans: list[tuple[float, str]] = []

    for block in blocks:
        if block.get("type") != 0:  # Skip non-text blocks
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size", 0)
                text = span.get("text", "").strip()
                if text and size > 0:
                    font_sizes.append(size)
                    text_spans.append((size, text))

    if not font_sizes:
        return sections

    # Heading = font size > average + 2 points
    avg_size = sum(font_sizes) / len(font_sizes)
    heading_threshold = avg_size + 2.0

    for size, text in text_spans:
        if size >= heading_threshold and len(text) > 2 and len(text) < 200:
            # Clean up the heading text
            cleaned = re.sub(r"\s+", " ", text).strip()
            if cleaned and cleaned not in sections:
                sections.append(cleaned)

    return sections


def _extract_metadata(doc: fitz.Document) -> dict:
    """Extract document-level metadata from PDF.

    Args:
        doc: A PyMuPDF Document object.

    Returns:
        Dictionary with metadata fields (title, author, subject, etc.).
    """
    raw_meta = doc.metadata
    metadata = {}

    if raw_meta:
        for key in ["title", "author", "subject", "keywords", "creator", "producer"]:
            value = raw_meta.get(key, "")
            if value:
                metadata[key] = value

    return metadata
