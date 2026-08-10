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
"""

import os
import sys
import re
import json
from copy import deepcopy
from typing import List, Optional
from matrix_utils import get_filename_slug, print_verbose

# Global config
use_verbose = os.environ.get("RUNNER_DEBUG") == "1"


def create_arduino_cli_compile_command(
    workspace_path: str,
    code_subfolder: str,
    fqbn: str,
    arduino_cli_config: str,
    arduino_cli_format: str,
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
    pio_config_file: str,
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
    if use_pio_config_file:
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
            "arduino-cli" if "arduino-cli" in job.get("command", [""])[0] else "pio"
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
    board = matrix_item.get("board", "")
    compiler_flags = list(matrix_item.get("compiler_flags", []))
    inline_flags = list(matrix_item.get("inline_flags", []))

    job_dict = deepcopy(matrix_item)
    job_dict["inline_flags"] = inline_flags
    output_file_name = get_filename_for_log(
        job_dict, artifact_path, list(matrix_item.keys())
    )

    if compiler == "arduino-cli":
        pio_to_acli = config["pio_to_acli"]
        acli_skip_boards = config["acli_skip_boards"]

        acli_board = (
            board if board in pio_to_acli else config["pio_env_to_board"].get(board)
        )
        if acli_board not in pio_to_acli or board in acli_skip_boards:
            if use_verbose:
                print(
                    f"Skipping {example} for {board} because no matching Arduino FQBN was found."
                )
            return None
        fqbn = pio_to_acli[acli_board]["fqbn"]
        build_command = create_arduino_cli_compile_command(
            workspace_path=workspace_path,
            code_subfolder=example,
            fqbn=fqbn,
            arduino_cli_config=config["arduino_cli_config"],
            arduino_cli_format=config["arduino_cli_format"],
            compiler_flags=compiler_flags,
        )
    elif compiler == "pio":
        pio_skip_boards = config["pio_skip_boards"]

        if board in pio_skip_boards:
            if use_verbose:
                print(
                    f"Skipping {example} for {board} because it is in the list of boards to skip for PlatformIO."
                )
            return None

        pio_board_or_env = board
        use_pio_config_file = board in config["pio_env_to_board"].keys()

        build_command = create_pio_ci_compile_command(
            workspace_path=workspace_path,
            code_subfolder=example,
            pio_board_or_env=pio_board_or_env,
            pio_config_file=config["pio_config_file"],
            use_pio_config_file=use_pio_config_file,
            compiler_flags=compiler_flags,
        )
    else:
        raise ValueError("Invalid compiler provided.")

    # Handle inline flags (sed commands)
    example_name = os.path.split(example)[-1]
    example_full_path = os.path.join(workspace_path, example, example_name + ".ino")
    sed_commands: List[str] = []
    for flag in inline_flags:
        if len(flag) > 0:
            define_name, _, define_value = flag.partition("=")
            sed_commands.append(
                f"sed -i '1i\\\n#if !defined({define_name})\\\n"
                f"#define {define_name}{' ' if define_value else ''}{define_value}\\\n"
                f'#endif\\\n\' "{example_full_path}"'
            )

    job_dict["output_file_name"] = output_file_name
    job_dict["other_commands"] = sed_commands
    job_dict["build_commands"] = [build_command]

    return deepcopy(job_dict)


if __name__ == "__main__":
    # Load config
    artifact_path = os.environ.get("ARTIFACT_PATH", "continuous_integration_artifacts")
    config_file = os.path.join(artifact_path, "matrix_config.json")

    with open(config_file, "r") as f:
        config = json.load(f)

    workspace_path = config["workspace_path"]
    final_matrix = config["final_matrix"]

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
        print(f"Using log grouping fields from config: {log_groupers}")
    else:
        log_groupers = list(final_matrix[0].keys())
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

        l_key = "-".join(l_names)
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
    end_job_commands: List[str] = ["\n\nexit $status"]

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
        if v["compiler"] == "pio"
    ]

    # Save to config
    config["arduino_job_matrix"] = arduino_job_matrix
    config["pio_job_matrix"] = pio_job_matrix

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nJob matrices saved to: {config_file}")

# cSpell:ignore acli_board
