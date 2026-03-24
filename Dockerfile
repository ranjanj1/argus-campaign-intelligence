FROM python:3.9-slim

WORKDIR /app

# Install system deps needed by spaCy and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy dependency files first (layer caching)
COPY pyproject.toml poetry.lock* ./

# Install deps (no dev deps in prod image)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY argus/ ./argus/
COPY settings.yaml ./

CMD ["python", "-m", "argus"]
