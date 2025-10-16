#!/usr/bin/env python3
"""
Test runner for Construction Management App
Runs comprehensive test suite with coverage reporting
"""

import subprocess
import sys
import os
import argparse

def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    print("🧪 Running Construction Manager Test Suite...")
    print("=" * 60)
    
    # Run pytest with coverage
    result = subprocess.run([
        "python", "-m", "pytest", 
        "tests/", 
        "-v", 
        "--tb=short",
        "--cov=backend",
        "--cov=utils",
        "--cov=scheduling_engin",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=80"  # Fail if coverage below 80%
    ])
    
    print("=" * 60)
    return result.returncode

def run_specific_test(test_path):
    """Run a specific test file or test function"""
    print(f"🧪 Running specific test: {test_path}")
    print("=" * 60)
    
    result = subprocess.run([
        "python", "-m", "pytest",
        test_path,
        "-v",
        "--tb=short"
    ])
    
    print("=" * 60)
    return result.returncode

def run_fast_tests():
    """Run tests quickly without coverage"""
    print("🧪 Running Fast Tests (No Coverage)...")
    print("=" * 60)
    
    result = subprocess.run([
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=line",
        "-x"  # Stop on first failure
    ])
    
    print("=" * 60)
    return result.returncode

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Run Construction Manager tests")
    parser.add_argument("--fast", action="store_true", help="Run fast tests without coverage")
    parser.add_argument("--test", type=str, help="Run specific test file or function")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage (default)")
    
    args = parser.parse_args()
    
    if args.test:
        return_code = run_specific_test(args.test)
    elif args.fast:
        return_code = run_fast_tests()
    else:
        return_code = run_tests_with_coverage()
    
    if return_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())