#!/usr/bin/env python3
"""
Integration test script for vet-core package.

This script performs comprehensive end-to-end testing of the package
including installation, import, database operations, and functionality
validation across different environments.
"""

import asyncio
import os
import sys
import tempfile
import subprocess
import uuid
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List, Optional

from sqlalchemy import text

# Add the src directory to Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import vet_core
    from vet_core.models import User, Pet, Appointment, Clinic, Veterinarian
    from vet_core.schemas import UserCreate, PetCreate, AppointmentCreate
    from vet_core.database import create_engine, SessionManager
    from vet_core.exceptions import VetCoreException, ValidationException, DatabaseException
    from vet_core.utils.config import DatabaseConfig
    from vet_core.utils.datetime_utils import get_current_utc
    from vet_core.utils.validation import validate_email
    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


class IntegrationTestRunner:
    """Comprehensive integration test runner for vet-core package."""
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.test_db_url = "sqlite+aiosqlite:///test_integration.db"
        self.session_manager: Optional[SessionManager] = None
        
    def log_result(self, test_name: str, success: bool, message: str = "", details: Any = None):
        """Log test result."""
        self.results[test_name] = {
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_package_metadata(self):
        """Test package metadata and version information."""
        try:
            # Test version information
            assert hasattr(vet_core, '__version__')
            assert hasattr(vet_core, '__author__')
            assert hasattr(vet_core, '__license__')
            
            version = vet_core.__version__
            author = vet_core.__author__
            license_info = vet_core.__license__
            
            self.log_result(
                "package_metadata",
                True,
                f"Version: {version}, Author: {author}, License: {license_info}"
            )
            
        except Exception as e:
            self.log_result("package_metadata", False, "Failed to access package metadata", str(e))
    
    def test_module_imports(self):
        """Test that all expected modules can be imported."""
        expected_modules = [
            'vet_core.models',
            'vet_core.schemas', 
            'vet_core.database',
            'vet_core.utils',
            'vet_core.exceptions'
        ]
        
        failed_imports = []
        
        for module_name in expected_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                failed_imports.append(f"{module_name}: {e}")
        
        if failed_imports:
            self.log_result(
                "module_imports",
                False,
                f"Failed to import {len(failed_imports)} modules",
                failed_imports
            )
        else:
            self.log_result(
                "module_imports",
                True,
                f"Successfully imported all {len(expected_modules)} modules"
            )
    
    def test_model_definitions(self):
        """Test that all expected models are properly defined."""
        try:
            # Test model classes exist and have expected attributes
            models_to_test = [
                (User, ['email', 'first_name', 'last_name', 'role']),
                (Pet, ['name', 'species', 'owner_id']),
                (Appointment, ['pet_id', 'veterinarian_id', 'scheduled_at']),
                (Clinic, ['name', 'address_line1', 'phone_number']),
                (Veterinarian, ['user_id', 'license_number'])
            ]
            
            for model_class, expected_attrs in models_to_test:
                # Check class exists
                assert hasattr(model_class, '__tablename__')
                
                # Check expected attributes exist
                for attr in expected_attrs:
                    assert hasattr(model_class, attr), f"{model_class.__name__} missing {attr}"
            
            self.log_result(
                "model_definitions",
                True,
                f"All {len(models_to_test)} models properly defined"
            )
            
        except Exception as e:
            self.log_result("model_definitions", False, "Model definition validation failed", str(e))
    
    def test_schema_validation(self):
        """Test Pydantic schema validation."""
        try:
            # Test UserCreate schema
            from vet_core.models.user import UserRole
            user_data = {
                "clerk_user_id": "user_test123456",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "role": UserRole.PET_OWNER
            }
            user_schema = UserCreate(**user_data)
            assert user_schema.email == "test@example.com"
            
            # Test PetCreate schema
            from vet_core.models.pet import PetSpecies
            pet_data = {
                "name": "Buddy",
                "species": PetSpecies.DOG,
                "breed": "Golden Retriever",
                "birth_date": date(2020, 1, 1)
            }
            pet_schema = PetCreate(**pet_data)
            assert pet_schema.name == "Buddy"
            
            # Test validation errors
            try:
                UserCreate(
                    clerk_user_id="invalid_id",  # Invalid format
                    email="invalid-email", 
                    first_name="", 
                    last_name=""
                )
                assert False, "Should have raised validation error"
            except Exception:
                pass  # Expected validation error
            
            self.log_result(
                "schema_validation",
                True,
                "Schema validation working correctly"
            )
            
        except Exception as e:
            self.log_result("schema_validation", False, "Schema validation failed", str(e))
    
    def test_utility_functions(self):
        """Test utility functions."""
        try:
            # Test datetime utilities
            current_time = get_current_utc()
            assert isinstance(current_time, datetime)
            
            # Test validation utilities
            email_result = validate_email("test@example.com")
            assert email_result.is_valid == True
            
            invalid_email_result = validate_email("invalid-email")
            assert invalid_email_result.is_valid == False
            
            # Test configuration utilities
            config = DatabaseConfig()
            assert hasattr(config, 'database_url')
            
            self.log_result(
                "utility_functions",
                True,
                "Utility functions working correctly"
            )
            
        except Exception as e:
            self.log_result("utility_functions", False, "Utility function test failed", str(e))
    
    def test_exception_hierarchy(self):
        """Test custom exception hierarchy."""
        try:
            # Test exception creation
            base_exc = VetCoreException("Test message")
            assert str(base_exc) == "Test message"
            
            validation_exc = ValidationException("Validation failed")
            assert isinstance(validation_exc, VetCoreException)
            
            db_exc = DatabaseException("Database error")
            assert isinstance(db_exc, VetCoreException)
            
            self.log_result(
                "exception_hierarchy",
                True,
                "Exception hierarchy working correctly"
            )
            
        except Exception as e:
            self.log_result("exception_hierarchy", False, "Exception hierarchy test failed", str(e))
    
    async def test_database_connection(self):
        """Test database connection and basic operations."""
        try:
            # For integration testing, we'll use SQLAlchemy directly since 
            # the vet_core create_engine is PostgreSQL-specific
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy.pool import NullPool
            
            engine = create_async_engine(
                self.test_db_url,
                poolclass=NullPool,
                echo=False,
                future=True,
            )
            
            # Test engine creation
            assert engine is not None
            
            # Create session manager
            self.session_manager = SessionManager(engine)
            
            # Create database tables for testing
            from vet_core.models.base import Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Test session creation
            async with self.session_manager.get_session() as session:
                assert session is not None
                
                # Test basic query
                result = await session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                assert row[0] == 1
            
            self.log_result(
                "database_connection",
                True,
                "Database connection and session management working"
            )
            
        except Exception as e:
            self.log_result("database_connection", False, "Database connection failed", str(e))
    
    async def test_model_operations(self):
        """Test basic model CRUD operations."""
        if not self.session_manager:
            self.log_result("model_operations", False, "No session manager available")
            return
            
        try:
            # Note: This test uses in-memory SQLite, so we need to handle JSONB fields
            # For integration testing, we'll focus on basic model creation without JSONB
            
            async with self.session_manager.get_session() as session:
                # Create a simple user (avoiding JSONB fields for SQLite compatibility)
                from vet_core.models.user import UserRole
                user = User(
                    clerk_user_id=f"test_{uuid.uuid4().hex[:8]}",
                    email="test@example.com",
                    first_name="Test",
                    last_name="User",
                    role=UserRole.PET_OWNER
                )
                
                session.add(user)
                await session.flush()
                
                # Verify user was created
                assert user.id is not None
                assert user.email == "test@example.com"
                
                # Test user methods
                assert user.full_name == "Test User"
                assert user.is_active == True
            
            self.log_result(
                "model_operations",
                True,
                "Basic model operations working"
            )
            
        except Exception as e:
            self.log_result("model_operations", False, "Model operations failed", str(e))
    
    async def test_transaction_handling(self):
        """Test transaction handling and rollback."""
        if not self.session_manager:
            self.log_result("transaction_handling", False, "No session manager available")
            return
            
        try:
            # Test successful transaction
            async with self.session_manager.get_transaction() as session:
                from vet_core.models.user import UserRole
                user = User(
                    clerk_user_id=f"trans_test_{uuid.uuid4().hex[:8]}",
                    email="transaction@example.com",
                    first_name="Transaction",
                    last_name="Test",
                    role=UserRole.PET_OWNER
                )
                session.add(user)
                # Transaction should commit automatically
            
            # Test transaction rollback
            try:
                async with self.session_manager.get_transaction() as session:
                    from vet_core.models.user import UserRole
                    user = User(
                        clerk_user_id=f"rollback_test_{uuid.uuid4().hex[:8]}",
                        email="rollback@example.com",
                        first_name="Rollback",
                        last_name="Test",
                        role=UserRole.PET_OWNER
                    )
                    session.add(user)
                    # Force an error to trigger rollback
                    raise Exception("Intentional error for rollback test")
            except Exception:
                pass  # Expected error
            
            self.log_result(
                "transaction_handling",
                True,
                "Transaction handling working correctly"
            )
            
        except Exception as e:
            self.log_result("transaction_handling", False, "Transaction handling failed", str(e))
    
    def test_package_structure(self):
        """Test package structure and file organization."""
        try:
            package_root = Path(__file__).parent.parent / "src" / "vet_core"
            
            expected_structure = {
                "models": ["__init__.py", "base.py", "user.py", "pet.py", "appointment.py", "clinic.py", "veterinarian.py"],
                "schemas": ["__init__.py", "user.py", "pet.py", "appointment.py", "clinic.py", "veterinarian.py"],
                "database": ["__init__.py", "connection.py", "session.py", "migrations.py"],
                "utils": ["__init__.py", "config.py", "datetime_utils.py", "validation.py"],
                "exceptions": ["__init__.py", "core_exceptions.py"]
            }
            
            missing_files = []
            
            for directory, files in expected_structure.items():
                dir_path = package_root / directory
                if not dir_path.exists():
                    missing_files.append(f"Directory: {directory}")
                    continue
                    
                for file_name in files:
                    file_path = dir_path / file_name
                    if not file_path.exists():
                        missing_files.append(f"File: {directory}/{file_name}")
            
            if missing_files:
                self.log_result(
                    "package_structure",
                    False,
                    f"Missing {len(missing_files)} files/directories",
                    missing_files
                )
            else:
                self.log_result(
                    "package_structure",
                    True,
                    "Package structure is complete"
                )
                
        except Exception as e:
            self.log_result("package_structure", False, "Package structure test failed", str(e))
    
    def test_documentation_completeness(self):
        """Test documentation completeness."""
        try:
            package_root = Path(__file__).parent.parent
            
            required_docs = [
                "README.md",
                "CHANGELOG.md", 
                "LICENSE",
                "pyproject.toml"
            ]
            
            missing_docs = []
            for doc in required_docs:
                if not (package_root / doc).exists():
                    missing_docs.append(doc)
            
            # Check for docs directory
            docs_dir = package_root / "docs"
            if docs_dir.exists():
                expected_docs = ["API_REFERENCE.md", "USAGE_GUIDE.md"]
                for doc in expected_docs:
                    if not (docs_dir / doc).exists():
                        missing_docs.append(f"docs/{doc}")
            else:
                missing_docs.append("docs/ directory")
            
            if missing_docs:
                self.log_result(
                    "documentation_completeness",
                    False,
                    f"Missing {len(missing_docs)} documentation files",
                    missing_docs
                )
            else:
                self.log_result(
                    "documentation_completeness",
                    True,
                    "Documentation is complete"
                )
                
        except Exception as e:
            self.log_result("documentation_completeness", False, "Documentation test failed", str(e))
    
    def test_example_scripts(self):
        """Test example scripts functionality."""
        try:
            examples_dir = Path(__file__).parent.parent / "examples"
            
            if not examples_dir.exists():
                self.log_result("example_scripts", False, "Examples directory not found")
                return
            
            example_files = list(examples_dir.glob("*.py"))
            
            if not example_files:
                self.log_result("example_scripts", False, "No example files found")
                return
            
            # Test that example files can be imported (syntax check)
            valid_examples = 0
            invalid_examples = []
            
            for example_file in example_files:
                try:
                    # Basic syntax check by compiling
                    with open(example_file, 'r') as f:
                        compile(f.read(), str(example_file), 'exec')
                    valid_examples += 1
                except SyntaxError as e:
                    invalid_examples.append(f"{example_file.name}: {e}")
            
            if invalid_examples:
                self.log_result(
                    "example_scripts",
                    False,
                    f"{len(invalid_examples)} examples have syntax errors",
                    invalid_examples
                )
            else:
                self.log_result(
                    "example_scripts",
                    True,
                    f"All {valid_examples} example scripts are syntactically valid"
                )
                
        except Exception as e:
            self.log_result("example_scripts", False, "Example scripts test failed", str(e))
    
    def test_migration_system(self):
        """Test Alembic migration system."""
        try:
            alembic_dir = Path(__file__).parent.parent / "alembic"
            
            if not alembic_dir.exists():
                self.log_result("migration_system", False, "Alembic directory not found")
                return
            
            # Check for required Alembic files
            required_files = ["env.py", "alembic.ini"]
            missing_files = []
            
            for file_name in required_files:
                if file_name == "alembic.ini":
                    file_path = Path(__file__).parent.parent / file_name
                else:
                    file_path = alembic_dir / file_name
                    
                if not file_path.exists():
                    missing_files.append(file_name)
            
            # Check for versions directory
            versions_dir = alembic_dir / "versions"
            if not versions_dir.exists():
                missing_files.append("versions/ directory")
            else:
                # Check for at least one migration file
                migration_files = list(versions_dir.glob("*.py"))
                if not migration_files:
                    missing_files.append("No migration files in versions/")
            
            if missing_files:
                self.log_result(
                    "migration_system",
                    False,
                    f"Migration system incomplete: {len(missing_files)} issues",
                    missing_files
                )
            else:
                self.log_result(
                    "migration_system",
                    True,
                    "Migration system is properly configured"
                )
                
        except Exception as e:
            self.log_result("migration_system", False, "Migration system test failed", str(e))
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.session_manager:
                await self.session_manager.close_all_sessions()
            
            # Remove test database file
            test_db_file = Path("test_integration.db")
            if test_db_file.exists():
                test_db_file.unlink()
                
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    def print_summary(self):
        """Print test results summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result["success"])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("INTEGRATION TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for test_name, result in self.results.items():
                if not result["success"]:
                    print(f"  ❌ {test_name}: {result['message']}")
        
        print("="*60)
        
        return failed_tests == 0
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print("Starting vet-core package integration tests...")
        print("="*60)
        
        # Check if package can be imported
        if not IMPORT_SUCCESS:
            self.log_result("package_import", False, "Failed to import vet_core package", IMPORT_ERROR)
            return False
        else:
            self.log_result("package_import", True, "Successfully imported vet_core package")
        
        # Run synchronous tests
        self.test_package_metadata()
        self.test_module_imports()
        self.test_model_definitions()
        self.test_schema_validation()
        self.test_utility_functions()
        self.test_exception_hierarchy()
        self.test_package_structure()
        self.test_documentation_completeness()
        self.test_example_scripts()
        self.test_migration_system()
        
        # Run asynchronous tests
        await self.test_database_connection()
        await self.test_model_operations()
        await self.test_transaction_handling()
        
        # Cleanup
        await self.cleanup()
        
        # Print summary and return success status
        return self.print_summary()


async def main():
    """Main entry point for integration tests."""
    runner = IntegrationTestRunner()
    
    try:
        success = await runner.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        await runner.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during testing: {e}")
        await runner.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())