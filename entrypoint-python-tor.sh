#!/bin/bash
set -e

echo "=========================================="
echo "YouTube Study Buddy with Tor"
echo "=========================================="

# Start Tor in background as debian-tor user
echo "Starting Tor..."
# Change ownership of Tor directories
chown -R debian-tor:debian-tor /var/lib/tor /var/run/tor 2>/dev/null || true
# Start Tor as debian-tor user (using su since sudo not installed in slim)
su -s /bin/bash debian-tor -c "tor -f /etc/tor/torrc" &
TOR_PID=$!
echo "Tor started with PID: $TOR_PID"

# Wait for Tor to be ready
echo "Waiting for Tor to be ready..."
for i in {1..30}; do
    if curl -x socks5h://127.0.0.1:9050 -s --max-time 5 https://check.torproject.org/ > /dev/null 2>&1; then
        echo "✓ Tor is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Tor failed to start within 30 seconds"
        echo "Tor logs:"
        tail -20 /var/log/tor/log 2>/dev/null || echo "No logs available"
        exit 1
    fi
    sleep 1
done

# Test Tor connection and show exit IP
echo ""
echo "Testing Tor connection..."
TOR_IP=$(curl -x socks5h://127.0.0.1:9050 -s https://api.ipify.org 2>/dev/null || echo "unknown")
REAL_IP=$(curl -s https://api.ipify.org 2>/dev/null || echo "unknown")
echo "Real IP:     $REAL_IP"
echo "Tor exit IP: $TOR_IP"

if [ "$TOR_IP" = "$REAL_IP" ]; then
    echo "⚠ WARNING: Tor may not be working! Exit IP same as real IP"
else
    echo "✓ Tor is working correctly (different IPs)"
fi

# Test circuit rotation capability
echo ""
echo "Testing circuit rotation..."
if echo "AUTHENTICATE" | nc -w 2 127.0.0.1 9051 > /dev/null 2>&1; then
    echo "✓ Tor control port accessible for circuit rotation"
else
    echo "⚠ Tor control port not accessible (circuit rotation may not work)"
fi

echo ""
echo "=========================================="
echo "Starting YouTube Study Buddy..."
echo "=========================================="
echo ""

# Start Streamlit
exec streamlit run /app/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
