# CI Build Pipeline System

This document describes the modular CI Build Pipeline system for compiling examples with multiple compilers and boards.

## Overview

The CI Build Pipeline is a comprehensive system for:

- Configuring CI platforms and board mappings
- Generating library and platform installation scripts
- Building job matrices for parallel execution
- Generating build and compilation scripts
- Outputting results to GitHub and artifacts

The original monolithic `generate_job_matrix.py` script (900+ lines) has been split into modular components that allow for easier maintenance, testing, and customization.

## Architecture

### Core Components

```
build_scripts/
├── matrix_utils.py                     # Shared utilities and helper functions
├── 0_setup_ci_platforms.py             # Setup platform and board configurations
├── 0_generate_install_scripts.py       # Generate library installation scripts
├── 1_configure_matrix.py               # Setup CI directories and download configs
├── 2_parse_inputs.py                   # Parse workflow inputs
├── 3_build_matrix.py                   # Build job matrix (supports custom builders)
├── 4_build_jobs.py                     # Generate jobs and bash scripts
├── 5_output_results.py                 # Output to GitHub and artifacts
├── 6_cleanup.py                        # Cleanup generated files (local only)
├── generate_job_matrix.py              # Wrapper script (entry point)
├── generate_job_matrix_orchestrator.py # Optional orchestrator (for testing)
├── generate_platform_installation_script.py  # Deprecated (use 0_setup_ci_platforms.py)
├── generate_library_installation_script.py   # Deprecated (use 0_generate_install_scripts.py)
└── parse_test_results.py               # Post-build results parsing
```

### Workflow Integration

The workflow in `.github/workflows/build_examples.yaml` executes the pipeline in stages:

**Stage 1: Platform Setup**

1. Downloads and runs `0_setup_ci_platforms.py` to configure platforms

**Stage 2: Dependency Script Generation**

1. Downloads and runs `0_generate_install_scripts.py` to generate installation scripts

**Stage 3: Job Matrix Generation**

1. Checks for a custom generator (`continuous_integration/generate_job_matrix.py`)
2. If found, runs it (backward compatibility)
3. If not found, runs the modular pipeline:
   - `1_configure_matrix.py` - Setup workspace
   - `2_parse_inputs.py` - Parse inputs
   - `3_build_matrix.py` - Build matrix
   - `4_build_jobs.py` - Generate jobs
   - `5_output_results.py` - Output results

## Module Descriptions

### matrix_utils.py

Shared utilities used by all scripts:

**Directory Setup Functions**:

- `setup_verbose_mode()` - Initialize verbose mode from RUNNER_DEBUG
- `get_workspace_path()` - Get workspace directory (handles GitHub Actions and local)
- `setup_ci_directories()` - Setup workspace, CI, and artifact directories
- `setup_full_directories()` - Setup all directories including examples and extras

**Platform and Board Functions**:

- `load_board_to_pio_mapping()` - Load PlatformIO board mappings
- `load_pio_to_arduino_boards_mapping()` - Load Arduino FQBN mappings
- `load_arduino_cli_config()` - Load/download Arduino CLI configuration

**Dependency Functions**:

- `load_library_dependencies()` - Load library.json dependencies
- `load_example_dependencies()` - Load example_dependencies.json

**Matrix Functions**:

- `dict_product()` - Cartesian product of dictionary values
- `remove_duplicate_dicts()` - Deduplication function
- `get_filename_slug()` - Sanitize names for file paths
- `load_json_file()` / `save_json_file()` - JSON I/O helpers
- `print_verbose()` - Debug output

**Dependencies**: requests, platformio (optional)

### 0_setup_ci_platforms.py

Configures platforms and board mappings for the CI build system.

**Outputs**:

- Downloads and validates board configuration files
- Verifies Arduino CLI and PlatformIO mappings

**Key Functions**:

- `validate_boards()` - Validate boards have valid configurations
- Uses `load_pio_to_arduino_boards_mapping()` from matrix_utils
- Uses `load_board_to_pio_mapping()` from matrix_utils

**Dependencies**: matrix_utils, platformio, requests

### 0_generate_install_scripts.py

Generates platform and library installation scripts for build jobs.

**Outputs**: Four bash scripts in artifacts directory:

- `install-library-libdeps-arduino-cli.sh` - Library dependencies for Arduino CLI
- `install-example-libdeps-arduino-cli.sh` - Example dependencies for Arduino CLI
- `install-library-libdeps-platformio.sh` - Library dependencies for PlatformIO
- `install-example-libdeps-platformio.sh` - Example dependencies for PlatformIO

**Key Functions**:

