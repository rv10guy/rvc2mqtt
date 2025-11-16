#!/usr/bin/env python3
"""
Test Runner for Phase 2 Bidirectional Communication

Runs all unit and integration tests and provides a summary report.
"""

import unittest
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import test modules
from tests import test_rvc_commands
from tests import test_command_validator
from tests import test_integration


def print_banner(text):
    """Print a banner"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def run_all_tests():
    """Run all test suites and provide summary"""

    print_banner("Phase 2 Test Suite - Bidirectional Communication")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create test loader and suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Track individual test suite results
    test_suites = [
        ("RV-C Command Encoder Tests", test_rvc_commands),
        ("Command Validator Tests", test_command_validator),
        ("Integration Tests", test_integration),
    ]

    results = []

    for suite_name, test_module in test_suites:
        print_banner(suite_name)

        # Create suite for this module
        module_suite = loader.loadTestsFromModule(test_module)

        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(module_suite)

        # Store results
        results.append((suite_name, result))

        print()

    # Print summary
    print_banner("Test Summary")

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    for suite_name, result in results:
        tests_run = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)

        total_tests += tests_run
        total_failures += failures
        total_errors += errors
        total_skipped += skipped

        # Status indicator
        if result.wasSuccessful():
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"

        print(f"{status:12} {suite_name:40} ({tests_run} tests, {failures} failures, {errors} errors)")

    print()
    print("-" * 80)
    print(f"Total Tests:    {total_tests}")
    print(f"Passed:         {total_tests - total_failures - total_errors - total_skipped}")
    print(f"Failed:         {total_failures}")
    print(f"Errors:         {total_errors}")
    print(f"Skipped:        {total_skipped}")

    if total_failures + total_errors == 0:
        print()
        print("✓ ALL TESTS PASSED")
        print()
        return 0
    else:
        print()
        print("✗ SOME TESTS FAILED")
        print()

        # Print failure details
        print_banner("Failure Details")

        for suite_name, result in results:
            if result.failures or result.errors:
                print(f"\n{suite_name}:")

                for test, traceback in result.failures:
                    print(f"\n  FAILURE: {test}")
                    print(f"  {traceback}")

                for test, traceback in result.errors:
                    print(f"\n  ERROR: {test}")
                    print(f"  {traceback}")

        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
