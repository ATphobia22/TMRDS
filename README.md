# TMRDS — Tucker Medical Research and Development System

Integrated multi-omics, imaging, PDE simulation, FHIR clinical bridge, medical LLMs, and structure prediction for precision medicine R&D — built to assist every clinician.

## Core Engines

| Module | Path | Responsibility |
|--------|------|----------------|
| **SimulationComputeMesh** | `engines/simulation_compute_mesh.py` | DeepXDE PINN (Fisher-KPP) for disease progression |
| **MONAIVisionNode** | `engines/monai_vision_node.py` | 3-D DICOM load + diffusion denoising/segmentation |
| **MedicalNetBackbone** | `engines/medicalnet_backbone.py` | Real MedicalNet 3D-ResNet weights via MONAI / HF |
| **PrecisionMedicineEngine** | `engines/precision_medicine_engine.py` | VCF parse + patent Freedom-to-Operate screening |
| **IntegratedEHRBridge** | `engines/integrated_ehr_bridge.py` | HL7 FHIR R4/R5 Bundle → flattened clinical structure |
| **ComprehendFHIRBridge** | `engines/comprehend_fhir_bridge.py` | AWS DetectEntitiesV2 + InferICD10CM → FHIR |
| **ClinicalLLMRouter** | `engines/clinical_llm_router.py` | vLLM / HF backends for Meditron-7B & Doctor-Dignity |
| **AlphaFold3Node** | `engines/alphafold3_node.py` | Structure prediction + structure-guided ligand ranking |
| **QuantumRubiksCureEngine** | `engines/quantum_cure_engine.py` | Hybrid quantum-classical VQE biomedical optimizer |

## Weight Download Guide

See **[docs/WEIGHTS_DOWNLOAD.md](docs/WEIGHTS_DOWNLOAD.md)** for exact Hugging Face / CLI commands for MedicalNet, Meditron, and AlphaFold3 parameters.

## Production Backends

| Capability | Production Path | Offline Fallback |
|------------|-----------------|------------------|
| 3D imaging backbone | MONAI `resnet*` + HF `TencentMedicalNet` | Feature-extractor stub |
| Clinical NLP | AWS Comprehend Medical DetectEntitiesV2 + InferICD10CM | Curated regex |
| Medical LLM | vLLM or HuggingFace transformers (Meditron-7B) | Mock clinical response |
| Structure prediction | AlphaFold Server / OpenFold3 / local AF3 | Deterministic mock metrics |

## AlphaFold3 Molecular Docking Notes

- AF3 co-folding predicts protein–ligand complexes directly from sequence + SMILES/CCD.
- Best used as **screening engine** or **post-docking filter**; complement with physics-based docking (AutoDock Vina, DOCK3).
- Confidence metrics (pLDDT, ipTM) guide pose selection; experimental validation remains mandatory.

## MONAI Imaging Stack

- Transforms, sliding-window inference, diffusion models, SegResNet / U-Net.
- MedicalNet pre-trained weights (10–200 layers) raise Dice 15–40 pts on small hospital cohorts.
- Auto3DSeg and nnU-Net runners available for full segmentation pipelines.

## Quick Start

```bash
chmod +x deploy.sh && ./deploy.sh
python tests/run_integration_test.py
```

## Safety Notice

All LLM, structure, and decision-support outputs carry an explicit research-only disclaimer. They are **not** a substitute for licensed clinical judgment.

---
**Status**: Private | Active development  
**Root Authority**: 13101 Bonebank Road
