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
import hashlib
import os
import re
from copy import deepcopy
from itertools import chain

import configargparse
from build_config import (
    get_extended_config,
    set_verbose_mode,
    write_config_file,
    print_verbose,
    unset_positive,
    unset_negative,
)
from build_utils import (
    remove_nested_duplicates,
    read_platformio_config,
    load_platformio_config,
    load_arduino_cli_config,
    load_pio_to_arduino_mapping,
    build_pio_mappings,
    build_arduino_mappings,
)


# %%
def match_input_with_known_dicts(
    input_item,
    primary_dict: dict[str, str],
    secondary_dict: dict[str, str | list[str]],
    return_type: str,
) -> str | list[str] | None:
    """
    Match an input item (board name, environment name, or FQBN) with expected values in dictionaries.
    The primary dictionary is checked first, followed by the secondary dictionary.
    The function returns either the key or value based on the return_type argument.
    The primary dictionary is expected to have unique keys and values,
    while the secondary dictionary may have non-unique values
    (e.g., multiple FQBNs for a single board name).
    """
    if return_type.lower() not in ["keys", "values"]:
        raise ValueError(
            "return_type must be either 'keys' or 'values'. Got: {}".format(return_type)
        )
    for match_dict in [primary_dict, secondary_dict]:
        # first try to match with the keys, and return the key or value based on the return_type
        for k, v in match_dict.items():
            if input_item.lower() == k.lower():
                return k if return_type.lower() == "keys" else v  # v may be a list!
        # next try to match with the values, and return the key or value based on the return_type
        for k, v in match_dict.items():
            if isinstance(v, list):
                for item in v:
                    if input_item.lower() == item.lower():
                        print_verbose(
                            f"::notice::Matched input '{input_item}' with '{k}'"
                        )
                        return k if return_type.lower() == "keys" else item
            else:
                if input_item.lower() == v.lower():
                    print_verbose(f"::notice::Matched input '{input_item}' with '{k}'")
                    return k if return_type.lower() == "keys" else v
    # if we get here, we didn't match
    if input_item not in ["uno_pic32", "genuino101", "zero"]:
        # ^^ don't print warnings for these known exceptions
        print(f"::warning:: '{input_item}' could not be matched!")
    return None


def match_inputs_with_known_dicts(
    input_list: list[str],
    primary_dict: dict[str, str],
    secondary_dict: dict[str, str | list[str]],
    return_type: str,
) -> list[str]:
    return_keys = return_type.lower() == "keys"
    matches = []
    for input_item in input_list:
        match = match_input_with_known_dicts(
            input_item, primary_dict, secondary_dict, return_type
        )
        if isinstance(match, list):
            matches.extend(match)
        elif match is not None:
            matches.append(match)
    return matches


def match_board_to_pio_env(
    board: str,
    pio_env_to_board: dict[str, str],
    board_to_pio_env: dict[str, str | list[str]],
) -> str | list[str] | None:
    """Match a board name to a PlatformIO environment name using the board_to_pio_env mapping."""
    matched_env = match_input_with_known_dicts(
        board, pio_env_to_board, board_to_pio_env, "keys"
    )
    return matched_env


def match_board_to_fqbn(
    board: str,
    pio_board_to_fqbn: dict[str, str],
    board_to_fqbn: dict[str, str | list[str]],
) -> str | list[str] | None:
    """Match a board name to an Arduino FQBN using the pio_board_to_fqbn."""
    matched_fqbn = match_input_with_known_dicts(
        board, pio_board_to_fqbn, board_to_fqbn, "values"
    )
    return matched_fqbn


def get_common_boards_to_build(
    args: configargparse.Namespace,
    compiler_board_dictionaries: list[dict[str, str]],
) -> list[str]:
    """Parse boards from environment or use all available boards"""

    print_verbose(f"Requested boards to build: {len(args.boards_to_build)}")
    for board in args.boards_to_build:
        print_verbose(f"  - {board}")
    print_verbose(f"Requested boards to ignore: {len(args.boards_to_ignore)}")
    for board in args.boards_to_ignore:
        print_verbose(f"  - {board}")

    # NOTE argparser will enforce that the user cannot specify both boards_to_build and boards_to_ignore
    #  at the same time, so we don't need to check for that here.
    build_boards = []
    if args.boards_to_build not in unset_positive:
        print("Building specified boards.")
        build_boards = args.boards_to_build
    else:
        print("Building all known boards.")
        build_boards = list(
            set().union(*[d.keys() for d in compiler_board_dictionaries])
        )

    if args.boards_to_ignore not in unset_negative:
        print("Ignoring specified boards.")
        build_boards = list(
            set(
                set().union(*[d.keys() for d in compiler_board_dictionaries])
            ).difference(set(args.boards_to_ignore))
        )

    return build_boards


