"""Live OpenNeuro GraphQL metadata pipeline."""
from __future__ import annotations

from typing import Any

import httpx


class OpenNeuroPipeline:
    """Read-only client for OpenNeuro public neuroimaging metadata."""

    GRAPHQL_URL = "https://openneuro.org/crg/graphql"
    QUERY = """
    query getDatasets($search: String, $first: Int) {
      datasets(search: $search, first: $first) {
        edges {
          node {
            id
            created
            latestSnapshot {
              description {
                Name
                Authors
              }
            }
          }
        }
      }
    }
    """

    async def search_datasets(self, query_term: str = "MRI", limit: int = 10) -> dict[str, Any]:
        """Fetch live public neuroimaging dataset metadata."""
        if not query_term.strip():
            raise ValueError("query_term must not be empty")
        variables = {"search": query_term.strip(), "first": max(1, min(limit, 50))}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(
                self.GRAPHQL_URL,
                json={"query": self.QUERY, "variables": variables},
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("OpenNeuro API returned an unexpected response shape")
        if data.get("errors"):
            raise RuntimeError(f"OpenNeuro GraphQL errors: {data['errors']}")
        return data
