@echo off
REM Run type checking with mypy (Windows version)

echo Running mypy type checker...
uv run mypy backend/ --exclude backend/tests/

if %ERRORLEVEL% EQU 0 (
    echo ✓ No type errors found!
) else (
    echo ✗ Type errors detected.
)

exit /b %ERRORLEVEL%
