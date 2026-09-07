# TMRDS Source-Governed Biomedical Evidence Graph

**Date:** 2026-09-07  
**Status:** Design approved in conversation; implementation pending written-spec review  
**Scope:** Research infrastructure layer for TMRDS

## 1. Purpose

TMRDS currently contains live research-source adapters, an Evidence Ledger, and a KRAGEN-oriented graph engine. This design upgrades those capabilities into a source-governed biomedical evidence graph rather than a collection of independent search endpoints.

The graph connects:

`Disease → Phenotype → Gene → Variant → Protein → Pathway → Compound → Drug → Trial → Publication → Imaging Dataset`

and supports additional biomedical entities and relationships while preserving source provenance, temporal state, evidence quality, conflicts, and human authority.

The graph is a research-discovery system. It does not autonomously diagnose, prescribe, issue treatment directives, or assert that a candidate intervention is a cure.

## 2. Existing Architecture Constraints

The design must preserve the existing TMRDS sovereignty model:

- Technology informs people; it does not silently govern people.
- Human authority remains final.
- Evidence precedes inference.
- Automated rankings and research conclusions remain advisory until explicitly accepted by authorized humans.
- Patient-level HIE/INPC data remain access-controlled and DUA/IRB/BAA-gated as applicable.
- Offline sovereign-edge operation must remain possible for local clinical/research workflows.
- The existing Evidence Ledger remains the provenance foundation.
- Neo4j remains the intended production graph-store path documented by TMRDS; the graph abstraction must not make the system dependent on a single storage vendor.

## 3. Architectural Principles

### 3.1 Provenance-first

Every imported or derived assertion must be traceable to one or more source records. An edge without provenance is invalid in the governed evidence layer.

### 3.2 Immutable evidence

Source observations and assertion records are append-only. Corrections, supersession, and new interpretations create new records rather than silently rewriting historical evidence.

### 3.3 Entity/Assertion separation

Canonical entities represent what a biomedical object is. Assertions represent what a source says about relationships between entities. This prevents a database identity from being mistaken for scientific truth.

### 3.4 Evidence quality is multidimensional

TMRDS must not collapse study design, source authority, replication, directness, recency, and methodology into a single unqualified truth score.

### 3.5 Conflicts are first-class data

Contradictory or heterogeneous findings must be represented and surfaced. Conflict detection may identify disagreement but must not silently resolve scientific controversy.

### 3.6 Open versus controlled access

Public/open sources, credentialed sources, institutional sources, and licensed sources must be represented with explicit access policy. TMRDS must not bypass authentication, licensing, IRB, DUA, BAA, or other access controls.

### 3.7 Reproducibility

Every ingestion operation records query/request parameters, retrieval time, source version/data timestamp when available, content hash, adapter version, and normalization version.

## 4. Logical Architecture

```text
                     ┌─────────────────────────┐
                     │ Source Registry          │
                     │ authority / license      │
                     │ update / access policy   │
                     └────────────┬────────────┘
                                  │
LIVE / CONTROLLED SOURCES         │
CDC · FDA · NIH/NLM · PubMed      │
Europe PMC · ClinicalTrials       │
OpenNeuro · genomics · pathways   │
proteomics · compounds · imaging  │
                                  ▼
                     ┌─────────────────────────┐
                     │ Source Adapter Layer     │
                     │ typed retrieval         │
                     │ schema validation       │
                     │ retry/rate-limit policy │
                     └────────────┬────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │ Canonicalization Layer  │
                     │ identifiers / terms     │
                     │ entity resolution       │
                     │ units / versions        │
                     └────────────┬────────────┘
                                  ▼
              ┌────────────────────────────────────┐
              │ Governed Biomedical Evidence Graph │
              │ entities + typed assertions        │
              │ temporal validity + evidence       │
              └───────────────┬────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
       ┌──────────────────┐       ┌──────────────────┐
       │ Evidence Ledger  │       │ Conflict Engine  │
       │ hashes / lineage │       │ detection/groups │
       └────────┬─────────┘       └────────┬─────────┘
                └────────────┬─────────────┘
                             ▼
                  ┌─────────────────────┐
                  │ Research API / RAG  │
                  │ paths / evidence    │
                  │ provenance / review │
                  └─────────────────────┘
```

