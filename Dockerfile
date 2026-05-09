# syntax=docker/dockerfile:1
FROM python:3.14-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p database outputs/logs

# Default transport: stdio (for MCP)
ENV CODECORTEX_TRANSPORT=stdio
ENV CODECORTEX_DB_PATH=/app/database/codecortex.db

# For HTTP mode
ENV CODECORTEX_HOST=0.0.0.0
ENV CODECORTEX_PORT=8001

EXPOSE 8001

# Health check for HTTP mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/status')" || exit 1

ENTRYPOINT ["python", "-m", "src.main"]
