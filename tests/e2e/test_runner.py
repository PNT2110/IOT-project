"""E2E Test Runner CLI.

Can be executed via:
    python -m tests.e2e.test_runner [--tier {1,2,3,4,all}] [-v]
or directly with pytest:
    pytest tests/e2e/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def run_e2e_tests(tier: str = "all", verbose: bool = True) -> int:
    """Run E2E test suites for a specific tier or all tiers."""
    e2e_dir = Path(__file__).resolve().parent
    args = []
    if verbose:
        args.append("-v")
        
    tier_files = {
        "1": [str(e2e_dir / "test_tier1_feature_coverage.py")],
        "2": [str(e2e_dir / "test_tier2_boundary_corner.py")],
        "3": [str(e2e_dir / "test_tier3_cross_feature.py")],
        "4": [str(e2e_dir / "test_tier4_scenarios.py")],
        "5": [str(e2e_dir / "test_tier5_adversarial_hardening.py")],
        "all": [str(e2e_dir)],
    }
    
    target_files = tier_files.get(str(tier).lower(), [str(e2e_dir)])
    args.extend(target_files)
    
    print(f"=== Running E2E Test Suite [Tier: {tier}] ===")
    return pytest.main(args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E2E Test Runner for IoT Drone Zone Management System")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "5", "all"], default="all", help="Target test tier")
    parser.add_argument("-v", "--verbose", action="store_true", default=True, help="Verbose pytest output")
    cli_args = parser.parse_args()
    
    sys.exit(run_e2e_tests(cli_args.tier, cli_args.verbose))
