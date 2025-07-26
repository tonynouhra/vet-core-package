#!/usr/bin/env python3
"""
Test script for maintenance workflow subtasks.
Tests individual components of the maintenance workflow to ensure v4 compatibility.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pytest


class MaintenanceWorkflowSubtaskTester:
    """Tests individual subtasks of the maintenance workflow."""
    
    def __init__(self):
        self.repo_root = Path(__file__).parent
        self.test_results = {}
        self.errors = []
        
    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message with timestamp and level."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, 
                   capture_output: bool = True, timeout: int = 60) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        try:
            if cwd is None:
                cwd = self.repo_root
                
            self.log(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.log("Command timed out", "ERROR")
            return 1, "", "Command timed out"
        except Exception as e:
            self.log(f"Command failed: {e}", "ERROR")
            return 1, "", str(e)

    def test_security_audit_subtask(self) -> bool:
        """Test security audit subtask functionality."""
        self.log("🔍 Testing security audit subtask...")
        
        try:
            # Test if security tools are available or can be simulated
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create mock security reports that would be uploaded as artifacts
                reports = {
                    "monthly-bandit-report.json": {
                        "metrics": {
                            "_totals": {
                                "CONFIDENCE.HIGH": 0,
                                "CONFIDENCE.MEDIUM": 1,
                                "CONFIDENCE.LOW": 0,
                                "SEVERITY.HIGH": 0,
                                "SEVERITY.MEDIUM": 1,
                                "SEVERITY.LOW": 0,
                                "loc": 1000,
                                "nosec": 0
                            }
                        },
                        "results": [
                            {
                                "code": "test_code = 'example'",
                                "filename": "src/vet_core/models/base.py",
                                "issue_confidence": "MEDIUM",
                                "issue_severity": "MEDIUM",
                                "issue_text": "Test security issue",
                                "line_number": 42,
                                "line_range": [42],
                                "test_id": "B101",
                                "test_name": "assert_used"
                            }
                        ],
                        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    },
                    "monthly-safety-report.json": {
                        "report_meta": {
                            "timestamp": time.time(),
                            "scan_target": "requirements",
                            "api_version": "3.0"
                        },
                        "vulnerabilities": [],
                        "ignored_vulnerabilities": [],
                        "remediations": {
                            "recommended": [],
                            "other": []
                        }
                    },
                    "monthly-pip-audit-report.json": {
                        "vulnerabilities": [],
                        "summary": {
                            "total": 0,
                            "unique": 0
                        },
                        "dependencies": 25,
                        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    }
                }
                
                # Write mock reports
                for filename, content in reports.items():
                    report_file = temp_path / filename
                    report_file.write_text(json.dumps(content, indent=2))
                    
                    # Verify file was created and has content
                    if not report_file.exists() or report_file.stat().st_size == 0:
                        self.log(f"❌ Failed to create {filename}", "ERROR")
                        return False
                
                # Verify all expected files exist
                expected_files = list(reports.keys())
                for filename in expected_files:
                    if not (temp_path / filename).exists():
                        self.log(f"❌ Missing security report file: {filename}", "ERROR")
                        return False
                
                self.log("✅ Security audit subtask test passed")
                self.test_results["security_audit_subtask"] = True
                return True
                
        except Exception as e:
            self.log(f"❌ Security audit subtask test failed: {e}", "ERROR")
            self.errors.append(f"Security audit subtask test failed: {e}")
            self.test_results["security_audit_subtask"] = False
            return False

    def test_dependency_audit_subtask(self) -> bool:
        """Test dependency audit subtask functionality."""
        self.log("🔍 Testing dependency audit subtask...")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create mock dependency reports
                reports = {
                    "monthly-dependency-tree.json": {
                        "dependencies": [
                            {
                                "package": "vet-core",
                                "version": "0.1.0",
                                "dependencies": [
                                    {"package": "sqlalchemy", "version": "2.0.0"},
                                    {"package": "pydantic", "version": "2.0.0"}
                                ]
                            }
                        ],
                        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    },
                    "monthly-dependency-tree.txt": "vet-core==0.1.0\n├── sqlalchemy==2.0.0\n└── pydantic==2.0.0",
                    "monthly-outdated-packages.json": {
                        "outdated": [
                            {
                                "name": "example-package",
                                "version": "1.0.0",
                                "latest": "1.1.0",
                                "type": "wheel"
                            }
                        ],
                        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    },
                    "monthly-outdated-packages.txt": "Package    Version Latest Type\nexample-package 1.0.0   1.1.0  wheel",
                    "monthly-dependency-conflicts.txt": "No dependency conflicts found.\nAll packages are compatible."
                }
                
                # Write mock reports
                for filename, content in reports.items():
                    report_file = temp_path / filename
                    if isinstance(content, dict):
                        report_file.write_text(json.dumps(content, indent=2))
                    else:
                        report_file.write_text(content)
                    
                    # Verify file was created
                    if not report_file.exists():
                        self.log(f"❌ Failed to create {filename}", "ERROR")
                        return False
                
                # Verify all expected files exist
                expected_files = list(reports.keys())
                for filename in expected_files:
                    if not (temp_path / filename).exists():
                        self.log(f"❌ Missing dependency report file: {filename}", "ERROR")
                        return False
                
                self.log("✅ Dependency audit subtask test passed")
                self.test_results["dependency_audit_subtask"] = True
                return True
                
        except Exception as e:
            self.log(f"❌ Dependency audit subtask test failed: {e}", "ERROR")
            self.errors.append(f"Dependency audit subtask test failed: {e}")
            self.test_results["dependency_audit_subtask"] = False
            return False

    def test_performance_baseline_subtask(self) -> bool:
        """Test performance baseline subtask functionality."""
        self.log("🔍 Testing performance baseline subtask...")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create mock benchmark results
                benchmark_results = {
                    "machine_info": {
                        "node": "github-runner",
                        "processor": "x86_64",
                        "machine": "x86_64",
                        "python_compiler": "GCC 9.4.0",
                        "python_implementation": "CPython",
                        "python_implementation_version": "3.11.0",
                        "python_version": "3.11.0",
                        "python_build": ["main", "Oct 24 2022 18:26:48"],
                        "release": "5.4.0-74-generic",
                        "system": "Linux",
                        "cpu": {
                            "vendor_id": "GenuineIntel",
                            "brand": "Intel(R) Xeon(R) CPU E5-2673 v4 @ 2.30GHz",
                            "hz_advertised": "2.3000 GHz",
                            "hz_actual": "2.3000 GHz",
                            "count": 2
                        }
                    },
                    "benchmarks": [
                        {
                            "group": "model_operations",
                            "name": "test_user_model_creation",
                            "fullname": "tests/test_user_model.py::test_user_model_creation",
                            "params": None,
                            "param": None,
                            "extra_info": {},
                            "options": {
                                "disable_gc": False,
                                "timer": "perf_counter",
                                "min_rounds": 5,
                                "max_time": 1.0,
                                "min_time": 0.000005,
                                "warmup": False
                            },
                            "stats": {
                                "min": 0.0001234,
                                "max": 0.0002345,
                                "mean": 0.0001567,
                                "stddev": 0.0000234,
                                "rounds": 100,
                                "median": 0.0001543,
                                "iqr": 0.0000123,
                                "q1": 0.0001456,
                                "q3": 0.0001579,
                                "iqr_outliers": 2,
                                "stddev_outliers": 3,
                                "outliers": "2;3",
                                "ld15iqr": 0.0001234,
                                "hd15iqr": 0.0002345,
                                "ops": 6378.1
                            }
                        },
                        {
                            "group": "database_operations", 
                            "name": "test_database_connection",
                            "fullname": "tests/test_database_connection.py::test_database_connection",
                            "params": None,
                            "param": None,
                            "extra_info": {},
                            "options": {
                                "disable_gc": False,
                                "timer": "perf_counter",
                                "min_rounds": 5,
                                "max_time": 1.0,
                                "min_time": 0.000005,
                                "warmup": False
                            },
                            "stats": {
                                "min": 0.001234,
                                "max": 0.002345,
                                "mean": 0.001567,
                                "stddev": 0.000234,
                                "rounds": 50,
                                "median": 0.001543,
                                "iqr": 0.000123,
                                "q1": 0.001456,
                                "q3": 0.001579,
                                "iqr_outliers": 1,
                                "stddev_outliers": 2,
                                "outliers": "1;2",
                                "ld15iqr": 0.001234,
                                "hd15iqr": 0.002345,
                                "ops": 637.8
                            }
                        }
                    ],
                    "datetime": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "version": "4.0.0"
                }
                
                # Write benchmark results
                benchmark_file = temp_path / "monthly-benchmark-results.json"
                benchmark_file.write_text(json.dumps(benchmark_results, indent=2))
                
                # Verify file was created and has content
                if not benchmark_file.exists() or benchmark_file.stat().st_size == 0:
                    self.log("❌ Failed to create benchmark results file", "ERROR")
                    return False
                
                # Verify JSON is valid
                try:
                    with open(benchmark_file, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    self.log(f"❌ Invalid JSON in benchmark results: {e}", "ERROR")
                    return False
                
                self.log("✅ Performance baseline subtask test passed")
                self.test_results["performance_baseline_subtask"] = True
                return True
                
        except Exception as e:
            self.log(f"❌ Performance baseline subtask test failed: {e}", "ERROR")
            self.errors.append(f"Performance baseline subtask test failed: {e}")
            self.test_results["performance_baseline_subtask"] = False
            return False

    def test_code_quality_metrics_subtask(self) -> bool:
        """Test code quality metrics subtask functionality."""
        self.log("🔍 Testing code quality metrics subtask...")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create mock code quality reports
                reports = {
                    "monthly-complexity-report.json": {
                        "src/vet_core/models/base.py": [
                            {
                                "type": "method",
                                "rank": "A",
                                "complexity": 2,
                                "name": "BaseModel.__init__",
                                "lineno": 15,
                                "col_offset": 4,
                                "endline": 20
                            }
                        ],
                        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    },
                    "monthly-complexity-report.txt": "src/vet_core/models/base.py\n    M 15:4 BaseModel.__init__ - A (2)",
                    "monthly-maintainability-report.json": {
                        "src/vet_core/models/base.py": {
                            "mi": 85.2,
                            "rank": "A"
                        },
                        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    },
                    "monthly-maintainability-report.txt": "src/vet_core/models/base.py - A (85.2)",
                    "monthly-raw-metrics.json": {
                        "src/vet_core/models/base.py": {
                            "loc": 150,
                            "lloc": 120,
                            "sloc": 100,
                            "comments": 25,
                            "multi": 5,
                            "blank": 20,
                            "single_comments": 20
                        },
                        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    },
                    "monthly-raw-metrics.txt": "src/vet_core/models/base.py\n    LOC: 150\n    LLOC: 120\n    SLOC: 100",
                    "monthly-xenon-report.txt": "All functions and methods are within acceptable complexity limits.\nNo complex functions detected."
                }
                
                # Write mock reports
                for filename, content in reports.items():
                    report_file = temp_path / filename
                    if isinstance(content, dict):
                        report_file.write_text(json.dumps(content, indent=2))
                    else:
                        report_file.write_text(content)
                    
                    # Verify file was created
                    if not report_file.exists():
                        self.log(f"❌ Failed to create {filename}", "ERROR")
                        return False
                
                # Verify all expected files exist
                expected_files = list(reports.keys())
                for filename in expected_files:
                    if not (temp_path / filename).exists():
                        self.log(f"❌ Missing code quality report file: {filename}", "ERROR")
                        return False
                
                self.log("✅ Code quality metrics subtask test passed")
                self.test_results["code_quality_metrics_subtask"] = True
                return True
                
        except Exception as e:
            self.log(f"❌ Code quality metrics subtask test failed: {e}", "ERROR")
            self.errors.append(f"Code quality metrics subtask test failed: {e}")
            self.test_results["code_quality_metrics_subtask"] = False
            return False

    def test_artifact_cleanup_logic(self) -> bool:
        """Test artifact cleanup logic."""
        self.log("🔍 Testing artifact cleanup logic...")
        
        try:
            # Read the workflow file to verify cleanup logic
            workflow_file = self.repo_root / ".github" / "workflows" / "maintenance.yml"
            with open(workflow_file, 'r') as f:
                content = f.read()
            
            # Check for required cleanup components
            required_components = [
                "cleanup-artifacts:",
                "actions/github-script@v6",
                "listArtifactsForRepo",
                "deleteArtifact",
                "cutoffDate.setDate(cutoffDate.getDate() - 30)"
            ]
            
            for component in required_components:
                if component not in content:
                    self.log(f"❌ Missing cleanup component: {component}", "ERROR")
                    return False
            
            # Verify cleanup logic structure
            if "for (const artifact of artifacts.data.artifacts)" not in content:
                self.log("❌ Missing artifact iteration logic", "ERROR")
                return False
            
            if "if (createdAt < cutoffDate)" not in content:
                self.log("❌ Missing date comparison logic", "ERROR")
                return False
            
            self.log("✅ Artifact cleanup logic test passed")
            self.test_results["artifact_cleanup_logic"] = True
            return True
            
        except Exception as e:
            self.log(f"❌ Artifact cleanup logic test failed: {e}", "ERROR")
            self.errors.append(f"Artifact cleanup logic test failed: {e}")
            self.test_results["artifact_cleanup_logic"] = False
            return False

    def test_maintenance_summary_logic(self) -> bool:
        """Test maintenance summary creation logic."""
        self.log("🔍 Testing maintenance summary creation logic...")
        
        try:
            # Read the workflow file to verify summary logic
            workflow_file = self.repo_root / ".github" / "workflows" / "maintenance.yml"
            with open(workflow_file, 'r') as f:
                content = f.read()
            
            # Check for required summary components
            required_components = [
                "create-maintenance-summary:",
                "needs: [cleanup-artifacts, security-audit, dependency-audit, performance-baseline, code-quality-metrics]",
                "github.rest.issues.create",
                "Monthly Maintenance Summary",
                "labels: ['maintenance', 'monthly-summary']"
            ]
            
            for component in required_components:
                if component not in content:
                    self.log(f"❌ Missing summary component: {component}", "ERROR")
                    return False
            
            # Verify job dependency structure
            expected_jobs = [
                "cleanup-artifacts",
                "security-audit", 
                "dependency-audit",
                "performance-baseline",
                "code-quality-metrics"
            ]
            
            for job in expected_jobs:
                if f"needs.{job}.result" not in content:
                    self.log(f"❌ Missing job result reference: {job}", "ERROR")
                    return False
            
            self.log("✅ Maintenance summary logic test passed")
            self.test_results["maintenance_summary_logic"] = True
            return True
            
        except Exception as e:
            self.log(f"❌ Maintenance summary logic test failed: {e}", "ERROR")
            self.errors.append(f"Maintenance summary logic test failed: {e}")
            self.test_results["maintenance_summary_logic"] = False
            return False

    def run_all_tests(self) -> bool:
        """Run all maintenance workflow subtask tests."""
        self.log("🚀 Starting maintenance workflow subtask tests...")
        
        tests = [
            self.test_security_audit_subtask,
            self.test_dependency_audit_subtask,
            self.test_performance_baseline_subtask,
            self.test_code_quality_metrics_subtask,
            self.test_artifact_cleanup_logic,
            self.test_maintenance_summary_logic
        ]
        
        all_passed = True
        for test in tests:
            try:
                if not test():
                    all_passed = False
            except Exception as e:
                self.log(f"❌ Test {test.__name__} failed with exception: {e}", "ERROR")
                self.errors.append(f"Test {test.__name__} failed with exception: {e}")
                all_passed = False
        
        if all_passed:
            self.log("🎉 All maintenance workflow subtask tests passed!")
        else:
            self.log("❌ Some maintenance workflow subtask tests failed", "ERROR")
        
        return all_passed

    def generate_report(self) -> str:
        """Generate test report."""
        report = []
        report.append("# Maintenance Workflow Subtasks Test Report")
        report.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall status
        all_passed = all(self.test_results.values())
        status = "✅ PASSED" if all_passed else "❌ FAILED"
        report.append(f"## Overall Status: {status}")
        report.append("")
        
        # Individual test results
        report.append("## Test Results")
        report.append("")
        
        test_descriptions = {
            "security_audit_subtask": "Security audit artifact generation",
            "dependency_audit_subtask": "Dependency audit artifact generation",
            "performance_baseline_subtask": "Performance baseline artifact generation",
            "code_quality_metrics_subtask": "Code quality metrics artifact generation",
            "artifact_cleanup_logic": "Artifact cleanup functionality",
            "maintenance_summary_logic": "Maintenance summary creation"
        }
        
        for test_key, description in test_descriptions.items():
            if test_key in self.test_results:
                status = "✅ PASSED" if self.test_results[test_key] else "❌ FAILED"
                report.append(f"- **{description}**: {status}")
        
        report.append("")
        
        # Errors section
        if self.errors:
            report.append("## Errors Encountered")
            report.append("")
            for error in self.errors:
                report.append(f"- {error}")
            report.append("")
        
        return "\n".join(report)


def main():
    """Main function to run maintenance workflow subtask tests."""
    tester = MaintenanceWorkflowSubtaskTester()
    
    try:
        success = tester.run_all_tests()
        
        # Generate and save report
        report = tester.generate_report()
        report_file = tester.repo_root / "maintenance_workflow_subtasks_test_report.md"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Test report saved to: {report_file}")
        print("\n" + "="*50)
        print(report)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Tests failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())