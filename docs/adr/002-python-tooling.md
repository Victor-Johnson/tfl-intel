# ADR 002: Python Tooling

## Status

Accepted

## Decision

Use `uv`, `pyproject.toml`, `uv.lock`, and a `src/` layout.

## Reason

This gives the project reproducible installs, fast local workflows, modern
Python packaging conventions, and clean separation between source code and
tests.
