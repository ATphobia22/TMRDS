-- TMRDS governed AI, retrieval, FHIR/OMOP research backbone.
-- Safe to apply after 001_biomedical_evidence_graph.sql.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ai_models (
    model_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    provider TEXT NOT NULL,
    purpose TEXT NOT NULL,
    governance_status TEXT NOT NULL DEFAULT 'active',
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at TIMESTAMPTZ,
    PRIMARY KEY (model_id, model_version)
);

CREATE TABLE IF NOT EXISTS ai_prompts (
    prompt_id TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    purpose TEXT NOT NULL,
    content_hash CHAR(64) NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (prompt_id, prompt_version),
    UNIQUE (content_hash)
);

CREATE TABLE IF NOT EXISTS ai_datasets (
    dataset_id TEXT PRIMARY KEY,
    dataset_version TEXT,
    provenance_uri TEXT,
    content_hash CHAR(64),
    access_policy TEXT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_evaluations (
    evaluation_id UUID PRIMARY KEY,
    model_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    evaluation_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    dataset_id TEXT REFERENCES ai_datasets(dataset_id),
    evaluated_at TIMESTAMPTZ NOT NULL,
    evaluator_version TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (model_id, model_version) REFERENCES ai_models(model_id, model_version)
);

CREATE TABLE IF NOT EXISTS ai_generations (
    generation_id UUID PRIMARY KEY,
    model_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    prompt_id TEXT,
    prompt_version TEXT,
    retrieved_at TIMESTAMPTZ NOT NULL,
    uncertainty DOUBLE PRECISION CHECK (uncertainty IS NULL OR uncertainty BETWEEN 0 AND 1),
    governance_status TEXT NOT NULL,
    human_authority_final BOOLEAN NOT NULL DEFAULT TRUE,
    research_advisory BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (model_id, model_version) REFERENCES ai_models(model_id, model_version),
    FOREIGN KEY (prompt_id, prompt_version) REFERENCES ai_prompts(prompt_id, prompt_version)
);

CREATE TABLE IF NOT EXISTS ai_generation_evidence (
    generation_id UUID NOT NULL REFERENCES ai_generations(generation_id) ON DELETE CASCADE,
    assertion_id TEXT NOT NULL REFERENCES evidence_assertions(assertion_id),
    PRIMARY KEY (generation_id, assertion_id)
);

CREATE TABLE IF NOT EXISTS ai_generation_datasets (
    generation_id UUID NOT NULL REFERENCES ai_generations(generation_id) ON DELETE CASCADE,
    dataset_id TEXT NOT NULL REFERENCES ai_datasets(dataset_id),
    PRIMARY KEY (generation_id, dataset_id)
);

CREATE TABLE IF NOT EXISTS evidence_embeddings (
    assertion_id TEXT PRIMARY KEY REFERENCES evidence_assertions(assertion_id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_version TEXT NOT NULL,
    embedded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_hnsw
    ON evidence_embeddings USING hnsw (embedding vector_cosine_ops);

-- Minimal OMOP CDM v5.4-aligned research tables. Patient-level linkage is deliberately
-- separated from public evidence tables and must be populated only through an authorized
-- research governance pathway.
CREATE SCHEMA IF NOT EXISTS omop;

CREATE TABLE IF NOT EXISTS omop.person (
    person_id BIGINT PRIMARY KEY,
    gender_concept_id INTEGER NOT NULL,
    year_of_birth INTEGER NOT NULL,
    month_of_birth INTEGER,
    day_of_birth INTEGER,
    birth_datetime TIMESTAMPTZ,
    race_concept_id INTEGER NOT NULL,
    ethnicity_concept_id INTEGER NOT NULL,
    location_id BIGINT,
    provider_id BIGINT,
    care_site_id BIGINT,
    person_source_value TEXT,
    gender_source_value TEXT,
    race_source_value TEXT,
    ethnicity_source_value TEXT
);

CREATE TABLE IF NOT EXISTS omop.observation_period (
    observation_period_id BIGINT PRIMARY KEY,
    person_id BIGINT NOT NULL REFERENCES omop.person(person_id),
    observation_period_start_date DATE NOT NULL,
    observation_period_end_date DATE NOT NULL,
    period_type_concept_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS omop.condition_occurrence (
    condition_occurrence_id BIGINT PRIMARY KEY,
    person_id BIGINT NOT NULL REFERENCES omop.person(person_id),
    condition_concept_id INTEGER NOT NULL,
    condition_start_date DATE NOT NULL,
    condition_end_date DATE,
    condition_type_concept_id INTEGER NOT NULL,
    condition_source_value TEXT
);

CREATE TABLE IF NOT EXISTS omop.drug_exposure (
    drug_exposure_id BIGINT PRIMARY KEY,
    person_id BIGINT NOT NULL REFERENCES omop.person(person_id),
    drug_concept_id INTEGER NOT NULL,
    drug_exposure_start_date DATE NOT NULL,
    drug_exposure_end_date DATE,
    drug_type_concept_id INTEGER NOT NULL,
    drug_source_value TEXT
);

CREATE TABLE IF NOT EXISTS omop.measurement (
    measurement_id BIGINT PRIMARY KEY,
    person_id BIGINT NOT NULL REFERENCES omop.person(person_id),
    measurement_concept_id INTEGER NOT NULL,
    measurement_date DATE NOT NULL,
    measurement_type_concept_id INTEGER NOT NULL,
    value_as_number DOUBLE PRECISION,
    unit_concept_id INTEGER,
    measurement_source_value TEXT
);

CREATE TABLE IF NOT EXISTS fhir_resource_observations (
    observation_id BIGSERIAL PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    fhir_version TEXT NOT NULL DEFAULT '4.0.1',
    profile_uri TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_hash CHAR(64) NOT NULL,
    resource JSONB NOT NULL,
    UNIQUE(resource_type, resource_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_fhir_resource_type_id
    ON fhir_resource_observations(resource_type, resource_id);

CREATE INDEX IF NOT EXISTS idx_fhir_resource_json
    ON fhir_resource_observations USING gin(resource);
