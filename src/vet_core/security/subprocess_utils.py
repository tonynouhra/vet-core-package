"""
Secure subprocess utilities for the vet_core security module.

This module provides utilities for safely executing subprocess calls
with proper input validation and security measures.
"""

import logging
import re
import shutil
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

# Security logger
security_logger = logging.getLogger("vet_core.security.subprocess")


class SubprocessSecurityError(Exception):
    """Base class for subprocess security errors."""


class CommandValidationError(SubprocessSecurityError):
    """Raised when command validation fails."""


class ExecutableNotFoundError(SubprocessSecurityError):
    """Raised when required executable is not found."""


class SecurityViolationError(SubprocessSecurityError):
    """Raised when a security violation is detected."""


@dataclass
class SubprocessSecurityEvent:
    """Security event data for subprocess operations."""

    timestamp: datetime
    operation_name: str
    command: List[str]  # Sanitized for logging
    success: bool
    duration: float
    error_message: Optional[str] = None
    security_validation_passed: bool = True


@dataclass
class CommandValidationResult:
    """Result of command validation."""

    is_valid: bool
    validated_command: List[str]
    validation_errors: List[str]
    security_warnings: List[str]


def validate_command_list(cmd: List[str]) -> List[str]:
    """
    Validate a command list for security.

    Args:
        cmd: Command list to validate

    Returns:
        Validated command list

    Raises:
        CommandValidationError: If command list is invalid
    """
    if not cmd or not isinstance(cmd, list):
        raise CommandValidationError("Command must be a non-empty list")

    if not all(isinstance(arg, str) for arg in cmd):
        raise CommandValidationError("All command arguments must be strings")

    # Check for dangerous characters in command arguments
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">"]
    for i, arg in enumerate(cmd):
        if any(char in arg for char in dangerous_chars):
            raise CommandValidationError(
                f"Command argument {i} '{arg}' contains potentially dangerous characters"
            )

    return cmd


def validate_timeout(timeout: Union[int, float, None]) -> Optional[float]:
    """
    Validate a timeout value for security.

    Args:
        timeout: Timeout value to validate

    Returns:
        Validated timeout value

    Raises:
        CommandValidationError: If timeout is invalid
    """
    if timeout is None:
        return None

    if not isinstance(timeout, (int, float)):
        raise CommandValidationError("Timeout must be a number or None")

    if timeout <= 0:
        raise CommandValidationError("Timeout must be positive")

    if timeout > 3600:  # 1 hour max
        raise CommandValidationError("Timeout cannot exceed 3600 seconds")

    return float(timeout)


def validate_working_directory(cwd: Union[str, Path, None]) -> Optional[Path]:
    """
    Validate a working directory for security.

    Args:
        cwd: Working directory path to validate

    Returns:
        Validated working directory path

    Raises:
        CommandValidationError: If working directory is invalid
    """
    if cwd is None:
        return None

    if isinstance(cwd, str):
        cwd = Path(cwd)

    if not isinstance(cwd, Path):
        raise CommandValidationError(
            "Working directory must be a Path object or string"
        )

    # Convert to absolute path for security
    cwd = cwd.resolve()

    # Check if directory exists
    if not cwd.exists():
        raise CommandValidationError(f"Working directory '{cwd}' does not exist")

    if not cwd.is_dir():
        raise CommandValidationError(f"Working directory '{cwd}' is not a directory")

    # Prevent access to sensitive system directories
    sensitive_dirs = ["/etc", "/sys", "/proc", "/dev"]
    for sensitive_dir in sensitive_dirs:
        if str(cwd).startswith(sensitive_dir):
            raise CommandValidationError(
                f"Access to sensitive directory '{cwd}' is not allowed"
            )

    return cwd


def sanitize_command_for_logging(cmd: List[str]) -> List[str]:
    """
    Sanitize command arguments for safe logging.

    Args:
        cmd: Command list to sanitize

    Returns:
        Sanitized command list safe for logging
    """
    sanitized = []
    for arg in cmd:
        # Replace potential secrets or sensitive data
        if any(
            keyword in arg.lower() for keyword in ["password", "token", "key", "secret"]
        ):
            sanitized.append("[REDACTED]")
        elif len(arg) > 100:  # Truncate very long arguments
            sanitized.append(arg[:97] + "...")
        else:
            sanitized.append(arg)
    return sanitized


