# TfL Intel

Transport for London (TfL) can tell you how a line is running now. But if you
travel at the same time each week, you might also want to know what has
happened on that line before.
TfL Intel keeps a history of line-status checks so you can see current status
alongside patterns from the times you usually travel.

It covers the Tube, Elizabeth line, DLR, London Overground, and Tram. The
project checks status every five minutes and shows **collection coverage**
beside its historical measures. A missed check is a gap in the evidence, not
proof that service was good.

## Questions it answers

- Is my line disrupted now, and how recent is that observation?
- At the weekday and hour I usually travel, how often was disruption observed?
- Were recent disruptions brief observations or longer sampled episodes?
- Is there enough collected history to compare two lines fairly?

This is historical context, not a route planner or a prediction. Check TfL's
live journey planner before travelling. Planned closures currently count as
disruptions in the historical figures, and a five-minute poll can miss shorter
events.

## Where it stands

The ingestion, models, API, and dashboard have passed local and CI checks. A
private Metabase dashboard has been tested with synthetic fixture data. The
public deployment is still being prepared, so the planned website is not yet
a live demo. Real collected history has gaps; charts show coverage so those
gaps remain visible.

## How it works

Status checks are stored in Postgres. Airflow rebuilds and tests historical
views with DuckDB and dbt, and FastAPI serves the dashboard. Validated views
can also be explored in Metabase. The API reads a published snapshot rather
than the ingestion database.

For the metric definitions, trade-offs, and evidence, see the
[case study](PORTFOLIO.md). The [runbook](docs/runbook.md) covers setup and
troubleshooting, and [deployment notes](DEPLOYMENT.md) cover the VPS.

## Run locally

Install Docker with Compose and Buildx, and [uv](https://docs.astral.sh/uv/).
Complete the [first-time setup](docs/runbook.md#first-time-setup), including
private passwords, before running:

```bash
make postgres-up
make postgres-init
make ingest-reference-data
make ingest-line-status
make duckdb-refresh
make stack-up
```

Open `http://localhost:8000/dashboard`. Run `make check` for the Python and
dbt checks. The runbook explains scheduled polling with Airflow and optional
Metabase setup.

Data provided by [Transport for London](https://tfl.gov.uk/info-for/open-data-users/).
TfL Intel is an independent, unofficial project and is not endorsed by TfL.
