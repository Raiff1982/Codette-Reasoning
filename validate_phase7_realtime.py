#!/usr/bin/env python3
"""Phase 7 Real-Time Validation Against Running Web Server

Tests all three routing paths (SIMPLE/MEDIUM/COMPLEX) against the running web server.
Compares actual latencies versus estimates and validates component activation.

Usage:
    python validate_phase7_realtime.py

Prerequisites:
    - codette_web.bat must be running at http://localhost:7860
    - Web server must show "Phase 7 Executive Controller initialized"
"""

import requests
import time
import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Test queries organized by complexity
TEST_QUERIES = {
    "SIMPLE": [
        {
            "query": "What is the speed of light?",
            "expected_latency_ms": (150, 250),  # 150-250ms
            "expect_components": False,  # All should be false
        },
        {
            "query": "Define entropy",
            "expected_latency_ms": (150, 250),
            "expect_components": False,
        },
    ],
    "MEDIUM": [
        {
            "query": "How does quantum mechanics relate to consciousness?",
            "expected_latency_ms": (800, 1200),  # 800-1200ms
            "expect_components": True,  # Some should be true
            "min_components": 3,  # At least 3 should be active
        },
        {
            "query": "What are the implications of artificial intelligence for society?",
            "expected_latency_ms": (800, 1200),
            "expect_components": True,
            "min_components": 3,
        },
    ],
    "COMPLEX": [
        {
            "query": "Can machines be truly conscious? And how should we ethically govern AI?",
            "expected_latency_ms": (2000, 3500),  # 2000-3500ms
            "expect_components": True,
            "expect_all": True,  # All components should be activated
        },
    ],
}