## 5. Canonical Entity Model

Initial first-class entity types:

- Disease
- Phenotype
- Gene
- Variant
- Protein
- Pathway
- Compound
- Drug
- ClinicalTrial
- Publication
- Preprint
- ImagingDataset
- ResearchDataset
- Study
- Organization
- Investigator
- Biomarker
- AnatomicalStructure
- CellType
- Tissue
- Population
- DrugTarget
- AdverseEvent

Entities must support source-specific identifiers without replacing canonical identity. At minimum, the model must permit multiple identifiers, namespace, label, normalized label, synonyms, source references, created/updated timestamps, and entity-version history.

## 6. Assertion / Edge Model

An evidence edge contains at least:

- `assertion_id`
- `subject_entity_id`
- `predicate`
- `object_entity_id`
- `source_id`
- `source_record_id`
- `source_uri` when permitted
- `published_at` when available
- `retrieved_at`
- `source_version` or source data timestamp when available
- `adapter_version`
- `normalization_version`
- `evidence_type`
- `evidence_grade`
- `directness`
- `replication_state`
- `effect_direction` when applicable
- `effect_measure` and units when applicable
- `population_context` when available
- `methodology`
- `content_hash`
- `supersedes_assertion_id` when applicable
- `conflict_group_id` when applicable
- `human_review_state`

An assertion is not considered a clinical recommendation merely because it connects a drug to a disease.

## 7. Relationship Vocabulary

The initial relationship vocabulary includes:

- `has_phenotype`
- `associated_with`
- `causes`
- `predisposes_to`
- `contains_variant`
- `affects_protein`
- `participates_in`
- `targets`
- `inhibits`
- `activates`
- `modulates`
- `investigated_in`
- `reports`
- `studies`
- `uses_dataset`
- `measures`
- `has_biomarker`
- `has_adverse_event`
- `mentioned_in`
- `derived_from`
- `same_as`
- `possibly_same_as`

New predicates require registry documentation and source semantics before ingestion.

## 8. Evidence Model

Evidence is represented independently from graph topology.

### Evidence dimensions

1. **Evidence type** — e.g. randomized trial, cohort, case-control, observational, computational, animal, in-vitro, curated database.
2. **Source authority** — regulatory, government/curated, peer-reviewed, preprint, institutional, computational/derived.
3. **Directness** — direct human evidence, indirect human evidence, preclinical, computational.
4. **Replication** — single observation, replicated, independently replicated, unknown.
5. **Methodological quality** — study-design-specific assessment where supported.
6. **Recency** — publication and retrieval timestamps.
7. **Graph confidence** — machine-calculated confidence kept separate from scientific truth.
8. **Human review** — unreviewed, reviewed, accepted-for-research, rejected, superseded.

No universal numerical evidence score may be presented as a substitute for expert interpretation.

## 9. Provenance and Evidence Ledger

The existing `EvidenceLedger` is retained as the low-level append-only provenance mechanism. The graph layer wraps it with typed records and database references.

Required lineage:

```text
source request
  → raw source record
  → normalized source record
  → canonical entities
  → assertion
  → evidence assessment
  → graph projection
  → derived research result
```

Every derived result must be able to enumerate the assertions and source records from which it was derived.

Content hashes must use canonical serialization and stable algorithms. Hashes identify content; they do not establish scientific validity.

## 10. Temporal Model

The graph distinguishes:

- source publication time
- source effective time when available
- source retrieval time
- ingestion time
- TMRDS normalization time
- assertion validity interval
- supersession time

Historical states must remain queryable. A newer source does not automatically delete an older source assertion.

## 11. Conflict Detection

