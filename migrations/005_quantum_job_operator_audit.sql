-- Append-only operator evidence for resolving ambiguous remote submissions.
-- Never use this table to justify re-submission; it records a confirmed remote job ID.
CREATE TABLE IF NOT EXISTS quantum_job_operator_resolutions (
    resolution_id UUID PRIMARY KEY,
    submission_id UUID NOT NULL REFERENCES quantum_job_submissions(submission_id),
    ibm_job_id TEXT NOT NULL UNIQUE,
    operator_id TEXT NOT NULL CHECK (length(operator_id) BETWEEN 1 AND 128),
    evidence_reference TEXT NOT NULL CHECK (length(evidence_reference) BETWEEN 1 AND 2048),
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_quantum_job_operator_resolutions_submission
    ON quantum_job_operator_resolutions(submission_id, resolved_at DESC);