def log_subprocess_execution(
    cmd: List[str],
    operation_name: str,
    result: subprocess.CompletedProcess,
    duration: float,
    error_message: Optional[str] = None,
    security_validation_passed: bool = True,
) -> None:
    """
    Log subprocess execution for security auditing.

    Args:
        cmd: Command that was executed
        operation_name: Name of the operation
        result: Subprocess result
        duration: Execution duration in seconds
        error_message: Error message if any
        security_validation_passed: Whether security validation passed
    """
    event = SubprocessSecurityEvent(
        timestamp=datetime.now(),
        operation_name=operation_name,
        command=sanitize_command_for_logging(cmd),
        success=result.returncode == 0,
        duration=duration,
        error_message=error_message,
        security_validation_passed=security_validation_passed,
    )

    log_level = logging.INFO if event.success else logging.WARNING
    if not security_validation_passed:
        log_level = logging.ERROR

    security_logger.log(
        log_level,
        "Subprocess execution: %s - Success: %s, Duration: %.3fs, "
        "Command: %s, Security validation: %s",
        operation_name,
        event.success,
        duration,
        event.command,
        security_validation_passed,
    )

    if error_message:
        security_logger.error(
            "Subprocess error in %s: %s", operation_name, error_message
        )


def validate_package_name(package_name: str) -> str:
    """
    Validate a Python package name for security.

    Args:
        package_name: Package name to validate

    Returns:
        Validated package name

    Raises:
        SubprocessSecurityError: If package name is invalid
    """
    if not package_name or not isinstance(package_name, str):
        raise CommandValidationError("Package name must be a non-empty string")

    # Allow only alphanumeric characters, hyphens, underscores, and dots
    if not re.match(r"^[a-zA-Z0-9._-]+$", package_name):
        raise CommandValidationError(
            f"Invalid package name '{package_name}'. Only alphanumeric characters, "
            "hyphens, underscores, and dots are allowed."
        )

    # Prevent path traversal attempts
    if ".." in package_name or package_name.startswith("/"):
        raise CommandValidationError(
            f"Package name '{package_name}' contains invalid path characters"
        )

    return package_name


def validate_version(version: str) -> str:
    """
    Validate a version string for security.

    Args:
        version: Version string to validate

    Returns:
        Validated version string

    Raises:
        SubprocessSecurityError: If version is invalid
    """
    if not version or not isinstance(version, str):
        raise CommandValidationError("Version must be a non-empty string")

    # Allow version patterns like 1.2.3, 1.2.3a1, 1.2.3.dev0, etc.
    if not re.match(r"^[a-zA-Z0-9._+-]+$", version):
        raise CommandValidationError(
            f"Invalid version '{version}'. Only alphanumeric characters, "
            "dots, hyphens, underscores, and plus signs are allowed."
        )

    # Prevent command injection attempts
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'"]
    if any(char in version for char in dangerous_chars):
        raise CommandValidationError(
            f"Version '{version}' contains potentially dangerous characters"
        )

    return version


def validate_module_name(module_name: str) -> str:
    """
    Validate a Python module name for security.

    Args:
        module_name: Module name to validate

    Returns:
        Validated module name

    Raises:
        SubprocessSecurityError: If module name is invalid
    """
    if not module_name or not isinstance(module_name, str):
        raise CommandValidationError("Module name must be a non-empty string")

    # Allow only valid Python module name characters
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", module_name):
        raise CommandValidationError(
            f"Invalid module name '{module_name}'. Must be a valid Python identifier."
        )

    # Prevent dangerous imports
    dangerous_modules = ["os", "subprocess", "sys", "__import__", "eval", "exec"]
    if module_name in dangerous_modules:
        raise SecurityViolationError(
            f"Module '{module_name}' is not allowed for security reasons"
        )

    return module_name


def validate_test_command(test_command: str) -> str:
    """
    Validate a test command for security.

    Args:
        test_command: Test command to validate

    Returns:
        Validated test command

    Raises:
        SubprocessSecurityError: If test command is invalid
    """
    if not test_command or not isinstance(test_command, str):
        raise CommandValidationError("Test command must be a non-empty string")

    # Allow only known safe test commands
    allowed_commands = ["pytest", "unittest", "nose2", "tox"]
    if test_command not in allowed_commands:
        raise SecurityViolationError(
            f"Test command '{test_command}' is not in the allowed list: "
            f"{allowed_commands}"
        )

    return test_command


