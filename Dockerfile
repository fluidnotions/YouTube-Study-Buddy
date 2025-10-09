# Start with Python slim (Debian-based, has tor in repos)
FROM python:3.13-slim

WORKDIR /app

# Install Tor and other dependencies
# Using Debian packages for Tor (more up-to-date than dperson/torproxy's Alpine)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    tor \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy application files
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/
COPY streamlit_app.py .
COPY main.py .
COPY entrypoint-python-tor.sh .

# Install Python dependencies
ENV UV_HTTP_TIMEOUT=300
RUN uv pip install --system --no-cache \
    torch --index-url https://download.pytorch.org/whl/cpu
RUN uv pip install --system --no-cache -e .

# Create notes directory
RUN mkdir -p /app/notes

# Set up Tor directories and permissions
RUN mkdir -p /var/lib/tor && \
    chown -R debian-tor:debian-tor /var/lib/tor && \
    chmod 700 /var/lib/tor

# Configure Tor (based on dperson/torproxy setup + our circuit rotation needs)
RUN echo "# YouTube Study Buddy Tor Configuration" > /etc/tor/torrc && \
    echo "# Based on dperson/torproxy setup" >> /etc/tor/torrc && \
    echo "" >> /etc/tor/torrc && \
    echo "# SOCKS proxy" >> /etc/tor/torrc && \
    echo "SOCKSPort 0.0.0.0:9050" >> /etc/tor/torrc && \
    echo "" >> /etc/tor/torrc && \
    echo "# Control port for circuit rotation" >> /etc/tor/torrc && \
    echo "ControlPort 0.0.0.0:9051" >> /etc/tor/torrc && \
    echo "CookieAuthentication 1" >> /etc/tor/torrc && \
    echo "CookieAuthFileGroupReadable 1" >> /etc/tor/torrc && \
    echo "" >> /etc/tor/torrc && \
    echo "# Exit policy (allow all)" >> /etc/tor/torrc && \
    echo "ExitPolicy accept *:*" >> /etc/tor/torrc && \
    echo "" >> /etc/tor/torrc && \
    echo "# Performance tuning" >> /etc/tor/torrc && \
    echo "NumEntryGuards 8" >> /etc/tor/torrc && \
    echo "NumDirectoryGuards 3" >> /etc/tor/torrc && \
    echo "" >> /etc/tor/torrc && \
    echo "# Logging" >> /etc/tor/torrc && \
    echo "Log notice stdout" >> /etc/tor/torrc

# Make entrypoint executable
RUN chmod +x /app/entrypoint-python-tor.sh

# Expose ports
EXPOSE 8501 9050 9051

# Environment variables
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    TOR_HOST=127.0.0.1 \
    TOR_PORT=9050

# Health check for both Tor and Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && \
        curl -x socks5h://127.0.0.1:9050 -s https://check.torproject.org/ > /dev/null || exit 1

CMD ["/app/entrypoint-python-tor.sh"]
