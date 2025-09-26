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

## PyCharm Professional Integration

### Setup
1. Open the project in PyCharm Professional
2. Configure Poetry interpreter (see Python Interpreter Configuration below)
3. Tests should be auto-discovered in the Test Runner

### Running Tests in PyCharm

#### Method 1: Test Runner Panel
- Open Test Runner panel (bottom toolbar)
- Click play button next to individual tests or test files
- View results with detailed output

#### Method 2: Right-Click Context Menu
- Right-click on test file or function
- Select "Run" or "Debug" from context menu

#### Method 3: Run Configurations
- Use pre-configured run configurations:
  - "Run Unit Tests"
  - "Run All Tests"
  - "Run Integration Tests"
  - "Debug Current Test File"

#### Method 4: Gutter Icons
- Click the green play button next to test functions
- Use the debug button for breakpoint debugging

### Debugging Tests
1. Set breakpoints in test files or source code (click in gutter)
2. Right-click test -> "Debug Test"
3. Use Variables and Console tabs for inspection
4. Step through code using F7 (step into), F8 (step over)

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

## PyCharm Configuration

### Python Interpreter Configuration
1. **File** → **Settings** → **Project** → **Python Interpreter**
2. Click the gear icon → **Add**
3. Select **Poetry Environment**
4. Choose **Existing environment** if Poetry is already set up
5. Point to: `D:\Documents\career transformation\ml_mono_repo\ytstudybuddy\.venv\Scripts\python.exe`

### Project Structure Configuration
1. **File** → **Settings** → **Project** → **Project Structure**
2. Mark `src` folder as **Sources Root** (blue folder icon)
3. Mark `tests` folder as **Test Sources Root** (green folder icon)
4. This ensures proper import resolution

### Jupyter Notebook Configuration
1. **File** → **Settings** → **Languages & Frameworks** → **Jupyter**
2. Ensure **Jupyter server** is set to use project interpreter
3. Configure **Startup timeout** if needed (default: 10 seconds)
4. Check **Run cells below** option for better workflow

### Test Framework Configuration
1. **File** → **Settings** → **Tools** → **Python Integrated Tools**
2. Set **Default test runner** to **pytest**
3. Ensure **Project interpreter** matches Poetry environment

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

### Jupyter Notebooks Not Working in PyCharm
1. **Check Python interpreter**: Ensure it's set to Poetry environment
2. **Verify Jupyter installation**: `poetry run jupyter --version`
3. **Restart Jupyter server**: In PyCharm, go to Tools → Stop Jupyter Server, then restart
4. **Check project structure**: Ensure `src` is marked as Sources Root
5. **Clear caches**: File → Invalidate Caches and Restart

### Tests Not Discovered in PyCharm
1. Check Python interpreter matches Poetry environment
2. Ensure pytest is installed: `poetry show pytest`
3. Mark `tests` folder as Test Sources Root
4. Invalidate caches and restart PyCharm
5. Check Run Configuration templates

### Import Errors in Notebooks/Tests
1. Verify project structure: `src` should be Sources Root
2. Check Poetry environment is active
3. Ensure `__init__.py` files exist in packages
4. Use absolute imports from project root

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