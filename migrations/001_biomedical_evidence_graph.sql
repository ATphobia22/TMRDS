CREATE TABLE IF NOT EXISTS evidence_sources (
    source_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    endpoint TEXT,
    protocol TEXT NOT NULL,
    authority_class TEXT NOT NULL,
    license TEXT NOT NULL,
    access_policy TEXT NOT NULL,
    allowed_use TEXT NOT NULL,
    update_frequency TEXT,
    version_strategy TEXT,
    schema_version TEXT,
    identifier_namespaces JSONB NOT NULL DEFAULT '[]'::jsonb,
    entity_types JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence_observations (
    observation_id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES evidence_sources(source_id),
    source_record_id TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    source_version TEXT,
    request_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_payload_hash CHAR(64) NOT NULL,
    adapter_version TEXT NOT NULL,
    normalization_version TEXT NOT NULL,
    UNIQUE(source_id, source_record_id, raw_payload_hash)
);

CREATE TABLE IF NOT EXISTS canonical_entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    label TEXT NOT NULL,
    normalized_label TEXT NOT NULL,
    synonyms JSONB NOT NULL DEFAULT '[]'::jsonb,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_identifiers (
    entity_id TEXT NOT NULL REFERENCES canonical_entities(entity_id) ON DELETE CASCADE,
    namespace TEXT NOT NULL,
    identifier TEXT NOT NULL,
    PRIMARY KEY(entity_id, namespace, identifier),
    UNIQUE(namespace, identifier)
);

CREATE TABLE IF NOT EXISTS entity_sources (
    entity_id TEXT NOT NULL REFERENCES canonical_entities(entity_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES evidence_sources(source_id),
    PRIMARY KEY(entity_id, source_id)
);

CREATE TABLE IF NOT EXISTS evidence_assertions (
    assertion_id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL REFERENCES canonical_entities(entity_id),
    predicate TEXT NOT NULL,
    object_entity_id TEXT NOT NULL REFERENCES canonical_entities(entity_id),
    source_id TEXT NOT NULL REFERENCES evidence_sources(source_id),
    source_record_id TEXT NOT NULL,
    source_uri TEXT,
    published_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL,
    source_version TEXT,
    adapter_version TEXT NOT NULL,
    normalization_version TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    evidence_grade TEXT NOT NULL,
    directness TEXT NOT NULL,
    replication_state TEXT NOT NULL,
    effect_direction TEXT,
    effect_measure DOUBLE PRECISION,
    effect_units TEXT,
    population_context TEXT,
    methodology TEXT,
    content_hash CHAR(64) NOT NULL UNIQUE,
    supersedes_assertion_id TEXT REFERENCES evidence_assertions(assertion_id),
    conflict_group_id TEXT,
    human_review_state TEXT NOT NULL DEFAULT 'unreviewed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_assertion_source_record
    ON evidence_assertions(source_id, source_record_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_assertion_subject ON evidence_assertions(subject_entity_id);
CREATE INDEX IF NOT EXISTS idx_assertion_object ON evidence_assertions(object_entity_id);
CREATE INDEX IF NOT EXISTS idx_assertion_predicate ON evidence_assertions(predicate);
CREATE INDEX IF NOT EXISTS idx_assertion_source ON evidence_assertions(source_id);
CREATE INDEX IF NOT EXISTS idx_assertion_published ON evidence_assertions(published_at);

CREATE TABLE IF NOT EXISTS evidence_assessments (
    assessment_id BIGSERIAL PRIMARY KEY,
    assertion_id TEXT NOT NULL REFERENCES evidence_assertions(assertion_id) ON DELETE CASCADE,
    source_authority TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    directness TEXT NOT NULL,
    replication_state TEXT NOT NULL,
    methodological_quality TEXT,
    recency_class TEXT,
    graph_confidence DOUBLE PRECISION CHECK (graph_confidence IS NULL OR (graph_confidence >= 0 AND graph_confidence <= 1)),
    reviewer_id TEXT,
    assessed_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS conflict_groups (
    conflict_group_id TEXT PRIMARY KEY,
    conflict_type TEXT NOT NULL,
    affected_entity_ids JSONB NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    comparison_basis TEXT NOT NULL,
    state TEXT NOT NULL,
    resolution_provenance TEXT
);

CREATE TABLE IF NOT EXISTS conflict_members (
    conflict_group_id TEXT NOT NULL REFERENCES conflict_groups(conflict_group_id) ON DELETE CASCADE,
    assertion_id TEXT NOT NULL REFERENCES evidence_assertions(assertion_id) ON DELETE CASCADE,
    PRIMARY KEY(conflict_group_id, assertion_id)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    ingestion_run_id UUID PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES evidence_sources(source_id),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    records_seen BIGINT NOT NULL DEFAULT 0,
    records_ingested BIGINT NOT NULL DEFAULT 0,
    records_deduplicated BIGINT NOT NULL DEFAULT 0,
    entities_resolved BIGINT NOT NULL DEFAULT 0,
    assertions_created BIGINT NOT NULL DEFAULT 0,
    conflicts_detected BIGINT NOT NULL DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS graph_projections (
    assertion_id TEXT PRIMARY KEY REFERENCES evidence_assertions(assertion_id) ON DELETE CASCADE,
    backend TEXT NOT NULL,
    projected_at TIMESTAMPTZ NOT NULL,
    projection_version TEXT NOT NULL
);
