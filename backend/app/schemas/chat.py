"""Pydantic schemas for the structured AI response.

Defines the complete 7-field response structure that every AI query returns:
    1. answer              — The generated answer text
    2. sources             — Source documents with citations
    3. kg_context          — Knowledge graph entity context
    4. confidence          — Confidence score with grounding info
    5. recommendations     — Engineering recommendations
    6. related_components  — Related building components
    7. response_time       — Timing breakdown

Domain: Building Knowledge Intelligence — buildings only.
Also defines the ChatRequest schema for incoming queries.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models for the structured response
# ---------------------------------------------------------------------------


class SourceDocument(BaseModel):
    """A source document referenced in the AI response."""

    document_name: str = Field(
        ...,
        description="Name of the source document.",
    )
    page: int | None = Field(
        default=None,
        description="Page number in the document (1-indexed), if applicable.",
    )
    section: str | None = Field(
        default=None,
        description="Section or heading within the document.",
    )
    chunk_preview: str = Field(
        ...,
        description="Short preview of the relevant text chunk.",
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Semantic similarity score between the query and this chunk.",
    )


class KGRelationship(BaseModel):
    """A relationship edge in the knowledge graph context."""

    type: str = Field(
        ...,
        description="Relationship type (e.g., CAUSED_BY, REPAIRED_BY, AFFECTS).",
    )
    target: str = Field(
        ...,
        description="Target entity name.",
    )
    target_type: str = Field(
        ...,
        description="Type of the target entity (e.g., Defect, Material, Cause).",
    )


class KGEntityContext(BaseModel):
    """A knowledge graph entity with its relationships."""

    entity: str = Field(
        ...,
        description="Entity name as it appears in the knowledge graph.",
    )
    type: str = Field(
        ...,
        description="Entity type (e.g., Defect, Cause, Material, Component).",
    )
    relationships: list[KGRelationship] = Field(
        default_factory=list,
        description="Relationships connecting this entity to others.",
    )


class ConfidenceScore(BaseModel):
    """Confidence assessment for the AI response."""

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 (no confidence) and 1.0 (full confidence).",
    )
    level: Literal["high", "medium", "low", "insufficient"] = Field(
        ...,
        description="Human-readable confidence level.",
    )
    grounding: Literal[
        "rag_and_kg", "rag_only", "kg_only", "insufficient_context"
    ] = Field(
        ...,
        description="Source of grounding for the response.",
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this confidence level was assigned.",
    )


class EngineeringRecommendation(BaseModel):
    """A specific engineering recommendation with prioritization."""

    action: str = Field(
        ...,
        description="Recommended action to take.",
    )
    priority: Literal["high", "medium", "low"] = Field(
        ...,
        description="Priority level of the recommendation.",
    )
    category: Literal[
        "investigation", "repair", "monitoring", "replacement", "further_analysis"
    ] = Field(
        ...,
        description="Category of the recommended action.",
    )
    source_reference: str | None = Field(
        default=None,
        description="Reference to the source document supporting this recommendation.",
    )


class RelatedComponent(BaseModel):
    """A building component related to the query context."""

    name: str = Field(
        ...,
        description="Component name (e.g., 'RCC Column', 'Roof Slab', 'Foundation').",
    )
    type: str = Field(
        ...,
        description="Component type (e.g., 'Structural Element', 'Foundation System', 'Envelope').",
    )
    related_defects: list[str] = Field(
        default_factory=list,
        description="Defects commonly associated with this building component.",
    )
    related_materials: list[str] = Field(
        default_factory=list,
        description="Materials this building component is made of.",
    )
    connection: str | None = Field(
        default=None,
        description="How this building component relates to the query context.",
    )


class ResponseTime(BaseModel):
    """Timing breakdown for the AI response pipeline."""

    total_ms: float = Field(
        ...,
        description="Total response time in milliseconds.",
    )
    retrieval_ms: float = Field(
        ...,
        description="Time spent on vector store retrieval.",
    )
    kg_lookup_ms: float = Field(
        ...,
        description="Time spent on knowledge graph lookup.",
    )
    llm_generation_ms: float = Field(
        ...,
        description="Time spent on LLM text generation.",
    )
    post_processing_ms: float = Field(
        ...,
        description="Time spent on post-processing (parsing, assembly).",
    )


# ---------------------------------------------------------------------------
# Main response and request models
# ---------------------------------------------------------------------------


class ChatResponse(BaseModel):
    """Complete structured AI response with all 7 mandatory fields.

    Every query to the system returns this structure, ensuring consistent
    source attribution, confidence scoring, and actionable recommendations.
    """

    answer: str = Field(
        ...,
        description="The AI-generated answer to the user's question.",
    )
    sources: list[SourceDocument] = Field(
        default_factory=list,
        description="Source documents referenced in the answer.",
    )
    kg_context: list[KGEntityContext] = Field(
        default_factory=list,
        description="Knowledge graph entities relevant to the answer.",
    )
    confidence: ConfidenceScore = Field(
        ...,
        description="Confidence assessment for the response.",
    )
    recommendations: list[EngineeringRecommendation] = Field(
        default_factory=list,
        description="Engineering recommendations based on the analysis.",
    )
    related_components: list[RelatedComponent] = Field(
        default_factory=list,
        description="Building components related to the query.",
    )
    response_time: ResponseTime = Field(
        ...,
        description="Timing breakdown for the response pipeline.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "Spalling in RCC columns is typically caused by corrosion of embedded steel reinforcement. As reinforcement corrodes, the resulting iron oxide products occupy a larger volume than the original steel, generating expansive pressure that cracks and eventually dislodges the concrete cover. This is referenced in the CPWD Handbook on Repairs & Rehabilitation of RCC Buildings, Section 4.3.",
                    "sources": [
                        {
                            "document_name": "CPWD Handbook on Repairs & Rehabilitation of RCC Buildings.pdf",
                            "page": 47,
                            "section": "4.3 Spalling Due to Corrosion",
                            "chunk_preview": "Spalling was observed on the ground floor columns. Corrosion stains visible on the concrete surface...",
                            "relevance_score": 0.94,
                        }
                    ],
                    "kg_context": [
                        {
                            "entity": "spalling",
                            "type": "Defect",
                            "relationships": [
                                {
                                    "type": "CAUSED_BY",
                                    "target": "corrosion",
                                    "target_type": "Cause",
                                },
                                {
                                    "type": "REPAIRED_BY",
                                    "target": "concrete jacketing",
                                    "target_type": "RepairMethod",
                                },
                                {
                                    "type": "AFFECTS",
                                    "target": "column",
                                    "target_type": "Component",
                                },
                            ],
                        }
                    ],
                    "confidence": {
                        "score": 0.91,
                        "level": "high",
                        "grounding": "rag_and_kg",
                        "reasoning": "Answer grounded in 2 CPWD source documents and 4 KG entities.",
                    },
                    "recommendations": [
                        {
                            "action": "Conduct half-cell potential test and carbonation depth measurement on affected columns",
                            "priority": "high",
                            "category": "investigation",
                            "source_reference": "CPWD Handbook on Repairs & Rehabilitation of RCC Buildings, Section 4.1",
                        },
                        {
                            "action": "Apply concrete jacketing with anti-corrosion treatment to severely spalled columns",
                            "priority": "high",
                            "category": "repair",
                            "source_reference": "CPWD Maintenance Manual, Chapter 6",
                        },
                    ],
                    "related_components": [
                        {
                            "name": "RCC Column",
                            "type": "Structural Element",
                            "related_defects": ["Spalling", "Cracking", "Honeycombing"],
                            "related_materials": ["Reinforced Concrete", "Steel Reinforcement"],
                            "connection": "Primary load-bearing element affected by corrosion-induced spalling",
                        },
                        {
                            "name": "Beam",
                            "type": "Structural Element",
                            "related_defects": ["Spalling", "Deflection"],
                            "related_materials": ["Reinforced Concrete"],
                            "connection": "Connected element that may be affected if column capacity is compromised",
                        },
                    ],
                    "response_time": {
                        "total_ms": 1923.0,
                        "retrieval_ms": 318.0,
                        "kg_lookup_ms": 152.0,
                        "llm_generation_ms": 1340.0,
                        "post_processing_ms": 113.0,
                    },
                }
            ]
        }
    }


class ChatRequest(BaseModel):
    """Request schema for the chat/query endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question about building engineering, maintenance, or structural assessment.",
    )
    include_kg_context: bool = Field(
        default=True,
        description="Whether to include knowledge graph context in the response.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of document chunks to retrieve for context.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What causes spalling in RCC columns and how should it be repaired?",
                    "include_kg_context": True,
                    "top_k": 5,
                },
                {
                    "question": "What does the CPWD manual recommend for water seepage in buildings?",
                    "include_kg_context": True,
                    "top_k": 5,
                },
            ]
        }
    }
