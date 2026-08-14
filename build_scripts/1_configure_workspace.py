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

Step 1 in the CI Build Pipeline sequence.
"""

# %%
from copy import deepcopy
import os
import json
import requests
import shutil
import subprocess
from itertools import chain
from build_config import (
    get_extended_config,
    set_verbose_mode,
    write_config_file,
    print_verbose,
    unset_positive,
    unset_negative,
)
from build_utils import remove_nested_duplicates


# %%
def load_pio_to_arduino_mapping():
    """Download the platformio_to_arduino_boards.json file"""
    print("Downloading board conversion file...")
    response = requests.get(
        "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/platformio_to_arduino_boards.json",
        timeout=30,
    )
    response.raise_for_status()

    # This is the dictionary of known FQBNs from the PlatformIO to Arduino mapping file.
    pio_env_to_fqbn = response.json()
    # Create a secondary dictionary that maps the unqualified FQBN (the part after the last colon) to the full FQBN.
    board_to_fqbn = {v.split(":")[-1]: v for v in pio_env_to_fqbn.values()}

    return pio_env_to_fqbn, board_to_fqbn
    # NOTE: We don't actually need this file, just the data from it.
    # #save the file locally to the CI directory for use in the build process
    # pio_to_acli_file = os.path.join(ci_path, "platformio_to_arduino_boards.json")
    # print("Saving board conversion file to: {}".format(pio_to_acli_file))
    # with open(pio_to_acli_file, "wb") as f:
    #     f.write(response.content)
    # # Also copy to artifacts for debugging
    # shutil.copyfile(
    #     pio_to_acli_file,
    #     os.path.join(artifact_path, "platformio_to_arduino_boards.json"),
    # )
    # with open(pio_to_acli_file) as f:
    #     pio_to_acli = json.load(f)


def load_arduino_cli_config(ci_path: str, artifact_path: str):
    """Load or download Arduino CLI configuration file, if necessary."""

    # NOTE THis file **is** required for the build process,
    # so we will download it if it does not exist.
    downloaded_arduino_cli_config = False
    arduino_cli_config = os.path.join(ci_path, "arduino_cli.yaml")

    if not os.path.isfile(arduino_cli_config):
        downloaded_arduino_cli_config = True
        print("Downloading default Arduino CLI configuration...")
        # download the default file
        response = requests.get(
            "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/arduino_cli.yaml",
            timeout=30,
        )
        response.raise_for_status()
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


# %%


def load_platformio_config(ci_path: str, artifact_path: str):
    """
    Download the PlatformIO configuration file, if necessary.
    """

    # NOTE THis file **is** required for the build process,
    # so we will download it if it does not exist.
    downloaded_pio_config = False
    pio_config_file = os.path.join(ci_path, "platformio.ini")

    if not os.path.isfile(pio_config_file):
        downloaded_pio_config = True
        print("Downloading default PlatformIO configuration...")
        # download the default file
        response = requests.get(
            "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/platformio.ini",
            timeout=30,
        )
        response.raise_for_status()
        # copy to the CI directory
        with open(os.path.join(ci_path, "platformio.ini"), "wb") as f:
            f.write(response.content)
        print("Saving PlatformIO configuration to: {}".format(pio_config_file))
        # also copy to the artifacts directory
        shutil.copyfile(
            os.path.join(ci_path, "platformio.ini"),
            os.path.join(artifact_path, "platformio.ini"),
        )

    return pio_config_file, downloaded_pio_config


def nested_list_to_dict(data):
    """Recursively convert a nested list structure into dictionaries."""

    if isinstance(data, list):
        # A list of [key, value] pairs -> dictionary
        if all(
            isinstance(item, list) and len(item) == 2 and isinstance(item[0], str)
            for item in data
        ):
            return {key: nested_list_to_dict(value) for key, value in data}

        # Otherwise, recursively process each list element
        return [nested_list_to_dict(item) for item in data]

    # Everything else (strings, numbers, etc.) stays unchanged
    return data


def read_platformio_config(pio_ini_dir: str = "."):
    result = subprocess.run(
        ["pio", "project", "config", "--json-output", "--project-dir", pio_ini_dir],
        capture_output=True,
        text=True,
        check=True,
    )

    project_config_l = []
    got_config = False
    for line in result.stdout.splitlines():
        if line.startswith("Error:"):
            raise RuntimeError(f"PlatformIO error: {line}")
        if line.startswith("[") or line.startswith("{"):
            project_config_l = json.loads(line)
            got_config = True
    if not got_config:
        raise RuntimeError("No PlatformIO configuration found in output")

    # The project config is returned as a list of lists, so we convert it to a dictionary for easier access.
    project_config = nested_list_to_dict(project_config_l)

    return project_config


def build_pio_mappings(pio_config):
    # Build mapping dictionaries
    board_to_pio_env = {}
    pio_env_to_platform = {}
    pio_env_to_board = {}
    # Read the environments from the PlatformIO config and
    for section, section_data in pio_config.items():
        if not section.startswith("env:") or not isinstance(section_data, dict):
            continue
        pio_env_name = section[len("env:") :]
        board = section_data.get("board")
        if board is None:
            print(
                f"::warning::No board found for environment '{pio_env_name}' in PlatformIO config. This environment will be ignored."
            )
            continue
        # build the mappings from environments to boards and platforms.
        # NOTE: PlatformIO does not allow duplicate environment names, so we can safely assume that
        # each environment name maps to a single board.
        pio_env_to_board[pio_env_name] = board
        pio_env_to_platform[pio_env_name] = section_data.get("platform")
        # build a reverse mapping from boards to environments
        # NOTE: This could be a one-to-many mapping.
        # In case of duplicate boards, we keep the first environment we encounter,
        # which is usually the one with the most generic flags.
        if board not in board_to_pio_env.keys():
            board_to_pio_env[board] = pio_env_name
        # Go in the opposite direction to map from PIO environment names to boards.
    return pio_env_to_board, pio_env_to_platform, board_to_pio_env


# %%
def match_input_with_known_dicts(
    input_list, primary_dict, secondary_dict, return_type: str
):
    if return_type.lower() not in ["keys", "values"]:
        raise ValueError(
            "return_type must be either 'keys' or 'values'. Got: {}".format(return_type)
        )
    return_keys = return_type.lower() == "keys"
    matches = []
    for input_item in input_list:
        got_match = False
        # check if it's a known environment name
        for k in primary_dict.keys():
            if input_item.lower() == k.lower():
                matches.append(k if return_keys else primary_dict[k])
                got_match = True
                break
        if got_match:
            continue
        # if it's not a known environment name, check if it's a known board name
        for k in secondary_dict.keys():
            if input_item.lower() == k.lower():
                matches.append(k if return_keys else secondary_dict[k])
                print_verbose(
                    f"::notice::Matched input '{input_item}' with '{k if return_keys else secondary_dict[k]}'"
                )
                got_match = True
                break
        if not got_match:
            print(
                f"::warning:: '{input_item}' is not a known board, FQBN, or environment. It will be ignored."
            )
    return matches


def get_pio_envs_to_build(
    args, pio_env_to_board: dict, pio_env_to_platform: dict, board_to_pio_env: dict
):
    """Parse boards from environment or use all available boards"""

    print_verbose(f"Requested environments to build: {len(args.pio_envs_to_build)}")
    for env in args.pio_envs_to_build:
        print_verbose(f"  - {env}")
    print_verbose(f"Requested environments to ignore: {len(args.pio_envs_to_ignore)}")
    for env in args.pio_envs_to_ignore:
        print_verbose(f"  - {env}")

    # NOTE argparser will enforce that the user cannot specify both pio_envs_to_build and pio_envs_to_ignore
    #  at the same time, so we don't need to check for that here.
    build_envs = []
    if args.pio_envs_to_build not in unset_positive:
        print("Building specified PlatformIO environments.")
        build_envs = match_input_with_known_dicts(
            args.pio_envs_to_build, pio_env_to_board, board_to_pio_env, "keys"
        )
    else:
        build_envs = list(pio_env_to_board.keys())
        print(
            "Building all known PlatformIO environments except those specified to ignore."
        )
        if args.pio_envs_to_ignore not in unset_negative:
            ignore_boards = match_input_with_known_dicts(
                args.pio_envs_to_ignore,
                pio_env_to_board,
                board_to_pio_env,
                "keys",
            )
            build_envs = list(
                set(pio_env_to_board.keys()).difference(set(ignore_boards))
            )

    build_platforms = [v for k, v in pio_env_to_platform.items() if k in build_envs]

    build_platforms = list(set(build_platforms))
    build_platforms.sort(key=str.casefold)

    print(f"PlatformIO Platforms to use: {len(build_platforms)}")
    print_verbose("Platforms to use:")
    for platform in build_platforms:
        print_verbose(f"  - {platform}")

    print(f"PlatformIO Environments to build: {len(build_envs)}")
    print_verbose("Environments to build:")
    for env in build_envs:
        print_verbose(f"  - {env}")

    return build_envs, list(set(build_platforms))


def get_arduino_fqbns_to_build(
    args, pio_env_to_fqbn: dict, board_to_fqbn: dict, board_to_pio_env: dict = {}
):
    """Parse boards from environment or use all available boards"""

    print_verbose(f"Requested boards to build: {len(args.arduino_fqbns_to_build)}")
    for board in args.arduino_fqbns_to_build:
        print_verbose(f"  - {board}")
    print_verbose(f"Requested boards to ignore: {len(args.arduino_fqbns_to_ignore)}")
    for board in args.arduino_fqbns_to_ignore:
        print_verbose(f"  - {board}")

    # NOTE argparser will enforce that the user cannot specify both
    # arduino_fqbns_to_build and arduino_fqbns_to_ignore at the same time.
    build_fqbns = []
    if args.arduino_fqbns_to_build not in unset_positive:
        print("Building specified Arduino boards.")
        build_fqbns = match_input_with_known_dicts(
            args.arduino_fqbns_to_build, pio_env_to_fqbn, board_to_fqbn, "values"
        )
    elif args.downloaded_pio_config in [False, "False", "false"]:
        print(
            "Building all Arduino boards matched with the custom PlatformIO configuration file, except those specified to ignore."
        )
        build_fqbns = [
            v for k, v in pio_env_to_fqbn.items() if k in board_to_pio_env.keys()
        ]
        if args.arduino_fqbns_to_ignore not in unset_negative:
            ignore_boards = match_input_with_known_dicts(
                args.arduino_fqbns_to_ignore, pio_env_to_fqbn, board_to_fqbn, "values"
            )
            build_fqbns = list(set(build_fqbns).difference(set(ignore_boards)))
    else:
        print("Building all known Arduino boards except those specified to ignore.")
        build_fqbns = list(pio_env_to_fqbn.values())
        if args.arduino_fqbns_to_ignore not in unset_negative:
            ignore_boards = match_input_with_known_dicts(
                args.arduino_fqbns_to_ignore, pio_env_to_fqbn, board_to_fqbn, "values"
            )
            build_fqbns = list(
                set(pio_env_to_fqbn.values()).difference(set(ignore_boards))
            )

    # The core is the first two parts of the FQBN (the part before the last colon).
    build_cores = [v.rsplit(":", 1)[0] for v in build_fqbns]

    # If EnviroDIY:samd is in the list, also add adafruit:samd (a dependency)
    if "EnviroDIY:samd" in build_cores and "adafruit:samd" not in build_cores:
        build_cores.append("adafruit:samd")

    build_cores = list(set(build_cores))
    build_cores.sort(key=str.casefold)

    print(f"Arduino Cores to use: {len(build_cores)}")
    print_verbose("Cores to use:")
    for core in build_cores:
        print_verbose(f"  - {core}")

    print(f"Arduino FQBNs to build: {len(build_fqbns)}")
    print_verbose("FQBNs to build:")
    for fqbn in build_fqbns:
        print_verbose(f"  - {fqbn}")

    return build_fqbns, build_cores


def match_board_to_pio_env(board: str, board_to_pio_env: dict, pio_env_to_board: dict):
    """Match a board name to a PlatformIO environment name using the board_to_pio_env mapping."""
    matched_env = match_input_with_known_dicts(
        [board], board_to_pio_env, pio_env_to_board, "keys"
    )
    if len(matched_env) == 0:
        print(
            f"::warning::Could not match board '{board}' to a PlatformIO environment."
        )
        return None
    return matched_env[0]


def match_board_to_fqbn(board: str, board_to_fqbn: dict, pio_env_to_fqbn: dict):
    """Match a board name to an Arduino FQBN using the pio_env_to_fqbn."""
    matched_fqbn = match_input_with_known_dicts(
        [board], board_to_fqbn, pio_env_to_fqbn, "values"
    )
    if len(matched_fqbn) == 0:
        print(f"::warning::Could not match board '{board}' to an Arduino FQBN.")
        return None
    return matched_fqbn[0]


# %%
def parse_examples_to_build(args):
    """Parse examples from environment or find all examples"""

    examples_to_build = args.examples_to_build

    if examples_to_build not in unset_positive:
        # NOTE: if this function has already been called, the examples_to_build list
        # will already be parsed and not equal to an unset_positive.
        # args.examples_to_build will simply be re-set to itself.
        print("Building specified examples.")
        # validate that the specified examples exist in the examples path or extras path
        valid_examples = []
        for example in examples_to_build:
            # if the example path is absolute, check if it exists and convert it to a relative path for the example name
            # if the example path is a file, check if it exists and convert it to a relative path for the example name
            if example.endswith(".ino"):
                example_path = os.path.dirname(example)
                ex_name = example_path.rsplit(os.path.sep, 1)[-1]
                if os.path.isabs(example):
                    full_file_path = example
                    sub_dir_path = os.path.relpath(example_path, args.workspace_path)
                else:
                    full_file_path = os.path.join(args.workspace_path, example)
                    sub_dir_path = example_path
                if not os.path.exists(full_file_path):
                    print(f"::error::Example '{example}' does not exist!")
                    exit(1)
                print_verbose(
                    f"Matched file path: {example} (relative path: {sub_dir_path}; full path: {full_file_path})"
                )
                valid_examples.append(sub_dir_path)
            elif os.path.isabs(example):
                example_path = example
                ex_name = example_path.rsplit(os.path.sep, 1)[-1]
                full_file_path = os.path.join(example_path, ex_name + ".ino")
                sub_dir_path = os.path.relpath(example, args.workspace_path)
                if not os.path.exists(full_file_path):
                    print(f"::error::Example '{example}' does not exist!")
                    exit(1)
                print_verbose(
                    f"Matched full path: {example} (relative path: {sub_dir_path}; full path: {full_file_path})"
                )
                valid_examples.append(sub_dir_path)
            else:
                ex_name = example.rsplit(os.path.sep, 1)[-1] + ".ino"
                found_file = False
                for root, subdirs, files in chain(
                    os.walk(args.examples_path), os.walk(args.extras_path)
                ):
                    for file in files:
                        if file == ex_name:
                            found_file = True
                            sub_dir_path = os.path.relpath(
                                os.path.join(root), args.workspace_path
                            )
                            valid_examples.append(sub_dir_path)
                            print_verbose(
                                f"Matched relative path: {example} (relative path: {sub_dir_path}; full path: {os.path.join(root, file)})"
                            )
                if not found_file:
                    print(f"::error::Example '{example}' does not exist!")
                    exit(1)
        examples_to_build = valid_examples
    else:
        print("Building all examples found in the example path.")
        examples_to_build = []
        excluded_folders = [".history", "archive", "logger_test", "tests", "more"]
        for root, subdirs, files in chain(
            os.walk(args.examples_path), os.walk(args.extras_path)
        ):
            for filename in files:
                file_path = os.path.join(root, filename)
                if filename == os.path.split(root)[-1] + ".ino" and not any(
                    e in os.path.normpath(root).split(os.sep) for e in excluded_folders
                ):
                    sub_dir_path = os.path.relpath(root, args.workspace_path)
                    examples_to_build.append(sub_dir_path)
                    print_verbose(
                        f"Found example: {filename} (relative path: {sub_dir_path}; full path: {file_path})"
                    )

        # Remove any ignored examples from the list
        ex_ignore = args.examples_to_ignore
        if ex_ignore is not None and ex_ignore not in unset_negative:
            examples_to_build = [
                example
                for example in examples_to_build
                if not any(
                    e in [p.lower() for p in os.path.normpath(example).split(os.sep)]
                    for e in [example_.lower().strip() for example_ in ex_ignore]
                )
            ]

    print(f"Total examples to build: {len(examples_to_build)}")
    print_verbose("Examples to build:")
    for example in examples_to_build:
        print_verbose(f"  - {example}")

    # add the examples to build to the args object for use in other scripts
    args.examples_to_build = examples_to_build

    return examples_to_build


def clean_input_defines(args):
    """
    Clean the inline and compiler flags to remove any duplicates and empty strings and
    to ensure that we consistently use the -D prefix for defines.
    """

    raw_inline_defines = args.raw_inline_defines
    # if the lists are separated by semicolons, we will split them into separate lists of lists.
    # If they are not separated by semicolons, we will treat them as a list with a single list.
    # inline flags must be defines and the will be inlined using `#define` in the
    # source code, so we will ensure that they do not have the -D prefix
    inline_defines = [
        list(
            set(
                [
                    define.removeprefix("-D").strip()
                    for define in group.split(",")
                    if define.strip() != ""
                ]
            )
        )
        for group in raw_inline_defines.split(";")
        if group.strip() != ""
    ]
    inline_defines = remove_nested_duplicates(deepcopy(inline_defines))
    # empty strings end up as a single empty list, so we will convert that to a list with a single empty list.
    if len(inline_defines) == 0:
        inline_defines = [[]]

    # set the value back to the args object for use in other scripts
    args.inline_defines = deepcopy(inline_defines)
    print_verbose("Inline defines:")
    for define in inline_defines:
        print_verbose(f"  - {define}")

    # compiler flags can be any flags, but we will ensure that they are unique and non-empty
    raw_compiler_flags = args.raw_compiler_flags
    compiler_flags = [
        list(
            set([define.strip() for define in group.split(",") if define.strip() != ""])
        )
        for group in raw_compiler_flags.split(";")
        if group.strip() != ""
    ]
    compiler_flags = remove_nested_duplicates(deepcopy(compiler_flags))
    # empty strings end up as a single empty list, so we will convert that to a list with a single empty list.
    if len(compiler_flags) == 0:
        compiler_flags = [[]]

    # set the value back to the args object for use in other scripts
    args.compiler_flags = deepcopy(compiler_flags)
    print_verbose("Compiler flags:")
    for flag in compiler_flags:
        print_verbose(f"  - {flag}")

    return inline_defines, compiler_flags


# %%
if __name__ == "__main__":
    print("=" * 60)
    print("CI Build Pipeline: Configure Matrix Workspace")
    print("=" * 60)

    print_verbose(
        "Reading configuration from environment variables, command line arguments, and the config file..."
    )
    args = get_extended_config()
    set_verbose_mode(args.verbose)

    # Download the PlatformIO config
    # Create mapping dictionaries for boards and environments
    # Save to args namespace for later use
    print_verbose("Looking for a PlatformIO config and downloading if needed...")
    pio_config_file, downloaded_pio_config = load_platformio_config(
        args.ci_path, args.artifact_path
    )

    # Read the PlatformIO config and build mapping dictionaries for boards and environments
    print_verbose("Reading the PlatformIO config...")
    pio_ini_dir = os.path.dirname(pio_config_file)
    pio_config = read_platformio_config(pio_ini_dir)
    print_verbose("Building mapping dictionaries...")
    pio_env_to_board, pio_env_to_platform, board_to_pio_env = build_pio_mappings(
        pio_config
    )

    # Compile the list of PlatformIO environments to build based on the inputs and the known boards
    print_verbose(
        "Compiling the list of PlatformIO environments to build based on the inputs and the known boards..."
    )
    build_envs, build_platforms = get_pio_envs_to_build(
        args, pio_env_to_board, pio_env_to_platform, board_to_pio_env
    )

    if "platformio" in args.compiler_list:
        args.pio_config_file = pio_config_file
        args.downloaded_pio_config = downloaded_pio_config
        args.build_envs = build_envs
        args.build_platforms = build_platforms
    else:
        args.pio_config_file = None
        args.downloaded_pio_config = False
        args.build_envs = []
        args.build_platforms = []

    # Download conversion from PlatformIO to Arduino boards
    # Save the file name and content to the args namespace for later use
    if "arduino-cli" in args.compiler_list:
        # Download Arduino CLI config
        # Save to args namespace for later use
        print_verbose("Looking for an Arduino CLI config and downloading if needed...")
        arduino_cli_config, downloaded_arduino_cli_config = load_arduino_cli_config(
            args.ci_path, args.artifact_path
        )
        args.arduino_cli_config = arduino_cli_config
        args.downloaded_arduino_cli_config = downloaded_arduino_cli_config

        print_verbose("Loading PlatformIO to Arduino board conversion mapping...")
        pio_env_to_fqbn, board_to_fqbn = load_pio_to_arduino_mapping()

        # Compile the list of Arduino FQBNs to build based on the inputs and the known boards
        print_verbose(
            "Compiling the list of Arduino FQBNs to build based on the inputs and the known boards..."
        )
        build_fqbns, build_cores = get_arduino_fqbns_to_build(
            args, pio_env_to_fqbn, board_to_fqbn, board_to_pio_env
        )
        args.build_fqbns = build_fqbns
        args.build_cores = build_cores
    else:
        args.arduino_cli_config = None
        args.downloaded_arduino_cli_config = False
        args.build_fqbns = []
        args.build_cores = []

    # Get the real list of examples to build based on the inputs and the examples found in the examples path
    print_verbose(
        "Parsing examples to build based on the inputs and the examples found in the examples path..."
    )
    parse_examples_to_build(args)

    # clean the inline and compiler flags to remove duplicates and empty strings
    print_verbose(
        "Cleaning inline and compiler flags to remove duplicates and empty strings..."
    )
    clean_input_defines(args)

    # Save to file for next script
    print_verbose("Writing updated configuration to file...")
    config_file = write_config_file(args)

    print(f"\n✓ Configuration saved to: {config_file}")
    print("✓ Workspace setup complete")


# %%
# CSpell:ignore argparser
