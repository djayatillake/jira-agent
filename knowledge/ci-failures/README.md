# CI Failure Learnings

This directory contains learnings from resolved CI/CD failures.

## Categories

- **pre-commit**: Formatting, linting, and hook failures
- **dbt-compile**: dbt model compilation errors
- **pytest**: Test failures and fixes
- **mypy**: Type checking issues
- **ruff/black/isort**: Code formatting issues

## Common Patterns

### Pre-commit Failures

Most pre-commit failures can be resolved by:
1. Running `pre-commit run --all-files`
2. Committing the auto-fixed changes

### dbt Compile Failures

Common causes:
- Missing source definitions
- Invalid SQL syntax
- Reference to non-existent models
- Schema mismatches

### Test Failures

Typical resolutions:
- Update test fixtures
- Fix assertion logic
- Mock external dependencies
