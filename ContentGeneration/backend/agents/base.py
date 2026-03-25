from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgent(ABC):
    """Base class for all agents in the ContentPilot platform."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent with the given input data.

        Args:
            input_data: Dictionary containing the input data for the agent

        Returns:
            Dictionary containing the agent's output
        """
        pass