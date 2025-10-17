#!/usr/bin/env python3
"""
Diagnostic script to test transcript fetching and identify failure points.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from yt_study_buddy.tor_transcript_fetcher import TorTranscriptFetcher
from yt_study_buddy.video_processor import VideoProcessor

def test_tor_connection():
    """Test if Tor proxy is working."""
    print("=" * 60)
    print("1. Testing Tor Connection")
    print("=" * 60)

    fetcher = TorTranscriptFetcher()

    if fetcher.check_tor_connection():
        print("✓ Tor proxy is working!")
        return True
    else:
        print("✗ Tor proxy NOT working")
        return False

def test_video_title(video_id: str):
    """Test fetching video title."""
    print("\n" + "=" * 60)
    print(f"2. Testing Video Title Fetch for {video_id}")
    print("=" * 60)

    processor = VideoProcessor(provider_type='tor')
    title = processor.get_video_title(video_id)

    print(f"Title: {title}")

    if title and not title.startswith("Video_"):
        print("✓ Title fetch successful")
        return True
    else:
        print("✗ Title fetch failed (using fallback)")
        return False

def test_transcript_fetch(video_id: str):
    """Test fetching transcript."""
    print("\n" + "=" * 60)
    print(f"3. Testing Transcript Fetch for {video_id}")
    print("=" * 60)

    fetcher = TorTranscriptFetcher()

    # Try with fallback
    result = fetcher.fetch_with_fallback(video_id)

    if result:
        print(f"✓ Transcript fetched successfully!")
        print(f"  Method: {result.get('method', 'unknown')}")
        print(f"  Length: {result.get('length', 0)} characters")
        print(f"  Duration: {result.get('duration', 'unknown')}")
        return True, result
    else:
        print("✗ Transcript fetch failed (both Tor and yt-dlp)")
        return False, None

def analyze_common_failures():
    """Analyze common failure patterns."""
    print("\n" + "=" * 60)
    print("4. Common Failure Analysis")
    print("=" * 60)

    print("\nChecking processing_log.json...")
    log_path = Path("notes/processing_log.json")

    if not log_path.exists():
        print("✗ processing_log.json doesn't exist yet")
        return

    import json
    try:
        with open(log_path, 'r') as f:
            jobs = json.load(f)

        if not jobs:
            print("✗ No jobs logged yet")
            return

        failed = [j for j in jobs if not j.get('success')]

        print(f"\nTotal jobs: {len(jobs)}")
        print(f"Failed jobs: {len(failed)}")

        if failed:
            print("\nFailure reasons:")
            error_counts = {}
            for job in failed:
                error = job.get('error', 'Unknown error')
                error_type = error.split(':')[0] if ':' in error else error
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

            for error_type, count in sorted(error_counts.items(), key=lambda x: -x[1]):
                print(f"  • {error_type}: {count} occurrences")

            # Show a sample failure
            print(f"\nSample failure details:")
            sample = failed[0]
            print(f"  Video ID: {sample.get('video_id')}")
            print(f"  Error: {sample.get('error')}")
            print(f"  Duration: {sample.get('processing_duration', 0):.1f}s")

    except Exception as e:
        print(f"✗ Error reading log: {e}")

def check_exit_nodes():
    """Check exit node tracker."""
    print("\n" + "=" * 60)
    print("5. Exit Node Tracker Status")
    print("=" * 60)

    log_path = Path("notes/exit_nodes.json")

    if not log_path.exists():
        print("✗ exit_nodes.json doesn't exist yet")
        print("  (This is created on first Tor use)")
        return

    import json
    from datetime import datetime

    try:
        with open(log_path, 'r') as f:
            nodes = json.load(f)

        print(f"Total tracked nodes: {len(nodes)}")

        if not nodes:
            print("  (No nodes tracked yet)")
            return

        now = datetime.now()
        in_cooldown = 0
        available = 0

        for ip, data in nodes.items():
            try:
                last_used = datetime.fromisoformat(data['last_used'])
                elapsed = (now - last_used).total_seconds()

                if elapsed < 3600:
                    in_cooldown += 1
                else:
                    available += 1
            except:
                pass

        print(f"In cooldown: {in_cooldown}")
        print(f"Available: {available}")

        # Show most recently used
        sorted_nodes = sorted(
            nodes.items(),
            key=lambda x: x[1].get('last_used', ''),
            reverse=True
        )

        print(f"\nMost recently used nodes:")
        for ip, data in sorted_nodes[:5]:
            last_used = data.get('last_used', 'N/A')[:19]
            use_count = data.get('use_count', 0)
            print(f"  • {ip}: {use_count} uses, last: {last_used}")

    except Exception as e:
        print(f"✗ Error reading exit nodes: {e}")

def main():
    """Run all diagnostics."""
    print("\n🔍 YouTube Study Buddy - Diagnostic Tool\n")

    # Test with a known working video
    test_video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up

    # Run tests
    tor_ok = test_tor_connection()

    if not tor_ok:
        print("\n⚠️  WARNING: Tor proxy not working!")
        print("   Start Tor with: sudo systemctl start tor")
        print("   Or use Docker: docker-compose up -d")
        return

    title_ok = test_video_title(test_video_id)
    transcript_ok, transcript_data = test_transcript_fetch(test_video_id)

    # Analyze existing failures
    analyze_common_failures()
    check_exit_nodes()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"Tor Connection:     {'✓ OK' if tor_ok else '✗ FAILED'}")
    print(f"Title Fetch:        {'✓ OK' if title_ok else '⚠ DEGRADED'}")
    print(f"Transcript Fetch:   {'✓ OK' if transcript_ok else '✗ FAILED'}")

    if transcript_ok and transcript_data:
        method = transcript_data.get('method', 'unknown')
        if method == 'tor':
            print("\n✓ Everything working with Tor!")
        elif method == 'yt-dlp':
            print("\n⚠ Tor failed, but yt-dlp fallback worked")
        else:
            print(f"\n⚠ Working but method unknown: {method}")
    elif not transcript_ok:
        print("\n✗ CRITICAL: Cannot fetch transcripts!")
        print("   Check:")
        print("   1. Is YouTube accessible?")
        print("   2. Is Tor working? (test manually)")
        print("   3. Try a different video ID")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
