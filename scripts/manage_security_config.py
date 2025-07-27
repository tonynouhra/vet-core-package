#!/usr/bin/env python3
"""
Security configuration management CLI tool.

This script provides a command-line interface for managing security configurations
across different environments.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vet_core.security.config import (
    SecurityConfigManager,
    Environment,
    ConfigurationError,
    VulnerabilitySeverity,
)


def create_config(
    config_manager: SecurityConfigManager,
    environment: Environment,
    interactive: bool = False
) -> None:
    """Create a new configuration for an environment."""
    try:
        if interactive:
            print(f"Creating configuration for {environment.value} environment...")
            
            # Get basic settings
            scan_schedule = input("Scan schedule (cron format) [0 6 * * *]: ").strip() or "0 6 * * *"
            
            # Auto-fix settings
            auto_fix_enabled = input("Enable auto-fix? (y/n) [n]: ").strip().lower() == 'y'
            
            if auto_fix_enabled:
                print("Available severity levels: critical, high, medium, low")
                max_severity = input("Maximum auto-fix severity [medium]: ").strip() or "medium"
                try:
                    max_severity_enum = VulnerabilitySeverity(max_severity)
                except ValueError:
                    print(f"Invalid severity level: {max_severity}. Using 'medium'.")
                    max_severity_enum = VulnerabilitySeverity.MEDIUM
            else:
                max_severity_enum = VulnerabilitySeverity.MEDIUM
            
            # Notification settings
            email_list = input("Email addresses (comma-separated): ").strip()
            emails = [email.strip() for email in email_list.split(",") if email.strip()]
            
            slack_webhook = input("Slack webhook URL (optional): ").strip() or None
            
            # Create configuration with user inputs
            config = config_manager._create_default_config(environment)
            config.base_config.scan_schedule = scan_schedule
            config.auto_fix.enabled = auto_fix_enabled
            config.auto_fix.max_severity = max_severity_enum
            config.notifications.email = emails
            config.notifications.slack_webhook = slack_webhook
            
        else:
            # Create default configuration
            config = config_manager._create_default_config(environment)
        
        # Validate configuration
        errors = config_manager.validate_config(config)
        if errors:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            return
        
        # Save configuration
        config_manager.save_config(config)
        print(f"✅ Configuration created for {environment.value} environment")
        
    except Exception as e:
        print(f"❌ Failed to create configuration: {e}")


def show_config(
    config_manager: SecurityConfigManager,
    environment: Environment,
    format_type: str = "yaml"
) -> None:
    """Display configuration for an environment."""
    try:
        config = config_manager.load_config(environment)
        
        print(f"Configuration for {environment.value} environment:")
        print("-" * 50)
        
        if format_type == "json":
            config_dict = {
                "environment": config.environment.value,
                "base_config": config.base_config.to_dict(),
                "notifications": {
                    "email": config.notifications.email,
                    "slack_webhook": config.notifications.slack_webhook,
                    "teams_webhook": config.notifications.teams_webhook,
                    "github_issues": config.notifications.github_issues,
                    "console": config.notifications.console,
                },
                "scanner": {
                    "primary_scanner": config.scanner.primary_scanner,
                    "backup_scanners": config.scanner.backup_scanners,
                    "timeout": config.scanner.timeout,
                    "retry_attempts": config.scanner.retry_attempts,
                },
                "auto_fix": {
                    "enabled": config.auto_fix.enabled,
                    "max_severity": config.auto_fix.max_severity.value,
                    "dry_run": config.auto_fix.dry_run,
                    "require_approval": config.auto_fix.require_approval,
                },
                "compliance": {
                    "audit_retention_days": config.compliance.audit_retention_days,
                    "compliance_standards": config.compliance.compliance_standards,
                    "generate_reports": config.compliance.generate_reports,
                }
            }
            print(json.dumps(config_dict, indent=2))
        else:
            # Human-readable format
            print(f"Environment: {config.environment.value}")
            print(f"Scan Schedule: {config.base_config.scan_schedule}")
            print(f"Scanner Timeout: {config.base_config.scanner_timeout}s")
            print()
            
            print("Auto-fix Settings:")
            print(f"  Enabled: {config.auto_fix.enabled}")
            print(f"  Max Severity: {config.auto_fix.max_severity.value}")
            print(f"  Dry Run: {config.auto_fix.dry_run}")
            print(f"  Require Approval: {config.auto_fix.require_approval}")
            print()
            
            print("Notifications:")
            print(f"  Email: {', '.join(config.notifications.email) if config.notifications.email else 'None'}")
            print(f"  Slack: {'Configured' if config.notifications.slack_webhook else 'Not configured'}")
            print(f"  Console: {config.notifications.console}")
            print()
            
            print("Scanner Settings:")
            print(f"  Primary: {config.scanner.primary_scanner}")
            print(f"  Backup: {', '.join(config.scanner.backup_scanners)}")
            print(f"  Timeout: {config.scanner.timeout}s")
            print()
            
            print("Compliance:")
            print(f"  Standards: {', '.join(config.compliance.compliance_standards)}")
            print(f"  Retention: {config.compliance.audit_retention_days} days")
            print(f"  Generate Reports: {config.compliance.generate_reports}")
            
    except Exception as e:
        print(f"❌ Failed to show configuration: {e}")


def list_environments(config_manager: SecurityConfigManager) -> None:
    """List all configured environments."""
    try:
        environments = config_manager.list_environments()
        
        if not environments:
            print("No configured environments found.")
            return
        
        print("Configured environments:")
        for env in environments:
            try:
                config = config_manager.load_config(env)
                errors = config_manager.validate_config(config)
                status = "✅ Valid" if not errors else f"❌ {len(errors)} error(s)"
                print(f"  - {env.value}: {status}")
            except Exception as e:
                print(f"  - {env.value}: ❌ Error loading config: {e}")
                
    except Exception as e:
        print(f"❌ Failed to list environments: {e}")


def update_config(
    config_manager: SecurityConfigManager,
    environment: Environment,
    setting: str,
    value: str
) -> None:
    """Update a specific configuration setting."""
    try:
        config = config_manager.load_config(environment)
        
        # Parse the setting path (e.g., "auto_fix.enabled", "notifications.email")
        parts = setting.split(".")
        
        if len(parts) == 2:
            section, key = parts
            
            if section == "auto_fix":
                if key == "enabled":
                    config.auto_fix.enabled = value.lower() in ("true", "yes", "1")
                elif key == "max_severity":
                    config.auto_fix.max_severity = VulnerabilitySeverity(value)
                elif key == "dry_run":
                    config.auto_fix.dry_run = value.lower() in ("true", "yes", "1")
                elif key == "require_approval":
                    config.auto_fix.require_approval = value.lower() in ("true", "yes", "1")
                else:
                    print(f"❌ Unknown auto_fix setting: {key}")
                    return
                    
            elif section == "scanner":
                if key == "primary_scanner":
                    config.scanner.primary_scanner = value
                elif key == "timeout":
                    config.scanner.timeout = int(value)
                elif key == "retry_attempts":
                    config.scanner.retry_attempts = int(value)
                else:
                    print(f"❌ Unknown scanner setting: {key}")
                    return
                    
            elif section == "base_config":
                if key == "scan_schedule":
                    config.base_config.scan_schedule = value
                elif key == "scanner_timeout":
                    config.base_config.scanner_timeout = int(value)
                else:
                    print(f"❌ Unknown base_config setting: {key}")
                    return
                    
            else:
                print(f"❌ Unknown configuration section: {section}")
                return
        else:
            print(f"❌ Invalid setting format. Use 'section.key' format.")
            return
        
        # Validate updated configuration
        errors = config_manager.validate_config(config)
        if errors:
            print("❌ Configuration validation failed after update:")
            for error in errors:
                print(f"  - {error}")
            return
        
        # Save updated configuration
        config_manager.save_config(config)
        print(f"✅ Updated {setting} = {value} for {environment.value} environment")
        
    except ValueError as e:
        print(f"❌ Invalid value for {setting}: {e}")
    except Exception as e:
        print(f"❌ Failed to update configuration: {e}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Manage security configurations"
    )
    parser.add_argument(
        "--config-dir",
        "-c",
        type=Path,
        help="Configuration directory path",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create new configuration")
    create_parser.add_argument(
        "environment",
        choices=[env.value for env in Environment],
        help="Environment to create configuration for",
    )
    create_parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive configuration creation",
    )
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show configuration")
    show_parser.add_argument(
        "environment",
        choices=[env.value for env in Environment],
        help="Environment to show configuration for",
    )
    show_parser.add_argument(
        "--format",
        "-f",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format",
    )
    
    # List command
    subparsers.add_parser("list", help="List all configured environments")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update configuration setting")
    update_parser.add_argument(
        "environment",
        choices=[env.value for env in Environment],
        help="Environment to update",
    )
    update_parser.add_argument(
        "setting",
        help="Setting to update (e.g., auto_fix.enabled, scanner.timeout)",
    )
    update_parser.add_argument(
        "value",
        help="New value for the setting",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize configuration manager
    config_manager = SecurityConfigManager(args.config_dir)
    
    try:
        if args.command == "create":
            create_config(
                config_manager,
                Environment(args.environment),
                args.interactive
            )
        elif args.command == "show":
            show_config(
                config_manager,
                Environment(args.environment),
                args.format
            )
        elif args.command == "list":
            list_environments(config_manager)
        elif args.command == "update":
            update_config(
                config_manager,
                Environment(args.environment),
                args.setting,
                args.value
            )
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()