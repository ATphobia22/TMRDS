# Quantum Research Navigation Cube (QRNC)

**Status:** Research-advisory only. Not SaMD. Not a cure engine. Human authority final.

## Metaphor

Six faces are **evidence planes**. Rotating the cube changes which research **arrows** a clinician reviews. Solving the cube is navigation of incomplete evidence — not a clinical endpoint.

| Face | Role |
|------|------|
| Disease / phenotype | OMOP / ICD concept map |
| Target / gene / pathway | CTQW + classical gene ranks |
| Structure / pocket | AFDB / Boltz / PDB metadata |
| Molecule / chemistry | ChEMBL / descriptors |
| Trials / labels | ClinicalTrials.gov / openFDA |
| Population / equity | Coverage gaps only |

## Continuous-time quantum walk (CTQW)

1. PPI adjacency matrix \(A\) (e.g. STRING edges).
2. Seed disease genes → initial state superposition.
3. Evolve \(|\psi(t)\rangle = e^{-iAt}|\psi_0\rangle\) via classical eigensolve.
4. Rank candidates by probability mass \(p_i = |\langle i|\psi(t)\rangle|^2\).
5. Always compare to classical PageRank-style baseline.

Backend tag: `classical_linear_algebra_simulator`. Scores are retrieval hypotheses, not pathogenicity.

## Open-source wiring priority

1. AlphaFold DB API (live metadata) — already in TMRDS
2. STRING (PPI for CTQW)
3. Open Targets + ChEMBL
4. ClinicalTrials.gov + openFDA
5. Boltz-2 (MIT) for complexes — preferred open alternative to AF3 weights
6. AlphaFold 3 only behind academic license; mocks return `MOCK_ONLY`

## API

```
GET  /api/v1/research/cube
POST /api/v1/research/cube/arrows
POST /api/v1/research/cube/gene-prioritize
GET  /api/v1/research/cube/integrations
```

## UI

`frontend/navigation_cube.html`

## Forbidden

No cure %, no Innovation Spark clinical gates, no autonomous prescribing.
