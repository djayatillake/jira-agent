# Error Resolution Learnings

This directory contains learnings from resolved errors that don't fit into CI failures or code patterns.

## Categories

- **syntax-error**: Syntax and parsing errors
- **import-error**: Module import issues
- **runtime-error**: Runtime exceptions
- **configuration**: Configuration and setup issues

## Common Resolutions

### Import Errors

Typical causes and fixes:
- Missing dependency: Add to requirements/pyproject.toml
- Circular import: Restructure imports or use lazy loading
- Path issues: Check PYTHONPATH or package structure

### Configuration Errors

Common issues:
- Missing environment variables
- Invalid YAML/JSON syntax
- Schema validation failures
