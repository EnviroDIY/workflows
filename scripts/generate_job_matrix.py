#!/usr/bin/env python
# %%
import json
import shutil
import re
from typing import List
from platformio.project.config import ProjectConfig
import re
import os
import copy
from pathlib import Path

# %%
# Some working directories

# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys():
    workspace_dir = os.environ.get("GITHUB_WORKSPACE")
else:
    workspace_dir = os.getcwd()
workspace_path = os.path.abspath(os.path.realpath(workspace_dir))
print(f"Workspace Path: {workspace_path}")

# The examples directory
examples_dir = "./examples/"
examples_path = os.path.join(workspace_dir, examples_dir)
examples_path = os.path.abspath(os.path.realpath(examples_path))
print(f"Examples Path: {examples_path}")

# The continuous integration directory
ci_dir = "./continuous_integration/"
ci_path = os.path.join(workspace_dir, ci_dir)
ci_path = os.path.abspath(os.path.realpath(ci_path))
print(f"Continuous Integration Path: {ci_path}")

# A directory of files to save and upload as artifacts to use in future jobs
artifact_dir = os.path.join(
    os.path.join(workspace_dir, "continuous_integration_artifacts")
)
artifact_path = os.path.abspath(os.path.realpath(artifact_dir))
print(f"Artifact Path: {artifact_path}")

if not os.path.exists(artifact_dir):
    print(f"Creating the directory for artifacts: {artifact_path}")
    os.makedirs(artifact_dir)

compilers = ["Arduino CLI", "PlatformIO"]

# %%
# read configurations based on existing files and environment variables

# Arduino CLI configurations
if "GITHUB_WORKSPACE" in os.environ.keys():
    arduino_cli_config = os.path.join(workspace_dir, "arduino_cli.yaml")
else:
    arduino_cli_config = os.path.join(ci_dir, "arduino_cli_local.yaml")

# PlatformIO configurations
pio_config_file = os.path.join(ci_path, "platformio.ini")
have_pio_config_file = False
if os.path.isfile(pio_config_file):
    have_pio_config_file = True
    pio_config = ProjectConfig(pio_config_file)
    board_to_pio_env = {}
    for pio_env_name in pio_config.envs():
        board_to_pio_env[pio_config.get("env:{}".format(pio_env_name), "board")] = (
            pio_env_name
        )
    boards = list(board_to_pio_env.values())
elif "BOARDS_TO_BUILD" in os.environ.keys():
    boards = os.environ.get("BOARDS_TO_BUILD").split(",")
else:
    boards = ["mayfly"]

# %%
# Get the examples to build
if "EXAMPLES_TO_BUILD" in os.environ.keys():
    examples_to_build = os.environ.get("EXAMPLES_TO_BUILD").split(",")
else:
    # Find all of the examples in the examples folder, append the path "examples" to it
    examples_to_build = [
        f"examples/{f}"
        for f in os.listdir(examples_path)
        if os.path.isdir(os.path.join(examples_path, f))
        and f not in [".history", "logger_test", "menu_a_la_carte"]
    ]

# %%
# helper functions to create commands

