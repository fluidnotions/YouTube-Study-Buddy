#!/usr/bin/env python3
"""Simple test - just 2 videos to verify circuit rotation or delays work."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from yt_study_buddy.video_processor import VideoProcessor

test_urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley
    "https://www.youtube.com/watch?v=9bZkp7q19f0",  # Gangnam Style
]

print("Testing 2 videos in sequence...")
print("=" * 80)

processor = VideoProcessor(provider_type="tor", tor_host="127.0.0.1", tor_port=9050)

for i, url in enumerate(test_urls, 1):
    print(f"\n[Video {i}/2] {url}")
    print("-" * 80)

    try:
        video_id = processor.get_video_id(url)
        print(f"✓ Video ID: {video_id}")

        transcript_data = processor.get_transcript(video_id)
        print(f"✓ Transcript: {transcript_data['length']} characters")

        title = processor.get_video_title(video_id)
        print(f"✓ Title: {title[:60]}...")

        print(f"✅ Video {i} SUCCESS!")

    except Exception as e:
        print(f"❌ Video {i} FAILED: {e}")
        break

print("\n" + "=" * 80)
print("Test complete!")
