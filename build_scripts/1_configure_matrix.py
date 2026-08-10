#!/usr/bin/env python
"""
Configure working directories and download necessary configuration files.

Sets up:
- workspace_path: The root workspace directory
- examples_path: Directory containing examples
- extras_path: Directory containing extras
- ci_path: Directory for CI artifacts
- artifact_path: Directory for generated artifacts

Downloads (if needed):
- Board conversion JSON (platformio_to_arduino_boards.json)
- Arduino CLI configuration
- PlatformIO configuration
"""

import os
import json
import requests
import shutil
from pathlib import Path
from typing import Any
from matrix_utils import print_verbose


def setup_workspace_dirs():
    """Configure and validate all workspace directories"""
    # The workspace directory
    if "GITHUB_WORKSPACE" in os.environ.keys():
        workspace_dir = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    else:
        workspace_dir = os.getcwd()

    if os.path.basename(os.path.normpath(workspace_dir)) == "continuous_integration":
        workspace_dir = os.path.dirname(workspace_dir)

    workspace_path = os.path.abspath(os.path.realpath(workspace_dir))
    print(f"Workspace Path: {workspace_path}")

    # The examples directory
    examples_dir = "./examples/"
    examples_path = os.path.join(workspace_dir, examples_dir)
    examples_path = os.path.abspath(os.path.realpath(examples_path))
    print(f"Examples Path: {examples_path}")

    # The extras directory
    extras_dir = "./extras/"
    extras_path = os.path.join(workspace_dir, extras_dir)
    extras_path = os.path.abspath(os.path.realpath(extras_path))
    print(f"Extras Path: {extras_path}")

    # The continuous integration directory
    ci_dir = "./continuous_integration/"
    ci_path = os.path.join(workspace_dir, ci_dir)
    ci_path = os.path.abspath(os.path.realpath(ci_path))
    print(f"Continuous Integration Path: {ci_path}")
    if not os.path.exists(ci_path):
        print(f"Creating the directory for CI: {ci_path}")
        os.makedirs(ci_path, exist_ok=True)

    # A directory of files to save and upload as artifacts
    artifact_dir = os.path.join(workspace_dir, "continuous_integration_artifacts")
    artifact_path = os.path.abspath(os.path.realpath(artifact_dir))
    print(f"Artifact Path: {artifact_path}")
    if not os.path.exists(artifact_dir):
        print(f"Creating the directory for artifacts: {artifact_path}")
        os.makedirs(artifact_dir)

    return {
        "workspace_path": workspace_path,
        "examples_path": examples_path,
        "extras_path": extras_path,
        "ci_path": ci_path,
        "artifact_path": artifact_path,
        "workspace_dir": workspace_dir,
    }


def download_board_conversion_file(ci_path: str, artifact_path: str):
    """Download the platformio_to_arduino_boards.json file"""
    print("Downloading board conversion file...")
    response = requests.get(
        "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/platformio_to_arduino_boards.json"
    )
    conversion_file = os.path.join(ci_path, "platformio_to_arduino_boards.json")
    with open(conversion_file, "wb") as f:
        f.write(response.content)
    # Also copy to artifacts for debugging
    shutil.copyfile(
        conversion_file,
        os.path.join(artifact_path, "platformio_to_arduino_boards.json"),
    )
    return conversion_file


def setup_arduino_cli_config(ci_path: str, artifact_path: str):
    """Setup Arduino CLI configuration file"""

    downloaded_arduino_cli_config = False
    arduino_cli_config = os.path.join(ci_path, "arduino_cli.yaml")
    arduino_cli_format = "json"

    if not os.path.isfile(arduino_cli_config):
        downloaded_arduino_cli_config = True
        print("Downloading default Arduino CLI configuration...")
        # download the default file
        response = requests.get(
            "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/arduino_cli.yaml"
        )
        # copy to the CI directory
        with open(os.path.join(ci_path, "arduino_cli.yaml"), "wb") as f:
            f.write(response.content)
        # also copy to the artifacts directory
        shutil.copyfile(
            os.path.join(ci_path, "arduino_cli.yaml"),
            os.path.join(artifact_path, "arduino_cli.yaml"),
        )

    return arduino_cli_config, arduino_cli_format, downloaded_arduino_cli_config


def setup_platformio_config(ci_path: str, artifact_path: str):
    """Setup PlatformIO configuration file"""
    from platformio.project.config import ProjectConfig

    downloaded_pio_config = False
    pio_config_file = os.path.join(ci_path, "platformio.ini")
    if not os.path.isfile(pio_config_file):
        downloaded_pio_config = True
        print("Downloading default PlatformIO configuration...")
        # download the default file
        response = requests.get(
            "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/platformio.ini"
        )
        # copy to the CI directory
        with open(os.path.join(ci_path, "platformio.ini"), "wb") as f:
            f.write(response.content)
        # also copy to the artifacts directory
        shutil.copyfile(
            os.path.join(ci_path, "platformio.ini"),
            os.path.join(artifact_path, "platformio.ini"),
        )

    pio_config = ProjectConfig(pio_config_file)

    # Load extra config if it exists
    pio_config_expanded = __import__("copy").deepcopy(pio_config)
    pio_extra_config_file = os.path.join(ci_path, "platformio_extra_flags.ini")
    if os.path.isfile(pio_extra_config_file):
        pio_config_expanded.read(pio_extra_config_file)

    # Build mapping dictionaries
    board_to_pio_env = {}
    pio_env_to_board = {}
    for pio_env_name in pio_config.envs():
        board_to_pio_env[pio_config.get("env:{}".format(pio_env_name), "board")] = (
            pio_env_name
        )
    for pio_env_name in pio_config_expanded.envs():
        pio_env_to_board[pio_env_name] = pio_config_expanded.get(
            "env:{}".format(pio_env_name), "board"
        )

    return pio_config_file, downloaded_pio_config, board_to_pio_env, pio_env_to_board


if __name__ == "__main__":
    dirs = setup_workspace_dirs()

    # Save directory config to JSON for use by other scripts
    config: dict[str, Any] = {
        "workspace_path": dirs["workspace_path"],
        "examples_path": dirs["examples_path"],
        "extras_path": dirs["extras_path"],
        "ci_path": dirs["ci_path"],
        "artifact_path": dirs["artifact_path"],
    }

    # Download board conversion file
    pio_to_acli_file = download_board_conversion_file(
        dirs["ci_path"], dirs["artifact_path"]
    )
    config["pio_to_acli_file"] = pio_to_acli_file

    # Setup Arduino CLI config
    arduino_cli_config, arduino_cli_format, downloaded_arduino_cli_config = (
        setup_arduino_cli_config(dirs["ci_path"], dirs["artifact_path"])
    )
    config["arduino_cli_config"] = arduino_cli_config
    config["arduino_cli_format"] = arduino_cli_format
    config["downloaded_arduino_cli_config"] = downloaded_arduino_cli_config

    # Setup PlatformIO config
    pio_config_file, downloaded_pio_config, board_to_pio_env, pio_env_to_board = (
        setup_platformio_config(dirs["ci_path"], dirs["artifact_path"])
    )
    config["pio_config_file"] = pio_config_file
    config["downloaded_pio_config"] = downloaded_pio_config
    config["board_to_pio_env"] = board_to_pio_env
    config["pio_env_to_board"] = pio_env_to_board

    # Save to file for next script
    config_file = os.path.join(dirs["artifact_path"], "matrix_config.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nConfiguration saved to: {config_file}")

# CSpell:ignore pio_to_acli_file
