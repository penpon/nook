#!/usr/bin/env python3
"""Fix unused variables by removing or prefixing with underscore."""

import re
from pathlib import Path

def fix_unused_mock_dedup(file_path: Path):
    """Remove unused mock_dedup variables that are not used."""
    content = file_path.read_text()

    # Pattern 1: mock_dedup = Mock() followed by immediate use
    # Keep these

    # Pattern 2: mock_dedup = Mock() not followed by any use
    # Remove these lines
    lines = content.split('\n')
    new_lines = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        # Check if this is an unused mock_dedup
        if 'mock_dedup = Mock()' in line:
            # Check the next few lines for usage
            has_usage = False
            for j in range(i + 1, min(i + 5, len(lines))):
                if 'mock_dedup.' in lines[j] or 'mock_load.return_value = mock_dedup' in lines[j]:
                    has_usage = True
                    break

            if not has_usage:
                # This is unused, skip it
                continue

        new_lines.append(line)

    file_path.write_text('\n'.join(new_lines))
    print(f"Fixed {file_path}")

def fix_unused_result(file_path: Path):
    """Prefix unused result variables with underscore."""
    content = file_path.read_text()

    # Find lines with "result = await service._retrieve_article"
    # where result is never used
    lines = content.split('\n')
    new_lines = []

    for i, line in enumerate(lines):
        if 'result = await service._retrieve_article' in line:
            # Check if result is used in subsequent lines
            has_usage = False
            for j in range(i + 1, min(i + 10, len(lines))):
                if re.search(r'\bresult\b', lines[j]) and 'result =' not in lines[j]:
                    has_usage = True
                    break

            if not has_usage:
                # Prefix with underscore
                line = line.replace('result = ', '_ = ')

        new_lines.append(line)

    file_path.write_text('\n'.join(new_lines))
    print(f"Fixed unused result in {file_path}")

def fix_unused_service(file_path: Path):
    """Prefix unused service variables with underscore."""
    content = file_path.read_text()

    # Pattern: service = TechFeed() inside pytest.raises
    content = re.sub(
        r'(\s+)(service) = (TechFeed\(\))',
        r'\1_ = \3  # noqa: F841',
        content
    )

    file_path.write_text(content)
    print(f"Fixed unused service in {file_path}")

def fix_imports(file_path: Path):
    """Fix import ordering using simple rules."""
    content = file_path.read_text()

    # Fix timezone.utc to datetime.UTC
    content = content.replace('tzinfo=timezone.utc', 'tzinfo=datetime.UTC')
    content = content.replace('timezone.utc', 'datetime.UTC')

    file_path.write_text(content)
    print(f"Fixed imports in {file_path}")

if __name__ == "__main__":
    # Fix test_tech_feed.py
    tech_feed_path = Path("tests/services/test_tech_feed.py")
    if tech_feed_path.exists():
        fix_unused_mock_dedup(tech_feed_path)
        fix_unused_result(tech_feed_path)
        fix_unused_service(tech_feed_path)

    # Fix test_zenn_explorer.py
    zenn_path = Path("tests/services/test_zenn_explorer.py")
    if zenn_path.exists():
        fix_imports(zenn_path)

    print("Done!")
