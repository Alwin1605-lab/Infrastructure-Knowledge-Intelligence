"""Unit tests for Building Knowledge Graph builder and query endpoints.

Tests entity extraction parsing, relationship validation, and KG query error handling.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch
from app.knowledge_graph.builder import KGBuilder, ExtractedEntity, ExtractedRelationship
from app.knowledge_graph.entities import BuildingEntityType, BuildingRelationshipType
from app.core.exceptions import KGBuildError, KGQueryError


@pytest.mark.asyncio
async def test_kg_builder_entity_parsing(mock_llm_provider):
    """Test parsing of LLM entity extraction JSON into Pydantic models."""
    builder = KGBuilder(llm_provider=mock_llm_provider)
    
    sample_llm_output = json.dumps({
        "entities": [
            {
                "name": "spalling",
                "type": "Defect",
                "mentions": ["spalling on column"],
                "attributes": {"severity": "high"}
            },
            {
                "name": "column",
                "type": "Component",
                "mentions": ["RCC columns"]
            }
        ]
    })
    
    mock_llm_provider.generate.return_value = AsyncMock(content=sample_llm_output)
    
    graph = await builder._extract_entities_from_text("spalling on column")
    
    assert len(graph.entities) == 2
    assert graph.entities[0].name == "spalling"
    assert graph.entities[0].type == "Defect"
    assert graph.entities[1].name == "column"
    assert graph.entities[1].type == "Component"


@pytest.mark.asyncio
async def test_kg_builder_relationship_parsing(mock_llm_provider):
    """Test parsing of LLM relationship extraction JSON."""
    builder = KGBuilder(llm_provider=mock_llm_provider)
    
    sample_rels_output = json.dumps({
        "relationships": [
            {
                "source": "spalling",
                "source_type": "Defect",
                "relationship": "AFFECTS",
                "target": "column",
                "target_type": "Component",
                "evidence": "spalling on column"
            }
        ]
    })
    
    mock_llm_provider.generate.return_value = AsyncMock(content=sample_rels_output)
    
    graph = await builder._extract_relationships_from_text("spalling on column", "[]")
    
    assert len(graph.relationships) == 1
    assert graph.relationships[0].source == "spalling"
    assert graph.relationships[0].relationship == "AFFECTS"
    assert graph.relationships[0].target == "column"


def test_entity_and_relationship_types():
    """Verify strictly allowed building entity types and relationship types."""
    assert BuildingEntityType.DEFECT.value == "Defect"
    assert BuildingEntityType.COMPONENT.value == "Component"
    assert BuildingEntityType.REPAIR_METHOD.value == "RepairMethod"
    
    assert BuildingRelationshipType.CAUSED_BY.value == "CAUSED_BY"
    assert BuildingRelationshipType.REPAIRED_BY.value == "REPAIRED_BY"
    assert BuildingRelationshipType.AFFECTS.value == "AFFECTS"
