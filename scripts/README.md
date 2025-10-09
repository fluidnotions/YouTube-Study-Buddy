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

- `test_simple.py` - Simple 2-video test to verify Tor circuit rotation
- `test_transcript.py` - Comprehensive transcript fetching test with different configs
- `test_tor_in_group.sh` - Test Tor access with group permissions
- `fix_and_test.sh` - Quick test and fix script

### Usage

```bash
# Run simple test
./scripts/run_with_tor.sh python scripts/test_simple.py

# Run comprehensive test
./scripts/run_with_tor.sh python scripts/test_transcript.py
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
