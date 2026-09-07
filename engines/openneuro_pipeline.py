"""Live OpenNeuro GraphQL metadata pipeline."""
from __future__ import annotations

from typing import Any

import httpx


class OpenNeuroPipeline:
    """Read-only client for OpenNeuro public neuroimaging metadata."""

    GRAPHQL_URL = "https://openneuro.org/crn/graphql"
    QUERY = """
    query advancedSearchDatasets($query: DatasetSearchInput!, $first: Int!) {
      datasets: advancedSearch(query: $query, first: $first) {
        edges {
          id
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
        pageInfo {
          hasNextPage
          endCursor
          count
        }
      }
    }
    """

    async def search_datasets(self, query_term: str = "MRI", limit: int = 10) -> dict[str, Any]:
        """Fetch live public neuroimaging dataset metadata."""
        if not query_term.strip():
            raise ValueError("query_term must not be empty")
        variables = {
            "query": {"keywords": [query_term.strip()]},
            "first": max(1, min(limit, 50)),
        }
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
