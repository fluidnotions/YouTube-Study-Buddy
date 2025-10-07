#!/usr/bin/env python3
"""
Test to check if playlist URLs are causing the "no element found" XML error.
Your URLs have ?list= parameters which might confuse the transcript API.
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from yt_study_buddy.video_processor import VideoProcessor
    print("✓ Libraries imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)


def test_playlist_url_issue():
    """Test if playlist URLs are causing the issue"""
    print("Testing playlist URL issue...")
    print("=" * 50)

    # Your actual failing URL
    playlist_url = "https://youtu.be/8w7mv0zjdUg?list=PL4MBLJ9EJIVaMPEU6_FSGdQlorDfU-7VM"

    # Clean version without playlist
    clean_url = "https://youtu.be/8w7mv0zjdUg"

    processor = VideoProcessor()

    print(f"Original URL: {playlist_url}")
    print(f"Clean URL:    {clean_url}")

    # Test video ID extraction
    print("\n--- Video ID Extraction ---")
    playlist_id = processor.get_video_id(playlist_url)
    clean_id = processor.get_video_id(clean_url)

    print(f"From playlist URL: '{playlist_id}'")
    print(f"From clean URL:    '{clean_id}'")

    if playlist_id != clean_id:
        print("⚠ WARNING: Different video IDs extracted!")
    else:
        print("✓ Same video ID extracted from both URLs")

    # Test transcript fetching with both
    print("\n--- Transcript Fetching ---")

    # Test with playlist URL video ID
    print(f"Testing with playlist-extracted ID: {playlist_id}")
    try:
        result = YouTubeTranscriptApi.get_transcript(playlist_id)
        print(f"✓ SUCCESS: Got {len(result)} segments")
    except Exception as e:
        print(f"✗ FAILED: {e}")

    # Test with clean URL video ID
    print(f"\nTesting with clean-extracted ID: {clean_id}")
    try:
        result = YouTubeTranscriptApi.get_transcript(clean_id)
        print(f"✓ SUCCESS: Got {len(result)} segments")
    except Exception as e:
        print(f"✗ FAILED: {e}")

    # Test direct video ID (manual)
    direct_id = "8w7mv0zjdUg"
    print(f"\nTesting with manual video ID: {direct_id}")
    try:
        result = YouTubeTranscriptApi.get_transcript(direct_id)
        print(f"✓ SUCCESS: Got {len(result)} segments")
    except Exception as e:
        print(f"✗ FAILED: {e}")


def test_video_processor_with_playlist():
    """Test if our VideoProcessor handles playlist URLs correctly"""
    print("\n" + "=" * 50)
    print("Testing VideoProcessor with playlist URLs...")

    processor = VideoProcessor()
    playlist_url = "https://youtu.be/8w7mv0zjdUg?list=PL4MBLJ9EJIVaMPEU6_FSGdQlorDfU-7VM"

    try:
        print(f"Testing URL: {playlist_url}")

        # Extract video ID
        video_id = processor.get_video_id(playlist_url)
        print(f"Extracted video ID: '{video_id}'")

        # Check if ID looks correct (11 characters, alphanumeric)
        if len(video_id) == 11 and video_id.replace('-', '').replace('_', '').isalnum():
            print("✓ Video ID format looks correct")
        else:
            print(f"⚠ Video ID format looks suspicious: '{video_id}'")

        # Try to get transcript
        transcript_data = processor.get_transcript(video_id)
        print(f"✓ SUCCESS: VideoProcessor got transcript with {transcript_data['length']} characters")

    except Exception as e:
        print(f"✗ FAILED: {e}")


def test_url_cleaning():
    """Test different URL formats and cleaning"""
    print("\n" + "=" * 50)
    print("Testing URL cleaning...")

    test_urls = [
        "https://youtu.be/8w7mv0zjdUg?list=PL4MBLJ9EJIVaMPEU6_FSGdQlorDfU-7VM",  # Your format
        "https://youtu.be/8w7mv0zjdUg",  # Clean short
        "https://www.youtube.com/watch?v=8w7mv0zjdUg",  # Standard format
        "https://www.youtube.com/watch?v=8w7mv0zjdUg&list=PL4MBLJ9EJIVaMPEU6_FSGdQlorDfU-7VM",  # Standard with playlist
        "8w7mv0zjdUg",  # Just ID
    ]

    processor = VideoProcessor()

    for url in test_urls:
        video_id = processor.get_video_id(url)
        print(f"'{url}' -> '{video_id}'")


def create_clean_urls_file():
    """Create a version of urls.txt without playlist parameters"""
    print("\n" + "=" * 50)
    print("Creating clean URLs file...")

    # Read the original urls.txt
    urls_file = os.path.join(os.path.dirname(__file__), '..', 'urls.txt')
    clean_urls_file = os.path.join(os.path.dirname(__file__), 'urls_clean.txt')

    if not os.path.exists(urls_file):
        print(f"✗ Original urls.txt not found at {urls_file}")
        return

    try:
        with open(urls_file, 'r') as f:
            urls = f.readlines()

        processor = VideoProcessor()
        clean_urls = []

        print(f"Processing {len(urls)} URLs...")

        for url in urls:
            url = url.strip()
            if not url or url.startswith('#'):
                clean_urls.append(url)  # Keep comments and empty lines
                continue

            # Extract video ID and create clean URL
            video_id = processor.get_video_id(url)
            if video_id:
                clean_url = f"https://youtu.be/{video_id}"
                clean_urls.append(clean_url)
                print(f"  {url[:50]}... -> {clean_url}")
            else:
                print(f"  ⚠ Could not extract ID from: {url}")
                clean_urls.append(url)  # Keep original if extraction fails

        # Write clean URLs
        with open(clean_urls_file, 'w') as f:
            f.write('\n'.join(clean_urls))

        print(f"✓ Clean URLs written to: {clean_urls_file}")
        print(f"  You can test with: python main.py --batch --file {os.path.basename(clean_urls_file)}")

    except Exception as e:
        print(f"✗ Failed to create clean URLs file: {e}")


def main():
    """Run playlist URL tests"""
    print("Playlist URL Diagnostic Test")
    print("=" * 60)

    test_playlist_url_issue()
    test_video_processor_with_playlist()
    test_url_cleaning()
    create_clean_urls_file()

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print("1. Try testing with the generated urls_clean.txt file")
    print("2. If clean URLs work, the issue is playlist parameters")
    print("3. Consider updating VideoProcessor to strip playlist params")
    print("4. Test individual videos manually in YouTube to confirm they have captions")


if __name__ == "__main__":
    main()