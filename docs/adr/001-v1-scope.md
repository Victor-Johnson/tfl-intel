# ADR 001: V1 Scope

## Status

Implemented

## Context

TfL Intel needed a credible first vertical slice before adding orchestration,
streaming, object storage, dashboards, forecasting, or AI briefing layers.

## Decision

Use the TfL Line/Status API for Tube, Elizabeth line, DLR, London Overground,
and Tram. Preserve a common raw grain and keep predictive ML outside V1.

Delay Redpanda, MinIO, Dagster, LSTM, Grafana, and AI briefing.

## Reason

This allowed the project to prove source ingestion, raw-data shape and parser
tests before adding Postgres, dbt, Airflow and the bundled dashboard. Those
downstream V1 layers are now implemented; the deliberately delayed streaming,
forecasting and AI briefing layers remain out of scope.
