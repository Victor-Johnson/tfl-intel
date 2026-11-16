# TfL Line/Status API Source Audit

## Endpoint

`https://api.tfl.gov.uk/Line/Mode/{mode}/Status`, where `{mode}` is one of
`tube`, `elizabeth-line`, `dlr`, `overground`, or `tram`.

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

Airflow polls each configured mode every five minutes. Every mode receives its
own pipeline-run identifier, so partial source failures remain diagnosable and
successful retries remain idempotent.

## Risks

The API response can include optional or missing fields, empty validity periods,
and multiple validity periods for one status item.

## V1 Ingestion Decision

Parse required line identity fields, tolerate optional status details, use the
first validity period only for now, and retain raw payload context for replay.