def validate_pip_command(pip_args: List[str]) -> List[str]:
    """
    Validate pip command arguments for security.

    Args:
        pip_args: List of pip command arguments

    Returns:
        Validated pip command arguments

    Raises:
        SubprocessSecurityError: If pip command is invalid
    """
    if not pip_args or not isinstance(pip_args, list):
        raise CommandValidationError("Pip arguments must be a non-empty list")

    # Validate each argument
    validated_args = []
    for arg in pip_args:
        if not isinstance(arg, str):
            raise CommandValidationError("All pip arguments must be strings")

        # Check for dangerous characters
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">"]
        if any(char in arg for char in dangerous_chars):
            raise CommandValidationError(
                f"Pip argument '{arg}' contains potentially dangerous characters"
            )

        validated_args.append(arg)

    # Validate first argument is a known pip subcommand
    if validated_args:
        allowed_subcommands = [
            "install",
            "uninstall",
            "freeze",
            "list",
            "show",
            "check",
            "search",
            "wheel",
            "hash",
            "completion",
            "debug",
            "help",
        ]
        if validated_args[0] not in allowed_subcommands:
            raise SecurityViolationError(
                f"Pip subcommand '{validated_args[0]}' is not in the allowed list: "
                f"{allowed_subcommands}"
            )

    return validated_args


def validate_startup_command(startup_cmd: List[str]) -> List[str]:
    """
    Validate a startup command for security.

    Args:
        startup_cmd: Startup command to validate

    Returns:
        Validated startup command

    Raises:
        SubprocessSecurityError: If startup command is invalid
    """
    if not startup_cmd or not isinstance(startup_cmd, list):
        raise CommandValidationError("Startup command must be a non-empty list")

    # Use general command validation
    validated_cmd = validate_command_list(startup_cmd)

    # Additional validation for startup commands
    if validated_cmd[0] not in [sys.executable, "python", "python3"]:
        # For non-Python commands, ensure they're in allowed list
        allowed_executables = ["node", "npm", "yarn", "java", "mvn", "gradle"]
        executable_name = Path(validated_cmd[0]).name
        if executable_name not in allowed_executables:
            raise SecurityViolationError(
                f"Startup executable '{executable_name}' is not in the allowed list: "
                f"{allowed_executables}"
            )

    return validated_cmd


