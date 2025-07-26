# Workflow Documentation Update

## Overview

This document outlines updates to workflow documentation to reflect the upgrade to GitHub Actions artifact actions version 4.

## Documentation Updates Required

### 1. README.md Updates

**Section: CI/CD Pipeline**

Add information about artifact handling:

```markdown
## CI/CD Pipeline

Our CI/CD pipeline uses GitHub Actions with the following key features:

### Artifact Management
- **Artifact Actions Version:** v4 (upgraded from v3 in January 2025)
- **Retention Policy:** 30 days for most artifacts, 90 days for releases
- **Compression:** Enhanced compression algorithms for faster transfers
- **Security:** Improved artifact access controls and audit logging

### Workflow Artifacts
- **Security Reports:** Bandit, Safety, and Semgrep scan results
- **Build Artifacts:** Distribution packages (wheels, source distributions)
- **Test Reports:** Coverage reports and performance benchmarks
- **Documentation:** Built HTML documentation and API coverage reports
```

### 2. Contributing Guidelines

**Section: Development Workflow**

Update artifact-related development practices:

```markdown
## Working with Workflow Artifacts

### Downloading Artifacts for Local Testing

```bash
# Install GitHub CLI if not already installed
gh auth login

# Download artifacts from latest CI run
gh run download --name dist
gh run download --name security-reports

# Download artifacts from specific run
gh run download [RUN_ID] --name coverage-reports
```

### Artifact Naming Conventions

- Use descriptive names: `security-reports-{sha}`, `coverage-reports-{sha}`
- Include run identifiers for uniqueness: `monthly-audit-{run_number}`
- Follow kebab-case format: `api-docs-coverage`

### Artifact Best Practices

- Keep artifacts under 100MB when possible
- Use compression for large files
- Set appropriate retention periods
- Include metadata files for context
```

### 3. Deployment Documentation

**Section: Release Process**

Update release artifact handling:

```markdown
## Release Artifacts

### Artifact Flow
1. **Build Stage:** Creates `release-dist` artifact with wheels and source distributions
2. **TestPyPI Stage:** Downloads `release-dist` for pre-release testing
3. **PyPI Stage:** Downloads `release-dist` for production release
4. **GitHub Release:** Downloads `release-dist` for release assets

### Artifact Security
- All release artifacts are scanned for vulnerabilities
- Checksums are automatically generated and verified
- Artifacts are signed using GitHub's attestation system
- Access is restricted to authorized workflows only

### Troubleshooting Release Artifacts
- Check artifact availability in GitHub Actions UI
- Verify artifact names match between upload and download steps
- Ensure proper permissions for artifact access
- Review workflow logs for detailed error messages
```

## Internal Documentation Updates

### 1. Developer Onboarding

**Section: Understanding Our CI/CD**

```markdown
## Artifact System

Our workflows use GitHub Actions artifacts to pass data between jobs and store results:

### Key Concepts
- **Artifacts:** Files or directories stored by workflows
- **Retention:** How long artifacts are kept (configurable)
- **Scope:** Artifacts are scoped to workflow runs
- **Access:** Artifacts can be downloaded by subsequent jobs or manually

### Common Artifacts in Our System
- `dist`: Python package distributions
- `security-reports-{sha}`: Security scan results
- `coverage-reports-{sha}`: Test coverage data
- `documentation`: Built HTML docs
- `benchmark-results-{sha}`: Performance test results

### Working with Artifacts
```bash
# View artifacts for a workflow run
gh run view [RUN_ID] --log

# Download all artifacts from a run
gh run download [RUN_ID]

# Download specific artifact
gh run download [RUN_ID] --name dist
```
```

### 2. Troubleshooting Guide

**Section: Workflow Issues**

```markdown
## Artifact-Related Issues

### Common Problems and Solutions

**Problem:** "Artifact not found" error
```
Error: Unable to find any artifacts for the associated workflow
```
**Solution:**
1. Check if the upload step completed successfully
2. Verify artifact name matches exactly (case-sensitive)
3. Ensure the job that uploads the artifact completed before download
4. Check if artifact has expired (retention period)

**Problem:** "Permission denied" when downloading
```
Error: Resource not accessible by integration
```
**Solution:**
1. Verify workflow has proper permissions
2. Check if GITHUB_TOKEN has required scopes
3. Ensure artifact is from the same repository
4. Review workflow permissions configuration

**Problem:** Slow artifact uploads/downloads
**Solution:**
1. Check artifact size (consider compression)
2. Review network connectivity
3. Split large artifacts into smaller chunks
4. Use artifact retention policies to clean up old files

### Debugging Steps
1. Check workflow logs for detailed error messages
2. Verify artifact names and paths
3. Test with minimal artifact first
4. Review GitHub Actions status page for service issues
```

