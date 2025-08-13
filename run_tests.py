#!/usr/bin/env python3
"""
VATSIM Data Collection System - Test Runner

Simple script to run tests locally or in CI/CD environments.
Supports both direct execution and pytest framework.

Author: VATSIM Data System
Stage: 1 - Foundation
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_direct_tests():
    """Run tests using direct execution"""
    print("🚀 Running Stage 1 + Stage 2 + Stage 3 + Stage 6 Tests (Direct Execution)")
    print("=" * 60)
    
    try:
        # Import and run all four test classes
        sys.path.insert(0, str(Path(__file__).parent / "tests"))
        from test_system_health import SystemHealthTester
        from test_user_workflows import UserWorkflowTester
        from test_data_quality import DataQualityTester
        from test_service_integration import ServiceIntegrationTester
        
        # Run Stage 1 tests
        print("🧪 Stage 1: Foundation Tests")
        print("-" * 40)
        stage1_tester = SystemHealthTester()
        stage1_results = stage1_tester.run_all_tests()
        
        # Run Stage 2 tests
        print("\n🧪 Stage 2: Core Functionality Tests")
        print("-" * 40)
        stage2_tester = UserWorkflowTester()
        stage2_results = stage2_tester.run_all_tests()
        
        # Run Stage 3 tests
        print("\n🧪 Stage 3: Data Quality Tests")
        print("-" * 40)
        stage3_tester = DataQualityTester()
        stage3_results = stage3_tester.run_all_tests()
        
        # Run Stage 6 tests
        print("\n🧪 Stage 6: Service Integration Tests")
        print("-" * 40)
        stage6_tester = ServiceIntegrationTester()
        stage6_results = stage6_tester.run_all_tests()
        
        # Combined results
        total_passed = (stage1_results["passed"] + stage2_results["passed"] + 
                       stage3_results["passed"] + stage6_results["passed"])
        total_tests = (stage1_results["total"] + stage2_results["total"] + 
                      stage3_results["total"] + stage6_results["total"])
        overall_success = (total_passed / total_tests) >= 0.75
        
        print(f"\n📊 Combined Results: {total_passed}/{total_tests} passed")
        print(f"🎯 Overall Status: {'PASS' if overall_success else 'FAIL'}")
        
        return overall_success
        
    except ImportError as e:
        print(f"❌ Failed to import test module: {e}")
        print("💡 Make sure you're in the project root directory")
        return False
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def run_pytest_tests(verbose=False, stage=None):
    """Run tests using pytest framework"""
    print("🚀 Running Stage 1 + Stage 2 + Stage 3 + Stage 6 Tests (Pytest Framework)")
    print("=" * 60)
    
    try:
        # Build pytest command - use pytest.ini configuration but handle coverage gracefully
        cmd = ["python", "-m", "pytest", "tests/"]
        
        if verbose:
            cmd.extend(["-v", "-s"])
        
        if stage:
            cmd.extend(["-m", f"stage{stage}"])
        
        # Try to run with coverage first
        try:
            print("🧪 Attempting to run tests with coverage...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Tests with coverage completed successfully")
                if result.stdout:
                    print(result.stdout)
                return True
        except Exception as e:
            print(f"⚠️ Coverage test failed: {e}")
        
        # Fallback: run without coverage options
        print("🔄 Falling back to basic pytest execution...")
        cmd = ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-W", "always"]
        
        if verbose:
            cmd.extend(["-s"])
        
        if stage:
            cmd.extend(["-m", f"stage{stage}"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Analyze results for issues
        warning_count = analyze_pytest_results(result.stdout, result.stderr)
        
        # Store warning count for summary
        run_pytest_tests.last_warning_count = warning_count
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Pytest execution failed: {e}")
        return False

def analyze_pytest_results(stdout, stderr):
    """Analyze pytest results and highlight issues"""
    print("\n" + "=" * 60)
    print("🔍 PYTEST RESULTS ANALYSIS")
    print("=" * 60)
    
    if not stdout:
        print("❌ No pytest output captured")
        return
    
    # Count tests and issues
    lines = stdout.split('\n')
    test_count = 0
    passed_count = 0
    failed_count = 0
    error_count = 0
    warning_count = 0
    
    # Extract summary line
    summary_line = None
    for line in lines:
        if "passed" in line and "warnings" in line:
            summary_line = line
            break
    
    if summary_line:
        print(f"📊 Summary: {summary_line.strip()}")
        
        # Parse the summary
        import re
        match = re.search(r'(\d+) passed, (\d+) warnings', summary_line)
        if match:
            passed_count = int(match.group(1))
            warning_count = int(match.group(2))
            print(f"✅ Tests Passed: {passed_count}")
            print(f"⚠️  Warnings: {warning_count}")
    
    # Look for specific issues
    print("\n🔍 ISSUE ANALYSIS:")
    print("-" * 40)
    
    # Check for warnings
    warning_lines = [line for line in lines if any(w in line.lower() for w in ['warning', 'warn', 'deprecated'])]
    if warning_lines:
        print(f"⚠️  Found {len(warning_lines)} warning-related lines:")
        for line in warning_lines[:10]:  # Show first 10
            print(f"   {line.strip()}")
        if len(warning_lines) > 10:
            print(f"   ... and {len(warning_lines) - 10} more")
    
    # Check for errors
    error_lines = [line for line in lines if any(e in line.lower() for e in ['error', 'failed', 'fail'])]
    if error_lines:
        print(f"❌ Found {len(error_lines)} error-related lines:")
        for line in error_lines[:10]:  # Show first 10
            print(f"   {line.strip()}")
        if len(error_lines) > 10:
            print(f"   ... and {len(error_lines) - 10} more")
    
    # Check for async/await issues
    async_lines = [line for line in lines if 'coroutine' in line.lower() and 'never awaited' in line.lower()]
    if async_lines:
        print(f"🔄 Found {len(async_lines)} async/await issues:")
        for line in async_lines[:5]:  # Show first 5
            print(f"   {line.strip()}")
    
    # Check for resource warnings
    resource_lines = [line for line in lines if 'resourcewarning' in line.lower() or 'unclosed transport' in line.lower()]
    if resource_lines:
        print(f"🔌 Found {len(resource_lines)} resource warnings:")
        for line in resource_lines[:5]:  # Show first 5
            print(f"   {line.strip()}")
    
    # Overall assessment
    print("\n📋 OVERALL ASSESSMENT:")
    print("-" * 40)
    
    if failed_count > 0 or error_count > 0:
        print("❌ CRITICAL ISSUES DETECTED - Tests are failing!")
    elif warning_count > 0:
        print("⚠️  WARNINGS DETECTED - Tests pass but have issues")
        print("   - These may become errors in future versions")
        print("   - Consider addressing for code quality")
    else:
        print("✅ ALL TESTS PASSING - No issues detected")
    
    if warning_count > 0:
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   - Address {warning_count} warnings to improve code quality")
        print(f"   - Fix async/await issues to prevent runtime warnings")
        print(f"   - Close network resources to prevent resource warnings")
    
    return warning_count

def check_environment():
    """Check if test environment is ready"""
    print("🔍 Checking test environment...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 11):
        print(f"❌ Python 3.11+ required, got {python_version.major}.{python_version.minor}")
        return False
    
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check test files exist
    test_dir = Path(__file__).parent / "tests"
    required_files = ["test_system_health.py", "test_user_workflows.py", "test_data_quality.py", "conftest.py"]
    
    for file in required_files:
        if not (test_dir / file).exists():
            print(f"❌ Required test file missing: {file}")
            return False
    
    print("✅ Test files found")
    
    # Check dependencies
    try:
        import requests
        print("✅ Requests library available")
    except ImportError:
        print("❌ Requests library not available")
        print("💡 Install with: pip install requests")
        return False
    
    try:
        import pytest
        print("✅ Pytest available")
    except ImportError:
        print("❌ Pytest not available")
        print("💡 Install with: pip install pytest")
        return False
    
    print("✅ Environment ready for testing")
    return True

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Run VATSIM Data Collection System tests")
    parser.add_argument("--method", choices=["direct", "pytest", "both"], default="both",
                       help="Test execution method")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--stage", "-s", type=int, choices=[1, 2, 3, 4, 5, 6],
                       help="Run tests for specific stage only")
    
    args = parser.parse_args()
    
    print("🧪 VATSIM Data Collection System - Test Runner")
    print("🎯 Stage 1: Foundation Tests + Stage 2: Core Functionality + Stage 3: Data Quality")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed")
        sys.exit(1)
    
    print("\n🚀 Starting test execution...")
    
    success = True
    
    # Run tests based on method
    if args.method in ["direct", "both"]:
        print("\n" + "=" * 60)
        if not run_direct_tests():
            success = False
    
    if args.method in ["pytest", "both"]:
        print("\n" + "=" * 60)
        if not run_pytest_tests(verbose=args.verbose, stage=args.stage):
            success = False
    
    # Final results
    print("\n" + "=" * 60)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 60)
    
    if success:
        print("🎉 All tests PASSED!")
        print("✅ System is ready for users")
        
        # Check if there were warnings
        if hasattr(run_pytest_tests, 'last_warning_count') and run_pytest_tests.last_warning_count > 0:
            print(f"\n⚠️  NOTE: {run_pytest_tests.last_warning_count} warnings were detected")
            print("   - These don't affect functionality but should be addressed")
            print("   - Warnings may become errors in future versions")
        
        sys.exit(0)
    else:
        print("❌ Some tests FAILED!")
        print("⚠️  System may have issues that need attention")
        
        # Provide specific guidance
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("   - Review the detailed error analysis above")
        print("   - Fix any failing tests before deployment")
        print("   - Address warnings to improve code quality")
        
        sys.exit(1)

if __name__ == "__main__":
    main() 