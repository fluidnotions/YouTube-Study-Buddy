#!/bin/bash
# Fix Tor permissions and restart to get a new IP

echo "Step 1: Fixing Tor control permissions..."
echo "==========================================="
bash setup_tor_control_auto.sh

echo ""
echo "Step 2: Getting a fresh Tor IP..."
echo "==========================================="
echo "Restarting Tor to get a new exit node..."
sudo systemctl restart tor
sleep 5

echo ""
echo "Step 3: Testing transcript fetching..."
echo "==========================================="
newgrp debian-tor <<EOF
uv run python test_simple.py
EOF

echo ""
echo "Done!"
