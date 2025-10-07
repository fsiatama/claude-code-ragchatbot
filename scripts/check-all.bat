@echo off
REM Run all quality checks (Windows version)

echo ================================
echo Running Code Quality Checks
echo ================================
echo.

echo 1. Formatting check...
uv run black --check backend/
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
echo ✓ Format check passed!
echo.

echo 2. Import sorting check...
uv run ruff check --select I backend/
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
echo ✓ Import check passed!
echo.

echo 3. Linting...
uv run ruff check backend/
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
echo ✓ Linting passed!
echo.

echo 4. Type checking...
uv run mypy backend/ --exclude backend/tests/
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
echo ✓ Type check passed!
echo.

echo ================================
echo All checks passed! ✨
echo ================================