def get_pio_envs_to_build(
    args: configargparse.Namespace,
    common_boards: list[str],
    pio_env_to_board: dict[str, str],
    pio_env_to_platform: dict[str, str],
    board_to_pio_env: dict[str, str | list[str]],
) -> tuple[list[str], list[str]]:
    """Parse boards from environment or use all available boards"""

    if common_boards not in unset_positive:
        print_verbose(f"Common boards to build: {len(common_boards)}")
        for board in common_boards:
            print_verbose(f"  - {board}")
    if args.pio_envs_to_build not in unset_positive:
        print_verbose(
            f"Additional environments to build: {len(args.pio_envs_to_build)}"
        )
        for env in args.pio_envs_to_build:
            print_verbose(f"  - {env}")
    if args.pio_envs_to_ignore not in unset_negative:
        print_verbose(f"Environments to ignore: {len(args.pio_envs_to_ignore)}")
        for env in args.pio_envs_to_ignore:
            print_verbose(f"  - {env}")

    build_envs = []
    # only add additional environments if the user has specified them
    # NOTE argparser will enforce that the user cannot specify both
    # pio_envs_to_build and pio_envs_to_ignore at the same time.
    if args.pio_envs_to_build not in unset_positive:
        print("Building specified PlatformIO environments.")
        build_envs = match_inputs_with_known_dicts(
            args.pio_envs_to_build, pio_env_to_board, board_to_pio_env, "keys"
        )
    # if the user hasn't specified either common boards or additional environments, add everything possible
    elif len(common_boards) == 0:
        build_envs = list(pio_env_to_board.keys())
        print("Building all known PlatformIO environments.")

    # add in any boards listed in the boards_to_build list that are not already in the build_envs list
    print("Adding common boards with matched PlatformIO environments.")
    for board in common_boards:
        matched_envs = match_board_to_pio_env(board, pio_env_to_board, board_to_pio_env)
        if matched_envs is not None:
            if isinstance(matched_envs, list):
                build_envs.extend(matched_envs)
            else:
                build_envs.append(matched_envs)

    if args.pio_envs_to_ignore not in unset_negative:
        ignore_boards = match_inputs_with_known_dicts(
            args.pio_envs_to_ignore,
            pio_env_to_board,
            board_to_pio_env,
            "keys",
        )
        build_envs = list(set(build_envs).difference(set(ignore_boards)))

    # de-duplicate
    build_envs = list(set(build_envs))
    build_envs.sort(key=str.casefold)

    # Get matching platforms for the build_envs list
    build_platforms = [v for k, v in pio_env_to_platform.items() if k in build_envs]
    # de-duplicate and sort the platforms list
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

    return build_envs, build_platforms


def get_pio_platform_groups(
    build_envs: list[str], pio_env_to_platform: dict[str, str]
) -> list[dict[str, str | list[str]]]:
    """Group selected PlatformIO environments by development platform."""

    grouped_envs: dict[str, list[str]] = {}
    for env in build_envs:
        platform = pio_env_to_platform[env]
        grouped_envs.setdefault(platform, []).append(env)

    platform_groups = []
    for platform, environments in sorted(
        grouped_envs.items(), key=lambda item: item[0].casefold()
    ):
        platform_name = platform.rstrip("/").rsplit("/", 1)[-1]
        platform_name = re.sub(r"\.(?:zip|tar(?:\.gz)?|tgz)$", "", platform_name)
        platform_name = platform_name.split("@", 1)[0]
        platform_name = re.sub(r"[^a-zA-Z0-9]+", "-", platform_name)
        platform_name = platform_name.strip("-").lower() or "platform"
        platform_hash = hashlib.sha256(platform.encode("utf-8")).hexdigest()[:8]
        platform_groups.append(
            {
                "platform": platform,
                "platform_cache_tag": f"{platform_name}-{platform_hash}",
                "pio_envs": sorted(environments, key=str.casefold),
            }
        )

    return platform_groups


