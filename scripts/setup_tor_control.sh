#!/bin/bash
# Setup Tor control port for circuit rotation
# This enables YouTube Study Buddy to rotate Tor circuits and avoid IP blocks

set -e

echo "=========================================="
echo "Tor Control Port Setup"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Enable Tor control port (9051)"
echo "  2. Enable cookie authentication"
echo "  3. Add current user to debian-tor group"
echo "  4. Restart Tor service"
echo ""
echo "You will be prompted for your sudo password."
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Check if Tor is installed
if ! command -v tor &> /dev/null; then
    echo "❌ Error: Tor is not installed"
    echo "Install with: sudo apt-get install tor"
    exit 1
fi

echo ""
echo "📝 Backing up current Tor configuration..."
sudo cp /etc/tor/torrc /etc/tor/torrc.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backup created"

echo ""
echo "🔧 Configuring Tor control port..."

# Check if ControlPort is already configured
if grep -q "^ControlPort 9051" /etc/tor/torrc 2>/dev/null; then
    echo "✓ ControlPort already configured"
else
    # Add ControlPort configuration
    echo "" | sudo tee -a /etc/tor/torrc > /dev/null
    echo "# Added by YouTube Study Buddy setup script" | sudo tee -a /etc/tor/torrc > /dev/null
    echo "ControlPort 9051" | sudo tee -a /etc/tor/torrc > /dev/null
    echo "✓ Added ControlPort 9051"
fi

# Check if CookieAuthentication is already configured
if grep -q "^CookieAuthentication 1" /etc/tor/torrc 2>/dev/null; then
    echo "✓ CookieAuthentication already configured"
else
    echo "CookieAuthentication 1" | sudo tee -a /etc/tor/torrc > /dev/null
    echo "✓ Added CookieAuthentication 1"
fi

echo ""
echo "👥 Adding user '$USER' to debian-tor group..."
sudo usermod -a -G debian-tor $USER
echo "✓ User added to debian-tor group"

echo ""
echo "🔄 Restarting Tor service..."
sudo systemctl restart tor

# Wait for Tor to start
echo "⏳ Waiting for Tor to initialize..."
sleep 3

# Check if Tor is running
if sudo systemctl is-active --quiet tor; then
    echo "✓ Tor service is running"
else
    echo "❌ Error: Tor service failed to start"
    echo "Check logs with: sudo journalctl -u tor -n 50"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "⚠️  IMPORTANT: You need to log out and log back in"
echo "    (or restart your terminal) for group changes"
echo "    to take effect."
echo ""
echo "    Alternatively, run: newgrp debian-tor"
echo ""
echo "📋 Configuration summary:"
echo "  • Tor control port: 9051"
echo "  • Authentication: Cookie-based"
echo "  • User group: debian-tor"
echo "  • Backup location: /etc/tor/torrc.backup.*"
echo ""
echo "🧪 Test with: uv run python test_transcript.py"
echo ""
