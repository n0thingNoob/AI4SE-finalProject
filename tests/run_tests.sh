#!/bin/bash
# Test run script (Linux/Mac)

set -e

echo "=========================================="
echo "Running Strategy Robustness Tests"
echo "=========================================="
python -m pytest tests/test_generated_strategy.py -v

echo ""
echo "=========================================="
echo "Running Static Code Quality Checks"
echo "=========================================="

# Ruff check
if command -v ruff &> /dev/null; then
    echo "Running Ruff..."
    ruff check strategy/ tests/
else
    echo "Ruff not installed, skipping"
fi

# Bandit security check (optional)
if command -v bandit &> /dev/null; then
    echo "Running Bandit..."
    bandit -r strategy/ -f json -o bandit-report.json || true
    echo "Bandit report saved to bandit-report.json"
else
    echo "Bandit not installed, skipping"
fi

echo ""
echo "=========================================="
echo "Tests Completed"
echo "=========================================="
