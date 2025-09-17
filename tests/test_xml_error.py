#!/usr/bin/env python3
"""
Focused test to diagnose the specific "no element found: line 1, column 0" XML error.
This error usually means the YouTube API is returning empty/invalid content.
"""
import sys
import os
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    print("✓ youtube-transcript-api imported successfully")
except ImportError as e:
    print(f"✗ Failed to import youtube-transcript-api: {e}")
    sys.exit(1)


def test_xml_parsing_issue():
    """Test specifically for the XML parsing error"""
    print("Testing XML parsing error with your exact video IDs...")

    # Use the exact video IDs from your error log
    failing_video_ids = [
        "8w7mv0zjdUg",  # First failing video
        "86zXDhlrGmo",  # Second failing video
        "d8bS3VBGE5k"   # Third failing video
    ]

    for video_id in failing_video_ids:
        print(f"\n--- Testing video ID: {video_id} ---")

        try:
            # Try to get the transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            print(f"✓ SUCCESS: Got transcript with {len(transcript)} segments")

        except TranscriptsDisabled:
            print("✗ Transcripts are disabled for this video")

        except NoTranscriptFound:
            print("✗ No transcript found for this video")

        except ParseError as e:
            print(f"✗ XML PARSING ERROR: {e}")
            print("  This is the 'no element found' error you're seeing")
            print("  This usually means YouTube returned empty/invalid content")

            # Try to get more info about what was actually returned
            try:
                # This is a bit hacky, but let's try to see what the raw response looks like
                print("  Attempting to diagnose the raw response...")

                # Try different approaches to get more error details
                import requests

                # Try to manually hit the YouTube API endpoint (this may not work directly)
                test_url = f"https://www.youtube.com/watch?v={video_id}"
                response = requests.get(test_url, timeout=10)
                print(f"  Video page status: {response.status_code}")

                if response.status_code != 200:
                    print(f"  ⚠ Video page returned {response.status_code} - video may not exist")

            except Exception as nested_e:
                print(f"  Could not diagnose further: {nested_e}")

        except Exception as e:
            print(f"✗ UNEXPECTED ERROR: {e}")
            print(f"  Error type: {type(e).__name__}")


def test_simple_known_working_video():
    """Test with a video that definitely has transcripts"""
    print("\n" + "="*50)
    print("Testing with known working video...")

    # TED talks usually have good transcripts
    known_working_videos = [
        "dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up (very popular)
        "fJ9rUzIMcZQ",  # TED talk
        "ZXsQAXx_ao0"   # Another popular video
    ]

    for video_id in known_working_videos:
        print(f"\n--- Testing known working video: {video_id} ---")
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            print(f"✓ SUCCESS: Got {len(transcript)} segments")
            print(f"  First segment: {transcript[0]['text'][:50]}...")
            return True  # If we get one working, that's good
        except Exception as e:
            print(f"✗ FAILED: {e}")

    return False


def test_transcript_availability():
    """Check if transcripts are available before trying to fetch"""
    print("\n" + "="*50)
    print("Checking transcript availability...")

    test_video_id = "8w7mv0zjdUg"  # Your first failing video

    try:
        # List available transcripts first
        transcript_list = YouTubeTranscriptApi.list_transcripts(test_video_id)

        print(f"Available transcripts for {test_video_id}:")
        for transcript in transcript_list:
            print(f"  - {transcript.language_code}: {transcript.language}")

        # Try to get one of the available transcripts
        for transcript in transcript_list:
            try:
                print(f"\nTrying to fetch {transcript.language_code} transcript...")
                data = transcript.fetch()
                print(f"✓ SUCCESS: Got {len(data)} segments")
                return True
            except Exception as e:
                print(f"✗ Failed to fetch {transcript.language_code}: {e}")

    except Exception as e:
        print(f"✗ Could not list transcripts: {e}")
        return False

    return False


def main():
    """Run the focused XML error tests"""
    print("XML Parsing Error Diagnostic")
    print("=" * 50)

    # Test 1: Check if the issue is with your specific videos
    print("TEST 1: Your specific failing videos")
    test_xml_parsing_issue()

    # Test 2: Try known working videos
    print("\nTEST 2: Known working videos")
    working = test_simple_known_working_video()

    # Test 3: Check transcript availability
    print("\nTEST 3: Transcript availability check")
    available = test_transcript_availability()

    # Summary and recommendations
    print("\n" + "="*50)
    print("DIAGNOSIS SUMMARY")
    print("="*50)

    if working:
        print("✓ The youtube-transcript-api library works with some videos")
        print("✗ Your specific videos are causing XML parsing errors")
        print("\nLIKELY CAUSES:")
        print("1. Your videos might not have transcripts enabled")
        print("2. The videos might be restricted/private")
        print("3. The playlist URLs might be confusing the API")
        print("\nRECOMMENDATIONS:")
        print("1. Try removing '?list=...' from your URLs")
        print("2. Check if the videos actually have captions when viewed manually")
        print("3. Add error handling to skip videos without transcripts")
    else:
        print("✗ The youtube-transcript-api library is not working at all")
        print("\nLIKELY CAUSES:")
        print("1. Library version issues")
        print("2. Network/firewall blocking")
        print("3. YouTube API changes")
        print("\nRECOMMENDATIONS:")
        print("1. Update the library: pip install --upgrade youtube-transcript-api")
        print("2. Check your internet connection")
        print("3. Try from a different network")


if __name__ == "__main__":
    main()