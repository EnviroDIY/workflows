#!/usr/bin/env python
"""
Output job matrices to GitHub outputs and artifacts.

Writes:
- JSON matrices to continuous_integration_artifacts/
- GitHub outputs for matrices
- Summary information
"""

import os
import json
from matrix_utils import save_json_file

if __name__ == "__main__":
    # Load config
    artifact_path = os.environ.get("ARTIFACT_PATH", "continuous_integration_artifacts")
    config_file = os.path.join(artifact_path, "matrix_config.json")

    with open(config_file, "r") as f:
        config = json.load(f)

    arduino_job_matrix = config["arduino_job_matrix"]
    pio_job_matrix = config["pio_job_matrix"]

    # Write matrices to JSON files
    arduino_matrix_file = os.path.join(artifact_path, "arduino_job_matrix.json")
    pio_matrix_file = os.path.join(artifact_path, "pio_job_matrix.json")

    save_json_file(arduino_matrix_file, arduino_job_matrix)
    save_json_file(pio_matrix_file, pio_job_matrix)

    print(f"Arduino job matrix saved to: {arduino_matrix_file}")
    print(f"PlatformIO job matrix saved to: {pio_matrix_file}")

    # Output to GitHub
    if "GITHUB_OUTPUT" in os.environ.keys():
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            print(
                "arduino_job_matrix={}".format(json.dumps(arduino_job_matrix)), file=fh
            )
            print("pio_job_matrix={}".format(json.dumps(pio_job_matrix)), file=fh)
        print("Outputs written to GITHUB_OUTPUT")
    else:
        print("::notice::Not running in GitHub Actions, skipping GITHUB_OUTPUT")

    # Print summary
    print("\n=== Job Matrix Summary ===")
    print(f"Arduino CLI jobs: {len(arduino_job_matrix)}")
    print(f"PlatformIO jobs: {len(pio_job_matrix)}")
    print(f"Total jobs: {len(arduino_job_matrix) + len(pio_job_matrix)}")

    if len(arduino_job_matrix) > 0:
        print("\nArduino CLI jobs:")
        for job in arduino_job_matrix:
            print(f"  - {job['job_name']}")

    if len(pio_job_matrix) > 0:
        print("\nPlatformIO jobs:")
        for job in pio_job_matrix:
            print(f"  - {job['job_name']}")
