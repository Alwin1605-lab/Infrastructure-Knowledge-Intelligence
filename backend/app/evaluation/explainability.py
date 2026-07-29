"""Explainability and Reporting Module for Phase 7.

Generates publication-ready Markdown summaries of benchmark runs
and provides deep JSON traces for visualization dashboards.
"""

from typing import Any
import json
from datetime import datetime


class ExplainabilityGenerator:
    """Generates evaluation reports and visualization datasets."""

    @staticmethod
    def generate_markdown_report(benchmark_results: dict[str, Any]) -> str:
        """Generate a publication-ready Markdown report from benchmark results."""
        summary = benchmark_results.get("summary", {})
        config_comparison = benchmark_results.get("config_comparison", {})
        errors = benchmark_results.get("failure_breakdown", {})

        md = [
            "# Benchmark Evaluation Report",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Evaluation Summary",
            f"- **Questions Tested:** {summary.get('questions_tested', 0)}",
            f"- **Overall Accuracy (Success Rate):** {summary.get('accuracy_percent', 0.0):.1f}%",
            f"- **Average Retrieval Precision@5:** {summary.get('avg_precision', 0.0):.3f}",
            f"- **Average Recall@5:** {summary.get('avg_recall', 0.0):.3f}",
            f"- **Average Retrieval Coverage:** {summary.get('avg_coverage', 0.0):.1f}%",
            f"- **Average Pipeline Latency:** {summary.get('avg_latency_s', 0.0):.2f} s",
            f"- **Average Agent Confidence:** {summary.get('avg_confidence', 0.0):.3f}",
            f"- **Citation Correctness:** {summary.get('avg_citation_correctness', 0.0)*100:.1f}%",
            "",
        ]

        if config_comparison:
            best_config = config_comparison.get("best_configuration", "Hybrid RAG + Agentic AI")
            md.extend([
                "## Architectural Comparison",
                f"**Best Configuration:** {best_config}",
                "",
                "### Improvement over LLM Only",
                f"- **+{config_comparison.get('retrieval_improvement_percent', 0.0):.1f}%** Retrieval Accuracy",
                f"- **+{config_comparison.get('recommendation_improvement_percent', 0.0):.1f}%** Recommendation Quality",
                "",
            ])

        if errors:
            md.extend([
                "## Failure Analysis",
                "Breakdown of why benchmarks failed to meet thresholds:",
                ""
            ])
            for err_type, count in errors.items():
                md.append(f"- **{err_type}:** {count}")
            md.append("")

        md.append("## Detailed Visualizations")
        md.append("Visualization payloads (latency, confidence) are available in the JSON export.")

        return "\n".join(md)

    @staticmethod
    def generate_visualization_payload(eval_runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract visualization-ready arrays for the frontend."""
        latencies = []
        confidences = []

        for run in eval_runs:
            # Look at agent trace for Phase 6 latency breakdown
            trace = run.get("pipeline_response", {}).get("execution_trace", [])
            qid = run.get("question_id", "unknown")
            
            for step in trace:
                latencies.append({
                    "question_id": qid,
                    "agent": step.get("agent"),
                    "ms": step.get("time_ms")
                })
                confidences.append({
                    "question_id": qid,
                    "agent": step.get("agent"),
                    "score": step.get("confidence")
                })

        return {
            "latency": latencies,
            "confidence_distributions": confidences
        }
