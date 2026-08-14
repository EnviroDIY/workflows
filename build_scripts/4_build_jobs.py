#!/usr/bin/env python
"""
Build command blocks and job scripts from the final matrix.

Converts the matrix into:
1. Command blocks (commands for each matrix item)
2. Log groups (grouped by log_groupers)
3. Jobs (grouped by job_groupers)
4. Bash scripts for each job

This script handles:
- Creating compile commands (Arduino CLI and PlatformIO)
- Processing extra commands (like sed for inline flags)
- Grouping commands for logging
- Generating bash scripts

Output job matrices to GitHub outputs and artifacts.

Writes:
- JSON matrices to continuous_integration_artifacts/
- GitHub outputs for matrices
- Summary information
"""

# %%
import os
import sys
import re
import json
from copy import deepcopy
from typing import List, Optional
from build_utils import get_filename_slug, save_json_file
from build_config import get_extended_config, set_verbose_mode, print_verbose

# Global config
use_verbose = os.environ.get("RUNNER_DEBUG") == "1"


def create_arduino_cli_compile_command(
    workspace_path: str,
    code_subfolder: str,
    fqbn: str,
    arduino_cli_config: str,
    arduino_cli_format: str = "json",
    compiler_flags: List[str] = [],
) -> str:
    """Create an Arduino CLI compile command"""
    arduino_command_args = [
        "arduino-cli",
        "compile",
    ]
    if use_verbose:
        arduino_command_args += ["--verbose"]
    arduino_command_args += [
        "--warnings",
        "more",
        "--config-file",
        f'"{arduino_cli_config}"',
        "--format",
        f"{arduino_cli_format}",
        "--fqbn",
        fqbn,
    ]
    if len(compiler_flags) > 0:
        arduino_command_args += [
            "--build-property",
            "compiler.cpp.extra_flags=" + " ".join(compiler_flags),
        ]
    arduino_command_args += [
        f'"{os.path.join(workspace_path, code_subfolder)}"',
    ]
    return " ".join(arduino_command_args)


def create_pio_ci_compile_command(
    workspace_path: str,
    code_subfolder: str,
    pio_board_or_env: str | List[str],
    pio_config_file: str | None,
    use_pio_config_file: bool,
    compiler_flags: List[str] | None = None,
    use_run: bool = False,
) -> str:
    """Create a PlatformIO compile command"""
    if compiler_flags is None:
        compiler_flags = []
    pio_command_args = [
        "pio",
        "run" if use_run else "ci",
    ]
    if use_verbose:
        pio_command_args += ["--verbose"]
    if use_pio_config_file and pio_config_file is not None:
        pio_command_args += ["--project-conf", f'"{pio_config_file}"']
        if isinstance(pio_board_or_env, str):
            pio_command_args += ["--environment", pio_board_or_env]
        else:
            for pio_board_or_env_item in pio_board_or_env:
                pio_command_args += [
                    "--environment",
                    pio_board_or_env_item,
                ]
    elif not use_run:
        if isinstance(pio_board_or_env, str):
            pio_command_args += [
                "--board",
                pio_board_or_env,
            ]
        else:
            for pio_board_or_env_item in pio_board_or_env:
                pio_command_args += [
                    "--board",
                    pio_board_or_env_item,
                ]
    else:
        raise ValueError(
            "you must be using a pio config file if you are using the 'run' command"
        )
    if use_run:
        artifact_dir = os.environ.get(
            "ARTIFACT_PATH", "continuous_integration_artifacts"
        )
        pio_command_args += [
            "--project-dir",
            f'"{os.path.realpath(os.path.join(artifact_dir, "pio_ci_build"))}"',
        ]
    if len(compiler_flags) > 0 and not use_pio_config_file and not use_run:
        pio_command_args += [
            "--project-option",
            f"\"build_flags = {' '.join(compiler_flags)}\"",
        ]
    if not use_run:
        pio_command_args += [
            f'"{os.path.join(workspace_path, code_subfolder)}"',
        ]

    return " ".join(pio_command_args)


def get_filename_for_log(job: dict, artifact_path: str, name_keys: list) -> str:
    """Generate filename for log output"""
    if "compiler" in job:
        compiler = job["compiler"]
    else:
        compiler = (
            "arduino-cli"
            if "arduino-cli" in job.get("command", [""])[0]
            else "platformio"
        )
    extension = "json" if compiler == "arduino-cli" else "log"

    file_name = ""
    for key in name_keys:
        if key not in job:
            raise ValueError(f"Job dictionary must contain the key '{key}'")
        if job[key] is not None and job[key] != "" and job[key] != []:
            file_name += "_" + get_filename_slug(key, job[key])

    if file_name.startswith("_"):
        file_name = file_name[1:]
    return os.path.abspath(
        os.path.join(
            artifact_path,
            f"{file_name}.{extension}",
        )
    )


