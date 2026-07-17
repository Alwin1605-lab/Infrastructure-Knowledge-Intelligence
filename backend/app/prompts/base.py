"""Base prompt template infrastructure.

Provides the foundation for all prompt templates in the application.
All prompt classes inherit from BasePromptTemplate and register
themselves via the PromptRegistry decorator.
"""

from abc import ABC
from typing import ClassVar


class BasePromptTemplate(ABC):
    """Abstract base for prompt template collections.

    Each subclass groups related prompts as class-level string constants.
    Variables use Python str.format() syntax: {variable_name}

    Example:
        @PromptRegistry.register
        class MyPrompts(BasePromptTemplate):
            GREETING = "Hello, {name}!"
    """

    @classmethod
    def list_templates(cls) -> dict[str, str]:
        """List all prompt templates defined in this class.

        Returns:
            Dict mapping template name to template string.
            Only includes uppercase string class attributes
            that do not start with an underscore.
        """
        return {
            name: value
            for name, value in vars(cls).items()
            if isinstance(value, str) and not name.startswith("_") and name.isupper()
        }


class PromptRegistry:
    """Central registry for all prompt template classes.

    Provides lookup by name across all registered prompt classes.
    Used as a decorator on prompt template subclasses.

    Example:
        @PromptRegistry.register
        class RAGPrompts(BasePromptTemplate):
            ...

        # Later:
        cls = PromptRegistry.get("RAGPrompts")
    """

    _registry: ClassVar[dict[str, type[BasePromptTemplate]]] = {}

    @classmethod
    def register(cls, prompt_class: type[BasePromptTemplate]) -> type[BasePromptTemplate]:
        """Register a prompt template class.

        Args:
            prompt_class: The prompt template class to register.

        Returns:
            The same class, unmodified (allows use as decorator).
        """
        cls._registry[prompt_class.__name__] = prompt_class
        return prompt_class

    @classmethod
    def get(cls, class_name: str) -> type[BasePromptTemplate] | None:
        """Get a registered prompt class by name.

        Args:
            class_name: The name of the prompt class to retrieve.

        Returns:
            The prompt class if found, None otherwise.
        """
        return cls._registry.get(class_name)

    @classmethod
    def list_all(cls) -> dict[str, type[BasePromptTemplate]]:
        """List all registered prompt classes.

        Returns:
            Dict mapping class name to class object.
        """
        return dict(cls._registry)
