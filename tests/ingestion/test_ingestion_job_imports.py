def test_ingestion_jobs_import_without_side_effects() -> None:
    import tfl_intel.ingestion.jobs.ingest_line_api_stage as line_api_stage
    import tfl_intel.ingestion.jobs.ingest_line_status as line_status
    import tfl_intel.ingestion.jobs.ingest_lines_by_mode as lines_by_mode
    import tfl_intel.ingestion.jobs.ingest_severity_codes as severity_codes

    assert callable(line_api_stage.main)
    assert callable(line_status.main)
    assert callable(lines_by_mode.main)
    assert callable(severity_codes.main)
