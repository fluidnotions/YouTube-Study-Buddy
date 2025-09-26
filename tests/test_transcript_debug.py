#!/usr/bin/env python3
"""
Test script to debug YouTube transcript API issues.
This will help identify why all videos are failing with "no element found: line 1, column 0"
"""
import sys
import os
import time
import requests
from pathlib import Path

# Add src to path so we can import our classes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    print("✓ youtube-transcript-api imported successfully")
except ImportError as e:
    print(f"✗ Failed to import youtube-transcript-api: {e}")
    sys.exit(1)

try:
    from yt_study_buddy.video_processor import VideoProcessor
    print("✓ VideoProcessor imported successfully")
except ImportError as e:
    print(f"✗ Failed to import VideoProcessor: {e}")
    sys.exit(1)


def test_direct_api_call():
    """Test the youtube-transcript-api directly with a known working video"""
    print("\n" + "="*50)
    print("TEST 1: Direct YouTube Transcript API Call")
    print("="*50)

    # Use a known video with transcripts (TED talk)
    test_video_id = "8w7mv0zjdUg"  # First video from your failing list

    try:
        print(f"Testing video ID: {test_video_id}")

        # Try to get available transcript languages first
        print("Getting available transcript languages...")
        transcript_list = YouTubeTranscriptApi.list_transcripts(test_video_id)

        available_languages = []
        for transcript in transcript_list:
            available_languages.append(transcript.language_code)

        print(f"Available languages: {available_languages}")

        # Try to get English transcript
        print("Attempting to get English transcript...")
        transcript = YouTubeTranscriptApi.get_transcript(test_video_id, languages=['en'])

        print(f"✓ SUCCESS: Got {len(transcript)} transcript segments")
        print(f"First segment: {transcript[0] if transcript else 'None'}")
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        print(f"Error type: {type(e).__name__}")

        # Try to get more details about the error
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text[:200]}...")

        return False


def test_video_processor_class():
    """Test our VideoProcessor class"""
    print("\n" + "="*50)
    print("TEST 2: VideoProcessor Class")
    print("="*50)

    processor = VideoProcessor()
    test_url = "https://youtu.be/8w7mv0zjdUg"

    try:
        # Test video ID extraction
        video_id = processor.get_video_id(test_url)
        print(f"✓ Video ID extracted: {video_id}")

        # Test transcript fetching
        print("Testing transcript fetch...")
        result = processor.get_transcript(video_id)
        print(f"✓ SUCCESS: Got transcript with {result['length']} characters")
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_rate_limiting():
    """Test if rate limiting is causing issues"""
    print("\n" + "="*50)
    print("TEST 3: Rate Limiting Test")
    print("="*50)

    test_videos = [
        "8w7mv0zjdUg",  # From your failing list
        "dQw4w9WgXcQ",  # Rick Roll (known to have transcripts)
        "JGwWNGJdvx8"   # Popular tech talk
    ]

    success_count = 0

    for i, video_id in enumerate(test_videos):
        try:
            print(f"Testing video {i+1}/3: {video_id}")

            # Add delay between requests
            if i > 0:
                print("  Adding 2-second delay...")
                time.sleep(2)

            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            print(f"  ✓ SUCCESS: Got {len(transcript)} segments")
            success_count += 1

        except Exception as e:
            print(f"  ✗ FAILED: {e}")

    print(f"\nRate limiting test: {success_count}/{len(test_videos)} successful")
    return success_count > 0


def test_network_connectivity():
    """Test basic network connectivity to YouTube"""
    print("\n" + "="*50)
    print("TEST 4: Network Connectivity")
    print("="*50)

    try:
        # Test basic connectivity to YouTube
        response = requests.get("https://www.youtube.com", timeout=10)
        print(f"✓ YouTube.com accessible (status: {response.status_code})")

        # Test specific video page
        test_video_url = "https://www.youtube.com/watch?v=8w7mv0zjdUg"
        response = requests.get(test_video_url, timeout=10)
        print(f"✓ Test video page accessible (status: {response.status_code})")

        return True

    except Exception as e:
        print(f"✗ Network connectivity failed: {e}")
        return False


def test_library_version():
    """Check library versions"""
    print("\n" + "="*50)
    print("TEST 5: Library Versions")
    print("="*50)

    try:
        import youtube_transcript_api
        print(f"youtube-transcript-api version: {youtube_transcript_api.__version__}")

        import requests
        print(f"requests version: {requests.__version__}")

        # Check if there are known issues with this version
        from packaging import version
        current_version = version.parse(youtube_transcript_api.__version__)

        # Known working version
        known_good = version.parse("0.6.0")

        if current_version < known_good:
            print(f"⚠ WARNING: Your version ({current_version}) is older than recommended ({known_good})")
            print("  Consider upgrading: pip install --upgrade youtube-transcript-api")
        else:
            print("✓ Library version looks good")

    except ImportError as e:
        print(f"✗ Could not check versions: {e}")


def main():
    """Run all diagnostic tests"""
    print("YouTube Transcript API Diagnostic Tool")
    print("=" * 60)

    test_results = []

    # Run all tests
    test_results.append(("Network Connectivity", test_network_connectivity()))
    test_results.append(("Library Versions", test_library_version()))
    test_results.append(("Direct API Call", test_direct_api_call()))
    test_results.append(("VideoProcessor Class", test_video_processor_class()))
    test_results.append(("Rate Limiting", test_rate_limiting()))

    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)

    for test_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:<25} {status}")

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == 0:
        print("\n⚠ RECOMMENDATIONS:")
        print("1. Check your internet connection")
        print("2. Update youtube-transcript-api: pip install --upgrade youtube-transcript-api")
        print("3. Try running from a different network/location")
        print("4. Check if your IP is being rate-limited by YouTube")
    elif passed < total:
        print("\n⚠ Some tests failed. Check the specific errors above.")
    else:
        print("\n✓ All tests passed! The issue might be elsewhere.")


if __name__ == "__main__":
    main()