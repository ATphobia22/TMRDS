# Verified Disease Pipeline (Research Notes)

**Status:** Research-advisory only. Not SaMD. Human authority final.

This document records registry- and label-grounded statuses used by `engines/verified_disease_pipeline.py`.

## Forbidden clinical-hype patterns

Never present as clinical truth:

- `99% closure`
- `cure engine` / `RubiksML Cure`
- `Innovation Spark` as a clinical gate
- VQE docking energy (kcal/mol) as a therapeutic endpoint
- AlphaFold pLDDT as a treatment decision criterion

## Entries

| ID | Domain | Clinical status |
|----|--------|-----------------|
| `diabetic_wound_ceria` | Diabetic wound / ceria nanoparticles | **Preclinical only** — no registered human Phase I/II/III for CeO₂ |
| `kras_g12d` | KRAS G12D inhibitors | **MRTX1133 terminated** (NCT05737706, 2025); other assets investigational; none approved |
| `als_sod1` | SOD1-ALS | **Tofersen (Qalsody) approved** (2023); **CNM-Au8 investigational** |
| `alzheimer` | Early Alzheimer’s | **Lecanemab (2023)** and **donanemab/Kisunla (2024)** approved for early disease with amyloid confirmation |

## API

```
GET /api/v1/research/disease-pipeline
GET /api/v1/research/disease-pipeline/{entry_id}
```

## Disclaimer

These notes are not treatment recommendations. Verify current trial and label status on ClinicalTrials.gov and FDA sources before any clinical use of information.