class Phase7Validator:
    """Validates Phase 7 routing in real-time against running web server."""

    def __init__(self, server_url: str = "http://localhost:7860"):
        self.server_url = server_url
        self.results = {
            "SIMPLE": [],
            "MEDIUM": [],
            "COMPLEX": [],
        }
        self.validation_start = None
        self.validation_end = None

    def is_server_running(self) -> bool:
        """Check if web server is running."""
        try:
            response = requests.get(f"{self.server_url}/api/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def query_server(
        self, query: str, complexity: str
    ) -> Optional[Dict[str, Any]]:
        """Send query to web server and capture response with metadata."""

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.server_url}/api/chat",
                json={"message": query, "complexity_hint": complexity},
                timeout=10,
            )

            actual_latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()

                # Try to extract phase7_routing from response
                phase7_routing = None
                if isinstance(data, dict):
                    # Direct format
                    if "phase7_routing" in data:
                        phase7_routing = data.get("phase7_routing")
                    # Nested in metadata
                    elif "metadata" in data and isinstance(data["metadata"], dict):
                        phase7_routing = data["metadata"].get("phase7_routing")

                return {
                    "success": True,
                    "response": data,
                    "actual_latency_ms": actual_latency_ms,
                    "phase7_routing": phase7_routing,
                    "status_code": response.status_code,
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "actual_latency_ms": actual_latency_ms,
                    "error": response.text,
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout (10s)",
                "actual_latency_ms": (time.time() - start_time) * 1000,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "actual_latency_ms": (time.time() - start_time) * 1000,
            }

    def validate_latency(
        self, actual_ms: float, expected_range: tuple, complexity: str
    ) -> tuple[bool, str]:
        """Check if actual latency falls within expected range."""
        min_ms, max_ms = expected_range

        if min_ms <= actual_ms <= max_ms:
            return True, f"OK ({actual_ms:.0f}ms within {min_ms}-{max_ms}ms)"
        elif actual_ms < min_ms:
            return False, f"FAST ({actual_ms:.0f}ms < {min_ms}ms expected)"
        else:
            return False, f"SLOW ({actual_ms:.0f}ms > {max_ms}ms expected)"

    def validate_components(
        self,
        phase7_routing: Optional[Dict],
        expect_components: bool,
        expect_all: bool = False,
        min_components: int = 0,
    ) -> tuple[bool, str]:
        """Validate component activation matches expectations."""

        if not phase7_routing:
            return False, "phase7_routing metadata missing"

        if "components_activated" not in phase7_routing:
            return False, "components_activated missing from metadata"

        components = phase7_routing["components_activated"]
        active_count = sum(1 for v in components.values() if v)
        total_count = len(components)

        if expect_all:
            if active_count == total_count:
                return True, f"OK (all {total_count} components activated)"
            else:
                return (
                    False,
                    f"NOT OK ({active_count}/{total_count} activated, expected all)",
                )

        if expect_components:
            if active_count >= min_components:
                return (
                    True,
                    f"OK ({active_count}/{total_count} activated, >= {min_components} required)",
                )
            else:
                return (
                    False,
                    f"NOT OK ({active_count}/{total_count} activated, < {min_components} required)",
                )

        # expect_components = False (SIMPLE)
        if active_count == 0:
            return True, f"OK (all {total_count} components skipped)"
        else:
            return False, f"NOT OK ({active_count}/{total_count} activated, expected none)"

    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{'='*75}")
        print(f"  {title}")
        print(f"{'='*75}\n")

    def run_validation(self) -> bool:
        """Run full Phase 7 validation suite."""

        self.print_header("Phase 7 Real-Time Validation")

        # Check server
        print("Step 1: Checking if web server is running...")
        if not self.is_server_running():
            print("[ERROR] Web server not responding at http://localhost:7860")
            print("        Please start codette_web.bat first")
            return False
        print("[OK] Web server is running\n")

        self.validation_start = datetime.now()

        # Test each complexity level
        all_passed = True
        for complexity in ["SIMPLE", "MEDIUM", "COMPLEX"]:
            self.print_header(f"Testing {complexity} Routing Path")

            for test_case in TEST_QUERIES[complexity]:
                query = test_case["query"]
                print(f"Query: {query}")

                # Send query
                result = self.query_server(query, complexity)

                if not result["success"]:
                    print(f"  [FAIL] Server error: {result.get('error')}")
                    all_passed = False
                    continue

                # Check latency
                latency_ok, latency_msg = self.validate_latency(
                    result["actual_latency_ms"],
                    test_case["expected_latency_ms"],
                    complexity,
                )
                latency_status = "[OK]" if latency_ok else "[SLOW/FAST]"
                print(f"  Latency:  {latency_status} {latency_msg}")
                if not latency_ok:
                    all_passed = False

                # Check components
                components_ok, components_msg = self.validate_components(
                    result["phase7_routing"],
                    test_case.get("expect_components", False),
                    test_case.get("expect_all", False),
                    test_case.get("min_components", 0),
                )
                components_status = "[OK]" if components_ok else "[FAIL]"
                print(f"  Components: {components_status} {components_msg}")
                if not components_ok:
                    all_passed = False

                # Extract reasoning if available
                if (
                    result["phase7_routing"]
                    and "reasoning" in result["phase7_routing"]
                ):
                    reasoning = result["phase7_routing"]["reasoning"]
                    print(f"  Routing: {reasoning}")

                # Store result
                self.results[complexity].append(
                    {
                        "query": query,
                        "latency_ok": latency_ok,
                        "actual_latency_ms": result["actual_latency_ms"],
                        "components_ok": components_ok,
                        "phase7_routing": result["phase7_routing"],
                    }
                )

                print()

        self.validation_end = datetime.now()
        return all_passed

    def generate_report(self) -> str:
        """Generate comprehensive validation report."""

        report_lines = []

        report_lines.append("\n" + "=" * 75)
        report_lines.append("  PHASE 7 VALIDATION REPORT")
        report_lines.append("=" * 75)

        # Summary
        report_lines.append(f"\nValidation Time: {self.validation_start}")
        report_lines.append(f"Duration: {self.validation_end - self.validation_start}")

        # Results by complexity
        for complexity in ["SIMPLE", "MEDIUM", "COMPLEX"]:
            results = self.results[complexity]
            if not results:
                continue

            report_lines.append(f"\n{complexity} Queries:")
            report_lines.append("-" * 75)

            latencies = [
                r["actual_latency_ms"] for r in results
            ]
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)

            report_lines.append(f"  Count: {len(results)}")
            report_lines.append(
                f"  Latencies: min={min_latency:.0f}ms, avg={avg_latency:.0f}ms, max={max_latency:.0f}ms"
            )

            latency_passed = sum(
                1 for r in results if r["latency_ok"]
            ) / len(results)
            components_passed = sum(1 for r in results if r["components_ok"]) / len(
                results
            )

            report_lines.append(
                f"  Latency Validation: {latency_passed:.0%} passed"
            )
            report_lines.append(
                f"  Components Validation: {components_passed:.0%} passed"
            )

        # Validation checklist
        report_lines.append("\n" + "=" * 75)
        report_lines.append("VALIDATION CHECKLIST")
        report_lines.append("=" * 75 + "\n")

        checklist = [
            (
                "Server launches with Phase 7 initialized",
                self.is_server_running(),
            ),
            (
                "SIMPLE queries run in 150-250ms range",
                all(r["latency_ok"]
                    for r in self.results["SIMPLE"]),
            ),
            (
                "MEDIUM queries run in 800-1200ms range",
                all(r["latency_ok"]
                    for r in self.results["MEDIUM"]),
            ),
            (
                "COMPLEX queries run in 2000-3500ms range",
                all(r["latency_ok"]
                    for r in self.results["COMPLEX"]),
            ),
            (
                "SIMPLE queries have zero components activated",
                all(r["components_ok"]
                    for r in self.results["SIMPLE"]),
            ),
            (
                "MEDIUM queries have selective components activated",
                all(r["components_ok"]
                    for r in self.results["MEDIUM"]),
            ),
            (
                "COMPLEX queries have all components activated",
                all(r["components_ok"]
                    for r in self.results["COMPLEX"]),
            ),
        ]

        for check, passed in checklist:
            status = "[OK]" if passed else "[FAIL]"
            report_lines.append(f"  {status} {check}")

        # Overall result
        all_passed = all(passed for _, passed in checklist)
        report_lines.append("\n" + "=" * 75)
        if all_passed:
            report_lines.append("RESULT: ALL VALIDATION CHECKS PASSED [OK]")
        else:
            report_lines.append("RESULT: SOME VALIDATION CHECKS FAILED [FAIL]")
        report_lines.append("=" * 75 + "\n")

        return "\n".join(report_lines)


def main():
    """Run Phase 7 real-time validation."""
    validator = Phase7Validator()

    # Run validation
    if not validator.run_validation():
        print("[ERROR] Validation encountered issues")
        sys.exit(1)

    # Generate and print report
    report = validator.generate_report()
    print(report)

    # Save report to file
    report_path = Path("phase7_validation_report.txt")
    report_path.write_text(report)
    print(f"Validation report saved to: {report_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
