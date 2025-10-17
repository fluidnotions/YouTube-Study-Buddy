#!/usr/bin/env python3
"""
Streamlit Web Interface for YouTube Study Buddy
Provides a user-friendly web interface for processing YouTube videos into study notes
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import streamlit as st

# Add src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from src.yt_study_buddy.app_interface import create_interface, StudyBuddyInterface


def initialize_session_state():
    """Initialize session state variables."""
    if 'processed_videos' not in st.session_state:
        st.session_state.processed_videos = []
    if 'current_processor' not in st.session_state:
        st.session_state.current_processor = None
    if 'extracted_urls' not in st.session_state:
        st.session_state.extracted_urls = ""
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'show_quick_start' not in st.session_state:
        st.session_state.show_quick_start = True


def create_processor(subject, global_context, generate_assessments=True, auto_categorize=True, base_dir="notes", parallel=False, max_workers=3, export_pdf=False, pdf_theme='obsidian'):
    """Create or update the YouTube processor based on settings."""
    return create_interface(
        subject=subject if subject else None,
        global_context=global_context,
        base_dir=base_dir,
        generate_assessments=generate_assessments,
        auto_categorize=auto_categorize,
        parallel=parallel,
        max_workers=max_workers,
        export_pdf=export_pdf,
        pdf_theme=pdf_theme
    )


def extract_playlist_urls(playlist_url):
    """
    Extract video URLs from a YouTube playlist using yt-dlp.

    Args:
        playlist_url: YouTube playlist URL

    Returns:
        List of video URLs or None if error
    """
    try:
        # Check if yt-dlp is available
        result = subprocess.run(
            ['yt-dlp', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None, "yt-dlp is not installed. Install with: pip install yt-dlp"

        # Extract URLs from playlist
        result = subprocess.run(
            [
                'yt-dlp',
                '--flat-playlist',
                '--print', 'url',
                playlist_url
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return None, f"Failed to extract playlist: {result.stderr}"

        # Parse URLs
        urls = [url.strip() for url in result.stdout.strip().split('\n') if url.strip()]

        if not urls:
            return None, "No URLs found in playlist"

        return urls, None

    except subprocess.TimeoutExpired:
        return None, "Timeout while extracting playlist (> 60s)"
    except FileNotFoundError:
        return None, "yt-dlp is not installed. Install with: pip install yt-dlp"
    except Exception as e:
        return None, f"Error: {str(e)}"


def display_knowledge_graph_stats(processor):
    """Display knowledge graph statistics in sidebar."""
    with st.sidebar:
        st.subheader("📊 Knowledge Graph Stats")
        try:
            stats = processor.get_knowledge_graph_stats()

            if 'error' in stats:
                st.error(f"Could not load stats: {stats['error']}")
                return

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Notes", stats['total_notes'])
            with col2:
                st.metric("Concepts", stats['total_concepts'])

            if stats.get('subject_count', 0) > 0:
                st.metric("Subjects", stats['subject_count'])
                with st.expander("View Subjects"):
                    for subject in stats.get('subjects', []):
                        st.write(f"• {subject}")
        except Exception as e:
            st.error(f"Could not load stats: {e}")


def validate_urls(url_text):
    """
    Validate URLs and return list of valid URLs with error message if any invalid.

    Returns:
        tuple: (list of valid URLs, error message or None)
    """
    if not url_text or not url_text.strip():
        return None, "⚠️ No URLs provided. Please enter at least one YouTube URL."

    lines = [line.strip() for line in url_text.strip().split('\n') if line.strip()]

    if not lines:
        return None, "⚠️ No valid URLs found. Please enter YouTube URLs (one per line)."

    valid_urls = []
    invalid_lines = []

    for i, line in enumerate(lines, 1):
        # Skip comments
        if line.startswith('#'):
            continue

        # Basic YouTube URL validation
        if 'youtube.com' in line or 'youtu.be' in line:
            valid_urls.append(line)
        else:
            invalid_lines.append(f"Line {i}: {line[:50]}...")

    if invalid_lines and not valid_urls:
        error = "❌ No valid YouTube URLs found.\n\nInvalid lines:\n" + "\n".join(invalid_lines[:5])
        if len(invalid_lines) > 5:
            error += f"\n... and {len(invalid_lines) - 5} more"
        return None, error

    if invalid_lines:
        warning = f"⚠️ Found {len(invalid_lines)} invalid line(s) - will skip these:\n" + "\n".join(invalid_lines[:3])
        if len(invalid_lines) > 3:
            warning += f"\n... and {len(invalid_lines) - 3} more"
        return valid_urls, warning

    return valid_urls, None


def process_single_video(url, processor, progress_container, worker_id=0):
    """Process a single YouTube video with progress tracking."""
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Process using interface
            status_text.text("🔍 Processing video...")
            progress_bar.progress(10)

            result = processor.process_video(url, worker_id=worker_id)

            if not result.success:
                st.error(f"❌ Error: {result.error}")
                return False

            progress_bar.progress(100)
            status_text.text("✅ Successfully processed!")

            # Store result for UI
            ui_result = {
                'title': result.video_title,
                'url': result.url,
                'filename': str(result.notes_filepath) if result.notes_filepath else None,
                'related_notes': result.related_notes_count,
                'transcript_length': result.transcript_length,
                'pdf_exported': result.notes_pdf_path is not None
            }
            st.session_state.processed_videos.append(ui_result)

            return ui_result

        except Exception as e:
            st.error(f"❌ Error processing video: {e}")
            return False


def main():
    st.set_page_config(
        page_title="YouTube Study Buddy",
        page_icon="📚",
        layout="wide"
    )

    initialize_session_state()

    st.title("📚 YouTube Study Buddy")
    st.markdown("Transform YouTube videos into organized study notes with AI-powered cross-referencing")

    # Sidebar - Status and Settings
    with st.sidebar:
        st.header("🔑 System Status")

        # API key check
        api_key = os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            st.success("✅ Claude API key found")
        else:
            st.error("❌ Claude API key not found")
            st.info("Set `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` environment variable")

        st.divider()

        # Output location (fixed for Docker)
        st.header("📁 Output Location")

        # Fixed output directory
        output_base_dir = "notes"

        st.info("📂 Notes saved to: `./notes/`")
        st.caption("💡 **Docker users**: Files appear in `./notes/` on your host machine")
        st.caption("💡 **CLI users**: Use `--base-dir` flag for custom paths")

        st.divider()

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🎬 Process Videos", "📊 Results", "❓ Help"])

    with tab1:
        # Quick start hint
        if st.session_state.show_quick_start:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.info("💡 **First time?** Use recommended settings below, or customize as needed.")
            with col2:
                if st.button("✕", help="Dismiss"):
                    st.session_state.show_quick_start = False
                    st.rerun()

        # Processing Settings Section
        st.subheader("⚙️ Processing Settings")

        col1, col2 = st.columns(2)

        with col1:
            subject = st.text_input(
                "📂 Subject",
                placeholder="e.g., Machine Learning, Python, History (optional)",
                help="Organize notes by subject. Leave blank to auto-categorize.",
                disabled=st.session_state.processing
            )

            global_context = st.checkbox(
                "🌐 Global cross-referencing",
                value=True,
                help="Find connections across all subjects vs. subject-only",
                disabled=st.session_state.processing
            )

        with col2:
            # Feature toggles in 2x2 grid
            col2a, col2b = st.columns(2)
            with col2a:
                generate_assessments = st.checkbox(
                    "📝 Assessments",
                    value=True,
                    help="Generate learning questions",
                    disabled=st.session_state.processing
                )
                auto_categorize = st.checkbox(
                    "🏷️ Auto-categorize",
                    value=True,
                    help="Auto-detect subject (when blank)",
                    disabled=st.session_state.processing
                )
            with col2b:
                export_pdf = st.checkbox(
                    "📄 Export PDF",
                    value=False,
                    help="Export notes and assessments to PDF",
                    disabled=st.session_state.processing
                )
                if export_pdf:
                    pdf_theme = st.selectbox(
                        "PDF Theme",
                        options=['obsidian', 'academic', 'minimal', 'default'],
                        index=0,
                        help="Choose PDF styling theme",
                        disabled=st.session_state.processing,
                        label_visibility="collapsed"
                    )
                else:
                    pdf_theme = 'obsidian'

        # Parallel processing settings
        st.subheader("⚡ Performance Settings")
        col1, col2 = st.columns(2)
        with col1:
            use_parallel = st.checkbox(
                "🚀 Parallel Processing",
                value=True,
                help="Process multiple videos simultaneously for faster batch operations",
                disabled=st.session_state.processing
            )
        with col2:
            if use_parallel:
                max_workers = st.slider(
                    "Workers",
                    min_value=1,
                    max_value=5,
                    value=3,
                    help="Number of concurrent processing tasks. More workers = faster but higher rate limit risk",
                    disabled=st.session_state.processing
                )
            else:
                max_workers = 1

        st.divider()

        # Playlist Extraction Section
        st.subheader("📋 Extract from YouTube Playlist (Optional)")
        st.caption("ℹ️ Note: Playlist must be public or unlisted to extract URLs")

        col1, col2 = st.columns([4, 1])
        with col1:
            playlist_url = st.text_input(
                "Playlist URL",
                placeholder="https://www.youtube.com/playlist?list=...",
                help="Enter a YouTube playlist URL to extract all video URLs. Playlist must be public or unlisted.",
                disabled=st.session_state.processing,
                label_visibility="collapsed"
            )
        with col2:
            extract_button = st.button(
                "🔍 Extract URLs",
                type="secondary",
                disabled=st.session_state.processing or not playlist_url
            )

        if extract_button and playlist_url:
            with st.spinner("Extracting playlist URLs..."):
                urls, error = extract_playlist_urls(playlist_url)

                if error:
                    st.error(error)
                else:
                    st.session_state.extracted_urls = '\n'.join(urls)
                    st.success(f"✅ Extracted {len(urls)} videos from playlist")
                    st.rerun()

        # Show extraction status
        if st.session_state.extracted_urls:
            url_count = len([u for u in st.session_state.extracted_urls.split('\n') if u.strip()])
            st.info(f"📊 {url_count} URL{'s' if url_count != 1 else ''} ready to process")

        st.divider()

        # URL Text Area
        st.subheader("📝 Video URLs (one per line)")

        url_text = st.text_area(
            "URLs",
            value=st.session_state.extracted_urls,
            placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...\n\n# You can add comments with #\nhttps://youtu.be/...",
            height=200,
            help="Enter YouTube URLs, one per line. Use # for comments.",
            disabled=st.session_state.processing,
            label_visibility="collapsed"
        )

        # Update session state
        if not st.session_state.processing:
            st.session_state.extracted_urls = url_text

        # Action buttons
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            process_button = st.button(
                "🚀 Process Videos",
                type="primary",
                disabled=st.session_state.processing,
                use_container_width=True
            )

        with col2:
            if st.session_state.processing:
                st.button("⏸️ Processing...", disabled=True, use_container_width=True)

        with col3:
            if st.button("🗑️ Clear", disabled=st.session_state.processing, use_container_width=True):
                st.session_state.extracted_urls = ""
                st.rerun()

        # Process videos
        if process_button:
            # Validate URLs
            valid_urls, error_or_warning = validate_urls(url_text)

            if valid_urls is None:
                st.error(error_or_warning)
            else:
                # Show warning if any invalid URLs
                if error_or_warning:
                    st.warning(error_or_warning)

                # Check API key
                if not api_key:
                    st.error("❌ Please set your Claude API key first")
                else:
                    # Set processing flag
                    st.session_state.processing = True

                    # Create processor with fixed output path
                    processor = create_processor(
                        subject if subject else None,
                        global_context,
                        generate_assessments,
                        auto_categorize and not subject,
                        base_dir=output_base_dir,
                        parallel=use_parallel,
                        max_workers=max_workers,
                        export_pdf=export_pdf,
                        pdf_theme=pdf_theme
                    )

                    # Switch to Results tab by rerunning with active tab
                    st.session_state.active_tab = "results"

                    # Process videos
                    progress_container = st.container()
                    status_container = st.container()

                    with status_container:
                        mode_text = f"parallel with {max_workers} workers" if use_parallel else "sequentially"
                        st.info(f"🎬 Processing {len(valid_urls)} video{'s' if len(valid_urls) != 1 else ''} {mode_text}...")

                    overall_progress = st.progress(0)
                    overall_status = st.empty()

                    if use_parallel:
                        # Parallel processing using the CLI's built-in method
                        results = []
                        completed = [0]  # Use list to allow modification in callback

                        def progress_callback(status, completed_count, total):
                            """Update Streamlit progress."""
                            completed[0] = completed_count
                            overall_progress.progress(completed_count / total)
                            overall_status.text(f"Processing: {completed_count}/{total} videos ({status})")

                        # Set progress callback
                        if hasattr(processor, 'parallel_processor'):
                            processor.parallel_processor.progress_callback = progress_callback

                        # Use the process_urls method which handles parallel internally
                        processor.process_urls(valid_urls)

                        # Count successful from metrics
                        successful = processor.metrics.successful if hasattr(processor, 'metrics') else len(valid_urls)
                    else:
                        # Sequential processing
                        successful = 0
                        for i, url in enumerate(valid_urls):
                            overall_status.text(f"Processing {i+1}/{len(valid_urls)}: {url[:60]}...")

                            if i > 0:  # Add delay between requests
                                time.sleep(3)

                            result = process_single_video(url, processor, progress_container)
                            if result:
                                successful += 1

                            overall_progress.progress((i + 1) / len(valid_urls))

                    # Reset processing flag
                    st.session_state.processing = False

                    # Show completion message
                    if successful == len(valid_urls):
                        st.success(f"✅ Successfully processed all {successful} video{'s' if successful != 1 else ''}!")
                    elif successful > 0:
                        st.warning(f"⚠️ Processed {successful}/{len(valid_urls)} videos. Some failed.")
                    else:
                        st.error(f"❌ Failed to process any videos.")

                    # Display knowledge graph stats in sidebar
                    with st.sidebar:
                        display_knowledge_graph_stats(processor)

    with tab2:
        st.header("📊 Processing Results")

        if st.session_state.processed_videos:
            st.info(f"Total videos processed this session: {len(st.session_state.processed_videos)}")

            for i, result in enumerate(reversed(st.session_state.processed_videos)):
                with st.expander(f"📹 {result['title']}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**URL:** [Link]({result['url']})")
                        st.write(f"**File:** {result['filename']}")
                    with col2:
                        st.metric("Related Notes", result['related_notes'])
                        st.metric("Transcript Length", f"{result['transcript_length']:,}")
        else:
            st.info("No videos processed yet. Use the tabs above to get started!")

        if st.button("🗑️ Clear Results"):
            st.session_state.processed_videos = []
            st.rerun()

    # Add Knowledge Graph stats to sidebar
    with st.sidebar:
        if st.session_state.processed_videos:
            # Create a dummy processor to show stats
            output_base_dir = "notes"  # Fixed output directory
            processor = create_processor(
                None, True, True, True,
                base_dir=output_base_dir
            )
            display_knowledge_graph_stats(processor)

    with tab3:
        st.header("❓ Help & Information")

        st.markdown("""
        ### 🚀 Getting Started

        1. **Set up your Claude API key** as an environment variable:
           - `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY`
           - Get it from [console.anthropic.com](https://console.anthropic.com/)

        2. **Configure processing settings** in the "Process Videos" tab:
           - **Subject**: Organize notes by topic (optional - leave blank for auto-categorization)
           - **Global cross-referencing**: Find connections across all subjects
           - **Transcript method**: Choose API, Scraper, or Tor
           - **Assessments**: Generate learning questions alongside notes
           - **Auto-categorize**: Automatically detect and organize by subject

        3. **Add video URLs**:
           - **Option A - Extract from playlist**: Enter playlist URL → Click "Extract URLs"
           - **Option B - Manual entry**: Paste URLs directly into the text area (one per line)
           - **Tip**: You can mix both methods - extract playlist then edit the list

        4. **Process and view results**:
           - Click "🚀 Process Videos" to start
           - View progress and results in the "Results" tab
           - Files are saved to `notes/[Subject]/` folders

        ### 📁 Output Structure

        Notes are saved in organized folders:
        ```
        notes/
        ├── [Subject Name]/
        │   ├── video1_notes.md
        │   └── video2_notes.md
        └── [Another Subject]/
            └── video3_notes.md
        ```

        ### 🔗 Features

        - **AI-powered summarization** using Claude Sonnet 4.5
        - **Learning assessments** with gap analysis and application questions
        - **Auto-categorization** using ML-based subject detection
        - **Playlist extraction** using yt-dlp for batch processing
        - **Cross-referencing** between related notes
        - **Obsidian integration** with automatic [[links]]
        - **Knowledge graph** for concept tracking
        - **Tor-based fetching** for reliable transcript access

        ### 💡 Tips

        - **Playlist processing**: Use the playlist extractor to quickly get all URLs from a YouTube playlist
        - **Auto-categorization**: Leave subject blank and enable auto-categorize to let AI organize your notes
        - **Assessments**: Enable assessments to get learning questions that test deeper understanding
        - **Cross-referencing**: Global finds connections across all subjects, subject-only stays focused
        - **Tor method**: For best results with rate limiting, use Tor with the tor-proxy container
        - The tool automatically adds delays between batch requests to avoid rate limiting

        ### 📦 Dependencies for Playlist Extraction

        Install yt-dlp to enable playlist URL extraction:
        ```bash
        pip install yt-dlp
        # or
        uv pip install yt-dlp
        ```
        """)


if __name__ == "__main__":
    main()