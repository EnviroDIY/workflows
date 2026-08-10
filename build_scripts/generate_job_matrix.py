#!/usr/bin/env python
"""
Wrapper script to run the complete matrix generation pipeline.

This script is the main entry point that the workflow should call.
It runs all matrix generation steps in sequence and handles output.

Usage:
    python generate_job_matrix.py

Environment Variables:
    BOARDS_TO_BUILD: Comma-separated list of boards to build (optional)
    BOARDS_TO_IGNORE: Comma-separated list of boards to ignore (optional)
    EXAMPLES_TO_BUILD: Comma-separated list of examples to build (optional)
    EXAMPLES_TO_IGNORE: Comma-separated list of examples to ignore (optional)
    RUNNER_DEBUG: Set to "1" for verbose output (optional)
    GITHUB_WORKSPACE: Automatically set in GitHub Actions (optional)
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Run the matrix generation pipeline"""
    # Determine if we're in GitHub Actions
    in_github = "GITHUB_WORKSPACE" in os.environ

    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Set artifact path for all scripts
    artifact_path = "continuous_integration_artifacts"
    os.makedirs(artifact_path, exist_ok=True)

    # Prepare environment for child processes
    env = os.environ.copy()
    env["ARTIFACT_PATH"] = os.path.abspath(artifact_path)
    env["PYTHONPATH"] = script_dir + ":" + env.get("PYTHONPATH", "")

    print(f"Matrix Generation Pipeline")
    print(f"Script directory: {script_dir}")
    print(f"Artifact path: {env['ARTIFACT_PATH']}")
    print(f"Running in GitHub Actions: {in_github}\n")

    # Check for custom generator first
    if os.path.exists("continuous_integration/generate_job_matrix.py"):
        print(
            "Found custom matrix generator at continuous_integration/generate_job_matrix.py"
        )
        print("Using custom generator instead of modular scripts\n")

        # Run custom generator
        result = subprocess.run(
            [sys.executable, "-u", "continuous_integration/generate_job_matrix.py"],
            env=env,
        )
        return result.returncode

    # Run modular scripts
    scripts = [
        "1_configure_matrix.py",
        "2_parse_inputs.py",
        "3_build_matrix.py",
        "4_build_jobs.py",
        "5_output_results.py",
    ]

    for script_name in scripts:
        script_path = os.path.join(script_dir, script_name)

        if not os.path.exists(script_path):
            print(f"ERROR: Script not found: {script_path}")
            print(f"Trying to download from GitHub...\n")

            # Try to download from GitHub
            url = f"https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/{script_name}"
            download_result = subprocess.run(
                ["curl", "-SL", url, "-o", script_path],
                env=env,
            )

            if download_result.returncode != 0:
                print(f"ERROR: Could not download {script_name}")
                return 1

        print(f"\n{'='*60}")
        print(f"Running: {script_name}")
        print(f"{'='*60}\n")

        result = subprocess.run(
            [sys.executable, "-u", script_path],
            env=env,
            cwd=script_dir,
        )

        if result.returncode != 0:
            print(f"\nERROR: {script_name} failed with exit code {result.returncode}")
            return 1

    # Run cleanup only if not in GitHub Actions
    if not in_github:
        print(f"\n{'='*60}")
        print("Running: 6_cleanup.py")
        print(f"{'='*60}\n")

        cleanup_script = os.path.join(script_dir, "6_cleanup.py")
        if os.path.exists(cleanup_script):
            subprocess.run(
                [sys.executable, "-u", cleanup_script],
                env=env,
                cwd=script_dir,
            )
    else:
        print("\nSkipping cleanup (running in GitHub Actions)")

    print(f"\n{'='*60}")
    print("Matrix generation completed successfully!")
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
