#!/usr/bin/env python
"""
Generate Platform and Library Installation Scripts.

Part of the CI Build Pipeline. This step:
- Loads library and example dependencies from library.json and example_dependencies.json
- Generates bash installation scripts for both Arduino CLI and PlatformIO
- Outputs scripts to artifacts directory

Step 0b in the CI Build Pipeline sequence.
"""

import os
import json
from typing import List, Union
from matrix_utils import (
    setup_ci_directories,
    setup_full_directories,
    load_library_dependencies,
    load_example_dependencies,
    print_verbose,
)

try:
    from platformio.package.meta import PackageSpec
except ImportError:
    print("::warning::PlatformIO not installed, skipping PlatformIO dependency generation")
    PackageSpec = None


# %%
# Bash script templates

DEBUG_TEXT = """set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

"""

ACLI_START_TEXT = """

echo "\\e[32mCurrent Arduino CLI version:\\e[0m"
arduino-cli version

echo "\\e[32mUpdating the library index\\e[0m"
arduino-cli --config-file "{0}" lib update-index
"""

ACLI_END_TEXT = """

echo "::group::Current globally installed libraries"
echo "\\e[32mCurrently installed libraries:\\e[0m"
arduino-cli --config-file "{0}" lib update-index
arduino-cli --config-file "{0}" lib list
echo "::endgroup::"
"""

PIO_START_TEXT = """

echo "\\e[32mCurrent PlatformIO version:\\e[0m"
pio --version

echo "\\e[32mCurrently installed libraries:\\e[0m"
pio pkg list -g -v --only-libraries

"""

PIO_END_TEXT = """

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


def add_log_to_command(command: str, group_title: str) -> List[str]:
    """Wrap command in logging group"""
    return [
        f'echo "::group::{group_title}"',
        command,
        'echo "::endgroup::"',
    ]


if __name__ == "__main__":
    print("=" * 60)
    print("CI Build Pipeline: Step 0b - Generate Installation Scripts")
    print("=" * 60)
    
    # Setup directories
    dirs = setup_full_directories()
    ci_path = dirs["ci_path"]
    artifact_path = dirs["artifact_path"]
    workspace_dir = dirs["workspace_dir"]
    
    # Load dependencies
    print("\nLoading dependencies...")
    library_specs = load_library_dependencies(workspace_dir)
    example_specs = load_example_dependencies(workspace_dir)
    
    # Ensure dependencies key exists
    if "dependencies" not in library_specs:
        library_specs["dependencies"] = []
    if "dependencies" not in example_specs:
        example_specs["dependencies"] = []
    
    print(f"Library dependencies: {len(library_specs['dependencies'])}")
    print(f"Example dependencies: {len(example_specs['dependencies'])}")
    
    if len(library_specs["dependencies"]) == 0 and len(example_specs["dependencies"]) == 0:
        print("\n✓ No dependencies to install")
    else:
        arduino_cli_config = os.path.join(ci_path, "arduino_cli.yaml")
        
        # Generate Arduino CLI scripts
        print("\nGenerating Arduino CLI installation scripts...")
        
        # Library dependencies for Arduino CLI
        bash_file_name = "install-library-libdeps-arduino-cli.sh"
        with open(os.path.join(artifact_path, bash_file_name), "w") as f:
            f.write("#!/bin/bash\n\n")
            f.write(DEBUG_TEXT)
            f.write(ACLI_START_TEXT.format(arduino_cli_config))
            for library in library_specs["dependencies"]:
                install_command = create_arduino_cli_lib_command(library)
                command_with_log = add_log_to_command(
                    install_command.format(arduino_cli_config),
                    f"Installing {library['name']}"
                )
                f.write("\n".join(command_with_log))
                f.write("\n")
            f.write(ACLI_END_TEXT.format(arduino_cli_config))
        print(f"✓ Generated {bash_file_name}")
        
        # Example dependencies for Arduino CLI
        bash_file_name = "install-example-libdeps-arduino-cli.sh"
        with open(os.path.join(artifact_path, bash_file_name), "w") as f:
            f.write("#!/bin/bash\n\n")
            f.write(DEBUG_TEXT)
            f.write(ACLI_START_TEXT.format(arduino_cli_config))
            for library in example_specs["dependencies"]:
                install_command = create_arduino_cli_lib_command(library)
                command_with_log = add_log_to_command(
                    install_command.format(arduino_cli_config),
                    f"Installing {library['name']}"
                )
                f.write("\n".join(command_with_log))
                f.write("\n")
            f.write(ACLI_END_TEXT.format(arduino_cli_config))
        print(f"✓ Generated {bash_file_name}")
        
        # Generate PlatformIO scripts (if available)
        if PackageSpec is not None:
            print("\nGenerating PlatformIO installation scripts...")
            
            # Library dependencies for PlatformIO
            bash_file_name = "install-library-libdeps-platformio.sh"
            with open(os.path.join(artifact_path, bash_file_name), "w") as f:
                f.write("#!/bin/bash\n\n")
                f.write(DEBUG_TEXT)
                f.write(PIO_START_TEXT)
                for library in library_specs["dependencies"]:
                    spec = get_package_spec(library)
                    if spec:
                        install_str = convert_dep_dict_to_str(library)
                        install_command = f"pio pkg install --skip-dependencies -g '{install_str}'"
                        command_with_log = add_log_to_command(
                            install_command,
                            f"Installing {library['name']}"
                        )
                        f.write("\n".join(command_with_log))
                        f.write("\n")
                f.write(PIO_END_TEXT)
            print(f"✓ Generated {bash_file_name}")
            
            # Example dependencies for PlatformIO
            bash_file_name = "install-example-libdeps-platformio.sh"
            with open(os.path.join(artifact_path, bash_file_name), "w") as f:
                f.write("#!/bin/bash\n\n")
                f.write(DEBUG_TEXT)
                f.write(PIO_START_TEXT)
                for library in example_specs["dependencies"]:
                    spec = get_package_spec(library)
                    if spec:
                        install_str = convert_dep_dict_to_str(library)
                        install_command = f"pio pkg install --skip-dependencies -g '{install_str}'"
                        command_with_log = add_log_to_command(
                            install_command,
                            f"Installing {library['name']}"
                        )
                        f.write("\n".join(command_with_log))
                        f.write("\n")
                f.write(PIO_END_TEXT)
            print(f"✓ Generated {bash_file_name}")
    
    print("\n✓ Installation scripts generated successfully")
    print("✓ Ready for job matrix building and compilation")
