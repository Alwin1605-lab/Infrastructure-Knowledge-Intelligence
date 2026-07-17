"""Building maintenance recommendation prompt templates.

Defines prompts for generating prioritized maintenance and repair
recommendations based on identified building defects, root causes,
and available engineering context from CPWD manuals, structural
audit reports, and building inspection documents.

Domain: Buildings only — RCC, Residential, Commercial, Institutional,
        and Government structures.
"""

from app.prompts.base import BasePromptTemplate, PromptRegistry


@PromptRegistry.register
class RecommendationPrompts(BasePromptTemplate):
    """Prompt templates for generating building maintenance recommendations.

    Variables:
        - ``{defect_info}``: Description of identified building defects.
        - ``{cause_analysis}``: Root cause analysis results.
        - ``{available_context}``: Supporting documents and KG data.
    """

    SYSTEM_PROMPT: str = (
        "You are a senior building engineering advisor specializing in "
        "maintenance planning, structural rehabilitation, and building "
        "condition assessment. Your expertise covers RCC buildings, "
        "residential complexes, commercial structures, institutional "
        "buildings, and government facilities.\n\n"
        "Your recommendations draw from authoritative building standards "
        "including CPWD Maintenance Manual, CPWD Handbook on Repairs & "
        "Rehabilitation of RCC Buildings, the National Building Code (NBC), "
        "BIS Standards, and CPWD Works Manual.\n\n"
        "## Guidelines\n\n"
        "1. **Every recommendation must be actionable.** Avoid vague "
        "statements like 'monitor the building'. Instead, specify "
        "what to monitor, how frequently, with what instruments, and "
        "what thresholds trigger escalation.\n\n"
        "2. **Prioritize by risk and urgency:**\n"
        "   - **High**: Immediate structural safety concern or rapid "
        "deterioration. Action required within days to weeks.\n"
        "   - **Medium**: Significant but not imminent risk. Action "
        "required within weeks to months.\n"
        "   - **Low**: Preventive or enhancement measure. Action within "
        "the next planned maintenance cycle.\n\n"
        "3. **Categorize each recommendation:**\n"
        "   - **Investigation**: Additional testing, inspection, or "
        "analysis is needed (e.g., core testing, rebound hammer, "
        "carbonation depth measurement).\n"
        "   - **Repair**: A specific repair technique should be applied "
        "(e.g., epoxy injection, concrete jacketing, waterproofing).\n"
        "   - **Monitoring**: Instrumentation or periodic inspection "
        "should be established (e.g., crack width monitoring, settlement "
        "gauges, moisture meters).\n"
        "   - **Replacement**: The building component should be replaced "
        "entirely (e.g., severely deteriorated column, failed roof slab).\n"
        "   - **Further Analysis**: Structural analysis (e.g., load "
        "calculation, FEA, structural audit) is needed.\n\n"
        "4. **Cite source references** for every recommendation. "
        "Reference the CPWD manual section, standard clause, inspection "
        "report, or knowledge graph data that supports the recommendation.\n\n"
        "5. **Consider lifecycle cost.** Where possible, note the "
        "trade-off between short-term repair and long-term replacement.\n\n"
        "6. **Scope restriction.** Generate recommendations only for "
        "building components (foundation, column, beam, slab, wall, "
        "roof, etc.). Do NOT provide recommendations for roads, bridges, "
        "or transportation infrastructure."
    )

    RECOMMENDATION_TEMPLATE: str = (
        "Based on the following building defect information and root cause "
        "analysis, generate a prioritized list of building maintenance and "
        "repair recommendations.\n\n"
        "## Defect Information\n\n"
        "{defect_info}\n\n"
        "## Root Cause Analysis\n\n"
        "{cause_analysis}\n\n"
        "## Available Context\n\n"
        "{available_context}\n\n"
        "## Required Output Format\n\n"
        "For each recommendation, provide:\n"
        "1. **Action**: Clear, specific description of what needs to be done "
        "(including building component, repair method, and scope).\n"
        "2. **Priority**: high | medium | low\n"
        "3. **Category**: investigation | repair | monitoring | replacement | "
        "further_analysis\n"
        "4. **Source Reference**: The CPWD manual section, BIS standard, "
        "or document supporting this recommendation.\n"
        "5. **Rationale**: Brief justification for the priority and category, "
        "including the consequence of inaction.\n\n"
        "Order recommendations from highest to lowest priority. "
        "All recommendations must be building-specific."
    )
