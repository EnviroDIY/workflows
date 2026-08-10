# Matrix Generation Customization Guide

This document explains how to customize the job matrix generation in your repository when using the modular matrix generation system.

## Overview

The matrix generation system is now split into modular scripts that allow customization at different levels:

1. **Level 1**: Use the default modular system (no customization)
2. **Level 2**: Customize the matrix using `build_job_matrix.py`
3. **Level 3**: Complete custom generator using `generate_job_matrix.py`

## Level 1: Default Usage

The workflow will automatically use the default modular scripts:

- Configuration, parsing, matrix building, job generation all handled automatically
- No special files needed in your repository
- Supports all workflow inputs: `boards_to_build`, `boards_to_ignore`, `examples_to_build`, `examples_to_ignore`

## Level 2: Custom Matrix (Recommended)

To customize only the matrix assembly logic, create `continuous_integration/build_job_matrix.py`:

```python
# continuous_integration/build_job_matrix.py
"""
Custom matrix builder for this repository.
"""
import json


def build_custom_matrix(config):
    """
    Build a custom job matrix.

    Args:
        config (dict): Configuration from previous scripts containing:
            - compiler_list: List of compilers to use
            - examples_to_build: List of examples
            - boards: List of boards
            - inline_flags: List of inline flags
            - compiler_flags: List of compiler flags
            - pio_to_acli: Board conversion mapping
            - board_to_pio_env: PlatformIO environment mapping
            - pio_env_to_board: Reverse mapping
            - acli_skip_boards: Boards to skip for Arduino CLI
            - pio_skip_boards: Boards to skip for PlatformIO

    Returns:
        list[dict]: List of matrix items with keys:
            - compiler: "arduino-cli" or "pio"
            - example: example path
            - board: board name
            - inline_flags: list of flags
            - compiler_flags: list of flags
            - (optional) any other keys for grouping
    """
    from matrix_utils import dict_product, remove_duplicate_dicts

    compiler_list = config.get("compiler_list", ["arduino-cli", "pio"])
    examples_to_build = config["examples_to_build"]
    boards = config["boards"]
    inline_flags = config["inline_flags"]
    compiler_flags = config["compiler_flags"]

    # Custom logic example: exclude certain combinations
    # For example, only build with Arduino CLI for certain boards

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

    # Apply custom filters
    filtered_matrix = []
    for item in cart_join:
        # Example: exclude certain board/compiler combinations
        if item["board"] == "specialized_board" and item["compiler"] == "arduino-cli":
            continue  # Skip this combination

        filtered_matrix.append(item)

    # Deduplicate and sort
    final_matrix = remove_duplicate_dicts(filtered_matrix)
    final_matrix = sorted(
        final_matrix,
        key=lambda x: (
            x["compiler"],
            x["board"],
            x["example"],
            x["inline_flags"],
            x["compiler_flags"],
        ),
    )

    return final_matrix
```

### Example Customizations

#### 1. Skip Specific Board/Compiler Combinations

```python
def build_custom_matrix(config):
    # ... setup code ...

    filtered_matrix = []
    for item in cart_join:
        # Skip Arduino CLI for boards that don't support it well
        if item["board"] in ["esp32", "esp32s2"] and item["compiler"] == "arduino-cli":
            continue
        filtered_matrix.append(item)

    return filtered_matrix
```

#### 2. Limit Matrix Size

```python
def build_custom_matrix(config):
    # ... setup code ...

    # Only build one example per compiler/board combination
    filtered_matrix = []
    seen = set()
    for item in sorted(cart_join, key=lambda x: x["example"]):
        key = (item["compiler"], item["board"])
        if key not in seen:
            filtered_matrix.append(item)
            seen.add(key)

    return filtered_matrix
```

#### 3. Custom Board/Example Combinations

