# GitHub Actions Artifact Upgrade Rollback Instructions

## Overview

This document provides step-by-step instructions for rolling back the GitHub Actions artifact upgrade from version 4 to version 3 if issues are encountered.

## When to Rollback

### Rollback Triggers

Execute rollback procedures if any of the following conditions occur:

🚨 **Critical Issues:**
- Workflow failure rate increases by >20%
- Artifacts become inaccessible or corrupted
- Cross-job dependencies break completely
- Security vulnerabilities introduced

⚠️ **Warning Signs:**
- Performance degrades significantly (>50% slower)
- Intermittent artifact upload/download failures
- New error patterns in workflow logs
- Artifact retention issues

## Pre-Rollback Checklist

Before initiating rollback, complete the following steps:

- [ ] **Document the Issue:** Record specific error messages, affected workflows, and impact
- [ ] **Notify Team:** Alert development team about the rollback decision
- [ ] **Backup Current State:** Ensure current workflow files are backed up
- [ ] **Check Dependencies:** Verify no other systems depend on v4-specific features
- [ ] **Prepare Monitoring:** Set up monitoring for post-rollback validation

## Rollback Procedures

### Method 1: Quick Rollback (Recommended)

This method reverts all workflows simultaneously for fastest recovery.

#### Step 1: Create Rollback Branch

```bash
# Create and switch to rollback branch
git checkout -b rollback/artifact-actions-v3
```

#### Step 2: Execute Bulk Replacement

```bash
# Navigate to workflow directory
cd .github/workflows/

# Replace all v4 references with v3
find . -name "*.yml" -exec sed -i 's/actions\/upload-artifact@v4/actions\/upload-artifact@v3/g' {} \;
find . -name "*.yml" -exec sed -i 's/actions\/download-artifact@v4/actions\/download-artifact@v3/g' {} \;

# Verify changes
grep -r "artifact@v" .
```

#### Step 3: Commit and Deploy

```bash
# Commit changes
git add .
git commit -m "Rollback: Revert artifact actions from v4 to v3

- Reverts all upload-artifact and download-artifact actions to v3
- Addresses critical issues with v4 implementation
- Restores previous stable configuration"

# Push to repository
git push origin rollback/artifact-actions-v3

# Create pull request for immediate merge
gh pr create --title "URGENT: Rollback Artifact Actions to v3" \
             --body "Critical rollback to resolve v4 issues" \
             --base main
```

### Method 2: Selective Rollback

Use this method to rollback specific workflows while keeping others on v4.

#### Workflow-Specific Rollback Commands

**CI Workflow Only:**
```bash
sed -i 's/actions\/upload-artifact@v4/actions\/upload-artifact@v3/g' .github/workflows/ci.yml
sed -i 's/actions\/download-artifact@v4/actions\/download-artifact@v3/g' .github/workflows/ci.yml
```

**Release Workflow Only:**
```bash
sed -i 's/actions\/upload-artifact@v4/actions\/upload-artifact@v3/g' .github/workflows/release.yml
sed -i 's/actions\/download-artifact@v4/actions\/download-artifact@v3/g' .github/workflows/release.yml
```

**Code Quality Workflow Only:**
```bash
sed -i 's/actions\/upload-artifact@v4/actions\/upload-artifact@v3/g' .github/workflows/code-quality.yml
sed -i 's/actions\/download-artifact@v4/actions\/download-artifact@v3/g' .github/workflows/code-quality.yml
```

**Documentation Workflow Only:**
```bash
sed -i 's/actions\/upload-artifact@v4/actions\/upload-artifact@v3/g' .github/workflows/docs.yml
sed -i 's/actions\/download-artifact@v4/actions\/download-artifact@v3/g' .github/workflows/docs.yml
```

**Pre-Release Workflow Only:**
```bash
sed -i 's/actions\/upload-artifact@v4/actions\/upload-artifact@v3/g' .github/workflows/pre-release.yml
sed -i 's/actions\/download-artifact@v4/actions\/download-artifact@v3/g' .github/workflows/pre-release.yml
```

**Maintenance Workflow Only:**
```bash
sed -i 's/actions\/upload-artifact@v4/actions\/upload-artifact@v3/g' .github/workflows/maintenance.yml
sed -i 's/actions\/download-artifact@v4/actions\/download-artifact@v3/g' .github/workflows/maintenance.yml
```

## Manual Rollback (Line-by-Line)

If automated rollback fails, use these manual instructions:

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Line ~95:** Change security reports upload
```yaml
# FROM:
- name: Upload security reports
  uses: actions/upload-artifact@v4

# TO:
- name: Upload security reports
  uses: actions/upload-artifact@v3
```

**Line ~125:** Change build artifacts upload
```yaml
# FROM:
- name: Upload build artifacts
  uses: actions/upload-artifact@v4

# TO:
- name: Upload build artifacts
  uses: actions/upload-artifact@v3
```

