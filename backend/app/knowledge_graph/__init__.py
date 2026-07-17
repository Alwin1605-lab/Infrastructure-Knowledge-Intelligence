"""Building Knowledge Graph package.

Provides connection management (`init_kg`, `close_kg`, `get_neo4j_driver`),
canonical building ontology & validation models (`BuildingEntityType`, `ExtractedGraph`),
graph extraction builder (`KGBuilder`), and Cypher retrieval queries (`get_defect_subgraph`, etc.).

Domain: Buildings only (RCC, Residential, Commercial, Institutional, Government).
"""

from app.knowledge_graph.connection import (
    init_kg,
    close_kg,
    get_neo4j_driver,
    get_neo4j_session,
)
from app.knowledge_graph.entities import (
    BuildingEntityType,
    BuildingRelationshipType,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractedGraph,
)
from app.knowledge_graph.builder import KGBuilder
from app.knowledge_graph.queries import (
    get_defect_subgraph,
    get_component_subgraph,
    get_repair_recommendations_from_kg,
    search_entities_by_text,
    get_document_subgraph,
    format_kg_context_for_rag,
)

__all__ = [
    "init_kg",
    "close_kg",
    "get_neo4j_driver",
    "get_neo4j_session",
    "BuildingEntityType",
    "BuildingRelationshipType",
    "ExtractedEntity",
    "ExtractedRelationship",
    "ExtractedGraph",
    "KGBuilder",
    "get_defect_subgraph",
    "get_component_subgraph",
    "get_repair_recommendations_from_kg",
    "search_entities_by_text",
    "get_document_subgraph",
    "format_kg_context_for_rag",
]
