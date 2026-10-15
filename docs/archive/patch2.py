import re

with open('backend/app/services/document_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = lines[:162]

new_func = """    async def _process_document_background(
        self,
        job: "ProcessingJob",
        document,
        is_duplicate: bool = False,
        workspace_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> None:
        from app.models.processing_job import JobStatus, JobStep
        from datetime import datetime, timezone
        import time
        import asyncio
        from app.config import get_settings
        
        start_time = time.time()
        settings = get_settings()
        
        async def update_job(step: str, status=None, **kwargs):
            job.current_step = step
            if status:
                job.status = status
            for k, v in kwargs.items():
                setattr(job, k, v)
            job.elapsed_seconds = time.time() - start_time
            job.updated_at = datetime.now(timezone.utc)
            await job.save()

        async def _processing_pipeline():
            await update_job(JobStep.UPLOAD, JobStatus.RUNNING, started_at=datetime.now(timezone.utc))
            
            # EXTRACTION
            if JobStep.EXTRACTION not in job.completed_steps:
                await update_job(JobStep.EXTRACTION)
                if isinstance(document, type(document)): # To avoid circular imports
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
                
                auto_meta = {}
                if result.metadata:
                    auto_meta = {
                        "title": result.metadata.get("title", ""),
                        "author": result.metadata.get("author", ""),
                        "creation_date": result.metadata.get("creationDate", ""),
                        "pages": result.total_pages,
                    }
                
                if isinstance(document, type(document)):
                    document.mark_extracted(pages=extracted_pages, full_text=result.full_text)
                    document.metadata = result.metadata
                    document.auto_metadata = auto_meta
                    await self._repo.update(document)
                
                job.completed_steps.append(JobStep.EXTRACTION)
                job.pages_extracted = result.total_pages
                job.total_pages = result.total_pages
                await update_job(JobStep.CHUNKING)
            else:
                # Need extracted_pages for downstream
                from app.models.document import ExtractedPage
                extracted_pages = document.pages
                result_full_text = document.full_text

            # CHUNKING + EMBEDDING
            if self._chroma_indexer and document.full_text.strip():
                if JobStep.EMBEDDING not in job.completed_steps:
                    if isinstance(document, type(document)):
                        document.status = document.status.CHUNKING
                        await self._repo.update(document)
                    
                    from app.utils.text_splitter import chunk_text, build_page_boundaries
                    page_boundaries = build_page_boundaries([
                        {"page_number": p.page_number, "text": p.text, "sections": p.sections}
                        for p in extracted_pages
                    ])
                    
                    metadata_updates = {"is_global": True}
                    if workspace_id:
                        metadata_updates = {"workspace_id": workspace_id, "is_global": False}
                    
                    chunks = chunk_text(
                        text=document.full_text,
                        document_id=str(document.id),
                        document_name=document.filename,
                        chunk_size=self._chunk_size,
                        chunk_overlap=self._chunk_overlap,
                        page_boundaries=page_boundaries,
                    )
                    for chunk in chunks:
                        chunk.metadata.update(metadata_updates)
                    
                    if JobStep.CHUNKING not in job.completed_steps:
                        job.completed_steps.append(JobStep.CHUNKING)
                    job.chunks_created = len(chunks)
                    await update_job(JobStep.EMBEDDING)
                    
                    if isinstance(document, type(document)):
                        document.status = document.status.EMBEDDING
                        await self._repo.update(document)
                    
                    await self._chroma_indexer.delete_document_chunks(str(document.id))
                    indexed_count = await self._chroma_indexer.index_chunks(chunks)
                    
                    if isinstance(document, type(document)):
                        document.total_chunks = indexed_count
                        await self._repo.update(document)
                    
                    job.completed_steps.append(JobStep.EMBEDDING)
                    job.embeddings_created = indexed_count
                
                # KG INDEXING
                if self._kg_builder and extracted_pages:
                    if JobStep.KG_INDEXING not in job.completed_steps:
                        await update_job(JobStep.KG_INDEXING)
                        if isinstance(document, type(document)):
                            document.status = document.status.INDEXING_KG
                            await self._repo.update(document)
                        
                        # Delete existing entities for idempotency
                        await self._kg_builder.delete_document_entities(str(document.id))
                        
                        total_entities, total_rels = await self._kg_builder.build_from_document(
                            document_id=str(document.id),
                            filename=document.filename,
                            pages=extracted_pages,
                        )
                        document.mark_kg_indexed(total_entities, total_rels)
                        job.kg_nodes_created = total_entities
                        job.kg_relations_created = total_rels
                        job.completed_steps.append(JobStep.KG_INDEXING)
                    
                if isinstance(document, type(document)):
                    document.mark_completed(total_chunks=document.total_chunks)
                    await self._repo.update(document)
            
            # COMPLETED
            job.status = JobStatus.COMPLETED
            job.current_step = JobStep.COMPLETED
            if JobStep.COMPLETED not in job.completed_steps:
                job.completed_steps.append(JobStep.COMPLETED)
            job.completed_at = datetime.now(timezone.utc)
            job.elapsed_seconds = time.time() - start_time
            await job.save()
            
            try:
                from app.services.notification_service import NotificationService
                from app.models.notification import NotificationType
                notif_svc = NotificationService()
                await notif_svc.create(
                    user_id=owner_id or "system",
                    title="Document Indexed Successfully",
                    message=f"'{document.filename}' has been indexed.",
                    notification_type=NotificationType.DOCUMENT_INDEXED,
                    link=f"/docs",
                )
            except Exception:
                pass

        try:
            # Wrap entire pipeline in asyncio.wait_for for global timeout
            timeout_seconds = settings.DOCUMENT_PROCESSING_TIMEOUT_SECONDS
            await asyncio.wait_for(_processing_pipeline(), timeout=timeout_seconds)
            
        except asyncio.TimeoutError:
            logger.error("document_processing_timeout", job_id=str(job.id))
            job.status = JobStatus.TIMEOUT
            job.failed_step = str(job.current_step)
            job.error_message = f"Processing timed out after {timeout_seconds} seconds"
            job.elapsed_seconds = time.time() - start_time
            await job.save()
            if isinstance(document, type(document)):
                document.status = document.status.TIMEOUT
                await self._repo.update(document)
                
        except Exception as exc:
            import traceback
            logger.error("document_background_processing_failed", error=str(exc), traceback=traceback.format_exc())
            from app.core.exceptions import LLMRateLimitError
            
            if isinstance(exc, LLMRateLimitError):
                job.status = JobStatus.RATE_LIMITED
                doc_status = document.status.RATE_LIMITED
            else:
                job.status = JobStatus.FAILED
                doc_status = document.status.FAILED
                
            job.failed_step = str(job.current_step)
            job.error_message = str(exc)
            job.elapsed_seconds = time.time() - start_time
            await job.save()
            
            if isinstance(document, type(document)):
                document.status = doc_status
                document.error_message = str(exc)
                await self._repo.update(document)
"""

new_lines.append(new_func)
new_lines.extend(lines[350:])

with open('backend/app/services/document_service.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
