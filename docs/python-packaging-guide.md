# Python Packaging Guide: UV, Packages vs Apps, and Publishing to PyPI

## Overview

This document explains how Python packaging works in this project, including UV package management, the difference between packages and apps, and how to publish to PyPI.

---

## What UV Creates

When you run `uv sync` in this project, UV performs these operations:

### 1. Reads `pyproject.toml`
This file is the source of truth for your package, defining:
- **Package metadata**: name, version, description, authors
- **Dependencies**: what your code needs to run
- **Entry points**: CLI commands that get created
- **Build system configuration**: how to build distribution files

### 2. Creates a Virtual Environment
- Isolated Python environment stored in `.venv/`
- Prevents conflicts with system Python or other projects
- Contains all dependencies and your package

### 3. Installs Dependencies
- Downloads and installs all required packages from PyPI
- Resolves version conflicts automatically
- Creates `uv.lock` file for reproducible installs

### 4. Installs Your Package in "Editable" Mode
- Creates a link from your source code to the virtual environment
- Changes to source code are immediately available (no reinstall needed)
- Package is importable: `import yt_study_buddy`
- CLI commands are available: `youtube-study-buddy`

---

## Package vs App

### Python Package (Library)
- **Purpose**: Library code that others can `import` and use in their own projects
- **Distribution**: Published to PyPI (Python Package Index)
- **Usage**: `import yt_study_buddy` from another project
- **Example**: `requests`, `numpy`, `pandas`
- **Can include**: CLI tools as "extras"

### Python App (Application)
- **Purpose**: End-user tool meant to be run directly
- **Distribution**: May or may not be packaged
- **Usage**: Run as executable command
- **Example**: `git`, `docker`, `pytest`

### This Project: Both!
YouTube Study Buddy is **both a package and an app**:
- **As a package**: Others can `from yt_study_buddy import analyze`
- **As an app**: Users run `youtube-study-buddy` command
- This is a common pattern for Python CLI tools

---

## How It's Linked Together

### Entry Points in `pyproject.toml`

```toml
[project.scripts]
youtube-study-buddy = "yt_study_buddy.cli:main"
```

This creates a **console script** entry point:
- **Command name**: `youtube-study-buddy` (what users type)
- **Points to**: `main()` function in `yt_study_buddy/cli.py`
- **When installed**: Creates executable in `.venv/bin/youtube-study-buddy`

### The Linking Process

1. UV reads the entry point definition in `pyproject.toml`
2. Creates an executable wrapper script in the virtual environment
3. When you run `uv run youtube-study-buddy`, it:
   - Activates the virtual environment
   - Calls the `main()` function in `yt_study_buddy/cli.py`
   - Passes any command-line arguments
4. Your code can also be imported: `from yt_study_buddy import analyze`

### Project Structure

```
ytstudybuddy/
├── src/
│   └── yt_study_buddy/        # Package code (importable)
│       ├── __init__.py
│       ├── cli.py             # Entry point for CLI
│       ├── core.py
│       └── ...
├── tests/                     # Test code
├── docs/                      # Documentation
├── pyproject.toml             # Package definition
├── uv.lock                    # Locked dependencies
└── .venv/                     # Virtual environment (created by UV)
```

This is the **modern Python packaging layout** (src layout):
- Prevents accidental imports of source vs installed package
- Clearer separation between package code and project files
- Recommended by Python Packaging Authority (PyPA)

---

## Publishing to PyPI

### Current State
Your package is **private/local** - only works on your machine via the editable install.

### Steps to Publish Publicly

#### 1. Prepare Your Package

Ensure your `pyproject.toml` is complete:

```toml
[project]
name = "youtube-study-buddy"
version = "0.1.0"
description = "YouTube transcript to study notes converter with AI integration"
authors = [
    {name = "Justin Robinson", email = "justin.g.robinson@gmail.com"}
]
readme = "README.md"
requires-python = ">=3.13"
license = {text = "MIT"}  # Add a license
# ... dependencies ...
```

**Pre-publication checklist**:
- ✅ Package metadata is complete
- ✅ README.md is well-written (becomes your PyPI page)
- ✅ License is specified
- ✅ Version number follows semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Check if package name is available on PyPI: https://pypi.org/project/youtube-study-buddy/
- ✅ All tests pass: `uv run pytest`

#### 2. Build Distribution Files

```bash
# Build both source distribution (.tar.gz) and wheel (.whl)
uv build

# This creates:
# dist/youtube_study_buddy-0.1.0.tar.gz
# dist/youtube_study_buddy-0.1.0-py3-none-any.whl
```

#### 3. Create PyPI Account

1. Register at https://pypi.org
2. Enable two-factor authentication (required)
3. Generate an API token:
   - Go to Account Settings → API tokens
   - Create token with "Entire account" scope
   - Save the token (starts with `pypi-`)

#### 4. Publish to PyPI

```bash
# Install publishing tool
uv pip install twine

# Upload to PyPI
uv run twine upload dist/*

# You'll be prompted for:
# Username: __token__
# Password: pypi-YOUR_TOKEN_HERE
```

