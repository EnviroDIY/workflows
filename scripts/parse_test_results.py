#!/usr/bin/env python
# %%
from glob import glob
import os
import re
import json

import pandas as pd

# %%
# The workspace directory
workspace_dir = os.getcwd()
if "\\continuous_integration" in workspace_dir:
    workspace_dir = workspace_dir.replace("\\continuous_integration", "")

workspace_path = os.path.abspath(os.path.realpath(workspace_dir))
print(f"Workspace Path: {workspace_path}")


# %%
# The continuous integration directory
ci_dir = "./continuous_integration/"
ci_path = os.path.join(workspace_dir, ci_dir)
ci_path = os.path.abspath(os.path.realpath(ci_path))
print(f"Continuous Integration Path: {ci_path}")
if not os.path.exists(ci_path):
    print(f"Creating the directory for CI: {ci_path}")
    os.makedirs(ci_path, exist_ok=True)


# %%
# A directory of files to save and upload as artifacts to use in future jobs
artifact_dir = os.path.join(
    os.path.join(workspace_dir, "continuous_integration_artifacts")
)
artifact_path = os.path.abspath(os.path.realpath(artifact_dir))


# %%
def parse_arduino_output(result_json: dict) -> dict[str, int | None] | None:
    if "builder_result" not in result_json.keys():
        return {
            "success": result_json.get("success", False),
        }
    if "executable_sections_size" in result_json["builder_result"].keys():
        ram = next(
            (
                x
                for x in result_json["builder_result"]["executable_sections_size"]
                if x["name"] == "data"
            ),
            None,
        )
        flash = next(
            (
                x
                for x in result_json["builder_result"]["executable_sections_size"]
                if x["name"] == "text"
            ),
            None,
        )
        ram_used = ram["size"] if ram else None
        flash_used = flash["size"] if flash else None
        ram_total = ram["max_size"] if ram else None
        flash_total = flash["max_size"] if flash else None
    elif "exceeds available space" in result_json.get(
        "error", ""
    ) or "Sketch too big" in result_json.get("compiler_err", ""):
        # the compiler out will be something like:
        # Sketch uses 28874 bytes (100%) of program storage space. Maximum is 28672 bytes.
        # Global variables use 757 bytes (29%) of dynamic memory, leaving 1803 bytes for local variables. Maximum is 2560 bytes.
        re_ram = re.compile(
            r"Global variables use\s+(?P<used_bytes>\d+)\s+bytes \(\d+%\) of dynamic memory, leaving \d+\s+bytes for local variables. Maximum is (?P<total_bytes>\d+)\s+bytes\."
        )
        re_flash = re.compile(
            r"Sketch uses\s+(?P<used_bytes>\d+)\s+bytes \(\d+%\) of program storage space. Maximum is (?P<total_bytes>\d+)\s+bytes\."
        )
        result_str = result_json.get("compiler_out", "")
        match_ram = re_ram.search(result_str)
        match_flash = re_flash.search(result_str)
        ram_used = int(match_ram.group("used_bytes")) if match_ram else None
        ram_total = int(match_ram.group("total_bytes")) if match_ram else None
        flash_used = int(match_flash.group("used_bytes")) if match_flash else None
        flash_total = int(match_flash.group("total_bytes")) if match_flash else None
    else:
        ram_used = None
        ram_total = None
        flash_used = None
        flash_total = None
    return {
        "ram_used": ram_used,
        "ram_total": ram_total,
        "flash_used": flash_used,
        "flash_total": flash_total,
        "success": result_json.get("success", False),
    }


