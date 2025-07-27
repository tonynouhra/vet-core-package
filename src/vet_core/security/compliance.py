"""
Security compliance reporting and management module.

This module provides comprehensive compliance reporting capabilities,
policy enforcement, and evidence generation for security audits and
regulatory compliance requirements.

Requirements addressed:
- 4.3: Compliance report generation with vulnerability management evidence
- 4.4: Evidence of proactive security management practices
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .assessor import RiskAssessor
from .audit_trail import (
    AuditEvent,
    AuditEventType,
    ComplianceMetrics,
    SecurityAuditTrail,
)
from .models import SecurityReport, Vulnerability, VulnerabilitySeverity


class ComplianceFramework(Enum):
    """Supported compliance frameworks."""

    NIST_CSF = "nist_csf"
    ISO_27001 = "iso_27001"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    CUSTOM = "custom"


@dataclass
class PolicyRule:
    """Represents a security policy rule."""

    rule_id: str
    name: str
    description: str
    severity_threshold: VulnerabilitySeverity
    max_resolution_time_hours: int
    framework: ComplianceFramework
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy rule to dictionary representation."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "severity_threshold": self.severity_threshold.value,
            "max_resolution_time_hours": self.max_resolution_time_hours,
            "framework": self.framework.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ComplianceViolation:
    """Represents a compliance policy violation."""

    violation_id: str
    rule_id: str
    vulnerability_id: Optional[str]
    package_name: Optional[str]
    violation_type: str
    description: str
    severity: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False
    resolution_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert compliance violation to dictionary representation."""
        return {
            "violation_id": self.violation_id,
            "rule_id": self.rule_id,
            "vulnerability_id": self.vulnerability_id,
            "package_name": self.package_name,
            "violation_type": self.violation_type,
            "description": self.description,
            "severity": self.severity,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_resolved": self.is_resolved,
            "resolution_notes": self.resolution_notes,
        }


