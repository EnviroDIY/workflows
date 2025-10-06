#!/usr/bin/env python
# %%
import os
from collections import OrderedDict
from typing import List
import json
import shutil
import requests

from platformio.project.config import ProjectConfig

# %%
# set verbose
use_verbose = False
if "RUNNER_DEBUG" in os.environ.keys() and os.environ["RUNNER_DEBUG"] == "1":
    use_verbose = True


# %%
# Some working directories

# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys():
    workspace_dir = os.environ.get("GITHUB_WORKSPACE")
else:
    workspace_dir = os.getcwd()
workspace_path = os.path.abspath(os.path.realpath(workspace_dir))
print(f"Workspace Path: {workspace_path}")


# %%
# The continuous integration directory
ci_dir = "./continuous_integration/"
ci_path = os.path.join(workspace_dir, ci_dir)
ci_path = os.path.abspath(os.path.realpath(ci_path))
print(f"Continuous Integration Path: {ci_path}")
if not os.path.exists(ci_path):
    print(f"Creating the directory for CI: {ci_path}")
    os.makedirs(ci_path, exist_ok=True)

# A directory of files to save and upload as artifacts to use in future jobs
artifact_dir = os.path.join(
    os.path.join(workspace_dir, "continuous_integration_artifacts")
)
artifact_path = os.path.abspath(os.path.realpath(artifact_dir))
print(f"Artifact Path: {artifact_path}")
if not os.path.exists(artifact_dir):
    print(f"Creating the directory for artifacts: {artifact_path}")
    os.makedirs(artifact_dir)


# %%
# Pull files to convert between boards and platforms and FQBNs

# Translation between board names on PlatformIO and the Arduino CLI
response = requests.get(
    "https://raw.githubusercontent.com/EnviroDIY/workflows/main/scripts/platformio_to_arduino_boards.json"
)
with open(os.path.join(ci_path, "platformio_to_arduino_boards.json"), "wb") as f:
    f.write(response.content)
with open(os.path.join(ci_path, "platformio_to_arduino_boards.json")) as f:
    pio_to_acli = json.load(f)

# Tools per platform
response = requests.get(
    "https://raw.githubusercontent.com/EnviroDIY/workflows/main/scripts/platformio_platform_tools.json"
)
with open(os.path.join(ci_path, "platformio_platform_tools.json"), "wb") as f:
    f.write(response.content)
with open(os.path.join(ci_path, "platformio_platform_tools.json")) as f:
    platformio_platform_tools = json.load(f)


# %%
# read configurations based on existing files and environment variables

# Arduino CLI configuration
# Always use the generic one from the shared workflow repository
if "GITHUB_WORKSPACE" in os.environ.keys():
    arduino_cli_config = os.path.join(ci_path, "arduino_cli.yaml")
    if not os.path.isfile(arduino_cli_config):
        # download the default file
        response = requests.get(
            "https://raw.githubusercontent.com/EnviroDIY/workflows/main/scripts/arduino_cli.yaml"
        )
        # copy to the CI directory
        with open(os.path.join(ci_path, "arduino_cli.yaml"), "wb") as f:
            f.write(response.content)
        # also copy to the artifacts directory
        shutil.copyfile(
            os.path.join(ci_path, "arduino_cli.yaml"),
            os.path.join(artifact_path, "arduino_cli.yaml"),
        )
else:
    arduino_cli_config = os.path.join(ci_dir, "arduino_cli_local.yaml")

# PlatformIO configuration
# If one exists in a "continuous_integration" subfolder of the repository, use it.
# Otherwise, use the generic one from the shared workflow repository
default_pio_config_file = False
pio_config_file = os.path.join(ci_path, "platformio.ini")
if not os.path.isfile(pio_config_file):
    # download the default file
    response = requests.get(
        "https://raw.githubusercontent.com/EnviroDIY/workflows/main/scripts/platformio.ini"
    )
    # make a directory for it and copy it there
    with open(os.path.join(ci_path, "platformio.ini"), "wb") as f:
        f.write(response.content)
    # also copy to the artifacts directory
    shutil.copyfile(
        os.path.join(ci_path, "platformio.ini"),
        os.path.join(artifact_path, "platformio.ini"),
    )
    # mark we're using default
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
# Parse the boards to build
if "BOARDS_TO_BUILD" in os.environ.keys() and os.environ.get("BOARDS_TO_BUILD") not in [
    "all",
    "",
]:
    boards = [board.strip() for board in os.environ.get("BOARDS_TO_BUILD").split(",")]
    if use_verbose:
        print("::debug::Building only boards specified in yaml.")
        print(f"::debug::{os.environ.get("BOARDS_TO_BUILD")}")
else:
    boards = list(board_to_pio_env.keys())
    if use_verbose:
        print("::debug::Building all boards available in the platformio.ini file.")
        print(f"::debug::{board_to_pio_env.keys()}")

