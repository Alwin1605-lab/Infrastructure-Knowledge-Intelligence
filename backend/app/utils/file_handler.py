"""File I/O helpers for document upload and management.

Handles saving uploaded files to disk, generating unique filenames,
validating file types, and cleanup.
"""

import os
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.exceptions import DocumentUploadError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Allowed MIME types and extensions
ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_CONTENT_TYPES = {"application/pdf"}


async def save_upload(
    file: BinaryIO,
    filename: str,
    upload_dir: str,
    max_size_mb: int = 50,
) -> tuple[str, int]:
    """Save an uploaded file to disk with a unique name.

    Generates a UUID-prefixed filename to avoid collisions, validates
    the file extension and size, and writes the content to the upload
    directory.

    Args:
        file: The file-like object to save.
        filename: The original filename.
        upload_dir: The directory to save the file in.
        max_size_mb: Maximum allowed file size in MB.

    Returns:
        Tuple of (saved_file_path, file_size_bytes).

    Raises:
        DocumentUploadError: If the file type is invalid or too large.
    """
    # Validate extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentUploadError(
            f"Unsupported file type: '{ext}'. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    save_path = os.path.join(upload_dir, unique_name)

    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)

    # Read and validate size
    content = file.read()
    file_size = len(content)
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        raise DocumentUploadError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB. "
            f"Maximum allowed: {max_size_mb}MB."
        )

    if file_size == 0:
        raise DocumentUploadError("Uploaded file is empty.")

    # Write to disk
    try:
        with open(save_path, "wb") as f:
            f.write(content)
    except OSError as exc:
        raise DocumentUploadError(f"Failed to save file: {exc}") from exc

    logger.info(
        "file_saved",
        filename=filename,
        saved_path=save_path,
        size_bytes=file_size,
    )

    return save_path, file_size


def delete_file(file_path: str) -> bool:
    """Delete a file from disk.

    Args:
        file_path: Absolute path to the file.

    Returns:
        True if the file was deleted, False if it didn't exist.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info("file_deleted", file_path=file_path)
            return True
        return False
    except OSError as exc:
        logger.error("file_delete_failed", file_path=file_path, error=str(exc))
        return False


def validate_content_type(content_type: str) -> bool:
    """Validate that the content type is allowed.

    Args:
        content_type: The MIME type to check.

    Returns:
        True if allowed.
    """
    return content_type in ALLOWED_CONTENT_TYPES