def get_arduino_fqbns_to_build(
    args: configargparse.Namespace,
    common_boards: list[str],
    pio_board_to_fqbn: dict[str, str],
    board_to_fqbn: dict[str, str | list[str]],
) -> tuple[list[str], list[str]]:
    """Parse boards from environment or use all available boards"""

    if common_boards not in unset_positive:
        print_verbose(f"Common boards to build: {len(common_boards)}")
        for board in common_boards:
            print_verbose(f"  - {board}")
    if args.arduino_fqbns_to_build not in unset_positive:
        print_verbose(f"Additional FQBNs to build: {len(args.arduino_fqbns_to_build)}")
        for fqbn in args.arduino_fqbns_to_build:
            print_verbose(f"  - {fqbn}")
    if args.arduino_fqbns_to_ignore not in unset_negative:
        print_verbose(f"FQBNs to ignore: {len(args.arduino_fqbns_to_ignore)}")
        for fqbn in args.arduino_fqbns_to_ignore:
            print_verbose(f"  - {fqbn}")

    # only add additional environments if the user has specified them
    # NOTE argparser will enforce that the user cannot specify both
    # arduino_fqbns_to_build and arduino_fqbns_to_ignore at the same time.
    build_fqbns = []
    if args.arduino_fqbns_to_build not in unset_positive:
        print("Building specified Arduino boards.")
        build_fqbns = match_inputs_with_known_dicts(
            args.arduino_fqbns_to_build, pio_board_to_fqbn, board_to_fqbn, "values"
        )
    # if the user hasn't specified either common boards or additional FQBNs, add everything possible
    elif len(common_boards) == 0:
        print("Building all known Arduino boards except those specified to ignore.")
        build_fqbns = list(pio_board_to_fqbn.values())
        if args.arduino_fqbns_to_ignore not in unset_negative:
            ignore_boards = match_inputs_with_known_dicts(
                args.arduino_fqbns_to_ignore, pio_board_to_fqbn, board_to_fqbn, "values"
            )
            build_fqbns = list(
                set(pio_board_to_fqbn.values()).difference(set(ignore_boards))
            )

    # add in any boards listed in the boards_to_build list that are not already in the build_envs list
    print("Adding common boards with matched Arduino FQBNs.")
    for board in common_boards:
        matched_envs = match_board_to_fqbn(board, pio_board_to_fqbn, board_to_fqbn)
        if matched_envs is not None:
            if isinstance(matched_envs, list):
                build_fqbns.extend(matched_envs)
            else:
                build_fqbns.append(matched_envs)

    if args.pio_envs_to_ignore not in unset_negative:
        ignore_boards = match_inputs_with_known_dicts(
            args.pio_envs_to_ignore,
            pio_board_to_fqbn,
            board_to_fqbn,
            "keys",
        )
        build_fqbns = list(set(build_fqbns).difference(set(ignore_boards)))

    # de-duplicate and sort the FQBNs list
    build_fqbns = list(set(build_fqbns))
    build_fqbns.sort(key=str.casefold)

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


