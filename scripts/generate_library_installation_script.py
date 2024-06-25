#!/usr/bin/env python
# %%
import json
import shutil
import sys
from typing import List
import os
import requests

# %%
# set verbose
if (
    "RUNNER_DEBUG" in os.environ.keys() and os.environ["RUNNER_DEBUG"] == "1"
) or "RUNNER_DEBUG" not in os.environ.keys():
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

# The examples directory
examples_dir = "./examples/"
examples_path = os.path.join(workspace_dir, examples_dir)
examples_path = os.path.abspath(os.path.realpath(examples_path))
print(f"Examples Path: {examples_path}")

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
#NOTE: No PlatformIO config file is needed to install libraries


# %%
# find dependencies based on the library specification and listings of example dependencies
with open(os.path.join(workspace_dir, "library.json")) as f:
    library_specs = json.load(f)
if os.path.isfile(os.path.join(examples_path, "example_dependencies.json")):
    with open(os.path.join(examples_path, "example_dependencies.json")) as f:
        example_specs = json.load(f)
else:
    example_specs = {"dependencies": []}

dependencies=[]
if "dependencies" in library_specs.keys():
    dependencies.extend(library_specs["dependencies"])
if "dependencies" in example_specs.keys():
    dependencies.extend(example_specs["dependencies"])

# quit if there are no dependencies
if len(dependencies) ==0:
    print("No dependencies to install!")
    sys.exit()


# %%
# helper functions to create commands
def create_arduino_cli_command(library: dict) -> str:
    arduino_command_args = [
        "arduino-cli",
        "--config-file",
        arduino_cli_config,
        "lib",
        "install",
    ]
    if "owner" in library.keys() and "github" in library["version"]:
        arduino_command_args.append("--git-url")
        arduino_command_args.append(library["version"])
    else:
        arduino_command_args.append(library["name"])
    arduino_command_args.append("--no-deps")
    return " ".join(arduino_command_args)


def create_pio_ci_command(
    library: dict,
) -> str:
    pio_command_args = [
        "pio",
        "pkg",
        "install",
        "--skip-dependencies",
        "-g",
        "--library",
    ]
    if "owner" in library.keys() and "github" in library["version"]:
        pio_command_args.append(library["version"])
    elif (
        "owner" in library.keys()
        and "name" in library.keys()
        and "version" in library.keys()
    ):
        lib_dep = f"{library['owner']}/{library['name']}"
        lib_dep += f"@{library['version']}"
        pio_command_args.append(lib_dep)
    elif "name" in library.keys() and "version" in library.keys():
        lib_dep = f"{library['name']}"
        lib_dep += f"@{library['version']}"
        pio_command_args.append(lib_dep)
    else:
        pio_command_args.append(library["name"])
    return " ".join(pio_command_args)


def add_log_to_command(command: str, group_title: str) -> List:
    command_list = []
    command_list.append(f'\necho "\\e[32m{group_title}\\e[0m"')
    command_list.append(command+"\n")
    return command_list


# %%
# write the bash file for the ArduinoCLI
bash_file_name = "install-libraries-arduino-cli.sh"
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

echo "\\e[32mUpdating the library index\\e[0m"
arduino-cli --config-file arduino_cli.yaml lib update-index
"""
)

for library in dependencies:
    install_command = create_arduino_cli_command(
        library=library,
    )
    command_with_log = add_log_to_command(install_command, f"Installing {library["name"]}")
    bash_out.write("\n".join(command_with_log))
bash_out.write(
    """

echo "::group::Current globally installed libraries"
echo "\\e[32mCurrently installed libraries:\\e[0m"
arduino-cli --config-file arduino_cli.yaml lib update-index
arduino-cli --config-file arduino_cli.yaml lib list
echo "::endgroup::"
"""
)
bash_out.close()

# %%

# %%
# write the bash file for PlatformIO
bash_file_name = "install-libraries-platformio.sh"
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

echo "\\e[32mCurrently installed libraries:\\e[0m"
pio pkg list -g -v --only-libraries

"""
)
for library in dependencies:
    install_command = create_pio_ci_command(library=library)
    command_with_log = add_log_to_command(install_command, f"Installing {library["name"]}")
    bash_out.write("\n".join(command_with_log))
bash_out.write(
    """

echo "::group::Current globally installed libraries"
echo "\\e[32mCurrently installed packages:\\e[0m"
pio pkg list -g -v --only-libraries
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
        print("Deleting default Arduino CLI file")
        os.remove(arduino_cli_config)  # remove downloaded file
        os.rmdir(ci_path)  # remove dir if empty
    except:
        pass

# %%
