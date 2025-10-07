#!/bin/bash
# Run all quality checks

set -e

echo "================================"
echo "Running Code Quality Checks"
echo "================================"
echo ""

echo "1. Formatting check..."
uv run black --check backend/
echo "✓ Format check passed!"
echo ""

echo "2. Import sorting check..."
uv run ruff check --select I backend/
echo "✓ Import check passed!"
echo ""

echo "3. Linting..."
uv run ruff check backend/
echo "✓ Linting passed!"
echo ""

echo "4. Type checking..."
uv run mypy backend/ --exclude backend/tests/
echo "✓ Type check passed!"
echo ""

echo "================================"
echo "All checks passed! ✨"
echo "================================"
