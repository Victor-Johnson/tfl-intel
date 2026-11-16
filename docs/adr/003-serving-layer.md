# ADR 003: Serving Layer

## Status

Accepted.

## Decision

Use FastAPI as a read-only serving layer over DuckDB analytics tables.

## Reason

The serving layer separates operational ingestion from analytics consumption and
provides clean dashboard-ready JSON without exposing raw Postgres tables
directly.

DuckDB gives the API a compact analytical read model. Postgres remains the raw
source of truth, while DuckDB holds refreshed snapshots and derived tables for
consumer-facing queries.

## Consequences

DuckDB refresh must run before the API serves fresh data.

The API is read-only and does not perform ingestion.

Consumers query stable JSON endpoints instead of raw database tables.
