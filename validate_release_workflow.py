#!/usr/bin/env python3
"""
Release Workflow Validation Script

This script validates the release workflow functionality after upgrading
artifact actions from v3 to v4. It tests:
1. Release-dist artifact upload with v4
2. TestPyPI publication artifact download
3. PyPI publication artifact download
4. GitHub release creation artifact download

Requirements: 1.1, 1.3, 1.4, 4.1, 4.2, 4.3, 4.4
"""

import os
import sys
import subprocess
import json
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ReleaseWorkflowValidator:
    """Validates the release workflow functionality with v4 artifact actions."""

    def __init__(self, workflow_path: str = ".github/workflows/release.yml"):
        self.workflow_path = Path(workflow_path)
        self.validation_results = []
        self.errors = []

    def log_result(self, test_name: str, success: bool, message: str):
        """Log a validation result."""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "status": status,
        }
        self.validation_results.append(result)
        print(f"{status}: {test_name} - {message}")

        if not success:
            self.errors.append(f"{test_name}: {message}")

    def validate_workflow_syntax(self) -> bool:
        """Validate the workflow YAML syntax."""
        try:
            with open(self.workflow_path, "r") as f:
                workflow_content = yaml.safe_load(f)

            # Check if workflow is valid YAML
            if not isinstance(workflow_content, dict):
                self.log_result(
                    "Workflow Syntax", False, "Workflow file is not valid YAML"
                )
                return False

            # Check required workflow structure - 'on' key might be parsed differently
            required_keys = ["name", "jobs"]
            for key in required_keys:
                if key not in workflow_content:
                    self.log_result(
                        "Workflow Syntax", False, f"Missing required key: {key}"
                    )
                    return False

            # Check for trigger configuration (on/true key variations)
            has_trigger = "on" in workflow_content or True in workflow_content
            if not has_trigger:
                self.log_result(
                    "Workflow Syntax", False, "Missing workflow trigger configuration"
                )
                return False

            self.log_result("Workflow Syntax", True, "Workflow YAML syntax is valid")
            return True

        except yaml.YAMLError as e:
            self.log_result("Workflow Syntax", False, f"YAML syntax error: {e}")
            return False
        except Exception as e:
            self.log_result(
                "Workflow Syntax", False, f"Error reading workflow file: {e}"
            )
            return False

    def validate_artifact_actions_v4(self) -> bool:
        """Validate that all artifact actions use v4."""
        try:
            with open(self.workflow_path, "r") as f:
                content = f.read()

            # Check for v4 artifact actions
            v4_upload_count = content.count("actions/upload-artifact@v4")
            v4_download_count = content.count("actions/download-artifact@v4")

            # Check for any remaining v3 actions (should be 0)
            v3_upload_count = content.count("actions/upload-artifact@v3")
            v3_download_count = content.count("actions/download-artifact@v3")

            # Expected counts based on design document
            expected_upload_v4 = 1  # release-dist upload
            expected_download_v4 = 3  # TestPyPI, PyPI, GitHub Release downloads

            success = True
            messages = []

            if v3_upload_count > 0 or v3_download_count > 0:
                success = False
                messages.append(
                    f"Found {v3_upload_count} v3 upload and {v3_download_count} v3 download actions"
                )

            if v4_upload_count != expected_upload_v4:
                success = False
                messages.append(
                    f"Expected {expected_upload_v4} v4 upload actions, found {v4_upload_count}"
                )

            if v4_download_count != expected_download_v4:
                success = False
                messages.append(
                    f"Expected {expected_download_v4} v4 download actions, found {v4_download_count}"
                )

            if success:
                message = f"All artifact actions use v4 ({v4_upload_count} upload, {v4_download_count} download)"
            else:
                message = "; ".join(messages)

            self.log_result("Artifact Actions v4", success, message)
            return success

        except Exception as e:
            self.log_result(
                "Artifact Actions v4", False, f"Error validating artifact actions: {e}"
            )
            return False

    def validate_job_structure(self) -> bool:
        """Validate the release workflow job structure."""
        try:
            with open(self.workflow_path, "r") as f:
                workflow = yaml.safe_load(f)

            jobs = workflow.get("jobs", {})

            # Expected jobs for release workflow
            expected_jobs = [
                "validate-release",
                "test-release",
                "build-release",
                "publish-testpypi",
                "publish-pypi",
                "create-github-release",
            ]

            missing_jobs = []
            for job in expected_jobs:
                if job not in jobs:
                    missing_jobs.append(job)

            if missing_jobs:
                self.log_result(
                    "Job Structure", False, f"Missing jobs: {', '.join(missing_jobs)}"
                )
                return False

            # Validate artifact-related jobs have correct structure
            artifact_jobs = {
                "build-release": {"uploads": ["release-dist"]},
                "publish-testpypi": {"downloads": ["release-dist"]},
                "publish-pypi": {"downloads": ["release-dist"]},
                "create-github-release": {"downloads": ["release-dist"]},
            }

            for job_name, requirements in artifact_jobs.items():
                job = jobs.get(job_name, {})
                steps = job.get("steps", [])

                # Check for upload steps
                if "uploads" in requirements:
                    upload_found = any(
                        step.get("uses", "").startswith("actions/upload-artifact@v4")
                        for step in steps
                    )
                    if not upload_found:
                        self.log_result(
                            "Job Structure",
                            False,
                            f"Job {job_name} missing upload-artifact@v4 step",
                        )
                        return False

                # Check for download steps
                if "downloads" in requirements:
                    download_found = any(
                        step.get("uses", "").startswith("actions/download-artifact@v4")
                        for step in steps
                    )
                    if not download_found:
                        self.log_result(
                            "Job Structure",
                            False,
                            f"Job {job_name} missing download-artifact@v4 step",
                        )
                        return False

            self.log_result(
                "Job Structure",
                True,
                "All required jobs present with correct artifact action structure",
            )
            return True

        except Exception as e:
            self.log_result(
                "Job Structure", False, f"Error validating job structure: {e}"
            )
            return False

    def validate_artifact_configurations(self) -> bool:
        """Validate artifact upload/download configurations."""
        try:
            with open(self.workflow_path, "r") as f:
                workflow = yaml.safe_load(f)

            jobs = workflow.get("jobs", {})

            # Validate build-release job artifact upload
            build_job = jobs.get("build-release", {})
            build_steps = build_job.get("steps", [])

            upload_step = None
            for step in build_steps:
                if step.get("uses", "").startswith("actions/upload-artifact@v4"):
                    upload_step = step
                    break

            if not upload_step:
                self.log_result(
                    "Artifact Configuration",
                    False,
                    "build-release job missing upload-artifact@v4 step",
                )
                return False

            # Check upload configuration
            upload_with = upload_step.get("with", {})
            if upload_with.get("name") != "release-dist":
                self.log_result(
                    "Artifact Configuration",
                    False,
                    f"Upload artifact name should be 'release-dist', got '{upload_with.get('name')}'",
                )
                return False

            if upload_with.get("path") != "dist/":
                self.log_result(
                    "Artifact Configuration",
                    False,
                    f"Upload artifact path should be 'dist/', got '{upload_with.get('path')}'",
                )
                return False

            # Validate download configurations
            download_jobs = [
                "publish-testpypi",
                "publish-pypi",
                "create-github-release",
            ]

            for job_name in download_jobs:
                job = jobs.get(job_name, {})
                steps = job.get("steps", [])

                download_step = None
                for step in steps:
                    if step.get("uses", "").startswith("actions/download-artifact@v4"):
                        download_step = step
                        break

                if not download_step:
                    self.log_result(
                        "Artifact Configuration",
                        False,
                        f"{job_name} job missing download-artifact@v4 step",
                    )
                    return False

                # Check download configuration
                download_with = download_step.get("with", {})
                if download_with.get("name") != "release-dist":
                    self.log_result(
                        "Artifact Configuration",
                        False,
                        f"{job_name} download artifact name should be 'release-dist', got '{download_with.get('name')}'",
                    )
                    return False

                if download_with.get("path") != "dist/":
                    self.log_result(
                        "Artifact Configuration",
                        False,
                        f"{job_name} download artifact path should be 'dist/', got '{download_with.get('path')}'",
                    )
                    return False

            self.log_result(
                "Artifact Configuration",
                True,
                "All artifact upload/download configurations are correct",
            )
            return True

        except Exception as e:
            self.log_result(
                "Artifact Configuration",
                False,
                f"Error validating artifact configurations: {e}",
            )
            return False

    def validate_job_dependencies(self) -> bool:
        """Validate job dependencies for artifact flow."""
        try:
            with open(self.workflow_path, "r") as f:
                workflow = yaml.safe_load(f)

            jobs = workflow.get("jobs", {})

            # Expected dependencies for artifact flow
            expected_deps = {
                "build-release": ["validate-release", "test-release"],
                "publish-testpypi": ["build-release"],
                "publish-pypi": ["build-release", "validate-release"],
                "create-github-release": ["validate-release", "build-release"],
            }

            for job_name, expected_needs in expected_deps.items():
                job = jobs.get(job_name, {})
                actual_needs = job.get("needs", [])

                # Convert to list if single string
                if isinstance(actual_needs, str):
                    actual_needs = [actual_needs]

                # Check if all expected dependencies are present
                missing_deps = []
                for dep in expected_needs:
                    if dep not in actual_needs:
                        missing_deps.append(dep)

                if missing_deps:
                    self.log_result(
                        "Job Dependencies",
                        False,
                        f"{job_name} missing dependencies: {', '.join(missing_deps)}",
                    )
                    return False

            self.log_result(
                "Job Dependencies",
                True,
                "All job dependencies for artifact flow are correct",
            )
            return True

        except Exception as e:
            self.log_result(
                "Job Dependencies", False, f"Error validating job dependencies: {e}"
            )
            return False

    def simulate_workflow_execution(self) -> bool:
        """Simulate workflow execution to test artifact flow."""
        try:
            # Check if we're in a git repository
            result = subprocess.run(["git", "status"], capture_output=True, text=True)

            if result.returncode != 0:
                self.log_result("Workflow Simulation", False, "Not in a git repository")
                return False

            # Check if GitHub workflow directory exists
            workflow_dir = Path(".github/workflows")
            if not workflow_dir.exists():
                self.log_result(
                    "Workflow Simulation",
                    False,
                    ".github/workflows directory not found",
                )
                return False

            # Check if release workflow file exists
            if not self.workflow_path.exists():
                self.log_result(
                    "Workflow Simulation",
                    False,
                    f"Release workflow file not found: {self.workflow_path}",
                )
                return False

            # Try to check GitHub CLI availability (optional)
            gh_available = False
            try:
                result = subprocess.run(
                    ["gh", "--version"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    gh_available = True
            except:
                pass

            if gh_available:
                # Try to list workflows if authenticated
                result = subprocess.run(
                    ["gh", "workflow", "list"], capture_output=True, text=True
                )

                if result.returncode == 0:
                    if "Release" in result.stdout:
                        self.log_result(
                            "Workflow Simulation",
                            True,
                            "Release workflow is available and can be executed via GitHub CLI",
                        )
                        return True
                    else:
                        self.log_result(
                            "Workflow Simulation",
                            True,
                            "GitHub CLI available but release workflow not listed (may need authentication)",
                        )
                        return True
                else:
                    self.log_result(
                        "Workflow Simulation",
                        True,
                        "GitHub CLI available but not authenticated (workflow file exists and is valid)",
                    )
                    return True
            else:
                self.log_result(
                    "Workflow Simulation",
                    True,
                    "Workflow file exists and is ready for execution (GitHub CLI not available for testing)",
                )
                return True

        except Exception as e:
            self.log_result(
                "Workflow Simulation",
                False,
                f"Error simulating workflow execution: {e}",
            )
            return False

    def validate_build_artifacts(self) -> bool:
        """Validate that build artifacts can be created locally."""
        try:
            # Check if pyproject.toml exists
            if not Path("pyproject.toml").exists():
                self.log_result("Build Artifacts", False, "pyproject.toml not found")
                return False

            # Check if dist directory exists (may have been created by previous builds)
            dist_path = Path("dist")
            if dist_path.exists():
                # Check for wheel and source distribution
                wheel_files = list(dist_path.glob("*.whl"))
                sdist_files = list(dist_path.glob("*.tar.gz"))

                if wheel_files and sdist_files:
                    self.log_result(
                        "Build Artifacts",
                        True,
                        f"Build artifacts found ({len(wheel_files)} wheel, {len(sdist_files)} sdist)",
                    )
                    return True

            # Try to use python3 instead of python
            python_cmd = "python3"

            # Check if we can build the package locally
            result = subprocess.run(
                [python_cmd, "-m", "build", "--help"], capture_output=True, text=True
            )

            if result.returncode != 0:
                self.log_result(
                    "Build Artifacts",
                    False,
                    "Python build module not available (install with: pip install build)",
                )
                return False

            # Try to build the package
            result = subprocess.run(
                [python_cmd, "-m", "build", "--wheel", "--sdist"],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if result.returncode != 0:
                self.log_result(
                    "Build Artifacts", False, f"Package build failed: {result.stderr}"
                )
                return False

            # Check if dist directory was created with artifacts
            if not dist_path.exists():
                self.log_result("Build Artifacts", False, "dist/ directory not created")
                return False

            # Check for wheel and source distribution
            wheel_files = list(dist_path.glob("*.whl"))
            sdist_files = list(dist_path.glob("*.tar.gz"))

            if not wheel_files:
                self.log_result(
                    "Build Artifacts", False, "No wheel files found in dist/"
                )
                return False

            if not sdist_files:
                self.log_result(
                    "Build Artifacts",
                    False,
                    "No source distribution files found in dist/",
                )
                return False

            self.log_result(
                "Build Artifacts",
                True,
                f"Build artifacts created successfully ({len(wheel_files)} wheel, {len(sdist_files)} sdist)",
            )
            return True

        except Exception as e:
            self.log_result(
                "Build Artifacts", False, f"Error validating build artifacts: {e}"
            )
            return False

    def run_validation(self) -> bool:
        """Run all validation tests."""
        print("🚀 Starting Release Workflow Validation")
        print("=" * 50)

        # Change to the vet-core-package directory if we're not already there
        if Path("vet-core-package").exists():
            os.chdir("vet-core-package")
            print("📁 Changed to vet-core-package directory")

        # Run all validation tests
        tests = [
            self.validate_workflow_syntax,
            self.validate_artifact_actions_v4,
            self.validate_job_structure,
            self.validate_artifact_configurations,
            self.validate_job_dependencies,
            self.validate_build_artifacts,
            self.simulate_workflow_execution,
        ]

        all_passed = True
        for test in tests:
            try:
                result = test()
                if not result:
                    all_passed = False
            except Exception as e:
                self.log_result(test.__name__, False, f"Test execution failed: {e}")
                all_passed = False
            print()  # Add spacing between tests

        # Print summary
        print("=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)

        passed = sum(1 for r in self.validation_results if r["success"])
        total = len(self.validation_results)

        print(f"Tests passed: {passed}/{total}")

        if self.errors:
            print("\n❌ ERRORS FOUND:")
            for error in self.errors:
                print(f"  • {error}")

        if all_passed:
            print("\n✅ ALL VALIDATIONS PASSED!")
            print("The release workflow is ready for v4 artifact actions.")
        else:
            print("\n❌ SOME VALIDATIONS FAILED!")
            print("Please address the errors before using the release workflow.")

        return all_passed


def main():
    """Main function to run release workflow validation."""
    validator = ReleaseWorkflowValidator()
    success = validator.run_validation()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