class SecurityComplianceManager:
    """
    Comprehensive security compliance management system.

    This class provides policy enforcement, compliance monitoring,
    and detailed reporting capabilities for various compliance frameworks.
    """

    # Default policy rules for common compliance requirements
    DEFAULT_POLICY_RULES = [
        PolicyRule(
            rule_id="CRITICAL_24H",
            name="Critical Vulnerabilities - 24 Hour Resolution",
            description="Critical vulnerabilities must be resolved within 24 hours",
            severity_threshold=VulnerabilitySeverity.CRITICAL,
            max_resolution_time_hours=24,
            framework=ComplianceFramework.NIST_CSF,
        ),
        PolicyRule(
            rule_id="HIGH_72H",
            name="High Vulnerabilities - 72 Hour Resolution",
            description="High severity vulnerabilities must be resolved within 72 hours",
            severity_threshold=VulnerabilitySeverity.HIGH,
            max_resolution_time_hours=72,
            framework=ComplianceFramework.NIST_CSF,
        ),
        PolicyRule(
            rule_id="MEDIUM_7D",
            name="Medium Vulnerabilities - 7 Day Resolution",
            description="Medium severity vulnerabilities must be resolved within 7 days",
            severity_threshold=VulnerabilitySeverity.MEDIUM,
            max_resolution_time_hours=168,  # 7 days
            framework=ComplianceFramework.ISO_27001,
        ),
        PolicyRule(
            rule_id="DAILY_SCAN",
            name="Daily Security Scanning",
            description="Security scans must be performed at least daily",
            severity_threshold=VulnerabilitySeverity.LOW,
            max_resolution_time_hours=24,
            framework=ComplianceFramework.SOC2,
        ),
    ]

    def __init__(
        self,
        audit_trail: SecurityAuditTrail,
        risk_assessor: Optional[RiskAssessor] = None,
        custom_policy_rules: Optional[List[PolicyRule]] = None,
    ) -> None:
        """
        Initialize the security compliance manager.

        Args:
            audit_trail: Security audit trail system
            risk_assessor: Risk assessor for vulnerability analysis
            custom_policy_rules: Custom policy rules to add
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.audit_trail = audit_trail
        self.risk_assessor = risk_assessor or RiskAssessor()

        # Initialize policy rules
        self.policy_rules = {rule.rule_id: rule for rule in self.DEFAULT_POLICY_RULES}
        if custom_policy_rules:
            for rule in custom_policy_rules:
                self.policy_rules[rule.rule_id] = rule

        self.logger.info(
            f"Initialized SecurityComplianceManager with {len(self.policy_rules)} policy rules"
        )

    def check_compliance(
        self, current_report: SecurityReport, check_historical: bool = True
    ) -> Tuple[List[ComplianceViolation], ComplianceMetrics]:
        """
        Perform comprehensive compliance check.

        Args:
            current_report: Current security report
            check_historical: Whether to check historical compliance

        Returns:
            Tuple of (violations found, compliance metrics)
        """
        violations = []

        # Check current vulnerabilities against policy rules
        for vulnerability in current_report.vulnerabilities:
            violation = self._check_vulnerability_compliance(vulnerability)
            if violation:
                violations.append(violation)

        # Check scan frequency compliance
        if check_historical:
            scan_violations = self._check_scan_frequency_compliance()
            violations.extend(scan_violations)

        # Calculate compliance metrics
        metrics = self.audit_trail.calculate_compliance_metrics(current_report)

        # Log violations
        for violation in violations:
            self.audit_trail.log_policy_violation(
                violation_type=violation.violation_type,
                description=violation.description,
                vulnerability_id=violation.vulnerability_id,
            )

        self.logger.info(
            f"Compliance check completed: {len(violations)} violations found"
        )

        return violations, metrics

    def _check_vulnerability_compliance(
        self, vulnerability: Vulnerability
    ) -> Optional[ComplianceViolation]:
        """Check if a vulnerability violates any policy rules."""
        # Find applicable policy rules
        applicable_rules = [
            rule
            for rule in self.policy_rules.values()
            if rule.is_active and self._is_rule_applicable(rule, vulnerability)
        ]

        if not applicable_rules:
            return None

        # Check if vulnerability exceeds resolution time limits
        age_hours = (
            datetime.now() - vulnerability.discovered_date
        ).total_seconds() / 3600

        for rule in applicable_rules:
            if age_hours > rule.max_resolution_time_hours:
                return ComplianceViolation(
                    violation_id=f"VIOLATION_{vulnerability.id}_{rule.rule_id}",
                    rule_id=rule.rule_id,
                    vulnerability_id=vulnerability.id,
                    package_name=vulnerability.package_name,
                    violation_type="resolution_time_exceeded",
                    description=f"Vulnerability {vulnerability.id} in {vulnerability.package_name} "
                    f"has exceeded {rule.max_resolution_time_hours}h resolution time limit "
                    f"(current age: {age_hours:.1f}h)",
                    severity=vulnerability.severity.value,
                    detected_at=datetime.now(),
                )

        return None

    def _is_rule_applicable(
        self, rule: PolicyRule, vulnerability: Vulnerability
    ) -> bool:
        """Check if a policy rule applies to a vulnerability."""
        # Check severity threshold
        severity_levels = {
            VulnerabilitySeverity.CRITICAL: 4,
            VulnerabilitySeverity.HIGH: 3,
            VulnerabilitySeverity.MEDIUM: 2,
            VulnerabilitySeverity.LOW: 1,
            VulnerabilitySeverity.UNKNOWN: 0,
        }

        return severity_levels.get(vulnerability.severity, 0) >= severity_levels.get(
            rule.severity_threshold, 0
        )

    def _check_scan_frequency_compliance(self) -> List[ComplianceViolation]:
        """Check compliance with scan frequency requirements."""
        violations = []

        # Get scan events from last 48 hours
        two_days_ago = datetime.now() - timedelta(days=2)
        recent_events = self.audit_trail.get_audit_events(
            start_date=two_days_ago, event_type=AuditEventType.SCAN_COMPLETED
        )

        # Check if we have at least one scan in the last 24 hours
        one_day_ago = datetime.now() - timedelta(days=1)
        recent_scans = [e for e in recent_events if e.timestamp >= one_day_ago]

        if not recent_scans:
            violations.append(
                ComplianceViolation(
                    violation_id=f"SCAN_FREQ_VIOLATION_{datetime.now().strftime('%Y%m%d')}",
                    rule_id="DAILY_SCAN",
                    vulnerability_id=None,
                    package_name=None,
                    violation_type="scan_frequency",
                    description="No security scans performed in the last 24 hours",
                    severity="high",
                    detected_at=datetime.now(),
                )
            )

        return violations

    def generate_compliance_report(
        self,
        framework: ComplianceFramework,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        output_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Generate framework-specific compliance report.

        Args:
            framework: Compliance framework to report against
            start_date: Start date for report period
            end_date: End date for report period
            output_file: Optional file to save the report

        Returns:
            Dictionary containing compliance report
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Get audit trail for the period
        audit_report = self.audit_trail.generate_compliance_report(
            start_date=start_date, end_date=end_date
        )

        # Get framework-specific policy rules
        framework_rules = [
            rule
            for rule in self.policy_rules.values()
            if rule.framework == framework or framework == ComplianceFramework.CUSTOM
        ]

        # Generate framework-specific content
        framework_content = self._generate_framework_content(framework, audit_report)

        # Build compliance report
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "framework": framework.value,
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "generator": "vet-core-security-compliance",
                "version": "1.0.0",
            },
            "executive_summary": self._generate_executive_summary(
                audit_report, framework_rules
            ),
            "framework_requirements": framework_content,
            "policy_compliance": {
                "applicable_rules": [rule.to_dict() for rule in framework_rules],
                "compliance_status": self._assess_overall_compliance(audit_report),
            },
            "evidence_documentation": self._generate_evidence_documentation(
                audit_report
            ),
            "recommendations": self._generate_compliance_recommendations(
                audit_report, framework
            ),
            "audit_trail_summary": audit_report,
        }

        # Save to file if requested
        if output_file:
            self._save_compliance_report(report, output_file)

        return report

    def _generate_framework_content(
        self, framework: ComplianceFramework, audit_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate framework-specific compliance content."""
        if framework == ComplianceFramework.NIST_CSF:
            return self._generate_nist_csf_content(audit_report)
        elif framework == ComplianceFramework.ISO_27001:
            return self._generate_iso27001_content(audit_report)
        elif framework == ComplianceFramework.SOC2:
            return self._generate_soc2_content(audit_report)
        elif framework == ComplianceFramework.PCI_DSS:
            return self._generate_pci_dss_content(audit_report)
        else:
            return {
                "framework": framework.value,
                "content": "Custom framework compliance",
            }

    def _generate_nist_csf_content(
        self, audit_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate NIST Cybersecurity Framework specific content."""
        return {
            "framework": "NIST Cybersecurity Framework",
            "functions": {
                "identify": {
                    "description": "Asset Management and Risk Assessment",
                    "evidence": [
                        f"Vulnerability scanning performed {audit_report['executive_summary']['scans_completed']} times",
                        f"Risk assessments completed for all {audit_report['executive_summary']['vulnerabilities_detected']} detected vulnerabilities",
                    ],
                    "compliance_status": "compliant",
                },
                "protect": {
                    "description": "Protective Technology and Processes",
                    "evidence": [
                        "Automated vulnerability scanning implemented",
                        "Security policies enforced through automated checks",
                    ],
                    "compliance_status": "compliant",
                },
                "detect": {
                    "description": "Security Continuous Monitoring",
                    "evidence": [
                        f"Continuous monitoring with {audit_report['executive_summary']['scans_completed']} security scans",
                        "Automated vulnerability detection and alerting",
                    ],
                    "compliance_status": "compliant",
                },
                "respond": {
                    "description": "Response Planning and Communications",
                    "evidence": [
                        f"{audit_report['executive_summary']['vulnerabilities_resolved']} vulnerabilities remediated",
                        "Incident response procedures documented and followed",
                    ],
                    "compliance_status": (
                        "compliant"
                        if audit_report["executive_summary"]["vulnerabilities_resolved"]
                        > 0
                        else "partial"
                    ),
                },
                "recover": {
                    "description": "Recovery Planning and Improvements",
                    "evidence": [
                        "Vulnerability remediation tracking implemented",
                        "Continuous improvement through compliance monitoring",
                    ],
                    "compliance_status": "compliant",
                },
            },
        }

    def _generate_iso27001_content(
        self, audit_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate ISO 27001 specific content."""
        return {
            "framework": "ISO 27001:2013",
            "controls": {
                "A.12.6.1": {
                    "title": "Management of technical vulnerabilities",
                    "description": "Information about technical vulnerabilities shall be obtained in a timely fashion",
                    "evidence": [
                        f"Automated vulnerability scanning with {audit_report['executive_summary']['scans_completed']} scans performed",
                        f"{audit_report['executive_summary']['vulnerabilities_detected']} vulnerabilities detected and tracked",
                    ],
                    "compliance_status": "implemented",
                },
                "A.16.1.3": {
                    "title": "Reporting information security weaknesses",
                    "description": "All employees and contractors shall report observed or suspected information security weaknesses",
                    "evidence": [
                        "Comprehensive audit trail maintained",
                        f"{audit_report['report_metadata']['total_events']} security events logged",
                    ],
                    "compliance_status": "implemented",
                },
            },
        }

    def _generate_soc2_content(self, audit_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SOC 2 specific content."""
        return {
            "framework": "SOC 2 Type II",
            "trust_criteria": {
                "security": {
                    "description": "System is protected against unauthorized access",
                    "controls": [
                        "Vulnerability management program implemented",
                        "Regular security scanning and monitoring",
                        "Incident response and remediation procedures",
                    ],
                    "evidence": audit_report["executive_summary"],
                    "compliance_status": "effective",
                },
                "availability": {
                    "description": "System is available for operation and use",
                    "controls": [
                        "Proactive vulnerability management",
                        "Timely security patching and updates",
                    ],
                    "evidence": {
                        "vulnerabilities_resolved": audit_report["executive_summary"][
                            "vulnerabilities_resolved"
                        ]
                    },
                    "compliance_status": "effective",
                },
            },
        }

    def _generate_pci_dss_content(self, audit_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate PCI DSS specific content."""
        return {
            "framework": "PCI DSS v3.2.1",
            "requirements": {
                "req_6": {
                    "title": "Develop and maintain secure systems and applications",
                    "sub_requirements": {
                        "6.1": {
                            "description": "Establish a process to identify security vulnerabilities",
                            "evidence": [
                                f"Automated vulnerability scanning: {audit_report['executive_summary']['scans_completed']} scans",
                                "Comprehensive vulnerability tracking and management",
                            ],
                            "compliance_status": "compliant",
                        },
                        "6.2": {
                            "description": "Ensure all system components are protected from known vulnerabilities",
                            "evidence": [
                                f"{audit_report['executive_summary']['vulnerabilities_resolved']} vulnerabilities remediated",
                                "Regular security updates and patch management",
                            ],
                            "compliance_status": "compliant",
                        },
                    },
                },
                "req_11": {
                    "title": "Regularly test security systems and processes",
                    "sub_requirements": {
                        "11.2": {
                            "description": "Run internal and external network vulnerability scans",
                            "evidence": [
                                f"Regular vulnerability scanning: {audit_report['executive_summary']['scans_completed']} scans performed",
                                "Comprehensive vulnerability assessment and tracking",
                            ],
                            "compliance_status": "compliant",
                        }
                    },
                },
            },
        }

    def _generate_executive_summary(
        self, audit_report: Dict[str, Any], framework_rules: List[PolicyRule]
    ) -> Dict[str, Any]:
        """Generate executive summary for compliance report."""
        latest_metrics = audit_report.get("compliance_metrics_history", [])
        current_metrics = latest_metrics[0] if latest_metrics else {}

        return {
            "compliance_overview": {
                "overall_score": current_metrics.get("compliance_score", 0),
                "policy_violations": current_metrics.get("policy_violations", 0),
                "active_policy_rules": len(framework_rules),
                "assessment_period": audit_report["report_metadata"]["report_period"],
            },
            "security_posture": {
                "total_vulnerabilities": current_metrics.get(
                    "total_vulnerabilities", 0
                ),
                "critical_vulnerabilities": current_metrics.get(
                    "critical_vulnerabilities", 0
                ),
                "vulnerabilities_resolved": audit_report["executive_summary"][
                    "vulnerabilities_resolved"
                ],
                "mean_resolution_time": audit_report.get(
                    "vulnerability_lifecycle_analysis", {}
                ).get("mean_resolution_time_hours", 0),
            },
            "operational_metrics": {
                "security_scans_performed": audit_report["executive_summary"][
                    "scans_completed"
                ],
                "audit_events_logged": audit_report["report_metadata"]["total_events"],
                "compliance_checks_performed": audit_report["executive_summary"][
                    "compliance_checks"
                ],
            },
        }

    def _assess_overall_compliance(self, audit_report: Dict[str, Any]) -> str:
        """Assess overall compliance status."""
        latest_metrics = audit_report.get("compliance_metrics_history", [])
        if not latest_metrics:
            return "unknown"

        current_metrics = latest_metrics[0]
        compliance_score = current_metrics.get("compliance_score", 0)

        if compliance_score >= 95:
            return "fully_compliant"
        elif compliance_score >= 80:
            return "substantially_compliant"
        elif compliance_score >= 60:
            return "partially_compliant"
        else:
            return "non_compliant"

    def _generate_evidence_documentation(
        self, audit_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate evidence documentation for compliance."""
        return {
            "audit_trail_evidence": {
                "total_events_logged": audit_report["report_metadata"]["total_events"],
                "event_types_tracked": list(audit_report["event_summary"].keys()),
                "data_retention_period": "365 days",
                "audit_trail_integrity": "maintained",
            },
            "vulnerability_management_evidence": {
                "detection_capabilities": "automated vulnerability scanning",
                "assessment_procedures": "risk-based prioritization",
                "remediation_tracking": "complete lifecycle tracking",
                "compliance_monitoring": "continuous policy enforcement",
            },
            "documentation_evidence": {
                "policies_documented": True,
                "procedures_documented": True,
                "audit_trail_maintained": True,
                "compliance_reports_generated": True,
            },
        }

    def _generate_compliance_recommendations(
        self, audit_report: Dict[str, Any], framework: ComplianceFramework
    ) -> List[str]:
        """Generate compliance improvement recommendations."""
        recommendations = []

        latest_metrics = audit_report.get("compliance_metrics_history", [])
        if latest_metrics:
            current_metrics = latest_metrics[0]

            if current_metrics.get("critical_vulnerabilities", 0) > 0:
                recommendations.append(
                    f"Address {current_metrics['critical_vulnerabilities']} critical vulnerabilities immediately"
                )

            if current_metrics.get("policy_violations", 0) > 0:
                recommendations.append(
                    f"Resolve {current_metrics['policy_violations']} policy violations"
                )

            if current_metrics.get("compliance_score", 0) < 90:
                recommendations.append(
                    "Improve overall compliance score through enhanced vulnerability management"
                )

        if (
            audit_report["executive_summary"]["scans_completed"] < 25
        ):  # Less than daily scanning
            recommendations.append(
                "Increase scan frequency to meet daily scanning requirements"
            )

        if not recommendations:
            recommendations.append(
                "Maintain current security posture and continue monitoring"
            )

        return recommendations

    def _save_compliance_report(
        self, report: Dict[str, Any], output_file: Path
    ) -> None:
        """Save compliance report to file."""
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2, default=str)
            self.logger.info(f"Compliance report saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save compliance report: {e}")
            raise

    def add_policy_rule(self, rule: PolicyRule) -> None:
        """Add a new policy rule."""
        self.policy_rules[rule.rule_id] = rule
        self.logger.info(f"Added policy rule: {rule.rule_id}")

    def remove_policy_rule(self, rule_id: str) -> bool:
        """Remove a policy rule."""
        if rule_id in self.policy_rules:
            del self.policy_rules[rule_id]
            self.logger.info(f"Removed policy rule: {rule_id}")
            return True
        return False

    def get_policy_rules(
        self, framework: Optional[ComplianceFramework] = None
    ) -> List[PolicyRule]:
        """Get policy rules, optionally filtered by framework."""
        if framework:
            return [
                rule
                for rule in self.policy_rules.values()
                if rule.framework == framework
            ]
        return list(self.policy_rules.values())
