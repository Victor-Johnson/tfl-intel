
-- basically an ingestion table to enable runs tracking 
CREATE TABLE IF NOT EXISTS raw.pipeline_runs (
    ingestion_run_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_endpoint TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    records_received INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pipeline_runs_status_check
        CHECK (status IN ('started', 'success', 'failed'))
);

-- Storing Valid TFL status severity codes.

CREATE TABLE IF NOT EXISTS raw.tfl_status_severity_codes(
    severity_level INTEGER NOT NULL,
    mode_name TEXT ,
    description TEXT NOT NULL,
    source_endpoint TEXT NOT NULL DEFAULT '/Meta/Severity',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL,

    CONSTRAINT tfl_status_severity_level_check
        CHECK (severity_level >= 0 )
);

-- Storing Line Metadata from /Mode/tube Endpoint 
CREATE TABLE IF NOT EXISTS raw.tfl_lines (
    line_id TEXT PRIMARY KEY,
    line_name TEXT NOT NULL,
    mode_name TEXT,
    created_source_at TIMESTAMPTZ,
    modified_source_at TIMESTAMPTZ,
    source_endpoint TEXT NOT NULL DEFAULT '/Mode/tube',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL
);

--Storing every Observed line status snapshot 
CREATE TABLE IF NOT EXISTS raw.tfl_line_status_observations (
    observation_id TEXT PRIMARY KEY,
    status_fingerprint TEXT NOT NULL,
    ingestion_run_id TEXT NOT NULL REFERENCES raw.pipeline_runs(ingestion_run_id),

    line_id TEXT NOT NULL,
    line_name TEXT NOT NULL,
    mode_name TEXT,

    status_id INTEGER,
    status_severity INTEGER NOT NULL,
    status_description TEXT NOT NULL,
    reason TEXT,

    status_created_at TIMESTAMPTZ,
    status_modified_at TIMESTAMPTZ,

    validity_start TIMESTAMPTZ,
    validity_end TIMESTAMPTZ,
    validity_is_now BOOLEAN,

    observed_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    source_endpoint TEXT NOT NULL DEFAULT '/Mode/tube/Status',
    raw_payload JSONB NOT NULL,

    CONSTRAINT tfl_line_status_severity_check
        CHECK (status_severity >= 0)
);

-- Store Invalid records -> that failed parsing or validation 
CREATE TABLE IF NOT EXISTS raw.invalid_records (
    invalid_record_id TEXT PRIMARY KEY,
    ingestion_run_id TEXT REFERENCES raw.pipeline_runs(ingestion_run_id),
    source_name TEXT NOT NULL,
    source_endpoint TEXT NOT NULL,
    error_message TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



