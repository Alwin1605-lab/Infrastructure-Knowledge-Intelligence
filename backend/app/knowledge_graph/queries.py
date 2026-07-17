"""Building Knowledge Graph query service and Cypher templates.

Provides async query execution methods for retrieving building domain subgraphs,
defect analysis trees, repair recommendations, and formatting structured knowledge graph
context (`kg_context`) for injection into RAG prompts.

Domain: Buildings only (RCC, Residential, Commercial, Institutional, Government).
"""

import json
from typing import Any, Optional

from app.core.exceptions import KGConnectionError, KGQueryError
from app.core.logging import get_logger
from app.knowledge_graph.connection import get_neo4j_driver

logger = get_logger(__name__)


async def get_defect_subgraph(defect_name: str) -> dict[str, Any]:
    """Retrieve all root causes, repair methods, and affected components for a building defect.

    Args:
        defect_name: Name of the building defect (e.g., 'spalling', 'honeycombing', 'corrosion').

    Returns:
        Dictionary containing defect details, causes, repairs, and affected components.

    Raises:
        KGQueryError: If the Cypher query fails.
    """
    normalized_name = defect_name.strip().lower()
    cypher = """
    MATCH (d:Defect)
    WHERE toLower(d.name) CONTAINS $name OR $name CONTAINS toLower(d.name)
    OPTIONAL MATCH (d)-[:CAUSED_BY]->(c:Cause)
    OPTIONAL MATCH (d)-[:REPAIRED_BY]->(r:RepairMethod)
    OPTIONAL MATCH (d)-[:AFFECTS]->(comp:Component)
    OPTIONAL MATCH (r)-[:SPECIFIED_IN]->(std:BuildingStandard)
    RETURN d.name AS defect,
           d.attributes AS attributes,
           collect(DISTINCT c.name) AS causes,
           collect(DISTINCT {repair: r.name, standard: std.name}) AS repairs,
           collect(DISTINCT comp.name) AS affected_components
    LIMIT 5
    """
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(cypher, name=normalized_name)
            records = [record async for record in result]
            if not records:
                return {}

            subgraphs = []
            for rec in records:
                if rec["defect"]:
                    subgraphs.append({
                        "defect": rec["defect"],
                        "attributes": rec["attributes"],
                        "causes": [c for c in rec["causes"] if c],
                        "repairs": [r for r in rec["repairs"] if r.get("repair")],
                        "affected_components": [comp for comp in rec["affected_components"] if comp],
                    })
            return {"defects_found": subgraphs} if subgraphs else {}
    except KGConnectionError:
        logger.debug("kg_query_skipped_no_connection", query="get_defect_subgraph")
        return {}
    except Exception as exc:
        logger.error("kg_defect_subgraph_query_failed", defect=defect_name, error=str(exc))
        raise KGQueryError(f"Failed to query defect subgraph for '{defect_name}': {exc}") from exc


async def get_component_subgraph(component_name: str) -> dict[str, Any]:
    """Retrieve building component details including defects affecting it and materials used.

    Args:
        component_name: Name of the building element (e.g., 'column', 'beam', 'foundation', 'slab').

    Returns:
        Dictionary containing component subgraph.
    """
    normalized_name = component_name.strip().lower()
    cypher = """
    MATCH (comp:Component)
    WHERE toLower(comp.name) CONTAINS $name OR $name CONTAINS toLower(comp.name)
    OPTIONAL MATCH (d:Defect)-[:AFFECTS]->(comp)
    OPTIONAL MATCH (comp)-[:MADE_OF]->(m:Material)
    OPTIONAL MATCH (comp)-[:PART_OF]->(parent:Component)
    RETURN comp.name AS component,
           collect(DISTINCT d.name) AS affecting_defects,
           collect(DISTINCT m.name) AS materials,
           collect(DISTINCT parent.name) AS part_of_system
    LIMIT 5
    """
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(cypher, name=normalized_name)
            records = [record async for record in result]
            if not records:
                return {}

            components = []
            for rec in records:
                if rec["component"]:
                    components.append({
                        "component": rec["component"],
                        "affecting_defects": [d for d in rec["affecting_defects"] if d],
                        "materials": [m for m in rec["materials"] if m],
                        "part_of": [p for p in rec["part_of_system"] if p],
                    })
            return {"components_found": components} if components else {}
    except KGConnectionError:
        return {}
    except Exception as exc:
        logger.error("kg_component_subgraph_query_failed", component=component_name, error=str(exc))
        return {}


async def get_repair_recommendations_from_kg(
    defect_name: str, component_name: Optional[str] = None
) -> list[dict[str, Any]]:
    """Retrieve repair recommendations and standard citations from the building KG."""
    cypher = """
    MATCH (d:Defect)-[:REPAIRED_BY]->(r:RepairMethod)
    WHERE toLower(d.name) CONTAINS $defect_name
    OPTIONAL MATCH (r)-[:SPECIFIED_IN]->(std:BuildingStandard)
    RETURN d.name AS defect,
           r.name AS repair_method,
           collect(DISTINCT std.name) AS standards
    """
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(cypher, defect_name=defect_name.strip().lower())
            records = [record async for record in result]
            repairs = []
            for rec in records:
                repairs.append({
                    "defect": rec["defect"],
                    "repair_method": rec["repair_method"],
                    "standards": [s for s in rec["standards"] if s],
                })
            return repairs
    except Exception:
        return []


