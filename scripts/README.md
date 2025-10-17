# Scripts Directory

This folder contains helper scripts for local development and testing. **These are NOT needed for Docker usage.**

## Local Tor Setup Scripts

**⚠️ Only needed if running locally WITHOUT Docker**

- `setup_tor_control.sh` - Interactive Tor control port setup for local development
- `setup_tor_control_auto.sh` - Non-interactive version for automation
- `run_with_tor.sh` - Helper to run commands with debian-tor group permissions

### Usage

```bash
# Setup Tor for local development
./scripts/setup_tor_control.sh

# Then run app with Tor group permissions
./scripts/run_with_tor.sh uv run streamlit run streamlit_app.py
```

## Test Scripts

### Development/Testing
- `test_simple.py` - Simple 2-video test to verify Tor circuit rotation
- `test_transcript.py` - Comprehensive transcript fetching test with different configs
- `test_parallel_processing.py` - Test parallel worker setup
- `test_parallel_optimization.py` - Parallel processing optimization tests
- `test_exit_node_tracking.py` - Test exit node tracker functionality
- `test_fallback.py` - Test fallback mechanisms
- `test_tor_in_group.sh` - Test Tor access with group permissions
- `fix_and_test.sh` - Quick test and fix script

### Diagnostic Tools
- `diagnose_tor.py` - Test Tor connection and exit node diversity
- `diagnose_failures.py` - Analyze failure patterns in processing logs
- `check_failures.py` - Quick failure check utility

### Example Scripts
- `example_job_logging.py` - Example of job logging functionality
- `debug_cli.py` - Debug wrapper for CLI commands (PyCharm debugging)

### Usage

```bash
# Run simple test
./scripts/run_with_tor.sh python scripts/test_simple.py

# Run comprehensive test
./scripts/run_with_tor.sh python scripts/test_transcript.py

# Diagnose Tor connection
uv run python scripts/diagnose_tor.py

# Check for failed jobs
uv run python scripts/check_failures.py
```

## Docker Users

**If you're using Docker, you don't need any of these scripts!**

Just use:
```bash
docker run -d --name youtube-study-buddy -p 8501:8501 --env-file .env youtube-study-buddy:python-tor
```

Or the convenience script in project root:
```bash
./run-docker.sh
```
