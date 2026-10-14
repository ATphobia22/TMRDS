-- Durable ledger for explicitly authorized IBM Quantum research jobs.
-- Never store API keys, bearer tokens, raw circuits, or clinical payloads here.
CREATE TABLE IF NOT EXISTS quantum_job_submissions (
    submission_id UUID PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    input_sha256 CHAR(64) NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
    artifact_uri TEXT NOT NULL,
    backend TEXT NOT NULL,
    shots INTEGER CHECK (shots IS NULL OR shots BETWEEN 1 AND 10000000),
    api_version TEXT NOT NULL,
    region TEXT NOT NULL CHECK (region IN ('us', 'eu-de')),
    state TEXT NOT NULL CHECK (state IN (
        'PREPARED', 'SUBMITTING', 'SUBMITTED', 'SUBMISSION_UNKNOWN',
        'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
    )),
    ibm_job_id TEXT UNIQUE,
    result_sha256 CHAR(64) CHECK (result_sha256 IS NULL OR result_sha256 ~ '^[0-9a-f]{64}$'),
    error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    submitted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_quantum_jobs_state_created
    ON quantum_job_submissions(state, created_at);
CREATE INDEX IF NOT EXISTS idx_quantum_jobs_backend_created
    ON quantum_job_submissions(backend, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quantum_jobs_ibm_job_id
    ON quantum_job_submissions(ibm_job_id) WHERE ibm_job_id IS NOT NULL;
