#!/usr/bin/env python
# %%
from collections import OrderedDict
import json
import shutil
import re
from typing import List
from platformio.project.config import ProjectConfig
import re
import os
import copy
from pathlib import Path
import requests


# %%
# Some working directories

# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys():
    workspace_dir = os.environ.get("GITHUB_WORKSPACE")
else:
    workspace_dir = os.getcwd()
workspace_path = os.path.abspath(os.path.realpath(workspace_dir))
print(f"Workspace Path: {workspace_path}")

# The continuous integration directory
ci_dir = "./continuous_integration/"
ci_path = os.path.join(workspace_dir, ci_dir)
ci_path = os.path.abspath(os.path.realpath(ci_path))
print(f"Continuous Integration Path: {ci_path}")

# A directory of files to save and upload as artifacts to use in future jobs
artifact_dir = os.path.join(
    os.path.join(workspace_dir, "continuous_integration_artifacts")
)
artifact_path = os.path.abspath(os.path.realpath(artifact_dir))
print(f"Artifact Path: {artifact_path}")

if not os.path.exists(artifact_dir):
    print(f"Creating the directory for artifacts: {artifact_path}")
    os.makedirs(artifact_dir)

compilers = ["Arduino CLI", "PlatformIO"]


# %%
# Get files linking boards and enviroments
os.makedirs(ci_path, exist_ok=True)
response = requests.get(
    "https://raw.githubusercontent.com/EnviroDIY/workflows/main/scripts/platformio_to_arduino_boards.json"
)
with open(os.path.join(ci_path, "platformio_to_arduino_boards.json"), "wb") as f:
    f.write(response.content)
response = requests.get(
    "https://raw.githubusercontent.com/EnviroDIY/workflows/main/scripts/platformio_platform_tools.json"
)
with open(os.path.join(ci_path, "platformio_platform_tools.json"), "wb") as f:
    f.write(response.content)

# Translation between board names on PlatformIO and the Arduino CLI
with open(os.path.join(ci_path, "platformio_to_arduino_boards.json")) as f:
    pio_to_acli = json.load(f)
# Tools per platform
with open(os.path.join(ci_path, "platformio_platform_tools.json")) as f:
    platformio_platform_tools = json.load(f)


# %%
# read configurations based on existing files and environment variables

# Arduino CLI configurations - always use the standard one here
if "GITHUB_WORKSPACE" in os.environ.keys():
    arduino_cli_config = os.path.join(workspace_dir, "arduino_cli.yaml")
else:
    arduino_cli_config = os.path.join(ci_dir, "arduino_cli_local.yaml")

# PlatformIO configurations - either the standard one or a found one
default_pio_config_file = False
pio_config_file = os.path.join(ci_path, "platformio.ini")
if not os.path.isfile(pio_config_file):
    response = requests.get(
        "https://raw.githubusercontent.com/EnviroDIY/workflows/main/scripts/platformio.ini"
    )
    os.makedirs(ci_path, exist_ok=True)
    with open(os.path.join(ci_path, "platformio.ini"), "wb") as f:
        f.write(response.content)
    default_pio_config_file = True

pio_config = ProjectConfig(pio_config_file)
board_to_pio_env = {}
board_to_pio_platform = {}
for pio_env_name in pio_config.envs():
    board_to_pio_env[pio_config.get("env:{}".format(pio_env_name), "board")] = (
        pio_env_name
    )
    board_to_pio_platform[pio_config.get("env:{}".format(pio_env_name), "board")] = (
        pio_config.get("env:{}".format(pio_env_name), "platform")
    )

# %%

if "BOARDS_TO_BUILD" in os.environ.keys() and os.environ.get("BOARDS_TO_BUILD") not in [
    "all",
    "",
]:
    boards = os.environ.get("BOARDS_TO_BUILD").split(",")
    use_pio_config_file = False
else:
    boards = list(board_to_pio_env.keys())
    use_pio_config_file = True

