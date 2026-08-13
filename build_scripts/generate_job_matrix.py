#!/usr/bin/env python
"""
Wrapper script to run the complete matrix generation pipeline.

This script is the main entry point that the workflow should call.
It runs all matrix generation steps in sequence and handles output.

Usage:
    python generate_job_matrix.py
"""

import os
import sys
import subprocess
from build_config import get_extended_config, set_verbose_mode, print_verbose

def main():
    """Run the matrix generation pipeline"""
    print("=" * 60)
    print("Running the matrix generation pipeline")
    print("=" * 60)

    print_verbose(
        "Reading configuration from environment variables, command line arguments, and the config file..."
    )
    args = get_extended_config()
    set_verbose_mode(args.verbose)

    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Determine if we're in GitHub Actions
    in_github = "GITHUB_WORKSPACE" in os.environ

    # Prepare environment for child processes
    env = os.environ.copy()
    env["PYTHONPATH"] = script_dir + ":" + env.get("PYTHONPATH", "")

    print(f"Matrix Generation Pipeline")
    print(f"Script directory: {script_dir}")
    print(f"Artifact path: {args.artifact_path}")
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
        ("1. Configure Workspace", "1_configure_workspace.py"),
        ("2. Generate Install Scripts", "2_generate_install_scripts.py"),
        ("3. Build Matrix", "3_build_matrix.py"),
        ("4. Build Jobs", "4_build_jobs.py"),
    ]
    for script_name, script_filename in scripts:
        script_path = os.path.join(script_dir, script_filename)

        if not os.path.exists(script_path):
            print(f"ERROR: Script not found: {script_path}")
            print(f"Trying to download from GitHub...\n")

            # Try to download from GitHub
            url = f"https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/{script_filename}"
            download_result = subprocess.run(
                ["curl", "-SL", url, "-o", script_path],
                env=env,
            )

            if download_result.returncode != 0:
                print(f"ERROR: Could not download {script_filename}")
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
        print("Running: 5_cleanup.py")
        print(f"{'='*60}\n")

        cleanup_script = os.path.join(script_dir, "5_cleanup.py")
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
