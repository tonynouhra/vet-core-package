# Vet Core Package

A foundational Python package providing shared data models, database utilities, and validation schemas for the veterinary clinic platform.

[![PyPI version](https://badge.fury.io/py/vet-core.svg)](https://badge.fury.io/py/vet-core)
[![Python versions](https://img.shields.io/pypi/pyversions/vet-core.svg)](https://pypi.org/project/vet-core/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/vetclinic/vet-core/workflows/CI/badge.svg)](https://github.com/vetclinic/vet-core/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/vetclinic/vet-core/branch/main/graph/badge.svg)](https://codecov.io/gh/vetclinic/vet-core)
[![Security](https://github.com/vetclinic/vet-core/workflows/Code%20Quality/badge.svg)](https://github.com/vetclinic/vet-core/actions/workflows/code-quality.yml)

## Overview

The `vet-core` package serves as the single source of truth for data structures across the distributed veterinary clinic platform. It provides a comprehensive foundation for building veterinary management applications with consistent data models, validation, and database operations.

### Key Benefits

- **Consistency**: Unified data models across all services
- **Type Safety**: Full type hints and Pydantic validation
- **Performance**: Async SQLAlchemy 2.0 with optimized queries
- **Reliability**: Comprehensive error handling and retry mechanisms
- **Developer Experience**: Rich documentation and examples

## Features

### 🗃️ SQLAlchemy Models
Comprehensive data models for veterinary entities with:
- **Users**: Multi-role support (pet owners, veterinarians, admins)
- **Pets**: Complete pet profiles with medical history
- **Appointments**: Flexible scheduling system
- **Clinics**: Location and service management
- **Veterinarians**: Professional profiles and availability

### ✅ Pydantic Schemas
Request/response validation and serialization with:
- Create, update, and response schemas for all entities
- Custom validators for business rules
- Nested schemas for complex data structures
- Automatic OpenAPI documentation support

### 🔄 Database Utilities
Production-ready database management:
- Async SQLAlchemy engine configuration
- Connection pooling and health checks
- Transaction management with context managers
- Retry mechanisms for transient failures
- Migration support through Alembic

### 🛠️ Helper Functions
Common utilities for:
- Timezone-aware datetime handling
- Data validation and sanitization
- Configuration management
- Error formatting and logging

### 🧪 Testing Support
Development and testing utilities:
- Factory classes for test data generation
- Database fixtures and cleanup utilities
- Mock data generators
- Integration test helpers

## Installation

### Basic Installation

```bash
pip install vet-core
```

### Development Installation

```bash
pip install vet-core[dev]
```

### Documentation Only

```bash
pip install vet-core[docs]
```

## Quick Start

### Basic Usage

```python
import asyncio
from vet_core import get_session, User, Pet, UserCreate, PetCreate
from vet_core.models import UserRole, PetSpecies

async def main():
    # Create and validate user data
    user_data = UserCreate(
        email="owner@example.com",
        first_name="John",
        last_name="Doe",
        role=UserRole.PET_OWNER
    )
    
    # Save to database
    async with get_session() as session:
        user = User(**user_data.model_dump())
        session.add(user)
        await session.commit()
        
        # Create a pet for the user
        pet_data = PetCreate(
            owner_id=user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            breed="Golden Retriever"
        )
        
        pet = Pet(**pet_data.model_dump())
        session.add(pet)
        await session.commit()
        
        print(f"Created user {user.email} with pet {pet.name}")

asyncio.run(main())
```

### Database Configuration

```python
import os
from vet_core import create_engine

# Configure database connection
database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/vetdb")
engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)
```

### Advanced Queries

```python
from sqlalchemy import select, func
from vet_core import get_session, Pet, Appointment, User

async def get_pet_statistics():
    async with get_session() as session:
        # Complex query with joins and aggregations
        stmt = (
            select(
                User.first_name,
                User.last_name,
                func.count(Pet.id).label('pet_count'),
                func.count(Appointment.id).label('appointment_count')
            )
            .join(Pet, Pet.owner_id == User.id)
            .outerjoin(Appointment, Appointment.pet_id == Pet.id)
            .group_by(User.id, User.first_name, User.last_name)
            .order_by(func.count(Pet.id).desc())
        )
        
        result = await session.execute(stmt)
        return result.all()
```

## Examples

The package includes comprehensive examples in the `examples/` directory:

- **[basic_usage_example.py](examples/basic_usage_example.py)**: Core functionality and common patterns
- **[advanced_patterns_example.py](examples/advanced_patterns_example.py)**: Complex queries, bulk operations, and optimization
- **[session_management_example.py](examples/session_management_example.py)**: Database session and connection management
- **[exception_handling_example.py](examples/exception_handling_example.py)**: Error handling and retry mechanisms

### Running Examples

```bash
# Set up your database connection
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/vetdb"

# Run basic examples
python examples/basic_usage_example.py

# Run advanced patterns
python examples/advanced_patterns_example.py
```

## API Reference

### Core Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `User` | User accounts with role-based access | `email`, `role`, `preferences` |
| `Pet` | Pet profiles with medical history | `name`, `species`, `medical_history` |
| `Appointment` | Appointment scheduling | `scheduled_at`, `service_type`, `status` |
| `Clinic` | Veterinary clinic information | `name`, `location`, `operating_hours` |
| `Veterinarian` | Veterinarian profiles | `license_number`, `specializations` |

### Database Operations

```python
from vet_core import get_session, get_transaction

# Read operations
async with get_session() as session:
    result = await session.execute(select(User))
    users = result.scalars().all()

# Write operations with automatic transaction management
async with get_transaction() as session:
    user = User(email="new@example.com")
    session.add(user)
    # Automatically committed on success, rolled back on error
```

### Schema Validation

```python
from vet_core.schemas import UserCreate, UserResponse

# Input validation
try:
    user_data = UserCreate(
        email="invalid-email",  # Will raise ValidationException
        first_name="John"
    )
except ValidationException as e:
    print(f"Validation errors: {e.validation_errors}")

# Response serialization
user_response = UserResponse.model_validate(user_instance)
```

## Requirements

- **Python**: 3.11 or higher
- **Database**: PostgreSQL 13 or higher
- **Dependencies**:
  - SQLAlchemy 2.0+
  - Pydantic 2.5+
  - asyncpg 0.29+
  - Alembic 1.13+

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/vetclinic/vet-core.git
cd vet-core

# Install in development mode
pip install -e .[dev]

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Database Setup

```bash
# Start PostgreSQL (using Docker)
docker run --name postgres-vet \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=vet_clinic_dev \
  -p 5432:5432 -d postgres:15

# Set environment variable
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/vet_clinic_dev"

# Run migrations
alembic upgrade head
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vet_core --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m database      # Database tests only

# Run tests with different Python versions
tox
```

### Code Quality

The project maintains high code quality standards:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Run all quality checks
pre-commit run --all-files
```

### CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment:

#### Automated Testing
- **CI Workflow**: Runs on every push and pull request
  - Tests across Python 3.11 and 3.12
  - PostgreSQL compatibility testing (versions 13-15)
  - Code quality checks (linting, formatting, type checking)
  - Security scanning (Bandit, Safety, pip-audit)
  - Coverage reporting with Codecov integration

#### Release Management
- **Automated Releases**: Triggered by version tags
  - Pre-release testing on TestPyPI
  - Automated PyPI publishing for stable releases
  - GitHub release creation with changelog
  - Cross-platform installation validation

#### Code Quality Monitoring
- **Daily Quality Checks**: Automated code quality monitoring
  - Security vulnerability scanning
  - Dependency health checks
  - Performance benchmarking
  - Documentation validation

#### Version Management
```bash
# Bump version using GitHub Actions
# Go to Actions → Version Bump → Run workflow
# Select version type: patch, minor, major, or prerelease

# Or manually tag a release
git tag v1.0.0
git push origin v1.0.0
```

### Building Documentation

```bash
# Install documentation dependencies
pip install vet-core[docs]

# Build documentation
cd docs/
make html

# Serve documentation locally
python -m http.server 8000 -d _build/html/
```

## Migration Guide

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new field to User model"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Version Compatibility

| vet-core Version | Python | SQLAlchemy | Pydantic |
|------------------|--------|------------|----------|
| 0.1.x | 3.11+ | 2.0+ | 2.5+ |

## Performance Considerations

### Connection Pooling

```python
# Optimize connection pool for your workload
engine = create_engine(
    database_url,
    pool_size=20,        # Base pool size
    max_overflow=30,     # Additional connections
    pool_timeout=30,     # Connection timeout
    pool_recycle=3600,   # Recycle connections hourly
    pool_pre_ping=True   # Validate connections
)
```

### Query Optimization

```python
# Use eager loading to avoid N+1 queries
from sqlalchemy.orm import selectinload, joinedload

stmt = (
    select(User)
    .options(
        selectinload(User.pets),           # Batch load pets
        joinedload(User.clinic)            # Join load clinic
    )
)
```

## Security Considerations

- **Input Validation**: All inputs are validated through Pydantic schemas
- **SQL Injection**: Protected by SQLAlchemy's parameterized queries
- **Sensitive Data**: Automatic sanitization in error messages and logs
- **Connection Security**: Support for SSL/TLS database connections

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Ensure all tests pass: `pytest`
5. Run code quality checks: `pre-commit run --all-files`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Reporting Issues

Please report issues on our [GitHub Issues](https://github.com/vetclinic/vet-core/issues) page.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed list of changes and version history.

## Support

- **Documentation**: [vet-core.readthedocs.io](https://vet-core.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/vetclinic/vet-core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/vetclinic/vet-core/discussions)
- **Email**: dev@vetclinic.com

---

Made with ❤️ by the Vet Clinic Platform Team