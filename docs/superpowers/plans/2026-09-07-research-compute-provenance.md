# TMRDS Research Compute and Experiment Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a governed research-compute plane that records reproducible experiments, evaluations, datasets, models, environments, and evidence lineage while adding typed graph computation and research-only consistency optimization without making optional scientific dependencies part of the TMRDS core runtime.

**Architecture:** PostgreSQL remains authoritative for persisted evidence and provenance. New research-compute services use typed Pydantic/domain models and repository boundaries, connect runs to existing Evidence Ledger and AI-governance identifiers, and emit non-authoritative derived artifacts. Graph and optimization algorithms are TMRDS-owned, deterministic, provenance-aware, and isolated from heavyweight scientific/quantum packages; a narrow optional native-compute protocol is reserved for future high-performance kernels.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, PostgreSQL/asyncpg, existing TMRDS Evidence Ledger, pytest/pytest-asyncio, optional Neo4j/pgvector projections, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-07-research-compute-provenance-design.md`

## Global Constraints

- The Evidence Ledger remains authoritative.
- PostgreSQL is authoritative for persisted evidence/provenance.
- pgvector and Neo4j remain derived projections.
- Research semantics are limited to `observed`, `derived`, `predicted`, and `hypothesized`.
- Optimization MUST NOT relabel predicted or hypothesized relationships as observed.
- Core runtime MUST NOT depend on `ATphobia22/openml-python`, `ATphobia22/Python`, or `ATphobia22/PyMatching`.
- Heavy scientific dependencies remain optional and MUST NOT break core startup or deterministic CI.
- PHI MUST remain outside public-source research ingestion unless an explicitly governed clinical boundary exists.
- Secrets MUST remain outside source code, fixtures, logs, and provenance payloads.
- Research outputs remain non-authoritative and human-reviewable.
- Core development/CI targets Python 3.11.
- All changes are made directly on `main`, per the approved repository workflow.

---

### Task 1: Map Existing Persistence and Governance Interfaces

**Files:**
- Read: `engines/biomedical_evidence_models.py`
- Read: `engines/evidence_graph_repository.py`
- Read: `engines/evidence_graph_service.py`
- Read: `engines/ai_governance.py`
- Read: `engines/__init__.py`
- Read: `migrations/*`
- Read: `api/main.py`
- Read: `api/ai_governance_routes.py`
- Read: `api/evidence_retrieval_routes.py`
- Test: existing `tests/` contracts related to evidence and AI governance

**Interfaces:**
- Consumes: current Evidence Ledger, AI-governance, migration, and API patterns.
- Produces: an implementation map used by subsequent tasks; no runtime behavior changes.

- [ ] **Step 1: Inspect the existing evidence domain models and identify reusable identifiers.**

- [ ] **Step 2: Inspect existing PostgreSQL migration conventions and connection/repository patterns.**

- [ ] **Step 3: Inspect AI-governance model and route contracts for model, dataset, evaluation, and generation-envelope linkage points.**

- [ ] **Step 4: Inspect existing graph repository/service interfaces and existing tests before defining the new graph-compute boundary.**

- [ ] **Step 5: Record any naming constraints in the implementation files rather than introducing duplicate concepts.**

- [ ] **Step 6: Commit only if the mapping requires a documentation artifact; otherwise continue without a no-op commit.**

---

### Task 2: Add Immutable Research Provenance Domain Models

**Files:**
- Create: `engines/research_provenance.py`
- Test: `tests/test_research_provenance.py`
- Modify: `engines/__init__.py`

**Interfaces:**
- Produces typed models for `DatasetProvenance`, `ExperimentProvenance`, `ModelProvenance`, `EvaluationProcedure`, `EvaluationResult`, `ArtifactProvenance`, and `ResearchRunLineage`.
- Every lineage object exposes `dataset_id`, `dataset_version`, `dataset_content_hash`, `experiment_id`, `experiment_version`, `model_id`, `model_version`, `evaluation_id`, `evaluation_procedure_id`, `source_commit`, `environment_hash`, `random_seed`, `created_at`, and `evidence_ids` where applicable.

- [ ] **Step 1: Write failing tests for valid provenance construction and required identifier validation.**

```python
def test_research_run_lineage_requires_core_identity():
    lineage = ResearchRunLineage(
        dataset_id="dataset-001",
        dataset_version="1",
        dataset_content_hash="sha256:abc",
        experiment_id="experiment-001",
        experiment_version="1",
        model_id="model-001",
        model_version="1",
        evaluation_id="evaluation-001",
        evaluation_procedure_id="procedure-001",
        source_commit="abc123",
        environment_hash="sha256:def",
        random_seed=42,
        evidence_ids=["evidence-001"],
    )
    assert lineage.random_seed == 42
    assert lineage.evidence_ids == ["evidence-001"]
```

- [ ] **Step 2: Run `python -m pytest -q tests/test_research_provenance.py -v` and verify the new symbols fail before implementation.**

- [ ] **Step 3: Implement immutable Pydantic models with strict validation, UTC timestamps, normalized hashes, non-negative seeds, and explicit research semantic classes.**

- [ ] **Step 4: Prevent mutation after construction and reject empty identifiers, malformed content hashes, duplicate evidence IDs, and invalid semantic classes.**

- [ ] **Step 5: Run the focused test suite and verify all provenance-model tests pass.**

- [ ] **Step 6: Export only the stable public provenance types through the lazy engine export mechanism.**

- [ ] **Step 7: Commit with `feat: add research provenance domain models`.**

---

### Task 3: Persist Dataset, Experiment, Evaluation, Artifact, and Environment Lineage

**Files:**
- Create: `migrations/00X_research_provenance.sql` using the next migration number after inspecting `migrations/`
- Create: `engines/research_provenance_repository.py`
- Test: `tests/test_research_provenance_repository.py`

**Interfaces:**
- Consumes: models from Task 2 and the existing async PostgreSQL repository/connection pattern.
- Produces repository operations for append-oriented provenance records and lineage reconstruction.

- [ ] **Step 1: Inspect the migration numbering and existing foreign-key/index conventions.**

- [ ] **Step 2: Write failing repository contract tests covering dataset registration, experiment creation, evaluation linkage, artifact hashes, and environment/seed capture.**

- [ ] **Step 3: Add PostgreSQL tables for datasets, experiments, models, evaluation procedures, evaluations, artifacts, environments, and run/evidence lineage using UUID/text identifiers consistent with the existing schema.**

- [ ] **Step 4: Add uniqueness constraints preventing duplicate versions and content hashes from silently replacing earlier records.**

- [ ] **Step 5: Add foreign keys and indexes for dataset→experiment→model→evaluation traversal and evidence-ID lookup.**

- [ ] **Step 6: Implement parameterized async repository methods; never interpolate identifiers or user-controlled values into SQL.**

- [ ] **Step 7: Make updates append-oriented: an execution-linked provenance record cannot be overwritten; new versions create new records.**

- [ ] **Step 8: Run repository tests using isolated database fixtures/mocks matching the existing test architecture.**

- [ ] **Step 9: Commit with `feat: persist research experiment provenance`.**

---

### Task 4: Integrate Provenance with Evidence Ledger and AI Evidence Envelopes

**Files:**
- Create: `engines/research_provenance_service.py`
- Modify: `engines/ai_governance.py`
- Modify: `engines/evidence_graph_service.py` only where a stable lineage hook is required
- Test: `tests/test_research_provenance_service.py`
- Test: existing AI-governance tests

**Interfaces:**
- Consumes: provenance repository, Evidence Ledger identifiers, and existing AI-governance contracts.
- Produces: `create_research_run`, `attach_evidence`, `build_evidence_envelope`, and `reconstruct_lineage` service operations.

- [ ] **Step 1: Write failing tests proving that a research run cannot be finalized without required provenance fields.**

- [ ] **Step 2: Write failing tests proving that evidence IDs are retained verbatim and never converted into unsupported medical claims.**

- [ ] **Step 3: Write failing tests for evidence-envelope construction containing model/version, retrieval timestamp, evidence IDs, prompt/policy provenance when supplied, uncertainty, and human-review status.**

- [ ] **Step 4: Implement the service as an orchestration boundary; keep SQL in the repository and governance semantics in domain/service code.**

- [ ] **Step 5: Require explicit human-review state for generated research outputs and preserve the existing research-advisory/non-clinical boundary.**

- [ ] **Step 6: Add lineage reconstruction that returns dataset→experiment→model→evaluation→evidence relationships in deterministic order.**

- [ ] **Step 7: Run focused provenance and AI-governance tests.**

- [ ] **Step 8: Commit with `feat: link research runs to governed evidence`.**

---

### Task 5: Build the TMRDS-Owned Typed Graph Compute Layer

**Files:**
- Create: `engines/research_graph.py`
- Create: `engines/research_graph_algorithms.py`
- Test: `tests/test_research_graph.py`
- Test: `tests/test_research_graph_algorithms.py`
- Modify: `engines/__init__.py`

**Interfaces:**
- Consumes: explicit typed nodes/edges with semantic class and optional non-negative weight.
- Produces: deterministic `traverse`, `shortest_path`, `connected_components`, `bounded_neighborhood`, and provenance/dependency path results.

- [ ] **Step 1: Write failing tests for deterministic breadth-first/depth-first traversal with explicit depth and node-count limits.**

- [ ] **Step 2: Write failing tests for shortest paths over non-negative weights, including unreachable nodes and equal-weight deterministic tie-breaking.**

- [ ] **Step 3: Write failing tests for connected components and bounded neighborhoods.**

- [ ] **Step 4: Implement immutable typed `ResearchGraphNode`, `ResearchGraphEdge`, and `ResearchGraph` structures without importing `ATphobia22/Python`.**

- [ ] **Step 5: Implement BFS/DFS with deterministic sorted adjacency and hard resource limits.**

- [ ] **Step 6: Implement Dijkstra-style shortest path with rejection of negative weights and deterministic predecessor selection.**

- [ ] **Step 7: Implement connected components and bounded-neighborhood extraction.**

- [ ] **Step 8: Preserve semantic class and evidence IDs on every returned path/edge; never infer `observed` from a computed score.**

- [ ] **Step 9: Run focused graph tests and commit with `feat: add governed research graph compute`.**

---

### Task 6: Add Research Consistency and Evidence-Relationship Optimization

**Files:**
- Create: `engines/research_consistency.py`
- Test: `tests/test_research_consistency.py`
- Modify: `engines/__init__.py`

**Interfaces:**
- Consumes: graph edges plus explicit scoring policy parameters.
- Produces: ranked relationship candidates carrying score, score components, evidence IDs, semantic class, and policy version.

- [ ] **Step 1: Write failing tests for deterministic scoring across source authority, evidence quality, replication, recency, methodology, provenance completeness, and dataset quality.**

- [ ] **Step 2: Write failing tests proving that `predicted` and `hypothesized` inputs retain their semantic class regardless of score.**

- [ ] **Step 3: Implement a versioned scoring-policy object with bounded normalized factors and explicit weights whose total is validated.**

- [ ] **Step 4: Implement ranking without destructive mutation of source evidence.**

- [ ] **Step 5: Return an advisory optimization result containing policy version, input evidence IDs, component scores, total score, and limitations.**

- [ ] **Step 6: Explicitly reject unsupported negative/NaN/infinite scores and missing provenance required by the policy.**

- [ ] **Step 7: Run focused tests and commit with `feat: add research evidence consistency optimization`.**

---

### Task 7: Establish Optional Native-Compute Boundary

**Files:**
- Create: `engines/native_compute.py`
- Create: `engines/native_compute_registry.py`
- Test: `tests/test_native_compute.py`
- Modify: `engines/__init__.py`
- Modify: `requirements.txt` only if a lightweight optional marker/profile mechanism is already used; otherwise do not add a heavy dependency

**Interfaces:**
- Produces a small protocol for optional compute kernels with `name`, `version`, `capabilities`, `is_available`, and deterministic execution metadata.
- Consumes no mandatory native/quantum dependency.

- [ ] **Step 1: Write failing tests for an unavailable optional backend being reported cleanly without import-time failure.**

- [ ] **Step 2: Write failing tests for capability registration, version reporting, and deterministic metadata.**

- [ ] **Step 3: Implement a `NativeComputeBackend` protocol and registry that discovers only explicitly registered optional adapters.**

- [ ] **Step 4: Add a null/unavailable backend result instead of importing PyMatching, DeepXDE, or other heavy packages from core startup.**

- [ ] **Step 5: Verify `import engines` and the default API test suite do not require optional native/scientific dependencies.**

- [ ] **Step 6: Commit with `feat: add optional research compute boundary`.**

---

### Task 8: Add Research-Compute API Contracts

**Files:**
- Create: `api/research_compute_routes.py`
- Test: `tests/test_research_compute_api.py`
- Modify: `api/main.py`

**Interfaces:**
- Exposes research-advisory endpoints for provenance registration, run lineage retrieval, graph computation, and consistency ranking.

- [ ] **Step 1: Write failing FastAPI contract tests for request validation and research-advisory response metadata.**

- [ ] **Step 2: Add Pydantic request/response schemas using the domain models without leaking database implementation details into the API.**

- [ ] **Step 3: Implement endpoints for creating/registering provenance records and reconstructing run lineage.**

- [ ] **Step 4: Implement graph-compute endpoints with explicit limits and deterministic result ordering.**

- [ ] **Step 5: Implement consistency-ranking endpoint with explicit policy version and semantic-class preservation.**

- [ ] **Step 6: Ensure every research-compute response carries `research-advisory`, `human_authority_final`, and `not_samd` governance metadata consistent with the existing API.**

- [ ] **Step 7: Register the router in `api/main.py` without importing optional engines eagerly.**

- [ ] **Step 8: Run focused API tests and commit with `feat: expose governed research compute API`.**

---

### Task 9: Add Deterministic and Security Regression Coverage

**Files:**
- Modify/create: `tests/test_security_regressions.py`
- Modify: `.github/workflows/*` only where required
- Modify: `pytest.ini` only where required

**Interfaces:**
- Consumes all implemented research-compute components.
- Produces a deterministic core CI gate and explicit optional/integration test boundary.

- [ ] **Step 1: Add tests rejecting secrets in provenance payloads and logs.**

- [ ] **Step 2: Add tests for PHI/public-source boundary enforcement where the existing architecture provides the corresponding classification hooks.**

- [ ] **Step 3: Add tests for stable ordering and repeated seeded computations producing identical results.**

- [ ] **Step 4: Run `python -m pytest -q -m "not integration"`.**

- [ ] **Step 5: Run targeted integration tests only where PostgreSQL/Neo4j/upstream services are available.**

- [ ] **Step 6: Verify no optional dependency was accidentally introduced into `requirements.txt`.**

- [ ] **Step 7: Commit with `test: harden research compute governance boundaries`.**

---

### Task 10: Update Architecture Documentation and README

**Files:**
- Modify: `README.md`
- Create: `docs/RESEARCH_COMPUTE_ARCHITECTURE.md`
- Create: `docs/RESEARCH_EXPERIMENT_PROVENANCE.md`
- Create: `docs/RESEARCH_COMPUTE_SECURITY.md`
- Create: `docs/ADR-RESEARCH-COMPUTE-PROVENANCE.md`

**Interfaces:**
- Documentation reflects only implemented behavior and keeps the research-only boundary explicit.

- [ ] **Step 1: Document the dataset→experiment→model→evaluation→evidence lineage.**

- [ ] **Step 2: Document graph-compute primitives, deterministic limits, and observed/derived/predicted/hypothesized semantics.**

- [ ] **Step 3: Document the consistency optimizer as evidence-ranking/organization, not medical truth inference.**

- [ ] **Step 4: Document optional/native compute and explicitly state that PyMatching and the other reference repositories are architectural references rather than core runtime dependencies.**

- [ ] **Step 5: Update README repository layout, API surface, testing commands, and architecture diagram to match actual implementation.**

- [ ] **Step 6: Review documentation for unsupported clinical, FDA, HIPAA-certification, or autonomous-decision claims and remove any such claims.**

- [ ] **Step 7: Commit with `docs: document governed research compute architecture`.**

---

### Task 11: Full Verification, Review, and Main-Branch Acceptance

**Files:**
- Read: all changed implementation/test/documentation files
- Read: `.github/workflows/*`

**Interfaces:**
- Consumes: completed implementation and documentation.
- Produces: verified `main` state satisfying the approved specification.

- [ ] **Step 1: Run syntax/import verification under Python 3.11.**

- [ ] **Step 2: Run the complete deterministic suite with `python -m pytest -q -m "not integration"`.**

- [ ] **Step 3: Run focused research-provenance, graph, optimization, API, and security tests independently and inspect failures rather than masking them.**

- [ ] **Step 4: Inspect the final Git diff for accidental secrets, unnecessary dependencies, generated artifacts, debug statements, and unsupported medical claims.**

- [ ] **Step 5: Verify migrations are ordered and internally consistent with existing schema conventions.**

- [ ] **Step 6: Verify optional engines remain lazy-loaded and `import engines` does not require heavyweight scientific packages.**

- [ ] **Step 7: Trigger/inspect GitHub Actions on the final `main` commit and verify the deterministic CI gate passes.**

- [ ] **Step 8: Perform a final code-review pass against every acceptance criterion in `docs/superpowers/specs/2026-09-07-research-compute-provenance-design.md`.**

- [ ] **Step 9: Create a verification record under `docs/superpowers/verification/` containing the final commit, test commands, CI result, and any explicitly skipped integration checks with reasons.**

- [ ] **Step 10: Only after verification, report completion and provide the final `main` commit SHA.**

---

## Spec Coverage Review

| Specification requirement | Plan coverage |
|---|---|
| Reproducible dataset/experiment/model/evaluation/environment/artifact provenance | Tasks 2–4 |
| Evidence Ledger linkage | Task 4 |
| Typed graph primitives | Task 5 |
| Research-only consistency optimization | Task 6 |
| Optional/native compute boundary | Task 7 |
| Deterministic core CI | Tasks 9 and 11 |
| Observed/derived/predicted/hypothesized distinction | Tasks 2, 5, 6, 8, 10 |
| AI evidence envelopes | Task 4 |
| Security/PHI/secret controls | Tasks 4, 9, 10, 11 |
| API contracts | Task 8 |
| Documentation/ADR/README | Task 10 |
| Final verification and acceptance | Task 11 |

## Self-Review

- No reference repository is introduced as a core dependency.
- No task authorizes autonomous clinical behavior.
- Every major subsystem has focused tests before implementation.
- Provenance is append-oriented and content-hash aware.
- Graph algorithms have explicit limits and deterministic ordering.
- Optimization preserves evidence semantic class.
- Optional scientific/native computation cannot break core imports.
- The final acceptance gate requires deterministic tests, CI, migration review, security review, and documentation accuracy.
