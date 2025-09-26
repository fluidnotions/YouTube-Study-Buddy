#!/usr/bin/env python3
"""
Quick test script to verify both transcript providers work.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from yt_study_buddy.video_processor import VideoProcessor


def test_provider(provider_type: str, video_url: str):
    """Test a specific provider with a video URL."""
    print(f"\n{'='*60}")
    print(f"Testing {provider_type.upper()} provider")
    print(f"{'='*60}")

    try:
        # Create processor with specified provider
        processor = VideoProcessor(provider_type=provider_type)

        # Extract video ID
        video_id = processor.get_video_id(video_url)
        print(f"Video ID: {video_id}")

        if not video_id:
            print("❌ Failed to extract video ID")
            return False

        # Test title extraction
        print("Getting video title...")
        title = processor.get_video_title(video_id)
        print(f"Title: {title}")

        # Test transcript extraction
        print("Getting transcript...")
        transcript_data = processor.get_transcript(video_id)

        print(f"✅ SUCCESS!")
        print(f"Transcript length: {transcript_data['length']} characters")
        if transcript_data['duration']:
            print(f"Duration: {transcript_data['duration']}")

        # Show first 200 characters of transcript
        preview = transcript_data['transcript'][:200]
        print(f"Preview: {preview}...")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Test both providers with a sample video."""
    print("Transcript Provider Test")
    print("="*60)

    # Use a popular video that likely has transcripts
    test_video = "https://youtu.be/dQw4w9WgXcQ"  # Rick Roll - very popular, definitely has captions

    print(f"Test video: {test_video}")

    # Test API provider
    api_success = test_provider("api", test_video)

    # Test scraper provider
    scraper_success = test_provider("scraper", test_video)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"API Provider:     {'✅ Working' if api_success else '❌ Failed'}")
    print(f"Scraper Provider: {'✅ Working' if scraper_success else '❌ Failed'}")

    if api_success and scraper_success:
        print("\n🎉 Both providers are working! You can use either method.")
        print("Use --method scraper if you encounter rate limiting with the API.")
    elif scraper_success and not api_success:
        print("\n⚠️ Only scraper provider is working.")
        print("Use --method scraper for all operations.")
    elif api_success and not scraper_success:
        print("\n⚠️ Only API provider is working.")
        print("Stick with default API method, but expect potential rate limiting.")
    else:
        print("\n❌ Both providers failed!")
        print("Check your internet connection and dependencies.")

    print(f"\nTo use with your tool:")
    print(f"  python main.py --method api <url>      # Use YouTube Transcript API")
    print(f"  python main.py --method scraper <url>  # Use web scraping")


if __name__ == "__main__":
    main()