FROM apache/airflow:2.10.5-python3.11

USER root
RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/tfl-intel /opt/tfl-venv \
    && chown -R airflow:root /opt/tfl-intel /opt/tfl-venv

USER airflow
RUN pip install --no-cache-dir uv \
    && uv python install 3.13

ENV UV_PROJECT_ENVIRONMENT=/opt/tfl-venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /opt/tfl-intel
COPY --chown=airflow:root pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=airflow:root src ./src
RUN uv sync --frozen --no-dev

WORKDIR /opt/airflow