def group_and_log_commands(
    build_commands: List[str],
    other_commands: List[str],
    group_title: str,
    output_filename: str,
) -> List[str]:
    """Create a log group with build commands"""
    command_list = []
    command_list.append("\necho ::group::{}".format(group_title))
    command_list.append("group_failed=0")
    command_list.extend(other_commands)
    for command in build_commands:
        if command.startswith("sed"):
            command_list.append(command)
        else:
            command_list.append(command + ' 2>&1 | tee -a "{}"'.format(output_filename))
            command_list.append("result_code=${PIPESTATUS[0]}")
            command_list.append(
                'if [ "$result_code" -ne "0" ]; then group_failed=1; status=1; fi'
            )
    command_list.append("echo ::endgroup::")
    command_list.append(
        f'if [ "$group_failed" -eq "0" ]; then echo -e "\\e[32m{group_title} successfully compiled\\e[0m"; else echo -e "\\e[31m{group_title} failed to compile\\e[0m"; fi'
    )
    return command_list


def create_command_list_from_matrix(
    matrix_item: dict,
    workspace_path: str,
    artifact_path: str,
    config: dict,
) -> Optional[dict]:
    """Convert a matrix item into a command block"""
    required_keys = ["compiler", "example", "board"]
    for key in required_keys:
        if key not in matrix_item:
            raise ValueError(f"Matrix item must contain the key '{key}'")

    compiler = matrix_item.get("compiler", "")
    example = matrix_item.get("example", "")
    compiler_flags = list(matrix_item.get("compiler_flags", []))
    inline_defines = list(matrix_item.get("inline_defines", []))

    job_dict = deepcopy(matrix_item)
    job_dict["inline_defines"] = inline_defines
    output_file_name = get_filename_for_log(
        job_dict,
        artifact_path,
        [
            k
            for k in matrix_item.keys()
            if k not in ["build_commands", "other_commands"]
        ],
    )

    if compiler == "arduino-cli":
        build_command = create_arduino_cli_compile_command(
            workspace_path=workspace_path,
            code_subfolder=example,
            fqbn=(
                matrix_item["fqbn"]
                if "fqbn" in matrix_item
                else matrix_item.get("board", "")
            ),
            arduino_cli_config=config["arduino_cli_config"],
            compiler_flags=compiler_flags,
        )
    elif compiler in ["platformio", "pio"]:
        build_command = create_pio_ci_compile_command(
            workspace_path=workspace_path,
            code_subfolder=example,
            pio_board_or_env=(
                matrix_item["pio_env"]
                if "pio_env" in matrix_item
                else matrix_item.get("board", "")
            ),
            pio_config_file=config["pio_config_file"],
            use_pio_config_file=True if "pio_config_file" in config else False,
            compiler_flags=compiler_flags,
        )
    else:
        raise ValueError("Invalid compiler provided.")

    # Handle inline flags (sed commands)
    example_name = os.path.split(example)[-1]
    example_full_path = os.path.join(workspace_path, example, example_name + ".ino")
    sed_commands: List[str] = []
    for flag in inline_defines:
        if len(flag) > 0:
            define_name, _, define_value = flag.partition("=")
            sed_commands.append(
                f"sed -i '1i\\\n#if !defined({define_name})\\\n"
                f"#define {define_name}{' ' if define_value else ''}{define_value}\\\n"
                f'#endif\\\n\' "{example_full_path}"'
            )

    job_dict["output_file_name"] = output_file_name
    job_dict["other_commands"] = matrix_item.get("other_commands", []) + sed_commands
    job_dict["build_commands"] = [build_command]

    return deepcopy(job_dict)


