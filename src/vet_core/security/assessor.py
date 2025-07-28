"""
Risk assessment and vulnerability prioritization module.

This module provides functionality to assess the risk and impact of
vulnerabilities and prioritize them for remediation.

The module implements a comprehensive risk assessment algorithm that considers:
- Vulnerability severity (CVSS scores and severity levels)
- Package criticality and importance to the system
- Exposure levels and attack surface
- Fix availability and upgrade complexity
- Age and urgency factors

Requirements addressed:
- 1.2: Risk assessment and impact analysis
- 3.3: Vulnerability prioritization with timeline recommendations
- 4.1: Detailed vulnerability tracking and assessment
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import SecurityReport, Vulnerability, VulnerabilitySeverity

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """
    Represents a comprehensive risk assessment for a vulnerability.

    This class encapsulates all the factors that contribute to the risk
    assessment of a vulnerability, including the calculated risk score,
    priority level, and detailed impact analysis.
    """

    vulnerability_id: str
    risk_score: float  # 0.0 to 10.0
    priority_level: str  # "immediate", "urgent", "scheduled", "planned"
    recommended_timeline: timedelta
    impact_factors: Dict[str, float]
    assessment_date: datetime
    confidence_score: float = 0.8  # Confidence in the assessment (0.0 to 1.0)
    remediation_complexity: str = "medium"  # "low", "medium", "high"
    business_impact: str = "medium"  # "low", "medium", "high", "critical"

    def to_dict(self) -> Dict[str, Any]:
        """Convert risk assessment to dictionary representation."""
        return {
            "vulnerability_id": self.vulnerability_id,
            "risk_score": self.risk_score,
            "priority_level": self.priority_level,
            "recommended_timeline_hours": int(
                self.recommended_timeline.total_seconds() / 3600
            ),
            "recommended_timeline_days": self.recommended_timeline.days,
            "impact_factors": self.impact_factors,
            "assessment_date": self.assessment_date.isoformat(),
            "confidence_score": self.confidence_score,
            "remediation_complexity": self.remediation_complexity,
            "business_impact": self.business_impact,
        }

    @property
    def is_high_confidence(self) -> bool:
        """Check if this assessment has high confidence (>= 0.7)."""
        return self.confidence_score >= 0.7

    @property
    def requires_immediate_action(self) -> bool:
        """Check if this vulnerability requires immediate action."""
        return self.priority_level == "immediate"


@dataclass
class PackageProfile:
    """
    Represents the security profile and criticality of a package.

    This class encapsulates information about how critical a package is
    to the system, its exposure level, and other factors that influence
    vulnerability impact assessment.
    """

    name: str
    criticality_score: float  # 0.0 to 1.0
    exposure_level: float  # 0.0 to 1.0
    usage_frequency: float = 0.5  # How often the package is used
    dependency_depth: int = 1  # How deep in the dependency tree
    has_network_access: bool = False  # Whether package can access network
    handles_sensitive_data: bool = False  # Whether package handles sensitive data
    is_development_only: bool = False  # Whether package is dev-only
    last_updated: Optional[datetime] = None
    maintainer_reputation: float = 0.5  # Reputation of package maintainers

    def calculate_exposure_score(self) -> float:
        """
        Calculate overall exposure score based on various factors.

        Returns:
            Exposure score from 0.0 to 1.0
        """
        base_exposure = self.exposure_level

        # Adjust based on usage patterns
        usage_multiplier = 0.5 + (self.usage_frequency * 0.5)

        # Network access increases exposure
        network_bonus = 0.2 if self.has_network_access else 0.0

        # Sensitive data handling increases exposure
        data_bonus = 0.3 if self.handles_sensitive_data else 0.0

        # Development-only packages have lower exposure in production
        dev_penalty = 0.3 if self.is_development_only else 0.0

        # Dependency depth affects exposure (deeper = less exposed)
        depth_factor = max(0.1, 1.0 - (self.dependency_depth - 1) * 0.1)

        exposure_score = (
            base_exposure * usage_multiplier * depth_factor
            + network_bonus
            + data_bonus
            - dev_penalty
        )

        return min(max(exposure_score, 0.0), 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert package profile to dictionary representation."""
        return {
            "name": self.name,
            "criticality_score": self.criticality_score,
            "exposure_level": self.exposure_level,
            "calculated_exposure_score": self.calculate_exposure_score(),
            "usage_frequency": self.usage_frequency,
            "dependency_depth": self.dependency_depth,
            "has_network_access": self.has_network_access,
            "handles_sensitive_data": self.handles_sensitive_data,
            "is_development_only": self.is_development_only,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "maintainer_reputation": self.maintainer_reputation,
        }


