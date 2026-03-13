@echo off
echo [LogicHive] Starting Quality Verification (GIGO Shield)...

echo.
echo 1. Checking Dependencies...
uv pip install -e .

echo.
echo 2. Running Ruff (Linter/Formatter)...
uv run ruff check . --fix
uv run ruff format .

echo.
echo 3. Running Mypy (Type Check)...
uv run mypy src/ --ignore-missing-imports

echo.
echo [LogicHive] Verification Complete.
pause
