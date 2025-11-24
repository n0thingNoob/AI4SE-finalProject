@echo off
REM Windows test run script

echo ==========================================
echo Running Strategy Robustness Tests
echo ==========================================
python -m pytest tests\test_generated_strategy.py -v

echo.
echo ==========================================
echo Running Static Code Quality Checks
echo ==========================================

REM Ruff check
where ruff >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Running Ruff...
    ruff check strategy\ tests\
) else (
    echo Ruff not installed, skipping
)

REM Bandit security check (optional)
where bandit >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Running Bandit...
    bandit -r strategy\ -f json -o bandit-report.json
    echo Bandit report saved to bandit-report.json
) else (
    echo Bandit not installed, skipping
)

echo.
echo ==========================================
echo Tests Completed
echo ==========================================
