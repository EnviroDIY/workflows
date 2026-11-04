#!/usr/bin/env python
"""
Shared utilities for matrix generation scripts and CI utilities.

Provides:
- Verbose output configuration
- Workspace and CI directory setup
- JSON file utilities
- Filename slug generation
- Matrix utilities (dict_product, deduplication)
"""

# %%
import hashlib
import os
import json
import re
from itertools import product
from typing import List, Dict, Any
import requests
import shutil
import subprocess

# Arduino package indexes do not declare these cross-package core dependencies.
ARDUINO_CORE_DEPENDENCIES = {
    "adafruit:avr": ["arduino:avr"],
    "EnviroDIY:avr": ["arduino:avr"],
    "EnviroDIY:samd": ["adafruit:samd"],
}


def expand_arduino_core_dependencies(cores: List[str]) -> List[str]:
    """Return Arduino cores and their dependencies in installation order."""

    expanded_cores = []
    visiting = set()
    visited = set()

    def add_core(core: str) -> None:
        if core in visited:
            return
        if core in visiting:
            raise ValueError(f"Circular Arduino core dependency involving '{core}'")

        visiting.add(core)
        for dependency in ARDUINO_CORE_DEPENDENCIES.get(core, []):
            add_core(dependency)
        visiting.remove(core)
        visited.add(core)
        expanded_cores.append(core)

    for core in sorted(set(cores), key=str.casefold):
        add_core(core)

    return expanded_cores


def get_arduino_core_cache_tag(cores: List[str]) -> str:
    """Return a stable, filename-safe tag for an Arduino core set."""

    expanded_cores = expand_arduino_core_dependencies(cores)
    core_names = "-".join(expanded_cores)
    core_name = re.sub(r"[^a-zA-Z0-9]+", "-", core_names).strip("-").lower()
    core_hash = hashlib.sha256("\n".join(expanded_cores).encode("utf-8")).hexdigest()[
        :8
    ]
    return f"{core_name}-{core_hash}"


def create_arduino_core_cache_info(
    cores: List[str], artifact_path: str, arduino_cli_config: str
) -> Dict[str, Any]:
    """Write an Arduino core-set install script and return its cache metadata."""

    expanded_cores = expand_arduino_core_dependencies(cores)
    core_cache_tag = get_arduino_core_cache_tag(expanded_cores)
    core_install_script = os.path.abspath(
        os.path.join(artifact_path, f"install-core-{core_cache_tag}.sh")
    )

    with open(core_install_script, "w") as bash_out:
        bash_out.write("#!/bin/bash\n\n")
        bash_out.write("""set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

""")
        bash_out.write('echo "\\e[32mCurrent Arduino CLI version:\\e[0m"\n')
        bash_out.write("arduino-cli version\n\n")
        bash_out.write('echo "\\e[32mUpdating the core index\\e[0m"\n')
        bash_out.write(
            f'arduino-cli --config-file "{arduino_cli_config}" core update-index\n'
        )

        for core in expanded_cores:
            group_title = core.replace(":", " ").title()
            bash_out.write(f'\necho "::group::{group_title}"\n')
            bash_out.write(f'echo "\\e[32m{group_title}\\e[0m"\n')
            bash_out.write(
                f'arduino-cli --config-file "{arduino_cli_config}" core install {core}\n'
            )
            bash_out.write('echo "::endgroup::"\n')

        bash_out.write('\necho "\\e[32mUpdating the core index\\e[0m"\n')
        bash_out.write(
            f'arduino-cli --config-file "{arduino_cli_config}" core update-index\n\n'
        )
        bash_out.write('echo "\\e[32mCurrently installed cores:\\e[0m"\n')
        bash_out.write(f'arduino-cli --config-file "{arduino_cli_config}" core list\n')

    with open(core_install_script, "rb") as script_file:
        core_cache_hash = hashlib.sha256(script_file.read()).hexdigest()

    return {
        "cores": expanded_cores,
        "core_cache_tag": core_cache_tag,
        "core_cache_hash": core_cache_hash,
        "core_install_script": core_install_script,
    }


# %%
# Utilities for matrix generation and deduplication


