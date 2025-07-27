"""
Security notification system for vulnerability alerts and remediation recommendations.

This module provides functionality to send notifications about security vulnerabilities
through various channels including email, Slack, GitHub issues, and more.
"""

import json
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from .assessor import RiskAssessor
from .models import SecurityReport, Vulnerability, VulnerabilitySeverity

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""

    # Email settings
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: Optional[List[str]] = None

    # Slack settings
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None

    # GitHub settings
    github_token: Optional[str] = None
    github_repo: Optional[str] = None

    # Notification thresholds
    min_severity_for_email: VulnerabilitySeverity = VulnerabilitySeverity.HIGH
    min_severity_for_slack: VulnerabilitySeverity = VulnerabilitySeverity.MEDIUM
    min_severity_for_github_issue: VulnerabilitySeverity = (
        VulnerabilitySeverity.CRITICAL
    )

    # General settings
    notification_title_prefix: str = "🚨 Security Alert"
    include_remediation_recommendations: bool = True

    def __post_init__(self) -> None:
        """Initialize default values after dataclass creation."""
        if self.email_to is None:
            self.email_to = []


class SecurityNotifier:
    """Handles sending security vulnerability notifications through multiple channels."""

    def __init__(self, config: NotificationConfig) -> None:
        """
        Initialize the security notifier.

        Args:
            config: Notification configuration
        """
        self.config = config
        self.risk_assessor = RiskAssessor()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def send_vulnerability_alert(
        self, report: SecurityReport, channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send vulnerability alerts through configured channels.

        Args:
            report: Security report containing vulnerabilities
            channels: Optional list of channels to use ('email', 'slack', 'github')
                     If None, all configured channels will be used

        Returns:
            Dictionary mapping channel names to success status
        """
        if not report.vulnerabilities:
            self.logger.info("No vulnerabilities found, skipping notifications")
            return {}

        # Determine which channels to use
        available_channels = self._get_available_channels()
        if channels:
            channels = [ch for ch in channels if ch in available_channels]
        else:
            channels = available_channels

        if not channels:
            self.logger.warning("No notification channels configured or available")
            return {}

        # Get risk assessment and prioritization
        prioritized = self.risk_assessor.get_prioritized_vulnerabilities(report)
        priority_summary = self.risk_assessor.generate_priority_summary(prioritized)

        # Determine notification urgency
        max_severity = self._get_max_severity(report.vulnerabilities)

        results = {}

        # Send email notifications
        if (
            "email" in channels
            and max_severity.value >= self.config.min_severity_for_email.value
        ):
            try:
                success = self._send_email_notification(
                    report, prioritized, priority_summary
                )
                results["email"] = success
            except Exception as e:
                self.logger.error(f"Failed to send email notification: {e}")
                results["email"] = False

        # Send Slack notifications
        if (
            "slack" in channels
            and max_severity.value >= self.config.min_severity_for_slack.value
        ):
            try:
                success = self._send_slack_notification(
                    report, prioritized, priority_summary
                )
                results["slack"] = success
            except Exception as e:
                self.logger.error(f"Failed to send Slack notification: {e}")
                results["slack"] = False

        # Create GitHub issues
        if (
            "github" in channels
            and max_severity.value >= self.config.min_severity_for_github_issue.value
        ):
            try:
                success = self._create_github_issue(
                    report, prioritized, priority_summary
                )
                results["github"] = success
            except Exception as e:
                self.logger.error(f"Failed to create GitHub issue: {e}")
                results["github"] = False

        return results

    def send_remediation_update(
        self,
        vulnerability_id: str,
        status: str,
        notes: Optional[str] = None,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        Send updates about vulnerability remediation progress.

        Args:
            vulnerability_id: ID of the vulnerability being updated
            status: Current status ('in_progress', 'completed', 'failed')
            notes: Optional additional notes
            channels: Channels to send updates to

        Returns:
            Dictionary mapping channel names to success status
        """
        available_channels = self._get_available_channels()
        if channels:
            channels = [ch for ch in channels if ch in available_channels]
        else:
            channels = available_channels

        results = {}

        # Create update message
        status_emoji = {"in_progress": "🔄", "completed": "✅", "failed": "❌"}

        emoji = status_emoji.get(status, "📋")
        title = f"{emoji} Vulnerability Remediation Update"

        message = f"""
**Vulnerability ID:** {vulnerability_id}
**Status:** {status.replace('_', ' ').title()}
**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

        if notes:
            message += f"\n**Notes:** {notes}"

        # Send to configured channels
        for channel in channels:
            try:
                if channel == "slack":
                    success = self._send_slack_message(title, message)
                    results[channel] = success
                elif channel == "email":
                    success = self._send_email_message(title, message)
                    results[channel] = success
                # GitHub updates would typically be comments on existing issues

            except Exception as e:
                self.logger.error(f"Failed to send {channel} update: {e}")
                results[channel] = False

        return results

    def _get_available_channels(self) -> List[str]:
        """Get list of available notification channels based on configuration."""
        channels = []

        if (
            self.config.smtp_server
            and self.config.email_from
            and self.config.email_to
            and self.config.smtp_username
        ):
            channels.append("email")

        if self.config.slack_webhook_url:
            channels.append("slack")

        if self.config.github_token and self.config.github_repo:
            channels.append("github")

        return channels

    def _get_max_severity(
        self, vulnerabilities: List[Vulnerability]
    ) -> VulnerabilitySeverity:
        """Get the maximum severity level from a list of vulnerabilities."""
        if not vulnerabilities:
            return VulnerabilitySeverity.UNKNOWN

        severity_order = [
            VulnerabilitySeverity.CRITICAL,
            VulnerabilitySeverity.HIGH,
            VulnerabilitySeverity.MEDIUM,
            VulnerabilitySeverity.LOW,
            VulnerabilitySeverity.UNKNOWN,
        ]

        for severity in severity_order:
            if any(v.severity == severity for v in vulnerabilities):
                return severity

        return VulnerabilitySeverity.UNKNOWN

    def _send_email_notification(
        self,
        report: SecurityReport,
        prioritized: Dict[str, List],
        priority_summary: Dict[str, Any],
    ) -> bool:
        """Send email notification about vulnerabilities."""
        try:
            # Create email content
            subject = f"{self.config.notification_title_prefix} - {report.vulnerability_count} Vulnerabilities Found"

            # Create HTML email body
            html_body = self._create_email_html_body(
                report, prioritized, priority_summary
            )

            # Create text email body
            text_body = self._create_email_text_body(
                report, prioritized, priority_summary
            )

            # Validate required email configuration
            if not self.config.email_from or not self.config.email_to:
                raise ValueError("Email configuration incomplete: email_from and email_to are required")
            if not self.config.smtp_server or not self.config.smtp_username or not self.config.smtp_password:
                raise ValueError("SMTP configuration incomplete: server, username, and password are required")

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.email_from
            msg["To"] = ", ".join(self.config.email_to)

            # Attach both text and HTML versions
            text_part = MIMEText(text_body, "plain")
            html_part = MIMEText(html_body, "html")

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)

            self.logger.info(
                f"Email notification sent to {len(self.config.email_to)} recipients"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False

    def _send_slack_notification(
        self,
        report: SecurityReport,
        prioritized: Dict[str, List],
        priority_summary: Dict[str, Any],
    ) -> bool:
        """Send Slack notification about vulnerabilities."""
        try:
            # Determine color based on severity
            color = (
                "danger"
                if report.critical_count > 0
                else "warning" if report.high_count > 0 else "good"
            )

            # Create Slack payload
            payload = {
                "text": f"{self.config.notification_title_prefix} - Vulnerability Scan Results",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {
                                "title": "Total Vulnerabilities",
                                "value": str(report.vulnerability_count),
                                "short": True,
                            },
                            {
                                "title": "Critical",
                                "value": str(report.critical_count),
                                "short": True,
                            },
                            {
                                "title": "High",
                                "value": str(report.high_count),
                                "short": True,
                            },
                            {
                                "title": "Medium",
                                "value": str(report.medium_count),
                                "short": True,
                            },
                            {
                                "title": "Low",
                                "value": str(report.low_count),
                                "short": True,
                            },
                            {
                                "title": "Fixable",
                                "value": str(report.fixable_count),
                                "short": True,
                            },
                        ],
                        "footer": f"Scan completed at {report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                        "ts": int(report.scan_date.timestamp()),
                    }
                ],
            }

            # Add immediate action items if critical vulnerabilities exist
            if report.critical_count > 0:
                immediate_vulns = prioritized.get("immediate", [])
                if immediate_vulns:
                    vuln_list = []
                    for vuln, assessment in immediate_vulns[:5]:  # Limit to first 5
                        vuln_list.append(f"• {vuln.package_name} ({vuln.id})")

                    payload["attachments"].append(
                        {
                            "color": "danger",
                            "title": "🚨 Immediate Action Required (24h)",
                            "text": "\n".join(vuln_list),
                            "footer": "Apply security fixes immediately",
                        }
                    )

            # Add channel if specified
            if self.config.slack_channel:
                payload["channel"] = self.config.slack_channel

            # Send to Slack
            response = requests.post(
                self.config.slack_webhook_url, json=payload, timeout=30
            )
            response.raise_for_status()

            self.logger.info("Slack notification sent successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _create_github_issue(
        self,
        report: SecurityReport,
        prioritized: Dict[str, List],
        priority_summary: Dict[str, Any],
    ) -> bool:
        """Create GitHub issue for critical vulnerabilities."""
        try:
            # Create issue title
            title = f"🚨 Critical Security Vulnerabilities - {report.scan_date.strftime('%Y-%m-%d')}"

            # Create issue body
            body = self._create_github_issue_body(report, prioritized, priority_summary)

            # GitHub API headers
            headers = {
                "Authorization": f"token {self.config.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            }

            # Create issue payload
            payload = {
                "title": title,
                "body": body,
                "labels": ["security", "vulnerability", "critical", "automated"],
            }

            # Validate GitHub configuration
            if not self.config.github_repo:
                raise ValueError("GitHub repository not configured")
            
            # Send to GitHub API
            repo_parts = self.config.github_repo.split("/")
            if len(repo_parts) != 2:
                raise ValueError("GitHub repository must be in format 'owner/repo'")
            url = f"https://api.github.com/repos/{repo_parts[0]}/{repo_parts[1]}/issues"

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            issue_data = response.json()
            issue_number = issue_data["number"]

            self.logger.info(f"GitHub issue #{issue_number} created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create GitHub issue: {e}")
            return False

    def _send_slack_message(self, title: str, message: str) -> bool:
        """Send a simple Slack message."""
        try:
            payload = {
                "text": title,
                "attachments": [{"text": message, "color": "good"}],
            }

            if self.config.slack_channel:
                payload["channel"] = self.config.slack_channel

            response = requests.post(
                self.config.slack_webhook_url, json=payload, timeout=30
            )
            response.raise_for_status()
            return True

        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")
            return False

    def _send_email_message(self, title: str, message: str) -> bool:
        """Send a simple email message."""
        try:
            msg = MIMEText(message)
            msg["Subject"] = title
            msg["From"] = self.config.email_from
            msg["To"] = ", ".join(self.config.email_to)

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            self.logger.error(f"Failed to send email message: {e}")
            return False

    def _create_email_html_body(
        self,
        report: SecurityReport,
        prioritized: Dict[str, List],
        priority_summary: Dict[str, Any],
    ) -> str:
        """Create HTML email body."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; }}
                .critical {{ color: #dc3545; }}
                .high {{ color: #fd7e14; }}
                .medium {{ color: #ffc107; }}
                .low {{ color: #28a745; }}
                .vulnerability {{ margin: 10px 0; padding: 10px; border-left: 4px solid #007bff; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 Security Vulnerability Report</h1>
                <p><strong>Scan Date:</strong> {report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Total Vulnerabilities:</strong> {report.vulnerability_count}</p>
            </div>
            
            <h2>Severity Summary</h2>
            <table>
                <tr>
                    <th>Severity</th>
                    <th>Count</th>
                </tr>
                <tr>
                    <td class="critical">Critical</td>
                    <td>{report.critical_count}</td>
                </tr>
                <tr>
                    <td class="high">High</td>
                    <td>{report.high_count}</td>
                </tr>
                <tr>
                    <td class="medium">Medium</td>
                    <td>{report.medium_count}</td>
                </tr>
                <tr>
                    <td class="low">Low</td>
                    <td>{report.low_count}</td>
                </tr>
            </table>
        """

        # Add immediate action items
        immediate_vulns = prioritized.get("immediate", [])
        if immediate_vulns:
            html += """
            <h2>🚨 Immediate Action Required (24 hours)</h2>
            <ul>
            """
            for vuln, assessment in immediate_vulns:
                html += f"""
                <li class="vulnerability">
                    <strong>{vuln.id}</strong> - {vuln.package_name} {vuln.installed_version}
                    <br>Risk Score: {assessment.risk_score:.1f}/10.0
                    {f'<br>Fix: Upgrade to {vuln.recommended_fix_version}' if vuln.recommended_fix_version else ''}
                </li>
                """
            html += "</ul>"

        html += """
            <h2>Next Steps</h2>
            <ol>
                <li>Review all critical and high severity vulnerabilities</li>
                <li>Apply available security fixes immediately</li>
                <li>Monitor for additional security updates</li>
                <li>Update security documentation and procedures</li>
            </ol>
            
            <p><em>This is an automated security alert. Please take immediate action on critical vulnerabilities.</em></p>
        </body>
        </html>
        """

        return html

    def _create_email_text_body(
        self,
        report: SecurityReport,
        prioritized: Dict[str, List],
        priority_summary: Dict[str, Any],
    ) -> str:
        """Create plain text email body."""
        text = f"""
SECURITY VULNERABILITY REPORT
=============================

Scan Date: {report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')}
Total Vulnerabilities: {report.vulnerability_count}

SEVERITY SUMMARY
----------------
Critical: {report.critical_count}
High: {report.high_count}
Medium: {report.medium_count}
Low: {report.low_count}
Fixable: {report.fixable_count}
"""

        # Add immediate action items
        immediate_vulns = prioritized.get("immediate", [])
        if immediate_vulns:
            text += """
IMMEDIATE ACTION REQUIRED (24 hours)
------------------------------------
"""
            for vuln, assessment in immediate_vulns:
                text += f"""
• {vuln.id} - {vuln.package_name} {vuln.installed_version}
  Risk Score: {assessment.risk_score:.1f}/10.0
"""
                if vuln.recommended_fix_version:
                    text += f"  Fix: Upgrade to {vuln.recommended_fix_version}\n"

        text += """
NEXT STEPS
----------
1. Review all critical and high severity vulnerabilities
2. Apply available security fixes immediately
3. Monitor for additional security updates
4. Update security documentation and procedures

This is an automated security alert. Please take immediate action on critical vulnerabilities.
"""

        return text

    def _create_github_issue_body(
        self,
        report: SecurityReport,
        prioritized: Dict[str, List],
        priority_summary: Dict[str, Any],
    ) -> str:
        """Create GitHub issue body."""
        body = f"""# 🚨 Critical Security Vulnerabilities Detected

**Scan Date:** {report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')}
**Total Vulnerabilities:** {report.vulnerability_count}

## Severity Breakdown
- **Critical:** {report.critical_count}
- **High:** {report.high_count}
- **Medium:** {report.medium_count}
- **Low:** {report.low_count}
- **Fixable:** {report.fixable_count}

## Immediate Action Required (24 hours)
"""

        immediate_vulns = prioritized.get("immediate", [])
        if immediate_vulns:
            for vuln, assessment in immediate_vulns:
                body += f"""
### {vuln.id} - {vuln.package_name}
- **Current Version:** {vuln.installed_version}
- **Risk Score:** {assessment.risk_score:.1f}/10.0
- **Severity:** {vuln.severity.value.title()}
"""
                if vuln.recommended_fix_version:
                    body += f"- **Recommended Fix:** Upgrade to {vuln.recommended_fix_version}\n"

                if vuln.description:
                    body += f"- **Description:** {vuln.description}\n"
        else:
            body += "\nNo immediate action items found.\n"

        body += f"""
## Next Steps
1. 🔍 Review all critical and high severity vulnerabilities
2. 🚀 Apply security fixes immediately
3. 📋 Update this issue with remediation progress
4. ✅ Close this issue once all critical vulnerabilities are resolved

## Remediation Checklist
"""

        for vuln, assessment in immediate_vulns:
            body += f"- [ ] Fix {vuln.id} ({vuln.package_name})\n"

        body += """
---

**Automated Security Monitoring**
This issue was created automatically by the security monitoring system.
Please update this issue with your remediation progress and close it once all critical vulnerabilities are resolved.
"""

        return body


def create_notification_config_from_env() -> NotificationConfig:
    """Create notification configuration from environment variables."""
    import os

    return NotificationConfig(
        # Email settings
        smtp_server=os.getenv("SMTP_SERVER"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        email_from=os.getenv("EMAIL_FROM"),
        email_to=os.getenv("EMAIL_TO", "").split(",") if os.getenv("EMAIL_TO") else [],
        # Slack settings
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
        slack_channel=os.getenv("SLACK_CHANNEL"),
        # GitHub settings
        github_token=os.getenv("GITHUB_TOKEN"),
        github_repo=os.getenv("GITHUB_REPOSITORY"),
        # Thresholds
        min_severity_for_email=VulnerabilitySeverity(
            os.getenv("MIN_SEVERITY_EMAIL", "high")
        ),
        min_severity_for_slack=VulnerabilitySeverity(
            os.getenv("MIN_SEVERITY_SLACK", "medium")
        ),
        min_severity_for_github_issue=VulnerabilitySeverity(
            os.getenv("MIN_SEVERITY_GITHUB", "critical")
        ),
    )
