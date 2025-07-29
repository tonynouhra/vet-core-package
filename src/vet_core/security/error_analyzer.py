"""
Error analysis module for categorizing and analyzing restoration errors.

This module provides functionality for:
- Categorizing different types of errors that occur during package restoration
- Analyzing error messages and providing recovery suggestions
- Determining error recoverability and confidence levels
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .upgrade_validator import RestoreResult


class ErrorCategory(Enum):
    """Categories of errors that can occur during package restoration."""
    
    UNKNOWN = "unknown"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    PACKAGE_NOT_FOUND = "package_not_found"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    DISK_SPACE_ERROR = "disk_space_error"
    PYTHON_VERSION_INCOMPATIBLE = "python_version_incompatible"
    CORRUPTED_PACKAGE = "corrupted_package"
    BACKUP_INVALID = "backup_invalid"
    SYSTEM_ERROR = "system_error"


@dataclass
class ErrorAnalysis:
    """Analysis results for a restoration error."""
    
    category: ErrorCategory
    confidence: float
    description: str
    suggested_actions: List[str] = field(default_factory=list)
    affected_packages: List[str] = field(default_factory=list)
    technical_details: Dict[str, Any] = field(default_factory=dict)
    is_recoverable: bool = True
    error_message: str = ""
    recovery_suggestions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize computed properties after dataclass initialization."""
        if not self.recovery_suggestions:
            self.recovery_suggestions = self.suggested_actions.copy()


