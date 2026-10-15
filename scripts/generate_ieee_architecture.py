"""IEEE Paper System Architecture Diagram Generator.

Revised for rigorous IEEE publication standards:
- ONLY verified components, models, and exact repository corpus statistics.
- Separate Online Runtime Multi-Agent Inference Pipeline and Offline Knowledge Ingestion Pipeline.
- Accurate data flow: User Query -> FastAPI -> LangGraph (5 Agents) -> Hybrid Retrieval ->
  ChromaDB + Neo4j -> Context Fusion -> LLM Inference (Groq + Gemini Fallback) ->
  Grounded Answer + Citations + Recommendations -> React UI.
- Offline Ingestion: Research Papers/Standards -> Processing -> Chunking+Embeddings -> ChromaDB
  & Entity/Relation Extraction -> Neo4j & Metadata -> MongoDB.
- Exact Corpus Stats: 20 validated documents, 1,066 ChromaDB vectors, 355 pages,
  5 engineering domains, 105 benchmark questions (20/20 documents represented).
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

def draw_diagram():
    # Canvas size: 16 x 12 inches at 300 DPI for ultra-sharp IEEE publication quality
    fig, ax = plt.subplots(figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Academic IEEE Color Palette
    C_HEADER = "#0F172A"           # Deep Navy / Slate
    C_CONTAINER_BG = "#F8FAFC"     # Slate 50 (soft academic background)
    C_CONTAINER_BORDER = "#94A3B8" # Slate 400
    C_INNER_BG = "#FFFFFF"         # Pure white inner containers
    C_CARD_BG = "#FFFFFF"          # Pure white cards
    C_CARD_BORDER = "#CBD5E1"      # Slate 300
    C_PRIMARY = "#1E40AF"          # IEEE Blue (600)
    C_TEAL = "#0F766E"             # Teal (700)
    C_INDIGO = "#4338CA"           # Indigo (700)
    C_AMBER = "#B45309"            # Amber (700)
    C_SLATE = "#334155"            # Slate (700)
    C_TEXT_DARK = "#0F172A"        # Main text
    C_TEXT_MUTED = "#334155"       # Subtitle & details text
    C_ARROW_RUNTIME = "#1E3A8A"    # Strong Blue for Online Runtime
    C_ARROW_OFFLINE = "#0F766E"    # Strong Teal for Offline Ingestion

    def draw_container(x, y, w, h, title, subtitle="", bg=C_CONTAINER_BG, border=C_CONTAINER_BORDER):
        """Draw a major section boundary."""
        box = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.3,rounding_size=0.8",
            facecolor=bg, edgecolor=border, linewidth=1.3,
            zorder=1
        )
        ax.add_patch(box)
        
        ax.text(
            x + 1.5, y + h - 1.8, title.upper(),
            fontsize=9.8, fontweight="bold", color=C_HEADER,
            va="center", ha="left", zorder=3, family="sans-serif"
        )
        if subtitle:
            ax.text(
                x + w - 1.5, y + h - 1.8, subtitle,
                fontsize=8.0, style="italic", color=C_TEXT_MUTED,
                va="center", ha="right", zorder=3, family="sans-serif"
            )

    def draw_card(x, y, w, h, title, lines=None, header_color=C_PRIMARY, fill=C_CARD_BG, border=C_CARD_BORDER):
        """Draw a functional modular card."""
        box = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.2,rounding_size=0.5",
            facecolor=fill, edgecolor=border, linewidth=1.0,
            zorder=2
        )
        ax.add_patch(box)

        # Header bar
        bar = FancyBboxPatch(
            (x + 0.1, y + h - 0.55), w - 0.2, 0.45,
            boxstyle="round,pad=0.08,rounding_size=0.25",
            facecolor=header_color, edgecolor="none",
            zorder=3
        )
        ax.add_patch(bar)

        # Title
        ax.text(
            x + w/2.0, y + h - 1.5, title,
            fontsize=8.5, fontweight="bold", color=C_TEXT_DARK,
            va="center", ha="center", zorder=4, family="sans-serif"
        )

        # Detail lines
        if lines:
            start_y = y + h - 2.8
            spacing = 1.25
            for idx, text in enumerate(lines):
                ax.text(
                    x + w/2.0, start_y - (idx * spacing), text,
                    fontsize=7.3, color=C_TEXT_MUTED,
                    va="center", ha="center", zorder=4, family="sans-serif"
                )

    def draw_flow_arrow(x1, y1, x2, y2, label="", color=C_ARROW_RUNTIME, rad=0.0, dashed=False, lw=1.3):
        """Draw directional data flow connection."""
        linestyle = (0, (4, 3)) if dashed else "solid"
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="-|>,head_length=4.5,head_width=2.8",
            connectionstyle=f"arc3,rad={rad}",
            color=color, linewidth=lw, linestyle=linestyle, zorder=6
        )
        ax.add_patch(arrow)
        if label:
            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0
            ax.text(
                mid_x, mid_y + 0.55, label,
                fontsize=6.8, fontweight="semibold", color=color,
                ha="center", va="bottom", zorder=7,
                bbox=dict(boxstyle="round,pad=0.15", fc="#FFFFFF", ec=color, lw=0.5, alpha=0.92)
            )

    # =========================================================================
    # TITLE & SUBTITLE
    # =========================================================================
    ax.text(50, 98.4, "Architecture of the Proposed AI-Driven Building Knowledge Intelligence System",
            fontsize=12.5, fontweight="bold", color=C_HEADER, ha="center", va="center", family="sans-serif")
    ax.text(50, 96.8, "Dual-Pipeline System Overview: Online Multi-Agent Hybrid RAG Runtime and Offline Knowledge Ingestion",
            fontsize=8.2, color=C_TEXT_MUTED, ha="center", va="center", family="sans-serif")

    # =========================================================================
    # PART I: ONLINE MULTI-AGENT HYBRID RAG INFERENCE PIPELINE (Runtime)
    # y: 38.0 to 95.5 (Height = 57.5)
    # =========================================================================
    draw_container(2.0, 38.0, 96.0, 57.5, 
                   "Part I: Online Multi-Agent Hybrid RAG Inference Pipeline (Runtime)",
                   "End-to-End Query Answering & Decision Support")

    # Row 1: UI Input -> Gateway -> UI Output
    # y: 84.0, h: 7.2 (Top = 91.2, leaving 2.6 units below container title at 93.8)
    draw_card(4.8, 84.0, 26.0, 7.2, "1. User Query & Interaction", 
              ["• Structural Engineer Query Input", "• Domain: RCC Building Diagnostics", "• React / Vite Client Application"], C_PRIMARY)

    draw_card(35.0, 84.0, 29.0, 7.2, "2. FastAPI Application Gateway", 
              ["• Asynchronous REST API (/api/v1/agents/query)", "• Input Normalization & Domain Guard", "• Lifespan & Service State Management"], C_INDIGO)

    draw_card(68.5, 84.0, 27.5, 7.2, "6. Grounded Response & UI Display", 
              ["• Answer with Code & Standard Citations", "• Prioritized Remediation Actions", "• Calibrated Confidence Score Display"], C_TEAL)

    # Arrow 1 -> 2
    draw_flow_arrow(30.8, 87.6, 35.0, 87.6, "HTTP Request")

    # Row 2: LangGraph 5-Agent Orchestrator Container
    # y: 58.5 to 81.5 (Height = 23.0, Top = 81.5)
    draw_container(3.5, 58.5, 93.0, 23.0, 
                   "", "", bg=C_INNER_BG, border=C_CARD_BORDER)

    # Centered Header for LangGraph to leave left and right empty for clear arrow routing
    ax.text(50.0, 79.7, "LANGGRAPH MULTI-AGENT ORCHESTRATION CORE (5 SEQUENTIAL AGENTS)",
            fontsize=9.2, fontweight="bold", color=C_HEADER, va="center", ha="center", zorder=4, family="sans-serif")

    agent_w = 17.0
    agent_h = 16.0
    spacing = 18.2
    agent_y = 60.0
    start_x = 4.8

    # Agent 1
    draw_card(start_x, agent_y, agent_w, agent_h, 
              "Agent 1: Query Analysis", 
              ["• Intent Classification",
               "• Defect & Component NER",
               "• Structural Scope Check",
               "• Query Parameterization"], C_PRIMARY)

    # Agent 2
    draw_card(start_x + spacing, agent_y, agent_w, agent_h, 
              "Agent 2: Retrieval Agent", 
              ["• Hybrid RAG Coordinator",
               "• ChromaDB Vector Querying",
               "• Neo4j Graph Querying",
               "• Candidate Passage Pooling"], C_INDIGO)

    # Agent 3
    draw_card(start_x + 2*spacing, agent_y, agent_w, agent_h, 
              "Agent 3: KG Reasoning", 
              ["• Multi-Hop Cypher Traversal",
               "• Defect -> Cause -> Effect",
               "• Entity Path Validation",
               "• Structural Risk Inference"], C_TEAL)

    # Agent 4
    draw_card(start_x + 3*spacing, agent_y, agent_w, agent_h, 
              "Agent 4: Recommendation", 
              ["• Repair Action Synthesis",
               "• Code-Compliant Workflows",
               "• Urgency & Priority Rating",
               "• Structural Safeguards"], C_AMBER)

    # Agent 5
    draw_card(start_x + 4*spacing, agent_y, agent_w, agent_h, 
              "Agent 5: Report Synthesis", 
              ["• Grounded Final Report",
               "• Clause & Source Citations",
               "• Evidence Synthesis",
               "• Confidence Aggregation"], C_SLATE)

    # Inter-agent sequential flow arrows
    for i in range(4):
        x_from = start_x + i * spacing + agent_w
        x_to = start_x + (i + 1) * spacing
        draw_flow_arrow(x_from, agent_y + 8.0, x_to, agent_y + 8.0, color=C_ARROW_RUNTIME)

    # Gateway into Agent 1 (Clean diagonal route through empty space)
    draw_flow_arrow(35.0, 84.0, 13.3, 76.0, "Trigger Pipeline", rad=0.0)

    # Agent 5 into Final Output Card (Clean straight vertical arrow)
    draw_flow_arrow(88.7, 76.0, 88.7, 84.0, "Grounded Output", rad=0.0)

    # Row 3: Hybrid RAG & LLM Inference
    # y: 39.5, h: 16.5
    draw_card(4.8, 39.5, 41.5, 16.5, "Hybrid RAG & Context Fusion Engine", 
              ["• HuggingFace all-MiniLM-L6-v2 (384-dimensional dense vectors)",
               "• Dense Semantic Search over ChromaDB Collection",
               "• Graph Pattern Matching over Neo4j Knowledge Graph",
               "• Context Fusion: Vector Text Passages + Knowledge Graph Triples",
               "• Calibrated Confidence Scoring (Deterministic Weighted Metric)"], 
              C_PRIMARY)

    draw_card(50.0, 39.5, 46.5, 16.5, "LLM Inference Subsystem (With Failover)", 
              ["• Primary Provider: Groq LLM Inference Engine",
               "   - Multi-API Key Rotation Pool (Accounts 1, 2, 3)",
               "   - Automated HTTP 429 Rate Limit Rotation",
               "• Fallback Provider: Google Gemini API (gemini-flash)",
               "   - Automatic Failover when Groq quota is exhausted",
               "• Citation & Evidence Grounding against Retrieved Sources"], 
              C_AMBER)

    # Connect Agents to Hybrid RAG and LLM
    draw_flow_arrow(23.0, 60.0, 23.0, 56.0, "Hybrid Retrieval Request")
    draw_flow_arrow(46.3, 47.7, 50.0, 47.7, "Fused Context")
    draw_flow_arrow(73.2, 56.0, 73.2, 60.0, "Grounded Inference Output")


    # =========================================================================
    # PART II: OFFLINE KNOWLEDGE INGESTION PIPELINE & HETEROGENEOUS STORAGE
    # y: 2.0 to 35.5 (Height = 33.5)
    # =========================================================================
    draw_container(2.0, 2.0, 96.0, 33.5, 
                   "Part II: Offline Knowledge Ingestion Pipeline & Heterogeneous Storage",
                   "Verified Research Corpus, Document Processing, and Multi-Store Persistence")

    # Corpus Card on the left (Full Height of Part II)
    draw_card(4.0, 3.6, 22.5, 27.5, "Authoritative Research Corpus", 
              ["• 20 Validated Documents",
               "• 355 Total Pages",
               "• 5 Engineering Domains:",
               "   1. Concrete Testing (IS 516)",
               "   2. RCC Design (IS 456)",
               "   3. Seismic Detailing (IS 13920)",
               "   4. NDT Assessment (IS 13311)",
               "   5. Maintenance & Repair",
               "• 105 Benchmark Evaluation",
               "   Questions (20/20 Docs)",
               "• Ground-Truth Citations"], C_SLATE)

    # Ingestion Middle Steps (Row 1 of Part II) - y: 17.5, h: 13.5 (Top = 31.0, below title at 33.5)
    draw_card(29.0, 17.5, 32.5, 13.6, "Document Processing & Chunking", 
              ["• PyMuPDF Text & Structural Section Parsing",
               "• Header, Table & Clause Boundary Recognition",
               "• Recursive Character Splitting (1000 chars, 200 overlap)",
               "• Source Document & Page Metadata Tagging"], C_TEAL)

    draw_card(64.5, 17.5, 32.0, 13.6, "Feature & Triple Extraction", 
              ["• HuggingFace all-MiniLM-L6-v2 Embeddings (384-d)",
               "• Dense Vector Generation for Semantic Search",
               "• Structural Defect & Component Entity Extraction",
               "• Knowledge Triple Extraction (Defect-Cause-Standard)"], C_PRIMARY)

    # Arrows for ingestion flow
    draw_flow_arrow(26.5, 24.3, 29.0, 24.3, "Raw PDFs", color=C_ARROW_OFFLINE)
    draw_flow_arrow(61.5, 24.3, 64.5, 24.3, "Parsed Chunks", color=C_ARROW_OFFLINE)

    # 3 Storage Databases (Row 2 of Part II) - y: 3.6, h: 12.0
    draw_card(29.0, 3.6, 20.5, 12.0, "ChromaDB (Vector DB)", 
              ["• Collection: infra_documents",
               "• 1,066 Dense Vectors",
               "• 384-d Cosine Metric Space",
               "• HNSW Hierarchical Index",
               "• Persistent Vector Index"], C_PRIMARY)

    draw_card(51.5, 3.6, 21.0, 12.0, "Neo4j (Knowledge Graph)", 
              ["• Neo4j Graph Database",
               "• Structural Defect Entities",
               "• Causal & Repair Relations",
               "• Cypher Query Protocol",
               "• Native Graph Traversal"], C_TEAL)

    draw_card(74.5, 3.6, 22.0, 12.0, "MongoDB (Metadata Store)", 
              ["• Database: infra_knowledge",
               "• Document Master Records",
               "• Processing Job Statuses",
               "• User Profiles & RBAC",
               "• Beanie Asynchronous ODM"], C_INDIGO)

    # Connecting Extracted Features to Storage
    draw_flow_arrow(69.0, 17.5, 39.2, 15.6, "Vectors", color=C_ARROW_OFFLINE, rad=0.06)
    draw_flow_arrow(77.5, 17.5, 62.0, 15.6, "Triples", color=C_ARROW_OFFLINE, rad=0.04)
    draw_flow_arrow(85.5, 17.5, 85.5, 15.6, "Metadata", color=C_ARROW_OFFLINE)

    # Clean vertical link through empty space between Storage and Runtime RAG (no text collision)
    draw_flow_arrow(43.0, 31.1, 43.0, 39.5, "Vector & Graph Retrieval", color=C_ARROW_RUNTIME, dashed=True)

    # Save diagram
    out_dir = os.path.join("docs", "figures")
    os.makedirs(out_dir, exist_ok=True)

    png_path = os.path.join(out_dir, "system_architecture_ieee.png")
    pdf_path = os.path.join(out_dir, "system_architecture_ieee.pdf")
    svg_path = os.path.join(out_dir, "system_architecture_ieee.svg")

    plt.tight_layout()
    plt.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="#FFFFFF")
    plt.savefig(pdf_path, format="pdf", bbox_inches="tight", facecolor="#FFFFFF")
    plt.savefig(svg_path, format="svg", bbox_inches="tight", facecolor="#FFFFFF")
    plt.close()

    print("IEEE System Architecture Diagram (Revised & Verified) successfully generated:")
    print(f" -> High-Res PNG (300 DPI): {png_path}")
    print(f" -> Vector PDF (for LaTeX): {pdf_path}")
    print(f" -> Vector SVG:            {svg_path}")

if __name__ == "__main__":
    draw_diagram()
