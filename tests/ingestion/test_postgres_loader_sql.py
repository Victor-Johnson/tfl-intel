from tfl_intel.ingestion.loaders import postgres_loader


def test_postgres_loader_exports_required_functions() -> None:
    required_functions = [
        "get_connection",
        "start_pipeline_run",
        "mark_pipeline_success",
        "mark_pipeline_failed",
        "insert_line_status_observations",
        "insert_status_severity_codes",
        "insert_lines",
    ]

    for function_name in required_functions:
        assert callable(getattr(postgres_loader, function_name))
