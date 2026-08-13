#!/usr/bin/env python
"""
Clean up generated files when running locally (not in GitHub Actions).

Removes:
- Continuous integration directory
- Generated artifacts
- Downloaded config files (conditionally based on configuration flags)
"""

# %%
import os
import json
import shutil
from build_config import get_extended_config, set_verbose_mode, print_verbose

# %%
if __name__ == "__main__":
    # Only clean up if NOT in GitHub Actions
    if "GITHUB_WORKSPACE" not in os.environ.keys():

        print_verbose(
            "Reading configuration from environment variables, command line arguments, and the config file..."
        )
        args = get_extended_config()
        set_verbose_mode(args.verbose)

        print("Running locally - cleaning up generated files...")

        if os.path.exists(args.ci_path):
            files_to_remove = []
            # Only remove arduino_cli.yaml if it was downloaded
            if args.downloaded_arduino_cli_config:
                files_to_remove.append(os.path.join(args.ci_path, "arduino_cli.yaml"))

            # Only remove platformio.ini if it was downloaded
            if args.downloaded_pio_config:
                files_to_remove.append(os.path.join(args.ci_path, "platformio.ini"))

            for file_path in files_to_remove:
                if os.path.exists(file_path):
                    try:
                        print(f"Removing file: {file_path}")
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Warning: Could not remove {file_path}: {e}")

            # remove the whole directory if it 's now empty
            try:
                print(f"Removing {args.ci_path} if it's empty")
                os.rmdir(args.ci_path)
            except Exception as e:
                print(f"Warning: Could not remove {args.ci_path}: {e}")

        # Remove the artifact directory regardless of whether it is empty or not.
        if args.cleanup and os.path.exists(args.artifact_path):
            try:
                print(
                    f"Removing artifact directory, empty or not: {args.artifact_path}"
                )
                shutil.rmtree(args.artifact_path)
            except Exception as e:
                print(f"Warning: Could not remove {args.artifact_path}: {e}")

        print("Cleanup complete")
    else:
        print("Running in GitHub Actions - skipping cleanup")
