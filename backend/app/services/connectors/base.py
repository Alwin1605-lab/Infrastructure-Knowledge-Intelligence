from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseConnector(ABC):
    @abstractmethod
    async def search_metadata(self, query: str) -> List[Dict[str, Any]]:
        """Search metadata based on a query."""
        pass
