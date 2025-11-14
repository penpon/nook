#!/usr/bin/env python3
"""Script to fix common lint issues."""

import subprocess
import sys


def run_ruff_fix():
    """Run ruff with --fix and --unsafe-fixes flags."""
    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", "--fix", "--unsafe-fixes", "nook/", "tests/"],
            capture_output=True,
            text=True,
            timeout=60
        )
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return result.returncode
    except Exception as e:
        print(f"Error running ruff: {e}", file=sys.stderr)
        return 1


def run_black():
    """Run black formatter."""
    try:
        result = subprocess.run(
            ["python", "-m", "black", "nook/", "tests/"],
            capture_output=True,
            text=True,
            timeout=60
        )
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return result.returncode
    except Exception as e:
        print(f"Error running black: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    print("Running Black formatter...")
    black_ret = run_black()

    print("\nRunning Ruff with auto-fix...")
    ruff_ret = run_ruff_fix()

    sys.exit(max(black_ret, ruff_ret))
