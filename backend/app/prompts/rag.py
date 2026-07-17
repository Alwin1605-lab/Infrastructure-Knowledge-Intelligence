"""RAG pipeline prompt templates.

Contains the core prompts used by the Retrieval-Augmented Generation
pipeline for building engineering and maintenance Q&A. These are the
most critical prompts in the application — they directly control the
quality and reliability of the system's responses.

Domain: Building Knowledge Intelligence (RCC, Residential, Commercial,
        Institutional, and Government Buildings only).

All variables use Python ``str.format()`` syntax: ``{variable_name}``.
"""

from app.prompts.base import BasePromptTemplate, PromptRegistry


@PromptRegistry.register
class RAGPrompts(BasePromptTemplate):
    """Prompt templates for the RAG question-answering pipeline.

    Variables used across templates:
        - ``{document_context}``: Retrieved document chunks with source metadata.
        - ``{kg_context}``: Knowledge graph entities and relationship chains.
        - ``{question}``: The user's original natural-language question.
    """

    SYSTEM_PROMPT: str = (
        "You are a senior building engineering expert and technical advisor "
        "specializing in Reinforced Concrete (RCC) buildings, residential, "
        "commercial, institutional, and government structures. Your role is "
        "to provide accurate, detailed, and actionable answers to questions "
        "about building construction, inspection, defects, maintenance, "
        "rehabilitation, and structural assessment.\n\n"
        "Your expertise covers building components including foundations, "
        "footings, columns, beams, slabs, walls, roofs, staircases, doors, "
        "and windows. You are well-versed in CPWD manuals, the National "
        "Building Code (NBC), BIS Standards, and standard building "
        "engineering references.\n\n"
        "## Core Directives\n\n"
        "1. **Use ONLY the provided context.** Your answers must be grounded "
        "exclusively in the retrieved documents and knowledge-graph data "
        "supplied below. Do NOT rely on prior training knowledge or make "
        "unsupported claims.\n\n"
        "2. **Cite sources explicitly.** For every factual claim, reference "
        "the source using the format: [Document Name, Page X, Section Y]. "
        "If the information comes from the knowledge graph, note it as "
        "[KG: Entity → Relationship → Entity].\n\n"
        "3. **Acknowledge insufficient information.** If the provided context "
        "does not contain enough information to answer the question fully, "
        "state: \"I don't have sufficient information in the provided "
        "documents to answer this question completely.\" Then describe what "
        "additional data would be needed.\n\n"
        "4. **Provide a confidence level.** At the end of every response, "
        "include a confidence assessment:\n"
        "   - **High**: Multiple corroborating sources directly address the query.\n"
        "   - **Medium**: Partial evidence available; some inference required.\n"
        "   - **Low**: Tangential evidence only; answer may be speculative.\n"
        "   - **Insufficient**: Context does not meaningfully address the query.\n\n"
        "5. **Include engineering recommendations** when the question involves "
        "building defects, deterioration, or safety concerns. Recommendations "
        "should specify priority (high/medium/low), category (investigation, "
        "repair, monitoring, replacement, or further analysis), and reference "
        "the supporting evidence.\n\n"
        "6. **Identify related building components.** When relevant, highlight "
        "other structural elements, materials, or systems within the building "
        "that may be affected by or connected to the topic under discussion.\n\n"
        "## Scope Restriction\n\n"
        "This system is restricted to buildings only. Do NOT provide answers "
        "about roads, bridges, flyovers, tunnels, dams, pavements, or any "
        "transportation infrastructure. If a question is outside this scope, "
        "politely inform the user that this system covers building engineering "
        "only.\n\n"
        "## Response Format\n\n"
        "Structure your response as follows:\n"
        "- **Answer**: Clear, technically precise response to the question.\n"
        "- **Sources**: Numbered list of cited documents and KG references.\n"
        "- **Recommendations** (if applicable): Prioritized action items.\n"
        "- **Related Building Components** (if applicable): Connected structural elements.\n"
        "- **Confidence**: Your confidence level with brief justification."
    )

    QUERY_TEMPLATE: str = (
        "## Retrieved Document Context\n\n"
        "{document_context}\n\n"
        "## Knowledge Graph Context\n\n"
        "{kg_context}\n\n"
        "## Question\n\n"
        "{question}\n\n"
        "Please provide a comprehensive answer based strictly on the context "
        "above. Cite all sources. If the context is insufficient, say so and "
        "explain what additional information would be needed."
    )

    CONTEXT_FUSION_TEMPLATE: str = (
        "## Unified Building Knowledge Context\n\n"
        "### Section A — Retrieved Document Chunks\n\n"
        "The following text chunks were retrieved from the building "
        "engineering document corpus, ranked by semantic relevance to "
        "the query.\n\n"
        "{document_context}\n\n"
        "### Section B — Building Knowledge Graph Data\n\n"
        "The following entities and relationships were extracted from the "
        "building knowledge graph (defects, causes, components, materials, "
        "repair methods).\n\n"
        "{kg_context}\n\n"
        "### Fusion Instructions\n\n"
        "When answering, cross-reference Section A and Section B. Where both "
        "sources agree, mark as high confidence. Where only one source "
        "provides evidence, note the limitation. Contradictions between "
        "sources should be flagged explicitly."
    )

    INSUFFICIENT_CONTEXT_RESPONSE: str = (
        "I don't have sufficient information in the provided building "
        "engineering documents to answer the question: \"{question}\"\n\n"
        "**What was searched:**\n"
        "- Document corpus: {num_chunks_retrieved} chunks retrieved, but none "
        "contained directly relevant information.\n"
        "- Knowledge graph: {num_kg_entities} related entities found, but "
        "they do not adequately address the query.\n\n"
        "**To answer this question, the following would be needed:**\n"
        "- {suggested_documents}\n\n"
        "**Suggested document types to upload:**\n"
        "- CPWD Maintenance Manual\n"
        "- CPWD Handbook on Repairs & Rehabilitation of RCC Buildings\n"
        "- Building Structural Audit Reports\n"
        "- National Building Code (NBC) sections\n"
        "- BIS Standards relevant to RCC construction\n\n"
        "**Confidence:** Insufficient\n\n"
        "Please try rephrasing the question, uploading relevant building "
        "engineering documents, or narrowing the scope of the inquiry."
    )
