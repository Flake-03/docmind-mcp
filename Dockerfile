FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
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
RUN chmod +x src/clients/git_askpass.sh

ENV PYTHONPATH=/app

CMD ["python", "-m", "src.server"]
