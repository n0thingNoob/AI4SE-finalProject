# Strategy Test Framework

## Directory Structure

```
tests/
├── __init__.py
├── framework_stub.py          # Stub implementation of framework APIs
├── strategy_loader.py          # Strategy discovery and loading module
├── test_data_generator.py      # Test data generator
├── robustness_tests.py         # Robustness test module
├── code_quality_scorer.py     # Code quality and robustness scoring
├── test_generated_strategy.py  # Main test file
├── run_tests.sh               # Linux/Mac test script
└── run_tests.bat              # Windows test script
```

## Usage

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Tests

#### Method 1: Direct Python Script

```bash
python tests/test_generated_strategy.py
```

#### Method 2: Using pytest

```bash
pytest tests/test_generated_strategy.py -v
```

#### Method 3: Using Test Scripts

**Windows:**
```cmd
tests\run_tests.bat
```

**Linux/Mac:**
```bash
chmod +x tests/run_tests.sh
./tests/run_tests.sh
```

### 3. Run Static Code Quality Checks

#### Ruff (Recommended)

```bash
ruff check strategy/ tests/
```

#### Bandit (Security Check, Optional)

```bash
bandit -r strategy/ -f json -o bandit-report.json
```

## Test Content

1. **initialize() test**: Verify strategy initialization works correctly
2. **Boundary tests**: Test strategy behavior under boundary conditions (None/NaN/Inf/extreme values)
3. **Random tests**: Test strategy robustness with random data
4. **Code Quality Scoring**: Evaluate code quality and robustness with detailed scores

## Scoring System

The test framework includes a comprehensive scoring system that evaluates:

### Robustness Score (0-100)
- Based on test pass rates for boundary and random tests
- Weighted: 60% boundary tests, 40% random tests

### Code Quality Score (0-100)
Evaluates five dimensions:
- **Structure** (20%): Code organization, required methods
- **Error Handling** (25%): Try-except blocks, None checks
- **Documentation** (15%): Docstrings and comments
- **Complexity** (15%): Cyclomatic complexity
- **Best Practices** (25%): Python conventions, code style

### Overall Score
- Weighted average: 40% Robustness + 60% Code Quality
- Grade assignment: A (≥90), B (≥80), C (≥70), D (≥60), F (<60)

## Configuration

- `pyproject.toml`: Ruff and Pylint configuration
- `requirements.txt`: Python dependencies
