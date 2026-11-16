# Metabase trip-planning dashboard

Metabase is a trip-history view alongside the custom dashboard. It connects
to tested DuckDB marts copied into Postgres `analytics`. Its reader cannot
access `raw`, `staging`, or `ml`. Do not expose an instance with example
credentials or publish a dashboard before checking its data quality.

## What a traveler can ask

The provisioned dashboard has seven cards: collection freshness, a line ID
list, the selected line's current sampled status, weekday/hour disruption
patterns, a 90-complete-day uptime/coverage trend, a seven-day comparison of
lines with at least 90% coverage, and recent observed episodes. Use the **Line
ID** filter (for example, `central`) to change the four line-specific cards.

The weekday/hour table reports observed and expected five-minute samples,
disrupted samples, observed disruption share, and coverage quality. Zero
observations produce a null disruption share, not a claim of Good Service.
This is historical context for a trip, **not** a route planner, forecast, or
guarantee about future service. TfL Go remains the source for live journey
planning and alternatives.

## Production setup

Replace all example passwords, start the stack, and publish validated marts:

```bash
make metabase-up
make publish-bi
```

Create the Metabase admin account at the private Metabase URL and create an
admin API key. Then provision the private dashboard:

```bash
METABASE_URL=http://127.0.0.1:3000 METABASE_API_KEY=YOUR_KEY \
  METABASE_READER_PASSWORD_FILE=secrets/metabase_reader_password.txt \
  make provision-metabase
```

The command creates a PostgreSQL connection named `TfL Intel Analytics`, a
`Trip planning insights` collection, seven saved questions, and one dashboard.
It reuses that dashboard on repeat runs. The connection uses
`metabase_reader` on `postgres:5432/tfl_intel`. The role is read-only,
limited to `analytics`, and has a 15-second statement timeout. Keep the API
key in an environment secret, not a committed file or shared shell history.
The provisioner never enables public sharing.

Before public sharing, log in as a viewer, check a selected line against TfL,
confirm the seven cards and line filter, and verify no `raw` table is visible.
Only then consider publishing this dashboard in Metabase Admin settings.
Metabase public links are accessible without login; keep administration
authenticated. After reviewing the dashboard, set `BI_DASHBOARD_URL` in `.env`
to its exact vetted HTTPS dashboard URL (not the Metabase root), keep
`BI_DASHBOARD_DEMO=false`, and recreate the API container. Until then, the
custom dashboard does not show a BI link.

## Local verified demo

An isolated local instance was created at `http://127.0.0.1:3001/dashboard/1`
with **synthetic dbt fixture data** in `tfl_metabase_check`. It is private and
not a live TfL product. Sign in as `admin@localhost.invalid` with the password
in the ignored `secrets/metabase_local_admin_password.txt` file. Its separate
app and reader passwords are also ignored; the existing secret files were
not changed. Seven card queries and the Bakerloo line filter passed through
the Metabase API. The local Compose override is
`docker-compose.metabase-local.yml`.
To link the local API dashboard to this demo, set
`BI_DASHBOARD_URL=http://127.0.0.1:3001/dashboard/1` and
`BI_DASHBOARD_DEMO=true` in the ignored `.env`, then recreate the API
container. The link says **fixture data** so it cannot be mistaken for the
API's live TfL history.

## Data lifecycle

All traveler history questions read at most the last 90 days; the trend and
weekday/hour pattern exclude the partial current local day. The daily backup
job verifies a full operational-Postgres restore into a disposable database
before pruning operational raw observations, invalid records, and unreferenced
run rows older than 90 days. The next DuckDB rebuild removes them from marts.
Backups can retain older data until their own rotation; the off-host backup
policy must be set separately. A test restore on the same host is not disaster
recovery proof.

## Analyst questions

The six earlier SQL files remain in this directory for a separate analyst
workspace. They are not installed by the traveler dashboard provisioner.
If that audience emerges, curate them as a second dashboard with explicit
time windows and coverage labels.

## Refresh behavior

The Airflow status DAG republishes all eleven allowlisted marts after dbt and
runtime validation succeed. Publication replaces the Postgres BI tables in
one transaction, so Metabase readers see either the preceding complete
version or the new complete version. DuckDB remains the FastAPI serving
store and source of analytical truth. The freshness question shows the
latest ingestion run included in the BI snapshot, not a separate BI
publication timestamp.
