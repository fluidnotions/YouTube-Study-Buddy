# Tor Setup for Circuit Rotation

## The Problem

When processing multiple YouTube videos, YouTube may block your IP after the first request. To work around this, the application needs to rotate Tor circuits (get new exit IPs) between requests.

## Quick Fix

Run these commands:

```bash
# Add configuration to Tor
echo "ControlPort 9051" | sudo tee -a /etc/tor/torrc
echo "CookieAuthentication 1" | sudo tee -a /etc/tor/torrc
echo "CookieAuthFileGroupReadable 1" | sudo tee -a /etc/tor/torrc

# Add your user to debian-tor group
sudo usermod -a -G debian-tor $USER

# Restart Tor
sudo systemctl restart tor

# Log out and log back in (or run this in your current terminal)
newgrp debian-tor
```

## Verify It's Working

```bash
# Check you're in the debian-tor group
groups | grep debian-tor

# Check the auth cookie is readable
ls -la /run/tor/control.authcookie

# Test transcript fetching
uv run python test_simple.py
```

## What Each Setting Does

- **ControlPort 9051**: Enables the Tor control port for circuit management
- **CookieAuthentication 1**: Uses a cookie file for authentication instead of a password
- **CookieAuthFileGroupReadable 1**: Allows members of debian-tor group to read the auth cookie

## Docker

The Dockerfile already includes these settings, so containers work out of the box.

## Troubleshooting

**"Permission denied" errors**:
- Make sure you logged out and back in after adding yourself to debian-tor group
- Check `groups` command shows debian-tor
- Check `/run/tor/control.authcookie` permissions with `ls -la`

**"Connection refused" errors**:
- Check Tor is running: `sudo systemctl status tor`
- Check the control port is configured: `grep ControlPort /etc/tor/torrc`

**YouTube still blocking**:
- Wait 5-10 minutes for previous blocks to expire
- Restart Tor to get a fresh exit IP: `sudo systemctl restart tor`
- Check your current Tor IP: `curl --socks5 127.0.0.1:9050 https://api.ipify.org`
