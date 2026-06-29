# ADR 001: V1 Scope

## Status

Accepted

## Context

TfL Intel needs a credible first vertical slice before adding orchestration,
streaming, object storage, dashboards, forecasting, or AI briefing layers.

## Decision

Start with TfL Line/Status API ingestion and a lightweight review theme mapping
scaffold.

Delay Redpanda, MinIO, Dagster, LSTM, Grafana, and AI briefing.

## Reason

This proves the vertical slice first: source API, Python ingestion, raw data
shape, parser tests, and a clear path to Postgres, dbt, and Metabase.
