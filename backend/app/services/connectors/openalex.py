import httpx
from .base import BaseConnector
from typing import List, Dict, Any

class OpenAlexConnector(BaseConnector):
    async def search_metadata(self, query: str = "", author: str = "", year: str = "", journal: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """Search OpenAlex for metadata with strict OA filters and advanced params."""
        filters = ["has_pdf_url:true", "is_oa:true"]
        
        if author:
            filters.append(f"author.id:{author}") # Note: In a real app we might search author names, but OpenAlex prefers ORCID/IDs for exact matches, or we use default search.
            
        if year:
            filters.append(f"publication_year:{year}")
            
        if journal:
            filters.append(f"primary_location.source.id:{journal}")
            
        filter_str = ",".join(filters)
        
        url = f"https://api.openalex.org/works?filter={filter_str}&per-page={limit}"
        if query:
            url += f"&search={query}"
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json().get("results", [])
            results = []
            for item in data:
                authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
                results.append({
                    "title": item.get("title", "Untitled"),
                    "authors": authors,
                    "year": item.get("publication_year"),
                    "doi": item.get("doi"),
                    "source_url": item.get("id"),
                    "pdf_url": item.get("open_access", {}).get("oa_url")
                })
            return results
