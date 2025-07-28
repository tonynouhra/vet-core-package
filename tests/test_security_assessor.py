"""
Tests for the enhanced security risk assessor module.

This module tests the comprehensive risk assessment and vulnerability
prioritization functionality implemented in the assessor module.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from vet_core.security.assessor import PackageProfile, RiskAssessment, RiskAssessor
from vet_core.security.models import (
    SecurityReport,
    Vulnerability,
    VulnerabilitySeverity,
)


class TestPackageProfile:
    """Test PackageProfile data model."""

    def test_package_profile_creation(self):
        """Test basic package profile creation."""
        profile = PackageProfile(
            name="test-package",
            criticality_score=0.8,
            exposure_level=0.7,
            usage_frequency=0.9,
            has_network_access=True,
            handles_sensitive_data=True,
        )

        assert profile.name == "test-package"
        assert profile.criticality_score == 0.8
        assert profile.exposure_level == 0.7
        assert profile.usage_frequency == 0.9
        assert profile.has_network_access is True
        assert profile.handles_sensitive_data is True

    def test_calculate_exposure_score(self):
        """Test exposure score calculation."""
        profile = PackageProfile(
            name="test-package",
            criticality_score=0.8,
            exposure_level=0.6,
            usage_frequency=0.8,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
            dependency_depth=1,
        )

        exposure_score = profile.calculate_exposure_score()

        # Should be higher than base exposure due to network access and sensitive data
        assert exposure_score > 0.6
        assert 0.0 <= exposure_score <= 1.0

    def test_calculate_exposure_score_dev_only(self):
        """Test exposure score calculation for development-only packages."""
        profile = PackageProfile(
            name="dev-package",
            criticality_score=0.5,
            exposure_level=0.6,
            usage_frequency=0.8,
            has_network_access=False,
            handles_sensitive_data=False,
            is_development_only=True,
            dependency_depth=1,
        )

        exposure_score = profile.calculate_exposure_score()

        # Should be lower due to development-only penalty
        assert exposure_score < 0.6
        assert 0.0 <= exposure_score <= 1.0

    def test_to_dict(self):
        """Test package profile serialization."""
        now = datetime.now()
        profile = PackageProfile(
            name="test-package",
            criticality_score=0.8,
            exposure_level=0.7,
            last_updated=now,
        )

        result = profile.to_dict()

        assert result["name"] == "test-package"
        assert result["criticality_score"] == 0.8
        assert result["exposure_level"] == 0.7
        assert result["last_updated"] == now.isoformat()
        assert "calculated_exposure_score" in result


class TestRiskAssessment:
    """Test RiskAssessment data model."""

    def test_risk_assessment_creation(self):
        """Test basic risk assessment creation."""
        assessment = RiskAssessment(
            vulnerability_id="TEST-001",
            risk_score=7.5,
            priority_level="urgent",
            recommended_timeline=timedelta(hours=72),
            impact_factors={"severity": 0.8, "criticality": 0.7},
            assessment_date=datetime.now(),
            confidence_score=0.85,
            remediation_complexity="medium",
            business_impact="high",
        )

        assert assessment.vulnerability_id == "TEST-001"
        assert assessment.risk_score == 7.5
        assert assessment.priority_level == "urgent"
        assert assessment.confidence_score == 0.85
        assert assessment.remediation_complexity == "medium"
        assert assessment.business_impact == "high"

    def test_is_high_confidence(self):
        """Test high confidence property."""
        high_confidence = RiskAssessment(
            vulnerability_id="TEST-001",
            risk_score=7.0,
            priority_level="urgent",
            recommended_timeline=timedelta(hours=72),
            impact_factors={},
            assessment_date=datetime.now(),
            confidence_score=0.8,
        )

        low_confidence = RiskAssessment(
            vulnerability_id="TEST-002",
            risk_score=7.0,
            priority_level="urgent",
            recommended_timeline=timedelta(hours=72),
            impact_factors={},
            assessment_date=datetime.now(),
            confidence_score=0.6,
        )

        assert high_confidence.is_high_confidence is True
        assert low_confidence.is_high_confidence is False

    def test_requires_immediate_action(self):
        """Test immediate action requirement property."""
        immediate = RiskAssessment(
            vulnerability_id="TEST-001",
            risk_score=9.0,
            priority_level="immediate",
            recommended_timeline=timedelta(hours=24),
            impact_factors={},
            assessment_date=datetime.now(),
        )

        urgent = RiskAssessment(
            vulnerability_id="TEST-002",
            risk_score=7.0,
            priority_level="urgent",
            recommended_timeline=timedelta(hours=72),
            impact_factors={},
            assessment_date=datetime.now(),
        )

        assert immediate.requires_immediate_action is True
        assert urgent.requires_immediate_action is False


class TestRiskAssessor:
    """Test RiskAssessor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.assessor = RiskAssessor()

        # Create test vulnerabilities
        self.critical_vuln = Vulnerability(
            id="CRIT-001",
            package_name="setuptools",
            installed_version="65.5.0",
            fix_versions=["78.1.1"],
            severity=VulnerabilitySeverity.CRITICAL,
            cvss_score=9.5,
            description="Critical vulnerability in setuptools",
            published_date=datetime.now() - timedelta(days=1),
        )

        self.high_vuln = Vulnerability(
            id="HIGH-001",
            package_name="requests",
            installed_version="2.25.0",
            fix_versions=["2.31.0"],
            severity=VulnerabilitySeverity.HIGH,
            cvss_score=7.8,
            description="High severity vulnerability in requests",
            published_date=datetime.now() - timedelta(days=7),
        )

        self.medium_vuln = Vulnerability(
            id="MED-001",
            package_name="black",
            installed_version="23.12.1",
            fix_versions=["24.3.0"],
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=5.5,
            description="Medium severity vulnerability in black",
            published_date=datetime.now() - timedelta(days=14),
        )

        self.low_vuln = Vulnerability(
            id="LOW-001",
            package_name="pytest",
            installed_version="7.0.0",
            fix_versions=["7.4.0"],
            severity=VulnerabilitySeverity.LOW,
            cvss_score=2.1,
            description="Low severity vulnerability in pytest",
            published_date=datetime.now() - timedelta(days=30),
        )

    def test_assessor_initialization(self):
        """Test risk assessor initialization."""
        assessor = RiskAssessor()

        assert len(assessor.package_profiles) > 0
        assert "setuptools" in assessor.package_profiles
        assert "black" in assessor.package_profiles
        assert len(assessor.priority_timelines) == 4
        assert "immediate" in assessor.priority_timelines

    def test_custom_initialization(self):
        """Test risk assessor with custom parameters."""
        custom_profiles = {
            "custom-package": PackageProfile(
                name="custom-package", criticality_score=0.9, exposure_level=0.8
            )
        }

        custom_timelines = {"immediate": timedelta(hours=12)}

        custom_thresholds = {"immediate": 7.5}

        assessor = RiskAssessor(
            custom_package_profiles=custom_profiles,
            custom_timelines=custom_timelines,
            custom_risk_thresholds=custom_thresholds,
        )

        assert "custom-package" in assessor.package_profiles
        assert assessor.priority_timelines["immediate"] == timedelta(hours=12)
        assert assessor.risk_thresholds["immediate"] == 7.5

    def test_assess_critical_vulnerability(self):
        """Test assessment of critical vulnerability."""
        assessment = self.assessor.assess_vulnerability(self.critical_vuln)

        assert assessment.vulnerability_id == "CRIT-001"
        assert assessment.priority_level == "immediate"
        assert assessment.risk_score >= 8.0  # Should be high risk score
        assert assessment.business_impact in ["high", "critical"]
        assert assessment.is_high_confidence

    def test_assess_high_vulnerability(self):
        """Test assessment of high severity vulnerability."""
        assessment = self.assessor.assess_vulnerability(self.high_vuln)

        assert assessment.vulnerability_id == "HIGH-001"
        assert assessment.risk_score >= 6.0  # Should be significant risk
        assert assessment.priority_level in ["immediate", "urgent"]
        assert assessment.business_impact in ["medium", "high"]

    def test_assess_medium_vulnerability(self):
        """Test assessment of medium severity vulnerability."""
        assessment = self.assessor.assess_vulnerability(self.medium_vuln)

        assert assessment.vulnerability_id == "MED-001"
        assert 4.0 <= assessment.risk_score < 8.0  # Should be moderate risk
        assert assessment.priority_level in ["scheduled", "urgent"]
        assert assessment.remediation_complexity == "low"  # Black is dev tool

    def test_assess_low_vulnerability(self):
        """Test assessment of low severity vulnerability."""
        assessment = self.assessor.assess_vulnerability(self.low_vuln)

        assert assessment.vulnerability_id == "LOW-001"
        assert assessment.risk_score < 6.0  # Should be lower risk
        assert assessment.priority_level in ["planned", "scheduled"]
        assert assessment.business_impact in ["low", "medium"]

    def test_assess_report(self):
        """Test assessment of complete security report."""
        vulnerabilities = [
            self.critical_vuln,
            self.high_vuln,
            self.medium_vuln,
            self.low_vuln,
        ]

        report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=vulnerabilities,
            total_packages_scanned=10,
            scan_duration=30.0,
            scanner_version="test",
        )

        assessments = self.assessor.assess_report(report)

        assert len(assessments) == 4
        # Should be sorted by risk score (highest first)
        assert assessments[0].risk_score >= assessments[1].risk_score
        assert assessments[1].risk_score >= assessments[2].risk_score
        assert assessments[2].risk_score >= assessments[3].risk_score

    def test_get_prioritized_vulnerabilities(self):
        """Test vulnerability prioritization."""
        vulnerabilities = [
            self.critical_vuln,
            self.high_vuln,
            self.medium_vuln,
            self.low_vuln,
        ]

        report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=vulnerabilities,
            total_packages_scanned=10,
            scan_duration=30.0,
            scanner_version="test",
        )

        prioritized = self.assessor.get_prioritized_vulnerabilities(report)

        assert "immediate" in prioritized
        assert "urgent" in prioritized
        assert "scheduled" in prioritized
        assert "planned" in prioritized

        # Critical vulnerability should be in immediate category
        immediate_ids = [vuln.id for vuln, _ in prioritized["immediate"]]
        assert "CRIT-001" in immediate_ids

    def test_generate_priority_summary(self):
        """Test priority summary generation."""
        vulnerabilities = [self.critical_vuln, self.high_vuln, self.medium_vuln]

        report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=vulnerabilities,
            total_packages_scanned=10,
            scan_duration=30.0,
            scanner_version="test",
        )

        prioritized = self.assessor.get_prioritized_vulnerabilities(report)
        summary = self.assessor.generate_priority_summary(prioritized)

        assert summary["total_vulnerabilities"] == 3
        assert "priority_counts" in summary
        assert "recommendations" in summary
        assert "risk_metrics" in summary
        assert "timeline_analysis" in summary
        assert "confidence_analysis" in summary

        # Should have risk metrics
        assert "average_risk_score" in summary["risk_metrics"]
        assert "max_risk_score" in summary["risk_metrics"]

    def test_get_package_risk_profile(self):
        """Test package risk profile generation."""
        profile = self.assessor.get_package_risk_profile("setuptools")

        assert profile["package_name"] == "setuptools"
        assert "profile" in profile
        assert "risk_factors" in profile
        assert "recommendations" in profile

        # Setuptools should be high criticality
        assert profile["risk_factors"]["criticality_level"] == "high"
        assert len(profile["recommendations"]) > 0

    def test_get_package_risk_profile_unknown(self):
        """Test package risk profile for unknown package."""
        profile = self.assessor.get_package_risk_profile("unknown-package")

        assert profile["package_name"] == "unknown-package"
        assert "profile" in profile
        # Should create default profile
        assert profile["profile"]["criticality_score"] == 0.5

    def test_analyze_vulnerability_trends(self):
        """Test vulnerability trend analysis."""
        # Create multiple reports with different dates
        reports = []
        for i in range(3):
            vulnerabilities = (
                [self.high_vuln, self.medium_vuln] if i < 2 else [self.critical_vuln]
            )
            report = SecurityReport(
                scan_date=datetime.now() - timedelta(days=i),
                vulnerabilities=vulnerabilities,
                total_packages_scanned=10,
                scan_duration=30.0,
                scanner_version="test",
            )
            reports.append(report)

        trends = self.assessor.analyze_vulnerability_trends(reports)

        assert trends["report_count"] == 3
        assert "date_range" in trends
        assert "vulnerability_trends" in trends
        assert "severity_trends" in trends

        # Should have calculated trends
        assert "total_vulnerabilities" in trends["vulnerability_trends"]
        assert "average_per_scan" in trends["vulnerability_trends"]

    def test_analyze_vulnerability_trends_empty(self):
        """Test vulnerability trend analysis with empty reports."""
        trends = self.assessor.analyze_vulnerability_trends([])

        assert "error" in trends

    def test_get_package_profile_caching(self):
        """Test that package profiles are cached for unknown packages."""
        # First call should create and cache the profile
        profile1 = self.assessor._get_package_profile("new-package")

        # Second call should return the cached profile
        profile2 = self.assessor._get_package_profile("new-package")

        assert profile1 is profile2  # Should be the same object
        assert "new-package" in self.assessor.package_profiles

    def test_calculate_dynamic_timeline(self):
        """Test dynamic timeline calculation."""
        impact_factors = {
            "exposure_level": 0.9,
            "age_urgency": 0.8,
        }

        # Test with critical vulnerability
        timeline = self.assessor._calculate_dynamic_timeline(
            "immediate", self.critical_vuln, impact_factors
        )

        # Should be shorter than base timeline due to critical severity
        base_timeline = self.assessor.priority_timelines["immediate"]
        assert timeline < base_timeline

    def test_assess_remediation_complexity(self):
        """Test remediation complexity assessment."""
        # Development tool should be low complexity
        dev_complexity = self.assessor._assess_remediation_complexity(
            self.medium_vuln
        )  # black
        assert dev_complexity == "low"

        # Core package should be medium complexity
        core_complexity = self.assessor._assess_remediation_complexity(
            self.critical_vuln
        )  # setuptools
        assert core_complexity == "medium"

        # Create vulnerability with no fix
        no_fix_vuln = Vulnerability(
            id="NO-FIX-001",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=[],
            severity=VulnerabilitySeverity.HIGH,
        )

        no_fix_complexity = self.assessor._assess_remediation_complexity(no_fix_vuln)
        assert no_fix_complexity == "high"

    def test_assess_business_impact(self):
        """Test business impact assessment."""
        impact_factors = {
            "package_criticality": 0.9,
            "data_sensitivity": 0.8,
        }

        # Critical vulnerability should have critical business impact
        impact = self.assessor._assess_business_impact(
            self.critical_vuln, impact_factors
        )
        assert impact == "critical"

        # Low vulnerability should have lower impact
        low_impact_factors = {
            "package_criticality": 0.3,
            "data_sensitivity": 0.2,
        }
        impact = self.assessor._assess_business_impact(
            self.low_vuln, low_impact_factors
        )
        assert impact in ["low", "medium"]

    def test_calculate_confidence_score(self):
        """Test confidence score calculation."""
        impact_factors = {f"factor_{i}": 0.5 for i in range(10)}  # All expected factors

        # Vulnerability with complete information should have high confidence
        confidence = self.assessor._calculate_confidence_score(
            self.critical_vuln, impact_factors
        )
        assert confidence > 0.7

        # Vulnerability with minimal information should have lower confidence
        minimal_vuln = Vulnerability(
            id="MIN-001",
            package_name="unknown-package",
            installed_version="1.0.0",
            fix_versions=[],
            severity=VulnerabilitySeverity.UNKNOWN,
        )

        minimal_confidence = self.assessor._calculate_confidence_score(minimal_vuln, {})
        assert minimal_confidence < 0.7