class ErrorAnalyzer:
    """Analyzes restoration errors and provides categorization and recovery suggestions."""
    
    def __init__(self):
        """Initialize the error analyzer with pattern matching rules."""
        self._error_patterns = {
            ErrorCategory.NETWORK_ERROR: [
                r"connection.*timed?\s*out",
                r"network.*error",
                r"could not connect",
                r"connection.*refused",
                r"timeout.*downloading",
                r"failed to download",
                r"network.*unreachable",
                r"dns.*resolution.*failed",
            ],
            ErrorCategory.PERMISSION_ERROR: [
                r"permission\s+denied",
                r"access\s+denied",
                r"cannot\s+write\s+to",
                r"insufficient.*privileges",
                r"operation.*not.*permitted",
                r"errno\s+13",
            ],
            ErrorCategory.PACKAGE_NOT_FOUND: [
                r"no\s+matching\s+distribution\s+found",
                r"could\s+not\s+find\s+a\s+version",
                r"package.*not.*found",
                r"no\s+such\s+package",
                r"404.*not.*found",
            ],
            ErrorCategory.DEPENDENCY_CONFLICT: [
                r"dependency.*conflict",
                r"cannot\s+satisfy\s+requirement",
                r"incompatible.*requirements",
                r"version.*conflict",
                r"requires.*but.*installed",
            ],
            ErrorCategory.DISK_SPACE_ERROR: [
                r"no\s+space\s+left\s+on\s+device",
                r"disk.*full",
                r"insufficient.*disk.*space",
                r"errno\s+28",
                r"cannot\s+write.*no\s+space",
            ],
            ErrorCategory.PYTHON_VERSION_INCOMPATIBLE: [
                r"requires\s+python\s+>=?\s*\d+\.\d+",
                r"python\s+version.*incompatible",
                r"unsupported\s+python\s+version",
                r"requires.*python.*but.*have",
            ],
            ErrorCategory.CORRUPTED_PACKAGE: [
                r"hash\s+mismatch",
                r"checksum.*failed",
                r"corrupted.*package",
                r"invalid.*wheel",
                r"bad.*archive",
                r"integrity.*check.*failed",
            ],
            ErrorCategory.BACKUP_INVALID: [
                r"backup.*validation.*failed",
                r"requirements.*file.*not.*found",
                r"invalid.*backup",
                r"backup.*corrupted",
            ],
            ErrorCategory.SYSTEM_ERROR: [
                r"oserror",
                r"system.*error",
                r"errno\s+\d+",
                r"no\s+such\s+file\s+or\s+directory",
                r"command.*not.*found",
            ],
        }
        
        self._recovery_suggestions = {
            ErrorCategory.NETWORK_ERROR: [
                "Check your internet connection",
                "Retry the operation after a few minutes",
                "Use a different package index or mirror",
                "Check firewall and proxy settings",
            ],
            ErrorCategory.PERMISSION_ERROR: [
                "Run the command with elevated privileges (sudo)",
                "Check file and directory permissions",
                "Use virtual environments to avoid system-wide installations",
                "Verify user has write access to target directories",
            ],
            ErrorCategory.PACKAGE_NOT_FOUND: [
                "Verify package names and versions are correct",
                "Check if the package exists in the package index",
                "Try using a different package index",
                "Check for typos in package specifications",
            ],
            ErrorCategory.DEPENDENCY_CONFLICT: [
                "Use dependency resolution tools to identify conflicts",
                "Update conflicting packages to compatible versions",
                "Consider using virtual environments",
                "Review and update requirements specifications",
            ],
            ErrorCategory.DISK_SPACE_ERROR: [
                "Free up disk space on the target device",
                "Clean up temporary files and caches",
                "Move installation to a different location with more space",
                "Check available disk space before operations",
            ],
            ErrorCategory.PYTHON_VERSION_INCOMPATIBLE: [
                "Upgrade Python to a compatible version",
                "Use a different Python environment",
                "Find alternative packages compatible with your Python version",
                "Consider using version-specific package variants",
            ],
            ErrorCategory.CORRUPTED_PACKAGE: [
                "Clear package cache and retry",
                "Download the package from a different source",
                "Verify package integrity manually",
                "Report the issue to package maintainers",
            ],
            ErrorCategory.BACKUP_INVALID: [
                "Recreate the backup with proper validation",
                "Check backup file integrity",
                "Verify backup contains all required files",
                "Use a different backup if available",
            ],
            ErrorCategory.SYSTEM_ERROR: [
                "Check system logs for more details",
                "Verify system dependencies are installed",
                "Restart the system if necessary",
                "Check for system-level issues",
            ],
            ErrorCategory.UNKNOWN: [
                "Review the full error message for clues",
                "Check system and application logs",
                "Try the operation again",
                "Seek help from community or documentation",
            ],
        }
    
    def analyze(self, result: RestoreResult) -> ErrorAnalysis:
        """
        Analyze a restoration result and categorize any errors.
        
        Args:
            result: RestoreResult instance to analyze
            
        Returns:
            ErrorAnalysis with categorized error information
        """
        if result.success:
            return ErrorAnalysis(
                category=ErrorCategory.UNKNOWN,
                confidence=1.0,
                description="Operation completed successfully",
                error_message="Operation was successful",
                suggested_actions=["No action needed - operation succeeded"],
                is_recoverable=True,
            )
        
        error_message = result.error_message or ""
        category, confidence = self._categorize_error(error_message)
        
        description = self._generate_description(category, error_message)
        suggested_actions = self._recovery_suggestions.get(category, [])
        affected_packages = result.packages_failed or []
        is_recoverable = self._determine_recoverability(category)
        
        technical_details = {
            "strategy": result.strategy_used,
            "duration": result.duration,
            "packages_failed_count": len(affected_packages),
        }
        
        return ErrorAnalysis(
            category=category,
            confidence=confidence,
            description=description,
            error_message=error_message,
            suggested_actions=suggested_actions,
            affected_packages=affected_packages,
            technical_details=technical_details,
            is_recoverable=is_recoverable,
        )
    
    def _categorize_error(self, error_message: str) -> tuple[ErrorCategory, float]:
        """
        Categorize an error message and return confidence level.
        
        Args:
            error_message: Error message to categorize
            
        Returns:
            Tuple of (ErrorCategory, confidence_level)
        """
        if not error_message:
            return ErrorCategory.UNKNOWN, 0.5
        
        error_lower = error_message.lower()
        
        # Define confidence levels for each category
        confidence_levels = {
            ErrorCategory.NETWORK_ERROR: 0.9,
            ErrorCategory.PERMISSION_ERROR: 0.95,
            ErrorCategory.PACKAGE_NOT_FOUND: 0.85,
            ErrorCategory.DEPENDENCY_CONFLICT: 0.8,
            ErrorCategory.DISK_SPACE_ERROR: 0.95,
            ErrorCategory.PYTHON_VERSION_INCOMPATIBLE: 0.9,
            ErrorCategory.CORRUPTED_PACKAGE: 0.85,
            ErrorCategory.BACKUP_INVALID: 0.9,
            ErrorCategory.SYSTEM_ERROR: 0.6,
            ErrorCategory.UNKNOWN: 0.1,
        }
        
        for category, patterns in self._error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return category, confidence_levels[category]
        
        # If no patterns matched, return unknown with low confidence
        return ErrorCategory.UNKNOWN, confidence_levels[ErrorCategory.UNKNOWN]
    
    def get_recovery_suggestions(self, analysis: ErrorAnalysis) -> List[str]:
        """
        Get enhanced recovery suggestions for an error analysis.
        
        Args:
            analysis: ErrorAnalysis object to get suggestions for
            
        Returns:
            List of enhanced recovery suggestions
        """
        # Start with base suggestions from the analysis
        suggestions = list(analysis.suggested_actions)
        
        # Add category-specific enhanced suggestions
        enhanced_suggestions = {
            ErrorCategory.NETWORK_ERROR: [
                "Check your internet connection and network settings",
                "Try using a different package index or mirror",
                "Use cached packages if available (pip --cache-dir)",
            ],
            ErrorCategory.PERMISSION_ERROR: [
                "Ensure you have appropriate permissions for the target directory",
                "Consider using sudo for system-wide installations",
                "Verify write access to the installation directory",
            ],
            ErrorCategory.PACKAGE_NOT_FOUND: [
                "Verify package names and versions are correct",
                "Check if the package exists on PyPI",
                "Consider alternative package versions or names",
            ],
            ErrorCategory.DEPENDENCY_CONFLICT: [
                "Review and resolve conflicting dependencies",
                "Use pip-tools to manage dependency resolution",
                "Try installing packages individually to isolate conflicts",
            ],
            ErrorCategory.DISK_SPACE_ERROR: [
                "Free up disk space on the target device",
                "Use 'pip cache purge' to clear pip cache",
                "Consider using a different temporary directory",
            ],
            ErrorCategory.PYTHON_VERSION_INCOMPATIBLE: [
                "Upgrade Python to a compatible version",
                "Use a virtual environment with the correct Python version",
                "Find alternative packages compatible with your Python version",
            ],
            ErrorCategory.CORRUPTED_PACKAGE: [
                "Clear pip cache and retry installation",
                "Download packages from a different source",
                "Verify package integrity manually",
            ],
            ErrorCategory.BACKUP_INVALID: [
                "Recreate the backup with proper validation",
                "Check backup file integrity and completeness",
                "Use a different backup if available",
            ],
            ErrorCategory.SYSTEM_ERROR: [
                "Check system logs for more details",
                "Verify system dependencies are installed",
                "Consider restarting the system if necessary",
            ],
        }
        
        # Add enhanced suggestions for this category
        category_suggestions = enhanced_suggestions.get(analysis.category, [])
        suggestions.extend(category_suggestions)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    def _generate_description(self, category: ErrorCategory, error_message: str) -> str:
        """
        Generate a human-readable description for the error category.
        
        Args:
            category: Error category
            error_message: Original error message
            
        Returns:
            Human-readable description
        """
        descriptions = {
            ErrorCategory.NETWORK_ERROR: "Network connectivity issues prevented the operation from completing",
            ErrorCategory.PERMISSION_ERROR: "Insufficient permissions to perform the requested operation",
            ErrorCategory.PACKAGE_NOT_FOUND: "One or more packages could not be found in the package index",
            ErrorCategory.DEPENDENCY_CONFLICT: "Dependency conflicts prevent package installation",
            ErrorCategory.DISK_SPACE_ERROR: "Insufficient disk space to complete the operation",
            ErrorCategory.PYTHON_VERSION_INCOMPATIBLE: "Python version incompatibility with required packages",
            ErrorCategory.CORRUPTED_PACKAGE: "Package corruption detected during download or installation",
            ErrorCategory.BACKUP_INVALID: "Backup validation failed - backup may be corrupted or incomplete",
            ErrorCategory.SYSTEM_ERROR: "System-level error occurred during the operation",
            ErrorCategory.UNKNOWN: "An unrecognized error occurred",
        }
        
        return descriptions.get(category, "An error occurred during the operation")
    
    def _determine_recoverability(self, category: ErrorCategory) -> bool:
        """
        Determine if an error category is generally recoverable.
        
        Args:
            category: Error category to evaluate
            
        Returns:
            True if the error is generally recoverable
        """
        # Python version incompatibility may require environment changes
        if category == ErrorCategory.PYTHON_VERSION_INCOMPATIBLE:
            return False
        
        # Most other errors are recoverable with appropriate actions
        return True
    
    def analyze_error(self, result: RestoreResult) -> ErrorAnalysis:
        """
        Analyze a restoration result and categorize any errors.
        This is an alias for the analyze method to maintain compatibility.
        
        Args:
            result: RestoreResult instance to analyze
            
        Returns:
            ErrorAnalysis with categorized error information
        """
        return self.analyze(result)
    
    def analyze_multiple_failures(self, results: List[RestoreResult]) -> Dict[ErrorCategory, List[ErrorAnalysis]]:
        """
        Analyze multiple restoration failures and categorize them.
        
        Args:
            results: List of RestoreResult instances to analyze
            
        Returns:
            Dictionary mapping error categories to lists of error analyses
        """
        categorized = {}
        
        for result in results:
            if not result.success:
                analysis = self.analyze(result)
                category = analysis.category
                
                if category not in categorized:
                    categorized[category] = []
                
                categorized[category].append(analysis)
        
        return categorized