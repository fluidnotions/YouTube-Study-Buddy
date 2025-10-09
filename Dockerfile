# YouTube Study Buddy - App only (connects to external Tor proxy)
FROM python:3.13-slim

# Metadata
LABEL org.opencontainers.image.title="YouTube Study Buddy"
LABEL org.opencontainers.image.description="Transform YouTube videos into AI-powered study notes with Obsidian links"
LABEL org.opencontainers.image.authors="fluidnotions"
LABEL org.opencontainers.image.source="https://github.com/fluidnotions/YouTube-Study-Buddy"
LABEL org.opencontainers.image.version="latest"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/
COPY streamlit_app.py .
COPY main.py .

# Install Python dependencies using UV
ENV UV_HTTP_TIMEOUT=300
RUN uv pip install --system --no-cache \
    torch --index-url https://download.pytorch.org/whl/cpu
RUN uv pip install --system --no-cache -e .

# Create notes directory
RUN mkdir -p /app/notes

# Expose Streamlit port
EXPOSE 8501

# Environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Default Tor proxy settings (override in docker-compose)
ENV TOR_HOST=tor-proxy \
    TOR_PORT=9050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit app
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
