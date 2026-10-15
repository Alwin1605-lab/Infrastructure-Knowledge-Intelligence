"""Building Knowledge Graph builder service.

Orchestrates the extraction of building entities and relationships from documents
using the LLM provider layer, validates extracted data against the building ontology,
and persists the consolidated graph nodes and edges into Neo4j using idempotent Cypher queries.

Domain: Buildings only (RCC, Residential, Commercial, Institutional, Government).
"""

import json
import re
from typing import Optional
import asyncio

from app.config import get_settings
from app.core.exceptions import KGBuildError, KGConnectionError, LLMRateLimitError
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.models.document import ExtractedPage
from app.prompts.entity_extraction import EntityExtractionPrompts
from app.knowledge_graph.connection import get_neo4j_driver
from app.knowledge_graph.entities import (
    ExtractedGraph,
    ExtractedEntity,
    ExtractedRelationship,
    BuildingEntityType,
    BuildingRelationshipType,
)

logger = get_logger(__name__)


class KGBuilder:
    """Orchestrates building knowledge graph extraction and Neo4j construction.

    Args:
        llm_provider: The active LLM provider used for entity and relationship extraction.
    """

    def __init__(self, llm_provider: BaseLLMProvider) -> None:
        self._llm = llm_provider
        self.settings = get_settings()

    async def _extract_with_retry(self, coro_func, *args, **kwargs):
        """Execute a coroutine with exponential backoff on rate limits."""
        max_retries = self.settings.MAX_RETRIES
        base_delay = 5.0
        
        for attempt in range(max_retries):
            try:
                return await coro_func(*args, **kwargs)
            except LLMRateLimitError as e:
                if attempt == max_retries - 1:
                    logger.error("kg_max_retries_exceeded", error=str(e))
                    raise
                
                delay = e.retry_after if getattr(e, 'retry_after', None) else base_delay * (2 ** attempt)
                logger.warning(f"Rate limited. Retrying in {delay} seconds...", attempt=attempt+1, max_retries=max_retries)
                await asyncio.sleep(delay)
            except Exception as e:
                # Other exceptions bubble up immediately
                raise

    async def build_from_document(
        self,
        document_id: str,
        filename: str,
        pages: list[ExtractedPage],
        max_pages_to_process: int = 15,
    ) -> tuple[int, int]:
        """Extract entities and relationships from a document and store in Neo4j.

        Args:
            document_id: MongoDB ID of the source building document.
            filename: Original document filename.
            pages: List of ExtractedPage objects with text content.
            max_pages_to_process: Maximum pages to run LLM extraction on to limit latency/tokens.

        Returns:
            Tuple of (total_entities_stored, total_relationships_stored).

        Raises:
            KGBuildError: If extraction or graph storage fails critically.
        """
        if not pages:
            logger.warning("kg_build_skipped_no_pages", document_id=document_id)
            return 0, 0

        logger.info(
            "kg_build_started",
            document_id=document_id,
            filename=filename,
            total_pages=len(pages),
        )

        consolidated_graph = ExtractedGraph()
        pages_to_process = pages[:max_pages_to_process]

        for i in range(0, len(pages_to_process), self.settings.KG_BATCH_SIZE_PAGES):
            batch = pages_to_process[i:i + self.settings.KG_BATCH_SIZE_PAGES]
            
            for p in batch:
                if not p.text or not p.text.strip():
                    continue

                try:
                    # Step 1: Extract entities from page text with retry
                    entities_graph = await self._extract_with_retry(self._extract_entities_from_text, p.text)
                    if not entities_graph.entities:
                        continue

                    # Step 2: Extract relationships given the extracted entities and text with retry
                    entities_json_str = json.dumps(
                        [{"name": e.name, "type": e.canonical_type.value} for e in entities_graph.entities],
                        indent=2,
                    )
                    relationships_graph = await self._extract_with_retry(
                        self._extract_relationships_from_text, p.text, entities_json_str
                    )

                    # Combine into single page graph
                    page_graph = ExtractedGraph(
                        entities=entities_graph.entities,
                        relationships=relationships_graph.relationships,
                    )
                    consolidated_graph = consolidated_graph.merge(page_graph)

                    logger.debug(
                        "kg_page_extracted",
                        document_id=document_id,
                        page_number=p.page_number,
                        entities=len(entities_graph.entities),
                        relationships=len(relationships_graph.relationships),
                    )
                except LLMRateLimitError:
                    # Rate limit exceeded even after retries, bubble up to trigger RATE_LIMITED state
                    logger.error("kg_batch_rate_limit_exceeded_bubbling_up", document_id=document_id)
                    raise
                except Exception as exc:
                    logger.warning(
                        "kg_page_extraction_error",
                        document_id=document_id,
                        page_number=p.page_number,
                        error=str(exc),
                    )
                    continue

        logger.info(
            "kg_extraction_complete",
            document_id=document_id,
            total_unique_entities=len(consolidated_graph.entities),
            total_unique_relationships=len(consolidated_graph.relationships),
        )

        # Step 3: Persist into Neo4j if driver is connected
        try:
            driver = get_neo4j_driver()
        except KGConnectionError:
            logger.warning(
                "neo4j_unavailable_for_kg_build",
                document_id=document_id,
                note="Extracted entities graph skipped saving to Neo4j.",
            )
            return len(consolidated_graph.entities), len(consolidated_graph.relationships)

        try:
            await self._store_graph_in_neo4j(driver, document_id, filename, consolidated_graph)
            return len(consolidated_graph.entities), len(consolidated_graph.relationships)
        except Exception as exc:
            logger.error("kg_storage_failed", document_id=document_id, error=str(exc))
            raise KGBuildError(f"Failed to save building graph to Neo4j: {exc}") from exc

    async def _extract_entities_from_text(self, text: str) -> ExtractedGraph:
        """Call LLM with EntityExtractionPrompts.EXTRACTION_TEMPLATE."""
        prompt = EntityExtractionPrompts.EXTRACTION_TEMPLATE.format(text=text[:3000])
        response = await self._llm.generate(
            prompt=prompt,
            system_prompt=EntityExtractionPrompts.SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=2048,
        )

        raw_json = self._clean_json_output(response.content)
        if not raw_json:
            return ExtractedGraph()

        try:
            data = json.loads(raw_json)
            raw_entities = data.get("entities", [])
            valid_entities = []
            for item in raw_entities:
                if isinstance(item, dict) and "name" in item and "type" in item:
                    valid_entities.append(
                        ExtractedEntity(
                            name=item["name"],
                            type=item["type"],
                            mentions=item.get("mentions", []) if isinstance(item.get("mentions"), list) else [],
                            attributes=item.get("attributes", {}) if isinstance(item.get("attributes"), dict) else {},
                        )
                    )
            return ExtractedGraph(entities=valid_entities)
        except Exception as exc:
            logger.debug("json_parse_error_entities", error=str(exc), response_snippet=response.content[:200])
            return ExtractedGraph()

    async def _extract_relationships_from_text(self, text: str, entities_json: str) -> ExtractedGraph:
        """Call LLM with EntityExtractionPrompts.RELATIONSHIP_TEMPLATE."""
        prompt_text = f"Text:\n{text[:2000]}\n\nEntities:\n{entities_json}"
        prompt = EntityExtractionPrompts.RELATIONSHIP_TEMPLATE.format(text=prompt_text)
        response = await self._llm.generate(
            prompt=prompt,
            system_prompt=EntityExtractionPrompts.SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=2048,
        )

        raw_json = self._clean_json_output(response.content)
        if not raw_json:
            return ExtractedGraph()

        try:
            data = json.loads(raw_json)
            raw_rels = data.get("relationships", [])
            valid_rels = []
            for item in raw_rels:
                if (
                    isinstance(item, dict)
                    and "source" in item
                    and "relationship" in item
                    and "target" in item
                ):
                    valid_rels.append(
                        ExtractedRelationship(
                            source=item["source"],
                            source_type=item.get("source_type", "Component"),
                            relationship=item["relationship"],
                            target=item["target"],
                            target_type=item.get("target_type", "Component"),
                            evidence=str(item.get("evidence", "")),
                        )
                    )
            return ExtractedGraph(relationships=valid_rels)
        except Exception as exc:
            logger.debug("json_parse_error_rels", error=str(exc), response_snippet=response.content[:200])
            return ExtractedGraph()

    @staticmethod
    def _clean_json_output(content: str) -> Optional[str]:
        """Extract JSON code block or object from LLM output."""
        content = content.strip()
        # Check for markdown code block
        codeblock_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if codeblock_match:
            return codeblock_match.group(1).strip()
        # Check for raw JSON object
        json_match = re.search(r"(\{.*\})", content, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        return None

    async def _store_graph_in_neo4j(
        self, driver, document_id: str, filename: str, graph: ExtractedGraph
    ) -> None:
        """Upsert Document node, Page/Entity nodes, and relationships using MERGE."""
        async with driver.session() as session:
            # 1. Upsert Document node
            await session.run(
                """
                MERGE (d:Document {document_id: $doc_id})
                SET d.filename = $filename,
                    d.domain = 'building_knowledge',
                    d.updated_at = datetime()
                """,
                doc_id=document_id,
                filename=filename,
            )

            # 2. Upsert Entities & connect to Document
            for e in graph.entities:
                label = e.canonical_type.value
                # Cypher doesn't allow parameters for labels directly, so we format securely with whitelist
                if label not in [t.value for t in BuildingEntityType]:
                    label = "Component"

                cypher = f"""
                MERGE (e:{label} {{name: $name}})
                ON CREATE SET e.created_at = datetime()
                SET e.attributes = $attributes
                WITH e
                MATCH (d:Document {{document_id: $doc_id}})
                MERGE (e)-[:MENTIONED_IN]->(d)
                """
                await session.run(
                    cypher,
                    name=e.name,
                    attributes=json.dumps(e.attributes),
                    doc_id=document_id,
                )

            # 3. Upsert Relationships
            for r in graph.relationships:
                src_label = r.canonical_source_type.value
                tgt_label = r.canonical_target_type.value
                rel_type = r.canonical_relationship.value

                if src_label not in [t.value for t in BuildingEntityType]:
                    src_label = "Component"
                if tgt_label not in [t.value for t in BuildingEntityType]:
                    tgt_label = "Component"
                if rel_type not in [t.value for t in BuildingRelationshipType]:
                    rel_type = "MENTIONED_IN"

                cypher = f"""
                MERGE (src:{src_label} {{name: $source}})
                MERGE (tgt:{tgt_label} {{name: $target}})
                MERGE (src)-[r:{rel_type}]->(tgt)
                ON CREATE SET r.evidence = $evidence, r.created_at = datetime()
                SET r.updated_at = datetime()
                """
                await session.run(
                    cypher,
                    source=r.source,
                    target=r.target,
                    evidence=r.evidence,
                )

    async def delete_document_entities(self, document_id: str) -> bool:
        """Remove a document node and detach its relationships from Neo4j."""
        try:
            driver = get_neo4j_driver()
        except KGConnectionError:
            return False

        async with driver.session() as session:
            try:
                await session.run(
                    """
                    MATCH (d:Document {document_id: $doc_id})
                    DETACH DELETE d
                    """,
                    doc_id=document_id,
                )
                logger.info("kg_document_node_deleted", document_id=document_id)
                return True
            except Exception as exc:
                logger.error("kg_delete_failed", document_id=document_id, error=str(exc))
                return False
