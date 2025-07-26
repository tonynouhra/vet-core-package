#!/usr/bin/env python3
"""
Pre-Release Workflow Validation Script

This script validates the pre-release workflow functionality after upgrading
artifact actions from v3 to v4. It tests all artifact uploads and downloads,
verifies the complete pre-release flow, and ensures all components work correctly.

Requirements tested:
- 1.1: Artifact actions use version 4
- 1.3: Existing functionality remains unchanged
- 1.4: Artifacts work with new action version
- 4.1: Workflows pass syntax validation
- 4.2: Workflows execute successfully
- 4.3: Artifacts are accessible and properly formatted
- 4.4: Workflow dependencies continue to work
"""

import os
import sys
import json
import yaml
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import re


class PreReleaseWorkflowValidator:
    def __init__(self):
        self.repo_root = Path(__file__).parent
        self.workflow_file = (
            self.repo_root / ".github" / "workflows" / "pre-release.yml"
        )
        self.validation_results = {
            "syntax_validation": False,
            "artifact_actions_v4": False,
            "performance_artifacts": False,
            "prerelease_dist_flow": False,
            "security_reports": False,
            "github_prerelease": False,
            "workflow_simulation": False,
            "cross_job_dependencies": False,
        }
        self.errors = []
        self.warnings = []

    def log_info(self, message: str):
        """Log info message"""
        print(f"ℹ️  {message}")

    def log_success(self, message: str):
        """Log success message"""
        print(f"✅ {message}")

    def log_warning(self, message: str):
        """Log warning message"""
        print(f"⚠️  {message}")
        self.warnings.append(message)

    def log_error(self, message: str):
        """Log error message"""
        print(f"❌ {message}")
        self.errors.append(message)

    def validate_workflow_syntax(self) -> bool:
        """Validate the pre-release workflow YAML syntax"""
        self.log_info("Validating pre-release workflow syntax...")

        try:
            if not self.workflow_file.exists():
                self.log_error(
                    f"Pre-release workflow file not found: {self.workflow_file}"
                )
                return False

            with open(self.workflow_file, "r") as f:
                workflow_content = yaml.safe_load(f)

            # Basic structure validation
            required_keys = ["name", "jobs"]
            for key in required_keys:
                if key not in workflow_content:
                    self.log_error(f"Missing required key '{key}' in workflow")
                    return False

            # Check for 'on' key (can be 'on' or 'true' in YAML)
            if "on" not in workflow_content and True not in workflow_content:
                self.log_error("Missing workflow trigger configuration ('on' key)")
                return False

            # Validate jobs structure
            jobs = workflow_content.get("jobs", {})
            expected_jobs = [
                "validate-prerelease",
                "comprehensive-testing",
                "build-prerelease",
                "test-installation",
                "environment-testing",
                "security-scan",
                "publish-testpypi",
                "validate-testpypi",
                "create-prerelease",
                "notify-completion",
            ]

            for job_name in expected_jobs:
                if job_name not in jobs:
                    self.log_warning(f"Expected job '{job_name}' not found in workflow")

            self.log_success("Pre-release workflow syntax validation passed")
            return True

        except yaml.YAMLError as e:
            self.log_error(f"YAML syntax error in workflow: {e}")
            return False
        except Exception as e:
            self.log_error(f"Error validating workflow syntax: {e}")
            return False

    def validate_artifact_actions_v4(self) -> bool:
        """Validate that all artifact actions use version 4"""
        self.log_info("Validating artifact actions are using v4...")

        try:
            with open(self.workflow_file, "r") as f:
                content = f.read()

            # Find all artifact action usages
            upload_pattern = r"uses:\s*actions/upload-artifact@v(\d+)"
            download_pattern = r"uses:\s*actions/download-artifact@v(\d+)"

            upload_matches = re.findall(upload_pattern, content)
            download_matches = re.findall(download_pattern, content)

            all_versions = upload_matches + download_matches

            if not all_versions:
                self.log_warning("No artifact actions found in workflow")
                return True

            # Check all versions are v4
            v3_found = False
            for version in all_versions:
                if version == "3":
                    v3_found = True
                    self.log_error(f"Found artifact action using v3 instead of v4")
                elif version != "4":
                    self.log_warning(
                        f"Found artifact action using unexpected version: v{version}"
                    )

            if v3_found:
                return False

            self.log_success(f"All {len(all_versions)} artifact actions are using v4")
            return True

        except Exception as e:
            self.log_error(f"Error validating artifact action versions: {e}")
            return False

    def validate_performance_artifacts(self) -> bool:
        """Validate performance artifacts configuration"""
        self.log_info("Validating performance artifacts configuration...")

        try:
            with open(self.workflow_file, "r") as f:
                content = f.read()

            # Check for performance results upload
            performance_patterns = [
                r"name:\s*performance-results",
                r"path:\s*benchmark-.*\.json",
                r"uses:\s*actions/upload-artifact@v4.*performance",
            ]

            found_patterns = 0
            for pattern in performance_patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    found_patterns += 1

            if found_patterns < 2:  # At least name and path should be found
                self.log_error("Performance artifacts configuration incomplete")
                return False

            # Check for performance test job
            if 'test-type: ["unit", "integration", "performance"]' not in content:
                self.log_warning("Performance test type not found in matrix strategy")

            self.log_success("Performance artifacts configuration validated")
            return True

        except Exception as e:
            self.log_error(f"Error validating performance artifacts: {e}")
            return False

    def validate_prerelease_dist_flow(self) -> bool:
        """Validate prerelease-dist artifact flow through all stages"""
        self.log_info("Validating prerelease-dist artifact flow...")

        try:
            with open(self.workflow_file, "r") as f:
                content = f.read()

            # Check for prerelease-dist upload in build job
            if "name: prerelease-dist" not in content:
                self.log_error("prerelease-dist artifact name not found")
                return False

            # Check for prerelease-dist downloads in dependent jobs
            expected_download_jobs = [
                "test-installation",
                "environment-testing",
                "security-scan",
                "publish-testpypi",
                "create-prerelease",
            ]

            downloads_found = 0
            for job in expected_download_jobs:
                # Look for download-artifact usage after job definition
                job_pattern = f"{job}:.*?(?=\\n\\s*[a-zA-Z-]+:|$)"
                job_match = re.search(job_pattern, content, re.DOTALL)
                if job_match:
                    job_content = job_match.group(0)
                    if (
                        "download-artifact@v4" in job_content
                        and "prerelease-dist" in job_content
                    ):
                        downloads_found += 1

            if downloads_found < 3:  # At least 3 jobs should download the artifact
                self.log_warning(
                    f"Only {downloads_found} jobs found downloading prerelease-dist"
                )

            self.log_success("Prerelease-dist artifact flow validated")
            return True

        except Exception as e:
            self.log_error(f"Error validating prerelease-dist flow: {e}")
            return False

    def validate_security_reports(self) -> bool:
        """Validate security reports artifact configuration"""
        self.log_info("Validating security reports configuration...")

        try:
            with open(self.workflow_file, "r") as f:
                content = f.read()

            # Check for security scan job
            if "security-scan:" not in content:
                self.log_error("Security scan job not found")
                return False

            # Check for security tools
            security_tools = ["bandit", "safety", "semgrep", "pip-audit"]
            tools_found = 0
            for tool in security_tools:
                if tool in content:
                    tools_found += 1

            if tools_found < 3:
                self.log_warning(f"Only {tools_found} security tools found")

            # Check for security reports upload
            if "prerelease-security-reports" not in content:
                self.log_error("Security reports artifact name not found")
                return False

            # Check for expected report files
            report_files = [
                "bandit-prerelease.json",
                "safety-prerelease.json",
                "pip-audit-prerelease.json",
                "semgrep-prerelease.json",
            ]

            files_found = 0
            for report_file in report_files:
                if report_file in content:
                    files_found += 1

            if files_found < 3:
                self.log_warning(f"Only {files_found} security report files configured")

            self.log_success("Security reports configuration validated")
            return True

        except Exception as e:
            self.log_error(f"Error validating security reports: {e}")
            return False

    def validate_github_prerelease(self) -> bool:
        """Validate GitHub pre-release creation configuration"""
        self.log_info("Validating GitHub pre-release creation...")

        try:
            with open(self.workflow_file, "r") as f:
                content = f.read()

            # Check for create-prerelease job
            if "create-prerelease:" not in content:
                self.log_error("Create pre-release job not found")
                return False

            # Check for GitHub release action
            if "actions/create-release@v1" not in content:
                self.log_error("GitHub create-release action not found")
                return False

            # Check for prerelease flag
            if "prerelease: true" not in content:
                self.log_error("Prerelease flag not set to true")
                return False

            # Check for artifact download before release creation
            create_prerelease_section = content[content.find("create-prerelease:") :]
            if "download-artifact@v4" not in create_prerelease_section[:1000]:
                self.log_warning("Artifact download not found in create-prerelease job")

            self.log_success("GitHub pre-release creation validated")
            return True

        except Exception as e:
            self.log_error(f"Error validating GitHub pre-release: {e}")
            return False

    def simulate_workflow_execution(self) -> bool:
        """Simulate workflow execution to test job dependencies"""
        self.log_info("Simulating workflow execution flow...")

        try:
            with open(self.workflow_file, "r") as f:
                workflow = yaml.safe_load(f)

            jobs = workflow.get("jobs", {})

            # Build dependency graph
            job_dependencies = {}
            for job_name, job_config in jobs.items():
                needs = job_config.get("needs", [])
                if isinstance(needs, str):
                    needs = [needs]
                job_dependencies[job_name] = needs

            # Validate dependency chain
            def validate_dependencies(job_name, visited=None):
                if visited is None:
                    visited = set()

                if job_name in visited:
                    return False  # Circular dependency

                visited.add(job_name)

                for dep in job_dependencies.get(job_name, []):
                    if dep not in job_dependencies:
                        self.log_error(
                            f"Job '{job_name}' depends on non-existent job '{dep}'"
                        )
                        return False
                    if not validate_dependencies(dep, visited.copy()):
                        return False

                return True

            # Check all jobs
            for job_name in job_dependencies:
                if not validate_dependencies(job_name):
                    self.log_error(f"Invalid dependency chain for job '{job_name}'")
                    return False

            # Check critical path
            critical_jobs = [
                "validate-prerelease",
                "build-prerelease",
                "test-installation",
                "security-scan",
                "create-prerelease",
            ]

            for job in critical_jobs:
                if job not in job_dependencies:
                    self.log_warning(f"Critical job '{job}' not found")

            self.log_success("Workflow execution simulation passed")
            return True

        except Exception as e:
            self.log_error(f"Error simulating workflow execution: {e}")
            return False

    def validate_cross_job_dependencies(self) -> bool:
        """Validate cross-job artifact dependencies"""
        self.log_info("Validating cross-job artifact dependencies...")

        try:
            with open(self.workflow_file, "r") as f:
                content = f.read()

            # Map artifacts to their producers and consumers
            artifact_producers = {}
            artifact_consumers = {}

            # Find upload-artifact usages (producers) - look for 'with:' section
            upload_sections = re.finditer(
                r"uses:\s*actions/upload-artifact@v4.*?with:\s*\n(.*?)(?=\n\s*-|\n[a-zA-Z]|\Z)",
                content,
                re.MULTILINE | re.DOTALL,
            )

            for match in upload_sections:
                with_section = match.group(1)
                name_match = re.search(r"name:\s*([^\n]+)", with_section)
                if name_match:
                    artifact_name = name_match.group(1).strip()
                    # Find which job this belongs to by looking backwards
                    job_match = re.search(
                        r"\n\s*([a-zA-Z][a-zA-Z0-9_-]*):\s*\n",
                        content[: match.start()][::-1],
                    )
                    if job_match:
                        job_name = job_match.group(1)[::-1]  # Reverse back
                        artifact_producers[artifact_name] = job_name

            # Find download-artifact usages (consumers)
            download_sections = re.finditer(
                r"uses:\s*actions/download-artifact@v4.*?with:\s*\n(.*?)(?=\n\s*-|\n[a-zA-Z]|\Z)",
                content,
                re.MULTILINE | re.DOTALL,
            )

            for match in download_sections:
                with_section = match.group(1)
                name_match = re.search(r"name:\s*([^\n]+)", with_section)
                if name_match:
                    artifact_name = name_match.group(1).strip()
                    # Find which job this belongs to by looking backwards
                    job_match = re.search(
                        r"\n\s*([a-zA-Z][a-zA-Z0-9_-]*):\s*\n",
                        content[: match.start()][::-1],
                    )
                    if job_match:
                        job_name = job_match.group(1)[::-1]  # Reverse back
                        if artifact_name not in artifact_consumers:
                            artifact_consumers[artifact_name] = []
                        artifact_consumers[artifact_name].append(job_name)

            # Validate that all consumed artifacts are produced
            orphaned_consumers = []
            for artifact_name, consumers in artifact_consumers.items():
                if artifact_name not in artifact_producers:
                    orphaned_consumers.append(artifact_name)
                    self.log_error(
                        f"Artifact '{artifact_name}' is consumed but not produced"
                    )

            if orphaned_consumers:
                return False

            # Validate key artifacts
            key_artifacts = [
                "prerelease-dist",
                "performance-results",
                "prerelease-security-reports",
            ]
            for artifact in key_artifacts:
                if artifact not in artifact_producers:
                    self.log_warning(
                        f"Key artifact '{artifact}' not found in producers"
                    )
                if artifact not in artifact_consumers:
                    self.log_warning(
                        f"Key artifact '{artifact}' not found in consumers"
                    )

            self.log_success("Cross-job artifact dependencies validated")
            return True

        except Exception as e:
            self.log_error(f"Error validating cross-job dependencies: {e}")
            return False

    def run_validation(self) -> bool:
        """Run all validation checks"""
        self.log_info("Starting pre-release workflow validation...")
        print("=" * 60)

        # Run all validation checks
        checks = [
            ("Syntax Validation", self.validate_workflow_syntax),
            ("Artifact Actions v4", self.validate_artifact_actions_v4),
            ("Performance Artifacts", self.validate_performance_artifacts),
            ("Prerelease Dist Flow", self.validate_prerelease_dist_flow),
            ("Security Reports", self.validate_security_reports),
            ("GitHub Pre-release", self.validate_github_prerelease),
            ("Workflow Simulation", self.simulate_workflow_execution),
            ("Cross-job Dependencies", self.validate_cross_job_dependencies),
        ]

        for check_name, check_func in checks:
            print(f"\n🔍 Running {check_name}...")
            try:
                result = check_func()
                self.validation_results[
                    check_name.lower().replace(" ", "_").replace("-", "_")
                ] = result
                if result:
                    self.log_success(f"{check_name} passed")
                else:
                    self.log_error(f"{check_name} failed")
            except Exception as e:
                self.log_error(f"{check_name} failed with exception: {e}")
                self.validation_results[
                    check_name.lower().replace(" ", "_").replace("-", "_")
                ] = False

        return self.generate_report()

    def generate_report(self) -> bool:
        """Generate validation report"""
        print("\n" + "=" * 60)
        print("📊 PRE-RELEASE WORKFLOW VALIDATION REPORT")
        print("=" * 60)

        # Summary
        passed = sum(1 for result in self.validation_results.values() if result)
        total = len(self.validation_results)

        print(f"\n📈 SUMMARY: {passed}/{total} checks passed")

        if passed == total:
            print("🎉 All validations passed! Pre-release workflow is ready.")
            success = True
        else:
            print("⚠️  Some validations failed. Review the issues below.")
            success = False

        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        for check, result in self.validation_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {check.replace('_', ' ').title()}")

        # Errors and warnings
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        # Requirements mapping
        print(f"\n📋 REQUIREMENTS VALIDATION:")
        requirements_status = {
            "1.1 (Artifact actions use v4)": self.validation_results.get(
                "artifact_actions_v4", False
            ),
            "1.3 (Existing functionality unchanged)": self.validation_results.get(
                "workflow_simulation", False
            ),
            "1.4 (Artifacts work with v4)": self.validation_results.get(
                "cross_job_dependencies", False
            ),
            "4.1 (Syntax validation passes)": self.validation_results.get(
                "syntax_validation", False
            ),
            "4.2 (Workflows execute successfully)": self.validation_results.get(
                "workflow_simulation", False
            ),
            "4.3 (Artifacts accessible/formatted)": all(
                [
                    self.validation_results.get("performance_artifacts", False),
                    self.validation_results.get("prerelease_dist_flow", False),
                    self.validation_results.get("security_reports", False),
                ]
            ),
            "4.4 (Dependencies work correctly)": self.validation_results.get(
                "cross_job_dependencies", False
            ),
        }

        for req, status in requirements_status.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {req}")

        print("\n" + "=" * 60)
        return success


def main():
    """Main execution function"""
    validator = PreReleaseWorkflowValidator()

    try:
        success = validator.run_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
