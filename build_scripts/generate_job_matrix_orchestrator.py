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
from build_config import get_extended_config, set_verbose_mode, print_verbose

def run_script(
    script_name: str, script_path: str, artifact_path: str, env: dict | None = None
):
    """Run a Python script and handle errors"""
    if env is None:
        env = os.environ.copy()

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
    print("=" * 60)
    print("Matrix Generation Orchestrator")
    print("=" * 60)

    print_verbose(
        "Reading configuration from environment variables, command line arguments, and the config file..."
    )
    args = get_extended_config()
    set_verbose_mode(args.verbose)

    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Run all scripts in order
    scripts = [
        ("1. Configure Workspace", "1_configure_workspace.py"),
        ("2. Generate Install Scripts", "2_generate_install_scripts.py"),
        ("3. Build Matrix", "3_build_matrix.py"),
        ("4. Build Jobs", "4_build_jobs.py"),
    ]

    for script_name, script_filename in scripts:
        script_path = os.path.join(script_dir, script_filename)

        if not os.path.exists(script_path):
            print(f"::error::Script not found: {script_path}")
            return False

        if not run_script(script_name, script_path, args.artifact_path):
            return False

    script_name = "5. Cleanup"
    script_path = os.path.join(script_dir, "5_cleanup.py")
    if os.path.exists(script_path):
        run_script(script_name, script_path, args.artifact_path)

    print(f"\n{'='*60}")
    print("Matrix generation completed successfully!")
    print(f"{'='*60}\n")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
