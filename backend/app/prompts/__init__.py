"""Prompt Management Module.

Centralized storage for all LLM prompts used across the application.
No service class should contain hardcoded prompts.

Usage:
    from app.prompts import RAGPrompts, EntityExtractionPrompts
    
    system_prompt = RAGPrompts.SYSTEM_PROMPT
    query_template = RAGPrompts.QUERY_TEMPLATE.format(context=ctx, question=q)
"""

from app.prompts.base import BasePromptTemplate, PromptRegistry
from app.prompts.rag import RAGPrompts
from app.prompts.entity_extraction import EntityExtractionPrompts
from app.prompts.recommendations import RecommendationPrompts
from app.prompts.reports import ReportPrompts

__all__ = [
    "BasePromptTemplate",
    "PromptRegistry",
    "RAGPrompts",
    "EntityExtractionPrompts",
    "RecommendationPrompts",
    "ReportPrompts",
]
