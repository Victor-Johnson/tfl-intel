FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /data \
    && chown app:app /data

USER app
EXPOSE 8000

CMD ["uvicorn", "tfl_intel.serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
