#!/usr/bin/env python3
"""
Simple focused test to diagnose the transcript issue.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from youtube_transcript_api import YouTubeTranscriptApi
from src.video_processor import VideoProcessor

def test_exact_failing_video():
    """Test the exact video that's failing"""
    print("Testing your exact failing video...")

    # Your exact failing URL
    failing_url = "https://youtu.be/8w7mv0zjdUg?list=PL4MBLJ9EJIVaMPEU6_FSGdQlorDfU-7VM"

    processor = VideoProcessor()

    # Extract video ID
    video_id = processor.get_video_id(failing_url)
    print(f"Extracted video ID: {video_id}")

    # Test 1: Direct API call with extracted ID
    print("\n--- Test 1: Direct youtube-transcript-api call ---")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        print(f"✓ SUCCESS: Got {len(transcript)} segments")
        print(f"First segment: {transcript[0]}")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        print(f"Error type: {type(e).__name__}")

    # Test 2: Try different languages
    print("\n--- Test 2: Try different languages ---")
    try:
        # Try any available language
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'auto'])
        print(f"✓ SUCCESS: Got {len(transcript)} segments")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")

    # Test 3: Check what transcripts are available
    print("\n--- Test 3: Check available transcripts ---")
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print("Available transcripts:")
        for transcript in transcript_list:
            print(f"  - {transcript.language_code}: {transcript.language}")

        # Try to get the first available one
        for transcript in transcript_list:
            try:
                data = transcript.fetch()
                print(f"✓ SUCCESS with {transcript.language_code}: Got {len(data)} segments")
                return True
            except Exception as e:
                print(f"✗ Failed {transcript.language_code}: {e}")

    except Exception as e:
        print(f"✗ Could not list transcripts: {e}")

    return False

def test_known_working_video():
    """Test with a video that definitely works"""
    print("\n" + "="*50)
    print("Testing known working video...")

    # Rick Roll - definitely has transcripts and is very popular
    test_video_id = "dQw4w9WgXcQ"

    try:
        transcript = YouTubeTranscriptApi.get_transcript(test_video_id)
        print(f"✓ Known working video SUCCESS: Got {len(transcript)} segments")
        print(f"First segment: {transcript[0]['text'][:50]}...")
        return True
    except Exception as e:
        print(f"✗ Even known working video failed: {e}")
        return False

def test_clean_url():
    """Test with clean URL (no playlist)"""
    print("\n" + "="*50)
    print("Testing clean URL (no playlist parameter)...")

    # Your video without playlist
    clean_video_id = "8w7mv0zjdUg"

    try:
        transcript = YouTubeTranscriptApi.get_transcript(clean_video_id)
        print(f"✓ Clean URL SUCCESS: Got {len(transcript)} segments")
        return True
    except Exception as e:
        print(f"✗ Clean URL failed: {e}")
        return False

def main():
    print("Simple Transcript Diagnostic")
    print("=" * 40)

    # Test the exact failing case
    exact_works = test_exact_failing_video()

    # Test known working video
    known_works = test_known_working_video()

    # Test clean URL
    clean_works = test_clean_url()

    # Summary
    print("\n" + "="*40)
    print("SUMMARY")
    print("="*40)

    if known_works and not exact_works:
        print("✓ Library works with some videos")
        print("✗ Your specific video has issues")
        print("\nLikely causes:")
        print("1. Video doesn't have transcripts")
        print("2. Video is private/restricted")
        print("3. Video is too old/new")
    elif not known_works:
        print("✗ Library not working at all")
        print("Possible network/library issues")
    else:
        print("✓ Everything seems to work!")
        print("The issue might be elsewhere")

if __name__ == "__main__":
    main()