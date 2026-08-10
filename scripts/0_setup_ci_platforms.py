#!/usr/bin/env python
"""
Setup CI Platforms and Board Configurations.

Part of the CI Build Pipeline. This step:
- Sets up platform-to-board mappings
- Downloads board conversion files (PlatformIO to Arduino CLI)
- Validates board configurations
- Prepares platform configurations

Step 0a in the CI Build Pipeline sequence.
"""

import os
import json
from matrix_utils import (
    setup_ci_directories,
    load_pio_to_arduino_boards_mapping,
    load_board_to_pio_mapping,
    print_verbose,
)


# Configuration
# Boards to always skip on each platform
PIO_SKIP_BOARDS = ["esp32-c6-devkitm-1", "arduino_nano_esp32"]
ACLI_SKIP_BOARDS = ["uno_pic32", "genuino101", "bluepill_f103c8"]


def validate_boards(boards, pio_to_acli, board_to_pio_platform):
    """
    Validate that requested boards have valid configurations.
    
    Args:
        boards: List of board names to validate
        pio_to_acli: Dict mapping PlatformIO boards to Arduino FQBNs
        board_to_pio_platform: Dict mapping boards to PlatformIO platforms
    
    Returns:
        list: Validated board list (with invalid boards removed)
    """
    validated_boards = []
    
    for board in boards:
        # Check for Arduino CLI mapping
        if board not in pio_to_acli.keys() and board not in ACLI_SKIP_BOARDS:
            print(
                f"""::error:: file=platformio_to_arduino_boards.json,title=No matching Arduino board::
Cannot find matching Arduino FQBN for {board}.
No core will be installed or cached for this board.
Please check the spelling of your board name or add an entry to the Arduino/PlatformIO board conversion file."""
            )
            continue
        
        # Check for PlatformIO configuration
        if board not in board_to_pio_platform.keys() and board not in PIO_SKIP_BOARDS:
            print(
                f"""::error:: file=platformio.ini,title=No matching PlatformIO environment::
Cannot find matching PlatformIO environment for {board}.
No platform will be installed or built for this board.
Please check the spelling of your board name or add an entry to the platformio.ini file."""
            )
            continue
        
        validated_boards.append(board)
    
    return validated_boards


if __name__ == "__main__":
    print("=" * 60)
    print("CI Build Pipeline: Step 0a - Setup CI Platforms")
    print("=" * 60)
    
    # Setup directories
    dirs = setup_ci_directories()
    ci_path = dirs["ci_path"]
    
    print("\nLoading platform configurations...")
    
    # Load board configurations
    pio_to_acli = load_pio_to_arduino_boards_mapping(ci_path)
    print(f"Loaded {len(pio_to_acli)} PlatformIO to Arduino mappings")
    
    board_to_pio_env, board_to_pio_platform = load_board_to_pio_mapping(ci_path)
    print(f"Loaded {len(board_to_pio_env)} PlatformIO board configurations")
    
    # Load Arduino CLI config
    arduino_cli_config = os.path.join(ci_path, "arduino_cli.yaml")
    print(f"Arduino CLI config: {arduino_cli_config}")
    
    print("\n✓ Platform configurations loaded successfully")
    print("✓ Ready for dependency script generation and job matrix building")
