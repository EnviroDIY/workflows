#!/usr/bin/env python
"""
Parse workflow inputs from environment variables.

Parses:
- EXAMPLES_TO_BUILD: Comma-separated list of examples to build (or "all" for all)
- EXAMPLES_TO_IGNORE: Comma-separated list of examples to ignore
- BOARDS_TO_BUILD: Comma-separated list of boards to build (or "all" for all)
- BOARDS_TO_IGNORE: Comma-separated list of boards to ignore
- INLINE_FLAGS: Comma-separated list of inline compiler flags (e.g., -DFLAG=value)
- COMPILER_FLAGS: Comma-separated list of compiler flags
"""

import os
import json
from itertools import chain
from matrix_utils import print_verbose


def parse_examples_to_build(examples_path: str, extras_path: str):
    """Parse examples from environment or find all examples"""
    if "EXAMPLES_TO_BUILD" in os.environ.keys() and os.environ.get(
        "EXAMPLES_TO_BUILD", ""
    ) not in ["all", ""]:
        examples_to_build = [
            example.strip()
            for example in os.environ.get("EXAMPLES_TO_BUILD", "").split(",")
        ]
        print("Building only examples specified in environment.")
    else:
        print("Building all examples found in the example path.")
        examples_to_build = []
        excluded_folders = [".history", "archive", "logger_test", "tests", "more"]
        for root, subdirs, files in chain(os.walk(examples_path), os.walk(extras_path)):
            for filename in files:
                file_path = os.path.join(root, filename)
                if filename == os.path.split(root)[-1] + ".ino" and not any(
                    e in os.path.normpath(root).split(os.sep) for e in excluded_folders
                ):
                    examples_to_build.append(
                        os.path.relpath(root, os.path.dirname(examples_path))
                    )
                    print_verbose(f"Found example: {filename} (full path: {file_path})")

    # Remove any ignored examples from the list
    if "EXAMPLES_TO_IGNORE" in os.environ.keys() and os.environ.get(
        "EXAMPLES_TO_IGNORE"
    ) not in [""]:
        ex_ignore = os.environ.get("EXAMPLES_TO_IGNORE", "").split(",")
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

    return examples_to_build


def parse_boards_to_build(board_to_pio_env: dict, pio_to_acli: dict):
    """Parse boards from environment or use all available boards"""
    if "BOARDS_TO_BUILD" in os.environ.keys() and os.environ.get(
        "BOARDS_TO_BUILD", ""
    ) not in ["all", ""]:
        boards = [
            board.strip() for board in os.environ.get("BOARDS_TO_BUILD", "").split(",")
        ]
        print("Building only boards specified in environment.")
    else:
        boards = list(board_to_pio_env.keys())
        print("Building all boards available in the platformio.ini file.")

    # Remove any ignored boards from the list
    if "BOARDS_TO_IGNORE" in os.environ.keys() and os.environ.get(
        "BOARDS_TO_IGNORE", ""
    ) not in [""]:
        boards = [
            board
            for board in boards
            if board
            not in [
                board_.strip()
                for board_ in os.environ.get("BOARDS_TO_IGNORE", "").split(",")
            ]
        ]

    print(f"Total boards to build: {len(boards)}")
    print_verbose("Boards to build:")
    for board in boards:
        print_verbose(f"  - {board}")

    return boards


def validate_boards(
    boards: list,
    pio_to_acli: dict,
    board_to_pio_env: dict,
    acli_skip_boards: list,
    pio_skip_boards: list,
):
    """Validate that boards have matching configurations"""
    valid_boards = []
    for board in boards:
        has_arduino = board in pio_to_acli or board not in acli_skip_boards
        has_pio = board in board_to_pio_env or board not in pio_skip_boards

        if not has_arduino and not has_pio:
            print(
                f"::error::Board {board} has no matching configuration for either Arduino CLI or PlatformIO"
            )
            continue

        if board not in pio_to_acli and board not in acli_skip_boards:
            print(
                f"::warning::Cannot find matching Arduino FQBN for {board}. This board will not be compiled with Arduino CLI"
            )

        if board not in board_to_pio_env and board not in pio_skip_boards:
            print(
                f"::warning::No matching environment was found in platformio.ini for {board}. This board will be compiled with no reference to a specific environment."
            )

        valid_boards.append(board)

    return valid_boards


def parse_inline_flags():
    """Parse inline compiler flags from environment"""
    if "INLINE_FLAGS" in os.environ.keys() and os.environ.get(
        "INLINE_FLAGS", ""
    ) not in [
        "all",
        "",
    ]:
        inline_flags = [
            flag.strip() for flag in os.environ.get("INLINE_FLAGS", "").split(",")
        ]
        print(f"Using {len(inline_flags)} inline flags")
    else:
        inline_flags = [[]]
        print("No inline flags specified")

    return inline_flags


def parse_compiler_flags():
    """Parse compiler flags from environment"""
    if "COMPILER_FLAGS" in os.environ.keys() and os.environ.get(
        "COMPILER_FLAGS", ""
    ) not in ["all", ""]:
        compiler_flags = [
            flag.strip() for flag in os.environ.get("COMPILER_FLAGS", "").split(",")
        ]
        print(f"Using {len(compiler_flags)} compiler flags")
    else:
        compiler_flags = [[]]
        print("No compiler flags specified")

    return compiler_flags


if __name__ == "__main__":
    # Load config from previous script
    config_file = os.path.join(
        os.environ.get("ARTIFACT_PATH", "continuous_integration_artifacts"),
        "matrix_config.json",
    )
    with open(config_file, "r") as f:
        config = json.load(f)

    # Load board conversion data
    with open(config["pio_to_acli_file"], "r") as f:
        pio_to_acli = json.load(f)

    # Parse all inputs
    examples_to_build = parse_examples_to_build(
        config["examples_path"], config["extras_path"]
    )
    boards = parse_boards_to_build(config["board_to_pio_env"], pio_to_acli)

    # Validate boards
    acli_skip_boards = os.environ.get("ACLI_SKIP_BOARDS", "uno_pic32,genuino101").split(
        ","
    )
    pio_skip_boards = os.environ.get(
        "PIO_SKIP_BOARDS", "esp32-c6-devkitm-1,arduino_nano_esp32"
    ).split(",")
    boards = validate_boards(
        boards,
        pio_to_acli,
        config["board_to_pio_env"],
        acli_skip_boards,
        pio_skip_boards,
    )

    inline_flags = parse_inline_flags()
    compiler_flags = parse_compiler_flags()

    # Save parsed inputs to config file
    config["examples_to_build"] = examples_to_build
    config["boards"] = boards
    config["inline_flags"] = inline_flags
    config["compiler_flags"] = compiler_flags
    config["pio_to_acli"] = pio_to_acli
    config["acli_skip_boards"] = acli_skip_boards
    config["pio_skip_boards"] = pio_skip_boards

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nParsed inputs saved to: {config_file}")

# cSpell:ignore DFLAG
