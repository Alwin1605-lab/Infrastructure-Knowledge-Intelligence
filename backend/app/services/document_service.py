"""Document service — orchestrates the complete document upload pipeline.

Handles the full lifecycle of a document upload:
    1. Save file to disk
    2. Extract text from PDF (with page/section metadata)
    3. Save metadata and extracted text to MongoDB (status: EXTRACTED)
    4. Chunk text into overlapping segments with source metadata
    5. Embed chunks using HuggingFace all-MiniLM-L6-v2 (local)
    6. Store chunk embeddings in ChromaDB (status: COMPLETED)
    7. Return the document record

Phase 4 will extend this to also:
    - Extract building entities (KG indexing via LLMService)
"""

from typing import BinaryIO, Optional, TYPE_CHECKING

from app.config import Settings
from app.core.exceptions import DocumentUploadError, DocumentExtractionError, VectorStoreIndexError
from app.core.logging import get_logger
from app.db.repositories.document_repo import DocumentRepository
from app.models.document import Document, DocumentStatus, DocumentType, ExtractedPage
from app.utils.pdf_parser import extract_text_from_pdf
from app.utils.file_handler import save_upload, validate_content_type, delete_file
from app.utils.text_splitter import chunk_text, build_page_boundaries

if TYPE_CHECKING:
    from app.vectorstore.indexer import ChromaIndexer
    from app.knowledge_graph.builder import KGBuilder

logger = get_logger(__name__)


