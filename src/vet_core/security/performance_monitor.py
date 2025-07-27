"""
Performance monitoring and regression testing for dependency upgrades.

This module provides functionality to measure and track performance metrics
during dependency upgrades to detect regressions.
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil

from .subprocess_utils import (
    SubprocessSecurityError,
    secure_subprocess_run,
    validate_module_name,
    validate_package_name,
    validate_test_command,
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    import_time: float = 0.0  # Time to import main modules (seconds)
    test_execution_time: float = 0.0  # Time to run test suite (seconds)
    memory_usage_peak: float = 0.0  # Peak memory usage (MB)
    memory_usage_baseline: float = 0.0  # Baseline memory usage (MB)
    package_size: float = 0.0  # Installed package size (MB)
    startup_time: float = 0.0  # Application startup time (seconds)
    cpu_usage_avg: float = 0.0  # Average CPU usage during tests (%)
    disk_io_read: float = 0.0  # Disk read operations (MB)
    disk_io_write: float = 0.0  # Disk write operations (MB)
    timestamp: datetime = field(default_factory=datetime.now)
    python_version: str = field(default_factory=lambda: sys.version.split()[0])

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "import_time": self.import_time,
            "test_execution_time": self.test_execution_time,
            "memory_usage_peak": self.memory_usage_peak,
            "memory_usage_baseline": self.memory_usage_baseline,
            "package_size": self.package_size,
            "startup_time": self.startup_time,
            "cpu_usage_avg": self.cpu_usage_avg,
            "disk_io_read": self.disk_io_read,
            "disk_io_write": self.disk_io_write,
            "timestamp": self.timestamp.isoformat(),
            "python_version": self.python_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceMetrics":
        """Create metrics from dictionary."""
        data = data.copy()
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class PerformanceRegression:
    """Information about a detected performance regression."""

    metric_name: str
    baseline_value: float
    current_value: float
    regression_percent: float
    threshold_percent: float
    severity: str  # "minor", "moderate", "severe"

    @property
    def is_significant(self) -> bool:
        """Check if regression is significant."""
        return self.regression_percent > self.threshold_percent


class PerformanceMonitor:
    """Monitor and track performance metrics during dependency upgrades."""

    def __init__(
        self,
        project_root: Path,
        baseline_file: Optional[Path] = None,
        regression_thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize performance monitor.

        Args:
            project_root: Path to project root directory
            baseline_file: Path to baseline metrics file
            regression_thresholds: Thresholds for regression detection (as percentages)
        """
        self.project_root = Path(project_root)
        self.baseline_file = baseline_file or (
            self.project_root / "performance_baseline.json"
        )

        # Default regression thresholds (as percentages)
        self.regression_thresholds = regression_thresholds or {
            "import_time": 20.0,  # 20% increase
            "test_execution_time": 15.0,  # 15% increase
            "memory_usage_peak": 25.0,  # 25% increase
            "package_size": 30.0,  # 30% increase
            "startup_time": 20.0,  # 20% increase
            "cpu_usage_avg": 25.0,  # 25% increase
        }

        self.process = psutil.Process()
        self.baseline_metrics: Optional[PerformanceMetrics] = None

    def load_baseline(self) -> Optional[PerformanceMetrics]:
        """Load baseline performance metrics."""
        if not self.baseline_file.exists():
            logger.warning(f"Baseline file not found: {self.baseline_file}")
            return None

        try:
            with open(self.baseline_file, "r") as f:
                data = json.load(f)
                self.baseline_metrics = PerformanceMetrics.from_dict(data)
                return self.baseline_metrics
        except Exception as e:
            logger.error(f"Failed to load baseline metrics: {e}")
            return None

    def save_baseline(self, metrics: PerformanceMetrics) -> None:
        """Save performance metrics as baseline."""
        try:
            with open(self.baseline_file, "w") as f:
                json.dump(metrics.to_dict(), f, indent=2)
            logger.info(f"Baseline metrics saved to {self.baseline_file}")
        except Exception as e:
            logger.error(f"Failed to save baseline metrics: {e}")

    def measure_import_time(self, modules: List[str]) -> float:
        """
        Measure time to import specified modules.

        Args:
            modules: List of module names to import

        Returns:
            Total import time in seconds
        """
        total_time = 0.0

        for module in modules:
            start_time = time.time()
            try:
                # Validate module name for security
                validated_module = validate_module_name(module)

                # Use secure subprocess to get clean import timing
                # nosec B603: Using secure subprocess wrapper with validation
                result = secure_subprocess_run(
                    [sys.executable, "-c", f"import {validated_module}"],
                    validate_first_arg=False,  # sys.executable is trusted
                    timeout=30,
                )

                if result.returncode == 0:
                    end_time = time.time()
                    import_time = end_time - start_time
                    total_time += import_time
                    logger.debug(f"Import time for {module}: {import_time:.4f}s")
                else:
                    logger.warning(f"Failed to import {module}: {result.stderr}")

            except SubprocessSecurityError as e:
                logger.error(f"Security validation failed for module {module}: {e}")
                continue
            except Exception as e:
                if "timeout" in str(e).lower():
                    logger.error(f"Import timeout for {module}")
                    total_time += 30.0  # Penalty for timeout
                else:
                    logger.error(f"Error measuring import time for {module}: {e}")

        return total_time

    def measure_test_execution_time(self, test_command: str = "pytest") -> float:
        """
        Measure test suite execution time.

        Args:
            test_command: Command to run tests

        Returns:
            Test execution time in seconds
        """
        start_time = time.time()

        try:
            # Validate test command for security
            validated_test_command = validate_test_command(test_command)

            # Change to project root
            original_cwd = os.getcwd()
            os.chdir(self.project_root)

            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                [sys.executable, "-m", validated_test_command, "--tb=no", "-q"],
                validate_first_arg=False,  # sys.executable is trusted
                timeout=600,
            )  # 10 minute timeout

            end_time = time.time()
            execution_time = end_time - start_time

            if result.returncode == 0:
                logger.info(f"Test execution time: {execution_time:.2f}s")
            else:
                logger.warning(f"Tests failed, execution time: {execution_time:.2f}s")

            return execution_time

        except SubprocessSecurityError as e:
            logger.error(
                f"Security validation failed for test command {test_command}: {e}"
            )
            return 0.0
        except Exception as e:
            if "timeout" in str(e).lower():
                logger.error("Test execution timed out")
                return 600.0  # Return timeout value
            else:
                logger.error(f"Error measuring test execution time: {e}")
                return 0.0
        finally:
            os.chdir(original_cwd)

    def measure_memory_usage(self, operation: Callable[[], Any]) -> Dict[str, float]:
        """
        Measure memory usage during an operation.

        Args:
            operation: Function to execute while monitoring memory

        Returns:
            Dictionary with baseline and peak memory usage in MB
        """
        # Get baseline memory usage
        baseline_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = baseline_memory

        # Monitor memory during operation
        def memory_monitor() -> None:
            nonlocal peak_memory
            while True:
                try:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    peak_memory = max(peak_memory, current_memory)
                    time.sleep(0.1)  # Check every 100ms
                except:
                    break

        import threading

        monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        monitor_thread.start()

        try:
            # Execute the operation
            operation()
        finally:
            # Stop monitoring (thread will exit when main thread exits)
            pass

        return {
            "baseline": baseline_memory,
            "peak": peak_memory,
        }

    def measure_package_size(self, package_name: str) -> float:
        """
        Measure installed package size.

        Args:
            package_name: Name of the package

        Returns:
            Package size in MB
        """
        try:
            # Validate package name for security
            validated_package_name = validate_package_name(package_name)

            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                [sys.executable, "-m", "pip", "show", validated_package_name],
                validate_first_arg=False,  # sys.executable is trusted
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Location:"):
                        location = line.split(":", 1)[1].strip()
                        package_path = Path(location) / validated_package_name.replace(
                            "-", "_"
                        )

                        if package_path.exists():
                            size_bytes = sum(
                                f.stat().st_size
                                for f in package_path.rglob("*")
                                if f.is_file()
                            )
                            return size_bytes / 1024 / 1024  # Convert to MB

            logger.warning(f"Could not determine size for package {package_name}")
            return 0.0

        except SubprocessSecurityError as e:
            logger.error(f"Security validation failed for package {package_name}: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Error measuring package size for {package_name}: {e}")
            return 0.0

    def measure_startup_time(self, startup_command: List[str]) -> float:
        """
        Measure application startup time.

        Args:
            startup_command: Command to start the application

        Returns:
            Startup time in seconds
        """
        start_time = time.time()

        try:
            # Validate startup command for security
            if not startup_command or not isinstance(startup_command, list):
                raise SubprocessSecurityError(
                    "Startup command must be a non-empty list"
                )

            # Log the command being executed for security auditing
            logger.info(f"Executing startup command: {' '.join(startup_command)}")

            # nosec B603: Using secure subprocess wrapper with validation
            # Note: This accepts arbitrary commands by design for performance testing
            # but logs the command for security auditing
            result = secure_subprocess_run(
                startup_command,
                validate_first_arg=True,  # Validate executable path
                timeout=30,
                cwd=self.project_root,
            )

            end_time = time.time()
            startup_time = end_time - start_time

            if result.returncode == 0:
                logger.info(f"Startup time: {startup_time:.2f}s")
            else:
                logger.warning(f"Startup failed, time: {startup_time:.2f}s")

            return startup_time

        except SubprocessSecurityError as e:
            logger.error(f"Security validation failed for startup command: {e}")
            return 0.0
        except Exception as e:
            if "timeout" in str(e).lower():
                logger.error("Startup timed out")
                return 30.0
            else:
                logger.error(f"Error measuring startup time: {e}")
                return 0.0

    def measure_cpu_usage(
        self, operation: Callable[[], Any], duration: float = 10.0
    ) -> float:
        """
        Measure average CPU usage during an operation.

        Args:
            operation: Function to execute while monitoring CPU
            duration: Maximum duration to monitor (seconds)

        Returns:
            Average CPU usage percentage
        """
        cpu_samples = []
        start_time = time.time()

        def cpu_monitor() -> None:
            while time.time() - start_time < duration:
                try:
                    cpu_percent = self.process.cpu_percent(interval=0.1)
                    cpu_samples.append(cpu_percent)
                except:
                    break

        import threading

        monitor_thread = threading.Thread(target=cpu_monitor, daemon=True)
        monitor_thread.start()

        try:
            operation()
        finally:
            pass

        # Wait for monitoring to complete or timeout
        monitor_thread.join(timeout=1.0)

        if cpu_samples:
            return sum(cpu_samples) / len(cpu_samples)
        return 0.0

    def measure_disk_io(self, operation: Callable[[], Any]) -> Dict[str, float]:
        """
        Measure disk I/O during an operation.

        Args:
            operation: Function to execute while monitoring I/O

        Returns:
            Dictionary with read and write I/O in MB
        """
        # Get initial I/O counters
        initial_io = self.process.io_counters()

        try:
            operation()
        except Exception as e:
            logger.error(f"Error during I/O monitoring operation: {e}")

        # Get final I/O counters
        final_io = self.process.io_counters()

        read_mb = (final_io.read_bytes - initial_io.read_bytes) / 1024 / 1024
        write_mb = (final_io.write_bytes - initial_io.write_bytes) / 1024 / 1024

        return {
            "read": read_mb,
            "write": write_mb,
        }

    def collect_comprehensive_metrics(
        self,
        modules_to_import: Optional[List[str]] = None,
        packages_to_measure: Optional[List[str]] = None,
        test_command: str = "pytest",
        startup_command: Optional[List[str]] = None,
    ) -> PerformanceMetrics:
        """
        Collect comprehensive performance metrics.

        Args:
            modules_to_import: List of modules to measure import time
            packages_to_measure: List of packages to measure size
            test_command: Command to run tests
            startup_command: Command to measure startup time

        Returns:
            PerformanceMetrics object with all measurements
        """
        logger.info("Collecting comprehensive performance metrics...")

        metrics = PerformanceMetrics()

        # Default modules to import
        if modules_to_import is None:
            modules_to_import = ["vet_core", "vet_core.models", "vet_core.database"]

        # Default packages to measure
        if packages_to_measure is None:
            packages_to_measure = ["vet_core"]

        # Measure import time
        try:
            metrics.import_time = self.measure_import_time(modules_to_import)
        except Exception as e:
            logger.error(f"Failed to measure import time: {e}")

        # Measure test execution time with memory monitoring
        def run_tests() -> None:
            metrics.test_execution_time = self.measure_test_execution_time(test_command)

        try:
            memory_usage = self.measure_memory_usage(run_tests)
            metrics.memory_usage_baseline = memory_usage["baseline"]
            metrics.memory_usage_peak = memory_usage["peak"]
        except Exception as e:
            logger.error(f"Failed to measure test execution and memory: {e}")

        # Measure package sizes
        try:
            total_size = 0.0
            for package in packages_to_measure:
                size = self.measure_package_size(package)
                total_size += size
            metrics.package_size = total_size
        except Exception as e:
            logger.error(f"Failed to measure package size: {e}")

        # Measure startup time if command provided
        if startup_command:
            try:
                metrics.startup_time = self.measure_startup_time(startup_command)
            except Exception as e:
                logger.error(f"Failed to measure startup time: {e}")

        # Measure CPU usage during a simple operation
        def simple_operation() -> None:
            time.sleep(1)  # Simple operation for CPU measurement

        try:
            metrics.cpu_usage_avg = self.measure_cpu_usage(simple_operation)
        except Exception as e:
            logger.error(f"Failed to measure CPU usage: {e}")

        # Measure disk I/O during test execution
        def test_operation() -> None:
            self.measure_test_execution_time(test_command)

        try:
            disk_io = self.measure_disk_io(test_operation)
            metrics.disk_io_read = disk_io["read"]
            metrics.disk_io_write = disk_io["write"]
        except Exception as e:
            logger.error(f"Failed to measure disk I/O: {e}")

        logger.info("Performance metrics collection completed")
        return metrics

    def detect_regressions(
        self,
        current_metrics: PerformanceMetrics,
        baseline_metrics: Optional[PerformanceMetrics] = None,
    ) -> List[PerformanceRegression]:
        """
        Detect performance regressions by comparing current metrics to baseline.

        Args:
            current_metrics: Current performance metrics
            baseline_metrics: Baseline metrics to compare against

        Returns:
            List of detected regressions
        """
        if baseline_metrics is None:
            baseline_metrics = self.load_baseline()

        if baseline_metrics is None:
            logger.warning("No baseline metrics available for regression detection")
            return []

        regressions = []

        # Check each metric for regressions
        for metric_name, threshold in self.regression_thresholds.items():
            baseline_value = getattr(baseline_metrics, metric_name, 0.0)
            current_value = getattr(current_metrics, metric_name, 0.0)

            if baseline_value > 0:  # Avoid division by zero
                regression_percent = (
                    (current_value - baseline_value) / baseline_value
                ) * 100

                if regression_percent > threshold:
                    # Determine severity
                    if regression_percent > threshold * 2:
                        severity = "severe"
                    elif regression_percent > threshold * 1.5:
                        severity = "moderate"
                    else:
                        severity = "minor"

                    regression = PerformanceRegression(
                        metric_name=metric_name,
                        baseline_value=baseline_value,
                        current_value=current_value,
                        regression_percent=regression_percent,
                        threshold_percent=threshold,
                        severity=severity,
                    )

                    regressions.append(regression)
                    logger.warning(
                        f"Performance regression detected in {metric_name}: "
                        f"{regression_percent:.1f}% increase "
                        f"(threshold: {threshold}%, severity: {severity})"
                    )

        return regressions

    def generate_performance_report(
        self,
        current_metrics: PerformanceMetrics,
        regressions: List[PerformanceRegression],
        output_file: Optional[Path] = None,
    ) -> str:
        """
        Generate a comprehensive performance report.

        Args:
            current_metrics: Current performance metrics
            regressions: List of detected regressions
            output_file: Optional file to save the report

        Returns:
            Report content as string
        """
        report_lines = [
            "# Performance Analysis Report",
            f"Generated: {datetime.now().isoformat()}",
            f"Python Version: {current_metrics.python_version}",
            "",
            "## Current Performance Metrics",
            f"- Import Time: {current_metrics.import_time:.4f}s",
            f"- Test Execution Time: {current_metrics.test_execution_time:.2f}s",
            f"- Memory Usage (Baseline): {current_metrics.memory_usage_baseline:.1f} MB",
            f"- Memory Usage (Peak): {current_metrics.memory_usage_peak:.1f} MB",
            f"- Package Size: {current_metrics.package_size:.1f} MB",
            f"- Startup Time: {current_metrics.startup_time:.2f}s",
            f"- CPU Usage (Average): {current_metrics.cpu_usage_avg:.1f}%",
            f"- Disk I/O (Read): {current_metrics.disk_io_read:.2f} MB",
            f"- Disk I/O (Write): {current_metrics.disk_io_write:.2f} MB",
            "",
        ]

        if regressions:
            report_lines.extend(
                [
                    "## Performance Regressions Detected",
                    "",
                ]
            )

            for regression in regressions:
                report_lines.extend(
                    [
                        f"### {regression.metric_name} ({regression.severity.upper()})",
                        f"- Baseline: {regression.baseline_value:.4f}",
                        f"- Current: {regression.current_value:.4f}",
                        f"- Regression: {regression.regression_percent:.1f}% increase",
                        f"- Threshold: {regression.threshold_percent:.1f}%",
                        "",
                    ]
                )
        else:
            report_lines.extend(
                [
                    "## Performance Status",
                    "✅ No significant performance regressions detected",
                    "",
                ]
            )

        report_content = "\n".join(report_lines)

        if output_file:
            try:
                output_file.write_text(report_content)
                logger.info(f"Performance report saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save performance report: {e}")

        return report_content
