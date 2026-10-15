import httpx
import os
from bson import ObjectId
from typing import List
from app.models.acquisition import AcquiredDocument, AcquisitionStatus
from app.services.connectors.openalex import OpenAlexConnector

class AcquisitionService:
    @staticmethod
    async def run_search(query: str = "", connector_type: str = "openalex", author: str = "", year: str = "", journal: str = "", limit: int = 50):
        """Search metadata and return raw results without saving."""
        if connector_type.lower() == "openalex":
            connector = OpenAlexConnector()
        else:
            raise ValueError(f"Unknown connector type: {connector_type}")

        metadata_results = await connector.search_metadata(query=query, author=author, year=year, journal=journal, limit=limit)
        return metadata_results

    @staticmethod
    async def import_doi(doi: str) -> AcquiredDocument:
        """Fetch metadata by DOI using OpenAlex and save it."""
        url = f"https://api.openalex.org/works/{doi}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise Exception(f"Failed to fetch DOI metadata. Status: {resp.status_code}")
            
            item = resp.json()
            authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
            
            doc = AcquiredDocument(
                title=item.get("title", "Untitled"),
                authors=authors,
                year=item.get("publication_year"),
                doi=item.get("doi"),
                source_url=item.get("id"),
                pdf_url=item.get("open_access", {}).get("oa_url"),
                status=AcquisitionStatus.METADATA_REVIEW
            )
            await doc.insert()
            return doc

    @staticmethod
    async def download_document(doc_id: str) -> AcquiredDocument:
        """Download document PDF and update its status."""
        doc = await AcquiredDocument.get(ObjectId(doc_id))
        if not doc:
            raise ValueError(f"Document with id {doc_id} not found.")
        
        if not doc.pdf_url:
            raise ValueError("Document does not have a PDF URL.")

        doc.status = AcquisitionStatus.DOWNLOADING
        await doc.save()

        try:
            os.makedirs("uploads", exist_ok=True)
            local_path = f"uploads/temp_{str(doc.id)}.pdf"

            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(doc.pdf_url)
                if resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                    doc.local_file_path = local_path
                    doc.status = AcquisitionStatus.FULL_REVIEW
                    
                    # Mock LLM scoring
                    doc.relevance_score = 0.8
                    doc.value_score = 0.8
                    doc.rag_suitability = 0.8
                    doc.kg_suitability = 0.8
                    doc.quality_summary = "Mocked quality summary."
                    
                    await doc.save()
                    return doc
                else:
                    raise Exception(f"Download failed with status {resp.status_code}")
        except Exception as e:
            doc.status = AcquisitionStatus.ERROR
            doc.error_message = str(e)
            await doc.save()
            raise e
