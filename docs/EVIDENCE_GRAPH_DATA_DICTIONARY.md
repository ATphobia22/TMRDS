# TMRDS Evidence Graph Data Dictionary

| Object | Key fields | Meaning |
|---|---|---|
| Source | `source_id`, authority, license, access policy | Governance identity for an upstream source |
| Observation | source record ID, retrieval time, source version, raw hash | Immutable observation of what an upstream source returned |
| Entity | canonical ID, entity type, identifiers, normalized label | Biomedical object identity |
| Assertion | subject, predicate, object, source, evidence fields, hash | A source-backed relationship between canonical entities |
| Assessment | evidence type, directness, replication, methodology, confidence | Multidimensional assessment of an assertion |
| Conflict | conflict type, assertion members, state, comparison basis | Explicit disagreement or incompatibility |
| Projection | assertion ID, backend, projection time | Record of downstream graph materialization |

## Entity types

Disease, Phenotype, Gene, Variant, Protein, Pathway, Compound, Drug, ClinicalTrial, Publication, Preprint, ImagingDataset, ResearchDataset, Study, Organization, Investigator, Biomarker, AnatomicalStructure, CellType, Tissue, Population, DrugTarget, AdverseEvent.

## Evidence dimensions

Evidence type, source authority, directness, replication state, methodological quality, recency, graph confidence, and human review state are separate dimensions. No single number represents scientific truth.

## Relationship examples

`has_phenotype`, `associated_with`, `contains_variant`, `affects_protein`, `participates_in`, `targets`, `investigated_in`, `reports`, `studies`, `uses_dataset`, `measures`, `has_biomarker`, `has_adverse_event`, `mentioned_in`, `derived_from`, `same_as`, `possibly_same_as`.

New predicates require documented source semantics before governed ingestion.