- `get_package_spec()` - Convert dependency dict to PackageSpec
- `create_arduino_cli_lib_command()` - Generate Arduino CLI install commands
- Uses dependency loaders from matrix_utils

**Dependencies**: matrix_utils, platformio (optional)

### 1_configure_matrix.py

Configures the CI workspace and prepares configuration files.

**Outputs**: `matrix_config.json` with:

- All workspace paths
- Arduino CLI configuration
- PlatformIO configuration and board mappings
- Downloaded board conversion file

**Key Functions**:

- `setup_workspace_dirs()` - Initialize directory structure
- `download_board_conversion_file()` - Get board mappings
- `setup_arduino_cli_config()` - Arduino CLI config setup
- `setup_platformio_config()` - PlatformIO config setup

**Dependencies**: matrix_utils, requests, platformio

### 2_parse_inputs.py

Parses workflow inputs from environment variables.

**Inputs (Environment Variables)**:

- `EXAMPLES_TO_BUILD` - Comma-separated list or empty for all
- `EXAMPLES_TO_IGNORE` - Comma-separated list to exclude
- `BOARDS_TO_BUILD` - Comma-separated list or empty for all
- `BOARDS_TO_IGNORE` - Comma-separated list to exclude
- `INLINE_FLAGS` - Compiler flags (preprocessor defines)
- `COMPILER_FLAGS` - Build flags
- `ACLI_SKIP_BOARDS` - Boards to skip for Arduino CLI
- `PIO_SKIP_BOARDS` - Boards to skip for PlatformIO

**Outputs**: Updates `matrix_config.json` with parsed inputs

**Key Functions**:

- `parse_examples_to_build()` - Find or parse examples
- `parse_boards_to_build()` - Get boards from config
- `validate_boards()` - Check board compatibility
- `parse_inline_flags()` / `parse_compiler_flags()` - Parse flags

**Dependencies**: matrix_utils

### 3_build_matrix.py

Builds the job matrix from parsed inputs.

**Features**:

- Default matrix builder using `dict_product()`
- Support for custom matrix builders
- Matrix inclusion/exclusion filtering
- Duplicate removal and sorting

**Outputs**: Updates `matrix_config.json` with `final_matrix` and `compiler_list`

**Key Functions**:

- `build_default_matrix()` - Create matrix from inputs
- `build_custom_matrix()` - Load external custom builder

**Dependencies**: matrix_utils

### 4_build_jobs.py

Generates individual build jobs and compilation bash scripts.

**Outputs**:

- Job lists for GitHub Actions matrix
- Bash compilation scripts in artifacts

**Key Functions**:

- Job generation from matrix
- Build script generation with compiler flags

**Dependencies**: matrix_utils

### 5_output_results.py

Outputs generated configuration to GitHub Actions and artifacts.

**Outputs**:

- GitHub Actions output variables (job matrices)
- Configuration files to artifacts directory

**Key Functions**:

- Format job matrices for GitHub
- Write configuration to files

**Dependencies**: matrix_utils

### parse_test_results.py

Post-build results processing and beautification (run after compilation).

**Features**:

- Parse compilation output
- Generate test result reports
- Format logs for GitHub Actions

**Dependencies**: matrix_utils, pandas, requests

## Migration from Single Script

If you have a monolithic `generate_job_matrix.py` script:

1. Rename it to `generate_job_matrix_old.py` for backup
2. Update `.github/workflows/build_examples.yaml` to use the new modular pipeline
3. The workflow will automatically fall back to custom builders in `continuous_integration/`

## Customization

To use a custom matrix builder, create:

- `continuous_integration/generate_job_matrix.py` with a `build_custom_matrix(config)` function

The pipeline will automatically detect and use it instead of the default builder.

## Running Locally

```bash
# Download utilities
curl -O https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/matrix_utils.py

# Download and run pipeline
curl -O https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/0_setup_ci_platforms.py
python 0_setup_ci_platforms.py

curl -O https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/0_generate_install_scripts.py
python 0_generate_install_scripts.py

curl -O https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/{1,2,3,4,5,6}_*.py
python 1_configure_matrix.py
python 2_parse_inputs.py
python 3_build_matrix.py
python 4_build_jobs.py
python 5_output_results.py
```

## Environment Variables

- `RUNNER_DEBUG=1` - Enable verbose debug output
- `GITHUB_WORKSPACE` - Set automatically by GitHub Actions
- `ARTIFACT_PATH` - Override artifact directory (default: `continuous_integration_artifacts`)
- Board and example inputs (see 2_parse_inputs.py section)

## cSpell:words acli
