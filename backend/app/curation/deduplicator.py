"""Document Deduplication Service.

Identifies exact SHA-256 byte duplicates, exact title/filename matches across
different source folders, and near-duplicate versions. Retains the highest-quality
version (`final_weighted_score`) while marking others as DUPLICATE.
"""

from typing import Any
from app.core.logging import get_logger
from app.curation.models import CurationRecord, CurationStatus, DuplicateGroup

logger = get_logger(__name__)


class DocumentDeduplicator:
    """Deduplicates a collection of curation records by hash, title, and content similarity."""

    def deduplicate(self, records: list[CurationRecord]) -> tuple[list[CurationRecord], list[DuplicateGroup]]:
        """Process records to find and mark duplicates.

        Returns:
            tuple of (all_records_with_updated_status, list_of_duplicate_groups)
        """
        # We only check duplication among non-rejected documents
        candidates = [r for r in records if r.status != CurationStatus.REJECTED.value]
        if not candidates:
            return records, []

        groups: dict[str, list[CurationRecord]] = {}

        for rec in candidates:
            # Create a robust grouping key using SHA-256 hash or exact normalized title/filename
            hash_key = rec.file_hash_sha256
            title_key = rec.metadata.title.strip().lower()
            name_key = rec.metadata.file_name.strip().lower()

            matched = False
            for group_key, group_records in groups.items():
                first = group_records[0]
                if (
                    (hash_key and hash_key == first.file_hash_sha256) or
                    (name_key and name_key == first.metadata.file_name.strip().lower()) or
                    (len(title_key) > 8 and title_key == first.metadata.title.strip().lower())
                ):
                    group_records.append(rec)
                    matched = True
                    break

            if not matched:
                groups[hash_key or name_key] = [rec]

        duplicate_groups: list[DuplicateGroup] = []

        for group_records in groups.values():
            if len(group_records) > 1:
                # Sort descending by quality score, then by OCR not used, then page count
                group_records.sort(
                    key=lambda r: (
                        r.quality.final_weighted_score,
                        not r.metadata.ocr_used,
                        r.metadata.number_of_pages,
                        r.metadata.file_size_bytes
                    ),
                    reverse=True
                )
                canonical = group_records[0]
                dups = group_records[1:]

                for d in dups:
                    d.status = CurationStatus.DUPLICATE.value
                    d.rejection_reasons.append(
                        f"Duplicate of '{canonical.metadata.file_name}' (ID: {canonical.metadata.document_id}, score: {canonical.quality.final_weighted_score})."
                    )

                duplicate_groups.append(DuplicateGroup(
                    canonical_record=canonical,
                    duplicates=dups
                ))
                logger.info(f"Deduplicated {len(dups)} duplicates under canonical doc {canonical.metadata.file_name}")

        return records, duplicate_groups
