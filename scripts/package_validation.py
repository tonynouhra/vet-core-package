#!/usr/bin/env python3
"""
Package validation script for vet-core package.

This script performs comprehensive validation of the package including:
- Package installation and import validation
- Documentation completeness
- Example script validation
- Basic functionality testing
- Package structure verification
"""

import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

def run_command(command: List[str], cwd: Path = None) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def test_package_build():
    """Test that the package can be built."""
    print("Testing package build...")
    
    package_root = Path(__file__).parent.parent
    success, output = run_command(["python", "-m", "build"], cwd=package_root)
    
    if success:
        # Check that dist files were created
        dist_dir = package_root / "dist"
        if dist_dir.exists():
            wheel_files = list(dist_dir.glob("*.whl"))
            tar_files = list(dist_dir.glob("*.tar.gz"))
            
            if wheel_files and tar_files:
                print("✅ Package build successful")
                return True
            else:
                print("❌ Package build failed: No distribution files created")
                return False
        else:
            print("❌ Package build failed: No dist directory created")
            return False
    else:
        print(f"❌ Package build failed: {output}")
        return False

def test_package_installation():
    """Test package installation in a clean environment."""
    print("Testing package installation...")
    
    package_root = Path(__file__).parent.parent
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Install the package in development mode
        success, output = run_command([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], cwd=package_root)
        
        if not success:
            print(f"❌ Package installation failed: {output}")
            return False
        
        # Test that the package can be imported
        success, output = run_command([
            sys.executable, "-c", "import vet_core; print('Import successful')"
        ])
        
        if success:
            print("✅ Package installation and import successful")
            return True
        else:
            print(f"❌ Package import failed: {output}")
            return False

def test_basic_functionality():
    """Test basic package functionality."""
    print("Testing basic functionality...")
    
    test_script = '''
import sys
sys.path.insert(0, "src")

try:
    # Test imports
    import vet_core
    from vet_core.models import User, Pet, Appointment, Clinic, Veterinarian
    from vet_core.schemas import UserCreate, PetCreate
    from vet_core.exceptions import VetCoreException, ValidationException
    from vet_core.utils.datetime_utils import get_current_utc
    from vet_core.utils.validation import validate_email
    
    # Test basic functionality
    current_time = get_current_utc()
    print(f"Current time: {current_time}")
    
    email_result = validate_email("test@example.com")
    print(f"Email validation: {email_result.is_valid}")
    
    # Test exception creation
    exc = VetCoreException("Test exception")
    print(f"Exception: {exc}")
    
    # Test model class existence
    print(f"User model: {User}")
    print(f"Pet model: {Pet}")
    
    print("All basic functionality tests passed")
    
except Exception as e:
    print(f"Basic functionality test failed: {e}")
    sys.exit(1)
'''
    
    package_root = Path(__file__).parent.parent
    success, output = run_command([
        sys.executable, "-c", test_script
    ], cwd=package_root)
    
    if success:
        print("✅ Basic functionality tests passed")
        return True
    else:
        print(f"❌ Basic functionality tests failed: {output}")
        return False

def test_documentation():
    """Test documentation completeness."""
    print("Testing documentation...")
    
    package_root = Path(__file__).parent.parent
    
    required_files = [
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        "pyproject.toml"
    ]
    
    missing_files = []
    for file_name in required_files:
        if not (package_root / file_name).exists():
            missing_files.append(file_name)
    
    # Check docs directory
    docs_dir = package_root / "docs"
    if docs_dir.exists():
        doc_files = ["API_REFERENCE.md", "USAGE_GUIDE.md"]
        for doc_file in doc_files:
            if not (docs_dir / doc_file).exists():
                missing_files.append(f"docs/{doc_file}")
    else:
        missing_files.append("docs/ directory")
    
    if missing_files:
        print(f"❌ Documentation incomplete: Missing {missing_files}")
        return False
    else:
        print("✅ Documentation is complete")
        return True

def test_examples():
    """Test example scripts."""
    print("Testing example scripts...")
    
    package_root = Path(__file__).parent.parent
    examples_dir = package_root / "examples"
    
    if not examples_dir.exists():
        print("❌ Examples directory not found")
        return False
    
    example_files = list(examples_dir.glob("*.py"))
    if not example_files:
        print("❌ No example files found")
        return False
    
    # Test syntax of example files
    failed_examples = []
    for example_file in example_files:
        try:
            with open(example_file, 'r') as f:
                compile(f.read(), str(example_file), 'exec')
        except SyntaxError as e:
            failed_examples.append(f"{example_file.name}: {e}")
    
    if failed_examples:
        print(f"❌ Example syntax errors: {failed_examples}")
        return False
    else:
        print(f"✅ All {len(example_files)} example scripts are valid")
        return True