**Line ~155:** Change build artifacts download
```yaml
# FROM:
- name: Download build artifacts
  uses: actions/download-artifact@v4

# TO:
- name: Download build artifacts
  uses: actions/download-artifact@v3
```

### 2. Release Workflow (`.github/workflows/release.yml`)

**Line ~125:** Change release-dist upload
```yaml
# FROM:
- name: Upload build artifacts
  uses: actions/upload-artifact@v4

# TO:
- name: Upload build artifacts
  uses: actions/upload-artifact@v3
```

**Lines ~145, ~175, ~205:** Change all download-artifact references
```yaml
# FROM:
- name: Download build artifacts
  uses: actions/download-artifact@v4

# TO:
- name: Download build artifacts
  uses: actions/download-artifact@v3
```

### 3. Code Quality Workflow (`.github/workflows/code-quality.yml`)

**Lines ~65, ~105, ~155, ~185:** Change all upload-artifact references
```yaml
# FROM:
uses: actions/upload-artifact@v4

# TO:
uses: actions/upload-artifact@v3
```

### 4. Documentation Workflow (`.github/workflows/docs.yml`)

**Lines ~35, ~95:** Change upload-artifact references
```yaml
# FROM:
uses: actions/upload-artifact@v4

# TO:
uses: actions/upload-artifact@v3
```

**Line ~55:** Change download-artifact reference
```yaml
# FROM:
uses: actions/download-artifact@v4

# TO:
uses: actions/download-artifact@v3
```

### 5. Pre-Release Workflow (`.github/workflows/pre-release.yml`)

**Upload Actions (Lines ~85, ~115, ~225):**
```yaml
# FROM:
uses: actions/upload-artifact@v4

# TO:
uses: actions/upload-artifact@v3
```

**Download Actions (Lines ~135, ~175, ~255, ~285):**
```yaml
# FROM:
uses: actions/download-artifact@v4

# TO:
uses: actions/download-artifact@v3
```

### 6. Maintenance Workflow (`.github/workflows/maintenance.yml`)

**Lines ~65, ~105, ~135, ~165:** Change all upload-artifact references
```yaml
# FROM:
uses: actions/upload-artifact@v4

# TO:
uses: actions/upload-artifact@v3
```

## Post-Rollback Validation

### Immediate Validation (0-2 hours)

1. **Trigger Test Workflows:**
```bash
# Trigger CI workflow
gh workflow run ci.yml

# Trigger code quality workflow
gh workflow run code-quality.yml

# Monitor workflow status
gh run list --limit 10
```

2. **Check Artifact Operations:**
   - Verify artifacts are being uploaded successfully
   - Confirm downloads work in dependent jobs
   - Check artifact accessibility in GitHub UI

3. **Monitor Error Logs:**
   - Review workflow logs for any new errors
   - Check for artifact-related failures
   - Verify cross-job dependencies work

### Extended Validation (2-24 hours)

1. **Full Workflow Testing:**
   - Test release workflow with a test tag
   - Run pre-release workflow
   - Execute maintenance workflow

2. **Performance Monitoring:**
   - Compare upload/download times to baseline
   - Monitor workflow execution duration
   - Check resource usage patterns

3. **Integration Testing:**
   - Verify CI/CD pipeline end-to-end
   - Test artifact passing between workflows
   - Confirm external integrations work

## Rollback Verification Checklist

- [ ] All workflow files reverted to v3
- [ ] No remaining v4 references in codebase
- [ ] Test workflows execute successfully
- [ ] Artifacts upload and download correctly
- [ ] Cross-job dependencies function properly
- [ ] No new errors in workflow logs
- [ ] Performance returns to baseline levels
- [ ] Team notified of successful rollback

## Re-attempt Strategy

After successful rollback and issue resolution:

### 1. Root Cause Analysis
- Identify specific cause of v4 issues
- Document lessons learned
- Update upgrade procedures

### 2. Preparation for Re-upgrade
- Address identified issues
- Enhance testing procedures
- Prepare more comprehensive validation

### 3. Phased Re-deployment
- Start with single workflow
- Gradually expand to all workflows
- Monitor each phase carefully

## Emergency Contacts

### Immediate Response Team
- **Primary:** Development Team Lead
- **Secondary:** DevOps Engineer
- **Escalation:** Engineering Manager

### Communication Channels
- **Slack:** #dev-alerts
- **Email:** dev-team@company.com
- **Incident Management:** [Incident Response System]

## Rollback History Log

| Date | Trigger | Workflows Affected | Duration | Resolution |
|------|---------|-------------------|----------|------------|
| [Date] | [Issue] | [Workflows] | [Time] | [Outcome] |

---

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Emergency Hotline:** [Contact Information]

## Quick Reference Commands

```bash
# Quick rollback all workflows
find .github/workflows -name "*.yml" -exec sed -i 's/@v4/@v3/g' {} \;

# Verify rollback
grep -r "artifact@v" .github/workflows/

# Test single workflow
gh workflow run ci.yml --ref rollback-branch
```