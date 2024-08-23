#!/usr/bin/env python
# %%
import os
import sys
from typing import List, Union
import json
import shutil
import requests

from platformio.project.config import ProjectConfig
from platformio.package.meta import PackageSpec

# %%
# set verbose
use_verbose = False
if "RUNNER_DEBUG" in os.environ.keys() and os.environ["RUNNER_DEBUG"] == "1":
    use_verbose = True

debug_text = """
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

"""

acli_start_text = """

echo "\\e[32mCurrent Arduino CLI version:\\e[0m"
arduino-cli version

echo "\\e[32mUpdating the library index\\e[0m"
arduino-cli --config-file arduino_cli.yaml lib update-index
"""

acli_end_text = """

echo "::group::Current globally installed libraries"
echo "\\e[32mCurrently installed libraries:\\e[0m"
arduino-cli --config-file arduino_cli.yaml lib update-index
arduino-cli --config-file arduino_cli.yaml lib list
echo "::endgroup::"
"""

pio_start_text = """

echo "\\e[32mCurrent PlatformIO version:\\e[0m"
pio --version

echo "\\e[32mCurrently installed libraries:\\e[0m"
pio pkg list -g -v --only-libraries

"""

pio_end_text = """

echo "::group::Current globally installed libraries"
echo "\\e[32mCurrently installed packages:\\e[0m"
pio pkg list -g -v --only-libraries
echo "::endgroup::"
"""


# %%
# Some working directories

# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys():
    workspace_dir = os.environ.get("GITHUB_WORKSPACE")
else:
    workspace_dir = os.getcwd()

    #%%
workspace_path = os.path.abspath(os.path.realpath(workspace_dir))
library_json_file = os.path.join(workspace_dir, "library.json")
print(f"Workspace Path: {workspace_path}")


# %%
# The examples directory
examples_dir = "./examples/"
examples_path = os.path.join(workspace_dir, examples_dir)
examples_path = os.path.abspath(os.path.realpath(examples_path))
examples_deps_file = os.path.join(examples_path, "example_dependencies.json")
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
# NOTE: No PlatformIO config file is needed to install libraries


# %%
# functions for parsing libraries
def get_package_spec(dependency: dict):
    spec = PackageSpec(
        id=dependency.get("id"),
        owner=dependency.get("owner"),
        name=dependency.get("name"),
        requirements=dependency.get("version"),
    )
    return spec


def convert_dep_dict_to_str(dependency: dict, include_version: bool = True) -> str:
    install_str = ""
    if "owner" in dependency.keys() and "github" in dependency["version"]:
        if "name" in dependency.keys():
            install_str += f"{dependency['name']}="
        install_str += dependency["version"]
    elif (
        "owner" in dependency.keys()
        and "name" in dependency.keys()
        and "version" in dependency.keys()
    ):
        lib_dep = f"{dependency['owner']}/{dependency['name']}"
        if include_version:
            lib_dep += f"@{dependency['version']}"
        install_str += lib_dep
    elif "name" in dependency.keys() and "version" in dependency.keys():
        lib_dep = f"{dependency['name']}"
        if include_version:
            lib_dep += f"@{dependency['version']}"
        install_str += lib_dep
    else:
        install_str += dependency["name"]

    return install_str


# %%
# find dependencies based on the library specification
if os.path.isfile(library_json_file):
    with open(library_json_file) as f:
        library_specs = json.load(f)
else:
    library_specs = {"dependencies": []}
# find dependencies based on the examples dependency specs
if os.path.isfile(examples_deps_file):
    with open(examples_deps_file) as f:
        example_specs = json.load(f)
else:
    example_specs = {"dependencies": []}

# %% Combine dependencies
dependencies = []
if "dependencies" in library_specs.keys():
    dependencies.extend(
        [get_package_spec(dependency) for dependency in library_specs["dependencies"]]
    )
if "dependencies" in example_specs.keys():
    dependencies.extend(
        [get_package_spec(dependency) for dependency in example_specs["dependencies"]]
    )

humanized_deps = [dep.as_dependency() for dep in dependencies]

