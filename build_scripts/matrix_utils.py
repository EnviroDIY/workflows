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

import os
import json
from itertools import product
from typing import List, Dict, Any

# %%
# Verbose output
use_verbose = False


def setup_verbose_mode() -> bool:
    """
    Initialize verbose mode from RUNNER_DEBUG environment variable.

    Returns:
        bool: True if verbose mode is enabled
    """

    global use_verbose
    if "RUNNER_DEBUG" in os.environ.keys() and os.environ["RUNNER_DEBUG"] == "1":
        use_verbose = True
    return use_verbose


# Initialize verbose mode on module import
setup_verbose_mode()


# %%
# Directory setup utilities
def get_workspace_path() -> str:
    """
    Get the workspace directory path.

    Handles both GitHub Actions and local development environments.

    Returns:
        str: Absolute path to the workspace directory
    """

    if "GITHUB_WORKSPACE" in os.environ.keys():
        workspace_dir = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    else:
        workspace_dir = os.getcwd()

    if os.path.basename(os.path.normpath(workspace_dir)) == "continuous_integration":
        workspace_dir = os.path.dirname(workspace_dir)

    workspace_path = os.path.abspath(os.path.realpath(workspace_dir))
    return workspace_path


def get_ci_directories() -> Dict[str, str]:
    """
    Get CI directory paths (workspace, CI, and artifacts) and create folders if they do not exist.

    Returns:
        dict: Dictionary with keys:
            - workspace_path: Root workspace directory
            - ci_path: Continuous integration directory
            - artifact_path: Artifacts output directory
    """

    workspace_path = get_workspace_path()

    if os.path.basename(os.path.normpath(workspace_path)) == "continuous_integration":
        workspace_path = os.path.dirname(workspace_path)

    print(f"Workspace Path: {workspace_path}")

    # The continuous integration directory
    ci_dir = "./continuous_integration/"
    ci_path = os.path.join(workspace_path, ci_dir)
    ci_path = os.path.abspath(os.path.realpath(ci_path))
    print(f"Continuous Integration Path: {ci_path}")
    if not os.path.exists(ci_path):
        print(f"Creating the directory for CI: {ci_path}")
        os.makedirs(ci_path, exist_ok=True)

    # Artifacts directory
    artifact_dir = os.path.join(workspace_path, "continuous_integration_artifacts")
    artifact_path = os.path.abspath(os.path.realpath(artifact_dir))
    print(f"Artifact Path: {artifact_path}")
    if not os.path.exists(artifact_path):
        print(f"Creating the directory for artifacts: {artifact_path}")
        os.makedirs(artifact_path, exist_ok=True)

    return {
        "workspace_path": workspace_path,
        "ci_path": ci_path,
        "artifact_path": artifact_path,
    }


def get_working_directories() -> Dict[str, str]:
    """
    Gets all workspace directories including examples and extras.

    Returns:
        dict: Dictionary with keys:
            - workspace_path: Root workspace directory
            - examples_path: Examples directory
            - extras_path: Extras directory
            - ci_path: Continuous integration directory
            - artifact_path: Artifacts output directory
    """

    dirs = get_ci_directories()
    workspace_path = dirs["workspace_path"]

    # The examples directory
    examples_dir = "./examples/"
    examples_path = os.path.join(workspace_path, examples_dir)
    examples_path = os.path.abspath(os.path.realpath(examples_path))
    print(f"Examples Path: {examples_path}")

    # The extras directory
    extras_dir = "./extras/"
    extras_path = os.path.join(workspace_path, extras_dir)
    extras_path = os.path.abspath(os.path.realpath(extras_path))
    print(f"Extras Path: {extras_path}")

    dirs["examples_path"] = examples_path
    dirs["extras_path"] = extras_path

    return dirs


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


def remove_duplicate_dicts(list_with_dup_dicts):
    """Remove duplicates based on all keys except 'job_group'"""

    def sort_lists_in_dict(d):
        """Recursively sort any lists in the dictionary for consistent comparison"""
        result = {}
        for k, v in d.items():
            if isinstance(v, list):
                # Sort the list (convert each element to string for consistent ordering)
                result[k] = sorted(v, key=str)
            elif isinstance(v, dict):
                result[k] = sort_lists_in_dict(v)
            else:
                result[k] = v
        return result

    seen = set()
    deduped_list = []

    for d in list_with_dup_dicts:
        filtered_dict = {k: v for k, v in d.items() if k != "job_group"}
        sorted_dict = sort_lists_in_dict(filtered_dict)
        json_str = json.dumps(sorted_dict, sort_keys=True)
        if json_str not in seen:
            seen.add(json_str)
            deduped_list.append(d)
    return deduped_list


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

    if job_key in ["compiler", "board", "flag"]:
        return replace_all(value)
    elif (
        job_key in ["inline_flags", "compiler_flags"]
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
    elif job_key in ["inline_flags", "compiler_flags"] and isinstance(value, list):
        return "-".join([replace_all(f) for f in value])
    elif job_key in ["inline_flags", "compiler_flags"] and isinstance(value, str):
        return replace_all(value)
    elif job_key == "example":
        return replace_all(str(value).rsplit(os.path.sep)[-1])
    else:
        return replace_all(str(value))


def print_verbose(msg: str) -> None:
    """Print debug message if verbose mode is enabled"""
    if use_verbose:
        print(f"::debug::{msg}")


# %%
# Platform and board configuration utilities


# %%
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


def load_example_dependencies(workspace_path: str) -> dict:
    """
    Load example dependencies from examples/example_dependencies.json.

    Returns:
        dict: Example specification with 'dependencies' key
    """

    examples_dir = os.path.join(workspace_path, "examples")
    examples_deps_file = os.path.join(examples_dir, "example_dependencies.json")

    if os.path.isfile(examples_deps_file):
        with open(examples_deps_file) as f:
            return json.load(f)
    return {"dependencies": []}
