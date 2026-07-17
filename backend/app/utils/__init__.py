"""Utility functions for the application.

Provides:
    - PDF text extraction with page/section metadata
    - Text chunking strategies
    - File I/O helpers
"""

from app.utils.pdf_parser import extract_text_from_pdf
from app.utils.text_splitter import chunk_text
from app.utils.file_handler import save_upload, delete_file

__all__ = ["extract_text_from_pdf", "chunk_text", "save_upload", "delete_file"]
