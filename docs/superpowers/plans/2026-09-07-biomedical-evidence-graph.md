# Biomedical Evidence Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved TMRDS source-governed biomedical evidence graph as a provenance-first research infrastructure layer spanning canonical entities, immutable assertions, evidence assessments, source governance, conflict detection, relational persistence, Neo4j projection, and provenance-aware APIs.

**Architecture:** PostgreSQL is the governed persistence layer for source observations, canonical entities, assertions, provenance, evidence assessments, source registry, conflicts, and ingestion state. Neo4j is a rebuildable graph projection consistent with the existing KRAGEN architecture; vector/RAG output remains a derived projection. Existing live adapters become governed ingestion adapters without introducing mocked upstream behavior.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, asyncpg, Neo4j Python driver, httpx, PostgreSQL, Neo4j, pytest, pytest-asyncio, SQL migrations.

**Spec:** `docs/superpowers/specs/2026-09-07-biomedical-evidence-graph-design.md`

## Global Constraints

- Every governed assertion MUST have source provenance and a stable content hash.
- Evidence quality MUST remain multidimensional; no universal truth score.
- Conflicts MUST be preserved and surfaced rather than silently resolved.
- Historical assertions MUST remain queryable.
- Existing public-source adapters remain live; upstream mocks are prohibited.
- Patient-level HIE/FHIR data remain access-controlled and segregated from public biomedical evidence.
- Human authority remains final; outputs remain research-advisory and non-prescriptive.
- Neo4j is a projection, not the authoritative evidence store.
- Secrets MUST remain outside source control.

---

### Task 1: Add governed graph domain models

**Files:**
- Create: `engines/biomedical_evidence_models.py`
- Test: `tests/test_biomedical_evidence_models.py`

**Interfaces:**
- Produces typed models: `SourceRecord`, `CanonicalEntity`, `EvidenceAssertion`, `EvidenceAssessment`, `ConflictGroup`, `IngestionObservation`, `GraphPathStep`.

- [ ] **Step 1: Write failing validation tests** for required identifiers, timestamps, evidence dimensions, and prohibited empty provenance.
- [ ] **Step 2: Run `pytest tests/test_biomedical_evidence_models.py -v` and verify failure.**
- [ ] **Step 3: Implement strict Pydantic models with enums for entity types, evidence types, review states, conflict states, directness, and replication.**
- [ ] **Step 4: Run the focused test and verify PASS.**
- [ ] **Step 5: Commit `feat: add governed biomedical evidence models`.**

### Task 2: Implement source registry and source observations

**Files:**
- Create: `engines/evidence_source_registry.py`
- Test: `tests/test_evidence_source_registry.py`

**Interfaces:**
- `EvidenceSourceRegistry.register(source: SourceRecord) -> SourceRecord`
- `EvidenceSourceRegistry.get(source_id: str) -> SourceRecord`
- `EvidenceSourceRegistry.list() -> list[SourceRecord]`
- `EvidenceSourceRegistry.validate_access(source_id: str) -> bool`

- [ ] **Step 1: Write failing tests for stable source IDs, duplicate registration rejection, and access-policy validation.**
- [ ] **Step 2: Run the focused tests and verify failure.**
- [ ] **Step 3: Implement registry semantics and register existing CDC, OpenNeuro, ClinicalTrials.gov, openFDA, NLM, PubMed, and Europe PMC adapters with explicit public/controlled/licensed metadata.**
- [ ] **Step 4: Run focused tests and verify PASS.**
- [ ] **Step 5: Commit `feat: add governed biomedical source registry`.**

### Task 3: Add PostgreSQL schema and migration

**Files:**
- Create: `migrations/001_biomedical_evidence_graph.sql`
- Create: `engines/evidence_graph_repository.py`
- Modify: `requirements.txt`
- Modify: `docker-compose.yml`
- Test: `tests/integration/test_postgres_evidence_graph.py`

