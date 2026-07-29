"""Benchmark Dataset Manager for Phase 7 Evaluation Framework.

Loads and manages categorized engineering evaluation questions.
Includes built-in test sets for building defects, structural components,
maintenance methods, and standards compliance.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkQuestion:
    """A single evaluation question from the benchmark dataset."""
    id: str
    category: str
    question: str
    expected_answer_keywords: list[str] = field(default_factory=list)
    expected_chunk_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BenchmarkDatasetManager:
    """Manages evaluation datasets for the Building Knowledge Intelligence System."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        """Initialize the dataset manager.

        Args:
            data_dir: Path to external JSON dataset files. If None, uses built-in data.
        """
        self._data_dir = Path(data_dir) if data_dir else None
        self._questions: list[BenchmarkQuestion] = self._load_builtin_dataset()

    def load_dataset(self, category: str | None = None) -> list[BenchmarkQuestion]:
        """Retrieve benchmark questions, optionally filtered by category.

        Args:
            category: If provided, return only questions from this category.

        Returns:
            List of BenchmarkQuestion objects.
        """
        if category:
            filtered = [q for q in self._questions if q.category == category]
            logger.info("dataset_loaded", category=category, count=len(filtered))
            return filtered
        logger.info("dataset_loaded", category="all", count=len(self._questions))
        return self._questions

    def get_categories(self) -> list[str]:
        """Return a list of all available categories in the loaded dataset."""
        return list(set(q.category for q in self._questions))

    def _load_builtin_dataset(self) -> list[BenchmarkQuestion]:
        """Load the standard evaluation dataset."""
        return [
            BenchmarkQuestion(
                id="def_01",
                category="defects",
                question="What causes spalling in RCC columns and how is it repaired?",
                expected_answer_keywords=["corrosion", "rebar", "carbonation", "jacketing", "epoxy"],
            ),
            BenchmarkQuestion(
                id="def_02",
                category="defects",
                question="Why does honeycombing occur in concrete and how can it be prevented?",
                expected_answer_keywords=["compaction", "vibration", "aggregate", "slump"],
            ),
            BenchmarkQuestion(
                id="mat_01",
                category="materials",
                question="What is the effect of high chloride content in concrete?",
                expected_answer_keywords=["corrosion", "pitting", "steel", "rust"],
            ),
            BenchmarkQuestion(
                id="maint_01",
                category="maintenance",
                question="What are the standard repair methods for severe cracks in a load-bearing wall?",
                expected_answer_keywords=["injection", "grouting", "stitching", "epoxy"],
            ),
            BenchmarkQuestion(
                id="std_01",
                category="standards",
                question="According to CPWD standards, what is the maximum permissible crack width in RCC members?",
                expected_answer_keywords=["0.3mm", "CPWD", "IS 456", "crack width"],
            ),
            BenchmarkQuestion(
                id="rej_01",
                category="out_of_domain",
                question="How do you inspect a highway bridge for corrosion?",
                expected_answer_keywords=["building", "domain", "infrastructure"],
            ),
        ]

    def load_from_json(self, file_path: str | Path) -> None:
        """Load additional questions from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            logger.error("dataset_file_not_found", path=str(path))
            raise FileNotFoundError(f"Dataset file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        loaded = 0
        for item in data.get("questions", []):
            q = BenchmarkQuestion(
                id=item.get("id", f"ext_{loaded}"),
                category=item.get("category", "general"),
                question=item.get("question", ""),
                expected_answer_keywords=item.get("expected_answer_keywords", []),
                expected_chunk_ids=item.get("expected_chunk_ids", []),
                metadata=item.get("metadata", {}),
            )
            self._questions.append(q)
            loaded += 1

        logger.info("dataset_json_loaded", file=path.name, added=loaded, total=len(self._questions))
