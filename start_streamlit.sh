#!/bin/bash
# Start Streamlit with correct uv environment

# Clear any conflicting VIRTUAL_ENV
unset VIRTUAL_ENV

# Change to project directory
cd "$(dirname "$0")"

# Run streamlit through uv's Python
echo "Starting Streamlit with uv environment..."
echo "Access the app at: http://localhost:8501"
echo ""

uv run python -m streamlit run streamlit_app.py "$@"
