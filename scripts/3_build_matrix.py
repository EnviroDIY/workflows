#!/usr/bin/env python
"""
Build the job matrix from parsed inputs.

Creates a matrix by combining:
- Compilers (arduino-cli, pio)
- Examples
- Boards
- Inline flags
- Compiler flags

Supports custom matrix builders via external scripts.
"""

import os
import json
import sys
from matrix_utils import dict_product, remove_duplicate_dicts, print_verbose


def build_default_matrix(
    compiler_list, examples_to_build, boards, inline_flags, compiler_flags
):
    """Build the default matrix using dict_product"""
    print("Building default job matrix...")

    cart_join = list(
        dict_product(
            {
                "compiler": compiler_list,
                "example": examples_to_build,
                "board": boards,
                "inline_flags": inline_flags,
                "compiler_flags": compiler_flags,
            }
        )
    )

    cart_join_list = [json.dumps(e) for e in cart_join]
    print(f"Total possible combinations: {len(cart_join)}")

    # Apply matrix exclusions (empty by default)
    matrix_exclusions = []
    expanded_matrix_exclusions = []
    for exclusion in matrix_exclusions:
        exclusion_list = list(dict_product(exclusion))
        expanded_matrix_exclusions.extend(exclusion_list)

    expanded_matrix_exclusions_set = remove_duplicate_dicts(expanded_matrix_exclusions)
    expanded_matrix_exclusions_list = [
        json.dumps(e) for e in expanded_matrix_exclusions_set
    ]
    print(f"Matrix exclusions: {len(expanded_matrix_exclusions_list)}")

    # Apply matrix inclusions (empty by default - includes all)
    matrix_inclusions = []
    expanded_matrix_inclusions = []
    for inclusion in matrix_inclusions:
        inclusion_list = list(dict_product(inclusion))
        expanded_matrix_inclusions.extend(inclusion_list)

    expanded_matrix_inclusions_set = remove_duplicate_dicts(expanded_matrix_inclusions)
    expanded_matrix_inclusions_list = [
        json.dumps(e) for e in expanded_matrix_inclusions_set
    ]
    print(f"Matrix inclusions: {len(expanded_matrix_inclusions_list)}")

    # Filter matrix
    assembled_matrix = [
        json.loads(e)
        for e in cart_join_list
        if e not in expanded_matrix_exclusions_list
        and (
            len(expanded_matrix_inclusions_list) == 0
            or e in expanded_matrix_inclusions_list
        )
    ]

    assembled_matrix = sorted(
        assembled_matrix,
        key=lambda x: (
            x["compiler"],
            x["board"],
            x["example"],
            x["inline_flags"],
            x["compiler_flags"],
        ),
    )

    final_matrix = remove_duplicate_dicts(assembled_matrix)
    print(f"Final filtered matrix: {len(final_matrix)}")

    return final_matrix


def build_custom_matrix(config_path: str) -> list[dict] | None:
    """
    Allow custom matrix builder script.

    Looks for: continuous_integration/build_job_matrix.py
    That script should define a function: build_custom_matrix(config) -> list[dict]
    """
    if not os.path.exists("continuous_integration/build_job_matrix.py"):
        return None

    print(
        "Loading custom matrix builder from continuous_integration/build_job_matrix.py..."
    )

    # Load the config
    with open(config_path, "r") as f:
        config = json.load(f)

    # Import and run custom builder
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "custom_matrix_builder", "continuous_integration/build_job_matrix.py"
    )
    if spec is not None:
        custom_module = importlib.util.module_from_spec(spec)
        if spec.loader is not None:
            spec.loader.exec_module(custom_module)

        if hasattr(custom_module, "build_custom_matrix"):
            return custom_module.build_custom_matrix(config)

    print("::warning::Custom matrix builder does not have build_custom_matrix function")
    return None


if __name__ == "__main__":
    # Load config from previous script
    artifact_path = os.environ.get("ARTIFACT_PATH", "continuous_integration_artifacts")
    config_file = os.path.join(artifact_path, "matrix_config.json")

    with open(config_file, "r") as f:
        config = json.load(f)

    # Get compiler list (default: both)
    compiler_list = os.environ.get("COMPILER_LIST", "arduino-cli,pio").split(",")
    compiler_list = [c.strip() for c in compiler_list]

    # Try custom matrix builder first
    final_matrix = build_custom_matrix(config_file)

    # Fall back to default
    if final_matrix is None:
        final_matrix = build_default_matrix(
            compiler_list,
            config["examples_to_build"],
            config["boards"],
            config["inline_flags"],
            config["compiler_flags"],
        )

    # Save matrix to config for next script
    config["final_matrix"] = final_matrix
    config["compiler_list"] = compiler_list

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nFinal matrix saved to: {config_file}")
