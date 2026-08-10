#!/usr/bin/env python
"""
Main orchestrator script for matrix generation.

This script coordinates all the matrix generation steps:
1. Configure directories and download configs
2. Parse workflow inputs
3. Build the job matrix
4. Build command blocks and job scripts
5. Output results
6. Cleanup (if local)

Usage:
    python generate_job_matrix_orchestrator.py [options]

Options:
    --no-cleanup    Don't clean up generated files when running locally
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_script(
    script_name: str, script_path: str, artifact_path: str, env: dict | None = None
):
    """Run a Python script and handle errors"""
    if env is None:
        env = os.environ.copy()

    # Ensure artifact path is set
    env["ARTIFACT_PATH"] = artifact_path

    print(f"\n{'='*60}")
    print(f"Running: {script_name}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, "-u", script_path],
        env=env,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    if result.returncode != 0:
        print(f"::error::{script_name} failed with exit code {result.returncode}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate job matrix for build_examples workflow"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't clean up generated files when running locally",
    )
    args = parser.parse_args()

    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Determine artifact path
    artifact_path = os.environ.get(
        "ARTIFACT_PATH", os.path.join(os.getcwd(), "continuous_integration_artifacts")
    )

    # Ensure artifact directory exists
    os.makedirs(artifact_path, exist_ok=True)

    print(f"Matrix Generation Orchestrator")
    print(f"Script directory: {script_dir}")
    print(f"Artifact path: {artifact_path}")

    # Run all scripts in order
    scripts = [
        ("1. Configure Matrix", "1_configure_matrix.py"),
        ("2. Parse Inputs", "2_parse_inputs.py"),
        ("3. Build Matrix", "3_build_matrix.py"),
        ("4. Build Jobs", "4_build_jobs.py"),
        ("5. Output Results", "5_output_results.py"),
    ]

    for script_name, script_filename in scripts:
        script_path = os.path.join(script_dir, script_filename)
        if not os.path.exists(script_path):
            print(f"::error::Script not found: {script_path}")
            return False

        if not run_script(script_name, script_path, artifact_path):
            return False

    # Run cleanup unless --no-cleanup flag is set
    if not args.no_cleanup:
        script_name = "6. Cleanup"
        script_path = os.path.join(script_dir, "6_cleanup.py")
        if os.path.exists(script_path):
            run_script(script_name, script_path, artifact_path)

    print(f"\n{'='*60}")
    print("Matrix generation completed successfully!")
    print(f"{'='*60}")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
