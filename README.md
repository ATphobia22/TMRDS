# TMRDS — Tucker Medical Research and Development System

**Zero-Latency Sovereignty** medical infrastructure for rural Tri-State clinics (Indiana / Kentucky / Illinois) and high-precision research.

> Technology informs people; it does not silently govern people. Human authority remains final.

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620

## Sovereignty & Governance Engines

| Module | Path | Responsibility |
|--------|------|----------------|
| **SovereignEdge** | `engines/sovereign_edge.py` | Offline sync queue — clinics operate without internet |
| **EvidenceLedger** | `engines/evidence_ledger.py` | Immutable `content_hash` provenance |
| **DoctorDignityEthics** | `engines/doctor_dignity_ethics.py` | Bias neutralization matrix |
| **OpenMedEngine** | `engines/openmed_nlp.py` | HIPAA PII scrub + Medical NER |
| **TurboVecIndex** | `engines/turbovec_index.py` | Clinical embedding search |
| **KRAGENGraphEngine** | `engines/kragen_graph_engine.py` | Multi-layer KG + Graph-of-Thoughts RAG |
| **IHIEBridge** | `engines/ihie_bridge.py` | Indiana HIE / INPC FHIR interoperability |

## Clinical & Research Engines

| Module | Path | Responsibility |
|--------|------|----------------|
| **SimulationComputeMesh** | `engines/simulation_compute_mesh.py` | DeepXDE PINN disease progression |
| **MONAIVisionNode** | `engines/monai_vision_node.py` | 3-D DICOM + diffusion segmentation |
| **MedicalNetBackbone** | `engines/medicalnet_backbone.py` | Tencent MedicalNet 3D-ResNet |
| **PrecisionMedicineEngine** | `engines/precision_medicine_engine.py` | VCF + Freedom-to-Operate |
| **IntegratedEHRBridge** | `engines/integrated_ehr_bridge.py` | FHIR R4/R5 parser |
| **ComprehendFHIRBridge** | `engines/comprehend_fhir_bridge.py` | AWS DetectEntitiesV2 → FHIR |
| **ClinicalLLMRouter** | `engines/clinical_llm_router.py` | vLLM / HF Meditron-7B |
| **AlphaFold3Node** | `engines/alphafold3_node.py` | Structure + ligand ranking |
| **GROVERMolecularNode** | `engines/grover_molecular_node.py` | ADMET / toxicity / BBBP |
| **RDKitChemistryNode** | `engines/rdkit_chemistry_node.py` | Descriptors, conformers, Lipinski |
| **QiskitNatureBridge** | `engines/qiskit_nature_bridge.py` | Molecular Hamiltonian → VQE |
| **BioCoderAssistant** | `engines/biocoder_assistant.py` | Bioinformatics code generation |
| **QuantumRubiksCureEngine** | `engines/quantum_cure_engine.py` | Hybrid quantum-classical VQE |

## Architecture Docs

- **[docs/ARCHITECTURE_SOVEREIGNTY.md](docs/ARCHITECTURE_SOVEREIGNTY.md)** — Sovereignty, KRAGEN, IHIE, autonomy ladder
- **[docs/WEIGHTS_DOWNLOAD.md](docs/WEIGHTS_DOWNLOAD.md)** — Model weight download instructions

## Clinical Pipeline (Sovereign)

```
Clinical text → OpenMedEngine (PII scrub + NER)
             → DoctorDignityEthics (bias gate)
             → EvidenceLedger (content_hash)
             → KRAGENGraphEngine (pathology/molecular/quantum links)
             → SovereignEdge queue / IHIEBridge (sync or HIE pull)
             → FHIR / LLM / imaging / molecular engines
```

## Indiana Ecosystem

- Indiana Department of Health (IDOH)
- Indiana Medicaid
- **Indiana Health Information Exchange (IHIE)** — Indiana Network for Patient Care (INPC)
- Regenstrief Institute (Bulk FHIR research access pattern)

Live IHIE/INPC access requires institutional BAA/DUA and applicable IRB.

## Safety Notice

All LLM, structure, quantum, and decision-support outputs are **research-advisory only**. They are not a substitute for licensed clinical judgment.

---
**Status**: Private | Active development  
**Steward**: Anthony John Tucker · Mount Vernon, Indiana 47620  
**Doctrine**: Evidence before inference · Human authority final
