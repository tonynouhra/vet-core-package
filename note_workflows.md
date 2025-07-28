# GitHub Workflows Documentation

This document describes the GitHub Actions workflows used in this project for continuous integration, quality assurance, security monitoring, and release management.

## Table of Contents

1. [ci.yml – Continuous Integration](#1-ciyml--continuous-integration)
2. [code-quality.yml – Code Quality Checks](#2-code-qualityyml--code-quality-checks)
3. [docs.yml – Documentation Build and Deployment](#3-docsyml--documentation-build-and-deployment)
4. [maintenance.yml – Monthly Maintenance](#4-maintenanceyml--monthly-maintenance)
5. [pre-release.yml – Pre-Release Testing Pipeline](#5-pre-releaseyml--pre-release-testing-pipeline)
6. [release.yml – Final Release Workflow](#6-releaseyml--final-release-workflow)
7. [security-monitoring.yml – Daily Security Monitoring](#7-security-monitoringyml--daily-security-monitoring)
8. [upgrade-validation.yml – Dependency Upgrade Validation](#8-upgrade-validationyml--dependency-upgrade-validation)
9. [version-bump.yml – Bump Package Version](#9-version-bumpyml--bump-package-version)

---

## 1. ci.yml – Continuous Integration

**Triggers:** Pushes or pull requests to `main` and `develop` branches

### Key Jobs

#### Test
- **Environment:** Ubuntu with PostgreSQL service
- **Actions:**
  - Installs dependencies
  - Sets up test database
  - Performs linting (black, isort)
  - Type checks with mypy
  - Runs unit tests with coverage reporting

#### Security
- Installs Bandit and Safety
- Performs security scans
- Uploads security reports

#### Build
- Builds the package using build and twine
- Uploads distribution artifacts

#### Integration Tests
- Downloads build artifacts
- Installs the wheel
- Verifies basic imports against multiple Python and PostgreSQL versions

---

## 2. code-quality.yml – Code Quality Checks

**Triggers:** Pushes, pull requests, and weekly cron schedule

### Main Jobs

#### lint
- Performs formatting and type checks using black, isort, and mypy

#### security
- Runs Bandit, Safety (or pip-audit), and Semgrep
- Uploads artifacts for review

#### dependency-check
- Generates vulnerability and dependency reports via pip-audit and pipdeptree

#### documentation
- Checks docstring style and documentation formatting
- Builds docs with link checking

#### performance
- **Trigger:** On pushes to main
- Runs benchmarks and uploads results

#### compatibility
- Verifies basic imports and unit tests across OS and Python versions

#### code-coverage
- Runs tests with coverage
- Enforces an 80% threshold
- Uploads results to Codecov

---

## 3. docs.yml – Documentation Build and Deployment

**Triggers:** Documentation or source changes, PRs to main, and manual dispatch

### Workflow Steps

#### debug-deploy-condition
- Prints context info for troubleshooting the deploy condition

#### build-docs
- Installs the `[docs]` extras
- Builds the Sphinx documentation
- Runs link checks
- Uploads the artifacts

#### deploy-docs
- **Condition:** If branch is `main`
- Uploads the built docs to GitHub Pages

#### validate-examples
- Parses Python code blocks in the README and example scripts
- Ensures they compile and run correctly with a test PostgreSQL database

#### check-api-docs
- Runs interrogate to check docstring coverage
- Uploads a coverage badge and report

---

## 4. maintenance.yml – Monthly Maintenance

**Triggers:** First of each month at 03:00 UTC or manual dispatch

### Important Jobs

#### cleanup-artifacts
- Deletes workflow artifacts older than 30 days via GitHub API

#### security-audit
- Performs monthly security scans using Bandit, Safety (or pip-audit), and pip-audit
- Uploads reports
- Opens a GitHub issue if vulnerabilities are found

#### dependency-audit
- Checks outdated dependencies

#### performance-baseline
- Gathers performance benchmarks

#### code-quality-metrics
- Generates complexity/maintainability reports using radon and xenon

#### create-maintenance-summary
- Creates a GitHub issue summarizing results of all jobs with action items

#### notify-completion
- Prints a completion message after the summary is generated

---

## 5. pre-release.yml – Pre-Release Testing Pipeline

**Triggers:** Manual dispatch with version string and optional environments

### Highlights

#### validate-prerelease
- Checks version format
- Parses test environments

#### comprehensive-testing
- Runs unit, integration, and performance tests across multiple Python and PostgreSQL versions

#### build-prerelease
- Updates `pyproject.toml`
- Builds the wheel
- Uploads artifacts

#### test-installation
- Installs the wheel on multiple OS/Python combinations
- Verifies basic imports

#### environment-testing
- **Optional:** Installs the package in specified environments (dev/staging) for further checks

#### security-scan
- Performs Bandit, Safety/pip-audit, and Semgrep scans on the built wheel

#### publish-testpypi
- Uploads the prerelease package to TestPyPI
- Validates installation from TestPyPI

#### create-prerelease
- Creates a GitHub prerelease with installation instructions and testing status summary

#### notify-completion
- Prints links to the TestPyPI package and GitHub release

---

## 6. release.yml – Final Release Workflow

**Triggers:** Pushing a tag (`v*`) or manual version specification

### Main Stages

#### validate-release
- Checks version consistency with `pyproject.toml`
- Determines if it is a prerelease

#### test-release
- Runs the full test suite and security checks on Python 3.11 and 3.12 with PostgreSQL service

#### build-release
- Builds the package
- Uploads artifacts for later jobs

#### test-installation
- Installs the wheel from artifacts on multiple OS/Python combinations
- Verifies the package works before publishing

#### publish-testpypi and publish-pypi
- Publishes to TestPyPI or PyPI depending on whether it is a prerelease

#### create-github-release
- Generates a changelog section
- Creates the GitHub release
- Attaches the built artifacts

#### notify-success
- Prints instructions indicating whether it was a prerelease or full release
- Provides installation instructions

---

## 7. security-monitoring.yml – Daily Security Monitoring

**Triggers:** Daily at 06:00 UTC, manually, or when dependency files change

### Key Actions

#### vulnerability-scan
- Installs dependencies
- Runs pip-audit
- Processes results with custom scripts
- Summarizes severity counts
- **When vulnerabilities are found:**
  - Processes the report into JSON/markdown/CSV using `process_vulnerabilities.py`
  - Posts a summary to the job output
  - Uploads reports as artifacts
  - For critical findings: creates or updates a GitHub issue and optionally sends Slack notifications
  - Posts a PR comment summarizing results when run on pull requests

#### security-trend-analysis
- **Trigger:** On scheduled runs
- Downloads recent security reports
- Generates a basic trend analysis report using `generate_trend_analysis.py`

---

## 8. upgrade-validation.yml – Dependency Upgrade Validation

**Triggers:** Weekly scheduled runs or manual invocation with package and target version

### Flow

#### prepare
- Parses Python version inputs
- Optionally runs a vulnerability scan with pip-audit
- Uploads results

#### baseline-performance
- Establishes a performance baseline using pytest-benchmark with PostgreSQL service

#### upgrade-validation
- **For each Python version:**
  - Installs dependencies
  - Runs `upgrade_testing_pipeline.py` either for vulnerable packages or a specified package
  - Uploads results

#### security-verification
- Reruns pip-audit after upgrades
- Compares results with the original vulnerabilities to ensure they are resolved

#### performance-analysis
- Aggregates performance results
- Checks for significant regressions

#### generate-report
- Combines all artifacts into a comprehensive JSON/markdown report
- Posts a PR comment when applicable

---

## 9. version-bump.yml – Bump Package Version

**Triggers:** Manual dispatch to update project version and push a tag

### Steps

1. **Choose bump type:** patch, minor, major, or prerelease (with optional prerelease label)
2. **Version calculation:** A Python script calculates the new version, updates `pyproject.toml` and `__init__.py`, and outputs the old and new versions
3. **Update and commit:** The changelog is updated, changes are committed, and a new tag is pushed to trigger the release workflow automatically

---

## Summary

This comprehensive CI/CD pipeline ensures code quality, security, and reliable releases through:

- **Automated testing** across multiple Python and PostgreSQL versions
- **Security monitoring** with daily scans and vulnerability tracking
- **Code quality enforcement** with linting, type checking, and coverage requirements
- **Documentation** building and deployment
- **Release management** with pre-release testing and automated publishing
- **Maintenance tasks** including artifact cleanup and dependency auditing

Each workflow is designed to work together to maintain a high-quality, secure, and well-documented Python package.