```python
def build_custom_matrix(config):
    # Only test specific combinations
    specific_combos = [
        {"compiler": "arduino-cli", "example": "examples/Example1", "board": "arduino_uno"},
        {"compiler": "pio", "example": "examples/Example1", "board": "arduino_uno"},
        {"compiler": "pio", "example": "examples/Example2", "board": "esp32"},
    ]

    # Add flags to each combination
    from copy import deepcopy
    final_matrix = []
    for combo in specific_combos:
        for inline_flag in config["inline_flags"]:
            for compiler_flag in config["compiler_flags"]:
                item = deepcopy(combo)
                item["inline_flags"] = inline_flag if isinstance(inline_flag, list) else [inline_flag]
                item["compiler_flags"] = compiler_flag if isinstance(compiler_flag, list) else [compiler_flag]
                final_matrix.append(item)

    return final_matrix
```

## Level 3: Complete Custom Generator

If you need to completely override the matrix generation, create `continuous_integration/generate_job_matrix.py`:

The workflow will detect this file and use it instead of the modular scripts. Copy the entire original `build_scripts/generate_job_matrix.py` and modify it as needed.

**Warning**: This bypasses all modular scripts, so you're responsible for:

- Downloading and managing config files
- Parsing workflow inputs
- Generating output in the correct format
- Setting GitHub outputs

## Environment Variables

The following environment variables are set by the workflow:

- `BOARDS_TO_BUILD`: Comma-separated list of boards (or empty for all)
- `BOARDS_TO_IGNORE`: Comma-separated list of boards to exclude
- `EXAMPLES_TO_BUILD`: Comma-separated list of examples (or empty for all)
- `EXAMPLES_TO_IGNORE`: Comma-separated list of examples to exclude
- `RUNNER_DEBUG`: "1" for verbose output
- `GITHUB_WORKSPACE`: Set in GitHub Actions only
- `GITHUB_OUTPUT`: Path to output file (set in GitHub Actions only)

## Output Format

The modular scripts produce two job matrices that must be output as JSON:

```json
[
  {
    "job_name": "arduino-cli - your_board - Your Example",
    "job_tag": "arduino-cli-your-board-your-example",
    "script": "/path/to/continuous_integration_artifacts/arduino-cli-your-board-your-example.sh"
  },
  ...
]
```

These are output to:

- `GITHUB_OUTPUT` (for GitHub Actions)
- `continuous_integration_artifacts/arduino_job_matrix.json`
- `continuous_integration_artifacts/pio_job_matrix.json`

## Testing Locally

To test locally:

```bash
# Set up environment variables
export BOARDS_TO_BUILD=""
export BOARDS_TO_IGNORE=""
export EXAMPLES_TO_BUILD=""
export EXAMPLES_TO_IGNORE=""
export RUNNER_DEBUG="1"  # For verbose output

# Run the orchestrator
python build_scripts/generate_job_matrix_orchestrator.py

# Or run individual scripts
python build_scripts/1_configure_matrix.py
python build_scripts/2_parse_inputs.py
python build_scripts/3_build_matrix.py
python build_scripts/4_build_jobs.py
python build_scripts/5_output_results.py
python build_scripts/6_cleanup.py  # Only runs locally
```

The generated matrices and scripts will be in `continuous_integration_artifacts/`.

## Troubleshooting

### Custom matrix builder not being called

- Ensure `continuous_integration/build_job_matrix.py` exists
- Ensure it has a `build_custom_matrix(config)` function
- Check workflow debug output with `RUNNER_DEBUG=1`

### Wrong boards in matrix

- Check that board names match your `platformio.ini`
- Use workflow input `boards_to_build` or `boards_to_ignore`
- Verify board conversion file includes your boards

### Missing examples

- Ensure examples follow the naming convention: `examples/ExampleName/ExampleName.ino`
- Examples in excluded folders (.history, archive, logger_test, tests, more) are skipped
- Use workflow input `examples_to_build` or `examples_to_ignore`

## Reference

### Matrix Item Keys

Default keys in each matrix item:

- `compiler`: "arduino-cli" or "pio"
- `example`: relative path to example
- `board`: board name
- `inline_flags`: list of inline #define flags
- `compiler_flags`: list of compiler flags

You can add additional keys for custom grouping logic.
