# Security Vulnerability Operational Runbooks

## Overview

This document provides detailed operational runbooks for handling different types of security vulnerabilities in the vet-core package. Each runbook includes step-by-step procedures, commands, and decision trees for specific vulnerability scenarios.

## Table of Contents

1. [Critical Vulnerability Runbook](#critical-vulnerability-runbook)
2. [High Severity Vulnerability Runbook](#high-severity-vulnerability-runbook)
3. [Dependency Conflict Resolution](#dependency-conflict-resolution)
4. [Build System Vulnerabilities](#build-system-vulnerabilities)
5. [Development Tool Vulnerabilities](#development-tool-vulnerabilities)
6. [Supply Chain Attack Response](#supply-chain-attack-response)
7. [Zero-Day Vulnerability Response](#zero-day-vulnerability-response)
8. [Batch Vulnerability Processing](#batch-vulnerability-processing)

## Critical Vulnerability Runbook

### Scope
- CVSS Score: 9.0-10.0
- Active exploitation possible
- Immediate security risk
- Response Time: 24 hours maximum

### Prerequisites
- Emergency response team activated
- Incident commander assigned
- Communication channels established

### Step-by-Step Procedure

#### Phase 1: Immediate Assessment (0-2 hours)

**Step 1: Confirm Vulnerability**
```bash
# Verify vulnerability exists in current environment
pip-audit --package {PACKAGE_NAME} --format json > critical-vuln-scan.json

# Check vulnerability details
python -c "
import json
with open('critical-vuln-scan.json') as f:
    data = json.load(f)
    for vuln in data.get('vulnerabilities', []):
        if vuln['id'] == '{VULNERABILITY_ID}':
            print(f'Confirmed: {vuln}')
"
```

**Step 2: Impact Assessment**
```bash
# Assess package criticality
python -c "
from vet_core.security.assessor import SecurityAssessor
assessor = SecurityAssessor()
impact = assessor.assess_package_criticality('{PACKAGE_NAME}')
print(f'Package criticality: {impact}')
"

# Check for active exploitation
python scripts/security_monitoring.py --check-exploitation {VULNERABILITY_ID}
```

**Step 3: Emergency Notification**
```bash
# Send critical alert
python scripts/security_monitoring.py --critical-alert {VULNERABILITY_ID} \
    --severity critical \
    --message "Critical vulnerability detected in {PACKAGE_NAME}"

# Update incident tracking
python -c "
from vet_core.security.audit_trail import AuditTrail
audit = AuditTrail()
audit.record_incident_start('{VULNERABILITY_ID}', 'critical', 'immediate_response_required')
"
```

#### Phase 2: Emergency Response (2-8 hours)

**Step 4: Temporary Mitigation**
```bash
# Check for temporary workarounds
python scripts/security_scan.py --workarounds {VULNERABILITY_ID}

# If workaround available, implement immediately
# Document workaround in audit trail
python -c "
from vet_core.security.audit_trail import AuditTrail
audit = AuditTrail()
audit.record_mitigation_action('{VULNERABILITY_ID}', 'temporary_workaround', 'details')
"
```

**Step 5: Emergency Fix Preparation**
```bash
# Identify fix version
python scripts/security_scan.py --fix-version {PACKAGE_NAME} {VULNERABILITY_ID}

# Validate fix availability
pip index versions {PACKAGE_NAME} | grep {FIX_VERSION}

# Create emergency branch
git checkout -b emergency-fix-{VULNERABILITY_ID}
```

**Step 6: Emergency Testing**
```bash
# Create test environment
python -m venv emergency-test-env
source emergency-test-env/bin/activate

# Install fix version
pip install {PACKAGE_NAME}=={FIX_VERSION}

# Run critical tests only
pytest tests/critical/ -x --tb=short --maxfail=1

# Validate vulnerability fix
pip-audit --package {PACKAGE_NAME} --format json | \
python -c "
import json, sys
data = json.load(sys.stdin)
vulns = [v for v in data.get('vulnerabilities', []) if v['id'] == '{VULNERABILITY_ID}']
if not vulns:
    print('VULNERABILITY FIXED')
    sys.exit(0)
else:
    print('VULNERABILITY STILL PRESENT')
    sys.exit(1)
"
```

#### Phase 3: Emergency Deployment (8-24 hours)

**Step 7: Emergency Deployment**
```bash
# Update pyproject.toml
python -c "
import toml
with open('pyproject.toml', 'r') as f:
    config = toml.load(f)

# Update dependency version
dependencies = config.get('project', {}).get('dependencies', [])
for i, dep in enumerate(dependencies):
    if dep.startswith('{PACKAGE_NAME}'):
        dependencies[i] = '{PACKAGE_NAME}>={FIX_VERSION}'
        break

with open('pyproject.toml', 'w') as f:
    toml.dump(config, f)
"

# Commit emergency fix
git add pyproject.toml
git commit -m "Emergency fix for {VULNERABILITY_ID} - upgrade {PACKAGE_NAME} to {FIX_VERSION}"

# Deploy immediately
python scripts/upgrade_testing_pipeline.py --emergency-deploy \
    --package {PACKAGE_NAME} \
    --version {FIX_VERSION}
```

**Step 8: Post-Deployment Validation**
```bash
# Verify deployment success
pip list | grep {PACKAGE_NAME}

# Run full security scan
python scripts/security_scan.py --comprehensive --output post-fix-scan.json

# Validate system functionality
pytest tests/ --tb=short

# Record successful remediation
python -c "
from vet_core.security.audit_trail import AuditTrail
audit = AuditTrail()
audit.record_remediation_completion('{VULNERABILITY_ID}', 'success', 'emergency_deployment')
"
```

### Decision Tree

```
Critical Vulnerability Detected
├── Is fix available?
│   ├── Yes → Proceed with emergency fix
│   └── No → Implement workaround/mitigation
├── Are tests passing?
│   ├── Yes → Deploy immediately
│   └── No → Assess risk vs. test failure
├── Is vulnerability confirmed fixed?
│   ├── Yes → Complete incident response
│   └── No → Escalate to security team
```

### Rollback Criteria
- Test suite failure rate > 10%
- Critical functionality broken
- New vulnerabilities introduced
- Performance degradation > 50%

## High Severity Vulnerability Runbook

### Scope
- CVSS Score: 7.0-8.9
- Significant security risk
- Response Time: 72 hours maximum

### Step-by-Step Procedure

#### Phase 1: Assessment (0-8 hours)

**Step 1: Vulnerability Analysis**
```bash
# Detailed vulnerability scan
python scripts/security_scan.py --detailed --package {PACKAGE_NAME} --output high-severity-analysis.json

# Risk assessment
python -c "
from vet_core.security.assessor import SecurityAssessor
assessor = SecurityAssessor()
risk = assessor.assess_vulnerability_risk('{VULNERABILITY_ID}')
print(f'Risk Assessment: {risk}')
"
```

**Step 2: Impact Evaluation**
```bash
# Check package usage
python -c "
import ast
import os
from pathlib import Path

def find_imports(directory):
    imports = set()
    for py_file in Path(directory).rglob('*.py'):
        try:
            with open(py_file) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith('{PACKAGE_NAME}'):
                            imports.add(str(py_file))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith('{PACKAGE_NAME}'):
                        imports.add(str(py_file))
        except:
            continue
    return imports

usage = find_imports('src/')
print(f'Package usage found in: {len(usage)} files')
for file in sorted(usage):
    print(f'  - {file}')
"
```

**Step 3: Fix Planning**
```bash
# Identify fix options
python scripts/security_scan.py --fix-options {VULNERABILITY_ID}

# Check compatibility
python scripts/validate_upgrades.py --compatibility-check \
    --package {PACKAGE_NAME} \
    --target-version {FIX_VERSION}
```

#### Phase 2: Implementation (8-48 hours)

**Step 4: Upgrade Preparation**
```bash
# Create feature branch
git checkout -b security-fix-{VULNERABILITY_ID}

# Backup current state
pip freeze > requirements-backup-$(date +%Y%m%d-%H%M%S).txt
cp pyproject.toml pyproject.toml.backup

# Create test environment
python -m venv test-upgrade-env
source test-upgrade-env/bin/activate
pip install -e .[dev]
```

**Step 5: Upgrade Implementation**
```bash
# Update dependency
pip install {PACKAGE_NAME}=={FIX_VERSION}

# Update configuration
python -c "
import toml
with open('pyproject.toml', 'r') as f:
    config = toml.load(f)

# Update dependency constraint
dependencies = config.get('project', {}).get('dependencies', [])
for i, dep in enumerate(dependencies):
    if dep.startswith('{PACKAGE_NAME}'):
        dependencies[i] = '{PACKAGE_NAME}>={FIX_VERSION},<{NEXT_MAJOR_VERSION}'
        break

with open('pyproject.toml', 'w') as f:
    toml.dump(config, f)
"
```

**Step 6: Comprehensive Testing**
```bash
# Run full test suite
pytest tests/ --cov=vet_core --cov-report=html --cov-report=term

# Performance testing
python scripts/upgrade_testing_pipeline.py --performance-test \
    --package {PACKAGE_NAME} \
    --baseline-version {CURRENT_VERSION} \
    --target-version {FIX_VERSION}

# Security validation
pip-audit --format json --output post-upgrade-scan.json
python scripts/security_scan.py --validate-fix {VULNERABILITY_ID}
```

#### Phase 3: Deployment (48-72 hours)

**Step 7: Staged Deployment**
```bash
# Commit changes
git add .
git commit -m "Security fix: Upgrade {PACKAGE_NAME} to {FIX_VERSION} (fixes {VULNERABILITY_ID})"

# Create pull request
gh pr create --title "Security Fix: {VULNERABILITY_ID}" \
    --body "Fixes vulnerability {VULNERABILITY_ID} by upgrading {PACKAGE_NAME} to {FIX_VERSION}"

# Deploy to staging
python scripts/upgrade_testing_pipeline.py --deploy-staging \
    --package {PACKAGE_NAME} \
    --version {FIX_VERSION}
```

**Step 8: Production Deployment**
```bash
# Final validation
python scripts/security_scan.py --final-validation {VULNERABILITY_ID}

# Deploy to production
python scripts/upgrade_testing_pipeline.py --deploy-production \
    --package {PACKAGE_NAME} \
    --version {FIX_VERSION}

# Post-deployment monitoring
python scripts/security_monitoring.py --monitor-deployment \
    --vulnerability {VULNERABILITY_ID} \
    --duration 24h
```

## Dependency Conflict Resolution

### Common Conflict Scenarios

#### Scenario 1: Version Constraint Conflicts

**Problem**: Multiple packages require incompatible versions of the same dependency

**Resolution Steps**:
```bash
# Analyze dependency tree
pip-tree --packages {CONFLICTING_PACKAGE}

# Find compatible version range
python -c "
import subprocess
import json

def get_compatible_versions(package1, package2):
    # Get version requirements for each package
    result1 = subprocess.run(['pip', 'show', package1], capture_output=True, text=True)
    result2 = subprocess.run(['pip', 'show', package2], capture_output=True, text=True)
    
    # Parse requirements and find intersection
    # Implementation depends on specific conflict
    pass

get_compatible_versions('{PACKAGE1}', '{PACKAGE2}')
"

# Test resolution
pip install {PACKAGE1}=={VERSION1} {PACKAGE2}=={VERSION2}
pytest tests/ --tb=short
```

#### Scenario 2: Transitive Dependency Conflicts

**Resolution Process**:
```bash
# Map transitive dependencies
python -c "
import pkg_resources

def map_dependencies(package_name):
    try:
        dist = pkg_resources.get_distribution(package_name)
        deps = {}
        for req in dist.requires():
            deps[req.project_name] = str(req.specifier)
        return deps
    except:
        return {}

deps = map_dependencies('{PACKAGE_NAME}')
for dep, version in deps.items():
    print(f'{dep}: {version}')
"

# Resolve conflicts using pip-tools
pip-compile --upgrade-package {CONFLICTING_PACKAGE}
```

## Build System Vulnerabilities

### setuptools Vulnerabilities

**Common Issues**:
- PYSEC-2022-43012: Command injection vulnerability
- PYSEC-2025-49: Path traversal vulnerability

**Resolution Steps**:
```bash
# Check current setuptools version
python -c "import setuptools; print(setuptools.__version__)"

# Upgrade setuptools
pip install --upgrade setuptools>=78.1.1

# Validate build process
python -m build --wheel --sdist

# Test package installation
pip install dist/*.whl
python -c "import vet_core; print('Import successful')"

# Verify vulnerability resolution
pip-audit --package setuptools --format json
```

### pip Vulnerabilities

**Resolution Process**:
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Verify pip functionality
pip --version
pip check

# Test package operations
pip install --dry-run some-test-package
```

## Development Tool Vulnerabilities

### Code Formatting Tool Vulnerabilities (black, flake8, etc.)

**Example: black PYSEC-2024-48**

**Resolution Steps**:
```bash
# Check current black version
black --version

# Upgrade black
pip install black>=24.3.0

# Test code formatting
black --check src/ tests/
black --diff src/ tests/

# Update pre-commit hooks
pre-commit autoupdate
pre-commit run black --all-files

# Validate formatting consistency
git diff --name-only | xargs black --check
```

### Linting Tool Vulnerabilities

**Resolution Process**:
```bash
# Update linting tools
pip install --upgrade flake8 pylint mypy

# Run linting validation
flake8 src/ tests/
pylint src/
mypy src/

# Update configuration if needed
# Check .flake8, pylint.rc, mypy.ini files
```

## Supply Chain Attack Response

### Indicators of Supply Chain Attack

**Detection Signs**:
- Unexpected package updates
- New dependencies not explicitly added
- Unusual network activity
- Modified package checksums

**Response Procedure**:
```bash
# Freeze current environment
pip freeze > emergency-freeze.txt

# Verify package integrity
python -c "
import hashlib
import subprocess

def verify_package_integrity(package_name):
    # Get package info
    result = subprocess.run(['pip', 'show', '-f', package_name], 
                          capture_output=True, text=True)
    
    # Check against known good hashes
    # Implementation depends on available hash database
    pass

verify_package_integrity('{SUSPICIOUS_PACKAGE}')
"

# Isolate affected systems
# Remove suspicious packages
pip uninstall {SUSPICIOUS_PACKAGE} -y

# Restore from known good state
pip install -r known-good-requirements.txt

# Report incident
python scripts/security_monitoring.py --report-incident \
    --type supply_chain_attack \
    --package {SUSPICIOUS_PACKAGE}
```

## Zero-Day Vulnerability Response

### When No Fix is Available

**Immediate Actions**:
```bash
# Assess exposure
python -c "
from vet_core.security.assessor import SecurityAssessor
assessor = SecurityAssessor()
exposure = assessor.assess_zero_day_exposure('{PACKAGE_NAME}', '{VULNERABILITY_DETAILS}')
print(f'Exposure assessment: {exposure}')
"

# Implement workarounds
# 1. Disable affected functionality
# 2. Add input validation
# 3. Implement monitoring

# Monitor for fixes
python scripts/security_monitoring.py --monitor-zero-day {VULNERABILITY_ID}
```

**Mitigation Strategies**:
1. **Code-level workarounds**
2. **Network-level protections**
3. **Runtime monitoring**
4. **Access restrictions**

## Batch Vulnerability Processing

### Multiple Vulnerabilities in Single Package

**Processing Steps**:
```bash
# Analyze all vulnerabilities
python scripts/security_scan.py --package {PACKAGE_NAME} --all-vulnerabilities

# Find minimum fix version
python -c "
import json
with open('vulnerability-scan.json') as f:
    data = json.load(f)

package_vulns = [v for v in data['vulnerabilities'] if v['package'] == '{PACKAGE_NAME}']
fix_versions = []
for vuln in package_vulns:
    fix_versions.extend(vuln['fix_versions'])

# Find minimum version that fixes all
from packaging import version
min_fix = max(fix_versions, key=lambda x: version.parse(x))
print(f'Minimum fix version: {min_fix}')
"

# Single upgrade for all vulnerabilities
pip install {PACKAGE_NAME}=={MIN_FIX_VERSION}
```

### Multiple Packages with Vulnerabilities

**Batch Processing**:
```bash
# Generate batch upgrade plan
python scripts/security_scan.py --batch-plan --output batch-upgrade-plan.json

# Execute batch upgrades
python scripts/upgrade_testing_pipeline.py --batch-upgrade batch-upgrade-plan.json

# Validate all fixes
python scripts/security_scan.py --validate-batch-fixes
```

## Monitoring and Alerting

### Continuous Monitoring Setup

**Monitoring Commands**:
```bash
# Start continuous monitoring
python scripts/security_monitoring.py --continuous \
    --interval 3600 \
    --alert-threshold high

# Monitor specific vulnerabilities
python scripts/security_monitoring.py --watch-list \
    --vulnerabilities PYSEC-2024-48,PYSEC-2022-43012
```

### Alert Configuration

**Alert Types**:
- Critical vulnerability detected
- Fix available for tracked vulnerability
- Upgrade validation failure
- Security scan failure

**Alert Setup**:
```bash
# Configure alerts
python scripts/manage_security_config.py --set-alerts \
    --critical-email security-team@company.com \
    --high-slack "#security-alerts" \
    --medium-ticket "JIRA:SEC"
```

## Troubleshooting Common Issues

### Upgrade Failures

**Common Causes and Solutions**:

1. **Dependency Conflicts**
   ```bash
   pip install --upgrade-strategy eager {PACKAGE_NAME}
   ```

2. **Test Failures**
   ```bash
   pytest tests/ -v --tb=long --maxfail=5
   # Analyze failures and update tests if needed
   ```

3. **Performance Regressions**
   ```bash
   python scripts/upgrade_testing_pipeline.py --performance-analysis \
       --baseline {OLD_VERSION} --target {NEW_VERSION}
   ```

### Rollback Issues

**Rollback Troubleshooting**:
```bash
# Verify rollback state
pip list | grep {PACKAGE_NAME}

# Check for residual changes
git status
git diff

# Force clean rollback
pip uninstall {PACKAGE_NAME} -y
pip install {PACKAGE_NAME}=={PREVIOUS_VERSION}
```

## Documentation and Reporting

### Incident Documentation

**Required Documentation**:
- Vulnerability details and impact
- Response timeline and actions
- Testing and validation results
- Lessons learned and improvements

**Documentation Template**:
```bash
# Generate incident report
python -c "
from vet_core.security.audit_trail import AuditTrail
audit = AuditTrail()
report = audit.generate_incident_report('{VULNERABILITY_ID}')
with open('incident-report-{VULNERABILITY_ID}.md', 'w') as f:
    f.write(report)
"
```

### Post-Incident Review

**Review Checklist**:
- [ ] Response time analysis
- [ ] Process effectiveness evaluation
- [ ] Tool and automation improvements
- [ ] Team training needs assessment
- [ ] Documentation updates required

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-27  
**Next Review**: 2025-04-27  
**Owner**: Security Team