# Source - https://stackoverflow.com/a/40623158
# Posted by Tarrasch, modified by community. See post 'Timeline' for change history
# Retrieved 2026-08-09, License - CC BY-SA 4.0
def dict_product(options):
    """
    >>> list(dict_product({'number': [1, 2], 'character': 'ab'}))
    [{'character': 'a', 'number': 1},
     {'character': 'a', 'number': 2},
     {'character': 'b', 'number': 1},
     {'character': 'b', 'number': 2}]
    """
    return (dict(zip(options.keys(), x)) for x in product(*options.values()))


def remove_nested_duplicates(list_with_dups):
    """Remove duplicates from a list of dictionaries or lists.

    Dictionaries are compared regardless of key ordering.
    Lists are compared regardless of item ordering, except for
    command-ordered fields (inline_defines, compiler_flags) which preserve order.
    Nested dictionaries and lists are handled recursively.

    For dictionaries, the 'job_group' key is ignored when comparing.
    """
    # Fields where list ordering indicates command order and must be preserved
    COMMAND_ORDERED_FIELDS = {"inline_defines", "compiler_flags"}

    def normalize(value, ignore_job_group=False, parent_key=None):
        """Recursively normalize a value for order-independent comparison.

        Args:
            value: The value to normalize
            ignore_job_group: Whether to ignore the 'job_group' key
            parent_key: The parent dictionary key containing this value
        """

        if isinstance(value, dict):
            return {
                k: normalize(v, parent_key=k)
                for k, v in value.items()
                if not (ignore_job_group and k == "job_group")
            }

        if isinstance(value, list):
            normalized_items = [
                normalize(item, parent_key=parent_key) for item in value
            ]

            # Preserve order for command-ordered fields; sort order-independent lists
            if parent_key in COMMAND_ORDERED_FIELDS:
                return normalized_items
            else:
                # Sort recursively normalized list items so list ordering
                # does not affect comparison for truly order-independent lists.
                return sorted(
                    normalized_items, key=lambda x: json.dumps(x, sort_keys=True)
                )

        return value

    seen = set()
    deduped_list = []

    for item in list_with_dups:

        # Only ignore job_group when the item itself is a dictionary.
        normalized_item = normalize(item, ignore_job_group=isinstance(item, dict))

        json_str = json.dumps(normalized_item, sort_keys=True)

        if json_str not in seen:
            seen.add(json_str)
            deduped_list.append(item)

    return deduped_list


# %%
# Utilities for loading and saving JSON files and generating filename-safe slugs
def load_json_file(filepath: str) -> Any:
    """Load a JSON file"""
    with open(filepath, "r") as f:
        return json.load(f)


