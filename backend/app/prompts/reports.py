"""Building assessment report generation prompt templates.

Defines prompts for producing structured technical reports for building
condition assessment, structural inspection, and maintenance planning.
Reports are aligned with CPWD standards and building engineering norms.

Report Types:
    - Building Inspection Report
    - Building Condition Assessment
    - Building Maintenance Recommendation Report
    - Structural Defect Analysis Report

Domain: Buildings only — RCC, Residential, Commercial, Institutional,
        and Government structures.
"""

from app.prompts.base import BasePromptTemplate, PromptRegistry


@PromptRegistry.register
class ReportPrompts(BasePromptTemplate):
    """Prompt templates for building assessment report generation.

    Variables:
        - ``{executive_summary_context}``: High-level findings for the executive summary.
        - ``{defect_details}``: Detailed defect descriptions and measurements.
        - ``{cause_analysis}``: Root cause analysis results.
        - ``{recommendations}``: Generated repair/maintenance recommendations.
        - ``{risk_assessment}``: Risk evaluation data and scores.
    """

    SYSTEM_PROMPT: str = (
        "You are a professional technical report writer specializing in "
        "building condition assessment, structural inspection, and building "
        "maintenance engineering. Your reports are used by building owners, "
        "maintenance engineers, government agencies (CPWD), and facility "
        "managers to make critical maintenance, rehabilitation, and safety "
        "decisions for RCC and masonry buildings.\n\n"
        "## Writing Standards\n\n"
        "1. **Use formal engineering language.** Write in third person, "
        "passive voice where appropriate, consistent with professional "
        "building inspection reports and CPWD documentation standards.\n\n"
        "2. **Be precise and quantitative.** Include measurements, "
        "ratings, scores, and percentages wherever the source data "
        "supports them (e.g., crack widths in mm, spalling area in m², "
        "corrosion extent as percentage). Avoid qualitative-only "
        "descriptions when quantitative data is available.\n\n"
        "3. **Follow a structured format.** Every report must include "
        "the standard sections described in the report template.\n\n"
        "4. **Cite all sources.** Every factual claim must reference "
        "the source document, page, and section (e.g., CPWD Maintenance "
        "Manual, Section X.Y). Knowledge graph data should be cited as "
        "[KG: Entity → Relationship → Entity].\n\n"
        "5. **Maintain objectivity.** Present findings neutrally. "
        "Recommendations should be clearly separated from observations.\n\n"
        "6. **Use standard building condition ratings** aligned with "
        "common building assessment scales (e.g., Good / Satisfactory / "
        "Fair / Poor / Critical) consistent with CPWD grading norms."
    )

    REPORT_TEMPLATE: str = (
        "Generate a comprehensive building assessment report using "
        "the data provided below. Follow the exact section structure.\n\n"
        "## Input Data\n\n"
        "### Executive Summary Context\n"
        "{executive_summary_context}\n\n"
        "### Defect Details\n"
        "{defect_details}\n\n"
        "### Root Cause Analysis\n"
        "{cause_analysis}\n\n"
        "### Recommendations\n"
        "{recommendations}\n\n"
        "### Risk Assessment Data\n"
        "{risk_assessment}\n\n"
        "## Required Report Sections\n\n"
        "### 1. Executive Summary\n"
        "Provide a concise overview (200–400 words) covering:\n"
        "- Building identification (type, location, age, occupancy).\n"
        "- Overall condition rating (Good / Satisfactory / Fair / Poor / Critical).\n"
        "- Most critical structural findings.\n"
        "- Top-priority recommended actions.\n\n"
        "### 2. Building Component Assessment\n"
        "For each defected building component, describe:\n"
        "- Component type (foundation, column, beam, slab, wall, roof, etc.).\n"
        "- Defect type and classification.\n"
        "- Location within the building (floor, zone, axis).\n"
        "- Severity and extent (quantified where possible, e.g., crack width, area).\n"
        "- Progression trend (if historical inspection data is available).\n\n"
        "### 3. Root Cause Analysis\n"
        "For each defect or defect group:\n"
        "- Identified root cause(s) with supporting evidence.\n"
        "- Contributing factors (construction quality, material, environment).\n"
        "- Mechanism of deterioration (e.g., corrosion-induced spalling).\n"
        "- References to relevant CPWD manuals, BIS standards, or NBC.\n\n"
        "### 4. Repair and Maintenance Recommendations\n"
        "Present recommendations in priority order:\n"
        "- Recommended action and repair methodology.\n"
        "- Priority level (high/medium/low) with justification.\n"
        "- Category (investigation/repair/monitoring/replacement/further analysis).\n"
        "- Applicable repair method (e.g., epoxy injection, concrete jacketing, "
        "waterproofing, re-plastering, grouting).\n"
        "- Relevant CPWD specification or BIS standard.\n\n"
        "### 5. Risk Matrix\n"
        "Provide a risk assessment table with:\n"
        "- Risk description (e.g., column failure, roof leakage).\n"
        "- Likelihood (high/medium/low).\n"
        "- Consequence (high/medium/low).\n"
        "- Overall risk rating.\n"
        "- Mitigation strategy.\n\n"
        "### 6. References\n"
        "Numbered list of all cited documents and standards, which may include:\n"
        "- CPWD Maintenance Manual\n"
        "- CPWD Handbook on Repairs & Rehabilitation of RCC Buildings\n"
        "- CPWD Works Manual\n"
        "- National Building Code (NBC)\n"
        "- BIS Standards (IS codes)\n"
        "- Building Structural Audit Reports\n"
        "- Knowledge graph sources"
    )
