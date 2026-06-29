# V1 Architecture

```text
TfL Line/Status API
  ↓
Python ingestion job
  ↓
Postgres raw tables
  ↓
dbt models later
  ↓
Metabase dashboard later

Review sample
  ↓
Theme tagging
  ↓
Review theme mart later
  ↓
Evidence gap dashboard later
```

The first vertical slice keeps implementation deliberately small. The current
code fetches and parses TfL status data, while Postgres, dbt, and Metabase are
documented as the next layers rather than built prematurely.