def save_json_file(filepath: str, data: Any) -> None:
    """Save data to a JSON file"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def get_filename_slug(job_key, value) -> str:
    """Convert job values to filename-safe slugs"""
    replace_list = [
        ("BUILD_MODEM_", ""),
        ("BUILD_SENSOR_", ""),
        ("BUILD_PUB_", ""),
        ("BUILD_TEST_", ""),
        ("_PUBLISHER", ""),
        ("TINY_GSM_MODEM_", ""),
        ("_", "-"),
        (" ", "-"),
    ]

    def replace_all(s):
        for old, new in replace_list:
            s = s.replace(old, new)
        return s

    if job_key in ["compiler", "flag"]:
        return replace_all(value)
    elif job_key in ["board", "fqbn", "pio_env"]:
        if ":" in value and "zephyr" in value:
            return replace_all(value.rsplit(":")[-1]) + "-zephyr"
        elif ":" in value:
            return replace_all(value.rsplit(":")[-1])
        else:
            return replace_all(value)
    elif (
        job_key in ["inline_defines", "compiler_flags"]
        and isinstance(value, list)
        and len(value) > 0
        and isinstance(value[0], list)
    ):
        return "-".join(
            [
                replace_all(f)
                for f in [
                    "-".join([replace_all(g) for g in sublist]) for sublist in value
                ]
            ]
        )
    elif job_key in ["inline_defines", "compiler_flags"] and isinstance(value, list):
        return "-".join([replace_all(f) for f in value])
    elif job_key in ["inline_defines", "compiler_flags"] and isinstance(value, str):
        return replace_all(value)
    elif job_key == "example":
        return replace_all(str(value).rsplit(os.path.sep)[-1])
    else:
        return replace_all(str(value))


# %%
def load_pio_to_arduino_mapping():
    """Download the platformio_to_arduino_boards.json file"""
    print("Downloading board conversion file...")
    response = requests.get(
        "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/platformio_to_arduino_boards.json",
        timeout=30,
    )
    response.raise_for_status()

    # This is the dictionary of known mappings between PlatformIO board names and Arduino FQBNs
    # NOTE: Both PlatformIO board names and Arduino FQBNs are universally unique, so we can use them as keys and values in the dictionary.
    # PlatformIO environment names are unique within a given PlatformIO configuration file, but they are not universally unique, so we cannot use them as keys in the dictionary.
    try:
        pio_to_acli = response.json()
        return pio_to_acli
    except json.JSONDecodeError as e:
        print("Error decoding JSON from platformio_to_arduino_boards.json:", e)
        raise

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


def build_arduino_mappings(pio_board_to_fqbn: dict[str, str]):
    # Create a dictionary that maps the unqualified FQBN (the part after the last colon) to the full FQBN.
    # Unqualified board names are not guaranteed to be unique, so this dictionary may have duplicate keys.
    # In case of duplicates, we will keep the first one we encounter.
    board_to_fqbn: dict[str, str | list[str]] = {}
    for fqbn in pio_board_to_fqbn.values():
        unqualified_name = fqbn.split(":")[-1]
        if unqualified_name not in board_to_fqbn:
            board_to_fqbn[unqualified_name] = fqbn
        else:
            # if it's already a list, append to it, otherwise convert it to a list and append
            if isinstance(board_to_fqbn[unqualified_name], list):
                board_to_fqbn[unqualified_name].append(fqbn)  # type: ignore
            else:
                board_to_fqbn[unqualified_name] = [board_to_fqbn[unqualified_name]]  # type: ignore
                board_to_fqbn[unqualified_name].append(fqbn)  # type: ignore

    # NOTE: We don't need to build a dictionary of cores;
    # the core is always the first two parts of the FQBN (the part before the last colon).
    # We can extract it when needed.

    return pio_board_to_fqbn, board_to_fqbn


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

    # NOTE This file **is** required for the build process,
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


def build_pio_mappings(
    pio_config,
) -> tuple[dict[str, str], dict[str, str], dict[str, str | list[str]]]:
    # Build mapping dictionaries
    board_to_pio_env: dict[str, str | list[str]] = {}
    pio_env_to_platform: dict[str, str] = {}
    pio_env_to_board: dict[str, str] = {}

    # Read the environments from the PlatformIO config and
    for section, section_data in pio_config.items():
        if not section.startswith("env:") or not isinstance(section_data, dict):
            continue
        pio_env_name = section[len("env:") :]
        board = section_data.get("board")
        platform = section_data.get("platform")
        if (
            not isinstance(board, str)
            or not isinstance(platform, str)
            or board in [None, ""]
            or platform in [None, ""]
        ):
            print(
                f"::warning::Board or platform is missing for environment '{pio_env_name}' in PlatformIO config. This environment will be ignored."
            )
            continue
        # build the mappings from environments to boards and platforms.
        # NOTE: PlatformIO does not allow duplicate environment names, so we can safely assume that
        # each environment name maps to a single board.
        pio_env_to_board[pio_env_name] = board
        pio_env_to_platform[pio_env_name] = platform

    # build a mapping from boards to environments
    # NOTE: This mapping *only applies to this configuration!*
    # NOTE: This could be a one-to-many mapping.
    # While the board names themselves are unique,
    # the same board can be used in multiple environments with different flags.
    for env, board in pio_env_to_board.items():
        # if it's already a list, append to it, otherwise convert it to a list and append
        if isinstance(board_to_pio_env.get(board), list):
            board_to_pio_env[board].append(env)  # type: ignore
        else:
            board_to_pio_env[board] = [env]  # type: ignore
    return pio_env_to_board, pio_env_to_platform, board_to_pio_env


# %%
# cSpell:ignore dups
