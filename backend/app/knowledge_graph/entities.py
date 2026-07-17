"""Building Knowledge Graph entity definitions and validation models.

Defines the core ontology (types and relationships) for the Building Knowledge Graph
as well as Pydantic models used to validate and structure entity extraction outputs
from the LLM.

Domain: Buildings only (RCC, Residential, Commercial, Institutional, Government).
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class BuildingEntityType(str, Enum):
    """Canonical building entity types in the Knowledge Graph."""

    DEFECT = "Defect"
    CAUSE = "Cause"
    MATERIAL = "Material"
    REPAIR_METHOD = "RepairMethod"
    RISK = "Risk"
    COMPONENT = "Component"
    BUILDING_STANDARD = "BuildingStandard"
    DOCUMENT = "Document"
    PAGE = "Page"

    @classmethod
    def from_string(cls, value: str) -> "BuildingEntityType":
        """Robustly parse string or enum into BuildingEntityType."""
        val = value.strip().replace(" ", "").lower()
        mapping = {
            "defect": cls.DEFECT,
            "cause": cls.CAUSE,
            "material": cls.MATERIAL,
            "repairmethod": cls.REPAIR_METHOD,
            "repair_method": cls.REPAIR_METHOD,
            "repair": cls.REPAIR_METHOD,
            "risk": cls.RISK,
            "component": cls.COMPONENT,
            "buildingcomponent": cls.COMPONENT,
            "buildingstandard": cls.BUILDING_STANDARD,
            "standard": cls.BUILDING_STANDARD,
            "document": cls.DOCUMENT,
            "page": cls.PAGE,
        }
        return mapping.get(val, cls.COMPONENT)  # Default to component if unknown building element


class BuildingRelationshipType(str, Enum):
    """Canonical relationship types between building entities."""

    CAUSED_BY = "CAUSED_BY"
    REPAIRED_BY = "REPAIRED_BY"
    AFFECTS = "AFFECTS"
    MADE_OF = "MADE_OF"
    MITIGATES = "MITIGATES"
    LOCATED_AT = "LOCATED_AT"
    PART_OF = "PART_OF"
    SPECIFIED_IN = "SPECIFIED_IN"
    MENTIONED_IN = "MENTIONED_IN"

    @classmethod
    def from_string(cls, value: str) -> "BuildingRelationshipType":
        """Robustly parse string or enum into BuildingRelationshipType."""
        val = value.strip().upper().replace(" ", "_")
        for rel in cls:
            if rel.value == val:
                return rel
        return cls.MENTIONED_IN  # Fallback general relationship


class ExtractedEntity(BaseModel):
    """A building entity extracted from text by the LLM."""

    name: str = Field(..., description="Canonical normalized name of the entity in lowercase.")
    type: str = Field(..., description="Entity type string or enum value.")
    mentions: list[str] = Field(default_factory=list, description="Text spans where the entity appears.")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Extracted attributes (severity, location, measurement).")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Ensure entity names are trimmed and normalized to lowercase."""
        return v.strip().lower()

    @property
    def canonical_type(self) -> BuildingEntityType:
        """Get the validated BuildingEntityType."""
        return BuildingEntityType.from_string(self.type)


class ExtractedRelationship(BaseModel):
    """A relationship between two building entities extracted by the LLM."""

    source: str = Field(..., description="Canonical name of the source entity.")
    source_type: str = Field(default="Component", description="Type of source entity.")
    relationship: str = Field(..., description="Relationship type enum value.")
    target: str = Field(..., description="Canonical name of the target entity.")
    target_type: str = Field(default="Component", description="Type of target entity.")
    evidence: str = Field(default="", description="Text excerpt supporting this relationship.")

    @field_validator("source", "target")
    @classmethod
    def normalize_entity_names(cls, v: str) -> str:
        """Normalize source and target entity names to lowercase."""
        return v.strip().lower()

    @property
    def canonical_relationship(self) -> BuildingRelationshipType:
        """Get the validated BuildingRelationshipType."""
        return BuildingRelationshipType.from_string(self.relationship)

    @property
    def canonical_source_type(self) -> BuildingEntityType:
        """Get the validated source BuildingEntityType."""
        return BuildingEntityType.from_string(self.source_type)

    @property
    def canonical_target_type(self) -> BuildingEntityType:
        """Get the validated target BuildingEntityType."""
        return BuildingEntityType.from_string(self.target_type)


class ExtractedGraph(BaseModel):
    """Container for all entities and relationships extracted from a document or chunk."""

    entities: list[ExtractedEntity] = Field(default_factory=list, description="List of extracted building entities.")
    relationships: list[ExtractedRelationship] = Field(default_factory=list, description="List of relationships between entities.")

    def merge(self, other: "ExtractedGraph") -> "ExtractedGraph":
        """Merge another extracted graph into this one, deduplicating entities and relationships by name/type."""
        entity_map = {(e.name, e.canonical_type.value): e for e in self.entities}
        for e in other.entities:
            key = (e.name, e.canonical_type.value)
            if key in entity_map:
                # Merge mentions and attributes
                existing = entity_map[key]
                existing.mentions = list(set(existing.mentions + e.mentions))
                existing.attributes.update(e.attributes)
            else:
                entity_map[key] = e

        rel_set = {(r.source, r.canonical_relationship.value, r.target) for r in self.relationships}
        new_rels = list(self.relationships)
        for r in other.relationships:
            key = (r.source, r.canonical_relationship.value, r.target)
            if key not in rel_set:
                rel_set.add(key)
                new_rels.append(r)

        return ExtractedGraph(
            entities=list(entity_map.values()),
            relationships=new_rels,
        )