**Optional: Test on TestPyPI first**

```bash
# Upload to test.pypi.org first to verify everything works
uv run twine upload --repository testpypi dist/*

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ youtube-study-buddy
```

#### 5. Now Anyone Can Install

Once published, anyone can install your package:

```bash
# Using pip
pip install youtube-study-buddy

# Using UV
uv pip install youtube-study-buddy

# Now they can:
# 1. Run the CLI: youtube-study-buddy --help
# 2. Import the library: from yt_study_buddy import analyze
```

---

## Package Naming Conventions

Python packages have three different names:

### 1. PyPI Distribution Name
- Defined in `pyproject.toml`: `name = "youtube-study-buddy"`
- Used when installing: `pip install youtube-study-buddy`
- Convention: lowercase with hyphens

### 2. Import Name
- Directory name in `src/`: `yt_study_buddy`
- Used when importing: `import yt_study_buddy`
- Convention: lowercase with underscores (must be valid Python identifier)

### 3. CLI Command Name
- Defined in `[project.scripts]`: `youtube-study-buddy = "..."`
- Used when running: `youtube-study-buddy --help`
- Convention: lowercase with hyphens (matches distribution name)

**Example from this project**:
- **PyPI name**: `youtube-study-buddy`
- **Import name**: `yt_study_buddy`
- **CLI command**: `youtube-study-buddy`

---

## What Actually Gets Created When Someone Installs

When someone runs `pip install youtube-study-buddy`, they get:

### 1. Importable Module
```python
import yt_study_buddy
from yt_study_buddy.core import analyze
```

### 2. CLI Command
```bash
youtube-study-buddy --url https://youtube.com/watch?v=...
```

### 3. All Dependencies
- Automatically installed based on `pyproject.toml`
- No need to manually install `anthropic`, `youtube-transcript-api`, etc.

### 4. Compiled Wheel File
- `.whl` file contains all code and metadata
- No source code access needed (unless they install from source)
- Installed into site-packages directory

---

## Local Development vs Published Package

### Local Development (Current Workflow)

```bash
# Install in editable mode
uv sync

# Your code lives in: src/yt_study_buddy/
# Changes are immediately available
# No reinstall needed after code changes
```

**How it works**:
- UV creates a `.pth` file pointing to your source directory
- Python imports directly from `src/yt_study_buddy/`
- Edits to source are instantly reflected

### Published Package (After PyPI Upload)

```bash
# Install from PyPI
pip install youtube-study-buddy

# Code lives in: site-packages/yt_study_buddy/
# Code is copied from .whl file
# Changes require reinstalling package
```

**How it works**:
- Pip downloads `.whl` file from PyPI
- Extracts contents to site-packages directory
- Creates CLI executable in bin/ directory
- All dependencies installed automatically

**Both create the same end result**:
- ✅ Importable module: `import yt_study_buddy`
- ✅ CLI command: `youtube-study-buddy`
- ✅ All dependencies available

---

## Updating Published Packages

When you make changes and want to publish an update:

### 1. Update Version Number

Edit `pyproject.toml`:

```toml
[project]
version = "0.1.1"  # Increment version (was 0.1.0)
```

**Semantic Versioning**:
- `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)
- **MAJOR**: Breaking changes (1.0.0 → 2.0.0)
- **MINOR**: New features, backwards compatible (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes (1.0.0 → 1.0.1)

### 2. Rebuild and Republish

```bash
# Remove old builds
rm -rf dist/

# Build new version
uv build

# Upload to PyPI
uv run twine upload dist/*
```

### 3. Users Update

```bash
# Users get the update with:
pip install --upgrade youtube-study-buddy
```

---

## Summary

### How It All Works Together

1. **`pyproject.toml`** defines everything about your package
2. **`src/yt_study_buddy/`** contains your actual code
3. **`[project.scripts]`** creates CLI commands that point to functions in your code
4. **UV** installs it in "editable mode" so changes are immediate during development
5. **When published**, users get both:
   - Importable module: `import yt_study_buddy`
   - Executable command: `youtube-study-buddy`

### Package vs App

| Aspect | Package (Library) | App (Application) | This Project |
|--------|------------------|-------------------|--------------|
| Purpose | Code to import | Tool to run | Both |
| Import | `import yt_study_buddy` | N/A | ✅ |
| CLI | N/A | `youtube-study-buddy` | ✅ |
| Distribution | PyPI | Binary/PyPI | PyPI |

### Key Commands

```bash
# Development
uv sync                          # Install dependencies + editable package
uv run youtube-study-buddy       # Run CLI
uv run pytest                    # Run tests

# Building
uv build                         # Create distribution files

# Publishing
uv run twine upload dist/*       # Upload to PyPI

# Installing (after publishing)
pip install youtube-study-buddy  # Anyone can install
```

---

## Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Package Index](https://pypi.org/)
- [UV Documentation](https://docs.astral.sh/uv/)
- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)
- [Semantic Versioning](https://semver.org/)
