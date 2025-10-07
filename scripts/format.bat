@echo off
REM Format code with black (Windows version)

echo Formatting code with black...
uv run black backend/

echo Sorting imports with ruff...
uv run ruff check --select I --fix backend/

echo Done! ✨