class RiskAssessor:
    """
    Advanced risk assessor for vulnerability prioritization and impact analysis.

    This class implements a comprehensive risk assessment algorithm that evaluates
    vulnerabilities based on multiple factors including severity, package criticality,
    exposure levels, and business impact. It provides automated timeline recommendations
    and detailed impact analysis.

    The assessor uses a weighted scoring system that considers:
    - CVSS scores and severity levels
    - Package criticality and system importance
    - Exposure levels and attack surface
    - Fix availability and remediation complexity
    - Age and urgency factors
    - Business impact and operational risk
    """

    # Enhanced package criticality mapping with detailed profiles
    DEFAULT_PACKAGE_PROFILES = {
        # Core system packages - highest criticality
        "setuptools": PackageProfile(
            name="setuptools",
            criticality_score=0.95,
            exposure_level=0.8,
            usage_frequency=0.9,
            dependency_depth=1,
            has_network_access=True,
            handles_sensitive_data=False,
            is_development_only=False,
        ),
        "pip": PackageProfile(
            name="pip",
            criticality_score=0.95,
            exposure_level=0.7,
            usage_frequency=0.8,
            dependency_depth=1,
            has_network_access=True,
            handles_sensitive_data=False,
            is_development_only=False,
        ),
        "wheel": PackageProfile(
            name="wheel",
            criticality_score=0.8,
            exposure_level=0.6,
            usage_frequency=0.7,
            dependency_depth=1,
            has_network_access=False,
            handles_sensitive_data=False,
            is_development_only=False,
        ),
        # Security-related packages - critical for security
        "cryptography": PackageProfile(
            name="cryptography",
            criticality_score=0.95,
            exposure_level=0.9,
            usage_frequency=0.8,
            dependency_depth=2,
            has_network_access=False,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        "pycryptodome": PackageProfile(
            name="pycryptodome",
            criticality_score=0.9,
            exposure_level=0.9,
            usage_frequency=0.6,
            dependency_depth=2,
            has_network_access=False,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        "requests": PackageProfile(
            name="requests",
            criticality_score=0.85,
            exposure_level=0.95,
            usage_frequency=0.9,
            dependency_depth=1,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        "urllib3": PackageProfile(
            name="urllib3",
            criticality_score=0.8,
            exposure_level=0.9,
            usage_frequency=0.8,
            dependency_depth=2,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        # Database and ORM packages
        "sqlalchemy": PackageProfile(
            name="sqlalchemy",
            criticality_score=0.85,
            exposure_level=0.8,
            usage_frequency=0.8,
            dependency_depth=1,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        "psycopg2": PackageProfile(
            name="psycopg2",
            criticality_score=0.75,
            exposure_level=0.7,
            usage_frequency=0.6,
            dependency_depth=2,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        "asyncpg": PackageProfile(
            name="asyncpg",
            criticality_score=0.7,
            exposure_level=0.7,
            usage_frequency=0.5,
            dependency_depth=2,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        # Web frameworks
        "django": PackageProfile(
            name="django",
            criticality_score=0.9,
            exposure_level=0.95,
            usage_frequency=0.9,
            dependency_depth=1,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        "flask": PackageProfile(
            name="flask",
            criticality_score=0.85,
            exposure_level=0.9,
            usage_frequency=0.8,
            dependency_depth=1,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        "fastapi": PackageProfile(
            name="fastapi",
            criticality_score=0.8,
            exposure_level=0.85,
            usage_frequency=0.7,
            dependency_depth=1,
            has_network_access=True,
            handles_sensitive_data=True,
            is_development_only=False,
        ),
        # Development tools - lower criticality for production
        "black": PackageProfile(
            name="black",
            criticality_score=0.3,
            exposure_level=0.2,
            usage_frequency=0.8,
            dependency_depth=1,
            has_network_access=False,
            handles_sensitive_data=False,
            is_development_only=True,
        ),
        "isort": PackageProfile(
            name="isort",
            criticality_score=0.2,
            exposure_level=0.1,
            usage_frequency=0.6,
            dependency_depth=1,
            has_network_access=False,
            handles_sensitive_data=False,
            is_development_only=True,
        ),
        "mypy": PackageProfile(
            name="mypy",
            criticality_score=0.25,
            exposure_level=0.1,
            usage_frequency=0.7,
            dependency_depth=1,
            has_network_access=False,
            handles_sensitive_data=False,
            is_development_only=True,
        ),
        "pytest": PackageProfile(
            name="pytest",
            criticality_score=0.3,
            exposure_level=0.2,
            usage_frequency=0.9,
            dependency_depth=1,
            has_network_access=False,
            handles_sensitive_data=False,
            is_development_only=True,
        ),
    }

    # Timeline recommendations based on priority level and severity
    PRIORITY_TIMELINES = {
        "immediate": timedelta(hours=24),
        "urgent": timedelta(hours=72),
        "scheduled": timedelta(days=7),
        "planned": timedelta(days=30),
    }

    # Risk score thresholds for priority determination
    RISK_THRESHOLDS = {
        "immediate": 8.0,
        "urgent": 6.0,
        "scheduled": 4.0,
        "planned": 0.0,
    }

    def __init__(
        self,
        custom_package_profiles: Optional[Dict[str, PackageProfile]] = None,
        custom_timelines: Optional[Dict[str, timedelta]] = None,
        custom_risk_thresholds: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Initialize the enhanced risk assessor.

        Args:
            custom_package_profiles: Custom package profile mappings
            custom_timelines: Custom timeline recommendations
            custom_risk_thresholds: Custom risk score thresholds
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize package profiles
        self.package_profiles = self.DEFAULT_PACKAGE_PROFILES.copy()
        if custom_package_profiles:
            self.package_profiles.update(custom_package_profiles)

        # Initialize timeline recommendations
        self.priority_timelines = self.PRIORITY_TIMELINES.copy()
        if custom_timelines:
            self.priority_timelines.update(custom_timelines)

        # Initialize risk thresholds
        self.risk_thresholds = self.RISK_THRESHOLDS.copy()
        if custom_risk_thresholds:
            self.risk_thresholds.update(custom_risk_thresholds)

        # Cache for package analysis
        self._package_analysis_cache: Dict[str, Dict[str, float]] = {}

        self.logger.info(
            f"Initialized RiskAssessor with {len(self.package_profiles)} package profiles"
        )

    def assess_vulnerability(self, vulnerability: Vulnerability) -> RiskAssessment:
        """
        Perform comprehensive risk assessment of a single vulnerability.

        This method implements the core risk assessment algorithm that evaluates
        vulnerabilities based on multiple factors and provides detailed analysis.

        Args:
            vulnerability: The vulnerability to assess

        Returns:
            RiskAssessment with calculated risk score, priority, and detailed analysis
        """
        # Calculate detailed impact factors
        impact_factors = self._calculate_enhanced_impact_factors(vulnerability)

        # Calculate overall risk score using weighted algorithm
        risk_score = self._calculate_weighted_risk_score(impact_factors, vulnerability)

        # Determine priority level based on risk score and severity
        priority_level = self._determine_priority_level(
            risk_score, vulnerability.severity
        )

        # Get recommended timeline
        recommended_timeline = self._calculate_dynamic_timeline(
            priority_level, vulnerability, impact_factors
        )

        # Assess remediation complexity
        remediation_complexity = self._assess_remediation_complexity(vulnerability)

        # Determine business impact
        business_impact = self._assess_business_impact(vulnerability, impact_factors)

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            vulnerability, impact_factors
        )

        assessment = RiskAssessment(
            vulnerability_id=vulnerability.id,
            risk_score=risk_score,
            priority_level=priority_level,
            recommended_timeline=recommended_timeline,
            impact_factors=impact_factors,
            assessment_date=datetime.now(),
            confidence_score=confidence_score,
            remediation_complexity=remediation_complexity,
            business_impact=business_impact,
        )

        self.logger.debug(
            f"Assessed {vulnerability.id}: risk_score={risk_score:.2f}, "
            f"priority={priority_level}, confidence={confidence_score:.2f}"
        )

        return assessment

    def assess_report(self, report: SecurityReport) -> List[RiskAssessment]:
        """
        Assess all vulnerabilities in a security report.

        Args:
            report: The security report to assess

        Returns:
            List of risk assessments sorted by risk score (highest first)
        """
        assessments = []

        for vulnerability in report.vulnerabilities:
            assessment = self.assess_vulnerability(vulnerability)
            assessments.append(assessment)

        # Sort by risk score (highest first)
        assessments.sort(key=lambda a: a.risk_score, reverse=True)

        self.logger.info(f"Assessed {len(assessments)} vulnerabilities")

        return assessments

    def get_prioritized_vulnerabilities(
        self, report: SecurityReport
    ) -> Dict[str, List[Tuple[Vulnerability, RiskAssessment]]]:
        """
        Get vulnerabilities grouped by priority level.

        Args:
            report: The security report to prioritize

        Returns:
            Dictionary mapping priority levels to lists of (vulnerability, assessment) tuples
        """
        assessments = self.assess_report(report)
        vulnerability_map = {v.id: v for v in report.vulnerabilities}

        prioritized: Dict[str, List[Tuple[Vulnerability, RiskAssessment]]] = {
            "immediate": [],
            "urgent": [],
            "scheduled": [],
            "planned": [],
        }

        for assessment in assessments:
            vulnerability = vulnerability_map[assessment.vulnerability_id]
            priority = assessment.priority_level
            prioritized[priority].append((vulnerability, assessment))

        return prioritized

    def _calculate_enhanced_impact_factors(
        self, vulnerability: Vulnerability
    ) -> Dict[str, float]:
        """
        Calculate comprehensive impact factors for a vulnerability.

        This method performs detailed analysis of various factors that contribute
        to the overall impact and risk of a vulnerability.

        Args:
            vulnerability: The vulnerability to analyze

        Returns:
            Dictionary of impact factor names to scores (0.0 to 1.0)
        """
        factors = {}
        package_name = vulnerability.package_name.lower()

        # Get package profile (or create default)
        package_profile = self._get_package_profile(package_name)

        # 1. Package criticality factor
        factors["package_criticality"] = package_profile.criticality_score

        # 2. Severity factor (enhanced with CVSS analysis)
        factors["severity"] = self._calculate_severity_factor(vulnerability)

        # 3. Exposure level factor (comprehensive analysis)
        factors["exposure_level"] = package_profile.calculate_exposure_score()

        # 4. Fix availability and complexity factor
        factors["fix_availability"] = self._calculate_fix_availability_factor(
            vulnerability
        )

        # 5. Age and urgency factor
        factors["age_urgency"] = self._calculate_age_urgency_factor(vulnerability)

        # 6. Attack vector and exploitability factor
        factors["exploitability"] = self._calculate_exploitability_factor(
            vulnerability, package_profile
        )

        # 7. Data sensitivity factor
        factors["data_sensitivity"] = self._calculate_data_sensitivity_factor(
            package_profile
        )

        # 8. Network exposure factor
        factors["network_exposure"] = self._calculate_network_exposure_factor(
            package_profile
        )

        # 9. Dependency impact factor
        factors["dependency_impact"] = self._calculate_dependency_impact_factor(
            package_profile
        )

        # 10. Maintainer and ecosystem factor
        factors["ecosystem_health"] = self._calculate_ecosystem_health_factor(
            package_profile
        )

        self.logger.debug(
            f"Calculated {len(factors)} impact factors for {vulnerability.id}"
        )

        return factors

    def _get_package_profile(self, package_name: str) -> PackageProfile:
        """
        Get or create a package profile for the given package.

        Args:
            package_name: Name of the package

        Returns:
            PackageProfile for the package
        """
        if package_name in self.package_profiles:
            return self.package_profiles[package_name]

        # Create default profile for unknown packages
        default_profile = PackageProfile(
            name=package_name,
            criticality_score=0.5,  # Medium criticality by default
            exposure_level=0.6,  # Moderate exposure by default
            usage_frequency=0.5,
            dependency_depth=2,  # Assume it's a dependency
            has_network_access=False,  # Conservative assumption
            handles_sensitive_data=False,  # Conservative assumption
            is_development_only=False,
            maintainer_reputation=0.5,
        )

        # Cache the profile for future use
        self.package_profiles[package_name] = default_profile

        self.logger.debug(
            f"Created default profile for unknown package: {package_name}"
        )

        return default_profile

    def _calculate_severity_factor(self, vulnerability: Vulnerability) -> float:
        """Calculate severity factor with enhanced CVSS analysis."""
        if vulnerability.cvss_score is not None:
            # Use CVSS score with non-linear scaling for higher sensitivity
            base_score = min(vulnerability.cvss_score / 10.0, 1.0)
            # Apply exponential scaling to emphasize higher scores
            return math.pow(base_score, 0.8)
        else:
            # Fallback to severity level mapping
            severity_scores = {
                VulnerabilitySeverity.CRITICAL: 1.0,
                VulnerabilitySeverity.HIGH: 0.8,
                VulnerabilitySeverity.MEDIUM: 0.6,
                VulnerabilitySeverity.LOW: 0.3,
                VulnerabilitySeverity.UNKNOWN: 0.5,
            }
            return severity_scores[vulnerability.severity]

    def _calculate_fix_availability_factor(self, vulnerability: Vulnerability) -> float:
        """Calculate fix availability factor with complexity analysis."""
        if not vulnerability.is_fixable:
            return 0.2  # Very low score if no fix available

        # Base score for having fixes
        base_score = 0.8

        # Bonus for multiple fix versions (indicates active maintenance)
        if len(vulnerability.fix_versions) > 1:
            base_score += 0.1

        # Consider version jump complexity (simplified analysis)
        if vulnerability.fix_versions:
            # This is a simplified heuristic - in practice, you'd want
            # more sophisticated version comparison
            base_score += 0.1

        return min(base_score, 1.0)

    def _calculate_age_urgency_factor(self, vulnerability: Vulnerability) -> float:
        """Calculate age and urgency factor with time-based analysis."""
        if not vulnerability.published_date:
            return 0.5  # Unknown age gets medium urgency

        days_since_published = (datetime.now() - vulnerability.published_date).days

        # Recent vulnerabilities (0-7 days) get highest urgency
        if days_since_published <= 7:
            return 1.0
        # Vulnerabilities 1-4 weeks old get high urgency
        elif days_since_published <= 28:
            return 0.8 - (days_since_published - 7) * 0.02
        # Older vulnerabilities get decreasing urgency
        else:
            return max(0.2, 0.6 - (days_since_published - 28) * 0.01)

    def _calculate_exploitability_factor(
        self, vulnerability: Vulnerability, package_profile: PackageProfile
    ) -> float:
        """Calculate exploitability factor based on attack vectors."""
        base_exploitability = 0.5

        # Network-accessible packages are more exploitable
        if package_profile.has_network_access:
            base_exploitability += 0.3

        # Packages handling sensitive data are higher targets
        if package_profile.handles_sensitive_data:
            base_exploitability += 0.2

        # High usage frequency increases exploitability
        base_exploitability += package_profile.usage_frequency * 0.2

        # Development-only packages are less exploitable in production
        if package_profile.is_development_only:
            base_exploitability -= 0.3

        return min(max(base_exploitability, 0.0), 1.0)

    def _calculate_data_sensitivity_factor(
        self, package_profile: PackageProfile
    ) -> float:
        """Calculate data sensitivity impact factor."""
        if package_profile.handles_sensitive_data:
            return 0.9
        elif package_profile.has_network_access:
            return 0.6  # Network packages might handle sensitive data
        else:
            return 0.3

    def _calculate_network_exposure_factor(
        self, package_profile: PackageProfile
    ) -> float:
        """Calculate network exposure impact factor."""
        if package_profile.has_network_access:
            # Higher exposure for packages with network access
            return 0.8 + (package_profile.usage_frequency * 0.2)
        else:
            return 0.2

    def _calculate_dependency_impact_factor(
        self, package_profile: PackageProfile
    ) -> float:
        """Calculate dependency impact factor."""
        # Packages higher in the dependency tree have more impact
        depth_factor = max(0.2, 1.0 - (package_profile.dependency_depth - 1) * 0.15)

        # Usage frequency affects impact
        usage_factor = package_profile.usage_frequency

        return (depth_factor + usage_factor) / 2

    def _calculate_ecosystem_health_factor(
        self, package_profile: PackageProfile
    ) -> float:
        """Calculate ecosystem health and maintainer reputation factor."""
        base_health = package_profile.maintainer_reputation

        # Recent updates indicate healthy maintenance
        if package_profile.last_updated:
            days_since_update = (datetime.now() - package_profile.last_updated).days
            if days_since_update <= 90:  # Updated within 3 months
                base_health += 0.2
            elif days_since_update <= 365:  # Updated within 1 year
                base_health += 0.1

        return min(base_health, 1.0)

    def _calculate_weighted_risk_score(
        self, impact_factors: Dict[str, float], vulnerability: Vulnerability
    ) -> float:
        """
        Calculate comprehensive risk score using weighted algorithm.

        This method implements a sophisticated weighted scoring system that
        considers all impact factors with appropriate weights based on their
        importance to overall risk assessment.

        Args:
            impact_factors: Dictionary of calculated impact factors
            vulnerability: The vulnerability being assessed

        Returns:
            Risk score from 0.0 to 10.0
        """
        # Enhanced weighting system with more factors
        weights = {
            # Core risk factors (70% of total weight)
            "severity": 0.25,  # CVSS/severity level
            "package_criticality": 0.20,  # How critical the package is
            "exposure_level": 0.15,  # How exposed the package is
            "exploitability": 0.10,  # How easily exploitable
            # Contextual factors (20% of total weight)
            "fix_availability": 0.08,  # Whether fixes are available
            "age_urgency": 0.07,  # How urgent based on age
            "data_sensitivity": 0.05,  # Sensitive data handling
            # Environmental factors (10% of total weight)
            "network_exposure": 0.04,  # Network accessibility
            "dependency_impact": 0.03,  # Impact on dependencies
            "ecosystem_health": 0.03,  # Maintainer reputation
        }

        weighted_score = 0.0
        total_weight = 0.0
        missing_factors = []

        # Calculate weighted sum
        for factor, weight in weights.items():
            if factor in impact_factors:
                weighted_score += impact_factors[factor] * weight
                total_weight += weight
            else:
                missing_factors.append(factor)

        # Log missing factors for debugging
        if missing_factors:
            self.logger.debug(
                f"Missing impact factors for {vulnerability.id}: {missing_factors}"
            )

        # Normalize to 0-10 scale
        if total_weight > 0:
            base_score = (weighted_score / total_weight) * 10.0
        else:
            base_score = 5.0  # Default middle score

        # Apply non-linear scaling for critical vulnerabilities
        if vulnerability.severity == VulnerabilitySeverity.CRITICAL:
            base_score = min(base_score * 1.2, 10.0)  # Boost critical vulnerabilities

        # Apply boost for high CVSS scores
        if vulnerability.cvss_score and vulnerability.cvss_score >= 9.0:
            base_score = min(base_score * 1.1, 10.0)

        return min(max(base_score, 0.0), 10.0)  # Clamp to 0-10 range

    def _determine_priority_level(
        self, risk_score: float, severity: VulnerabilitySeverity
    ) -> str:
        """
        Determine priority level based on risk score and severity.

        Args:
            risk_score: Calculated risk score (0.0 to 10.0)
            severity: Vulnerability severity level

        Returns:
            Priority level string
        """
        # Critical vulnerabilities are always immediate priority
        if severity == VulnerabilitySeverity.CRITICAL:
            return "immediate"

        # High severity vulnerabilities with high risk scores should be immediate
        if severity == VulnerabilitySeverity.HIGH and risk_score >= 8.5:
            return "immediate"

        # Use configurable risk score thresholds
        for priority in ["immediate", "urgent", "scheduled", "planned"]:
            if risk_score >= self.risk_thresholds[priority]:
                return priority

        return "planned"  # Fallback

    def _calculate_dynamic_timeline(
        self,
        priority_level: str,
        vulnerability: Vulnerability,
        impact_factors: Dict[str, float],
    ) -> timedelta:
        """
        Calculate dynamic timeline based on priority and specific factors.

        Args:
            priority_level: Determined priority level
            vulnerability: The vulnerability being assessed
            impact_factors: Calculated impact factors

        Returns:
            Recommended timeline as timedelta
        """
        base_timeline = self.priority_timelines[priority_level]

        # Adjust timeline based on specific factors
        adjustment_factor = 1.0

        # Urgent adjustments for high-risk scenarios
        if vulnerability.severity == VulnerabilitySeverity.CRITICAL:
            adjustment_factor *= 0.5  # Halve the timeline

        # Adjust based on fix availability
        if not vulnerability.is_fixable:
            adjustment_factor *= 2.0  # Double timeline if no fix available

        # Adjust based on exposure level
        exposure = impact_factors.get("exposure_level", 0.5)
        if exposure > 0.8:
            adjustment_factor *= 0.8  # Reduce timeline for high exposure

        # Adjust based on age urgency
        age_urgency = impact_factors.get("age_urgency", 0.5)
        if age_urgency > 0.8:
            adjustment_factor *= 0.7  # Reduce timeline for recent vulnerabilities

        # Calculate adjusted timeline
        adjusted_hours = base_timeline.total_seconds() / 3600 * adjustment_factor
        adjusted_timeline = timedelta(hours=max(adjusted_hours, 1))  # Minimum 1 hour

        return adjusted_timeline

    def _assess_remediation_complexity(self, vulnerability: Vulnerability) -> str:
        """
        Assess the complexity of remediating a vulnerability.

        Args:
            vulnerability: The vulnerability to assess

        Returns:
            Complexity level: "low", "medium", or "high"
        """
        if not vulnerability.is_fixable:
            return "high"  # No fix available = high complexity

        # Simple heuristic based on package and fix versions
        package_name = vulnerability.package_name.lower()

        # Development tools are typically easier to upgrade
        dev_tools = {"black", "isort", "mypy", "pytest", "flake8", "bandit"}
        if package_name in dev_tools:
            return "low"

        # Core system packages may be more complex
        core_packages = {"setuptools", "pip", "wheel"}
        if package_name in core_packages:
            return "medium"

        # Security and database packages may require careful testing
        sensitive_packages = {"cryptography", "sqlalchemy", "django", "flask"}
        if package_name in sensitive_packages:
            return "high"

        # Default to medium complexity
        return "medium"

    def _assess_business_impact(
        self, vulnerability: Vulnerability, impact_factors: Dict[str, float]
    ) -> str:
        """
        Assess the business impact of a vulnerability.

        Args:
            vulnerability: The vulnerability to assess
            impact_factors: Calculated impact factors

        Returns:
            Business impact level: "low", "medium", "high", or "critical"
        """
        # Start with severity-based impact
        severity_impact = {
            VulnerabilitySeverity.CRITICAL: "critical",
            VulnerabilitySeverity.HIGH: "high",
            VulnerabilitySeverity.MEDIUM: "medium",
            VulnerabilitySeverity.LOW: "low",
            VulnerabilitySeverity.UNKNOWN: "medium",
        }

        base_impact = severity_impact[vulnerability.severity]

        # Adjust based on package criticality
        package_criticality = impact_factors.get("package_criticality", 0.5)
        if package_criticality > 0.8 and base_impact in ["low", "medium"]:
            # Upgrade impact level for critical packages, but only by one level
            # and never upgrade HIGH severity vulnerabilities to critical
            impact_levels = ["low", "medium", "high", "critical"]
            current_index = impact_levels.index(base_impact)
            if current_index < len(impact_levels) - 1:
                base_impact = impact_levels[current_index + 1]

        # Consider data sensitivity
        data_sensitivity = impact_factors.get("data_sensitivity", 0.3)
        if data_sensitivity > 0.8 and base_impact in ["low", "medium"]:
            base_impact = "high"

        return base_impact

    def _calculate_confidence_score(
        self, vulnerability: Vulnerability, impact_factors: Dict[str, float]
    ) -> float:
        """
        Calculate confidence score for the risk assessment.

        Args:
            vulnerability: The vulnerability being assessed
            impact_factors: Calculated impact factors

        Returns:
            Confidence score from 0.0 to 1.0
        """
        confidence = 0.5  # Base confidence

        # Higher confidence if we have CVSS score
        if vulnerability.cvss_score is not None:
            confidence += 0.2

        # Higher confidence if we have published date
        if vulnerability.published_date is not None:
            confidence += 0.1

        # Higher confidence if we have fix versions
        if vulnerability.is_fixable:
            confidence += 0.1

        # Higher confidence for known packages
        package_name = vulnerability.package_name.lower()
        if package_name in self.package_profiles:
            confidence += 0.1

        # Adjust based on completeness of impact factors
        expected_factors = 10  # Number of factors we calculate
        actual_factors = len(impact_factors)
        completeness_ratio = actual_factors / expected_factors
        confidence *= completeness_ratio

        return min(max(confidence, 0.0), 1.0)

    def generate_priority_summary(
        self, prioritized: Dict[str, List[Tuple[Vulnerability, RiskAssessment]]]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of vulnerability priorities.

        Args:
            prioritized: Dictionary of prioritized vulnerabilities

        Returns:
            Enhanced summary dictionary with counts, recommendations, and analytics
        """
        total_vulns = sum(len(vulns) for vulns in prioritized.values())

        recommendations: List[str] = []
        summary = {
            "total_vulnerabilities": total_vulns,
            "priority_counts": {
                level: len(vulns) for level, vulns in prioritized.items()
            },
            "recommendations": recommendations,
            "risk_metrics": {},
            "timeline_analysis": {},
            "confidence_analysis": {},
        }

        # Generate priority-based recommendations
        if prioritized["immediate"]:
            count = len(prioritized["immediate"])
            recommendations.append(
                f"CRITICAL: {count} vulnerabilities require immediate attention (within 24 hours)"
            )

        if prioritized["urgent"]:
            count = len(prioritized["urgent"])
            recommendations.append(
                f"HIGH: {count} vulnerabilities should be addressed within 72 hours"
            )

        if prioritized["scheduled"]:
            count = len(prioritized["scheduled"])
            recommendations.append(
                f"MEDIUM: {count} vulnerabilities should be scheduled for next week"
            )

        if prioritized["planned"]:
            count = len(prioritized["planned"])
            recommendations.append(
                f"LOW: {count} vulnerabilities can be planned for next month"
            )

        # Calculate risk metrics
        all_assessments = []
        for priority_vulns in prioritized.values():
            all_assessments.extend([assessment for _, assessment in priority_vulns])

        if all_assessments:
            risk_scores = [a.risk_score for a in all_assessments]
            summary["risk_metrics"] = {
                "average_risk_score": sum(risk_scores) / len(risk_scores),
                "max_risk_score": max(risk_scores),
                "min_risk_score": min(risk_scores),
                "high_risk_count": len([s for s in risk_scores if s >= 7.0]),
            }

            # Timeline analysis
            timelines = [
                a.recommended_timeline.total_seconds() / 3600 for a in all_assessments
            ]
            summary["timeline_analysis"] = {
                "average_timeline_hours": sum(timelines) / len(timelines),
                "urgent_timeline_count": len([t for t in timelines if t <= 24]),
            }

            # Confidence analysis
            confidences = [a.confidence_score for a in all_assessments]
            summary["confidence_analysis"] = {
                "average_confidence": sum(confidences) / len(confidences),
                "high_confidence_count": len([c for c in confidences if c >= 0.7]),
                "low_confidence_count": len([c for c in confidences if c < 0.5]),
            }

        return summary

    def get_package_risk_profile(self, package_name: str) -> Dict[str, Any]:
        """
        Get comprehensive risk profile for a specific package.

        Args:
            package_name: Name of the package to analyze

        Returns:
            Dictionary containing package risk profile information
        """
        package_profile = self._get_package_profile(package_name.lower())

        return {
            "package_name": package_name,
            "profile": package_profile.to_dict(),
            "risk_factors": {
                "criticality_level": self._categorize_score(
                    package_profile.criticality_score
                ),
                "exposure_level": self._categorize_score(
                    package_profile.calculate_exposure_score()
                ),
                "security_sensitivity": (
                    "high" if package_profile.handles_sensitive_data else "low"
                ),
                "network_risk": "high" if package_profile.has_network_access else "low",
                "production_impact": (
                    "low" if package_profile.is_development_only else "high"
                ),
            },
            "recommendations": self._generate_package_recommendations(package_profile),
        }

    def analyze_vulnerability_trends(
        self, reports: List[SecurityReport]
    ) -> Dict[str, Any]:
        """
        Analyze trends across multiple security reports.

        Args:
            reports: List of security reports to analyze

        Returns:
            Dictionary containing trend analysis
        """
        if not reports:
            return {"error": "No reports provided for analysis"}

        # Sort reports by date
        sorted_reports = sorted(reports, key=lambda r: r.scan_date)

        trend_data = {
            "report_count": len(reports),
            "date_range": {
                "start": sorted_reports[0].scan_date.isoformat(),
                "end": sorted_reports[-1].scan_date.isoformat(),
            },
            "vulnerability_trends": {},
            "severity_trends": {},
            "package_trends": {},
        }

        # Analyze vulnerability count trends
        vuln_counts = [len(r.vulnerabilities) for r in sorted_reports]
        trend_data["vulnerability_trends"] = {
            "total_vulnerabilities": sum(vuln_counts),
            "average_per_scan": sum(vuln_counts) / len(vuln_counts),
            "trend_direction": self._calculate_trend_direction(
                [float(x) for x in vuln_counts]
            ),
        }

        # Analyze severity trends
        severity_counts: Dict[str, List[int]] = {
            severity.value: [] for severity in VulnerabilitySeverity
        }
        for report in sorted_reports:
            for severity in VulnerabilitySeverity:
                count = len(report.get_vulnerabilities_by_severity(severity))
                severity_counts[severity.value].append(count)

        trend_data["severity_trends"] = {
            severity: {
                "total": sum(counts),
                "average": sum(counts) / len(counts),
                "trend": self._calculate_trend_direction([float(x) for x in counts]),
            }
            for severity, counts in severity_counts.items()
        }

        return trend_data

    def _categorize_score(self, score: float) -> str:
        """Categorize a numeric score into descriptive levels."""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "very_low"

    def _generate_package_recommendations(
        self, package_profile: PackageProfile
    ) -> List[str]:
        """Generate recommendations for a package based on its profile."""
        recommendations = []

        if package_profile.criticality_score > 0.8:
            recommendations.append(
                "High-priority package: Monitor closely for vulnerabilities"
            )

        if package_profile.has_network_access:
            recommendations.append(
                "Network-accessible package: Prioritize security updates"
            )

        if package_profile.handles_sensitive_data:
            recommendations.append(
                "Handles sensitive data: Implement strict update policies"
            )

        if package_profile.is_development_only:
            recommendations.append("Development-only package: Lower production risk")

        if package_profile.calculate_exposure_score() > 0.7:
            recommendations.append(
                "High exposure: Consider additional security measures"
            )

        return recommendations

    def _calculate_trend_direction(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values."""
        if len(values) < 2:
            return "insufficient_data"

        # Simple linear trend calculation
        first_half = values[: len(values) // 2]
        second_half = values[len(values) // 2 :]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if second_avg > first_avg * 1.1:
            return "increasing"
        elif second_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"
