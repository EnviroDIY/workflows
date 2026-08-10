#!/usr/bin/env python
"""
Generate Platform and Library Installation Scripts.

Part of the CI Build Pipeline. This step:
- Loads platform and board configurations
- Loads library and example dependencies from library.json and example_dependencies.json
- Generates bash installation scripts for both Arduino CLI and PlatformIO cores/platforms
- Generates bash installation scripts for libraries and examples
- Outputs scripts to artifacts directory

Step 2 in the CI Build Pipeline sequence.
"""

import os
import json
from collections import OrderedDict
from typing import List, Union
from matrix_utils import (
    get_ci_directories,
    get_working_directories,
    load_library_dependencies,
    load_example_dependencies,
    load_board_to_pio_mapping,
    load_pio_to_arduino_boards_mapping,
    print_verbose,
)

try:
    from platformio.package.meta import PackageSpec
except ImportError:
    print(
        "::warning::PlatformIO not installed, skipping PlatformIO dependency generation"
    )
    PackageSpec = None


# Configuration
# Boards to always skip on each platform
PIO_SKIP_BOARDS = ["esp32-c6-devkitm-1", "arduino_nano_esp32"]
ACLI_SKIP_BOARDS = ["uno_pic32", "genuino101", "bluepill_f103c8"]


# %%
# Bash script templates

DEBUG_TEXT = """set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

"""

ACLI_PLATFORM_START_TEXT = """
echo "\\e[32mCurrent Arduino CLI version:\\e[0m"
arduino-cli version

echo "\\e[32mUpdating the core index\\e[0m"
arduino-cli --config-file "{0}" core update-index
"""

ACLI_PLATFORM_END_TEXT = """
echo "\\e[32mUpdating the core index\\e[0m"
arduino-cli --config-file "{0}" core update-index

echo "\\e[32mUpgrading all cores\\e[0m"
arduino-cli --config-file "{0}" core upgrade

echo "\\e[32mCurrently installed cores:\\e[0m"
arduino-cli --config-file "{0}" core list
"""

PIO_PLATFORM_START_TEXT = """
echo "\\e[32mCurrent PlatformIO version:\\e[0m"
pio --version
"""

PIO_PLATFORM_END_TEXT = """
echo "::group::Package List"
echo "\\e[32mCurrently installed packages:\\e[0m"
pio pkg list -g -v
echo "::endgroup::"
"""

ACLI_LIBRARY_START_TEXT = """

echo "\\e[32mCurrent Arduino CLI version:\\e[0m"
arduino-cli version

echo "\\e[32mUpdating the library index\\e[0m"
arduino-cli --config-file "{0}" lib update-index
"""

ACLI_LIBRARY_END_TEXT = """

echo "::group::Current globally installed libraries"
echo "\\e[32mCurrently installed libraries:\\e[0m"
arduino-cli --config-file "{0}" lib update-index
arduino-cli --config-file "{0}" lib list
echo "::endgroup::"
"""

PIO_LIBRARY_START_TEXT = """

echo "\\e[32mCurrent PlatformIO version:\\e[0m"
pio --version

echo "\\e[32mCurrently installed libraries:\\e[0m"
pio pkg list -g -v --only-libraries

"""

PIO_LIBRARY_END_TEXT = """

echo "::group::Current globally installed libraries"
echo "\\e[32mCurrently installed packages:\\e[0m"
pio pkg list -g -v --only-libraries
echo "::endgroup::"
"""

# Special installation scripts for non-standard libraries
INSTALL_SDI12_EXT_ACLI = """echo "\\e[32mDownloading External Interrupt version of the SDI-12 library as a zip\\e[0m"
curl -L --retry 15 --retry-delay 0 https://github.com/EnviroDIY/Arduino-SDI-12/archive/refs/heads/ExtInts.zip --create-dirs -o home/arduino/downloads/EnviroDIY_SDI12_ExtInts.zip
echo "\\e[32mDecompressing EnviroDIY_SDI12_ExtInts\\e[0m"
unzip -q -o home/arduino/downloads/EnviroDIY_SDI12_ExtInts.zip -d home/arduino/downloads/
echo "\\e[32mMoving EnviroDIY_SDI12_ExtInts to the libraries folder\\e[0m"
mkdir -p home/arduino/user/libraries/EnviroDIY_SDI12_ExtInts
mv home/arduino/downloads/Arduino-SDI-12-ExtInts/* home/arduino/user/libraries/EnviroDIY_SDI12_ExtInts

"""