async def search_entities_by_text(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for building entities across all labels matching a query string."""
    cypher = """
    MATCH (n)
    WHERE (n:Defect OR n:Cause OR n:Component OR n:Material OR n:RepairMethod OR n:Risk OR n:BuildingStandard)
      AND toLower(n.name) CONTAINS toLower($query)
    RETURN labels(n)[0] AS type, n.name AS name, n.attributes AS attributes
    LIMIT $limit
    """
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(cypher, query=query.strip(), limit=limit)
            records = [record async for record in result]
            return [
                {
                    "type": rec["type"],
                    "name": rec["name"],
                    "attributes": rec["attributes"],
                }
                for rec in records
            ]
    except Exception:
        return []


async def get_document_subgraph(document_id: str) -> dict[str, Any]:
    """Retrieve all building entities and relationships extracted from a specific document."""
    cypher = """
    MATCH (e)-[:MENTIONED_IN]->(d:Document {document_id: $doc_id})
    OPTIONAL MATCH (e)-[r]->(target)-[:MENTIONED_IN]->(d)
    WHERE type(r) <> 'MENTIONED_IN' AND target IS NOT NULL
    RETURN collect(DISTINCT {name: e.name, type: labels(e)[0]}) AS entities,
           collect(DISTINCT {source: e.name, relationship: type(r), target: target.name}) AS relationships
    """
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(cypher, doc_id=document_id)
            record = await result.single()
            if not record:
                return {"entities": [], "relationships": []}
            return {
                "entities": [e for e in record["entities"] if e.get("name")],
                "relationships": [r for r in record["relationships"] if r.get("source") and r.get("target")],
            }
    except Exception:
        return {"entities": [], "relationships": []}


def format_kg_context_for_rag(subgraph_data: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Format structured building knowledge graph data into clear Markdown for RAG context (`kg_context`).

    Args:
        subgraph_data: Dictionary or list returned by KG query methods.

    Returns:
        Formatted string summarizing building entities, defects, causes, and repairs.
    """
    if not subgraph_data:
        return "No specific building knowledge graph entities directly matched the query."

    lines = ["### Building Knowledge Graph Context (Structured Ontology)"]

    if isinstance(subgraph_data, dict):
        if "defects_found" in subgraph_data:
            for d in subgraph_data["defects_found"]:
                lines.append(f"\n- **Defect**: `{d['defect']}`")
                if d.get("causes"):
                    lines.append(f"  - *Root Causes*: {', '.join(d['causes'])}")
                if d.get("repairs"):
                    rep_strs = [
                        f"{r['repair']} (Ref: {r['standard']})" if r.get("standard") else r["repair"]
                        for r in d["repairs"]
                    ]
                    lines.append(f"  - *Repair Methods*: {', '.join(rep_strs)}")
                if d.get("affected_components"):
                    lines.append(f"  - *Affected Components*: {', '.join(d['affected_components'])}")

        elif "components_found" in subgraph_data:
            for c in subgraph_data["components_found"]:
                lines.append(f"\n- **Building Component**: `{c['component']}`")
                if c.get("affecting_defects"):
                    lines.append(f"  - *Affecting Defects*: {', '.join(c['affecting_defects'])}")
                if c.get("materials"):
                    lines.append(f"  - *Materials*: {', '.join(c['materials'])}")
                if c.get("part_of"):
                    lines.append(f"  - *Part of System*: {', '.join(c['part_of'])}")

        elif "entities" in subgraph_data and "relationships" in subgraph_data:
            lines.append("\n**Extracted Document Entities:**")
            for e in subgraph_data["entities"][:15]:
                lines.append(f"- `{e['name']}` ({e['type']})")
            if subgraph_data["relationships"]:
                lines.append("\n**Relationships:**")
                for r in subgraph_data["relationships"][:15]:
                    lines.append(f"- `{r['source']}` --[{r['relationship']}]--> `{r['target']}`")
        else:
            lines.append(f"```json\n{json.dumps(subgraph_data, indent=2)}\n```")

    elif isinstance(subgraph_data, list):
        for item in subgraph_data:
            if isinstance(item, dict) and "defect" in item and "repair_method" in item:
                stds = f" [{', '.join(item['standards'])}]" if item.get("standards") else ""
                lines.append(f"- **Defect `{item['defect']}`** -> Repair by `{item['repair_method']}`{stds}")
            elif isinstance(item, dict) and "name" in item and "type" in item:
                lines.append(f"- `{item['name']}` ({item['type']})")
            else:
                lines.append(f"- {json.dumps(item)}")

    return "\n".join(lines)