def get_arduino_core_groups(build_fqbns: list[str]) -> list[dict]:
    """Group selected Arduino FQBNs by the cores required to build them."""

    grouped_fqbns: dict[str, list[str]] = {}
    for fqbn in build_fqbns:
        core = fqbn.rsplit(":", 1)[0]
        grouped_fqbns.setdefault(core, []).append(fqbn)

    core_groups = []
    if "EnviroDIY:samd" in grouped_fqbns:
        cores = ["EnviroDIY:samd", "adafruit:samd"]
        fqbns = grouped_fqbns.pop("EnviroDIY:samd")
        fqbns.extend(grouped_fqbns.pop("adafruit:samd", []))
        core_groups.append((cores, fqbns))

    for core, fqbns in grouped_fqbns.items():
        core_groups.append(([core], fqbns))

    grouped_cores = []
    for cores, fqbns in sorted(core_groups, key=lambda item: item[0][0].casefold()):
        cores = sorted(cores, key=str.casefold)
        core_names = "-".join(cores)
        core_name = re.sub(r"[^a-zA-Z0-9]+", "-", core_names).strip("-").lower()
        core_hash = hashlib.sha256("\n".join(cores).encode("utf-8")).hexdigest()[:8]
        grouped_cores.append(
            {
                "cores": cores,
                "core_cache_tag": f"{core_name}-{core_hash}",
                "fqbns": sorted(fqbns, key=str.casefold),
            }
        )

    return grouped_cores


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
        excluded_folders = [".history", "archive", "logger_test", "tests"]
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
            lowered_ex_ignore = [
                os.sep.join(
                    [p.lower().strip() for p in os.path.normpath(ei_).split(os.sep)]
                )
                for ei_ in ex_ignore
            ]
            examples_to_build = [
                example
                for example in examples_to_build
                if not os.sep.join(
                    [p.lower() for p in os.path.normpath(example).split(os.sep)]
                )
                in lowered_ex_ignore
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
    args: configargparse.Namespace = get_extended_config()
    set_verbose_mode(args.verbose)

    print_verbose("Creating the continuous integration directory, if needed...")
    os.makedirs(args.ci_path, exist_ok=True)
    os.makedirs(args.artifact_path, exist_ok=True)

    # if the user has requested to build PlatformIO environments or if they have not
    # specified any boards to build, we will download the PlatformIO config to get all
    # typical build boards and environments and build the mapping dictionaries.
    if "platformio" in args.compiler_list or args.boards_to_build in unset_positive:
        # Download the PlatformIO config
        # Create mapping dictionaries for boards and environments
        # Save to args namespace for later use
        print_verbose(
            "Looking for a PlatformIO config or downloading the default with all test environments..."
        )
        pio_config_file, downloaded_pio_config = load_platformio_config(
            args.ci_path, args.artifact_path
        )
        args.pio_config_file = pio_config_file
        args.downloaded_pio_config = downloaded_pio_config

        # Read the PlatformIO config and build mapping dictionaries for boards and environments
        print_verbose("Reading the PlatformIO config...")
        pio_ini_dir = os.path.dirname(pio_config_file)
        pio_config = read_platformio_config(pio_ini_dir)
        print_verbose("Building mapping dictionaries...")
        pio_env_to_board, pio_env_to_platform, board_to_pio_env = build_pio_mappings(
            pio_config
        )
    else:
        args.pio_config_file = None
        args.downloaded_pio_config = False
        pio_env_to_board: dict[str, str] = {}
        pio_env_to_platform: dict[str, str] = {}
        board_to_pio_env: dict[str, str | list[str]] = {}

    # if the user has requested to build Arduino boards or if they have not
    # specified any boards to build, we will download the mapping which has all
    # typical build FQBNs and build the mapping dictionaries.
    if "arduino-cli" in args.compiler_list or args.boards_to_build in unset_positive:
        print_verbose("Loading PlatformIO to Arduino board conversion mapping...")
        pio_board_to_fqbn = load_pio_to_arduino_mapping()
        print_verbose("Building mapping dictionaries...")
        pio_board_to_fqbn, board_to_fqbn = build_arduino_mappings(pio_board_to_fqbn)
    else:
        pio_board_to_fqbn: dict[str, str] = {}
        board_to_fqbn: dict[str, str | list[str]] = {}

    if (
        args.boards_to_build in unset_positive
        or args.boards_to_ignore in unset_negative
    ):
        print_verbose(
            "Compiling the list of common boards to build based on the inputs and the known boards..."
        )
        common_boards = get_common_boards_to_build(
            args, [pio_env_to_board, pio_board_to_fqbn]
        )
    else:
        common_boards = []

    common_boards.sort(key=str.casefold)

    if "platformio" in args.compiler_list:
        # Compile the list of PlatformIO environments to build based on the inputs and the known boards
        print_verbose(
            "Getting specifically requested PlatformIO environments and converting common boards to PlatformIO environments..."
        )
        build_envs, build_platforms = get_pio_envs_to_build(
            args, common_boards, pio_env_to_board, pio_env_to_platform, board_to_pio_env
        )
        args.build_envs = build_envs
        args.build_platforms = build_platforms
        args.pio_platform_groups = get_pio_platform_groups(
            build_envs, pio_env_to_platform
        )
    else:
        args.build_envs = []
        args.build_platforms = []
        args.pio_platform_groups = []

    if "arduino-cli" in args.compiler_list:
        # Compile the list of Arduino FQBNs to build based on the inputs and the known boards
        print_verbose(
            "Getting specifically requested Arduino FQBNs and converting common boards to Arduino FQBNs..."
        )
        build_fqbns, build_cores = get_arduino_fqbns_to_build(
            args, common_boards, pio_board_to_fqbn, board_to_fqbn
        )
        args.build_fqbns = build_fqbns
        args.build_cores = build_cores
        args.arduino_core_groups = get_arduino_core_groups(build_fqbns)

        # Download Arduino CLI config
        # Save to args namespace for later use
        # NOTE: This does NOT contain a list of boards or specific build environments!
        print_verbose("Looking for an Arduino CLI config and downloading if needed...")
        arduino_cli_config, downloaded_arduino_cli_config = load_arduino_cli_config(
            args.ci_path, args.artifact_path
        )
        args.arduino_cli_config = arduino_cli_config
        args.downloaded_arduino_cli_config = downloaded_arduino_cli_config
    else:
        args.build_fqbns = []
        args.build_cores = []
        args.arduino_core_groups = []
        args.arduino_cli_config = None
        args.downloaded_arduino_cli_config = False

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
