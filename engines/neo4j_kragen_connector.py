"""
Neo4j Connector for TMRDS KRAGEN layer.

Production GraphRAG pattern (UMLS / PubMed literature graphs):
  - Store biomedical concepts + relations in Neo4j
  - Cypher traversal for multi-hop evidence
  - Optional GraphCypherQAChain-style LLM → Cypher → context

Offline: no driver required; methods return structured stubs.
Install: pip install neo4j
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.Neo4j")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class Neo4jKRAGENConnector:
    """
    Bridge between TMRDS KRAGENGraphEngine and a Neo4j instance.

    Typical Cypher patterns (biomedical GraphRAG):
      MATCH (d:Disease)-[:TREATS|ASSOCIATE]-(g:Gene)
      MATCH (g:Gene)-[:MENTIONED_IN]->(p:Paper)
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.uri = uri
        self.user = user
        self._driver = None
        if NEO4J_AVAILABLE and uri and user and password:
            try:
                self._driver = GraphDatabase.driver(uri, auth=(user, password))
                self.mode = "CONNECTED"
            except Exception as exc:  # noqa: BLE001
                logger.error("Neo4j connect failed: %s", exp if False else exc)
                self.mode = "OFFLINE"
        else:
            self.mode = "OFFLINE"

    def run_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.mode != "CONNECTED" or self._driver is None:
            return {
                "status": "OFFLINE",
                "query": query,
                "records": [],
                "note": "Configure NEO4J_URI/USER/PASSWORD and pip install neo4j",
            }
        try:
            with self._driver.session() as session:
                result = session.run(query, params or {})
                records = [r.data() for r in result]
            return {"status": "OK", "query": query, "records": records, "count": len(records)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "error": str(exc), "query": query}

    def disease_gene_neighbors(self, disease: str, limit: int = 25) -> Dict[str, Any]:
        cypher = (
            "MATCH (d:Disease)-[r]-(g:Gene) "
            "WHERE toLower(d.name) CONTAINS toLower($disease) "
            "OR toLower(d.mention) CONTAINS toLower($disease) "
            "RETURN d, type(r) AS rel, g LIMIT $limit"
        )
        return self.run_cypher(cypher, {"disease": disease, "limit": limit})

    def gene_papers(self, gene: str, limit: int = 20) -> Dict[str, Any]:
        cypher = (
            "MATCH (g:Gene)-[:MENTIONED_IN]->(p:Paper) "
            "WHERE toUpper(g.mention) = toUpper($gene) OR toUpper(g.name) = toUpper($gene) "
            "RETURN p.pmid AS pmid, p.title AS title, p.year AS year "
            "ORDER BY p.year DESC LIMIT $limit"
        )
        return self.run_cypher(cypher, {"gene": gene, "limit": limit})

    def push_kragen_nodes(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.mode != "CONNECTED":
            return {"status": "OFFLINE", "nodes": len(nodes), "edges": len(edges)}
        loaded = 0
        for n in nodes:
            q = (
                "MERGE (x:Entity {id: $id}) "
                "SET x.label = $label, x.layer = $layer"
            )
            self.run_cypher(q, {"id": n["id"], "label": n.get("label"), "layer": n.get("layer")})
            loaded += 1
        for e in edges:
            q = (
                "MATCH (a:Entity {id: $src}), (b:Entity {id: $dst}) "
                "MERGE (a)-[r:REL {type: $rel}]->(b)"
            )
            self.run_cypher(q, {"src": e["src"], "dst": e["dst"], "rel": e.get("relation", "RELATED")})
        return {"status": "UPSERTED", "nodes_loaded": loaded, "edges": len(edges)}

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()

    def status(self) -> Dict[str, Any]:
        return {
            "node": "Neo4jKRAGENConnector",
            "neo4j_driver": NEO4J_AVAILABLE,
            "mode": self.mode,
            "uri": self.uri,
            "status": "READY",
        }