arduino_cli_cores = list(
    OrderedDict.fromkeys(
        [pio_to_acli[board]["fqbn"].rsplit(":", 1)[0] for board in boards]
    )
)
pio_platforms = list(
    OrderedDict.fromkeys([board_to_pio_platform[board] for board in boards])
)


# %%
# helper functions to create commands


def create_arduino_cli_command(core_name: str) -> str:
    arduino_command_args = [
        "arduino-cli",
        "--config-file",
        arduino_cli_config,
        "core",
        "install",
        core_name,
    ]
    return " ".join(arduino_command_args)


def create_pio_ci_command(
    platform_name: str,
    is_tool: bool = False,
) -> str:
    pio_command_args = [
        "pio",
        "pkg",
        "install",
        "-g",
        "--tool" if is_tool else "--platform",
        platform_name,
    ]
    return " ".join(pio_command_args)


def add_log_to_command(command: str, group_title: str) -> List:
    command_list = []
    command_list.append('\necho "::group::{}"'.format(group_title))
    command_list.append(f'echo "\\e[32m{group_title}\\e[0m"')
    command_list.append(command)
    command_list.append('echo "::endgroup::"\n')
    return command_list


# %%
# write the bash file for the ArduinoCLI
bash_file_name = "install-platforms-arduino-cli.sh"
print(f"Wrinting bash file to {os.path.join(artifact_path, bash_file_name)}")
bash_out = open(os.path.join(artifact_path, bash_file_name), "w+")
bash_out.write("#!/bin/bash\n\n")
bash_out.write(
    """
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

echo "\\e[32mCurrent Arduino CLI version:\\e[0m"
arduino-cli version

echo "\\e[32mUpdating the core index\\e[0m"
arduino-cli --config-file arduino_cli.yaml core update-index
"""
)

for core in arduino_cli_cores:
    install_command = create_arduino_cli_command(
        core_name=core,
    )
    command_with_log = add_log_to_command(
        install_command, core.replace(":", " ").title()
    )
    bash_out.write("\n".join(command_with_log))
bash_out.write(
    """

echo "\\e[32mUpdating the core index\\e[0m"
arduino-cli --config-file arduino_cli.yaml core update-index

echo "\\e[32mUpgrading all cores\\e[0m"
arduino-cli --config-file arduino_cli.yaml core upgrade

echo "\\e[32mCurrently installed cores:\\e[0m"
arduino-cli --config-file arduino_cli.yaml core list
"""
)
bash_out.close()

# %%

# %%
# write the bash file for PlatformIO
bash_file_name = "install-platforms-platformio.sh"
print(f"Wrinting bash file to {os.path.join(artifact_path, bash_file_name)}")
bash_out = open(os.path.join(artifact_path, bash_file_name), "w+")
bash_out.write("#!/bin/bash\n\n")
bash_out.write(
    """
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

echo "\\e[32mCurrent PlatformIO version:\\e[0m"
pio --version
"""
)
for platform in pio_platforms:
    install_command = create_pio_ci_command(platform_name=platform, is_tool=False)
    for tool in platformio_platform_tools[platform]["tools"]:
        install_command += "\n" + create_pio_ci_command(
            platform_name=tool, is_tool=True
        )
    command_with_log = add_log_to_command(
        install_command, platformio_platform_tools[platform]["name"]
    )
    bash_out.write("\n".join(command_with_log))
bash_out.write(
    """

echo "::group::Package List"
echo "\\e[32mCurrently installed packages:\\e[0m"
pio pkg list -g -v
echo "::endgroup::"
"""
)
bash_out.close()


# %%
if "GITHUB_WORKSPACE" not in os.environ.keys():
    try:
        print("Deleting artifact directory")
        shutil.rmtree(artifact_dir)
    except:
        pass
    try:
        print("Deleting default_pio_config_file")
        os.remove(
            os.path.join(ci_path, "platformio_platform_tools.json")
        )  # remove downloaded file
        os.remove(
            os.path.join(ci_path, "platformio_to_arduino_boards.json")
        )  # remove downloaded file
        os.rmdir(ci_path)  # remove dir if empty
    except:
        pass

# %%
