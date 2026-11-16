# Portfolio publishing package

This directory contains content prepared for `victorjohnson.dev`:

- `project.json` matches the public `/api/projects/{id}` content shape.
- `building-a-coverage-aware-tfl-platform.md` is ready for the Markdown-backed
  blog editor.
- `assets/` contains the dashboard preview, architecture, dbt lineage, and
  social card.

When the portfolio source repository is available, upload the assets through
its existing media workflow, replace the asset URLs in `project.json` if that
workflow changes them, then create the project and post through the current
content model. Keep the article body as Markdown; do not paste rendered HTML.

Suggested article metadata:

```json
{
  "title": "Building a Coverage-Aware Reliability Platform for the London Underground",
  "category": "Data Engineering",
  "excerpt": "How I turned short-lived transport status updates into an idempotent, tested and deployable analytics platform without mistaking missing data for good service.",
  "date": "2026-09-11",
  "url": ""
}
```

The generated social card was created with OpenAI's built-in image generation
tool from an independent data-platform brief. It intentionally contains no TfL
roundel or official branding.
