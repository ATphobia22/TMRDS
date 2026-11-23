# Quantum Rubik's Research Cube — reproducible Grover benchmark and open-source roadmap

**Scope:** public, anonymous, research metadata and mathematical demonstration. Human Authority Final. Not SaMD; not clinical care, therapeutic recommendation, or a cure.

## What has actually been implemented

The live cube is a three-dimensional, rotatable **visual navigation model** with six scientific evidence planes. The new bounded `GET /api/v1/research/cube-search` computes **exact textbook Grover amplitude amplification** with the Python standard library, representing the six planes with six qubits / 64 abstract research review configurations. Its *phase oracle* returns true for configurations containing the requested coverage planes and no more than the requested review budget. The algorithm applies negative phase to marked states, then the Grover diffusion transformation `a_i <- 2*mean(a)-a_i`, repeating a bounded number of times.

The endpoint reports the oracle, deterministic SHA-256 receipt, marked count, exact simulated probability, 64-evaluation classical enumerative baseline, idealized quantum oracle count, and a bounded set of marked example configurations. Its browser control runs from the same-origin public research backend, not the GitHub Pages static site. No SMILES, biomarker, EHR, personal health detail, clinical label, chemical target prediction, or patient record is accepted.

**Crucial distinctions**:
- The original **Grover search algorithm** concerns amplifying amplitudes of states satisfying an *implemented oracle*. It does not know a disease's cure and has not solved the astronomical oracle-construction and data-loading costs.
- The original **GROVER molecular graph model** (Rong et al., NeurIPS 2020) is an unrelated graph-transformer model; the repository's `engines/grover_molecular_node.py` remains separate and must not be described as a quantum-search program.
- **Sparse Blossom**, implemented in **PyMatching v2**, is a minimum-weight perfect-matching **quantum-error-correction syndrome decoder**. It is not a biomedical hypothesis matcher, drug-target solver or replacement for clinical evidence checking. Stim may generate QEC benchmark circuits. Neither package is installed in the public research container.
- An exact statevector run on a conventional CPU is **not quantum hardware**, a wall-clock speedup, quantum advantage, a molecule simulation or proof of treatment efficacy.
- A square or cube of choices cannot encode all causal, mechanistic, regulatory or clinical unknowns of an illness. Multi-source clinical research requires independent experimental and human assessment.

### Reproduce the bounded demonstration

```bash
python -m unittest discover -s tests -p 'test_cube_grover_research.py' -v
python - <<'PY'
from engines.cube_grover_research import simulate_grover_research_plan
r = simulate_grover_research_plan()
print(r["algorithm"], r["oracle"], r["simulated_probability_of_valid_plan"])
PY
```

API: `/api/v1/research/cube-search?required=disease_phenotype,target_pathway,trials_labels&max_planes=4`. GET only; the endpoint rejects arbitrary plane names and allows only six choices and a six-qubit space. The **uniform baseline** probability is 4/64 for the default query. All returned probabilities are synthetic plan-search probabilities, not scientific confidence intervals.

## Open-source technology verified and catalogued

Repository and license metadata checked against official repositories on **2026-11-23**. The public 122-entry registry now additionally lists seven reviewed discovery candidates with `integration_state=optional_not_installed`, `clinical_access_enabled=false`, `public_api_connected=false`. Cataloguing does not install or execute them.

| Project | Official repository | Code license as listed | Safe integration target |
|---|---|---|---|
| PyMatching / Sparse Blossom | https://github.com/oscarhiggott/PyMatching | Apache-2.0 | Offline QEC simulation benchmarking, separated from medical ranking |
| Stim | https://github.com/quantumlib/Stim | Apache-2.0 | QEC circuit and detector modeling; optional research runtime |
| DeepChem | https://github.com/deepchem/deepchem | MIT | Offline QSAR and curated molecular benchmark evaluation; per-dataset model review |
| Boltz-2 | https://github.com/jwohlwend/boltz | MIT | GPU-only sandbox for biomolecular complexes; hold-out assays/affinity validation |
| scispaCy | https://github.com/allenai/scispacy | Apache-2.0 | Local biomedical NER under approved text rights |
| medspaCy | https://github.com/medspacy/medspacy | MIT | Negation/section detection in separately authorized environments |
| Presidio | https://github.com/microsoft/presidio | verify exact release | Supplementary local PII detection; never claim it ensures HIPAA compliance |