# Translation between board names on PlatformIO and the Arduino CLI
pio_to_acli = {
    # EnviroDIY boards
    "mayfly": {"fqbn": "EnviroDIY:avr:envirodiy_mayfly"},
    # Official Arduino AVR boards
    "uno": {"fqbn": "arduino:avr:uno"},
    "megaatmega2560": {"fqbn": "arduino:avr:mega"},
    "leonardo": {"fqbn": "arduino:avr:leonardo"},
    # Official Arduino SAM boards
    "dueUSB": {"fqbn": "arduino:sam:arduino_due_x"},
    # Official Arduino SAMD boards
    "zeroUSB": {"fqbn": "arduino:samd:mzero_bl"},
    "mkrvidor4000": {"fqbn": "arduino:samd:mkrvidor4000"},
    # Official Arduino Mega AVR boards
    "nano_every": {"fqbn": "arduino:megaavr:nona4809"},
    "uno_wifi_rev2": {"fqbn": "arduino:megaavr:uno2018"},
    # Official Arduino ESP32 boards
    "arduino_nano_esp32": {"fqbn": "arduino:esp32:nano_nora"},
    # Official Arduino Rasberry Pi boards
    "pico": {"fqbn": "arduino:mbed_rp2040:pico"},
    # Official Arduino Renesas boards
    "uno_r4_wifi": {"fqbn": "arduino:renesas_uno:unor4wifi"},
    # Adafruit boards
    "adafruit_feather_m0": {"fqbn": "adafruit:samd:adafruit_feather_m0"},
    "adafruit_feather_m4": {"fqbn": "adafruit:samd:adafruit_feather_m4"},
    "adafruit_grandcentral_m4": {"fqbn": "adafruit:samd:adafruit_grandcentral_m4"},
    # Espressif Boards
    "nodemcuv": {"fqbn": "esp8266:esp8266:nodemcuv"},
    "nodemcuv2": {"fqbn": "esp8266:esp8266:nodemcuv2"},
    "esp32dev": {"fqbn": "esp32:esp32:esp32"},
    "esp32-c6-devkitc-1": {"fqbn": "esp32:esp32:esp32c6"},
    "esp32-c3-devkitm-1": {"fqbn": "esp32:esp32:esp32c3"},
    "esp32-s3-devkitm-1": {"fqbn": "esp32:esp32:esp32s3"},
}


def get_example_folder(subfolder_name):
    return os.path.join(examples_path, subfolder_name)


def get_example_filepath(subfolder_name):
    ex_folder = get_example_folder(subfolder_name)
    ex_file = os.path.join(ex_folder, subfolder_name + ".ino")
    return ex_file


def create_arduino_cli_command(code_subfolder: str, pio_board: str) -> str:
    arduino_command_arguments = [
        "arduino-cli",
        "compile",
        # "--verbose",
        "--warnings",
        "more",
        "--config-file",
        arduino_cli_config,
        "--format",
        "text",
        "--fqbn",
        pio_to_acli[pio_board]["fqbn"],
        os.path.join(workspace_path, code_subfolder),
    ]
    return " ".join(arduino_command_arguments)


def create_pio_ci_command(
    code_subfolder: str,
    pio_env: str,
    pio_env_file: str = pio_config_file,
    have_pio_config_file: bool = True,
) -> str:
    if have_pio_config_file:
        pio_command_args = [
            "pio",
            "ci",
            # "--verbose",
            "--project-conf",
            pio_env_file,
            "--environment",
            pio_env,
            os.path.join(workspace_path, code_subfolder),
        ]
    else:
        pio_command_args = [
            "pio",
            "ci",
            # "--verbose",
            "--board",
            pio_env,
            os.path.join(workspace_path, code_subfolder),
        ]
    return " ".join(pio_command_args)


def add_log_to_command(command: str, group_title: str) -> List:
    command_list = []
    command_list.append("\necho ::group::{}".format(group_title))
    command_list.append(command + " 2>&1 | tee output.log")
    command_list.append("result_code=${PIPESTATUS[0]}")
    command_list.append(
        'if [ "$result_code" -eq "0" ]; then echo " - {title} :white_check_mark:" >> $GITHUB_STEP_SUMMARY; else echo " - {title} :x:" >> $GITHUB_STEP_SUMMARY; fi'.format(
            title=group_title
        )
    )
    command_list.append(
        'if [ "$result_code" -eq "0" ] && [ "$status" -eq "0" ]; then status=0; else status=1; fi'
    )
    command_list.append("echo ::endgroup::")
    command_list.append(
        'if [ "$result_code" -eq "0" ]; then echo -e "\e[32m{title} successfully compiled\e[0m"; else echo -e "\e[31m{title} failed to compile\e[0m"; fi'.format(
            title=group_title
        )
    )
    return command_list


