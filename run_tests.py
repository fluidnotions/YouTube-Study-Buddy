#!/usr/bin/env python3
"""
Test runner script for YouTube to Study Notes tool.
Provides convenient test execution with different options.
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print the result."""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print(f"\n✅ {description} - PASSED")
    else:
        print(f"\n❌ {description} - FAILED (exit code: {result.returncode})")

    return result.returncode == 0


def main():
    """Main test runner."""
    project_root = Path(__file__).parent
    os.chdir(project_root)

    print("YouTube to Study Notes - Test Runner")
    print("="*60)

    if len(sys.argv) < 2:
        print("""
Usage: python run_tests.py <option>

Options:
  unit        Run unit tests only (fast, no external dependencies)
  integration Run integration tests (may hit external APIs)
  all         Run all tests
  coverage    Run tests with coverage report
  debug       Run tests with debugging output
  specific    Run specific test file or function
  lint        Run code linting
  format      Run code formatting check

Examples:
  python run_tests.py unit
  python run_tests.py coverage
  python run_tests.py specific tests/test_video_processor.py::TestVideoProcessor::test_video_id_extraction
        """)
        sys.exit(1)

    option = sys.argv[1].lower()
    success = True

    if option == "unit":
        success = run_command([
            "python", "-m", "pytest",
            "tests/",
            "-m", "unit",
            "-v"
        ], "Unit Tests")

    elif option == "integration":
        success = run_command([
            "python", "-m", "pytest",
            "tests/",
            "-m", "integration",
            "-v"
        ], "Integration Tests")

    elif option == "all":
        # Run unit tests first
        unit_success = run_command([
            "python", "-m", "pytest",
            "tests/",
            "-m", "unit",
            "-v"
        ], "Unit Tests")

        # Then integration tests
        integration_success = run_command([
            "python", "-m", "pytest",
            "tests/",
            "-m", "integration",
            "-v"
        ], "Integration Tests")

        success = unit_success and integration_success

    elif option == "coverage":
        success = run_command([
            "python", "-m", "pytest",
            "tests/",
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term",
            "-v"
        ], "Coverage Tests")

        if success:
            print(f"\n📊 Coverage report generated in htmlcov/index.html")

    elif option == "debug":
        success = run_command([
            "python", "-m", "pytest",
            "tests/",
            "-v",
            "-s",
            "--tb=long",
            "--capture=no"
        ], "Debug Tests")

    elif option == "specific":
        if len(sys.argv) < 3:
            print("Error: Please specify test file or function")
            print("Example: python run_tests.py specific tests/test_video_processor.py")
            sys.exit(1)

        test_target = sys.argv[2]
        success = run_command([
            "python", "-m", "pytest",
            test_target,
            "-v",
            "-s"
        ], f"Specific Test: {test_target}")

    elif option == "lint":
        try:
            success = run_command([
                "python", "-m", "flake8",
                "src/",
                "tests/",
                "--max-line-length=100",
                "--ignore=E203,W503"
            ], "Code Linting")
        except FileNotFoundError:
            print("❌ flake8 not installed. Install with: pip install flake8")
            success = False

    elif option == "format":
        try:
            success = run_command([
                "python", "-m", "black",
                "--check",
                "--diff",
                "src/",
                "tests/"
            ], "Code Formatting Check")
        except FileNotFoundError:
            print("❌ black not installed. Install with: pip install black")
            success = False

    else:
        print(f"❌ Unknown option: {option}")
        sys.exit(1)

    # Final result
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("📝 To run tests in VSCode:")
        print("   1. Open Command Palette (Ctrl+Shift+P)")
        print("   2. Type 'Python: Configure Tests'")
        print("   3. Select 'pytest'")
        print("   4. Use Test Explorer in sidebar")
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔍 Check the output above for details")
        sys.exit(1)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()