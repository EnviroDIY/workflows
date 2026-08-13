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

# %%
import os
import json
from typing import List
import requests
from build_config import get_extended_config, set_verbose_mode, print_verbose

from platformio.package.meta import PackageSpec


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


def load_pio_tools():
    """Download the platformio_platform_tools.json file"""
    print("Downloading tools file...")
    response = requests.get(
        "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/platformio_platform_tools.json",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
    # NOTE: We don't actually need this file, just the data from it.
    # pio_tools_file = os.path.join(ci_path, "platformio_platform_tools.json")
    # print("Saving tools file to: {}".format(pio_tools_file))
    # with open(pio_tools_file, "wb") as f:
    #     f.write(response.content)
    # # Also copy to artifacts for debugging
    # shutil.copyfile(
    #     pio_tools_file,
    #     os.path.join(artifact_path, "platformio_platform_tools.json"),
    # )
    # with open(pio_tools_file) as f:
    #     pio_tools = json.load(f)


# Dependency loading and parsing utilities
def load_library_dependencies(workspace_path: str) -> dict:
    """
    Load library dependencies from library.json.

    Returns:
        dict: Library specification with 'dependencies' key
    """

    library_json_file = os.path.join(workspace_path, "library.json")
    if os.path.isfile(library_json_file):
        with open(library_json_file) as f:
            return json.load(f)
    return {"dependencies": []}


def load_example_dependencies(examples_path: str) -> dict:
    """
    Load example dependencies from examples/example_dependencies.json.

    Returns:
        dict: Example specification with 'dependencies' key
    """

    examples_deps_file = os.path.join(examples_path, "example_dependencies.json")
    if os.path.isfile(examples_deps_file):
        with open(examples_deps_file) as f:
            return json.load(f)
    return {"dependencies": []}


def get_package_spec(dependency: dict):
    """Convert dependency dict to PackageSpec"""

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


def create_pio_ci_lib_command(
    library: str | dict | PackageSpec,
    update: bool = True,
    include_version: bool = True,
) -> str:
    pio_command_args = [
        "pio",
        "pkg",
        "update" if update else "install",
        "--skip-dependencies",
        "-g",
        "--library",
    ]
    if isinstance(library, PackageSpec):
        # NOTE: if we get a PackageSpec, we always include the version, since it's part of the spec
        pio_command_args.append(f'"{library.as_dependency()}"')
    elif isinstance(library, dict):
        pio_command_args.append(
            f'"{convert_dep_dict_to_str(library, include_version)}"'
        )
    elif isinstance(library, str):
        # NOTE if we get a string, we don't try to guess if the version is included, we just use it as is
        pio_command_args.append(f'"{library}"')

    return " ".join(pio_command_args)


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
    print("CI Build Pipeline: Generate Installation Scripts")
    print("=" * 60)

    print_verbose(
        "Reading configuration from environment variables, command line arguments, and the config file..."
    )
    args = get_extended_config()
    set_verbose_mode(args.verbose)

    print("\n" + "=" * 60)
    print("Generating Platform and Core Installation Scripts")
    print("=" * 60)

    # Print out the list of platforms/cores
    print(f"Arduino cores to install: {len(args.build_cores)}")
    print_verbose("Cores to install:")
    for core in args.build_cores:
        print_verbose(f"  - {core}")

    # Write the bash file for Arduino CLI platforms
    bash_file_name = "install-platforms-arduino-cli.sh"
    arduino_cli_config = os.path.join(args.ci_path, "arduino_cli.yaml")
    print(f"\nWriting {bash_file_name}...")
    with open(os.path.join(args.artifact_path, bash_file_name), "w") as bash_out:
        bash_out.write("#!/bin/bash\n\n")
        bash_out.write(DEBUG_TEXT)
        bash_out.write(ACLI_PLATFORM_START_TEXT.format(arduino_cli_config))

        for core in args.build_cores:
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

    # Download PlatformIO tools associated with each platform.
    print_verbose(
        "Downloading the list of extra tools associated with each PlatformIO platform..."
    )
    pio_tools = load_pio_tools()

    print(f"\nPlatformIO platforms to install: {len(args.build_platforms)}")
    print_verbose("Platforms to install:")
    for platform in args.build_platforms:
        print_verbose(f"  - {platform}")

    # Write the bash file for PlatformIO platforms
    bash_file_name = "install-platforms-platformio.sh"
    print(f"Writing {bash_file_name}...")
    with open(os.path.join(args.artifact_path, bash_file_name), "w") as bash_out:
        bash_out.write("#!/bin/bash\n\n")
        bash_out.write(DEBUG_TEXT)
        bash_out.write(PIO_PLATFORM_START_TEXT)

        for platform in args.build_platforms:
            install_command = create_pio_ci_core_command(
                platform_name=platform, is_tool=False
            )
            if platform in pio_tools.keys():
                for tool in pio_tools[platform]["tools"]:
                    install_command += "\n" + create_pio_ci_core_command(
                        platform_name=tool, is_tool=True
                    )
                group_title = pio_tools[platform]["name"]
            else:
                group_title = platform
            command_with_log = add_log_to_command(install_command, group_title)
            bash_out.write("\n".join(command_with_log))

        bash_out.write(PIO_PLATFORM_END_TEXT)

    print(f"✓ Generated {bash_file_name}")

    # Generate library installation scripts

    print("\n" + "=" * 60)
    print("Generating Library Installation Scripts")
    print("=" * 60)

    # Load dependencies
    print("Loading dependencies...")
    library_specs = load_library_dependencies(args.workspace_path)
    example_specs = load_example_dependencies(args.workspace_path)

    # Ensure dependencies key exists
    if "dependencies" not in library_specs:
        library_specs["dependencies"] = []
    if "dependencies" not in example_specs:
        example_specs["dependencies"] = []

    print(f"Library dependencies: {len(library_specs['dependencies'])}")
    print(f"Example dependencies: {len(example_specs['dependencies'])}")
    print_verbose("Dependencies to install:")
    for lib in library_specs["dependencies"] + example_specs["dependencies"]:
        print_verbose(f"  - {lib.get('name') or lib.get('id') or lib}")

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
        with open(os.path.join(args.artifact_path, bash_file_name), "w") as f:
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
        with open(os.path.join(args.artifact_path, bash_file_name), "w") as f:
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
        print("\nGenerating PlatformIO installation scripts...")

        # Library dependencies for PlatformIO
        bash_file_name = "install-library-libdeps-platformio.sh"
        with open(os.path.join(args.artifact_path, bash_file_name), "w") as f:
            f.write("#!/bin/bash\n\n")
            f.write(DEBUG_TEXT)
            f.write(PIO_LIBRARY_START_TEXT)
            for library in library_specs["dependencies"]:
                # spec = get_package_spec(library)
                # if spec:
                install_command = create_pio_ci_lib_command(
                    library, update=False, include_version=True
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
        with open(os.path.join(args.artifact_path, bash_file_name), "w") as f:
            f.write("#!/bin/bash\n\n")
            f.write(DEBUG_TEXT)
            f.write(PIO_LIBRARY_START_TEXT)
            for library in example_specs["dependencies"]:
                # spec = get_package_spec(library)
                # if spec:
                install_command = create_pio_ci_lib_command(
                    library, update=False, include_version=True
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


# %%
# CSpell:ignore fqbns
