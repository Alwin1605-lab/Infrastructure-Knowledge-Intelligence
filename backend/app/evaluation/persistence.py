"""Benchmark Result Persistence for Phase 7.

Saves benchmark runs to a local directory (evaluation_results/) in both
JSON and Markdown formats. Allows tracking and comparing system
improvements over time.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class BenchmarkPersistence:
    """Handles saving and loading of benchmark evaluation results."""

    def __init__(self, base_dir: str | Path = "evaluation_results") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_benchmark(self, results: dict[str, Any], markdown_report: str) -> dict[str, str]:
        """Save benchmark results to JSON and Markdown files.

        Args:
            results: The full JSON payload of the benchmark run.
            markdown_report: The generated publication-ready Markdown text.

        Returns:
            Dict containing the paths to the saved files.
        """
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        json_path = self.base_dir / f"benchmark_{timestamp}.json"
        md_path = self.base_dir / f"benchmark_{timestamp}.md"

        # Save JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        # Save Markdown
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)

        logger.info("benchmark_saved", json=str(json_path), md=str(md_path))
        return {
            "json_file": str(json_path),
            "md_file": str(md_path)
        }

    def list_history(self) -> list[dict[str, Any]]:
        """List all previous benchmark runs found in the directory."""
        history = []
        for file_path in sorted(self.base_dir.glob("benchmark_*.json"), reverse=True):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                summary = data.get("summary", {})
                history.append({
                    "filename": file_path.name,
                    "date": data.get("timestamp"),
                    "accuracy_percent": summary.get("accuracy_percent"),
                    "questions_tested": summary.get("questions_tested"),
                    "avg_latency_s": summary.get("avg_latency_s"),
                })
            except Exception as e:
                logger.error("history_load_failed", file=file_path.name, error=str(e))
                
        return history
