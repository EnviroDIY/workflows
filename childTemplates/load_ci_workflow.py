"""Run the local CI pipeline with inputs from the build-examples workflow."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


INPUT_ENVIRONMENT_VARIABLES = {
    "working_path": "WORKING_PATH",
    "ci_path": "CI_PATH",
    "artifact_path": "ARTIFACT_PATH",
    "examples_path": "EXAMPLES_PATH",
    "extras_path": "EXTRAS_PATH",
    "config_file_name": "CONFIG_FILE_NAME",
    "compiler_list": "COMPILER_LIST",
    "examples_to_build": "EXAMPLES_TO_BUILD",
    "examples_to_ignore": "EXAMPLES_TO_IGNORE",
    "boards_to_build": "BOARDS_TO_BUILD",
    "boards_to_ignore": "BOARDS_TO_IGNORE",
    "arduino_fqbns_to_build": "ARDUINO_FQBNS_TO_BUILD",
    "arduino_fqbns_to_ignore": "ARDUINO_FQBNS_TO_IGNORE",
    "pio_envs_to_build": "PIO_ENVS_TO_BUILD",
    "pio_envs_to_ignore": "PIO_ENVS_TO_IGNORE",
    "inline_defines": "INLINE_DEFINES",
    "compiler_flags": "COMPILER_FLAGS",
    "log_grouping_fields": "LOG_GROUPING_FIELDS",
    "job_grouping_fields": "JOB_GROUPING_FIELDS",
}

MUTUALLY_EXCLUSIVE_INPUTS = (
    ("examples_to_build", "examples_to_ignore"),
    ("boards_to_build", "boards_to_ignore"),
    ("arduino_fqbns_to_build", "arduino_fqbns_to_ignore"),
    ("pio_envs_to_build", "pio_envs_to_ignore"),
)


def get_workflow_inputs(workflow: Any) -> dict[str, str]:
    """Return the supported inputs from jobs.build_examples.with."""
    if not isinstance(workflow, dict):
        raise ValueError("The workflow must contain a YAML mapping.")

    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        raise ValueError("The workflow must contain a 'jobs' mapping.")

    build_examples = jobs.get("build_examples")
    if not isinstance(build_examples, dict):
        raise ValueError("The workflow must contain a 'jobs.build_examples' mapping.")

    workflow_inputs = build_examples.get("with") or {}
    if not isinstance(workflow_inputs, dict):
        raise ValueError("The 'jobs.build_examples.with' value must be a mapping.")

    unknown_inputs = sorted(set(workflow_inputs) - set(INPUT_ENVIRONMENT_VARIABLES))
    if unknown_inputs:
        unknown_list = ", ".join(unknown_inputs)
        raise ValueError(f"Unsupported build_examples input(s): {unknown_list}")

    inputs: dict[str, str] = {}
    for name, value in workflow_inputs.items():
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise ValueError(
                f"The '{name}' input must be a quoted string, "
                f"not {type(value).__name__}."
            )
        inputs[name] = value

    return inputs


def get_environment_updates(workflow_inputs: dict[str, str]) -> dict[str, str]:
    """Map workflow inputs to the environment used by the CI pipeline."""
    selected_inputs = dict(workflow_inputs)

    # Match the reusable workflow: an ignore value takes priority over its build value.
    for build_name, ignore_name in MUTUALLY_EXCLUSIVE_INPUTS:
        if ignore_name in selected_inputs:
            selected_inputs.pop(build_name, None)

    return {
        INPUT_ENVIRONMENT_VARIABLES[name]: value
        for name, value in selected_inputs.items()
    }


def run_pipeline(
    pipeline_path: Path,
    pipeline_args: list[str],
    environment_updates: dict[str, str],
) -> int:
    """Run the batch pipeline with the workflow inputs in its environment."""
    if not pipeline_path.is_file():
        raise FileNotFoundError(f"CI pipeline not found: {pipeline_path}")

    environment = os.environ.copy()
    environment.update(environment_updates)

    for build_name, ignore_name in MUTUALLY_EXCLUSIVE_INPUTS:
        build_variable = INPUT_ENVIRONMENT_VARIABLES[build_name]
        ignore_variable = INPUT_ENVIRONMENT_VARIABLES[ignore_name]
        if ignore_variable in environment_updates:
            environment.pop(build_variable, None)
        elif build_variable in environment_updates:
            environment.pop(ignore_variable, None)

    completed_process = subprocess.run(
        [str(pipeline_path), *pipeline_args],
        env=environment,
        check=False,
    )
    return completed_process.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load local CI inputs from a build_examples workflow."
    )
    parser.add_argument("workflow", type=Path, help="path to build_examples.yaml")
    parser.add_argument("pipeline", type=Path, help="path to run_CI_pipeline.bat")
    parser.add_argument(
        "pipeline_args",
        nargs=argparse.REMAINDER,
        help="additional arguments to pass to the CI pipeline",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        workflow = yaml.safe_load(args.workflow.read_text(encoding="utf-8"))
        workflow_inputs = get_workflow_inputs(workflow)
        environment_updates = get_environment_updates(workflow_inputs)
        return run_pipeline(args.pipeline, args.pipeline_args, environment_updates)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
