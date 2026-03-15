from typing import Dict, Any
import httpx
from .base import BaseAgent
from src.backend.core.config import settings

class ResearchAgent(BaseAgent):
    """Agent responsible for researching content from various sources."""

    def __init__(self):
        super().__init__("Research Agent")
        self.searxng_url = settings.SEARXNG_URL

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research content based on the input data.

        Args:
            input_data: Dictionary containing research parameters
                       {
                           "queries": ["list", "of", "search", "queries"],
                           "channel_id": "channel identifier",
                           "max_results": 10
                       }

        Returns:
            Dictionary containing research results
        """
        queries = input_data.get("queries", [])
        max_results = input_data.get("max_results", 10)

        results = []

        # For each query, search using SearXNG
        for query in queries:
            search_results = await self._search_searxng(query, max_results)
            results.extend(search_results)

        return {
            "agent": self.name,
            "results": results,
            "total_results": len(results)
        }

    async def _search_searxng(self, query: str, max_results: int) -> list:
        """
        Search using SearXNG instance.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of search results
        """
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "q": query,
                    "format": "json",
                    "count": max_results
                }

                response = await client.get(
                    f"{self.searxng_url}/search",
                    params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
                else:
                    return []
        except Exception as e:
            print(f"Error searching SearXNG: {str(e)}")
            return []