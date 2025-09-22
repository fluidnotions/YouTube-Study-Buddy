#!/usr/bin/env python3
"""
Streamlit Web Interface for YouTube Study Buddy
Provides a user-friendly web interface for processing YouTube videos into study notes
"""

import streamlit as st
import os
import sys
import tempfile
import time
from pathlib import Path

# Add src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from main import YouTubeStudyNotes
from yt_study_buddy.knowledge_graph import KnowledgeGraph


def initialize_session_state():
    """Initialize session state variables."""
    if 'processed_videos' not in st.session_state:
        st.session_state.processed_videos = []
    if 'current_processor' not in st.session_state:
        st.session_state.current_processor = None


def create_processor(subject, global_context, provider_type):
    """Create or update the YouTube processor based on settings."""
    return YouTubeStudyNotes(
        subject=subject if subject else None,
        global_context=global_context,
        provider_type=provider_type
    )


def display_knowledge_graph_stats(processor):
    """Display knowledge graph statistics in sidebar."""
    with st.sidebar:
        st.subheader("📊 Knowledge Graph Stats")
        try:
            stats = processor.knowledge_graph.get_stats()
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


def process_single_video(url, processor):
    """Process a single YouTube video with progress tracking."""
    with st.container():
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Extract video ID
        status_text.text("🔍 Extracting video ID...")
        progress_bar.progress(10)

        video_id = processor.video_processor.get_video_id(url)
        if not video_id:
            st.error(f"❌ Invalid YouTube URL: {url}")
            return False

        # Get transcript
        status_text.text("📄 Fetching transcript...")
        progress_bar.progress(30)

        try:
            transcript_data = processor.video_processor.get_transcript(video_id)
            transcript = transcript_data['transcript']

            # Get video title
            status_text.text("📝 Getting video title...")
            progress_bar.progress(50)

            video_title = processor.video_processor.get_video_title(video_id)

            # Find related notes
            status_text.text("🔗 Finding related notes...")
            progress_bar.progress(70)

            related_notes = processor.knowledge_graph.find_related_notes(transcript)

            # Generate study notes
            status_text.text("🤖 Generating study notes with Claude...")
            progress_bar.progress(85)

            if not processor.notes_generator.is_ready():
                st.error("❌ Claude API not ready. Check your API key.")
                return False

            study_notes = processor.notes_generator.generate_notes(transcript, related_notes)
            if not study_notes:
                st.error("❌ Failed to generate study notes")
                return False

            # Save to file
            status_text.text("💾 Saving study notes...")
            progress_bar.progress(95)

            os.makedirs(processor.output_dir, exist_ok=True)
            original_url = f"https://www.youtube.com/watch?v={video_id}"
            filename = processor.notes_generator.create_markdown_file(
                video_title, original_url, study_notes, processor.output_dir, video_id
            )

            # Add Obsidian links
            processor.obsidian_linker.process_file(filename)
            processor.knowledge_graph.refresh_cache()

            progress_bar.progress(100)
            status_text.text("✅ Successfully processed!")

            # Store result
            result = {
                'title': video_title,
                'url': original_url,
                'filename': filename,
                'related_notes': len(related_notes),
                'transcript_length': transcript_data['length']
            }
            st.session_state.processed_videos.append(result)

            return result

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

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API key check
        api_key = os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            st.success("✅ Claude API key found")
        else:
            st.error("❌ Claude API key not found")
            st.info("Set CLAUDE_API_KEY or ANTHROPIC_API_KEY environment variable")

        # Subject configuration
        subject = st.text_input(
            "📂 Subject (optional)",
            help="Organize notes by subject. Creates a folder structure."
        )

        # Cross-reference scope
        global_context = st.checkbox(
            "🌐 Global cross-referencing",
            value=True,
            help="Find connections across all subjects vs. subject-only"
        )

        # Provider selection
        provider_type = st.selectbox(
            "🔧 Transcript Method",
            ["api", "scraper"],
            help="API: YouTube Transcript API (may hit rate limits)\nScraper: Web scraping (bypasses limits)"
        )

        st.divider()

    # Create processor
    processor = create_processor(subject, global_context, provider_type)
    display_knowledge_graph_stats(processor)

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Single Video", "📦 Batch Processing", "📊 Results", "❓ Help"])

    with tab1:
        st.header("Process Single YouTube Video")

        col1, col2 = st.columns([3, 1])
        with col1:
            url = st.text_input(
                "YouTube URL",
                placeholder="https://www.youtube.com/watch?v=...",
                help="Paste a YouTube video URL"
            )
        with col2:
            process_button = st.button("🚀 Process Video", type="primary")

        if process_button and url:
            if not api_key:
                st.error("❌ Please set your Claude API key first")
            else:
                result = process_single_video(url, processor)
                if result:
                    st.success(f"✅ Successfully processed: **{result['title']}**")
                    with st.expander("📋 Details"):
                        st.write(f"**File:** {result['filename']}")
                        st.write(f"**Related Notes:** {result['related_notes']}")
                        st.write(f"**Transcript Length:** {result['transcript_length']} characters")

    with tab2:
        st.header("Batch Process Multiple Videos")

        # File upload method
        st.subheader("📁 Upload URLs File")
        uploaded_file = st.file_uploader(
            "Choose a text file with YouTube URLs (one per line)",
            type=['txt']
        )

        if uploaded_file is not None:
            urls = uploaded_file.getvalue().decode('utf-8').strip().split('\n')
            urls = [url.strip() for url in urls if url.strip() and not url.startswith('#')]

            st.info(f"Found {len(urls)} URLs to process")

            if st.button("🚀 Process All URLs", type="primary"):
                if not api_key:
                    st.error("❌ Please set your Claude API key first")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    successful = 0
                    for i, url in enumerate(urls):
                        status_text.text(f"Processing {i+1}/{len(urls)}: {url}")

                        if i > 0:  # Add delay between requests
                            time.sleep(3)

                        result = process_single_video(url, processor)
                        if result:
                            successful += 1

                        progress_bar.progress((i + 1) / len(urls))

                    st.success(f"✅ Batch complete: {successful}/{len(urls)} videos processed")

        # Direct text input method
        st.subheader("📝 Direct Input")
        url_text = st.text_area(
            "Enter YouTube URLs (one per line)",
            placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...",
            height=100
        )

        if url_text and st.button("🚀 Process URLs", type="primary"):
            urls = [url.strip() for url in url_text.strip().split('\n') if url.strip()]
            if not api_key:
                st.error("❌ Please set your Claude API key first")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                successful = 0
                for i, url in enumerate(urls):
                    status_text.text(f"Processing {i+1}/{len(urls)}: {url}")

                    if i > 0:
                        time.sleep(3)

                    result = process_single_video(url, processor)
                    if result:
                        successful += 1

                    progress_bar.progress((i + 1) / len(urls))

                st.success(f"✅ Batch complete: {successful}/{len(urls)} videos processed")

    with tab3:
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

    with tab4:
        st.header("❓ Help & Information")

        st.markdown("""
        ### 🚀 Getting Started

        1. **Set up your Claude API key** as an environment variable:
           - `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY`
           - Get it from [console.anthropic.com](https://console.anthropic.com/)

        2. **Configure your settings** in the sidebar:
           - Choose a subject to organize your notes
           - Select global or subject-only cross-referencing
           - Pick transcript extraction method

        3. **Process videos**:
           - Single videos: Paste URL and click Process
           - Batch: Upload text file or paste multiple URLs

        ### 📁 Output Structure

        Notes are saved in organized folders:
        ```
        Study notes/
        ├── [Subject Name]/
        │   ├── video1_notes.md
        │   └── video2_notes.md
        └── [Another Subject]/
            └── video3_notes.md
        ```

        ### 🔗 Features

        - **AI-powered summarization** using Claude
        - **Cross-referencing** between related notes
        - **Obsidian integration** with automatic [[links]]
        - **Knowledge graph** for concept tracking
        - **Batch processing** for multiple videos
        - **Rate limiting protection** with delays

        ### 🛠️ Transcript Methods

        - **API**: YouTube Transcript API (faster, may hit rate limits)
        - **Scraper**: Web scraping (slower, bypasses rate limits)

        ### 💡 Tips

        - Use subjects to organize notes by topic
        - Global cross-referencing finds connections across all subjects
        - Subject-only cross-referencing keeps connections within the same subject
        - The tool automatically adds delays between batch requests to avoid rate limiting
        """)


if __name__ == "__main__":
    main()