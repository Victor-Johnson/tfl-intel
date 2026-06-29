# TfL Line/Status API Source Audit

## Endpoint

`https://api.tfl.gov.uk/Line/Mode/tube,dlr,overground,elizabeth-line/Status`

## Method

`GET`

## Authentication

TfL `app_id` and `app_key` query parameters are optional in local development
and should be loaded from environment variables when used.

## Response Shape

The API returns a list of line objects. Each line may contain a `lineStatuses`
array with one or more status records.

## Expected Grain

One raw parsed observation per line status item.

## Important Fields

- `id`
- `name`
- `lineStatuses.statusSeverity`
- `lineStatuses.statusSeverityDescription`
- `lineStatuses.reason`
- `lineStatuses.validityPeriods`

## Polling Strategy

V1 should be manually runnable. A future scheduler can poll at a small fixed
interval once raw Postgres tables and idempotency checks are designed.

## Risks

The API response can include optional or missing fields, empty validity periods,
and multiple validity periods for one status item.

## V1 Ingestion Decision

Parse required line identity fields, tolerate optional status details, use the
first validity period only for now, and retain raw payload context for replay.
