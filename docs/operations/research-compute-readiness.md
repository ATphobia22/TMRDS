# Research Compute and Genetics Readiness

**Scope:** Current truthfulness and implementation status of Ensembl, molecular Hamiltonian, and quantum-research adapters.

## Ensembl REST adapter

- Gene lookup calls the live Ensembl symbol endpoint and returns only the identifier and metadata present in the upstream response. No synthetic ENSG_mock identifiers are produced.
- Expanded transcript retrieval uses /lookup/id/:id?expand=1; stable IDs, versions, exon metadata, retrieval time, and raw-response SHA-256 provenance are preserved.
- The adapter discovers available data releases via /info/data. If a caller explicitly pins a release, the lookup fails closed unless the endpoint exposes exactly that release. The default uses the live endpoint and records the observed release when unambiguous.
- The adapter supports GRCh38 and the dedicated Ensembl GRCh37 REST host. It does not claim an assembly when the source response contradicts configuration.
- VEP annotation is supported for common HGVS notation. SPDI inputs are rejected rather than converted incorrectly; robust RefSeq accession/coordinate normalization remains an explicit implementation task. Variant annotation failure is not represented as an empty successful result.

## Qiskit Nature / PySCF

- A Hamiltonian is returned only after actual construction with the optional Qiskit Nature and PySCF dependencies.
- When those dependencies are unavailable, the result is NOT_CONFIGURED, and coefficient, qubit, and term fields are null. There is no automatic hard-coded H2 fallback for a different molecular geometry.
- Hamiltonian construction is not VQE optimization and is not quantum-hardware execution. The adapter reports that boundary explicitly.

## Quantum research sandbox

- QuantumResearchSandboxFixed currently creates bounded research-reference records only. It does not execute docking, build a molecular Hamiltonian, calculate a classical baseline, run VQE, invoke a simulator, or submit hardware jobs.
- Records use NOT_CONFIGURED, no numeric scores, no fabricated qubit/shot/seed/runtime/cost metadata, and explicit limitations.
- Installed Python packages do not change the status until an actual solver adapter and result-validation contract are implemented.
- The input cap is enforced as a validation error instead of silently discarding compounds beyond the ten-item budget.

## Remaining implementation milestone

A later research-compute PR should add a real, optional pipeline with typed input models, licensing/resource-policy checks, bounded execution, a validated classical baseline, an actual tested simulator or hardware adapter, provenance for every output, artifact integrity verification, deterministic tests with small known molecular systems, and clear failure states. Do not represent package availability as scientific execution or infer treatment efficacy from computed energies.
