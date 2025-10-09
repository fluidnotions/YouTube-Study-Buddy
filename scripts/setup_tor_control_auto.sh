#!/bin/bash
# Setup Tor control port for circuit rotation (non-interactive)
set -e

echo "Setting up Tor control port..."

# Backup current config
sudo cp /etc/tor/torrc /etc/tor/torrc.backup.$(date +%Y%m%d_%H%M%S)

# Add ControlPort if not already present
if ! grep -q "^ControlPort 9051" /etc/tor/torrc 2>/dev/null; then
    echo "" | sudo tee -a /etc/tor/torrc > /dev/null
    echo "# Added by YouTube Study Buddy" | sudo tee -a /etc/tor/torrc > /dev/null
    echo "ControlPort 9051" | sudo tee -a /etc/tor/torrc > /dev/null
fi

# Add CookieAuthentication if not already present
if ! grep -q "^CookieAuthentication 1" /etc/tor/torrc 2>/dev/null; then
    echo "CookieAuthentication 1" | sudo tee -a /etc/tor/torrc > /dev/null
fi

# Add CookieAuthFileGroupReadable if not already present
if ! grep -q "^CookieAuthFileGroupReadable 1" /etc/tor/torrc 2>/dev/null; then
    echo "CookieAuthFileGroupReadable 1" | sudo tee -a /etc/tor/torrc > /dev/null
fi

# Add user to debian-tor group
sudo usermod -a -G debian-tor $USER

# Restart Tor
sudo systemctl restart tor

sleep 3

echo "✅ Tor control port setup complete!"
echo "Run: newgrp debian-tor"
