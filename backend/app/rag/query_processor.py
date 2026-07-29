"""Query Preprocessor for the Hybrid RAG Pipeline.

Performs three operations before retrieval:
    1. Domain guard — rejects non-building queries before they hit any LLM or DB.
    2. Entity extraction — identifies defects, components, repair methods, and materials
       mentioned in the query using regex matching against the building ontology.
    3. Query expansion — appends canonical technical synonyms to improve recall.

This is a purely local, deterministic module. It does NOT call the LLM.
"""

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Building domain ontology dictionaries (shared with curation pipeline)
# ---------------------------------------------------------------------------

BUILDING_DEFECTS = {
    "crack", "cracking", "spalling", "corrosion", "honeycombing",
    "water seepage", "seepage", "efflorescence", "settlement", "dampness",
    "delamination", "carbonation", "chloride attack", "blistering",
    "scaling", "leakage", "deflection", "buckling", "reinforcement exposure",
}

BUILDING_COMPONENTS = {
    "column", "beam", "slab", "footing", "foundation", "wall", "roof",
    "window", "door", "staircase", "lintel", "basement", "plinth",
    "masonry", "shear wall", "balcony", "parapet", "ceiling", "floor",
    "corbel", "pillar", "rcc", "reinforced concrete",
}

REPAIR_METHODS = {
    "epoxy injection", "concrete jacketing", "jacketing", "grouting",
    "waterproofing", "protective coating", "re-plastering", "shotcrete",
    "guniting", "cathodic protection", "crack sealing", "strengthening",
    "polymer modification", "repair mortar", "retrofitting", "rehabilitation",
}

MATERIALS = {
    "concrete", "steel", "rebar", "cement", "mortar", "epoxy",
    "polymer", "bitumen", "brick", "fly ash", "admixture",
}

# Non-building exclusion trigger phrases — if query is PRIMARILY about these, reject
_EXCLUSION_PATTERNS = [
    r"\bhighway\s+bridge\b", r"\brailway\s+bridge\b", r"\bflyover\b",
    r"\bpavement\s+design\b", r"\basphalt\s+pavement\b",
    r"\bdam\s+safety\b", r"\btunnel\s+boring\b", r"\bairport\s+runway\b",
    r"\btraffic\s+signal\b", r"\broad\s+maintenance\b",
]

# Query expansion synonyms for key building concepts
_EXPANSION_MAP: dict[str, list[str]] = {
    "crack": ["cracking", "fracture", "fissure", "hairline crack", "structural crack"],
    "spalling": ["concrete spalling", "concrete spelling", "cover spalling"],
    "corrosion": ["reinforcement corrosion", "rebar corrosion", "steel corrosion", "rusting"],
    "honeycombing": ["voids in concrete", "porous concrete", "honeycomb defect"],
    "seepage": ["water seepage", "dampness", "leakage", "moisture ingress", "water penetration"],
    "column": ["rcc column", "reinforced concrete column", "pillar", "structural column"],
    "beam": ["rcc beam", "lintel", "bending member", "structural beam"],
    "slab": ["roof slab", "floor slab", "rcc slab", "flat slab"],
    "foundation": ["footing", "raft foundation", "pile foundation", "strip footing"],
    "repair": ["rehabilitation", "retrofitting", "strengthening", "restoration"],
}


@dataclass
class ProcessedQuery:
    """Output of the QueryProcessor step.

    Attributes:
        original_query: The unmodified input question.
        expanded_query: The query with synonym expansion appended.
        is_building_domain: False if the query is about non-building infrastructure.
        rejection_reason: Set if is_building_domain is False.
        extracted_defects: Building defects detected in the query.
        extracted_components: Building components detected in the query.
        extracted_repair_methods: Repair/rehabilitation methods detected.
        extracted_materials: Construction materials detected.
        kg_search_terms: Combined terms to use for KG entity search.
    """

    original_query: str
    expanded_query: str
    is_building_domain: bool = True
    rejection_reason: str | None = None
    extracted_defects: list[str] = field(default_factory=list)
    extracted_components: list[str] = field(default_factory=list)
    extracted_repair_methods: list[str] = field(default_factory=list)
    extracted_materials: list[str] = field(default_factory=list)
    kg_search_terms: list[str] = field(default_factory=list)


class QueryProcessor:
    """Preprocesses user queries before they enter the retrieval stage.

    Steps:
        1. Domain validation against exclusion patterns.
        2. Entity extraction from the building ontology.
        3. Query expansion with canonical synonyms.

    This class is fully synchronous and does not perform any I/O.
    """

    def preprocess(self, query: str) -> ProcessedQuery:
        """Process a raw user query into a structured ProcessedQuery.

        Args:
            query: The raw user question.

        Returns:
            ProcessedQuery containing extracted entities, expanded text, and domain flag.
        """
        query = query.strip()
        lower_q = query.lower()

        # --- Step 1: Domain guard ---
        for pattern in _EXCLUSION_PATTERNS:
            if re.search(pattern, lower_q):
                logger.info("query_domain_rejected", query=query[:60], pattern=pattern)
                return ProcessedQuery(
                    original_query=query,
                    expanded_query=query,
                    is_building_domain=False,
                    rejection_reason=(
                        f"This system is restricted to building engineering only. "
                        f"Your query appears to be about non-building infrastructure "
                        f"(matched: '{pattern}'). Please ask questions about RCC buildings, "
                        f"residential, commercial, institutional, or government structures."
                    ),
                )

        # --- Step 2: Entity extraction ---
        defects = [d for d in BUILDING_DEFECTS if re.search(rf"\b{re.escape(d)}\b", lower_q)]
        components = [c for c in BUILDING_COMPONENTS if re.search(rf"\b{re.escape(c)}\b", lower_q)]
        repairs = [r for r in REPAIR_METHODS if re.search(rf"\b{re.escape(r)}\b", lower_q)]
        materials = [m for m in MATERIALS if re.search(rf"\b{re.escape(m)}\b", lower_q)]

        # --- Step 3: Query expansion ---
        expansion_terms: list[str] = []
        all_matched = defects + components + repairs + materials
        for term in all_matched:
            synonyms = _EXPANSION_MAP.get(term, [])
            for syn in synonyms:
                if syn.lower() not in lower_q and syn not in expansion_terms:
                    expansion_terms.append(syn)

        expanded_query = query
        if expansion_terms:
            expanded_query = f"{query} {' '.join(expansion_terms[:6])}"  # Limit expansion to 6 terms

        # KG search terms: prioritize defects and components
        kg_terms = list(dict.fromkeys(defects + components + repairs))[:8]

        logger.debug(
            "query_preprocessed",
            defects=defects,
            components=components,
            repairs=repairs,
            expansion_added=len(expansion_terms),
            kg_terms=kg_terms,
        )

        return ProcessedQuery(
            original_query=query,
            expanded_query=expanded_query,
            is_building_domain=True,
            extracted_defects=defects,
            extracted_components=components,
            extracted_repair_methods=repairs,
            extracted_materials=materials,
            kg_search_terms=kg_terms,
        )
