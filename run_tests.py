#!/usr/bin/env python3
"""
Test runner for VATSIM Data Collection System.

This script runs all tests and quality gates for the system.
"""

import asyncio
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any

from tests.quality.quality_gates import QualityGate


class TestRunner:
    """Test runner for the VATSIM Data Collection System."""

    def __init__(self):
        self.test_results: Dict[str, Any] = {}
        self.quality_gate = QualityGate()

    async def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests."""
        print("🔬 Running unit tests...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
                capture_output=True,
                text=True
            )
            
            passed = result.returncode == 0
            return {
                "type": "unit",
                "passed": passed,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_count": self._count_tests(result.stdout)
            }
        except Exception as e:
            return {
                "type": "unit",
                "passed": False,
                "error": str(e),
                "test_count": 0
            }

    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        print("🔗 Running integration tests...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
                capture_output=True,
                text=True
            )
            
            passed = result.returncode == 0
            return {
                "type": "integration",
                "passed": passed,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_count": self._count_tests(result.stdout)
            }
        except Exception as e:
            return {
                "type": "integration",
                "passed": False,
                "error": str(e),
                "test_count": 0
            }

    async def run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests."""
        print("🌐 Running end-to-end tests...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/e2e/", "-v", "--tb=short"],
                capture_output=True,
                text=True
            )
            
            passed = result.returncode == 0
            return {
                "type": "e2e",
                "passed": passed,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_count": self._count_tests(result.stdout)
            }
        except Exception as e:
            return {
                "type": "e2e",
                "passed": False,
                "error": str(e),
                "test_count": 0
            }

    async def run_quality_gates(self) -> Dict[str, Any]:
        """Run quality gates."""
        print("✅ Running quality gates...")
        try:
            checks = await self.quality_gate.run_all_checks()
            summary = self.quality_gate.get_summary()
            
            return {
                "type": "quality",
                "passed": self.quality_gate.is_passed(),
                "summary": summary,
                "checks": checks
            }
        except Exception as e:
            return {
                "type": "quality",
                "passed": False,
                "error": str(e)
            }

    async def run_coverage_report(self) -> Dict[str, Any]:
        """Run coverage report."""
        print("📊 Running coverage report...")
        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    "--cov=app",
                    "--cov-report=term-missing",
                    "--cov-report=html:htmlcov",
                    "--cov-fail-under=80",
                    "tests/"
                ],
                capture_output=True,
                text=True
            )
            
            # Parse coverage percentage
            coverage_percentage = 0.0
            if result.stdout:
                for line in result.stdout.splitlines():
                    if "TOTAL" in line and "%" in line:
                        try:
                            coverage_percentage = float(line.split("%")[0].split()[-1])
                            break
                        except (ValueError, IndexError):
                            pass
            
            passed = coverage_percentage >= 80.0
            return {
                "type": "coverage",
                "passed": passed,
                "coverage_percentage": coverage_percentage,
                "minimum_required": 80.0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {
                "type": "coverage",
                "passed": False,
                "error": str(e),
                "coverage_percentage": 0.0
            }

    def _count_tests(self, output: str) -> int:
        """Count the number of tests from pytest output."""
        if not output:
            return 0
        
        count = 0
        for line in output.splitlines():
            if "::test_" in line or "::Test" in line:
                count += 1
        return count

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and quality gates."""
        print("🚀 Starting comprehensive test suite...")
        print("=" * 60)
        
        # Run all test types
        unit_result = await self.run_unit_tests()
        integration_result = await self.run_integration_tests()
        e2e_result = await self.run_e2e_tests()
        quality_result = await self.run_quality_gates()
        coverage_result = await self.run_coverage_report()
        
        # Compile results
        self.test_results = {
            "unit": unit_result,
            "integration": integration_result,
            "e2e": e2e_result,
            "quality": quality_result,
            "coverage": coverage_result,
            "summary": self._generate_summary([
                unit_result, integration_result, e2e_result, quality_result, coverage_result
            ])
        }
        
        return self.test_results

    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of all test results."""
        total_tests = sum(r.get("test_count", 0) for r in results if "test_count" in r)
        passed_tests = sum(1 for r in results if r.get("passed", False))
        total_types = len(results)
        
        return {
            "total_test_types": total_types,
            "passed_test_types": passed_tests,
            "failed_test_types": total_types - passed_tests,
            "success_rate": (passed_tests / total_types * 100) if total_types > 0 else 0,
            "total_tests": total_tests,
            "overall_passed": all(r.get("passed", False) for r in results)
        }

    def print_results(self):
        """Print test results in a formatted way."""
        print("\n" + "=" * 60)
        print("📋 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        if not self.test_results:
            print("❌ No test results available")
            return
        
        summary = self.test_results.get("summary", {})
        
        # Print overall summary
        print(f"🎯 Overall Status: {'✅ PASSED' if summary.get('overall_passed') else '❌ FAILED'}")
        print(f"📊 Success Rate: {summary.get('success_rate', 0):.1f}%")
        print(f"🧪 Test Types: {summary.get('passed_test_types', 0)}/{summary.get('total_test_types', 0)} passed")
        print(f"🔢 Total Tests: {summary.get('total_tests', 0)}")
        
        print("\n📋 Detailed Results:")
        print("-" * 40)
        
        # Print individual test results
        for test_type, result in self.test_results.items():
            if test_type == "summary":
                continue
                
            status = "✅ PASSED" if result.get("passed") else "❌ FAILED"
            test_count = result.get("test_count", "N/A")
            
            print(f"{test_type.upper():12} | {status:10} | Tests: {test_count}")
            
            # Print additional details for failed tests
            if not result.get("passed"):
                if "error" in result:
                    print(f"  └─ Error: {result['error']}")
                elif "stderr" in result and result["stderr"]:
                    print(f"  └─ Error: {result['stderr'][:100]}...")
        
        # Print quality gate details
        if "quality" in self.test_results:
            quality_result = self.test_results["quality"]
            if "summary" in quality_result:
                q_summary = quality_result["summary"]
                print(f"\n✅ Quality Gates: {q_summary.get('passed_checks', 0)}/{q_summary.get('total_checks', 0)} passed")
                print(f"📈 Quality Score: {q_summary.get('success_rate', 0):.1f}%")
        
        # Print coverage details
        if "coverage" in self.test_results:
            coverage_result = self.test_results["coverage"]
            coverage_pct = coverage_result.get("coverage_percentage", 0)
            print(f"\n📊 Code Coverage: {coverage_pct:.1f}% (min: 80.0%)")
        
        print("\n" + "=" * 60)

    def save_results(self, filename: str = "test_results.json"):
        """Save test results to a JSON file."""
        import json
        from datetime import datetime
        
        results_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            "results": self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(results_with_timestamp, f, indent=2, default=str)
        
        print(f"💾 Test results saved to {filename}")


async def main():
    """Main function to run tests."""
    parser = argparse.ArgumentParser(description="Run VATSIM Data Collection System tests")
    parser.add_argument("--save-results", action="store_true", help="Save results to JSON file")
    parser.add_argument("--output-file", default="test_results.json", help="Output file for results")
    parser.add_argument("--test-type", choices=["unit", "integration", "e2e", "quality", "coverage", "all"], 
                       default="all", help="Type of tests to run")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.test_type == "all":
            results = await runner.run_all_tests()
        elif args.test_type == "unit":
            results = {"unit": await runner.run_unit_tests()}
        elif args.test_type == "integration":
            results = {"integration": await runner.run_integration_tests()}
        elif args.test_type == "e2e":
            results = {"e2e": await runner.run_e2e_tests()}
        elif args.test_type == "quality":
            results = {"quality": await runner.run_quality_gates()}
        elif args.test_type == "coverage":
            results = {"coverage": await runner.run_coverage_report()}
        
        runner.test_results = results
        runner.print_results()
        
        if args.save_results:
            runner.save_results(args.output_file)
        
        # Exit with appropriate code
        summary = results.get("summary", {})
        if summary.get("overall_passed", False):
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 