### 3. Monitoring and Alerting

**Section: Workflow Monitoring**

```markdown
## Artifact Monitoring

### Key Metrics
- **Upload Success Rate:** Percentage of successful artifact uploads
- **Download Success Rate:** Percentage of successful artifact downloads
- **Average Upload Time:** Time taken to upload artifacts
- **Average Download Time:** Time taken to download artifacts
- **Storage Usage:** Total artifact storage consumption
- **Retention Compliance:** Artifacts cleaned up according to policy

### Alerting Thresholds
- Upload/Download success rate < 95%
- Average upload/download time > 5 minutes
- Storage usage > 80% of limit
- Artifacts not cleaned up after retention period

### Monitoring Tools
- GitHub Actions workflow status
- Custom monitoring scripts in `/scripts/` directory
- Weekly artifact usage reports
- Monthly cleanup and optimization reviews
```

## API Documentation Updates

### 1. Package Documentation

**Section: Installation and Setup**

```markdown
## Development Setup

### Working with CI Artifacts

If you're contributing to the project, you may need to work with CI artifacts:

```python
# Example: Loading test data from CI artifacts
import json
from pathlib import Path

def load_benchmark_data(artifact_path: str) -> dict:
    """Load benchmark data from CI artifacts.
    
    Args:
        artifact_path: Path to downloaded benchmark artifact
        
    Returns:
        Dictionary containing benchmark results
    """
    with open(Path(artifact_path) / "benchmark-results.json") as f:
        return json.load(f)

# Usage
benchmark_data = load_benchmark_data("./artifacts/benchmark-results")
```

### Artifact Integration

The package includes utilities for working with CI artifacts:

```python
from vet_core.utils import ArtifactLoader

# Load security reports
loader = ArtifactLoader("security-reports")
reports = loader.load_security_data()

# Load performance data
perf_data = loader.load_benchmark_data()
```
```

## External Documentation Updates

### 1. GitHub Wiki Updates

**Page: CI/CD Pipeline Overview**

```markdown
# CI/CD Pipeline Overview

## Artifact Management

Our CI/CD pipeline uses GitHub Actions artifacts (v4) to manage build outputs, test results, and deployment assets.

### Artifact Types
- **Build Artifacts:** Python packages ready for distribution
- **Security Reports:** Vulnerability scans and security analysis
- **Test Results:** Coverage reports and performance benchmarks
- **Documentation:** Generated API docs and user guides

### Artifact Lifecycle
1. **Creation:** Generated during workflow execution
2. **Storage:** Stored in GitHub Actions artifact system
3. **Access:** Available for download by authorized users
4. **Retention:** Automatically cleaned up based on retention policy
5. **Cleanup:** Removed after expiration to manage storage costs

### Best Practices
- Use descriptive artifact names
- Include version or commit SHA in names
- Set appropriate retention periods
- Compress large artifacts
- Document artifact contents and usage
```

### 2. Team Documentation

**Section: Workflow Maintenance**

```markdown
## Workflow Maintenance Tasks

### Monthly Artifact Review
- [ ] Review artifact storage usage
- [ ] Check retention policy compliance
- [ ] Analyze artifact access patterns
- [ ] Update artifact naming conventions if needed
- [ ] Review and update documentation

### Quarterly Artifact Optimization
- [ ] Analyze artifact sizes and compression ratios
- [ ] Review artifact retention policies
- [ ] Update artifact cleanup procedures
- [ ] Assess artifact security and access controls
- [ ] Plan for artifact system improvements

### Annual Artifact Strategy Review
- [ ] Evaluate artifact management tools and practices
- [ ] Review GitHub Actions artifact limits and costs
- [ ] Plan for artifact system scaling
- [ ] Update team training on artifact best practices
- [ ] Document lessons learned and improvements
```

## Documentation Maintenance Schedule

### Weekly Tasks
- [ ] Review workflow documentation for accuracy
- [ ] Update any changed artifact names or procedures
- [ ] Check for broken links in documentation

### Monthly Tasks
- [ ] Comprehensive review of all workflow documentation
- [ ] Update performance metrics and benchmarks
- [ ] Review and update troubleshooting guides
- [ ] Validate all code examples and commands

### Quarterly Tasks
- [ ] Major documentation review and updates
- [ ] Update screenshots and UI references
- [ ] Review and update best practices
- [ ] Plan documentation improvements

## Documentation Quality Checklist

- [ ] All artifact names are accurate and up-to-date
- [ ] Code examples are tested and working
- [ ] Links to external resources are valid
- [ ] Screenshots and UI references are current
- [ ] Troubleshooting steps are comprehensive
- [ ] Best practices reflect current standards
- [ ] Documentation is accessible and well-organized

---

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Next Review:** April 2025