# remove any ignored boards from the list
if "BOARDS_TO_IGNORE" in os.environ.keys() and os.environ.get(
    "BOARDS_TO_IGNORE"
) not in [
    "",
]:
    if use_verbose:
        print("::debug::Ignoring boards specified in yaml.")
        print(f"::debug::{os.environ.get("BOARDS_TO_IGNORE")}")
    boards = [
        board
        for board in boards
        if board
        not in [
            board_.strip() for board_ in os.environ.get("BOARDS_TO_IGNORE").split(",")
        ]
    ]

# Make sure we have an equivalent Arduino FQBN (and thus core) or PlatformIO environment for all requested boards
for board in boards:
    if board not in pio_to_acli.keys():
        print(
            f"""::error:: file=platformio_to_arduino_boards.json,title=No matching Arduino board::
Cannot find matching Arduino FQBN for {board}.
No core will be installed or cached for this board.
Please check the spelling of your board name or add an entry to the Arduino/PlatformIO board conversion file."""
        )
        boards.remove(board)
    if board not in board_to_pio_platform.keys():
        print(
            f"""::warning file=platformio.ini,title=No PlatformIO Environment::
No matching environment was found in the platformio.ini file for {board}.
No platforms or tools will be installed or cached for this board.
Please check the spelling of your board name or add an entry to your platformio.ini if this is not your expected behavior."""
        )

# convert the list of boards into a list of cores and platforms to install
arduino_cli_cores = list(
    OrderedDict.fromkeys(
        [pio_to_acli[board]["fqbn"].rsplit(":", 1)[0] for board in boards]
    )
)
# if EnviroDIY:samd is in the list, also add adafruit:samd (a dependency of EnviroDIY:samd
if "EnviroDIY:samd" in arduino_cli_cores and "adafruit:samd" not in arduino_cli_cores:
    arduino_cli_cores.append("adafruit:samd")
pio_platforms = list(
    OrderedDict.fromkeys([board_to_pio_platform[board] for board in boards])
)

# print out the list of platforms/cores
print("The following PlatformIO platforms will be installed:")
print(pio_platforms)


print("The following Arduino cores will be installed:")
print(arduino_cli_cores)


# %%
# helper functions to create commands
def create_arduino_cli_core_command(core_name: str) -> str:
    arduino_command_args = [
        "arduino-cli",
        "--config-file",
        f'"{arduino_cli_config}"',
        "core",
        "install",
        core_name,
    ]
    return " ".join(arduino_command_args)


def create_pio_ci_core_command(
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


def add_log_to_core_command(command: str, group_title: str) -> List:
    command_list = []
    command_list.append('\necho "::group::{}"'.format(group_title))
    command_list.append(f'echo "\\e[32m{group_title}\\e[0m"')
    command_list.append(command)
    command_list.append('echo "::endgroup::"\n')
    return command_list


# %%
# write the bash file for the ArduinoCLI
bash_file_name = "install-platforms-arduino-cli.sh"
print(f"Writing bash file to {os.path.join(artifact_path, bash_file_name)}")
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
arduino-cli --config-file "{0}" core update-index
""".format(
        arduino_cli_config
    )
)

for core in arduino_cli_cores:
    install_command = create_arduino_cli_core_command(
        core_name=core,
    )
    command_with_log = add_log_to_core_command(
        install_command, core.replace(":", " ").title()
    )
    bash_out.write("\n".join(command_with_log))
bash_out.write(
    """

echo "\\e[32mUpdating the core index\\e[0m"
arduino-cli --config-file "{0}" core update-index

echo "\\e[32mUpgrading all cores\\e[0m"
arduino-cli --config-file "{0}" core upgrade

echo "\\e[32mCurrently installed cores:\\e[0m"
arduino-cli --config-file "{0}" core list
""".format(
        arduino_cli_config
    )
)
bash_out.close()

# %%
# write the bash file for PlatformIO
bash_file_name = "install-platforms-platformio.sh"
print(f"Writing bash file to {os.path.join(artifact_path, bash_file_name)}")
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
    install_command = create_pio_ci_core_command(platform_name=platform, is_tool=False)
    if platform in platformio_platform_tools.keys():
        for tool in platformio_platform_tools[platform]["tools"]:
            install_command += "\n" + create_pio_ci_core_command(
                platform_name=tool, is_tool=True
            )
        command_with_log = add_log_to_core_command(
            install_command, platformio_platform_tools[platform]["name"]
        )
    else:
        command_with_log = add_log_to_core_command(install_command, platform)
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
        print("Deleting downloaded jsons")
        os.remove(
            os.path.join(ci_path, "platformio_platform_tools.json")
        )  # remove downloaded file
        os.remove(
            os.path.join(ci_path, "platformio_to_arduino_boards.json")
        )  # remove downloaded file
        os.rmdir(ci_path)  # remove dir if empty
    except:
        pass
    try:
        print("Deleting default Arduino CLI file")
        os.remove(arduino_cli_config)  # remove downloaded file
        os.rmdir(ci_path)  # remove dir if empty
    except:
        pass

# %%
