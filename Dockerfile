FROM python:3.12-slim

# System deps for skia-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install deps (CPU-only torch to save ~1.5GB)
RUN uv sync --frozen --no-dev && \
    .venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet

# Copy application code and assets
COPY server.py ./
COPY runeform/ ./runeform/
COPY fonts/ ./fonts/

# Create runtime directories
RUN mkdir -p output uploads brand_data models

EXPOSE 8002

# Railway sets PORT; default to 8002 for local docker use
CMD uv run uvicorn server:app --host 0.0.0.0 --port ${PORT:-8002}
