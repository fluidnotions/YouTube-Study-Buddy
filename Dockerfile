FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    tor \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
COPY src/ ./src/
COPY streamlit_app.py .
COPY main.py .

RUN uv pip install --system --no-cache -e .

RUN mkdir -p /app/notes

RUN mkdir -p /var/lib/tor && \
    chown -R debian-tor:debian-tor /var/lib/tor && \
    chmod 700 /var/lib/tor

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV TOR_HOST=127.0.0.1
ENV TOR_PORT=9050

RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting Tor..."\n\
tor &\n\
TOR_PID=$!\n\
\n\
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
echo "Starting Streamlit..."\n\
exec streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && \
        curl -x socks5h://127.0.0.1:9050 -s https://check.torproject.org/ > /dev/null || exit 1

CMD ["/app/entrypoint.sh"]