def test_migrations():
    """Test migration system."""
    print("Testing migration system...")
    
    package_root = Path(__file__).parent.parent
    
    # Check Alembic configuration
    alembic_ini = package_root / "alembic.ini"
    alembic_dir = package_root / "alembic"
    
    if not alembic_ini.exists():
        print("❌ alembic.ini not found")
        return False
    
    if not alembic_dir.exists():
        print("❌ alembic/ directory not found")
        return False
    
    # Check for env.py
    env_py = alembic_dir / "env.py"
    if not env_py.exists():
        print("❌ alembic/env.py not found")
        return False
    
    # Check versions directory
    versions_dir = alembic_dir / "versions"
    if not versions_dir.exists():
        print("❌ alembic/versions/ directory not found")
        return False
    
    # Check for migration files
    migration_files = list(versions_dir.glob("*.py"))
    if not migration_files:
        print("❌ No migration files found")
        return False
    
    print(f"✅ Migration system configured with {len(migration_files)} migrations")
    return True

def test_package_structure():
    """Test package structure."""
    print("Testing package structure...")
    
    package_root = Path(__file__).parent.parent / "src" / "vet_core"
    
    expected_structure = {
        "models": ["__init__.py", "base.py", "user.py", "pet.py", "appointment.py", "clinic.py", "veterinarian.py"],
        "schemas": ["__init__.py", "user.py", "pet.py", "appointment.py", "clinic.py", "veterinarian.py"],
        "database": ["__init__.py", "connection.py", "session.py", "migrations.py"],
        "utils": ["__init__.py", "config.py", "datetime_utils.py", "validation.py"],
        "exceptions": ["__init__.py", "core_exceptions.py"]
    }
    
    missing_items = []
    
    for directory, files in expected_structure.items():
        dir_path = package_root / directory
        if not dir_path.exists():
            missing_items.append(f"Directory: {directory}")
            continue
        
        for file_name in files:
            file_path = dir_path / file_name
            if not file_path.exists():
                missing_items.append(f"File: {directory}/{file_name}")
    
    if missing_items:
        print(f"❌ Package structure incomplete: {missing_items}")
        return False
    else:
        print("✅ Package structure is complete")
        return True

def test_dependencies():
    """Test that all dependencies are properly specified."""
    print("Testing dependencies...")
    
    package_root = Path(__file__).parent.parent
    pyproject_toml = package_root / "pyproject.toml"
    
    if not pyproject_toml.exists():
        print("❌ pyproject.toml not found")
        return False
    
    # Check that we can parse the dependencies
    try:
        import tomllib
        with open(pyproject_toml, 'rb') as f:
            data = tomllib.load(f)
        
        dependencies = data.get('project', {}).get('dependencies', [])
        if not dependencies:
            print("❌ No dependencies specified")
            return False
        
        # Check for key dependencies
        required_deps = ['sqlalchemy', 'pydantic', 'alembic', 'asyncpg']
        missing_deps = []
        
        for req_dep in required_deps:
            found = any(req_dep in dep for dep in dependencies)
            if not found:
                missing_deps.append(req_dep)
        
        if missing_deps:
            print(f"❌ Missing required dependencies: {missing_deps}")
            return False
        
        print(f"✅ Dependencies properly specified ({len(dependencies)} total)")
        return True
        
    except ImportError:
        print("⚠️  Cannot test dependencies (tomllib not available)")
        return True
    except Exception as e:
        print(f"❌ Error reading dependencies: {e}")
        return False

def run_tests():
    """Run all validation tests."""
    print("Starting vet-core package validation...")
    print("=" * 60)
    
    tests = [
        ("Package Structure", test_package_structure),
        ("Documentation", test_documentation),
        ("Dependencies", test_dependencies),
        ("Examples", test_examples),
        ("Migrations", test_migrations),
        ("Basic Functionality", test_basic_functionality),
        ("Package Build", test_package_build),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
        print()
    
    # Print summary
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed < total:
        print("\nFAILED TESTS:")
        for test_name, result in results.items():
            if not result:
                print(f"  ❌ {test_name}")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)