def parse_pio_output(result_str: str) -> dict[str, int | None] | None:
    # the compile size lines are like:
    # RAM:   [====      ]  35.4% (used 28996 bytes from 81920 bytes)
    # Flash: [===       ]  26.9% (used 280463 bytes from 1044464 bytes)
    re_ram = re.compile(
        r"RAM:\s+\[[=\s]*\]\s+\d+\.\d+%\s+\(used\s+(?P<used_bytes>\d+)\s+bytes from (?P<total_bytes>\d+)\s+bytes\)"
    )
    re_flash = re.compile(
        r"Flash:\s+\[[=\s]*\]\s+\d+\.\d+%\s+\(used\s+(?P<used_bytes>\d+)\s+bytes from (?P<total_bytes>\d+)\s+bytes\)"
    )
    match_ram = re_ram.search(result_str)
    match_flash = re_flash.search(result_str)
    # the final results are like:
    # Environment    Status    Duration
    # -------------  --------  ------------
    # mayfly         SUCCESS   00:00:07.963
    re_success = re.compile(
        r"^(?P<env_name>\S+)\s+(?P<status>(?:SUCCESS)|(?:FAILED))\s+(?P<duration>\d+:\d+:\d+\.\d+)$",
        re.MULTILINE,
    )
    match_success = re_success.search(result_str)
    return {
        "ram_used": int(match_ram.group("used_bytes")) if match_ram else None,
        "ram_total": int(match_ram.group("total_bytes")) if match_ram else None,
        "flash_used": int(match_flash.group("used_bytes")) if match_flash else None,
        "flash_total": int(match_flash.group("total_bytes")) if match_flash else None,
        "success": (
            match_success.group("status") == "SUCCESS" if match_success else None
        ),
    }


def get_job_info_from_filename(filename: str) -> dict:
    name_parts = os.path.basename(filename).split("_")
    if len(name_parts) == 3:
        return {
            "compiler": name_parts[0],
            "board": name_parts[1],
            "example": name_parts[2].rsplit(".", 1)[0],
        }
    else:
        return {
            "compiler": name_parts[0],
            "flag": name_parts[1],
            "board": name_parts[2],
            "example": name_parts[3].rsplit(".", 1)[0],
        }


# %%
# parse all of the job logs and create a summary CSV file
pio_logs = glob(os.path.join(artifact_path, "pio_*.log"))
acli_logs = glob(os.path.join(artifact_path, "arduino_*.json"))


log_results = []
for log_file in pio_logs + acli_logs:
    job_info = get_job_info_from_filename(log_file)
    with open(log_file, "r") as f:
        if job_info["compiler"] == "pio":
            log_contents = f.read()
            parsed_result = parse_pio_output(log_contents)
        else:
            try:
                log_contents = json.load(f)
                parsed_result = parse_arduino_output(log_contents)
            except json.JSONDecodeError:
                parsed_result = {"success": False}
    if parsed_result is not None:
        job_info.update(parsed_result)
    log_results.append(job_info)


df = pd.DataFrame(log_results)
df["flash_percent"] = df.apply(
    lambda row: (
        (row["flash_used"] / row["flash_total"] * 100) if row["flash_total"] else None
    ),
    axis=1,
)
df["flash_percent"] = df["flash_percent"].round(1)
df["ram_percent"] = df.apply(
    lambda row: (
        (row["ram_used"] / row["ram_total"] * 100) if row["ram_total"] else None
    ),
    axis=1,
)
df["ram_percent"] = df["ram_percent"].round(1)
df["success"] = df["success"].fillna(2).astype(int)
# sort with failures at the top, then by board, example, flag, and compiler
df = df.sort_values(
    by=["success", "board", "example", "flag", "compiler"],
    ascending=[True, True, True, True, True],
)
df["success"] = df["success"].replace(
    {2: ":black_circle:", 1: ":heavy_check_mark:", 0: ":x:"}
)


# %%
md_table = df[
    [
        "compiler",
        "example",
        "board",
        "flag",
        "success",
        "ram_used",
        "ram_percent",
        "flash_used",
        "flash_percent",
    ]
].to_markdown(index=False, tablefmt="github")

print("\n\n### Summary of Build Results\n")
print(md_table)


# %%
if "GITHUB_WORKSPACE" in os.environ.keys():
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
        fh.write("\n\n### Summary of Build Results\n")
        fh.write(md_table)


# %%
# cSpell:words devkitm acli genuino bluepill fqbn fqbns pipestatus jsons endgroup DTINY_GSM_RX_BUFFER Wextra