def create_logged_command(
    compiler: str,
    group_title: str,
    code_subfolder: str,
    pio_board: str,
    pio_env_file: str = pio_config_file,
):
    output_commands = []
    lower_compiler = compiler.lower().replace(" ", "").strip()
    if lower_compiler == "platformio":
        build_command = create_pio_ci_command(
            code_subfolder=code_subfolder, pio_env=pio_board, pio_env_file=pio_env_file
        )
    elif lower_compiler == "arduinocli":
        build_command = create_arduino_cli_command(
            code_subfolder=code_subfolder,
            pio_board=pio_board,
        )
    else:
        build_command = ""

    command_with_log = add_log_to_command(build_command, group_title)
    output_commands.extend(command_with_log)

    return copy.deepcopy(output_commands)


# %%
# set up outputs
arduino_job_matrix = []
pio_job_matrix = []
start_job_commands = "status=0"
end_job_commands = "\n\nexit $status"

# %%
# Create job info for the basic examples
# Use one job per board with one command per example
for example in examples_to_build:
    arduino_ex_commands = [
        start_job_commands,
    ]
    pio_ex_commands = [
        start_job_commands,
    ]

    for pio_board in boards:
        for compiler, command_list in zip(
            compilers, [arduino_ex_commands, pio_ex_commands]
        ):
            command_list.extend(
                create_logged_command(
                    compiler=compiler,
                    group_title=pio_board,
                    code_subfolder=example,
                    pio_board=pio_board,
                )
            )

    arduino_job_matrix.append(
        {
            "job_name": "Arduino - {}".format(example),
            "command": "\n".join(arduino_ex_commands + [end_job_commands]),
        }
    )
    pio_job_matrix.append(
        {
            "job_name": "Platformio - {}".format(example),
            "command": "\n".join(pio_ex_commands + [end_job_commands]),
        }
    )


# %%
# Convert commands in the matrix into bash scripts
for matrix_job in arduino_job_matrix + pio_job_matrix:
    bash_file_name = matrix_job["job_name"].replace(" ", "") + ".sh"
    print(f"Wrinting bash file to {os.path.join(artifact_path, bash_file_name)}")
    bash_out = open(os.path.join(artifact_path, bash_file_name), "w+")
    bash_out.write("#!/bin/bash\n\n")
    bash_out.write(
        "# Makes the bash script print out every command before it is executed, except echo\n"
    )
    bash_out.write(
        "trap '[[ $BASH_COMMAND != echo* ]] && echo $BASH_COMMAND' DEBUG\n\n"
    )
    bash_out.write(matrix_job["command"])
    bash_out.close()
    matrix_job["script"] = os.path.join(artifact_path, bash_file_name)

# Remove the command from the dictionaries before outputting them
for items in arduino_job_matrix + pio_job_matrix:
    if "command" in items:
        del items["command"]


# %%
# Write out output
print(
    'echo "arduino_job_matrix={}" >> $GITHUB_OUTPUT'.format(
        json.dumps(arduino_job_matrix)
    )
)
json_out = open(os.path.join(artifact_dir, "arduino_job_matrix.json"), "w+")
json.dump(arduino_job_matrix, json_out, indent=2)
json_out.close()


print('echo "pio_job_matrix={}" >> $GITHUB_OUTPUT'.format(json.dumps(pio_job_matrix)))
json_out = open(os.path.join(artifact_dir, "pio_job_matrix.json"), "w+")
json.dump(pio_job_matrix, json_out, indent=2)
json_out.close()


# %%
# different attempt to save output
if "GITHUB_WORKSPACE" in os.environ.keys():
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        print("arduino_job_matrix={}".format(json.dumps(arduino_job_matrix)), file=fh)
        print("pio_job_matrix={}".format(json.dumps(pio_job_matrix)), file=fh)


# %%
if "GITHUB_WORKSPACE" not in os.environ.keys():
    try:
        shutil.rmtree(artifact_dir)
    except:
        pass

# %%