Already catalogued or present in the repository: Orthanc, OHIF, 3D Slicer, pydicom, MONAI/MONAI Label, Synthea, OpenEMR, HAPI FHIR, Nextflow/nf-core, RDKit, OpenMM, OpenFermion, PySCF and Qiskit. **None of their presence in the catalog proves that their servers, licensed data, model weights or runtime binaries are installed.** Each is a different risk and maintenance boundary.

## Full scientific stack: gated work packages (not yet implemented)

1. **Evidence discovery**: existing source-bounded PubMed, PMC, Europe PMC, ClinicalTrials.gov, Open Targets, ChEMBL, Reactome, GWAS Catalog v2, FDA, PubChem and other metadata adapters. Preserve PMIDs/DOIs/NCT/UniProt/ChEMBL source identifiers, dates, access rights, and `source_unavailable`; never treat matching PMIDs as independent replications.
2. **Molecular hypotheses**: extend RDKit sanitized molecule generation, ChEMBL assay distinctions, target protein accessions, OpenMM energies, DeepChem baseline models. Pair each score with a specific objective, target, provenance, negative controls, out-of-distribution/ADMET caveats and held-out assay validation. Boltz-2 requires separate model-weight rights/compute and external benchmarking.
3. **Genomics**: prepare isolated nf-core pipelines, ClinVar/germline provenance, VCF/BCF, BAM/CRAM, FASTQ/FASTA and reference genome/consent checks, synthetic test datasets first. DeepVariant and GATK are separate execution environments with licenses, large reference assets and hardware budgets; do not load them into the free public API.
4. **Imaging**: retain the existing research-mode OHIF and bounded DICOMweb access. Model bundles loaded into MONAI must have source signature/checksum, license and human-reviewed use-case. Orthanc and 3D Slicer require their own authorized storage/PACS and security perimeter. In particular, the public research API is never a PACS or patient upload service.
5. **Clinical NLP / records**: optional local Presidio + medspaCy/scispaCy pipelines require rights, access control, privacy testing, negative-identifier leak testing and human sampling. No de-identifier is sufficient on its own. Actual EHRs/FHIR exchange need separate authentication, audit trails, permissions and compliance review.
6. **Quantum research**: first establish robust classical baselines and chemically meaningful optimization objectives, such as molecular conformation or combinatorial target prioritization. Next benchmark on exact Qiskit Aer statevectors with oracle construction and total computational costs charged. Only then evaluate QPUs with actual provider/job receipt and a preregistered advantage criterion. PyMatching + Stim belong behind a distinct hardware error-correction interface.
7. **Source & experimental validity**: compare independent laboratory and prospective evidence where possible; use dated official source snapshots, negative controls, source-specific licensing/retention, multi-cohort validation and adjudication by qualified experts.

The site does **not** support unrestricted ingestion of PDFs, proprietary full text, DICOM studies, personal EHRs, arbitrary URLs, arbitrary Python packages, medical devices, or controlled-access genetics. Actual file-format coverage is explicitly enumerated in `/api/v1/research/file-format-capabilities` and cannot truthfully be called “all medical research formats.”

## Mathematics and limits

For `N=2^n` candidate bitstrings and `M` marked states, put `theta = asin(sqrt(M/N))`. After `r` ideal Grover iterations, the success probability of measuring one of the marked *abstract configurations* is

```text
P(valid plan) = sin²((2r + 1) theta)
r ≈ round(pi / (4 theta) - 1/2)
```

The oracle's validity is chosen by the developer/user; the algorithm does not discover which clinical hypotheses are true. Constructing that oracle can itself be harder than searching. The present simulator enumerates its truth table classically, so **no runtime advantage has been claimed**.

**Primary references:**
- IBM/Qiskit textbook: https://qiskit.qotlabs.org/docs/tutorials/grovers-algorithm
- Qiskit Grover adaptive search: https://qiskit-community.github.io/qiskit-optimization/tutorials/04_grover_optimizer.html
- PyMatching v2: https://pymatching.readthedocs.io/en/latest/
- Sparse Blossom original peer-reviewed article: https://quantum-journal.org/papers/q-2025-01-20-1600/
- RDKit: https://www.rdkit.org/docs/Install.html
- DeepChem: https://github.com/deepchem/deepchem
- Boltz-2: https://github.com/jwohlwend/boltz
