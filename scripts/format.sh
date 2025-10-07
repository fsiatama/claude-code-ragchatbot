#!/bin/bash
# Format code with black

echo "Formatting code with black..."
uv run black backend/

echo "Sorting imports with ruff..."
uv run ruff check --select I --fix backend/

echo "Done! ✨"
