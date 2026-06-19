# Backend image. Note (CLAUDE.md): during Kubernetes development the backend runs on
# the host via `uv run`; this image is the packaging target, not the dev loop.
FROM python:3.12-slim

# Install uv (project + dependency manager).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev || uv sync --no-dev

# Copy application code.
COPY app ./app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