**Interfaces:**
- `EvidenceGraphRepository.connect() -> None`
- `upsert_source(...)`
- `record_observation(...)`
- `upsert_entity(...)`
- `create_assertion(...)`
- `create_assessment(...)`
- `create_conflict_group(...)`
- `get_entity(...)`
- `get_assertions_for_entity(...)`
- `get_assertion(...)`
- `list_sources(...)`
- `ingestion_status(...)`

- [ ] **Step 1: Write live PostgreSQL integration tests for schema creation, entity uniqueness, assertion provenance constraints, and idempotent source-record ingestion.**
- [ ] **Step 2: Run integration tests against the repository PostgreSQL service and verify failure before implementation.**
- [ ] **Step 3: Implement normalized PostgreSQL tables for sources, source observations, entities, entity identifiers, assertions, evidence assessments, conflict groups/members, ingestion runs, and graph projections.**
- [ ] **Step 4: Add indexes and constraints for canonical identifiers, source-record identity, assertion hashes, temporal fields, and foreign keys.**
- [ ] **Step 5: Add PostgreSQL service and health dependency to Docker Compose using environment-driven credentials.**
- [ ] **Step 6: Implement asyncpg repository transactions with parameterized SQL only.**
- [ ] **Step 7: Run integration tests and verify PASS.**
- [ ] **Step 8: Commit `feat: add persistent biomedical evidence graph store`.**

### Task 4: Integrate immutable provenance and idempotent ingestion

**Files:**
- Create: `engines/governed_evidence_ingestion.py`
- Modify: `engines/evidence_ledger.py`
- Test: `tests/test_governed_evidence_ingestion.py`

**Interfaces:**
- `GovernedEvidenceIngestion.ingest_observation(...) -> IngestionObservation`
- `GovernedEvidenceIngestion.normalize_entity(...) -> CanonicalEntity`
- `GovernedEvidenceIngestion.assert_relation(...) -> EvidenceAssertion`

- [ ] **Step 1: Write deterministic tests proving identical source records yield one assertion and distinct source versions yield separate historical observations.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement canonical JSON hashing, observation persistence, entity resolution, immutable assertions, and ledger linkage.**
- [ ] **Step 4: Ensure missing provenance fails closed before graph publication.**
- [ ] **Step 5: Run focused tests and verify PASS.**
- [ ] **Step 6: Commit `feat: govern evidence ingestion with immutable provenance`.**

### Task 5: Implement biomedical canonicalization and identifier resolution

**Files:**
- Create: `engines/biomedical_canonicalization.py`
- Test: `tests/test_biomedical_canonicalization.py`

**Interfaces:**
- `canonicalize_label(label: str) -> str`
- `normalize_identifier(namespace: str, identifier: str) -> str`
- `resolve_entity_key(entity_type: str, identifiers: list[tuple[str, str]], normalized_label: str) -> str`
- `canonicalize_record(...) -> CanonicalEntity`

- [ ] **Step 1: Write tests for stable normalization, namespace preservation, Unicode/whitespace handling, and no fabricated identifiers.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement deterministic normalization and identifier-key generation without inventing biological identity.**
- [ ] **Step 4: Run focused tests and verify PASS.**
- [ ] **Step 5: Commit `feat: add biomedical entity canonicalization`.**

### Task 6: Implement conflict detection

**Files:**
- Create: `engines/evidence_conflict_engine.py`
- Test: `tests/test_evidence_conflict_engine.py`

**Interfaces:**
- `EvidenceConflictEngine.detect(assertions: list[EvidenceAssertion]) -> list[ConflictGroup]`
- `compare_assertions(left, right) -> ConflictGroup | None`

- [ ] **Step 1: Write tests for opposite effects, positive/null findings, incompatible classifications, supersession, and non-conflicts caused by different populations/endpoints.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement conservative predicate/evidence-type-aware comparison rules and explicit `OPEN`, `MIXED`, `RESOLVED_BY_SOURCE`, and `HUMAN_REVIEW_REQUIRED` states.**
- [ ] **Step 4: Persist conflict groups and memberships transactionally with assertions.**
- [ ] **Step 5: Run focused tests and verify PASS.**
- [ ] **Step 6: Commit `feat: detect and preserve biomedical evidence conflicts`.**

