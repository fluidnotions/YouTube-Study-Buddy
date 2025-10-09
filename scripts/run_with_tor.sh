#!/bin/bash
# Helper script to run commands with Tor group permissions

if [ $# -eq 0 ]; then
    echo "Usage: ./run_with_tor.sh <command>"
    echo ""
    echo "Examples:"
    echo "  ./run_with_tor.sh uv run pytest"
    echo "  ./run_with_tor.sh uv run python test_simple.py"
    echo "  ./run_with_tor.sh uv run streamlit run streamlit_app.py"
    exit 1
fi

sg debian-tor -c "$*"
