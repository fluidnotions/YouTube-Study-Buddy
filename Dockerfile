FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    tor \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/
COPY streamlit_app.py .
COPY main.py .
COPY entrypoint.sh .

ENV UV_HTTP_TIMEOUT=300
RUN uv pip install --system --no-cache \
    torch --index-url https://download.pytorch.org/whl/cpu
RUN uv pip install --system --no-cache -e .

RUN mkdir -p /app/notes

RUN mkdir -p /var/lib/tor && \
    chown -R debian-tor:debian-tor /var/lib/tor && \
    chmod 700 /var/lib/tor

RUN chmod +x /app/entrypoint.sh

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    TOR_HOST=127.0.0.1 \
    TOR_PORT=9050

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && \
        curl -x socks5h://127.0.0.1:9050 -s https://check.torproject.org/ > /dev/null || exit 1

CMD ["/app/entrypoint.sh"]
