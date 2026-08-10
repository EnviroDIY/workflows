#!/usr/bin/env python
"""
Configure CI workspace and download necessary configuration files.

This is the first step of the CI Build Pipeline. It sets up all necessary
directories and downloads configuration files needed for the build process.

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

Step 0 in the CI Build Pipeline sequence.
"""

import os
import json
import requests
import shutil
from typing import Any
from matrix_utils import get_working_directories


def load_pio_to_arduino_mapping(ci_path: str, artifact_path: str):
    """Download the platformio_to_arduino_boards.json file"""
    print("Downloading board conversion file...")
    response = requests.get(
        "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/platformio_to_arduino_boards.json"
    )
    pio_to_acli_file = os.path.join(ci_path, "platformio_to_arduino_boards.json")
    print("Saving board conversion file to: {}".format(pio_to_acli_file))
    with open(pio_to_acli_file, "wb") as f:
        f.write(response.content)
    # Also copy to artifacts for debugging
    shutil.copyfile(
        pio_to_acli_file,
        os.path.join(artifact_path, "platformio_to_arduino_boards.json"),
    )

    with open(pio_to_acli_file) as f:
        pio_to_acli = json.load(f)

    return pio_to_acli_file, pio_to_acli


def load_arduino_cli_config(ci_path: str, artifact_path: str):
    """Load or download Arduino CLI configuration file."""

    downloaded_arduino_cli_config = False
    arduino_cli_config = os.path.join(ci_path, "arduino_cli.yaml")

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
        print("Saving Arduino CLI configuration to: {}".format(arduino_cli_config))
        # also copy to the artifacts directory
        shutil.copyfile(
            os.path.join(ci_path, "arduino_cli.yaml"),
            os.path.join(artifact_path, "arduino_cli.yaml"),
        )

    return arduino_cli_config, downloaded_arduino_cli_config


def load_platformio_config(ci_path: str, artifact_path: str):
    """
    Download the PlatformIO configuration file, if necessary,
    and build mapping dictionaries for boards and environments.
    """

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
        print("Saving PlatformIO configuration to: {}".format(pio_config_file))
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
    board_to_pio_platform = {}
    pio_env_to_board = {}
    # Read the environments from the PlatformIO config and build the mappings
    # to boards and platforms.
    # NOTE: we use the unexpanded config here because we want to capture the original
    # mapping of boards to environments, not any additional environments that may
    # have been added in the extra config.
    # NOTE: In case of duplicate boards, we keep the first one we encounter,
    # which is usually the one with the most generic flags.
    for pio_env_name in pio_config.envs():
        board = pio_config.get("env:{}".format(pio_env_name), "board")
        if board not in board_to_pio_env.keys():
            board_to_pio_env[board] = pio_env_name
        if board not in board_to_pio_platform.keys():
            board_to_pio_platform[board] = pio_config.get(
                "env:{}".format(pio_env_name), "platform"
            )
    # Go in the opposite direction to map from PIO environment names to boards.
    # NOTE: for this we use the expanded config because there may be additional
    # environments that use the same board but have different flags,
    # and we want to capture all of them.
    # NOTE: PlatformIO does not allow duplicate environment names, so we can safely assume that
    # each environment name maps to a single board.
    for pio_env_name in pio_config_expanded.envs():
        pio_env_to_board[pio_env_name] = pio_config_expanded.get(
            "env:{}".format(pio_env_name), "board"
        )

    return (
        pio_config_file,
        downloaded_pio_config,
        board_to_pio_env,
        board_to_pio_platform,
        pio_env_to_board,
    )


def load_pio_tools(ci_path: str, artifact_path: str):
    """Download the platformio_platform_tools.json file"""
    print("Downloading tools file...")
    response = requests.get(
        "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/platformio_platform_tools.json"
    )
    pio_tools_file = os.path.join(ci_path, "platformio_platform_tools.json")
    print("Saving tools file to: {}".format(pio_tools_file))
    with open(pio_tools_file, "wb") as f:
        f.write(response.content)
    # Also copy to artifacts for debugging
    shutil.copyfile(
        pio_tools_file,
        os.path.join(artifact_path, "platformio_platform_tools.json"),
    )

    with open(pio_tools_file) as f:
        pio_tools = json.load(f)

    return pio_tools_file, pio_tools


if __name__ == "__main__":
    print("=" * 60)
    print("CI Build Pipeline: Step 0 - Configure Matrix Workspace")
    print("=" * 60)

    dirs = get_working_directories()

    # Save directory config to JSON for use by other scripts
    config: dict[str, Any] = {
        "workspace_path": dirs["workspace_path"],
        "examples_path": dirs["examples_path"],
        "extras_path": dirs["extras_path"],
        "ci_path": dirs["ci_path"],
        "artifact_path": dirs["artifact_path"],
    }

    # Download board conversion file
    pio_to_acli_file, pio_to_acli = load_pio_to_arduino_mapping(
        dirs["ci_path"], dirs["artifact_path"]
    )
    config["pio_to_acli_file"] = pio_to_acli_file
    config["pio_to_acli"] = pio_to_acli

    pio_tools_file, pio_tools = load_pio_tools(dirs["ci_path"], dirs["artifact_path"])
    config["pio_tools_file"] = pio_tools_file
    config["pio_tools"] = pio_tools

    # Setup Arduino CLI config
    arduino_cli_config, downloaded_arduino_cli_config = load_arduino_cli_config(
        dirs["ci_path"], dirs["artifact_path"]
    )
    config["arduino_cli_config"] = arduino_cli_config
    config["downloaded_arduino_cli_config"] = downloaded_arduino_cli_config

    # Setup PlatformIO config
    (
        pio_config_file,
        downloaded_pio_config,
        board_to_pio_env,
        board_to_pio_platform,
        pio_env_to_board,
    ) = load_platformio_config(dirs["ci_path"], dirs["artifact_path"])
    config["pio_config_file"] = pio_config_file
    config["downloaded_pio_config"] = downloaded_pio_config
    config["board_to_pio_env"] = board_to_pio_env
    config["board_to_pio_platform"] = board_to_pio_platform
    config["pio_env_to_board"] = pio_env_to_board

    # Save to file for next script
    config_file = os.path.join(dirs["artifact_path"], "matrix_config.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ Configuration saved to: {config_file}")
    print("✓ Workspace setup complete")

# CSpell:ignore pio_to_acli_file