INSTALL_SS_EXT_ACLI = """echo "\\e[32mDownloading SoftwareSerial with External Interrupts as a zip\\e[0m"
curl -L --retry 15 --retry-delay 0 https://github.com/EnviroDIY/SoftwareSerial_ExternalInts/archive/master.zip --create-dirs -o home/arduino/downloads/SoftwareSerial_ExternalInts.zip
echo "\\e[32mDecompressing SoftwareSerial_ExternalInts\\e[0m"
unzip -q -o home/arduino/downloads/SoftwareSerial_ExternalInts.zip -d home/arduino/downloads/
echo "\\e[32mMoving SoftwareSerial_ExternalInts to the libraries folder\\e[0m"
mkdir -p home/arduino/user/libraries/SoftwareSerial_ExternalInts
mv home/arduino/downloads/SoftwareSerial_ExtInts-master/* home/arduino/user/libraries/SoftwareSerial_ExternalInts

"""


# %%
# Helper functions


def get_package_spec(dependency: dict):
    """Convert dependency dict to PackageSpec"""
    if PackageSpec is None:
        return None

    spec = PackageSpec(
        id=dependency.get("id"),
        owner=dependency.get("owner"),
        name=dependency.get("name"),
        requirements=dependency.get("version"),
    )
    return spec


def convert_dep_dict_to_str(dependency: dict, include_version: bool = True) -> str:
    """Convert dependency dict to install string"""
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


def create_arduino_cli_lib_command(library: dict, include_version: bool = True) -> str:
    """Generate Arduino CLI library installation command"""
    arduino_command_args = [
        "arduino-cli",
        "--config-file",
        '"{0}"',  # Will be formatted later
        "lib",
        "install",
    ]

    if "github" in library.get("version", ""):
        arduino_command_args.append("--git-url")
        arduino_command_args.append(library["version"])
    elif library.get("name") in ["MS5803", "DallasTemperature"]:
        arduino_command_args.append("--git-url")
        arduino_command_args.append(library.get("url", ""))
    elif include_version:
        clean_version = (
            library.get("version", "")
            .replace("~", "")
            .replace(">", "")
            .replace("<", "")
            .replace("=", "")
            .replace("^", "")
        )
        arduino_command_args.append(f"\"{library['name']}@{clean_version}\"")
    else:
        arduino_command_args.append(f"\"{library['name']}\"")

    arduino_command_args.append("--no-deps")

    if library.get("name") in ["SDI-12_ExtInts"]:
        return INSTALL_SDI12_EXT_ACLI
    elif library.get("name") == "SoftwareSerial_ExternalInts":
        return INSTALL_SS_EXT_ACLI
    else:
        return " ".join(arduino_command_args)


def create_arduino_cli_core_command(core_name: str, arduino_cli_config: str) -> str:
    """Generate Arduino CLI core installation command"""
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
    """Generate PlatformIO core/platform installation command"""
    pio_command_args = [
        "pio",
        "pkg",
        "install",
        "-g",
        "--tool" if is_tool else "--platform",
        platform_name,
    ]
    return " ".join(pio_command_args)


def add_log_to_command(command: str, group_title: str) -> List[str]:
    """Wrap core installation command in logging group with ANSI colors"""
    command_list = []
    command_list.append('\necho "::group::{}"'.format(group_title))
    command_list.append(f'echo "\\e[32m{group_title}\\e[0m"')
    command_list.append(command)
    command_list.append('echo "::endgroup::"\n')
    return command_list


# %%
# Main script

