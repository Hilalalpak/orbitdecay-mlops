-- Pipeline metadata schema
-- Tables: pipeline_runs, dataset_metadata, run_history
-- Run this once on a fresh database before starting the pipeline.

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id UUID PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    execution_mode TEXT,
    target_date TEXT,
    parameters JSONB,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS dataset_metadata (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id     UUID NOT NULL REFERENCES pipeline_runs(run_id),
    phase_id            TEXT NOT NULL,          -- pipeline phase identifier (e.g. 'phase1', 'phase3')
    output_data_type    TEXT NOT NULL,          -- 'orbital_collection', 'feature_set', 'model'
    artifact_name       TEXT NOT NULL,
    version             TEXT,
    base_path           TEXT,
    manifest_files      TEXT[],
    record_count        INTEGER,
    status              TEXT,
    execution_mode      TEXT,
    decision_reason     TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS run_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phase TEXT,
    param_hash TEXT,
    source_id TEXT,
    filter_params JSONB,
    manifest_files TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    extra_metadata JSONB
);