class TestRiskAssessorIntegration:
    """Integration tests for the risk assessor."""

    def test_end_to_end_assessment(self):
        """Test complete end-to-end vulnerability assessment workflow."""
        assessor = RiskAssessor()

        # Create a realistic vulnerability scenario
        vulnerabilities = [
            Vulnerability(
                id="PYSEC-2024-48",
                package_name="black",
                installed_version="23.12.1",
                fix_versions=["24.3.0"],
                severity=VulnerabilitySeverity.MEDIUM,
                cvss_score=5.5,
                description="Code injection vulnerability in black",
                published_date=datetime.now() - timedelta(days=5),
            ),
            Vulnerability(
                id="PYSEC-2025-49",
                package_name="setuptools",
                installed_version="65.5.0",
                fix_versions=["78.1.1"],
                severity=VulnerabilitySeverity.HIGH,
                cvss_score=8.1,
                description="Remote code execution in setuptools",
                published_date=datetime.now() - timedelta(days=2),
            ),
        ]

        report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=vulnerabilities,
            total_packages_scanned=50,
            scan_duration=45.2,
            scanner_version="pip-audit 2.6.0",
        )

        # Perform complete assessment
        prioritized = assessor.get_prioritized_vulnerabilities(report)
        summary = assessor.generate_priority_summary(prioritized)

        # Verify results
        assert summary["total_vulnerabilities"] == 2
        assert len(summary["recommendations"]) > 0
        assert summary["risk_metrics"]["max_risk_score"] > 0

        # Setuptools vulnerability should be higher priority than black
        setuptools_found = False
        black_found = False
        setuptools_priority = None
        black_priority = None

        for priority_level in ["immediate", "urgent", "scheduled", "planned"]:
            for vuln, assessment in prioritized[priority_level]:
                if vuln.package_name == "setuptools":
                    setuptools_found = True
                    setuptools_priority = priority_level
                elif vuln.package_name == "black":
                    black_found = True
                    black_priority = priority_level

        assert setuptools_found and black_found

        # Setuptools should have higher or equal priority
        priority_order = ["immediate", "urgent", "scheduled", "planned"]
        setuptools_index = priority_order.index(setuptools_priority)
        black_index = priority_order.index(black_priority)
        assert setuptools_index <= black_index