if __name__ == "__main__":
    print("=" * 60)
    print("CI Build Pipeline: Step 2 - Generate Installation Scripts")
    print("=" * 60)

    # Setup directories
    dirs = get_working_directories()
    ci_path = dirs["ci_path"]
    artifact_path = dirs["artifact_path"]
    workspace_dir = dirs["workspace_dir"]

    # Load configuration from previous step
    config_file = os.path.join(artifact_path, "matrix_config.json")
    with open(config_file, "r") as f:
        config = json.load(f)

    # Load platform configurations from config
    print("\nLoading platform configurations...")
    pio_to_acli = config.get("pio_to_acli", {})
    board_to_pio_env = config.get("board_to_pio_env", {})
    board_to_pio_platform = config.get("board_to_pio_platform", {})
    arduino_cli_config = os.path.join(ci_path, "arduino_cli.yaml")

    # Try to load platform tools configuration
    platform_tools_file = os.path.join(ci_path, "platformio_platform_tools.json")
    platformio_platform_tools = {}
    if os.path.exists(platform_tools_file):
        with open(platform_tools_file, "r") as f:
            platformio_platform_tools = json.load(f)

    # Load dependencies
    print("Loading dependencies...")
    library_specs = load_library_dependencies(workspace_dir)
    example_specs = load_example_dependencies(workspace_dir)

    # Ensure dependencies key exists
    if "dependencies" not in library_specs:
        library_specs["dependencies"] = []
    if "dependencies" not in example_specs:
        example_specs["dependencies"] = []

    print(f"Library dependencies: {len(library_specs['dependencies'])}")
    print(f"Example dependencies: {len(example_specs['dependencies'])}")

    # %%
    # Generate platform installation scripts

    print("\n" + "=" * 60)
    print("Generating Platform Installation Scripts")
    print("=" * 60)

    # Load boards from configuration (parsed in step 1)
    boards = config.get("boards", [])
    if not boards:
        print("::error::No boards found in configuration. Did you run step 1?")
        exit(1)

    print(f"Boards to build: {boards}")

    # Validate boards
    for board in boards[:]:  # Use slice to iterate over a copy
        if board not in pio_to_acli.keys() and board not in ACLI_SKIP_BOARDS:
            print(
                f"""::error:: file=platformio_to_arduino_boards.json,title=No matching Arduino board::
Cannot find matching Arduino FQBN for {board}.
No core will be installed or cached for this board.
Please check the spelling of your board name or add an entry to the Arduino/PlatformIO board conversion file."""
            )
            boards.remove(board)
        elif board not in board_to_pio_platform.keys() and board not in PIO_SKIP_BOARDS:
            print(
                f"""::warning:: file=platformio.ini,title=No matching PlatformIO environment::
Cannot find matching environment in platformio.ini for {board}.
No platforms or tools will be installed or built for this board.
Please check the spelling of your board name or add an entry to your platformio.ini if not expected."""
            )

    # Convert boards to cores and platforms
    arduino_cli_cores = list(
        OrderedDict.fromkeys(
            [
                pio_to_acli[board]["fqbn"].rsplit(":", 1)[0]
                for board in boards
                if board in pio_to_acli.keys() and board not in ACLI_SKIP_BOARDS
            ]
        )
    )

    # If EnviroDIY:samd is in the list, also add adafruit:samd (a dependency)
    if (
        "EnviroDIY:samd" in arduino_cli_cores
        and "adafruit:samd" not in arduino_cli_cores
    ):
        arduino_cli_cores.append("adafruit:samd")

    pio_platforms = list(
        OrderedDict.fromkeys(
            [
                board_to_pio_platform[board]
                for board in boards
                if board in board_to_pio_platform.keys()
                and board not in PIO_SKIP_BOARDS
            ]
        )
    )

    # Print out the list of platforms/cores
    print(f"\nPlatformIO platforms to install: {pio_platforms}")
    print(f"Arduino cores to install: {arduino_cli_cores}")

    # Write the bash file for Arduino CLI platforms
    bash_file_name = "install-platforms-arduino-cli.sh"
    print(f"\nWriting {bash_file_name}...")
    with open(os.path.join(artifact_path, bash_file_name), "w") as bash_out:
        bash_out.write("#!/bin/bash\n\n")
        bash_out.write(DEBUG_TEXT)
        bash_out.write(ACLI_PLATFORM_START_TEXT.format(arduino_cli_config))

        for core in arduino_cli_cores:
            install_command = create_arduino_cli_core_command(
                core_name=core,
                arduino_cli_config=arduino_cli_config,
            )
            command_with_log = add_log_to_command(
                install_command, core.replace(":", " ").title()
            )
            bash_out.write("\n".join(command_with_log))

        bash_out.write(ACLI_PLATFORM_END_TEXT.format(arduino_cli_config))

    print(f"✓ Generated {bash_file_name}")

    # Write the bash file for PlatformIO platforms
    bash_file_name = "install-platforms-platformio.sh"
    print(f"Writing {bash_file_name}...")
    with open(os.path.join(artifact_path, bash_file_name), "w") as bash_out:
        bash_out.write("#!/bin/bash\n\n")
        bash_out.write(DEBUG_TEXT)
        bash_out.write(PIO_PLATFORM_START_TEXT)

        for platform in pio_platforms:
            install_command = create_pio_ci_core_command(
                platform_name=platform, is_tool=False
            )
            if platform in platformio_platform_tools.keys():
                for tool in platformio_platform_tools[platform]["tools"]:
                    install_command += "\n" + create_pio_ci_core_command(
                        platform_name=tool, is_tool=True
                    )
                command_with_log = add_log_to_command(
                    install_command, platformio_platform_tools[platform]["name"]
                )
            else:
                command_with_log = add_log_to_command(install_command, platform)
            bash_out.write("\n".join(command_with_log))

        bash_out.write(PIO_PLATFORM_END_TEXT)

    print(f"✓ Generated {bash_file_name}")

    # %%
    # Generate library installation scripts

    print("\n" + "=" * 60)
    print("Generating Library Installation Scripts")
    print("=" * 60)

    if (
        len(library_specs["dependencies"]) == 0
        and len(example_specs["dependencies"]) == 0
    ):
        print("\n✓ No dependencies to install")
    else:
        # Generate Arduino CLI scripts
        print("\nGenerating Arduino CLI installation scripts...")

        # Library dependencies for Arduino CLI
        bash_file_name = "install-library-libdeps-arduino-cli.sh"
        with open(os.path.join(artifact_path, bash_file_name), "w") as f:
            f.write("#!/bin/bash\n\n")
            f.write(DEBUG_TEXT)
            f.write(ACLI_LIBRARY_START_TEXT.format(arduino_cli_config))
            for library in library_specs["dependencies"]:
                install_command = create_arduino_cli_lib_command(library)
                command_with_log = add_log_to_command(
                    install_command.format(arduino_cli_config),
                    f"Installing {library['name']}",
                )
                f.write("\n".join(command_with_log))
                f.write("\n")
            f.write(ACLI_LIBRARY_END_TEXT.format(arduino_cli_config))
        print(f"✓ Generated {bash_file_name}")

        # Example dependencies for Arduino CLI
        bash_file_name = "install-example-libdeps-arduino-cli.sh"
        with open(os.path.join(artifact_path, bash_file_name), "w") as f:
            f.write("#!/bin/bash\n\n")
            f.write(DEBUG_TEXT)
            f.write(ACLI_LIBRARY_START_TEXT.format(arduino_cli_config))
            for library in example_specs["dependencies"]:
                install_command = create_arduino_cli_lib_command(library)
                command_with_log = add_log_to_command(
                    install_command.format(arduino_cli_config),
                    f"Installing {library['name']}",
                )
                f.write("\n".join(command_with_log))
                f.write("\n")
            f.write(ACLI_LIBRARY_END_TEXT.format(arduino_cli_config))
        print(f"✓ Generated {bash_file_name}")

        # Generate PlatformIO scripts (if available)
        if PackageSpec is not None:
            print("\nGenerating PlatformIO installation scripts...")

            # Library dependencies for PlatformIO
            bash_file_name = "install-library-libdeps-platformio.sh"
            with open(os.path.join(artifact_path, bash_file_name), "w") as f:
                f.write("#!/bin/bash\n\n")
                f.write(DEBUG_TEXT)
                f.write(PIO_LIBRARY_START_TEXT)
                for library in library_specs["dependencies"]:
                    spec = get_package_spec(library)
                    if spec:
                        install_str = convert_dep_dict_to_str(library)
                        install_command = (
                            f"pio pkg install --skip-dependencies -g '{install_str}'"
                        )
                        command_with_log = add_log_to_command(
                            install_command, f"Installing {library['name']}"
                        )
                        f.write("\n".join(command_with_log))
                        f.write("\n")
                f.write(PIO_LIBRARY_END_TEXT)
            print(f"✓ Generated {bash_file_name}")

            # Example dependencies for PlatformIO
            bash_file_name = "install-example-libdeps-platformio.sh"
            with open(os.path.join(artifact_path, bash_file_name), "w") as f:
                f.write("#!/bin/bash\n\n")
                f.write(DEBUG_TEXT)
                f.write(PIO_LIBRARY_START_TEXT)
                for library in example_specs["dependencies"]:
                    spec = get_package_spec(library)
                    if spec:
                        install_str = convert_dep_dict_to_str(library)
                        install_command = (
                            f"pio pkg install --skip-dependencies -g '{install_str}'"
                        )
                        command_with_log = add_log_to_command(
                            install_command, f"Installing {library['name']}"
                        )
                        f.write("\n".join(command_with_log))
                        f.write("\n")
                f.write(PIO_LIBRARY_END_TEXT)
            print(f"✓ Generated {bash_file_name}")

    print("\n✓ Installation scripts generated successfully")
    print("✓ Ready for job matrix building and compilation")