The conflict engine identifies candidate conflicts based on compatible assertion semantics.

Examples:

- opposite effect directions for the same relationship and comparable population/endpoint
- positive versus null findings
- mutually incompatible classifications
- inconsistent variant interpretations
- source-version disagreement
- duplicate entity records with incompatible identity claims
- incompatible units or measurement scales
- superseded versus active source assertions

Conflict output contains:

- `conflict_group_id`
- participating assertions
- conflict type
- detected_at
- comparison basis
- affected entities
- status: `OPEN`, `MIXED`, `RESOLVED_BY_SOURCE`, or `HUMAN_REVIEW_REQUIRED`
- resolution provenance if a human or authoritative source resolves it

Automatic conflict detection must be conservative. False-positive conflict groups are preferable to silent deletion of disagreement, but the implementation should minimize noisy comparisons through predicate- and evidence-type-aware rules.

## 12. Storage Strategy

The logical model is storage-neutral.

### Initial persistence target

Use PostgreSQL-compatible relational persistence for canonical entities, assertions, provenance, source registry, conflict groups, and ingestion state when it fits the existing TMRDS deployment.

### Production graph projection

Support Neo4j as the production graph projection consistent with the existing TMRDS Neo4j/KRAGEN architecture. The projection must be rebuildable from governed relational/evidence records.

### Vector/RAG integration

Graph assertions may be rendered into retrieval statements, but vectorized text is a derived projection. Vector embeddings are never the authoritative evidence store.

## 13. Source Registry and Governance

Each source is registered with:

- stable source ID
- provider
- official name
- endpoint or access descriptor
- API/protocol
- authority class
- license
- access policy
- allowed-use constraints
- update frequency
- version/data-timestamp strategy
- schema version
- identifier namespaces
- supported entity types
- adapter implementation
- last successful retrieval
- last observed upstream timestamp
- health state

Source-specific credentials are supplied through environment/secret management and never committed to the repository.

## 14. Ingestion Pipeline

```text
Discover
  ↓
Retrieve live source data
  ↓
Validate upstream response
  ↓
Persist source observation + hash
  ↓
Normalize identifiers/terminology
  ↓
Resolve canonical entities
  ↓
Create immutable assertions
  ↓
Run conflict detection
  ↓
Project graph
  ↓
Update source/ingestion state
  ↓
Expose provenance-aware research API
```

Ingestion must be idempotent. Reprocessing the same source record should not create duplicate canonical assertions.

## 15. Initial Source Domains

Existing live adapters become governed source adapters:

- CDC public data
- OpenNeuro
- ClinicalTrials.gov API v2
- openFDA
- NLM Clinical Tables
- PubMed
- Europe PMC

Expansion should prioritize verified public/open biomedical resources, followed by explicitly credentialed or licensed resources where access is legally and technically available.

Potential future domains include:

- disease/phenotype ontologies
- genes/variants
- genomics repositories
- proteomics
- structural biology
- pathways
- chemical/compound databases
- pharmacology
- regulatory and safety data
- clinical trials
- biomedical literature/preprints
- imaging datasets
- population/epidemiologic datasets

A source is not considered integrated until its provenance, access policy, schema, identifier mapping, freshness behavior, and failure modes are documented.

## 16. API Contract

Initial research endpoints:

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

Responses must include research-advisory metadata and enough identifiers to reproduce or inspect the underlying evidence.

Example envelope:

```json
{
  "status": "research-advisory",
  "human_authority_final": true,
  "not_samd": true,
  "query": {},
  "retrieved_at": "2026-09-07T00:00:00Z",
  "results": [],
  "provenance": [],
  "conflicts": []
}
```

The timestamp above is illustrative API shape only; production responses use the actual retrieval time.

## 17. Research Query Semantics

The API must distinguish at least:

- entity lookup
- evidence lookup
- relationship traversal
- multi-hop path discovery
- source-restricted traversal
- time-bounded traversal
- evidence-type filtering
- conflict inspection
- provenance inspection

