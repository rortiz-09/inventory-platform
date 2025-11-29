# Server Governance Platform - Production Dockerfile
# Base: uv with Python 3.12 on Debian Bookworm Slim

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

# Copy all files first (hatchling needs README.md)
COPY . .

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# Create data directory for DuckDB persistence
RUN mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run command
CMD ["uv", "run", "streamlit", "run", "src/main.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"]