# %%
# quit if there are no dependencies
if len(dependencies) == 0:
    print("No dependencies to install!")
    # sys.exit()


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
    if "github" in library["version"]:
        arduino_command_args.append("--git-url")
        arduino_command_args.append(library["version"])
    elif library["name"]=="MS5803":
        arduino_command_args.append("--git-url")
        arduino_command_args.append(library["url"])
    else:
        arduino_command_args.append(f"\"{library["name"]}\"")
    arduino_command_args.append("--no-deps")
    return " ".join(arduino_command_args)


def create_pio_ci_command(
    library: Union[str | dict | PackageSpec],
    update: bool = True,
    include_version: bool = True,
) -> list:
    pio_command_args = [
        "pio",
        "pkg",
        "update" if update else "install",
        # "--skip-dependencies",
        "-g",
        "--library",
    ]
    if isinstance(library, PackageSpec):
        pio_command_args.append(f'"{library.as_dependency()}"')
        return pio_command_args
    elif isinstance(library, dict):
        pio_command_args.append(f'"{convert_dep_dict_to_str(library)}"')
        return pio_command_args
    elif isinstance(library, str):
        pio_command_args.append(f'"{library}"')
        return pio_command_args


def add_log_to_command(command: str, group_title: str) -> List:
    command_list = []
    command_list.append(f'\necho "\\e[32m{group_title}\\e[0m"')
    command_list.append(command + "\n")
    return command_list


# %%
# write the bash files for the ArduinoCLI

# write bash to install library dependencies
bash_file_name = "install-library-libdeps-arduino-cli.sh"
print(f"Writing bash file to {os.path.join(artifact_path, bash_file_name)}")
bash_out = open(os.path.join(artifact_path, bash_file_name), "w+")
bash_out.write("#!/bin/bash\n\n")
bash_out.write(debug_text)
bash_out.write(acli_start_text)
for library in library_specs["dependencies"]:
    install_command = create_arduino_cli_command(
        library=library,
    )
    command_with_log = add_log_to_command(
        install_command, f"Installing {library['name']}"
    )
    bash_out.write("\n".join(command_with_log))
bash_out.write(acli_end_text)
bash_out.close()


# write bash to install additional example dependencies
bash_file_name = "install-example-libdeps-arduino-cli.sh"
print(f"Writing bash file to {os.path.join(artifact_path, bash_file_name)}")
bash_out = open(os.path.join(artifact_path, bash_file_name), "w+")
bash_out.write("#!/bin/bash\n\n")
bash_out.write(debug_text)
bash_out.write(acli_start_text)
for library in example_specs["dependencies"]:
    install_command = create_arduino_cli_command(
        library=library,
    )
    command_with_log = add_log_to_command(
        install_command, f"Installing {library['name']}"
    )
    bash_out.write("\n".join(command_with_log))
bash_out.write(acli_end_text)
bash_out.close()

# %%
# write the bash file for PlatformIO

# write bash to install library dependencies
bash_file_name = "install-library-libdeps-platformio.sh"
print(f"Writing bash file to {os.path.join(artifact_path, bash_file_name)}")
bash_out = open(os.path.join(artifact_path, bash_file_name), "w+")
bash_out.write("#!/bin/bash\n\n")
bash_out.write(debug_text)
bash_out.write(pio_start_text)
for library in [
    get_package_spec(dependency) for dependency in library_specs["dependencies"]
]:
    install_command = create_pio_ci_command(library=library, update=False)
    command_with_log = add_log_to_command(
        " ".join(install_command), f"Installing {library.name}"
    )
    bash_out.write("\n".join(command_with_log))
bash_out.write(pio_end_text)
bash_out.close()


# write bash to install additional example dependencies
bash_file_name = "install-example-libdeps-platformio.sh"
print(f"Writing bash file to {os.path.join(artifact_path, bash_file_name)}")
bash_out = open(os.path.join(artifact_path, bash_file_name), "w+")
bash_out.write("#!/bin/bash\n\n")
bash_out.write(debug_text)
bash_out.write(pio_start_text)
for library in [
    get_package_spec(dependency) for dependency in example_specs["dependencies"]
]:
    install_command = create_pio_ci_command(library=library, update=False)
    command_with_log = add_log_to_command(
        " ".join(install_command), f"Installing {library.name}"
    )
    bash_out.write("\n".join(command_with_log))
bash_out.write(pio_end_text)
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