### Task 7: Convert live source adapters into governed ingestion adapters

**Files:**
- Modify: `engines/cdc_data_pipeline.py`
- Modify: `engines/openneuro_pipeline.py`
- Modify: `engines/clinical_trials_pipeline.py`
- Modify: `engines/openfda_pipeline.py`
- Modify: `engines/nlm_research_pipeline.py`
- Modify: `engines/europe_pmc_pipeline.py`
- Modify: `engines/pubmed_literature_bridge.py`
- Create: `engines/source_ingestion_adapters.py`
- Test: `tests/integration/test_live_source_ingestion.py`

**Interfaces:**
- `LiveSourceIngestionAdapter.ingest(query: str, limit: int) -> list[EvidenceAssertion]`

- [ ] **Step 1: Write live integration tests that retrieve actual records and require source IDs, retrieval timestamps, source-record IDs, and content hashes.**
- [ ] **Step 2: Run live integration tests and record any current upstream schema failures without substituting mocks.**
- [ ] **Step 3: Implement adapters that transform actual upstream payloads into governed observations/assertions while retaining raw source identity.**
- [ ] **Step 4: Verify ClinicalTrials.gov v2, openFDA paths, OpenNeuro GraphQL, CDC SODA, NLM Clinical Tables, Europe PMC, and PubMed against current live contracts.**
- [ ] **Step 5: Run live integration tests and verify PASS or isolate a documented upstream outage/schema-drift failure.**
- [ ] **Step 6: Commit `feat: govern live biomedical source ingestion`.**

### Task 8: Implement Neo4j projection for KRAGEN

**Files:**
- Create: `engines/neo4j_evidence_projection.py`
- Modify: `engines/kragen_graph_engine.py`
- Modify: `requirements.txt`
- Modify: `docker-compose.yml`
- Test: `tests/integration/test_neo4j_projection.py`

**Interfaces:**
- `Neo4jEvidenceProjection.project_assertion(assertion: EvidenceAssertion) -> None`
- `Neo4jEvidenceProjection.project_entity(entity: CanonicalEntity) -> None`
- `Neo4jEvidenceProjection.project_conflict(conflict: ConflictGroup) -> None`
- `Neo4jEvidenceProjection.rebuild() -> dict[str, int]`

- [ ] **Step 1: Write live Neo4j integration tests for node/edge projection, provenance properties, idempotent MERGE behavior, and rebuild counts.**
- [ ] **Step 2: Run tests against the repository Neo4j service and verify failure before implementation.**
- [ ] **Step 3: Implement parameterized Cypher projection using canonical entities and evidence-bearing assertion relationships.**
- [ ] **Step 4: Preserve conflict groups and assertion IDs as graph properties.**
- [ ] **Step 5: Make projection rebuildable entirely from PostgreSQL governed records.**
- [ ] **Step 6: Run integration tests and verify PASS.**
- [ ] **Step 7: Commit `feat: add Neo4j governed evidence projection`.**

### Task 9: Add provenance-aware graph query service and API

**Files:**
- Create: `engines/evidence_graph_service.py`
- Modify: `api/main.py`
- Test: `tests/test_evidence_graph_api.py`

**Interfaces:**
- `EvidenceGraphService.entity(entity_id: str) -> dict`
- `EvidenceGraphService.assertions(entity_id: str, filters: ...) -> dict`
- `EvidenceGraphService.path(subject_id: str, predicates: list[str], max_hops: int) -> dict`
- `EvidenceGraphService.conflicts(...) -> dict`
- `EvidenceGraphService.sources(...) -> dict`

Endpoints:

