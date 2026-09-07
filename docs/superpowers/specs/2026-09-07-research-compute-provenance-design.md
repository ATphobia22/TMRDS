# TMRDS Research Compute and Experiment Provenance Design

**Date:** 2026-09-07  
**Repository:** `ATphobia22/TMRDS`  
**Base:** `main`

## Purpose

Extend TMRDS with a governed research-compute plane informed by the useful architectural patterns found in `ATphobia22/openml-python`, `ATphobia22/Python`, and `ATphobia22/PyMatching`, without importing those repositories wholesale or weakening the core biomedical evidence stack.

## Goals

1. Capture reproducible dataset, experiment, model, evaluation, environment, and artifact provenance.
2. Link research computations to authoritative Evidence Ledger records.
3. Provide typed graph-computation primitives for evidence/provenance traversal and analysis.
4. Provide a research-only weighted consistency/optimization layer for competing evidence relationships.
5. Establish an optional native-compute boundary for future high-performance kernels.
6. Preserve deterministic core CI and keep heavyweight scientific dependencies optional.
7. Make every research-derived result distinguishable from observed/source-backed evidence.

## Non-goals

- No autonomous diagnosis, prescribing, treatment recommendation, or clinical authority.
- No claim that graph optimization establishes medical truth.
- No direct clinical use of quantum error-correction algorithms.
- No wholesale vendoring or runtime dependency on the three reference repositories.
- No promotion of predictions/hypotheses into authoritative evidence.

## Architecture

```text
                    TMRDS RESEARCH COMPUTE PLANE

  Dataset Registry ─┐
  Experiment Registry│
  Evaluation Registry├──> Provenance Service ──> Evidence Ledger
  Model Registry ────┤             │
  Environment/Seed ─┘             ├──> Evidence Envelope
                                   └──> Research Graph
                                             │
                         ┌───────────────────┴──────────────────┐
                         ▼                                      ▼
                  Graph Compute                         Consistency /
                  traversal/search                      optimization
                         │                                      │
                         └───────────────────┬──────────────────┘
                                             ▼
                                  Research-advisory result
                                             │
                                      Human review gate
```

The Evidence Ledger remains authoritative. PostgreSQL is authoritative for persisted evidence/provenance. pgvector and Neo4j remain derived projections. Research computations consume governed evidence and emit provenance-bearing derived artifacts.

## Provenance model

Every reproducible research run should be representable by these identifiers/attributes:

- `dataset_id`
- `dataset_version`
- `dataset_content_hash`
- `experiment_id`
- `experiment_version`
- `model_id`
- `model_version`
- `evaluation_id`
- `evaluation_procedure_id`
- `source_commit`
- `environment_hash`
- `random_seed`
- `created_at`
- `evidence_ids`

Records are append-oriented. Existing provenance records are not silently overwritten. Content hashes provide integrity checks for externally supplied artifacts and datasets.

## Evidence semantics

Research edges and results carry an explicit semantic class:

- `observed`: directly supported by an authoritative/source-backed record.
- `derived`: deterministic computation over governed evidence.
- `predicted`: model-generated result requiring uncertainty metadata.
- `hypothesized`: research hypothesis requiring validation.

Optimization may rank or select relationships, but it must never relabel a predicted or hypothesized relationship as observed merely because it receives a high score.

## Experiment and evaluation boundaries

The Experiment Registry records what was run; the Evaluation Registry records how performance or consistency was assessed. Evaluation procedures are versioned and immutable after execution linkage. Metrics must identify the metric name, value, units where applicable, evaluation procedure, and uncertainty/limitations where available.

Model and prompt provenance are linked to existing AI Governance controls. Generated outputs retain an evidence envelope containing model/version, retrieval timestamp, evidence IDs, prompt/policy provenance where applicable, uncertainty, and human-review status.

## Graph compute

The graph layer exposes small typed primitives rather than importing the `ATphobia22/Python` repository. Initial capabilities include:

- breadth/depth traversal;
- shortest path over non-negative weighted edges;
- connected components;
- dependency/provenance path extraction;
- bounded neighborhood traversal;
- deterministic ordering and explicit limits.

Algorithms must operate on explicit typed graph inputs and return structured results with provenance/context sufficient for audit.

## Research consistency optimization

The optimization layer may score evidence relationships using factors such as source authority, evidence quality, replication, recency, methodology, provenance completeness, and dataset quality. Scores are advisory and must remain traceable to the input evidence and scoring policy.

The design is inspired by the graph-optimization boundary in `PyMatching`, but TMRDS does not treat minimum-weight perfect matching as a medical inference mechanism. A future optional adapter may expose high-performance/native algorithms behind a stable Python interface.

## Dependency policy

Core runtime dependencies remain the existing FastAPI/Pydantic/HTTP/PostgreSQL/Neo4j/numerical stack. The three reference repositories are architectural sources, not mandatory package dependencies. Optional research engines may be installed through explicit extras/profiles when their use case is justified.

No dependency is added solely to reproduce a reference implementation when an appropriately small, typed TMRDS implementation is sufficient.

## Security and governance

- PHI remains outside public-source research ingestion unless an explicitly governed clinical boundary exists.
- Research records require provenance and authorization metadata appropriate to their deployment boundary.
- Secrets are never stored in source code, fixtures, logs, or provenance payloads.
- Dataset/artifact hashes are integrity metadata, not confidentiality controls.
- Research outputs are non-authoritative and human-reviewable.
- Audit records must make source, computation, model, and evaluation lineage reconstructable.

## Testing requirements

Tests must cover:

1. creation and validation of provenance records;
2. immutability/content-hash behavior;
3. deterministic random-seed/environment capture;
4. dataset → experiment → model → evaluation linkage;
5. evidence-envelope linkage;
6. graph traversal and shortest-path determinism;
7. optimization scoring and semantic-class preservation;
8. rejection of incomplete/unauthorized provenance where required;
9. API contract behavior;
10. core CI remaining independent of optional scientific dependencies.

## Documentation requirements

The implementation must update the README and architecture documentation so that the research-compute plane, provenance model, optional dependency policy, and research-only boundary are accurately represented.

## Acceptance criteria

The change is complete when:

- the new provenance/evaluation subsystem is persisted through the existing PostgreSQL architecture;
- research runs can be linked to Evidence Ledger records and AI evidence envelopes;
- graph computation is available through a typed TMRDS-owned interface;
- research consistency optimization is available without asserting medical truth;
- optional/native compute has a clean interface and does not affect core startup;
- deterministic tests pass;
- GitHub Actions core CI passes on `main`;
- documentation accurately reflects implemented behavior;
- no reference repository is introduced as an unnecessary core dependency.
