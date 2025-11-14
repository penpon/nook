#!/usr/bin/env python3
"""Script to fix lint issues automatically."""

import subprocess
import sys

def main():
    """Run ruff to fix lint issues."""
    print("Running ruff with --fix and --unsafe-fixes...")

    result = subprocess.run(
        ["python", "-m", "ruff", "check", "--fix", "--unsafe-fixes", "nook/", "tests/"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
