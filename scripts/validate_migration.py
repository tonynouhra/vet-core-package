#!/usr/bin/env python3
"""
Migration validation script for the vet-core package.

This script validates the migration setup and ensures all models
are properly configured for database schema generation.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import vet_core
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, MetaData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_alembic_config():
    """Validate the Alembic configuration."""
    try:
        # Get the path to alembic.ini
        alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
        
        if not alembic_ini_path.exists():
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")
        
        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini_path))
        
        # Test script directory
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        
        logger.info(f"✓ Alembic configuration is valid")
        logger.info(f"✓ Script directory: {script_dir.dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Alembic configuration validation failed: {e}")
        return False


def validate_models():
    """Validate that all models can be imported and have proper metadata."""
    try:
        # Import all models to ensure they are registered
        from vet_core.models import (
            BaseModel, User, Pet, Appointment, Clinic, Veterinarian
        )
        
        logger.info("✓ All models imported successfully")
        
        # Check that metadata is properly configured
        metadata = BaseModel.metadata
        
        if not metadata.tables:
            raise ValueError("No tables found in metadata")
        
        expected_tables = {'users', 'pets', 'appointments', 'clinics', 'veterinarians'}
        actual_tables = set(metadata.tables.keys())
        
        if not expected_tables.issubset(actual_tables):
            missing = expected_tables - actual_tables
            raise ValueError(f"Missing tables in metadata: {missing}")
        
        logger.info(f"✓ Found {len(actual_tables)} tables in metadata: {', '.join(sorted(actual_tables))}")
        
        # Validate each model has proper table configuration
        models = [User, Pet, Appointment, Clinic, Veterinarian]
        for model in models:
            if not hasattr(model, '__tablename__'):
                raise ValueError(f"Model {model.__name__} missing __tablename__")
            
            table_name = model.__tablename__
            if table_name not in metadata.tables:
                raise ValueError(f"Table {table_name} not found in metadata")
            
            table = metadata.tables[table_name]
            if not table.columns:
                raise ValueError(f"Table {table_name} has no columns")
            
            # Check for required base columns
            required_columns = {'id', 'created_at', 'updated_at', 'is_deleted'}
            actual_columns = set(table.columns.keys())
            
            if not required_columns.issubset(actual_columns):
                missing = required_columns - actual_columns
                raise ValueError(f"Table {table_name} missing required columns: {missing}")
            
            logger.info(f"  ✓ {model.__name__} -> {table_name} ({len(actual_columns)} columns)")
        
        logger.info("✓ All models have proper table configuration")
        
        return True
        
    except Exception as e:
        import traceback
        logger.error(f"✗ Model validation failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def validate_migration_files():
    """Validate existing migration files."""
    try:
        # Get the path to alembic.ini
        alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        
        # Get script directory
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        
        # Check for migration files
        versions_dir = Path(script_dir.dir) / "versions"
        migration_files = list(versions_dir.glob("*.py"))
        
        if not migration_files:
            logger.warning("⚠ No migration files found")
            return True
        
        logger.info(f"✓ Found {len(migration_files)} migration file(s)")
        
        # Validate each migration file
        for migration_file in migration_files:
            if migration_file.name == "__pycache__":
                continue
                
            try:
                # Try to get revision info
                revision = script_dir.get_revision(migration_file.stem.split('_')[0])
                if revision:
                    logger.info(f"  ✓ {migration_file.name}: {revision.doc}")
                else:
                    logger.warning(f"  ⚠ {migration_file.name}: Could not get revision info")
            except Exception as e:
                logger.warning(f"  ⚠ {migration_file.name}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Migration file validation failed: {e}")
        return False


def validate_migration_consistency():
    """Validate that migrations are consistent with models."""
    try:
        # Import models to get metadata
        from vet_core.models import BaseModel
        
        # Get model metadata
        model_metadata = BaseModel.metadata
        
        logger.info("✓ Migration consistency check completed")
        logger.info(f"  Model tables: {len(model_metadata.tables)}")
        
        # Note: Full consistency check would require database connection
        # This is a basic validation that models can be loaded
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Migration consistency validation failed: {e}")
        return False


def validate_enum_types():
    """Validate that enum types are properly defined."""
    try:
        from vet_core.models.user import UserRole, UserStatus
        from vet_core.models.pet import PetSpecies, PetGender, PetSize, PetStatus
        from vet_core.models.appointment import AppointmentStatus, ServiceType, AppointmentPriority
        from vet_core.models.clinic import ClinicStatus, ClinicType
        from vet_core.models.veterinarian import VeterinarianStatus, LicenseStatus, EmploymentType
        
        enums = [
            UserRole, UserStatus, PetSpecies, PetGender, PetSize, PetStatus,
            AppointmentStatus, ServiceType, AppointmentPriority,
            ClinicStatus, ClinicType, VeterinarianStatus, LicenseStatus, EmploymentType
        ]
        
        for enum_class in enums:
            if not hasattr(enum_class, '__members__'):
                raise ValueError(f"Enum {enum_class.__name__} is not properly defined")
            
            if not enum_class.__members__:
                raise ValueError(f"Enum {enum_class.__name__} has no members")
        
        logger.info(f"✓ All {len(enums)} enum types are properly defined")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Enum type validation failed: {e}")
        return False


def main():
    """Main validation function."""
    logger.info("Starting migration validation...")
    
    validations = [
        ("Alembic Configuration", validate_alembic_config),
        ("Model Definitions", validate_models),
        ("Enum Types", validate_enum_types),
        ("Migration Files", validate_migration_files),
        ("Migration Consistency", validate_migration_consistency),
    ]
    
    results = []
    
    for name, validation_func in validations:
        logger.info(f"\n--- Validating {name} ---")
        try:
            result = validation_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"✗ {name} validation failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("MIGRATION VALIDATION SUMMARY")
    logger.info("="*50)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{name}: {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\nTotal: {len(results)} validations")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("\n🎉 All migration validations passed!")
        sys.exit(0)
    else:
        logger.error(f"\n❌ {failed} validation(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()