class DocumentService:
    """Service for managing document uploads and processing.

    Orchestrates file saving, text extraction, chunking, embedding,
    and MongoDB + ChromaDB persistence. All external dependencies
    are injected via the constructor.
    """

    def __init__(
        self,
        settings: Settings,
        chroma_indexer: Optional["ChromaIndexer"] = None,
        kg_builder: Optional["KGBuilder"] = None,
    ) -> None:
        """Initialize the document service.

        Args:
            settings: Application settings.
            chroma_indexer: Optional ChromaDB indexer for embedding pipeline.
            kg_builder: Optional Knowledge Graph builder for entity extraction.
        """
        self._upload_dir = settings.UPLOAD_DIR
        self._max_upload_size_mb = settings.MAX_UPLOAD_SIZE_MB
        self._chunk_size = settings.RAG_CHUNK_SIZE
        self._chunk_overlap = settings.RAG_CHUNK_OVERLAP
        self._repo = DocumentRepository()
        self._chroma_indexer = chroma_indexer
        self._kg_builder = kg_builder

    async def upload_document(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        document_type: DocumentType = DocumentType.GENERAL,
    ) -> Document:
        """Upload and fully process a building document.

        Pipeline:
            1. Validate content type (PDF only)
            2. Save file to disk
            3. Create MongoDB record (status: UPLOADED)
            4. Extract text with page/section metadata (status: EXTRACTED)
            5. Chunk text into overlapping segments (status: CHUNKING)
            6. Embed + index in ChromaDB (status: EMBEDDING → COMPLETED)

        Args:
            file: The uploaded file binary content.
            filename: Original filename.
            content_type: MIME type of the file.
            document_type: Building document category.

        Returns:
            The created Document with extracted text and chunk count.

        Raises:
            DocumentUploadError: If file type is invalid or save fails.
            DocumentExtractionError: If text extraction fails.
        """
        # Step 1: Validate content type
        if not validate_content_type(content_type):
            raise DocumentUploadError(
                f"Unsupported content type: '{content_type}'. Only PDF files are accepted."
            )

        # Step 2: Save file to disk
        file_path, file_size = await save_upload(
            file=file,
            filename=filename,
            upload_dir=self._upload_dir,
            max_size_mb=self._max_upload_size_mb,
        )

        # Step 3: Create document record
        document = Document(
            filename=filename,
            file_path=file_path,
            file_size_bytes=file_size,
            content_type=content_type,
            document_type=document_type,
            status=DocumentStatus.UPLOADED,
        )
        await self._repo.create(document)

        # Step 4: Extract text
        try:
            document.mark_extracting()
            await self._repo.update(document)

            result = extract_text_from_pdf(file_path)

            extracted_pages = [
                ExtractedPage(
                    page_number=page.page_number,
                    text=page.text,
                    sections=page.sections,
                    char_count=page.char_count,
                )
                for page in result.pages
            ]

            document.mark_extracted(
                pages=extracted_pages,
                full_text=result.full_text,
            )
            document.metadata = result.metadata
            await self._repo.update(document)

        except DocumentExtractionError:
            document.mark_failed("Text extraction failed.")
            await self._repo.update(document)
            raise
        except Exception as exc:
            document.mark_failed(str(exc))
            await self._repo.update(document)
            raise DocumentExtractionError(
                f"Unexpected error during extraction: {exc}"
            ) from exc

        # Step 5 & 6: Chunk + Embed (if ChromaDB indexer is available)
        if self._chroma_indexer and result.full_text.strip():
            try:
                document.status = DocumentStatus.CHUNKING
                await self._repo.update(document)

                # Build page boundary markers for citation annotation
                page_boundaries = build_page_boundaries([
                    {
                        "page_number": p.page_number,
                        "text": p.text,
                        "sections": p.sections,
                    }
                    for p in result.pages
                ])

                # Chunk the extracted text
                chunks = chunk_text(
                    text=result.full_text,
                    document_id=str(document.id),
                    document_name=filename,
                    chunk_size=self._chunk_size,
                    chunk_overlap=self._chunk_overlap,
                    page_boundaries=page_boundaries,
                )

                logger.info(
                    "document_chunked",
                    document_id=str(document.id),
                    total_chunks=len(chunks),
                )

                document.status = DocumentStatus.EMBEDDING
                await self._repo.update(document)

                # Delete any existing chunks for this doc (idempotent re-upload)
                await self._chroma_indexer.delete_document_chunks(str(document.id))

                # Embed and store in ChromaDB
                indexed_count = await self._chroma_indexer.index_chunks(chunks)
                document.total_chunks = indexed_count
                await self._repo.update(document)

                # Step 7: Knowledge Graph Extraction & Indexing (if kg_builder is available)
                if self._kg_builder and extracted_pages:
                    try:
                        document.status = DocumentStatus.INDEXING_KG
                        await self._repo.update(document)

                        total_entities, total_rels = await self._kg_builder.build_from_document(
                            document_id=str(document.id),
                            filename=filename,
                            pages=extracted_pages,
                        )
                        document.mark_kg_indexed(total_entities, total_rels)
                    except Exception as kg_exc:
                        logger.warning(
                            "kg_indexing_failed_non_fatal",
                            document_id=str(document.id),
                            error=str(kg_exc),
                        )

                document.mark_completed(total_chunks=indexed_count)
                await self._repo.update(document)

                logger.info(
                    "document_fully_processed",
                    document_id=str(document.id),
                    filename=filename,
                    total_pages=result.total_pages,
                    total_chunks=indexed_count,
                )

            except VectorStoreIndexError as exc:
                # Embedding failed — document is still usable (extracted text is stored)
                logger.warning(
                    "embedding_failed_document_still_usable",
                    document_id=str(document.id),
                    error=str(exc),
                )
                document.mark_failed(f"Embedding failed: {exc}. Document text still available.")
                await self._repo.update(document)
        else:
            if not self._chroma_indexer:
                logger.warning(
                    "no_chroma_indexer",
                    document_id=str(document.id),
                    note="ChromaDB not available — document extracted but not embedded.",
                )

        return document

    async def get_document(self, document_id: str) -> Document:
        """Retrieve a document by ID."""
        return await self._repo.get_by_id(document_id)

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[DocumentStatus] = None,
    ) -> tuple[list[Document], int]:
        """List documents with pagination."""
        documents = await self._repo.get_all(skip=skip, limit=limit, status=status)
        total = await self._repo.count(status=status)
        return documents, total

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document, its file, and its vector embeddings."""
        doc = await self._repo.get_by_id(document_id)

        # Remove file from disk
        delete_file(doc.file_path)

        # Remove chunks from ChromaDB
        if self._chroma_indexer:
            await self._chroma_indexer.delete_document_chunks(document_id)

        # Remove entities from Neo4j
        if self._kg_builder:
            await self._kg_builder.delete_document_entities(document_id)

        # Remove from MongoDB
        await self._repo.delete(document_id)
        logger.info("document_deleted_completely", document_id=document_id)
        return True