if __name__ == "__main__":
    print("=" * 60)
    print("CI Build Pipeline: Build Jobs")
    print("=" * 60)

    print_verbose(
        "Reading configuration from environment variables, command line arguments, and the config file..."
    )
    args = get_extended_config()
    set_verbose_mode(args.verbose)
    config = vars(args)

    workspace_path = args.workspace_path
    artifact_path = args.artifact_path
    final_matrix = args.final_matrix

    # if any("board" in matrix_item.keys() for matrix_item in final_matrix):
    #     import importlib.util

    #     file_name = "1_configure_workspace.py"
    #     spec = importlib.util.spec_from_file_location("module_name", file_name)
    #     if spec is None or spec.loader is None:
    #         raise ImportError(f"Could not load module from {file_name}")
    #     module = importlib.util.module_from_spec(spec)
    #     spec.loader.exec_module(module)

    #     # Read the PlatformIO config and build mapping dictionaries for boards and environments
    #     print_verbose("Reading the PlatformIO config...")
    #     pio_ini_dir = os.path.dirname(args.pio_config_file)
    #     pio_config = module.read_platformio_config(pio_ini_dir)
    #     print_verbose("Building mapping dictionaries...")
    #     pio_env_to_board, pio_env_to_platform, board_to_pio_env = (
    #         module.build_pio_mappings(pio_config)
    #     )

    #     print_verbose("Loading PlatformIO to Arduino board conversion mapping...")
    #     pio_env_to_fqbn, board_to_fqbn = module.load_pio_to_arduino_mapping()

    #     # Compile the list of Arduino FQBNs to build based on the inputs and the known boards
    #     print_verbose(
    #         "Compiling the list of Arduino FQBNs to build based on the inputs and the known boards..."
    #     )
    #     build_fqbns, build_cores = module.get_arduino_fqbns_to_build(
    #         args, pio_env_to_fqbn, board_to_fqbn
    #     )

    #     for n, matrix_item in enumerate(final_matrix):
    #         if "board" in matrix_item:
    #             board = matrix_item["board"]
    #             fqbn = module.match_board_to_fqbn(board, pio_env_to_fqbn, board_to_fqbn)
    #             env = module.match_board_to_env(
    #                 board, pio_env_to_board, board_to_pio_env
    #             )
    #             final_matrix[n]["fqbn"] = fqbn
    #             final_matrix[n]["pio_env"] = env

    # Convert matrix to command blocks
    print(f"Converting {len(final_matrix)} matrix items to command blocks...")
    complete_command_matrix: List[dict] = []
    for matrix_item in final_matrix:
        command_block = create_command_list_from_matrix(
            matrix_item=matrix_item,
            workspace_path=workspace_path,
            artifact_path=artifact_path,
            config=config,
        )
        if command_block is not None:
            complete_command_matrix.append(command_block)

    print(f"Total command blocks: {len(complete_command_matrix)}")

    # Group commands for logging
    if len(complete_command_matrix) == 0:
        print("::warning::No command blocks to process!")
        sys.exit(0)

    # Use log_grouping_fields from config, or default to all keys
    if "log_grouping_fields" in config and len(config["log_grouping_fields"]) > 0:
        log_groupers = config["log_grouping_fields"]
        if "build_commands" or "other_commands" in log_groupers:
            print(
                "::warning::'build_commands' and 'other_commands' should not be used as log grouping fields. They will be ignored."
            )
        # remove "build_commands" and "other_commands" from log_groupers if present
        log_groupers = [
            g for g in log_groupers if g not in ["build_commands", "other_commands"]
        ]
        print(f"Using log grouping fields from config: {log_groupers}")
    else:
        log_groupers = list(final_matrix[0].keys())
        # remove "build_commands" and "other_commands" from log_groupers if present
        log_groupers = [
            g for g in log_groupers if g not in ["build_commands", "other_commands"]
        ]
        print(f"Using all matrix keys as log grouping fields: {log_groupers}")
    grouped_command_matrix: dict[str, dict] = {}

    for matrix_item in complete_command_matrix:
        l_names = []
        for grouper in log_groupers:
            if grouper not in matrix_item.keys():
                raise ValueError(
                    f"Matrix item {matrix_item} does not have the key {grouper}"
                )
            elif matrix_item[grouper] is None:
                raise ValueError(
                    f"Matrix item {matrix_item} has a None value for the key {grouper}"
                )
            else:
                l_names.append(get_filename_slug(grouper, matrix_item[grouper]))

        l_key = "_".join(l_names)
        l_key = re.sub(r"[\-]{2,}", "-", l_key)
        l_key = re.sub(r"[_]{2,}", "_", l_key)

        l_command_list = group_and_log_commands(
            matrix_item["build_commands"],
            matrix_item["other_commands"],
            group_title=l_key,
            output_filename=matrix_item["output_file_name"],
        )

        if l_key not in grouped_command_matrix.keys():
            l_dict: dict = {
                "log_group": l_key,
                "group_commands": l_command_list,
            }
            for grouper in log_groupers:
                l_dict[grouper] = matrix_item[grouper]
            grouped_command_matrix[l_key] = l_dict
        else:
            grouped_command_matrix[l_key]["group_commands"] += l_command_list

    print(f"Total log groups: {len(grouped_command_matrix)}")

    # Group into jobs
    # Use job_grouping_fields from config, or default to ["compiler", "board"]
    if "job_grouping_fields" in config and len(config["job_grouping_fields"]) > 0:
        job_groupers = config["job_grouping_fields"]
        print(f"Using job grouping fields from config: {job_groupers}")
    else:
        job_groupers = ["compiler", "board"]
        print(f"Using default job grouping fields: {job_groupers}")
    grouped_job_matrix = {}

    for l_key, group_dict in grouped_command_matrix.items():
        j_names = []
        for grouper in job_groupers:
            if grouper not in group_dict.keys():
                raise ValueError(
                    f"Matrix item {group_dict} does not have the key {grouper}"
                )
            elif group_dict[grouper] is None:
                raise ValueError(
                    f"Matrix item {group_dict} has a None value for the key {grouper}"
                )
            else:
                j_names.append(get_filename_slug(grouper, group_dict[grouper]))

        job_name = " - ".join(j_names)
        job_tag = "-".join(j_names)

        if job_tag not in grouped_job_matrix.keys():
            j_dict: dict = {
                "job_name": job_name,
                "job_tag": job_tag.lower(),
                "job_command": group_dict["group_commands"],
            }
            for grouper in log_groupers:
                j_dict[grouper] = group_dict[grouper]
            grouped_job_matrix[job_tag] = j_dict
        else:
            grouped_job_matrix[job_tag]["job_command"] += group_dict["group_commands"]

    print(f"Total jobs: {len(grouped_job_matrix)}")

    # Generate bash scripts
    start_job_commands: List[str] = ["status=0"]
    end_job_commands: List[str] = [
        "\n\nls -R continuous_integration_artifacts",
        f"\n\nls -R {artifact_path}",
        "\n\nexit $status",
    ]

    for job_tag, matrix_job in grouped_job_matrix.items():
        bash_file_name = job_tag + ".sh"
        bash_file_path = os.path.join(artifact_path, bash_file_name)
        if use_verbose:
            print(f"Writing bash script to {bash_file_path}")

        with open(bash_file_path, "w") as bash_out:
            bash_out.write("#!/bin/bash\n\n")
            bash_out.write("""set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

""")
            bash_out.write("\n".join(start_job_commands))
            bash_out.write("\n\n")
            bash_out.write("\n".join(matrix_job["job_command"]))
            bash_out.write("\n\n")
            bash_out.write("\n".join(end_job_commands))

        matrix_job["script"] = bash_file_path

    # Prepare output matrices
    arduino_job_matrix = [
        {
            vk: vv
            for vk, vv in v.items()
            if vk == "job_name" or vk == "job_tag" or vk == "script"
        }
        for k, v in grouped_job_matrix.items()
        if v["compiler"] == "arduino-cli"
    ]

    pio_job_matrix = [
        {
            vk: vv
            for vk, vv in v.items()
            if vk == "job_name" or vk == "job_tag" or vk == "script"
        }
        for k, v in grouped_job_matrix.items()
        if v["compiler"] in ["platformio", "pio"]
    ]

    # Write matrices to JSON files
    artifact_path = config["artifact_path"]
    arduino_matrix_file = os.path.join(artifact_path, "arduino_job_matrix.json")
    pio_matrix_file = os.path.join(artifact_path, "pio_job_matrix.json")

    save_json_file(arduino_matrix_file, arduino_job_matrix)
    save_json_file(pio_matrix_file, pio_job_matrix)

    print(f"Arduino job matrix saved to: {arduino_matrix_file}")
    print(f"PlatformIO job matrix saved to: {pio_matrix_file}")

    # Output to GitHub
    if "GITHUB_OUTPUT" in os.environ.keys():
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            print(
                "arduino_job_matrix={}".format(json.dumps(arduino_job_matrix)), file=fh
            )
            print("pio_job_matrix={}".format(json.dumps(pio_job_matrix)), file=fh)
        print("Outputs written to GITHUB_OUTPUT")
    else:
        print("::notice::Not running in GitHub Actions, skipping GITHUB_OUTPUT")

    # Print summary
    print("\n=== Job Matrix Summary ===")
    print(f"Arduino CLI jobs: {len(arduino_job_matrix)}")
    print(f"PlatformIO jobs: {len(pio_job_matrix)}")
    print(f"Total jobs: {len(arduino_job_matrix) + len(pio_job_matrix)}")

    if len(arduino_job_matrix) > 0:
        print("\nArduino CLI jobs:")
        for job in arduino_job_matrix:
            print(f"  - {job['job_name']}")

    if len(pio_job_matrix) > 0:
        print("\nPlatformIO jobs:")
        for job in pio_job_matrix:
            print(f"  - {job['job_name']}")

# cSpell:ignore fqbns
