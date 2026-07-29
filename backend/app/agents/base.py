"""Abstract base class for all agents in the Agentic Pipeline.

Every agent must implement:
    - name: str property — used in execution traces
    - run(state) -> AgentState — processes state and returns updated state

Agents MUST:
    - Append an AgentExecutionStep to state["execution_trace"] with:
        * agent name
        * status (success | skipped | failed)
        * time_ms
        * confidence (0.0–1.0, agent-specific assessment)
        * reason (human-readable explanation of what the agent decided)
    - Be stateless — no instance variables mutated between calls
    - Handle their own errors gracefully and mark status as "failed" rather than raising

Agents MUST NOT:
    - Raise exceptions to the orchestrator for transient errors
    - Store request data in instance variables
    - Call other agents directly (only the orchestrator chains agents)
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.state import AgentState


class BaseAgent(ABC):
    """Abstract base class for all agentic pipeline nodes.

    Subclasses implement `run()` which reads from and writes to AgentState.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the agent's display name used in execution traces.

        Returns:
            str: Human-readable name, e.g., "QueryAnalysisAgent".
        """
        ...

    @abstractmethod
    async def run(self, state: "AgentState") -> "AgentState":
        """Execute the agent's logic and return the updated state.

        Args:
            state: Current shared AgentState from the pipeline.

        Returns:
            AgentState: Updated state with this agent's outputs and trace appended.
        """
        ...
