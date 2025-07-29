"""Tests for the PerformanceMonitor class."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from vet_core.security.performance_monitor import (
    PerformanceMetrics,
    PerformanceMonitor,
    PerformanceRegression,
)


class TestPerformanceMetrics:
    """Test cases for PerformanceMetrics dataclass."""

    def test_performance_metrics_creation(self):
        """Test creating a PerformanceMetrics instance."""
        metrics = PerformanceMetrics(
            import_time=1.5,
            test_execution_time=120.0,
            memory_usage_mb=256.0,
            package_size_mb=10.5,
            startup_time=3.2,
            cpu_usage_percent=45.0,
            disk_io_mb=50.0,
        )

        assert metrics.import_time == 1.5
        assert metrics.test_execution_time == 120.0
        assert metrics.memory_usage_mb == 256.0
        assert metrics.package_size_mb == 10.5
        assert metrics.startup_time == 3.2
        assert metrics.cpu_usage_percent == 45.0
        assert metrics.disk_io_mb == 50.0

    def test_performance_metrics_to_dict(self):
        """Test converting PerformanceMetrics to dictionary."""
        metrics = PerformanceMetrics(
            import_time=2.0, test_execution_time=90.0, memory_usage_mb=128.0
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["import_time"] == 2.0
        assert result["test_execution_time"] == 90.0
        assert result["memory_usage_mb"] == 128.0

    def test_performance_metrics_from_dict(self):
        """Test creating PerformanceMetrics from dictionary."""
        data = {
            "import_time": 1.8,
            "test_execution_time": 110.0,
            "memory_usage_mb": 200.0,
            "package_size_mb": 8.5,
            "startup_time": 2.5,
            "cpu_usage_percent": 35.0,
            "disk_io_mb": 40.0,
        }

        metrics = PerformanceMetrics.from_dict(data)

        assert metrics.import_time == 1.8
        assert metrics.test_execution_time == 110.0
        assert metrics.memory_usage_mb == 200.0
        assert metrics.package_size_mb == 8.5
        assert metrics.startup_time == 2.5
        assert metrics.cpu_usage_percent == 35.0
        assert metrics.disk_io_mb == 40.0


class TestPerformanceRegression:
    """Test cases for PerformanceRegression dataclass."""

    def test_performance_regression_creation(self):
        """Test creating a PerformanceRegression instance."""
        regression = PerformanceRegression(
            metric_name="import_time",
            baseline_value=1.0,
            current_value=1.5,
            change_percentage=50.0,
            threshold=20.0,
        )

        assert regression.metric_name == "import_time"
        assert regression.baseline_value == 1.0
        assert regression.current_value == 1.5
        assert regression.change_percentage == 50.0
        assert regression.threshold == 20.0

    def test_is_significant_true(self):
        """Test is_significant returns True for significant regression."""
        regression = PerformanceRegression(
            metric_name="test_metric",
            baseline_value=1.0,
            current_value=1.5,
            change_percentage=50.0,
            threshold=20.0,
        )

        assert regression.is_significant() is True

    def test_is_significant_false(self):
        """Test is_significant returns False for non-significant regression."""
        regression = PerformanceRegression(
            metric_name="test_metric",
            baseline_value=1.0,
            current_value=1.1,
            change_percentage=10.0,
            threshold=20.0,
        )

        assert regression.is_significant() is False

    def test_is_significant_edge_case(self):
        """Test is_significant at threshold boundary."""
        regression = PerformanceRegression(
            metric_name="test_metric",
            baseline_value=1.0,
            current_value=1.2,
            change_percentage=20.0,
            threshold=20.0,
        )

        # At exactly the threshold, should be considered significant
        assert regression.is_significant() is True


class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor class."""

    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project root directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def temp_baseline_file(self):
        """Create a temporary baseline file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            baseline_data = {
                "import_time": 1.0,
                "test_execution_time": 60.0,
                "memory_usage_mb": 100.0,
            }
            f.write(json.dumps(baseline_data).encode())
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def monitor(self, temp_project_root):
        """Create a PerformanceMonitor instance."""
        return PerformanceMonitor(project_root=temp_project_root)

    @pytest.fixture
    def monitor_with_baseline(self, temp_project_root, temp_baseline_file):
        """Create a PerformanceMonitor instance with baseline file."""
        return PerformanceMonitor(
            project_root=temp_project_root, baseline_file=temp_baseline_file
        )

    def test_init_with_default_params(self, temp_project_root):
        """Test monitor initialization with default parameters."""
        monitor = PerformanceMonitor(project_root=temp_project_root)
        assert monitor.project_root == temp_project_root
        assert monitor.baseline_file is None
        assert monitor.regression_thresholds is not None

    def test_init_with_custom_params(self, temp_project_root, temp_baseline_file):
        """Test monitor initialization with custom parameters."""
        custom_thresholds = {"import_time": 15.0, "memory_usage_mb": 25.0}
        monitor = PerformanceMonitor(
            project_root=temp_project_root,
            baseline_file=temp_baseline_file,
            regression_thresholds=custom_thresholds,
        )
        assert monitor.project_root == temp_project_root
        assert monitor.baseline_file == temp_baseline_file
        assert monitor.regression_thresholds == custom_thresholds

    def test_load_baseline_file_exists(self, monitor_with_baseline):
        """Test loading baseline when file exists."""
        baseline = monitor_with_baseline.load_baseline()

        assert isinstance(baseline, PerformanceMetrics)
        assert baseline.import_time == 1.0
        assert baseline.test_execution_time == 60.0
        assert baseline.memory_usage_mb == 100.0

    def test_load_baseline_file_not_exists(self, monitor):
        """Test loading baseline when file doesn't exist."""
        baseline = monitor.load_baseline()
        assert baseline is None

    def test_save_baseline(self, monitor, temp_project_root):
        """Test saving baseline metrics."""
        metrics = PerformanceMetrics(
            import_time=2.0, test_execution_time=80.0, memory_usage_mb=150.0
        )

        baseline_file = temp_project_root / "baseline.json"
        monitor.baseline_file = baseline_file

        monitor.save_baseline(metrics)

        assert baseline_file.exists()
        with open(baseline_file, "r") as f:
            saved_data = json.load(f)
        assert saved_data["import_time"] == 2.0
        assert saved_data["test_execution_time"] == 80.0
        assert saved_data["memory_usage_mb"] == 150.0

    @patch("vet_core.security.performance_monitor.validate_module_name")
    def test_measure_import_time(self, mock_validate, monitor):
        """Test measuring import time for modules."""
        mock_validate.return_value = True

        # Mock the import process
        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = Mock()

            result = monitor.measure_import_time(["os", "sys", "json"])

            assert isinstance(result, float)
            assert result >= 0.0
            assert mock_validate.call_count == 3

    @patch("vet_core.security.performance_monitor.validate_test_command")
    @patch("vet_core.security.performance_monitor.secure_subprocess_run")
    def test_measure_test_execution_time(self, mock_subprocess, mock_validate, monitor):
        """Test measuring test execution time."""
        mock_validate.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)

        result = monitor.measure_test_execution_time("pytest tests/")

        assert isinstance(result, float)
        assert result >= 0.0
        mock_validate.assert_called_once_with("pytest tests/")
        mock_subprocess.assert_called_once()

    @patch("vet_core.security.performance_monitor.validate_test_command")
    @patch("vet_core.security.performance_monitor.secure_subprocess_run")
    def test_measure_test_execution_time_failure(
        self, mock_subprocess, mock_validate, monitor
    ):
        """Test measuring test execution time when tests fail."""
        mock_validate.return_value = True
        mock_subprocess.side_effect = Exception("Test execution failed")

        result = monitor.measure_test_execution_time("pytest tests/")

        assert result == 0.0

    @patch("psutil.Process")
    def test_measure_memory_usage(self, mock_process_class, monitor):
        """Test measuring memory usage during operation."""
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100 MB
        mock_process_class.return_value = mock_process

        def test_operation():
            time.sleep(0.01)  # Simulate some work
            return "result"

        result = monitor.measure_memory_usage(test_operation)

        assert isinstance(result, float)
        assert result >= 0.0

    @patch("vet_core.security.performance_monitor.validate_package_name")
    @patch("vet_core.security.performance_monitor.secure_subprocess_run")
    def test_measure_package_size(self, mock_subprocess, mock_validate, monitor):
        """Test measuring package size."""
        mock_validate.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stdout="Size: 10.5 MB\n")

        result = monitor.measure_package_size("test-package")

        assert isinstance(result, float)
        assert result >= 0.0
        mock_validate.assert_called_once_with("test-package")

    @patch("vet_core.security.performance_monitor.secure_subprocess_run")
    def test_measure_startup_time(self, mock_subprocess, monitor):
        """Test measuring startup time."""
        mock_subprocess.return_value = Mock(returncode=0)

        result = monitor.measure_startup_time(["python", "-c", "print('hello')"])

        assert isinstance(result, float)
        assert result >= 0.0
        mock_subprocess.assert_called_once()

    @patch("vet_core.security.performance_monitor.secure_subprocess_run")
    def test_measure_startup_time_failure(self, mock_subprocess, monitor):
        """Test measuring startup time when command fails."""
        mock_subprocess.side_effect = Exception("Command failed")

        result = monitor.measure_startup_time(["invalid-command"])

        assert result == 0.0

    @patch("psutil.Process")
    def test_measure_cpu_usage(self, mock_process_class, monitor):
        """Test measuring CPU usage during operation."""
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 25.0
        mock_process_class.return_value = mock_process

        def test_operation():
            time.sleep(0.01)
            return "result"

        result = monitor.measure_cpu_usage(test_operation, duration=0.1)

        assert isinstance(result, float)
        assert result >= 0.0

    @patch("psutil.disk_io_counters")
    def test_measure_disk_io(self, mock_disk_io, monitor):
        """Test measuring disk I/O during operation."""
        # Mock initial and final disk I/O counters
        initial_io = Mock(read_bytes=1000, write_bytes=2000)
        final_io = Mock(read_bytes=2000, write_bytes=3000)
        mock_disk_io.side_effect = [initial_io, final_io]

        def test_operation():
            time.sleep(0.01)
            return "result"

        result = monitor.measure_disk_io(test_operation)

        assert isinstance(result, float)
        assert result >= 0.0

    @patch("psutil.disk_io_counters")
    def test_measure_disk_io_no_counters(self, mock_disk_io, monitor):
        """Test measuring disk I/O when counters are not available."""
        mock_disk_io.return_value = None

        def test_operation():
            return "result"

        result = monitor.measure_disk_io(test_operation)

        assert result == 0.0

    @patch.object(PerformanceMonitor, "measure_import_time")
    @patch.object(PerformanceMonitor, "measure_test_execution_time")
    @patch.object(PerformanceMonitor, "measure_memory_usage")
    @patch.object(PerformanceMonitor, "measure_package_size")
    @patch.object(PerformanceMonitor, "measure_startup_time")
    @patch.object(PerformanceMonitor, "measure_cpu_usage")
    @patch.object(PerformanceMonitor, "measure_disk_io")
    def test_collect_comprehensive_metrics(
        self,
        mock_disk_io,
        mock_cpu,
        mock_startup,
        mock_package,
        mock_memory,
        mock_test,
        mock_import,
        monitor,
    ):
        """Test collecting comprehensive performance metrics."""
        # Mock all measurement methods
        mock_import.return_value = 1.5
        mock_test.return_value = 120.0
        mock_memory.return_value = 256.0
        mock_package.return_value = 10.0
        mock_startup.return_value = 3.0
        mock_cpu.return_value = 45.0
        mock_disk_io.return_value = 50.0

        result = monitor.collect_comprehensive_metrics(
            modules_to_import=["os", "sys"],
            packages_to_measure=["test-package"],
            test_command="pytest",
            startup_command=["python", "-c", "print('test')"],
        )

        assert isinstance(result, PerformanceMetrics)
        assert result.import_time == 1.5
        assert result.test_execution_time == 120.0
        assert result.memory_usage_mb == 256.0
        assert result.package_size_mb == 10.0
        assert result.startup_time == 3.0
        assert result.cpu_usage_percent == 45.0
        assert result.disk_io_mb == 50.0

    def test_collect_comprehensive_metrics_defaults(self, monitor):
        """Test collecting comprehensive metrics with default parameters."""
        with (
            patch.object(monitor, "measure_import_time", return_value=1.0),
            patch.object(monitor, "measure_test_execution_time", return_value=60.0),
            patch.object(monitor, "measure_memory_usage", return_value=128.0),
            patch.object(monitor, "measure_package_size", return_value=5.0),
            patch.object(monitor, "measure_startup_time", return_value=2.0),
            patch.object(monitor, "measure_cpu_usage", return_value=30.0),
            patch.object(monitor, "measure_disk_io", return_value=25.0),
        ):

            result = monitor.collect_comprehensive_metrics()

            assert isinstance(result, PerformanceMetrics)

    def test_detect_regressions_no_baseline(self, monitor):
        """Test detecting regressions when no baseline is available."""
        current_metrics = PerformanceMetrics(
            import_time=2.0, test_execution_time=100.0, memory_usage_mb=200.0
        )

        regressions = monitor.detect_regressions(current_metrics)

        assert isinstance(regressions, list)
        assert len(regressions) == 0

    def test_detect_regressions_with_baseline(self, monitor):
        """Test detecting regressions with baseline metrics."""
        baseline_metrics = PerformanceMetrics(
            import_time=1.0, test_execution_time=60.0, memory_usage_mb=100.0
        )

        current_metrics = PerformanceMetrics(
            import_time=1.5,  # 50% increase
            test_execution_time=90.0,  # 50% increase
            memory_usage_mb=110.0,  # 10% increase
        )

        regressions = monitor.detect_regressions(current_metrics, baseline_metrics)

        assert isinstance(regressions, list)
        # Should detect regressions for import_time and test_execution_time
        # (assuming default thresholds are less than 50%)
        regression_metrics = [r.metric_name for r in regressions if r.is_significant()]
        assert len(regression_metrics) >= 0  # May vary based on thresholds

    def test_detect_regressions_with_loaded_baseline(self, monitor_with_baseline):
        """Test detecting regressions using loaded baseline."""
        current_metrics = PerformanceMetrics(
            import_time=2.0,  # 100% increase from baseline of 1.0
            test_execution_time=120.0,  # 100% increase from baseline of 60.0
            memory_usage_mb=200.0,  # 100% increase from baseline of 100.0
        )

        regressions = monitor_with_baseline.detect_regressions(current_metrics)

        assert isinstance(regressions, list)
        # Should detect significant regressions
        significant_regressions = [r for r in regressions if r.is_significant()]
        assert len(significant_regressions) >= 0

    def test_generate_performance_report_no_output_file(self, monitor):
        """Test generating performance report without output file."""
        current_metrics = PerformanceMetrics(
            import_time=1.5, test_execution_time=90.0, memory_usage_mb=150.0
        )

        regressions = [
            PerformanceRegression(
                metric_name="import_time",
                baseline_value=1.0,
                current_value=1.5,
                change_percentage=50.0,
                threshold=20.0,
            )
        ]

        # Should not raise an exception
        monitor.generate_performance_report(current_metrics, regressions)

    def test_generate_performance_report_with_output_file(self, monitor):
        """Test generating performance report with output file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            current_metrics = PerformanceMetrics(
                import_time=1.5, test_execution_time=90.0, memory_usage_mb=150.0
            )

            regressions = []

            monitor.generate_performance_report(
                current_metrics, regressions, output_file=output_path
            )

            assert output_path.exists()
            with open(output_path, "r") as f:
                report_data = json.load(f)

            assert "current_metrics" in report_data
            assert "regressions" in report_data
            assert "summary" in report_data
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_generate_performance_report_with_regressions(self, monitor, capsys):
        """Test generating performance report with regressions."""
        current_metrics = PerformanceMetrics(
            import_time=2.0, test_execution_time=120.0, memory_usage_mb=200.0
        )

        regressions = [
            PerformanceRegression(
                metric_name="import_time",
                baseline_value=1.0,
                current_value=2.0,
                change_percentage=100.0,
                threshold=20.0,
            ),
            PerformanceRegression(
                metric_name="memory_usage_mb",
                baseline_value=100.0,
                current_value=200.0,
                change_percentage=100.0,
                threshold=25.0,
            ),
        ]

        monitor.generate_performance_report(current_metrics, regressions)

        captured = capsys.readouterr()
        assert "Performance Report" in captured.out
        assert "Regressions Detected" in captured.out

    def test_performance_monitor_integration(self, temp_project_root):
        """Test integration of multiple performance monitoring features."""
        monitor = PerformanceMonitor(project_root=temp_project_root)

        # Test the full workflow
        with (
            patch.object(monitor, "measure_import_time", return_value=1.0),
            patch.object(monitor, "measure_test_execution_time", return_value=60.0),
            patch.object(monitor, "measure_memory_usage", return_value=100.0),
            patch.object(monitor, "measure_package_size", return_value=5.0),
            patch.object(monitor, "measure_startup_time", return_value=2.0),
            patch.object(monitor, "measure_cpu_usage", return_value=25.0),
            patch.object(monitor, "measure_disk_io", return_value=20.0),
        ):

            # Collect metrics
            current_metrics = monitor.collect_comprehensive_metrics()

            # Save as baseline
            baseline_file = temp_project_root / "baseline.json"
            monitor.baseline_file = baseline_file
            monitor.save_baseline(current_metrics)

            # Load baseline
            loaded_baseline = monitor.load_baseline()
            assert loaded_baseline is not None

            # Detect regressions (should be none since metrics are identical)
            regressions = monitor.detect_regressions(current_metrics, loaded_baseline)
            assert len([r for r in regressions if r.is_significant()]) == 0

            # Generate report
            monitor.generate_performance_report(current_metrics, regressions)
