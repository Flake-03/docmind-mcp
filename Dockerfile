FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates git \
    && pip install --no-cache-dir poetry==2.2.1 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN poetry install --only main --no-root
COPY src/ ./src/
RUN chmod 0555 /app/src/project_docs_mcp/clients/git_askpass.sh \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/git \
    && chown -R appuser:appuser /data

ENV PYTHONPATH=/app/src

USER appuser
CMD ["python", "-m", "project_docs_mcp.server"]
