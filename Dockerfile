# YouTube Study Buddy - Streamlit Application with Tor
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Tor
RUN apt-get update && apt-get install -y \
    git \
    curl \
    tor \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY streamlit_app.py .
COPY main.py .

# Install Python dependencies using UV
RUN uv pip install --system --no-cache -e .

# Create default output directory (no spaces for cleaner paths)
RUN mkdir -p /app/notes

# Configure Tor
RUN mkdir -p /var/lib/tor && \
    chown -R debian-tor:debian-tor /var/lib/tor && \
    chmod 700 /var/lib/tor

# Expose Streamlit port
EXPOSE 8501

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Set environment variables for Tor connection (localhost since Tor runs in same container)
ENV TOR_HOST=127.0.0.1
ENV TOR_PORT=9050

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Start Tor in background\n\
echo "Starting Tor..."\n\
tor &\n\
TOR_PID=$!\n\
\n\
# Wait for Tor to be ready\n\
echo "Waiting for Tor to be ready..."\n\
for i in {1..30}; do\n\
    if curl -x socks5h://127.0.0.1:9050 -s https://check.torproject.org/ > /dev/null 2>&1; then\n\
        echo "Tor is ready!"\n\
        break\n\
    fi\n\
    if [ $i -eq 30 ]; then\n\
        echo "Tor failed to start"\n\
        exit 1\n\
    fi\n\
    sleep 1\n\
done\n\
\n\
# Start Streamlit\n\
echo "Starting Streamlit..."\n\
exec streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && \
        curl -x socks5h://127.0.0.1:9050 -s https://check.torproject.org/ > /dev/null || exit 1

# Run startup script
CMD ["/app/entrypoint.sh"]
