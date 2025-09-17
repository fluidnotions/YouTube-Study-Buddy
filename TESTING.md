# Testing Guide

This guide explains how to run and debug tests for the YouTube to Study Notes tool.

## Quick Start

### Install Test Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
# Quick smoke tests (fast)
python run_tests.py unit

# All tests
python run_tests.py all

# With coverage report
python run_tests.py coverage
```

## VSCode Integration

### Setup
1. Open the project in VSCode
2. Install the Python extension
3. Tests should be auto-discovered in the Test Explorer

### Running Tests in VSCode

#### Method 1: Test Explorer
- Open Test Explorer panel (sidebar)
- Click play button next to individual tests or test files
- View results in the explorer

#### Method 2: Command Palette
- Press `Ctrl+Shift+P`
- Type "Python: Run All Tests" or "Python: Debug All Tests"

#### Method 3: Debug Configuration
- Press `F5` and select test configuration:
  - "Debug All Tests" - Run all tests with debugger
  - "Debug Unit Tests Only" - Run only unit tests
  - "Debug Integration Tests" - Run integration tests
  - "Debug Current Test File" - Debug the currently open test file

#### Method 4: Tasks
- Press `Ctrl+Shift+P` -> "Tasks: Run Task"
- Select from available test tasks:
  - "Run Unit Tests"
  - "Run All Tests"
  - "Run Tests with Coverage"
  - "Run Quick Smoke Tests"

### Debugging Tests
1. Set breakpoints in test files or source code
2. Use "Debug Current Test File" configuration
3. Or right-click on test function -> "Debug Test"

## Test Categories

Tests are organized with pytest markers:

### Unit Tests (`@pytest.mark.unit`)
- Fast tests that don't require external APIs
- Mock external dependencies
- Test isolated functionality

```bash
python run_tests.py unit
```

### Integration Tests (`@pytest.mark.integration`)
- May hit external APIs (YouTube, Claude)
- Test component interactions
- Slower execution

```bash
python run_tests.py integration
```

### Specific API Tests
```bash
# API provider tests
python -m pytest tests/ -m api -v

# Scraper provider tests
python -m pytest tests/ -m scraper -v

# Network-dependent tests
python -m pytest tests/ -m network -v
```

## Test Structure

```
tests/
├── __init__.py                 # Test package
├── conftest.py                 # Pytest fixtures and configuration
├── test_quick_smoke.py         # Fast smoke tests
├── test_video_processor.py     # VideoProcessor tests
├── test_transcript_providers.py # Provider interface tests
└── test_main_integration.py    # Main application tests
```

## Key Test Files

### `test_quick_smoke.py`
- Fastest tests for basic functionality
- Import validation
- Basic object creation
- File structure validation

### `test_video_processor.py`
- URL parsing and video ID extraction
- Provider switching
- Error handling
- Filename sanitization

### `test_transcript_providers.py`
- Protocol and ABC interface testing
- API provider functionality
- Scraper provider functionality
- Provider comparison

### `test_main_integration.py`
- End-to-end workflow testing
- Command-line argument processing
- Batch processing
- Interactive mode

## Running Specific Tests

### Single Test Function
```bash
python run_tests.py specific tests/test_video_processor.py::TestVideoProcessor::test_video_id_extraction
```

### Single Test File
```bash
python run_tests.py specific tests/test_quick_smoke.py
```

### Test Class
```bash
python run_tests.py specific tests/test_video_processor.py::TestVideoProcessor
```

## Test Configuration

### `pytest.ini`
- Test discovery settings
- Marker definitions
- Output formatting
- Warning filters

### `.vscode/settings.json`
- VSCode test discovery
- Python path configuration
- Test framework settings

### `.vscode/launch.json`
- Debug configurations for tests
- Environment variable setup
- PYTHONPATH configuration

## Coverage Reports

Generate coverage reports:
```bash
python run_tests.py coverage
```

View HTML report:
```bash
# Opens htmlcov/index.html in browser
start htmlcov/index.html    # Windows
open htmlcov/index.html     # Mac
xdg-open htmlcov/index.html # Linux
```

## Troubleshooting

### Tests Not Discovered in VSCode
1. Check Python interpreter is set correctly
2. Ensure pytest is installed: `pip install pytest`
3. Reload window: `Ctrl+Shift+P` -> "Developer: Reload Window"
4. Check `.vscode/settings.json` configuration

### Import Errors
1. Verify PYTHONPATH includes `src/` directory
2. Check that `__init__.py` files exist
3. Use absolute imports in test files

### External API Test Failures
1. Check internet connection
2. Be aware that YouTube may rate limit
3. Some tests may fail due to external service issues
4. Use mocking for consistent testing

### Performance Issues
1. Run unit tests only: `python run_tests.py unit`
2. Skip slow tests: `python -m pytest tests/ -m "not slow"`
3. Run specific test files instead of all tests

## Best Practices

### Writing Tests
1. Use appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
2. Mock external dependencies in unit tests
3. Use descriptive test names
4. Test both success and failure cases
5. Use fixtures for common setup

### Debugging
1. Use `pytest -s` to see print statements
2. Set breakpoints in VSCode for interactive debugging
3. Use `pytest --tb=long` for detailed tracebacks
4. Add `import pdb; pdb.set_trace()` for command-line debugging

### CI/CD Considerations
1. Run unit tests first (faster feedback)
2. Separate integration tests that require network
3. Use coverage thresholds to maintain quality
4. Consider separate test environments for external APIs