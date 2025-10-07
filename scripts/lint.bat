@echo off
REM Run linting checks with ruff (Windows version)

echo Running ruff linter...
uv run ruff check backend/

if %ERRORLEVEL% EQU 0 (
    echo ✓ No linting issues found!
) else (
    echo ✗ Linting issues detected. Run 'scripts\format.bat' to auto-fix some issues.
)

exit /b %ERRORLEVEL%
