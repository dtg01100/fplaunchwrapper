# Test Suite for fplaunchwrapper

This directory contains self-contained tests for the fplaunchwrapper project.

## Test Files

### test_wrapper_generation.sh
Tests core wrapper generation functionality:
- Basic wrapper creation
- Name collision detection
- Blocklist functionality
- Invalid name handling
- Environment variable loading
- Pre-launch script execution
- Preference handling
- Wrapper cleanup
- Tar extraction safety
- System command detection

### test_management_functions.sh
Tests management and configuration functions:
- Preference setting and retrieval
- Alias creation and management
- Environment variable management
- Blocklist add/remove
- Export/import preferences
- Script management (pre-launch/post-run)
- Wrapper removal with cleanup
- Listing wrappers

### run_all_tests.sh
Runs all test suites and provides a summary.

## Running Tests

### Run all tests:
```bash
cd tests
./run_all_tests.sh
```

### Run individual test suites:
```bash
./test_wrapper_generation.sh
./test_management_functions.sh
```

## Test Design

All tests are self-contained and:
- Use temporary directories (auto-cleaned on exit)
- Don't require actual Flatpak installation
- Mock external dependencies
- Test both success and failure cases
- Provide clear pass/fail indicators

## Test Output

- ✓ Green checkmark = Test passed
- ✗ Red X = Test failed
- ~ Yellow tilde = Test skipped
- Summary at end shows total passed/failed

## Adding New Tests

To add a new test:
1. Create test function following naming convention: `test_<feature_name>()`
2. Use assert functions for validation
3. Add to main() to execute
4. Ensure cleanup happens (use trap)
5. Make test self-contained with mocks