```text
GET /api/v1/evidence/entities/{entity_id}
GET /api/v1/evidence/entities/{entity_id}/assertions
GET /api/v1/evidence/path
GET /api/v1/evidence/graph
GET /api/v1/evidence/conflicts
GET /api/v1/evidence/assertions/{assertion_id}
GET /api/v1/evidence/sources
GET /api/v1/evidence/sources/{source_id}
GET /api/v1/evidence/ingestion/status
```

- [ ] **Step 1: Write API contract tests for envelope shape, provenance presence, conflict exposure, time/evidence filters, and advisory metadata.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement service methods over the repository with bounded traversal and explicit unsupported-path behavior.**
- [ ] **Step 4: Add routes to FastAPI without removing existing research endpoints.**
- [ ] **Step 5: Run API tests and verify PASS.**
- [ ] **Step 6: Commit `feat: expose provenance-aware evidence graph API`.**

### Task 10: Add ingestion observability and health reporting

**Files:**
- Create: `engines/evidence_graph_observability.py`
- Modify: `api/main.py`
- Test: `tests/test_evidence_graph_observability.py`

**Interfaces:**
- `record_ingestion_metrics(...) -> None`
- `source_health(...) -> dict`
- `graph_health(...) -> dict`

- [ ] **Step 1: Write tests for source latency, success/failure, records ingested/deduplicated, conflicts, freshness, and projection lag.**
- [ ] **Step 2: Implement structured metrics without storing patient identifiers.**
- [ ] **Step 3: Add health output distinguishing application, database, Neo4j, and upstream source state.**
- [ ] **Step 4: Run focused tests and verify PASS.**
- [ ] **Step 5: Commit `feat: add evidence graph observability`.**

### Task 11: Security and compliance hardening

**Files:**
- Modify: `docker-compose.yml`
- Modify: `requirements.txt`
- Create: `docs/EVIDENCE_GRAPH_SECURITY.md`
- Test: `tests/test_evidence_graph_security.py`

- [ ] **Step 1: Write tests proving credentials are environment-driven, public endpoints reject patient identifiers, and malformed payloads fail closed.**
- [ ] **Step 2: Add non-root database/application defaults where compatible, bounded request sizes/timeouts, and explicit CORS/auth boundaries appropriate to the existing application.**
- [ ] **Step 3: Document public versus controlled source access and patient-data segregation.**
- [ ] **Step 4: Run security tests and verify PASS.**
- [ ] **Step 5: Commit `security: harden governed evidence graph boundaries`.**

### Task 12: Full verification, documentation, and integration audit

**Files:**
- Create: `docs/EVIDENCE_GRAPH_OPERATIONS.md`
- Create: `docs/EVIDENCE_GRAPH_DATA_DICTIONARY.md`
- Modify: `README.md`
- Test: `tests/integration/test_full_evidence_graph.py`

- [ ] **Step 1: Run syntax/static validation over all changed Python modules.**
- [ ] **Step 2: Start PostgreSQL and Neo4j services from Docker Compose.**
- [ ] **Step 3: Apply migrations and verify database constraints/indexes.**
- [ ] **Step 4: Run deterministic tests without mocks.**
- [ ] **Step 5: Run live upstream integration tests.**
- [ ] **Step 6: Run Neo4j projection/rebuild tests.**
- [ ] **Step 7: Start FastAPI and exercise health, evidence, path, conflict, source, and existing research endpoints.**
- [ ] **Step 8: Verify provenance lineage from source request through graph path.**
- [ ] **Step 9: Verify conflict preservation and historical assertions.**
- [ ] **Step 10: Document actual verification results, including any external upstream failures.**
- [ ] **Step 11: Commit `docs: finalize biomedical evidence graph operations and verification`.**

## Final Acceptance

The implementation is complete only when every governed assertion is provenance-bearing, source/version/timestamp metadata are preserved, ingestion is idempotent, conflicts remain visible, graph paths expose edge-level evidence, source access policies are explicit, Neo4j can be rebuilt from governed records, existing public research endpoints remain operational, and verification results are based on actual execution rather than mocks or assumptions.
