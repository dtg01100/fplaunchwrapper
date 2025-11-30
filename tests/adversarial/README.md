# Adversarial Test Suite

This directory contains **DANGEROUS** adversarial tests designed to attack fplaunchwrapper code and test its robustness against unusual system setups.

## ⚠️  CRITICAL WARNINGS ⚠️

### These tests are **UNSAFE** and should ONLY be run in:
- **Isolated development environments** (VMs/containers recommended)
- **Dedicated testing systems** you are authorized to test
- **NEVER** on production systems or user workstations

### These tests may:
- Execute malicious inputs through fplaunchwrapper
- Test fplaunchwrapper security boundaries
- Attempt to bypass fplaunchwrapper protections
- Create unusual file system layouts
- Simulate broken system configurations
- Leave residual test artifacts

### Requirements:
- Run in isolated environment (VM/container recommended)
- **NEVER** run as root
- Backup your system before running
- Monitor system during execution

## Test Files

### `test_fplaunchwrapper_adversarial.sh`
**Purpose**: Attack fplaunchwrapper security functions and input validation

**Attack Vectors Tested**:
- Command injection through wrapper options
- Path traversal attacks
- Environment variable poisoning
- Symlink attacks on configuration files
- Input validation bypasses
- Privilege escalation attempts
- File system attacks
- Memory and process attacks

### `test_robustness_adversarial.sh`
**Purpose**: Test fplaunchwrapper robustness against weird user setups

**Weird Setups Tested**:
- No HOME directory
- Non-existent XDG directories
- Read-only directories
- No write permissions
- Weird HOME structure
- No PATH
- PATH with spaces and special characters
- Unicode and encoding issues
- Extremely long paths
- No /tmp directory
- Full filesystem
- Weird file permissions
- Broken symlinks
- Environment variable pollution
- Concurrent access
- Network filesystem simulation
- Case sensitivity issues
- Resource limits
- Mixed encoding files
- Timezone and locale issues

### `test_wrapper_options_adversarial.sh`
**Purpose**: Attack wrapper --fpwrapper-* options functionality

**Attack Vectors Tested**:
- Command injection through wrapper options
- Path traversal via config directory options
- Privilege escalation through sandbox editing
- Environment variable poisoning
- Race conditions in script management
- Resource exhaustion attacks
- Symlink attacks on configuration files
- Input validation bypasses

### `test_systemd_adversarial.sh`
**Purpose**: Attack systemd integration points

**Attack Vectors Tested**:
- Malicious systemd service creation
- Privilege escalation through systemd
- Persistence attacks
- Resource exhaustion attacks
- File system attacks
- Network-based attacks

### `test_package_adversarial.sh`
**Purpose**: Attack package manager integration

**Attack Vectors Tested**:
- Malicious package installation
- Privilege escalation through package scripts
- Package database poisoning
- Repository hijacking attacks
- Package signature spoofing
- Dependency confusion attacks
- Supply chain attacks

## Running Adversarial Tests

### Safety Confirmation
All adversarial tests require explicit confirmation:

```bash
# You must type: "I UNDERSTAND THE RISKS"
TESTING=1 tests/adversarial/test_fplaunchwrapper_adversarial.sh
```

### Individual Tests
```bash
# Test fplaunchwrapper security
TESTING=1 tests/adversarial/test_fplaunchwrapper_adversarial.sh

# Test robustness against weird setups
TESTING=1 tests/adversarial/test_robustness_adversarial.sh

# Test wrapper options security
TESTING=1 tests/adversarial/test_wrapper_options_adversarial.sh

# Test systemd integration security
TESTING=1 tests/adversarial/test_systemd_adversarial.sh

# Test package manager security
TESTING=1 tests/adversarial/test_package_adversarial.sh
```

### From Main Test Runner
```bash
# Run all safe tests
tests/run_all_tests.sh

# Then run adversarial tests (separately)
TESTING=1 tests/adversarial/test_fplaunchwrapper_adversarial.sh
```

## Expected Outcomes

### Success Indicators
- All attacks blocked
- No vulnerabilities found
- Weird setups handled gracefully
- Robust behavior maintained

### Failure Indicators
- Vulnerabilities found
- Attacks not blocked
- System compromised
- Robustness issues

### Test Results
Each test provides detailed output:
- ✅ **Passed**: Test succeeded, attack blocked
- ❌ **Failed**: Test failed, vulnerability found
- 🟣 **[ATTACK]**: Attack being attempted
- 🛡️ **[DEFENSE]**: Attack successfully blocked
- ℹ️ **[INFO]**: Test information

## Test Philosophy

These adversarial tests follow the principle:

> **"The best way to secure code is to actively try to break it"**

Rather than just testing happy paths, these tests:
1. **Attack** fplaunchwrapper with malicious inputs
2. **Probe** for security vulnerabilities
3. **Test** robustness against edge cases
4. **Verify** proper error handling
5. **Ensure** graceful degradation

## Integration with Development

### During Development
Run adversarial tests frequently to catch regressions:
```bash
# After making changes
TESTING=1 tests/adversarial/test_fplaunchwrapper_adversarial.sh
TESTING=1 tests/adversarial/test_robustness_adversarial.sh
```

### Before Releases
Run full adversarial test suite:
```bash
# Comprehensive testing
TESTING=1 tests/adversarial/test_fplaunchwrapper_adversarial.sh
TESTING=1 tests/adversarial/test_robustness_adversarial.sh
TESTING=1 tests/adversarial/test_wrapper_options_adversarial.sh
```

### CI/CD Integration
Add to CI pipeline (isolated environment only):
```yaml
# Example GitHub Actions
- name: Run Adversarial Tests
  run: |
    docker run --rm -v $(pwd):/app ubuntu:22.04 /app/tests/adversarial/test_fplaunchwrapper_adversarial.sh
```

## Contributing

When adding new adversarial tests:

1. **Focus on fplaunchwrapper code**, not system security
2. **Test specific attack vectors** with clear success/failure criteria
3. **Include safety warnings** and confirmation prompts
4. **Document attack scenarios** clearly
5. **Test both security and robustness**
6. **Ensure proper cleanup** after tests

## Troubleshooting

### Test Environment Issues
- Ensure isolated environment
- Check permissions on test directories
- Verify mock commands are working
- Monitor system resources during tests

### False Positives
- Some tests may "fail" when they're actually working correctly
- Review test logic and expected behavior
- Consider if "failure" indicates proper security blocking

### Test Isolation
- Use unique test directories with process IDs
- Clean up all test artifacts
- Don't modify real system files
- Use mock commands instead of real system tools

## Security Considerations

These tests themselves are secure because they:
- Never run as root
- Use isolated test environments
- Clean up all artifacts
- Require explicit user confirmation
- Focus on testing our code, not attacking systems

## License

These adversarial tests follow the same license as fplaunchwrapper and are intended for security testing and robustness verification only.