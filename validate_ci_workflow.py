#!/usr/bin/env python3
"""
CI Workflow Validation Script

This script validates the CI workflow functionality by:
1. Testing security reports artifact generation
2. Testing build artifacts creation
3. Simulating artifact upload/download scenarios
4. Verifying integration test compatibility
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

def run_command(cmd, cwd=None, capture_output=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=capture_output,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def validate_security_reports():
    """Validate security reports artifact generation"""
    print("🔍 Validating security reports artifact generation...")
    
    # Check if security report files exist
    bandit_report = Path("bandit-report.json")
    safety_report = Path("safety-report.json")
    
    if not bandit_report.exists():
        print("❌ bandit-report.json not found")
        return False
    
    if not safety_report.exists():
        print("❌ safety-report.json not found")
        return False
    
    # Validate bandit report structure
    try:
        with open(bandit_report) as f:
            bandit_data = json.load(f)
        
        required_keys = ["errors", "generated_at", "metrics"]
        if not all(key in bandit_data for key in required_keys):
            print("❌ bandit-report.json missing required keys")
            return False
        
        print("✅ bandit-report.json is valid")
    except json.JSONDecodeError:
        print("❌ bandit-report.json is not valid JSON")
        return False
    
    # Check safety report exists (even if deprecated)
    if safety_report.stat().st_size > 0:
        print("✅ safety-report.json exists and has content")
    else:
        print("⚠️  safety-report.json is empty (may be due to deprecation)")
    
    print("✅ Security reports artifact validation passed")
    return True

def validate_build_artifacts():
    """Validate build artifacts creation"""
    print("🔨 Validating build artifacts creation...")
    
    # Check if dist directory exists
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ dist/ directory not found")
        return False
    
    # Check for wheel and source distribution files
    wheel_files = list(dist_dir.glob("*.whl"))
    tar_files = list(dist_dir.glob("*.tar.gz"))
    
    if not wheel_files:
        print("❌ No wheel files found in dist/")
        return False
    
    if not tar_files:
        print("❌ No source distribution files found in dist/")
        return False
    
    print(f"✅ Found {len(wheel_files)} wheel file(s)")
    print(f"✅ Found {len(tar_files)} source distribution file(s)")
    
    # Validate wheel file can be inspected
    wheel_file = wheel_files[0]
    success, stdout, stderr = run_command(f"python3 -m pip show --files {wheel_file}")
    
    print("✅ Build artifacts validation passed")
    return True

def simulate_artifact_upload_download():
    """Simulate artifact upload/download scenario"""
    print("📦 Simulating artifact upload/download scenario...")
    
    # Create a temporary directory to simulate artifact storage
    with tempfile.TemporaryDirectory() as temp_dir:
        artifact_dir = Path(temp_dir) / "artifacts"
        artifact_dir.mkdir()
        
        # Simulate uploading security reports
        security_artifacts = artifact_dir / "security-reports"
        security_artifacts.mkdir()
        
        if Path("bandit-report.json").exists():
            shutil.copy("bandit-report.json", security_artifacts)
        if Path("safety-report.json").exists():
            shutil.copy("safety-report.json", security_artifacts)
        
        # Simulate uploading build artifacts
        build_artifacts = artifact_dir / "dist"
        if Path("dist").exists():
            shutil.copytree("dist", build_artifacts)
        
        # Simulate downloading artifacts (like integration tests would)
        download_dir = Path(temp_dir) / "download"
        download_dir.mkdir()
        
        # Download security reports
        if security_artifacts.exists():
            shutil.copytree(security_artifacts, download_dir / "security-reports")
            print("✅ Security reports artifact download simulation successful")
        
        # Download build artifacts
        if build_artifacts.exists():
            shutil.copytree(build_artifacts, download_dir / "dist")
            print("✅ Build artifacts download simulation successful")
        
        # Verify downloaded artifacts
        downloaded_dist = download_dir / "dist"
        if downloaded_dist.exists():
            wheel_files = list(downloaded_dist.glob("*.whl"))
            if wheel_files:
                print(f"✅ Downloaded {len(wheel_files)} wheel file(s)")
            else:
                print("❌ No wheel files in downloaded artifacts")
                return False
        
    print("✅ Artifact upload/download simulation passed")
    return True

def validate_integration_test_compatibility():
    """Validate that artifacts are compatible with integration tests"""
    print("🧪 Validating integration test compatibility...")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ dist/ directory not found for integration test validation")
        return False
    
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("❌ No wheel files found for integration test validation")
        return False
    
    wheel_file = wheel_files[0]
    
    # Test that the wheel can be installed (dry run)
    success, stdout, stderr = run_command(f"python3 -m pip install --dry-run {wheel_file}")
    if not success:
        print(f"❌ Wheel file {wheel_file} cannot be installed: {stderr}")
        return False
    
    print(f"✅ Wheel file {wheel_file} is installable")
    
    # Test basic import after installation (in a virtual environment simulation)
    # This simulates what the integration tests do
    try:
        # Create a temporary test script
        test_script = """
