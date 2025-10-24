"""
Error message classifier and simplifier for YouTube transcript fetching.

Converts verbose error messages into concise, actionable summaries.
"""
import re
from typing import Optional
from loguru import logger


class ErrorClassifier:
    """
    Classify and simplify YouTube transcript API errors.

    Takes verbose error messages and returns concise, actionable summaries.
    """

    # Error patterns and their simplified messages
    PATTERNS = [
        # IP blocks and rate limits
        (
            r"blocking requests from your IP|IP has been blocked|rate limit",
            "YouTube blocked exit IP (rate limit or datacenter IP)"
        ),
        (
            r"Too many requests",
            "Rate limit exceeded"
        ),
        (
            r"cloud provider|AWS|Google Cloud|Azure",
            "Exit IP from blocked cloud provider"
        ),

        # Transcript availability
        (
            r"Could not retrieve a transcript.*Subtitles are disabled",
            "Video has no subtitles/transcripts"
        ),
        (
            r"No transcripts? were found|transcript.*not available",
            "No transcripts available for this video"
        ),
        (
            r"No subtitles found for requested languages",
            "No English transcript (check other languages)"
        ),

        # Authentication/Access
        (
            r"Video unavailable|This video is unavailable",
            "Video unavailable (deleted, private, or region-locked)"
        ),
        (
            r"private video|Private video",
            "Video is private"
        ),
        (
            r"members-only|Members-only",
            "Members-only content"
        ),

        # Network/Connection
        (
            r"Connection.*timed out|Timeout|timeout",
            "Connection timeout"
        ),
        (
            r"Connection.*refused|Connection.*reset",
            "Connection refused by YouTube"
        ),
        (
            r"Failed to establish.*connection",
            "Network connection failed"
        ),

        # API/Format issues
        (
            r"Unable to extract|Could not extract",
            "Failed to extract transcript data"
        ),
        (
            r"Invalid.*video.*ID|video ID.*invalid",
            "Invalid video ID format"
        ),
    ]

    @classmethod
    def classify(cls, error_message: str) -> str:
        """
        Classify an error message and return a concise summary.

        Args:
            error_message: Raw error message (can be multi-line)

        Returns:
            Concise, actionable error summary
        """
        if not error_message:
            return "Unknown error"

        # Normalize: lowercase, collapse whitespace
        normalized = " ".join(error_message.lower().split())

        # Try each pattern
        for pattern, summary in cls.PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return summary

        # If no pattern matches, extract first meaningful line
        lines = [line.strip() for line in error_message.split('\n') if line.strip()]

        # Skip generic headers
        skip_phrases = [
            "this is most likely caused by",
            "ways to work around",
            "if you are sure",
            "please create an issue",
            "make sure that there are no open issues"
        ]

        for line in lines:
            if len(line) < 200:  # Keep it concise
                # Skip if it's a generic instruction line
                if not any(phrase in line.lower() for phrase in skip_phrases):
                    # Extract just the core message
                    # Remove URLs
                    line = re.sub(r'https?://[^\s]+', '', line)
                    # Remove "This usually is due to..."
                    line = re.sub(r'This (usually|often) is.*?:', '', line, flags=re.IGNORECASE)
                    # Clean up
                    line = line.strip()
                    if line and len(line) > 10:
                        return line[:150]  # Cap at 150 chars

        # Last resort: first sentence
        first_sentence = error_message.split('.')[0].strip()
        if first_sentence and len(first_sentence) < 200:
            return first_sentence

        return "Transcript fetch failed"

    @classmethod
    def classify_with_solution(cls, error_message: str) -> tuple[str, Optional[str]]:
        """
        Classify error and provide solution suggestion.

        Args:
            error_message: Raw error message

        Returns:
            Tuple of (summary, solution_hint)
        """
        summary = cls.classify(error_message)

        # Map summaries to solutions
        solutions = {
            "YouTube blocked exit IP": "Rotate Tor circuit or wait 5 minutes",
            "Exit IP from blocked cloud provider": "Rotate Tor to get residential IP",
            "Rate limit exceeded": "Wait 5-10 minutes before retrying",
            "Video has no subtitles": "Video doesn't have transcripts",
            "No transcripts available": "Creator didn't enable transcripts",
            "No English transcript": "Check video for other language options",
            "Video unavailable": "Video deleted, private, or region-locked",
            "Video is private": "Cannot access private videos",
            "Connection timeout": "Check internet connection or try again",
            "Connection refused": "YouTube may be blocking connection",
            "Invalid video ID": "Check URL format is correct",
        }

        solution = solutions.get(summary)
        return summary, solution


def simplify_error(error_message: str) -> str:
    """
    Quick helper to simplify an error message.

    Args:
        error_message: Raw error message

    Returns:
        Concise error summary
    """
    return ErrorClassifier.classify(error_message)


def get_error_with_solution(error_message: str) -> str:
    """
    Get simplified error with solution hint.

    Args:
        error_message: Raw error message

    Returns:
        Formatted string: "Error: [summary] → [solution]"
    """
    summary, solution = ErrorClassifier.classify_with_solution(error_message)

    if solution:
        return f"{summary} → {solution}"
    return summary


# Test examples
if __name__ == "__main__":
    test_cases = [
        # IP blocks
        """Could not retrieve a transcript for the video https://www.youtube.com/watch?v=abc! This is most likely caused by:

YouTube is blocking requests from your IP. This usually is due to one of the following reasons:
- You have done too many requests and your IP has been blocked by YouTube
- You are doing requests from an IP belonging to a cloud provider (like AWS, Google Cloud Platform, Azure, etc.). Unfortunately, most IPs from cloud providers are blocked by YouTube.

Ways to work around this are explained in the "Working around IP bans" section of the README (https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans-requestblocked-or-ipblocked-exception).

If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!""",

        # No subtitles
        "No subtitles found for requested languages",

        # Timeout
        "Connection timed out after 60 seconds",

        # Private video
        "Video unavailable: This video is private",
    ]

    logger.error("Error Classification Tests")
    logger.info("=" * 60)

    for i, error in enumerate(test_cases, 1):
        logger.info(f"\nTest {i}:")
        logger.error(f"Original ({len(error)} chars):")
        logger.error(f"  {error[:100]}...")
        logger.info(f"\nSimplified:")
        logger.error(f"  ✓ {simplify_error(error)}")
        logger.info(f"\nWith solution:")
        logger.error(f"  ✓ {get_error_with_solution(error)}")
        logger.info("-" * 60)