A path query such as:

`Disease → Gene → Protein → Pathway → Compound → Trial`

returns the path plus the evidence supporting every traversed edge. A path with one unsupported edge must not be represented as a fully evidenced causal chain.

## 18. Security and Privacy

- No secrets in source control.
- Least-privilege database roles.
- Source credentials isolated from application code.
- Audit ingestion and human-review actions.
- Do not expose patient identifiers through public research endpoints.
- Patient-level FHIR/HIE data remain segregated from public biomedical evidence unless an explicitly authorized data-governance pathway permits linkage.
- Treat external source content as untrusted input.
- Validate payload sizes and schemas.
- Apply rate limits and timeouts to upstream APIs.
- Fail closed when provenance is incomplete for a governed assertion.

## 19. Testing and Verification

The project explicitly requires real integrations rather than mocks for upstream-source testing.

Testing layers:

1. deterministic unit tests for canonicalization and pure graph rules
2. schema/invariant tests
3. live integration tests against supported public sources
4. database migration tests
5. provenance/hash integrity tests
6. idempotent-ingestion tests
7. conflict-detection tests using controlled assertion records
8. API contract tests
9. security tests
10. performance/load tests
11. reproducibility tests

A test must never claim an upstream service is healthy merely because a mock returned expected data.

## 20. Operational Observability

Record:

- source request count
- success/failure count
- latency
- HTTP status distribution
- rate-limit events
- validation failures
- records ingested
- records deduplicated
- entities resolved
- assertions created
- conflicts detected
- source freshness
- ingestion lag
- graph projection lag

Health endpoints should distinguish application health from upstream-source health.

## 21. Failure Handling

Upstream failures must not corrupt previously accepted evidence.

Rules:

- transient network failures → bounded retry according to source policy
- rate limits → backoff and explicit status
- malformed source payload → quarantine observation and preserve error metadata
- schema drift → fail ingestion for that source rather than guessing fields
- identifier resolution failure → retain unresolved source identity; do not fabricate canonical identity
- provenance failure → do not publish the assertion into the governed graph
- database transaction failure → rollback atomically

## 22. Migration Strategy

1. Preserve existing live research endpoints.
2. Introduce source registry and governed ingestion interfaces.
3. Introduce canonical entity/assertion persistence.
4. Adapt existing pipelines to emit governed source observations.
5. Project governed assertions into Neo4j/KRAGEN.
6. Add provenance-aware graph API.
7. Add conflict detection.
8. Expand source coverage.
9. Deprecate direct raw-aggregation paths only after equivalent governed paths are verified.

No destructive migration of existing evidence is permitted.

## 23. Acceptance Criteria

The implementation is complete only when:

- every governed graph assertion has provenance
- source and retrieval timestamps are preserved
- source/version metadata are retained when available
- canonical identifiers are traceable to source identifiers
- duplicate ingestion is idempotent
- conflicts are represented rather than hidden
- graph paths expose edge-level evidence
- source access policies are explicit
- existing public-source adapters are wired into governance
- controlled/licensed data are not treated as public
- no mocks are used for live upstream integration tests
- database migrations execute successfully
- the API contract is tested
- security controls are tested
- runtime verification has actually been executed
- failures are reported honestly rather than inferred from static code review

## 24. Non-Goals

This layer does not:

- autonomously diagnose patients
- autonomously select or prescribe treatment
- claim a treatment is a cure
- replace clinician judgment
- silently resolve scientific disagreement
- bypass restricted datasets
- scrape sources in violation of access/licensing rules
- treat LLM output or vector similarity as primary evidence
- make unsupported causal claims from associative graph paths

## 25. Future Extension

The governed graph provides the substrate for later TMRDS research capabilities including graph-based literature synthesis, molecular target discovery, imaging/laboratory correlation, hypothesis generation, reproducible computational experiments, and quantum/AI research workflows.

Those systems consume evidence from this layer; they do not rewrite its source assertions.
