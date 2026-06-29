# TfL Line API Source Audit

## V1 Endpoints

- `GET https://api.tfl.gov.uk/Line/Meta/Severity`
- `GET https://api.tfl.gov.uk/Line/Mode/{modes}`
- `GET https://api.tfl.gov.uk/Line/Mode/{modes}/Status`

## First Ingestion Endpoint

`/Mode/tube/Status` is the first ingestion endpoint because it provides current
passenger-visible disruption state with a compact response shape: line identity,
mode, status severity, optional reason text, timestamps, and validity periods.
That gives the project a useful raw observation grain before adding richer
detail payloads or other modes.

## Parser Grain

The parser emits one row per line-status item per ingestion run. If a line has
multiple `lineStatuses` entries, each status becomes a separate observation. For
V1, the parser stores the first `validityPeriods` entry in the normalized fields
and keeps the original line/status payload in `raw_payload` for audit and replay.

## Known Risks

- `reason` is optional and may be missing or null.
- `validityPeriods` may be empty.
- A line can contain multiple `lineStatuses` entries.
- Detail payloads can add nested disruption data that should be modeled after
  the raw database schema is designed.
