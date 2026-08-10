#!/usr/bin/env python
"""
Clean up generated files when running locally (not in GitHub Actions).

Removes:
- Continuous integration directory
- Generated artifacts
- Downloaded config files (conditionally based on configuration flags)
"""

import os
import json
import shutil

if __name__ == "__main__":
    # Only clean up if NOT in GitHub Actions
    if "GITHUB_WORKSPACE" not in os.environ.keys():
        artifact_path = os.environ.get(
            "ARTIFACT_PATH", "continuous_integration_artifacts"
        )
        ci_path = os.environ.get("CI_PATH", "continuous_integration")

        print("Running locally - cleaning up generated files...")

        # Load configuration to check which files were downloaded
        config = {}
        config_file = os.path.join(artifact_path, "matrix_config.json")
        if os.path.isfile(config_file):
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")

        # Remove artifact directory
        if os.path.exists(artifact_path):
            try:
                print(f"Removing artifact directory: {artifact_path}")
                shutil.rmtree(artifact_path)
            except Exception as e:
                print(f"Warning: Could not remove {artifact_path}: {e}")

        # Remove CI directory and downloaded files
        if os.path.exists(ci_path):
            files_to_remove = [
                os.path.join(ci_path, "platformio_to_arduino_boards.json"),
            ]

            # Only remove arduino_cli.yaml if it was downloaded
            if config.get("downloaded_arduino_cli_config", False):
                files_to_remove.append(os.path.join(ci_path, "arduino_cli.yaml"))

            # Only remove platformio.ini if it was downloaded
            if config.get("downloaded_pio_config", False):
                files_to_remove.append(os.path.join(ci_path, "platformio.ini"))

            for file_path in files_to_remove:
                if os.path.exists(file_path):
                    try:
                        print(f"Removing file: {file_path}")
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Warning: Could not remove {file_path}: {e}")

            # Try to remove CI directory if empty
            try:
                os.rmdir(ci_path)
                print(f"Removed empty CI directory: {ci_path}")
            except Exception as e:
                print(f"CI directory not empty, leaving it: {e}")

        print("Cleanup complete")
    else:
        print("Running in GitHub Actions - skipping cleanup")
