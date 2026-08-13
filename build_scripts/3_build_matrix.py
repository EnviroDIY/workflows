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

# %%
import os
import json
import sys
from build_utils import dict_product, remove_nested_duplicates
from build_config import (
    get_extended_config,
    set_verbose_mode,
    print_verbose,
    write_config_file,
)

def build_default_matrix(config: dict):
    """Build the default matrix using dict_product"""
    print("Building default job matrix...")

    workspace_path = config.get("workspace_path", os.getcwd())
    examples_to_build = config.get("examples_to_build", [])
    build_envs = config.get("build_envs", [])
    build_fqbns = config.get("build_fqbns", [])
    inline_defines = config.get("inline_defines", [])
    compiler_flags = config.get("compiler_flags", [])

    p_cart_join = list(
        dict_product(
            {
                "compiler": ["platformio"],
                "example": examples_to_build,
                "pio_env": build_envs,
                "inline_defines": inline_defines,
                "compiler_flags": compiler_flags,
            }
        )
    )

    a_cart_join = list(
        dict_product(
            {
                "compiler": ["arduino-cli"],
                "example": examples_to_build,
                "fqbn": build_fqbns,
                "inline_defines": inline_defines,
                "compiler_flags": compiler_flags,
            }
        )
    )

    cart_join = p_cart_join + a_cart_join
    cart_join_list = [json.dumps(e) for e in cart_join]
    print(f"Total possible combinations: {len(cart_join)}")

    # Apply matrix exclusions (empty by default)
    matrix_exclusions = []
    expanded_matrix_exclusions = []
    for exclusion in matrix_exclusions:
        exclusion_list = list(dict_product(exclusion))
        expanded_matrix_exclusions.extend(exclusion_list)

    expanded_matrix_exclusions_set = remove_nested_duplicates(
        expanded_matrix_exclusions
    )
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

    expanded_matrix_inclusions_set = remove_nested_duplicates(
        expanded_matrix_inclusions
    )
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
            (
                x["board"]
                if "board" in x
                else x["pio_env"] if "pio_env" in x else x.get("fqbn", "")
            ),
            x["example"],
            x["inline_defines"],
            x["compiler_flags"],
        ),
    )

    for matrix_entry in assembled_matrix:
        example = matrix_entry["example"]
        example_name = os.path.split(example)[-1]
        example_full_path = os.path.join(workspace_path, example, example_name + ".ino")
        matrix_entry["other_commands"] = [
            r"sed -i 's/#define TINY_GSM_MODEM_/\/\/ #define TINY_GSM_MODEM_/g' "
            + f'"{example_full_path}"'
        ]

    final_matrix = remove_nested_duplicates(assembled_matrix)
    print(f"Final filtered matrix: {len(final_matrix)}")

    return final_matrix


def build_custom_matrix(config: dict) -> list[dict] | None:
    """
    Allow custom matrix builder script.

    Looks for: continuous_integration/build_job_matrix.py
    That script should define a function: build_custom_matrix(config) -> list[dict]
    """
    if not os.path.exists(os.path.join(config["ci_path"], "build_job_matrix.py")):
        return None

    # Import and run custom builder
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "custom_matrix_builder", os.path.join(config["ci_path"], "build_job_matrix.py")
    )
    if spec is not None:
        custom_module = importlib.util.module_from_spec(spec)
        if spec.loader is not None:
            spec.loader.exec_module(custom_module)

        if hasattr(custom_module, "build_custom_matrix"):
            return custom_module.build_custom_matrix(config)

    print("::warning::Custom matrix builder does not have build_custom_matrix function")
    return None


# %%
if __name__ == "__main__":
    print("=" * 60)
    print("CI Build Pipeline: Build Matrix")
    print("=" * 60)

    print_verbose(
        "Reading configuration from environment variables, command line arguments, and the config file..."
    )
    args = get_extended_config()
    set_verbose_mode(args.verbose)

    # Try custom matrix builder first
    final_matrix = build_custom_matrix(vars(args))

    # Fall back to default
    if final_matrix is None:
        final_matrix = build_default_matrix(vars(args))

    # Save matrix to config for next script
    args.final_matrix = final_matrix

    # Save to file for next script
    print_verbose("Writing updated configuration to file...")
    config_file = write_config_file(args)

    print(f"\nFinal matrix saved to: {config_file}")


# %%
# CSpell:ignore fqbns
