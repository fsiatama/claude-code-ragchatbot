#!/bin/bash
# Run linting checks with ruff

echo "Running ruff linter..."
uv run ruff check backend/

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✓ No linting issues found!"
else
    echo "✗ Linting issues detected. Run './scripts/format.sh' to auto-fix some issues."
fi

exit $exit_code