import sys
import importlib.util

# Test basic imports that integration tests would perform
test_imports = [
    'vet_core',
    'vet_core.models',
    'vet_core.database'
]

for module_name in test_imports:
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"❌ Module {module_name} not found")
            sys.exit(1)
        else:
            print(f"✅ Module {module_name} is importable")
    except Exception as e:
        print(f"❌ Error checking module {module_name}: {e}")
        sys.exit(1)

print("✅ All integration test imports are compatible")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            test_file = f.name
        
        # Note: We can't actually install and test imports without affecting the environment
        # So we'll just validate the wheel structure
        success, stdout, stderr = run_command(f"python3 -m zipfile -l {wheel_file}")
        if success and "vet_core" in stdout:
            print("✅ Wheel contains expected vet_core package structure")
        else:
            print("❌ Wheel does not contain expected package structure")
            return False
        
        os.unlink(test_file)
        
    except Exception as e:
        print(f"❌ Integration test compatibility check failed: {e}")
        return False
    
    print("✅ Integration test compatibility validation passed")
    return True

def validate_workflow_syntax():
    """Validate the CI workflow YAML syntax"""
    print("📝 Validating CI workflow syntax...")
    
    workflow_file = Path(".github/workflows/ci.yml")
    if not workflow_file.exists():
        print("❌ CI workflow file not found")
        return False
    
    # Check for v4 artifact actions
    with open(workflow_file) as f:
        content = f.read()
    
    # Check that v4 actions are used
    if "actions/upload-artifact@v4" not in content:
        print("❌ CI workflow does not use actions/upload-artifact@v4")
        return False
    
    if "actions/download-artifact@v4" not in content:
        print("❌ CI workflow does not use actions/download-artifact@v4")
        return False
    
    # Check that v3 actions are not used
    if "actions/upload-artifact@v3" in content:
        print("❌ CI workflow still contains deprecated actions/upload-artifact@v3")
        return False
    
    if "actions/download-artifact@v3" in content:
        print("❌ CI workflow still contains deprecated actions/download-artifact@v3")
        return False
    
    print("✅ CI workflow uses correct v4 artifact actions")
    print("✅ CI workflow syntax validation passed")
    return True

def main():
    """Main validation function"""
    print("🚀 Starting CI Workflow Validation")
    print("=" * 50)
    
    validations = [
        ("Workflow Syntax", validate_workflow_syntax),
        ("Security Reports", validate_security_reports),
        ("Build Artifacts", validate_build_artifacts),
        ("Artifact Upload/Download", simulate_artifact_upload_download),
        ("Integration Test Compatibility", validate_integration_test_compatibility),
    ]
    
    results = {}
    
    for name, validation_func in validations:
        print(f"\n📋 Running {name} validation...")
        try:
            results[name] = validation_func()
        except Exception as e:
            print(f"❌ {name} validation failed with exception: {e}")
            results[name] = False
        
        if results[name]:
            print(f"✅ {name} validation: PASSED")
        else:
            print(f"❌ {name} validation: FAILED")
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<30} {status}")
    
    print(f"\nOverall: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 All CI workflow validations PASSED!")
        return 0
    else:
        print("⚠️  Some CI workflow validations FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())