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
from app.models.workspace_document import WorkspaceDocument
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

    async def upload_and_queue(
        self,
        file,
        filename: str,
        content_type: str,
        document_type: str = "general",
        category: str = "GENERAL",
        workspace_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> "ProcessingJob":
        """Upload file and create a background processing job.
        
        Returns the ProcessingJob immediately. Processing runs in background.
        """
        from app.models.processing_job import ProcessingJob, JobStatus, JobStep
        from app.models.document import DocumentCategory
        from app.services.notification_service import NotificationService
        import hashlib
        import asyncio
        
        # Step 1: Validate and save file
        from app.utils.file_handler import save_upload, validate_content_type
        if not validate_content_type(content_type):
            raise DocumentUploadError(f"Unsupported content type: {content_type}")
        
        # Read file content for hashing
        file_content = file.read()
        file.seek(0)
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check for duplicate
        existing = await Document.find_one({"sha256_hash": sha256_hash})
        is_duplicate = existing is not None
        
        # Handle versioning
        version = 1
        original_filename = filename
        existing_versions = await Document.find({"original_filename": filename}).sort("-version").limit(1).to_list()
        if existing_versions:
            version = existing_versions[0].version + 1
        
        file_path, file_size = await save_upload(
            file=file,
            filename=filename,
            upload_dir=self._upload_dir,
            max_size_mb=self._max_upload_size_mb,
        )
        
        # Step 2: Create Document record
        try:
            doc_category = DocumentCategory[category] if hasattr(DocumentCategory, category) else DocumentCategory.GENERAL
        except (KeyError, AttributeError):
            doc_category = DocumentCategory.GENERAL
        
        document = Document(
            filename=filename,
            file_path=file_path,
            file_size_bytes=file_size,
            content_type=content_type,
            document_type=document_type,
            status=DocumentStatus.UPLOADED,
            sha256_hash=sha256_hash,
            version=version,
            original_filename=original_filename,
            category=doc_category,
            indexed_by=owner_id,
        )
        await self._repo.create(document)
        
        # Step 3: Create ProcessingJob
        job = ProcessingJob(
            document_id=str(document.id),
            filename=filename,
            status=JobStatus.QUEUED,
            current_step=JobStep.UPLOAD,
            user_id=owner_id or "system",
            workspace_id=workspace_id,
        )
        await job.insert()
        
        # Step 4: Launch background task
        asyncio.create_task(
            self._process_document_background(
                job=job,
                document=document,
                is_duplicate=is_duplicate,
                workspace_id=workspace_id,
                owner_id=owner_id,
            )
        )
        
        logger.info(
            "document_queued_for_processing",
            job_id=str(job.id),
            document_id=str(document.id),
            is_duplicate=is_duplicate,
        )
        return job
    
    async def _process_document_background(
        self,
        job: "ProcessingJob",
        document,
        is_duplicate: bool = False,
        workspace_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> None:
        """Background processing pipeline. Updates job status at each step."""
        from app.models.processing_job import JobStatus, JobStep
        from datetime import datetime, timezone
        import time
        
        start_time = time.time()
        
        async def update_job(step: str, status=None, **kwargs):
            job.current_step = step
            if status:
                job.status = status
            for k, v in kwargs.items():
                setattr(job, k, v)
            job.elapsed_seconds = time.time() - start_time
            job.updated_at = datetime.now(timezone.utc)
            await job.save()
        
        try:
            await update_job(JobStep.UPLOAD, JobStatus.RUNNING, started_at=datetime.now(timezone.utc))
            
            # EXTRACT
            await update_job(JobStep.EXTRACT)
            if isinstance(document, Document):
                document.mark_extracting()
                await self._repo.update(document)
            
            from app.utils.pdf_parser import extract_text_from_pdf
            from app.models.document import ExtractedPage
            result = extract_text_from_pdf(document.file_path)
            
            extracted_pages = [
                ExtractedPage(
                    page_number=p.page_number,
                    text=p.text,
                    sections=p.sections,
                    char_count=p.char_count,
                )
                for p in result.pages
            ]
            
            # Auto-extract metadata from PDF
            auto_meta = {}
            if result.metadata:
                auto_meta = {
                    "title": result.metadata.get("title", ""),
                    "author": result.metadata.get("author", ""),
                    "creation_date": result.metadata.get("creationDate", ""),
                    "pages": result.total_pages,
                }
            
            if isinstance(document, Document):
                document.mark_extracted(pages=extracted_pages, full_text=result.full_text)
                document.metadata = result.metadata
                document.auto_metadata = auto_meta
                await self._repo.update(document)
            
            job.completed_steps.append(JobStep.EXTRACT)
            job.pages_extracted = result.total_pages
            await update_job(JobStep.CHUNK)
            
            # CHUNK + EMBED
            if self._chroma_indexer and result.full_text.strip():
                if isinstance(document, Document):
                    document.status = document.status.CHUNKING
                    await self._repo.update(document)
                
                from app.utils.text_splitter import chunk_text, build_page_boundaries
                page_boundaries = build_page_boundaries([
                    {"page_number": p.page_number, "text": p.text, "sections": p.sections}
                    for p in result.pages
                ])
                
                metadata_updates = {"is_global": True}
                if workspace_id:
                    metadata_updates = {"workspace_id": workspace_id, "is_global": False}
                
                chunks = chunk_text(
                    text=result.full_text,
                    document_id=str(document.id),
                    document_name=document.filename,
                    chunk_size=self._chunk_size,
                    chunk_overlap=self._chunk_overlap,
                    page_boundaries=page_boundaries,
                )
                for chunk in chunks:
                    chunk.metadata.update(metadata_updates)
                
                job.completed_steps.append(JobStep.CHUNK)
                job.chunks_created = len(chunks)
                await update_job(JobStep.EMBED)
                
                if isinstance(document, Document):
                    document.status = document.status.EMBEDDING
                    await self._repo.update(document)
                
                await self._chroma_indexer.delete_document_chunks(str(document.id))
                indexed_count = await self._chroma_indexer.index_chunks(chunks)
                
                if isinstance(document, Document):
                    document.total_chunks = indexed_count
                    await self._repo.update(document)
                
                job.completed_steps.append(JobStep.EMBED)
                job.embeddings_created = indexed_count
                
                # KG INDEXING
                if self._kg_builder and extracted_pages and isinstance(document, Document):
                    await update_job(JobStep.KG_INDEX)
                    if isinstance(document, Document):
                        document.status = document.status.INDEXING_KG
                        await self._repo.update(document)
                    try:
                        total_entities, total_rels = await self._kg_builder.build_from_document(
                            document_id=str(document.id),
                            filename=document.filename,
                            pages=extracted_pages,
                        )
                        document.mark_kg_indexed(total_entities, total_rels)
                        job.kg_nodes_created = total_entities
                        job.kg_relations_created = total_rels
                        job.completed_steps.append(JobStep.KG_INDEX)
                    except Exception as kg_exc:
                        logger.warning("kg_indexing_failed_non_fatal", error=str(kg_exc))
                
                if isinstance(document, Document):
                    document.mark_completed(total_chunks=indexed_count)
                    await self._repo.update(document)
            
            # COMPLETE
            job.status = JobStatus.COMPLETED
            job.current_step = JobStep.COMPLETE
            job.completed_steps.append(JobStep.COMPLETE)
            job.completed_at = datetime.now(timezone.utc)
            job.elapsed_seconds = time.time() - start_time
            await job.save()
            
            # Send notification
            try:
                from app.services.notification_service import NotificationService
                from app.models.notification import NotificationType
                notif_svc = NotificationService()
                await notif_svc.create(
                    user_id=owner_id or "system",
                    title="Document Indexed Successfully",
                    message=f"'{document.filename}' has been indexed. {job.chunks_created} chunks, {job.kg_nodes_created} KG entities created.",
                    notification_type=NotificationType.DOCUMENT_INDEXED,
                    link=f"/docs",
                )
            except Exception as notif_exc:
                logger.warning("notification_failed", error=str(notif_exc))
            
            logger.info(
                "document_background_processing_complete",
                job_id=str(job.id),
                elapsed=round(time.time() - start_time, 1),
            )
        
        except Exception as exc:
            logger.error("document_background_processing_failed", error=str(exc))
            job.status = JobStatus.FAILED
            job.failed_step = str(job.current_step)
            job.error_message = str(exc)
            job.elapsed_seconds = time.time() - start_time
            await job.save()
            
            try:
                from app.services.notification_service import NotificationService
                from app.models.notification import NotificationType
                notif_svc = NotificationService()
                await notif_svc.create(
                    user_id=owner_id or "system",
                    title="Processing Failed",
                    message=f"Failed to process '{document.filename}': {str(exc)[:100]}",
                    notification_type=NotificationType.JOB_FAILED,
                    link=f"/docs",
                )
            except Exception:
                pass
    
    async def get_job_status(self, job_id: str):
        """Get current status of a processing job."""
        from app.models.processing_job import ProcessingJob
        from beanie import PydanticObjectId
        try:
            return await ProcessingJob.get(job_id)
        except Exception:
            return None
    
    async def list_jobs(
        self,
        user_id: Optional[str] = None,
        status=None,
        limit: int = 20,
    ):
        """List processing jobs."""
        from app.models.processing_job import ProcessingJob
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if status:
            filters["status"] = status
        return await ProcessingJob.find(filters).sort("-created_at").limit(limit).to_list()

    async def upload_document(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        document_type: str = DocumentType.GENERAL,
        workspace_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ):
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
        if workspace_id and owner_id:
            document = WorkspaceDocument(
                filename=filename,
                file_path=file_path,
                content_type=content_type,
                workspace_id=workspace_id,
                owner_id=owner_id,
                status="uploaded"
            )
            await document.insert()
        else:
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
            if isinstance(document, Document):
                document.mark_extracting()
                await self._repo.update(document)
            else:
                document.status = "extracting"
                await document.save()

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

            if isinstance(document, Document):
                document.mark_extracted(
                    pages=extracted_pages,
                    full_text=result.full_text,
                )
                document.metadata = result.metadata
                await self._repo.update(document)
            else:
                document.status = "extracted"
                document.pages = result.total_pages
                await document.save()

        except DocumentExtractionError:
            if isinstance(document, Document):
                document.mark_failed("Text extraction failed.")
                await self._repo.update(document)
            else:
                document.status = "failed"
                await document.save()
            raise
        except Exception as exc:
            if isinstance(document, Document):
                document.mark_failed(str(exc))
                await self._repo.update(document)
            else:
                document.status = "failed"
                await document.save()
            raise DocumentExtractionError(
                f"Unexpected error during extraction: {exc}"
            ) from exc

        # Step 5 & 6: Chunk + Embed (if ChromaDB indexer is available)
        if self._chroma_indexer and result.full_text.strip():
            try:
                if isinstance(document, Document):
                    document.status = DocumentStatus.CHUNKING
                    await self._repo.update(document)
                else:
                    document.status = "chunking"
                    await document.save()

                # Build page boundary markers for citation annotation
                page_boundaries = build_page_boundaries([
                    {
                        "page_number": p.page_number,
                        "text": p.text,
                        "sections": p.sections,
                    }
                    for p in result.pages
                ])

                # Build extra metadata
                metadata_updates = {}
                if isinstance(document, WorkspaceDocument):
                    metadata_updates = {"workspace_id": workspace_id, "is_global": False}
                else:
                    metadata_updates = {"is_global": True}

                # Chunk the extracted text
                chunks = chunk_text(
                    text=result.full_text,
                    document_id=str(document.id),
                    document_name=filename,
                    chunk_size=self._chunk_size,
                    chunk_overlap=self._chunk_overlap,
                    page_boundaries=page_boundaries,
                )
                
                # Attach extra metadata to each chunk
                for chunk in chunks:
                    chunk.metadata.update(metadata_updates)

                logger.info(
                    "document_chunked",
                    document_id=str(document.id),
                    total_chunks=len(chunks),
                )

                if isinstance(document, Document):
                    document.status = DocumentStatus.EMBEDDING
                    await self._repo.update(document)
                else:
                    document.status = "embedding"
                    await document.save()

                # Delete any existing chunks for this doc (idempotent re-upload)
                await self._chroma_indexer.delete_document_chunks(str(document.id))

                # Embed and store in ChromaDB
                indexed_count = await self._chroma_indexer.index_chunks(chunks)
                if isinstance(document, Document):
                    document.total_chunks = indexed_count
                    await self._repo.update(document)
                else:
                    document.chunks_created = indexed_count
                    await document.save()

                # Step 7: Knowledge Graph Extraction & Indexing (if kg_builder is available and it's global)
                if self._kg_builder and extracted_pages and isinstance(document, Document):
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

                if isinstance(document, Document):
                    document.mark_completed(total_chunks=indexed_count)
                    await self._repo.update(document)
                else:
                    document.status = "completed"
                    await document.save()

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
                if isinstance(document, Document):
                    document.mark_failed(f"Embedding failed: {exc}. Document text still available.")
                    await self._repo.update(document)
                else:
                    document.status = "failed"
                    await document.save()
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
