#!/bin/bash
# Test Tor access within debian-tor group context

echo "Testing Tor circuit rotation with group permissions..."
echo ""

# Run the test within the debian-tor group context
sg debian-tor -c "cd /home/justin/Documents/dev/python/PycharmProjects/ytstudybuddy && uv run python -c '
from src.yt_study_buddy.tor_transcript_fetcher import TorTranscriptFetcher
import sys

fetcher = TorTranscriptFetcher()
print(\"✓ TorTranscriptFetcher initialized\")

# Test circuit rotation
success = fetcher.rotate_tor_circuit()
if success:
    print(\"✅ Circuit rotation successful!\")
    sys.exit(0)
else:
    print(\"❌ Circuit rotation failed\")
    sys.exit(1)
'"
