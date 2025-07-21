# Database Migrations

This directory contains Alembic database migrations for the vet-core package.

## Overview

The migration system uses Alembic to manage database schema changes for the veterinary clinic platform. All core models (User, Pet, Appointment, Clinic, Veterinarian) are included in the initial migration.

## Files

- `alembic.ini` - Alembic configuration file
- `env.py` - Alembic environment configuration with async support
- `versions/` - Directory containing migration files
- `versions/001_initial_migration_with_all_core_models.py` - Initial migration with all core models

## Usage

### Running Migrations

To upgrade to the latest migration:
```bash
cd vet-core-package
python -m alembic upgrade head
```

To upgrade to a specific revision:
```bash
python -m alembic upgrade <revision_id>
```

### Creating New Migrations

To create a new migration with auto-generated changes:
```bash
python -m alembic revision --autogenerate -m "Description of changes"
```

To create an empty migration file:
```bash
python -m alembic revision -m "Description of changes"
```

### Migration Information

To see current migration status:
```bash
python -m alembic current
```

To see migration history:
```bash
python -m alembic history
```

### Downgrading

To downgrade to a previous revision:
```bash
python -m alembic downgrade <revision_id>
```

## Environment Variables

The migration system supports the following environment variables:

- `DATABASE_URL` - Complete database URL
- `DB_HOST` - Database host (default: localhost)
- `DB_PORT` - Database port (default: 5432)
- `DB_NAME` - Database name (default: vetcore)
- `DB_USER` - Database username (default: postgres)
- `DB_PASSWORD` - Database password

## Testing and Validation

### Validate Migration Setup
```bash
python scripts/validate_migration.py
```

### Test Migrations
```bash
python scripts/migration_test.py
```

### Test Specific Migration Features
```bash
# Test fresh migration
python scripts/migration_test.py --test fresh

# Test migration rollback
python scripts/migration_test.py --test rollback

# Test migration validation
python scripts/migration_test.py --test validation
```

## Migration Utilities

The package provides Python utilities for migration management:

```python
from vet_core.database import (
    MigrationManager,
    run_migrations_async,
    get_migration_status
)

# Create migration manager
manager = MigrationManager()

# Run migrations programmatically
await run_migrations_async(engine)

# Get migration status
status = get_migration_status()
```

## Database Schema

The initial migration creates the following tables:

### Core Tables
- `users` - User accounts with authentication integration
- `clinics` - Veterinary clinic information
- `veterinarians` - Veterinarian profiles and credentials
- `pets` - Pet information and medical history
- `appointments` - Appointment scheduling and management

### Enum Types
- `userrole` - User roles (pet_owner, veterinarian, etc.)
- `userstatus` - User account statuses
- `petspecies` - Pet species types
- `petgender` - Pet gender options
- `petsize` - Pet size categories
- `petstatus` - Pet status options
- `appointmentstatus` - Appointment statuses
- `servicetype` - Types of veterinary services
- `appointmentpriority` - Appointment priority levels
- `clinicstatus` - Clinic operational statuses
- `clinictype` - Types of veterinary clinics
- `veterinarianstatus` - Veterinarian employment statuses
- `licensestatus` - Veterinary license statuses
- `employmenttype` - Employment arrangement types

## Best Practices

1. **Always backup your database** before running migrations in production
2. **Test migrations** in a development environment first
3. **Review generated migrations** before applying them
4. **Use descriptive migration messages** for better tracking
5. **Keep migrations small and focused** on specific changes
6. **Don't edit existing migration files** - create new ones for changes

## Troubleshooting

### Common Issues

1. **Connection errors**: Check database URL and credentials
2. **Permission errors**: Ensure database user has necessary permissions
3. **Migration conflicts**: Use `alembic merge` to resolve conflicts
4. **Schema inconsistencies**: Use validation scripts to check consistency

### Getting Help

- Check the validation script output for detailed error information
- Review Alembic logs for migration execution details
- Use the migration test script to isolate issues
- Consult the Alembic documentation for advanced usage

## Development

When adding new models or modifying existing ones:

1. Update the model definitions in `src/vet_core/models/`
2. Generate a new migration: `alembic revision --autogenerate -m "Add new model"`
3. Review the generated migration file
4. Test the migration with the test script
5. Apply the migration: `alembic upgrade head`

## Production Deployment

For production deployments:

1. Backup the database
2. Run migration validation
3. Test migrations in staging environment
4. Apply migrations during maintenance window
5. Verify migration success
6. Monitor application functionality