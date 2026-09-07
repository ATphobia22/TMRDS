-- TMRDS real-world real-time data fabric.
-- Raw observations are append-only; current source state is mutable operational metadata.

CREATE TABLE IF NOT EXISTS data_fabric_sources (
    source_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    format TEXT NOT NULL CHECK (format IN ('json', 'geojson')),
    authority_class TEXT NOT NULL,
    update_frequency TEXT NOT NULL,
    requires_api_key BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    default_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_fabric_source_state (
    source_id TEXT PRIMARY KEY REFERENCES data_fabric_sources(source_id) ON DELETE CASCADE,
    etag TEXT,
    last_modified TEXT,
    last_success_at TIMESTAMPTZ,
    last_error TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_fabric_observations (
    observation_id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES data_fabric_sources(source_id),
    record_id TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    payload_hash CHAR(64) NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
    source_version TEXT,
    source_uri TEXT,
    etag TEXT,
    last_modified TEXT,
    provenance_status TEXT NOT NULL DEFAULT 'source-retrieved',
    fabric_version TEXT NOT NULL,
    UNIQUE (source_id, record_id, payload_hash)
);

CREATE INDEX IF NOT EXISTS idx_data_fabric_observations_source_time
    ON data_fabric_observations (source_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_fabric_observations_hash
    ON data_fabric_observations (payload_hash);
CREATE INDEX IF NOT EXISTS idx_data_fabric_observations_retrieved
    ON data_fabric_observations (retrieved_at DESC);