def validate_scan_output(output: str) -> str:
    """
    Validate and sanitize scan output for security.

    Args:
        output: Raw scan output to validate

    Returns:
        Validated and sanitized output

    Raises:
        SubprocessSecurityError: If output contains dangerous content
    """
    if not isinstance(output, str):
        raise CommandValidationError("Scan output must be a string")

    # Check for potential code injection in output
    dangerous_patterns = [
        r"<script[^>]*>",
        r"javascript:",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            raise SecurityViolationError(
                f"Scan output contains potentially dangerous content matching: {pattern}"
            )

    # Truncate very long output to prevent memory issues
    max_output_length = 1024 * 1024  # 1MB
    if len(output) > max_output_length:
        output = output[:max_output_length] + "\n[OUTPUT TRUNCATED]"

    return output


def validate_command_structure(
    cmd: List[str], operation_type: str = "general"
) -> CommandValidationResult:
    """
    Comprehensively validate a command structure for security.

    Args:
        cmd: Command list to validate
        operation_type: Type of operation (pip, test, scan, startup, general)

    Returns:
        CommandValidationResult with validation details

    Raises:
        SubprocessSecurityError: If command validation fails critically
    """
    validation_errors = []
    security_warnings = []
    validated_command = []

    try:
        # Basic command list validation
        validated_command = validate_command_list(cmd)

        # Operation-specific validation
        if operation_type == "pip" and len(validated_command) > 1:
            try:
                validate_pip_command(validated_command[1:])
            except SubprocessSecurityError as e:
                validation_errors.append(str(e))

        elif operation_type == "test" and validated_command:
            try:
                validate_test_command(validated_command[0])
            except SubprocessSecurityError as e:
                validation_errors.append(str(e))

        elif operation_type == "startup":
            try:
                validate_startup_command(validated_command)
            except SubprocessSecurityError as e:
                validation_errors.append(str(e))

        # Check for potential security warnings
        for i, arg in enumerate(validated_command):
            # Warn about relative paths
            if "/" in arg and not arg.startswith("/"):
                security_warnings.append(f"Argument {i} '{arg}' contains relative path")

            # Warn about very long arguments
            if len(arg) > 200:
                security_warnings.append(
                    f"Argument {i} is very long ({len(arg)} characters)"
                )

    except SubprocessSecurityError as e:
        validation_errors.append(str(e))

    is_valid = len(validation_errors) == 0

    return CommandValidationResult(
        is_valid=is_valid,
        validated_command=validated_command if is_valid else cmd,
        validation_errors=validation_errors,
        security_warnings=security_warnings,
    )


def get_executable_path(executable: str) -> str:
    """
    Get the full path to an executable, addressing B607 bandit warning.

    Args:
        executable: Name of the executable

    Returns:
        Full path to the executable

    Raises:
        SubprocessSecurityError: If executable is not found
    """
    full_path = shutil.which(executable)
    if not full_path:
        raise ExecutableNotFoundError(f"Executable '{executable}' not found in PATH")

    return full_path


def create_secure_environment() -> dict:
    """
    Create a secure environment dictionary for subprocess execution.

    Returns:
        Secure environment dictionary

    Raises:
        SubprocessSecurityError: If environment creation fails
    """
    import os

    # Start with a minimal environment
    secure_env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
        "LANG": os.environ.get("LANG", "C"),
        "LC_ALL": os.environ.get("LC_ALL", "C"),
    }

    # Add Python-specific environment variables if they exist
    python_env_vars = ["PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV"]

    for var in python_env_vars:
        if var in os.environ:
            secure_env[var] = os.environ[var]

    # Remove potentially dangerous environment variables
    dangerous_vars = [
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "DYLD_INSERT_LIBRARIES",
        "DYLD_LIBRARY_PATH",
        "PYTHONSTARTUP",
    ]

    for var in dangerous_vars:
        secure_env.pop(var, None)

    return secure_env


def secure_subprocess_run(
    cmd: List[str],
    validate_first_arg: bool = True,
    use_secure_env: bool = True,
    operation_type: str = "general",
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    Securely run a subprocess command with validation.

    Args:
        cmd: Command list to execute
        validate_first_arg: Whether to validate the first argument as an executable
        use_secure_env: Whether to use a secure environment
        operation_type: Type of operation for validation
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        CompletedProcess result

    Raises:
        CommandValidationError: If command validation fails
        SecurityViolationError: If security violation is detected
    """
    # Comprehensive command validation
    validation_result = validate_command_structure(cmd, operation_type)
    if not validation_result.is_valid:
        raise CommandValidationError(
            f"Command validation failed: {'; '.join(validation_result.validation_errors)}"
        )

    # Use validated command
    cmd = validation_result.validated_command

    # Log security warnings if any
    if validation_result.security_warnings:
        for warning in validation_result.security_warnings:
            security_logger.warning("Security warning: %s", warning)

    # Validate that we're not using shell=True (security risk)
    if kwargs.get("shell", False):
        raise SecurityViolationError("shell=True is not allowed for security reasons")

    # Validate timeout if provided
    if "timeout" in kwargs:
        kwargs["timeout"] = validate_timeout(kwargs["timeout"])

    # Validate working directory if provided
    if "cwd" in kwargs:
        kwargs["cwd"] = validate_working_directory(kwargs["cwd"])

    # Validate first argument if requested
    if validate_first_arg and cmd[0] != sys.executable:
        # For non-Python executables, ensure we have the full path
        try:
            cmd[0] = get_executable_path(cmd[0])
        except ExecutableNotFoundError:
            # If we can't find the executable, let subprocess handle the error
            pass

    # Set secure environment if requested
    if use_secure_env and "env" not in kwargs:
        kwargs["env"] = create_secure_environment()

    # Set secure defaults
    secure_kwargs = {
        "shell": False,  # Never use shell
        "capture_output": True,  # Capture output by default
        "text": True,  # Use text mode by default
        "check": False,  # Set check=False by default to handle errors manually
        **kwargs,  # Allow overrides (including check parameter)
    }

    # nosec B603
    return subprocess.run(cmd, **secure_kwargs)  # nosec


def secure_subprocess_run_with_logging(
    cmd: List[str],
    operation_name: str,
    validate_first_arg: bool = True,
    use_secure_env: bool = True,
    operation_type: str = "general",
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    Securely run a subprocess command with validation and logging.

    Args:
        cmd: Command list to execute
        operation_name: Name of the operation for logging
        validate_first_arg: Whether to validate the first argument as an executable
        use_secure_env: Whether to use a secure environment
        operation_type: Type of operation for validation
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        CompletedProcess result

    Raises:
        CommandValidationError: If command validation fails
        SecurityViolationError: If security violation is detected
    """
    start_time = time.time()
    error_message = None
    security_validation_passed = True
    result = None

    try:
        # Run the secure subprocess
        result = secure_subprocess_run(
            cmd,
            validate_first_arg=validate_first_arg,
            use_secure_env=use_secure_env,
            operation_type=operation_type,
            **kwargs,
        )

        # Check if command failed
        if result.returncode != 0:
            error_message = f"Command failed with return code {result.returncode}"
            if result.stderr:
                error_message += f": {result.stderr.strip()}"

        return result

    except (
        CommandValidationError,
        SecurityViolationError,
        ExecutableNotFoundError,
    ) as e:
        security_validation_passed = False
        error_message = str(e)
        # Create a failed result for logging
        result = subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr=str(e)
        )
        raise

    except subprocess.TimeoutExpired as e:
        error_message = f"Command timed out after {e.timeout} seconds"
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=124,  # Standard timeout exit code
            stdout="",
            stderr=error_message,
        )
        raise

    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        result = subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr=error_message
        )
        raise

    finally:
        duration = time.time() - start_time
        # Log the execution regardless of success/failure
        if result is not None:
            log_subprocess_execution(
                cmd=cmd,
                operation_name=operation_name,
                result=result,
                duration=duration,
                error_message=error_message,
                security_validation_passed=security_validation_passed,
            )


