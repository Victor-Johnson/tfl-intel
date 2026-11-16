# ADR 002: Publish validated marts to Postgres for Metabase

## Status

Accepted

## Context

The product dashboard needs predictable, low-latency reads, while reviewers
and analysts benefit from drill-down, ad hoc questions, and reusable BI cards.
Metabase has a native PostgreSQL connector. DuckDB connectivity requires a
community driver, and a persistent external JDBC pool would contend with the
separate process that refreshes the analytical file.

## Decision

Keep DuckDB as the analytical build and FastAPI serving store. After dbt and
runtime validation pass, publish a fixed allowlist of marts into the existing
Postgres `analytics` schema in one transaction. Connect Metabase through a
dedicated role with read-only transactions, a short statement timeout, and no
access to operational schemas.

Store Metabase's application state in a separate Postgres container and back
it up alongside the operational database. Keep the custom dashboard as the
primary public experience; publish only one curated Metabase dashboard as the
secondary exploration surface.

## Consequences

- Metabase uses an officially supported connector and cannot lock DuckDB.
- BI readers see complete publication versions rather than partially loaded
  tables.
- Raw payloads and pipeline write credentials remain outside Metabase.
- The small mart dataset is duplicated, adding a controlled publication step.
- Dashboard definitions live in the backed-up Metabase application database;
  canonical question SQL also remains versioned in `docs/metabase`.
