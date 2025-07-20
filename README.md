# Vet Core Package

A foundational Python package providing shared data models, database utilities, and validation schemas for the veterinary clinic platform.

## Overview

The `vet-core` package serves as the single source of truth for data structures across the distributed veterinary clinic platform. It includes SQLAlchemy models for core entities, Pydantic schemas for validation, database connection utilities, and helper functions that ensure consistency across all services.

## Features

- **SQLAlchemy Models**: Comprehensive data models for veterinary entities (Users, Pets, Appointments, Clinics, Veterinarians)
- **Pydantic Schemas**: Request/response validation and serialization schemas
- **Database Utilities**: Async SQLAlchemy engine configuration and session management
- **Helper Functions**: Common utilities for datetime handling, validation, and configuration
- **Migration Support**: Alembic integration for database schema management
- **Testing Utilities**: Factory classes and test fixtures for development

## Installation

```bash
pip install vet-core
```

For development dependencies:

```bash
pip install vet-core[dev]
```

## Quick Start

```python
from vet_core.models import User, Pet, Appointment
from vet_core.database import AsyncSessionLocal
from vet_core.schemas import UserCreate, PetCreate

# Example usage will be added as the package is implemented
```

## Requirements

- Python 3.11+
- PostgreSQL 13+
- SQLAlchemy 2.0+
- Pydantic 2.5+

## Development

### Setup

1. Clone the repository
2. Install development dependencies: `pip install -e .[dev]`
3. Set up pre-commit hooks: `pre-commit install`
4. Run tests: `pytest`

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vet_core

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Git hooks for quality checks

## Documentation

Full documentation is available at [vet-core.readthedocs.io](https://vet-core.readthedocs.io/)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code quality checks pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.