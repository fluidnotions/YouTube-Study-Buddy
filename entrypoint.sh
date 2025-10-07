#!/bin/bash
set -e

echo "Starting Tor..."
tor &
TOR_PID=$!

echo "Waiting for Tor to be ready..."
for i in {1..30}; do
    if curl -x socks5h://127.0.0.1:9050 -s https://check.torproject.org/ > /dev/null 2>&1; then
        echo "Tor is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Tor failed to start"
        exit 1
    fi
    sleep 1
done

echo "Starting Streamlit..."
exec streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
