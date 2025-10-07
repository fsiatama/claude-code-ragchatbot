#!/bin/bash
# Run type checking with mypy

echo "Running mypy type checker..."
uv run mypy backend/ --exclude backend/tests/

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✓ No type errors found!"
else
    echo "✗ Type errors detected."
fi

exit $exit_code
