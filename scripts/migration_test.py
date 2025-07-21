#!/usr/bin/env python3
"""
Migration testing script for the vet-core package.

This script provides utilities for testing database migrations,
including setup, teardown, and validation of migration states.
"""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Add the src directory to the path so we can import vet_core
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vet_core.database.connection import create_engine, test_connection, close_engine
from vet_core.database.migrations import MigrationManager, run_migrations_async
from vet_core.utils.config import EnvironmentConfig
from vet_core.exceptions import MigrationException, DatabaseException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationTester:
    """Test utility for database migrations."""
    
    def __init__(self, test_database_url: Optional[str] = None):
        """
        Initialize the migration tester.
        
        Args:
            test_database_url: Optional test database URL
        """
        self.test_database_url = test_database_url or self._get_test_database_url()
        self.engine = None
        self.manager = None
    
    def _get_test_database_url(self) -> str:
        """Get test database URL from environment or create a default."""
        # Try to get test database URL from environment
        test_url = EnvironmentConfig.get_str("TEST_DATABASE_URL")
        
        if test_url:
            return test_url
        
        # Build test database URL from components
        host = EnvironmentConfig.get_str("DB_HOST", "localhost")
        port = EnvironmentConfig.get_int("DB_PORT", 5432)
        username = EnvironmentConfig.get_str("DB_USER", "postgres")
        password = EnvironmentConfig.get_str("DB_PASSWORD", "")
        
        # Use a test-specific database name
        test_db_name = "vetcore_test"
        
        if password:
            return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{test_db_name}"
        else:
            return f"postgresql+asyncpg://{username}@{host}:{port}/{test_db_name}"
    
    async def setup(self) -> None:
        """Set up the test environment."""
        logger.info("Setting up migration test environment")
        
        # Create database engine
        self.engine = create_engine(
            self.test_database_url,
            pool_size=1,
            max_overflow=0,
            echo=False
        )
        
        # Test connection
        if not await test_connection(self.engine):
            raise DatabaseException("Could not connect to test database")
        
        # Create migration manager
        self.manager = MigrationManager(database_url=self.test_database_url)
        
        logger.info("Migration test environment set up successfully")
    
    async def teardown(self) -> None:
        """Tear down the test environment."""
        logger.info("Tearing down migration test environment")
        
        if self.engine:
            await close_engine(self.engine)
        
        logger.info("Migration test environment torn down")
    
    async def test_fresh_migration(self) -> Dict[str, Any]:
        """
        Test migration on a fresh database.
        
        Returns:
            Test results dictionary
        """
        logger.info("Testing fresh migration")
        
        try:
            # Run migrations from scratch
            result = await run_migrations_async(
                self.engine,
                target_revision="head",
                validate_before=False
            )
            
            # Validate final state
            validation = self.manager.validate_migration_state()
            
            test_result = {
                "test_name": "fresh_migration",
                "success": result["success"] and validation["valid"],
                "migration_result": result,
                "validation_result": validation,
                "errors": result.get("errors", [])
            }
            
            if not validation["valid"]:
                test_result["errors"].extend(validation.get("issues", []))
            
            logger.info(f"Fresh migration test completed: {'PASSED' if test_result['success'] else 'FAILED'}")
            return test_result
            
        except Exception as e:
            logger.error(f"Fresh migration test failed: {e}")
            return {
                "test_name": "fresh_migration",
                "success": False,
                "error": str(e),
                "migration_result": None,
                "validation_result": None
            }
    
    async def test_migration_rollback(self) -> Dict[str, Any]:
        """
        Test migration rollback functionality.
        
        Returns:
            Test results dictionary
        """
        logger.info("Testing migration rollback")
        
        try:
            # First, ensure we're at head
            await run_migrations_async(self.engine, "head")
            
            # Get current revision
            current_revision = self.manager.get_current_revision()
            
            if not current_revision:
                return {
                    "test_name": "migration_rollback",
                    "success": False,
                    "error": "No current revision found",
                    "skipped": True
                }
            
            # Get migration history to find a previous revision
            history = self.manager.get_migration_history()
            
            if len(history) < 2:
                return {
                    "test_name": "migration_rollback",
                    "success": False,
                    "error": "Not enough migrations for rollback test",
                    "skipped": True
                }
            
            # Find the previous revision
            previous_revision = None
            for i, revision in enumerate(history):
                if revision["revision"] == current_revision and i + 1 < len(history):
                    previous_revision = history[i + 1]["revision"]
                    break
            
            if not previous_revision:
                return {
                    "test_name": "migration_rollback",
                    "success": False,
                    "error": "Could not find previous revision",
                    "skipped": True
                }
            
            # Perform rollback
            self.manager.downgrade_database(previous_revision)
            
            # Verify rollback
            rolled_back_revision = self.manager.get_current_revision()
            rollback_success = rolled_back_revision == previous_revision
            
            # Roll forward again
            self.manager.upgrade_database("head")
            final_revision = self.manager.get_current_revision()
            rollforward_success = final_revision == current_revision
            
            test_result = {
                "test_name": "migration_rollback",
                "success": rollback_success and rollforward_success,
                "initial_revision": current_revision,
                "rollback_target": previous_revision,
                "rollback_result": rolled_back_revision,
                "rollforward_result": final_revision,
                "rollback_success": rollback_success,
                "rollforward_success": rollforward_success
            }
            
            logger.info(f"Migration rollback test completed: {'PASSED' if test_result['success'] else 'FAILED'}")
            return test_result
            
        except Exception as e:
            logger.error(f"Migration rollback test failed: {e}")
            return {
                "test_name": "migration_rollback",
                "success": False,
                "error": str(e)
            }
    
    async def test_migration_validation(self) -> Dict[str, Any]:
        """
        Test migration validation functionality.
        
        Returns:
            Test results dictionary
        """
        logger.info("Testing migration validation")
        
        try:
            # Run validation
            validation_result = self.manager.validate_migration_state()
            
            # Check for conflicts
            conflicts = self.manager.check_migration_conflicts()
            
            test_result = {
                "test_name": "migration_validation",
                "success": validation_result["valid"] and len(conflicts) == 0,
                "validation_result": validation_result,
                "conflicts": conflicts,
                "has_conflicts": len(conflicts) > 0
            }
            
            logger.info(f"Migration validation test completed: {'PASSED' if test_result['success'] else 'FAILED'}")
            return test_result
            
        except Exception as e:
            logger.error(f"Migration validation test failed: {e}")
            return {
                "test_name": "migration_validation",
                "success": False,
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all migration tests.
        
        Returns:
            Comprehensive test results
        """
        logger.info("Running all migration tests")
        
        await self.setup()
        
        try:
            results = {
                "overall_success": True,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "test_results": []
            }
            
            # Test fresh migration
            fresh_result = await self.test_fresh_migration()
            results["test_results"].append(fresh_result)
            results["tests_run"] += 1
            
            if fresh_result["success"]:
                results["tests_passed"] += 1
            else:
                results["tests_failed"] += 1
                results["overall_success"] = False
            
            # Test migration validation
            validation_result = await self.test_migration_validation()
            results["test_results"].append(validation_result)
            results["tests_run"] += 1
            
            if validation_result["success"]:
                results["tests_passed"] += 1
            else:
                results["tests_failed"] += 1
                results["overall_success"] = False
            
            # Test migration rollback (only if fresh migration passed)
            if fresh_result["success"]:
                rollback_result = await self.test_migration_rollback()
                results["test_results"].append(rollback_result)
                results["tests_run"] += 1
                
                if rollback_result.get("skipped"):
                    logger.info("Migration rollback test was skipped")
                elif rollback_result["success"]:
                    results["tests_passed"] += 1
                else:
                    results["tests_failed"] += 1
                    results["overall_success"] = False
            
            logger.info(f"All migration tests completed: {results['tests_passed']}/{results['tests_run']} passed")
            return results
            
        finally:
            await self.teardown()


async def main():
    """Main function to run migration tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test database migrations")
    parser.add_argument(
        "--database-url",
        help="Test database URL (default: from environment)"
    )
    parser.add_argument(
        "--test",
        choices=["fresh", "rollback", "validation", "all"],
        default="all",
        help="Which test to run (default: all)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    tester = MigrationTester(args.database_url)
    
    try:
        if args.test == "all":
            results = await tester.run_all_tests()
        else:
            await tester.setup()
            try:
                if args.test == "fresh":
                    results = await tester.test_fresh_migration()
                elif args.test == "rollback":
                    results = await tester.test_migration_rollback()
                elif args.test == "validation":
                    results = await tester.test_migration_validation()
            finally:
                await tester.teardown()
        
        # Print results
        print("\n" + "="*50)
        print("MIGRATION TEST RESULTS")
        print("="*50)
        
        if args.test == "all":
            print(f"Overall Result: {'PASSED' if results['overall_success'] else 'FAILED'}")
            print(f"Tests Run: {results['tests_run']}")
            print(f"Tests Passed: {results['tests_passed']}")
            print(f"Tests Failed: {results['tests_failed']}")
            print("\nIndividual Test Results:")
            
            for test_result in results["test_results"]:
                status = "PASSED" if test_result["success"] else "FAILED"
                if test_result.get("skipped"):
                    status = "SKIPPED"
                print(f"  {test_result['test_name']}: {status}")
                
                if not test_result["success"] and "error" in test_result:
                    print(f"    Error: {test_result['error']}")
        else:
            status = "PASSED" if results["success"] else "FAILED"
            if results.get("skipped"):
                status = "SKIPPED"
            print(f"Test Result: {status}")
            
            if not results["success"] and "error" in results:
                print(f"Error: {results['error']}")
        
        # Exit with appropriate code
        if args.test == "all":
            sys.exit(0 if results["overall_success"] else 1)
        else:
            sys.exit(0 if results["success"] or results.get("skipped") else 1)
            
    except Exception as e:
        logger.error(f"Migration test failed: {e}")
        print(f"\nMIGRATION TEST FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())