def secure_pip_command(
    pip_args: List[str],
    operation_name: str,
    timeout: Optional[float] = 300,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    Execute a pip command securely with validation and logging.

    Args:
        pip_args: Pip command arguments (without 'pip' itself)
        operation_name: Name of the operation for logging
        timeout: Command timeout in seconds
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        CompletedProcess result

    Raises:
        SubprocessSecurityError: If command validation fails
    """
    # Construct full pip command
    pip_cmd = [sys.executable, "-m", "pip"] + pip_args

    return secure_subprocess_run_with_logging(
        cmd=pip_cmd,
        operation_name=operation_name,
        validate_first_arg=False,  # sys.executable is already validated
        operation_type="pip",
        timeout=timeout,
        **kwargs,
    )


def secure_python_command(
    python_args: List[str],
    operation_name: str,
    timeout: Optional[float] = 60,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    Execute a Python command securely with validation and logging.

    Args:
        python_args: Python command arguments (without 'python' itself)
        operation_name: Name of the operation for logging
        timeout: Command timeout in seconds
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        CompletedProcess result

    Raises:
        SubprocessSecurityError: If command validation fails
    """
    # Construct full Python command
    python_cmd = [sys.executable] + python_args

    return secure_subprocess_run_with_logging(
        cmd=python_cmd,
        operation_name=operation_name,
        validate_first_arg=False,  # sys.executable is already validated
        operation_type="general",
        timeout=timeout,
        **kwargs,
    )


def secure_tool_command(
    tool_name: str,
    tool_args: List[str],
    operation_name: str,
    timeout: Optional[float] = 300,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    Execute a tool command securely with validation and logging.

    Args:
        tool_name: Name of the tool executable
        tool_args: Tool command arguments
        operation_name: Name of the operation for logging
        timeout: Command timeout in seconds
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        CompletedProcess result

    Raises:
        SubprocessSecurityError: If command validation fails
    """
    # Construct full tool command
    tool_cmd = [tool_name] + tool_args

    return secure_subprocess_run_with_logging(
        cmd=tool_cmd,
        operation_name=operation_name,
        validate_first_arg=True,
        operation_type="general",
        timeout=timeout,
        **kwargs,
    )
