#!/usr/bin/env python
"""
Parse workflow inputs from environment variables to provide them to all subsequent steps in the CI pipeline.
This script is not intended to be run as a standalone script.
"""

# %%
import os
import json
from typing import Dict
import configargparse

# %%
# settings

# Arguments that are path related
path_args = [
    "workspace-path",
    "ci-path",
    "artifact-path",
    "examples-path",
    "extras-path",
]
# Paths that must exist
existing_path_args = ["workspace_path", "examples_path"]
# Paths that can be created if they do not exist
create_path_args = ["artifact_path"]
# NOTE: The extras-path is not required to exist, but if it does,
# it will be used to find examples.
# If it does not exist, it will be ignored.
# NOTE: The ci-path is not required to exist, but if it does,
# it will be used to store CI-related files.
# If it does not exist, it will be ignored.


# arguments that are lists of strings, separated by commas, and can be empty
# NOTE: We cannot use the "type=list" argument in configargparse because we are also
# using environment variables and those are always strings.
# So we will parse the lists ourselves later.
# list_args = [
#     v.dest
#     for v in parser._actions
#     if isinstance(v, configargparse.Action)
#     and v.type == str
#     and v.help is not None
#     and "list" in v.help
# ]
list_args = [
    "compiler_list",
    "examples_to_build",
    "examples_to_ignore",
    "boards_to_build",
    "boards_to_ignore",
    "arduino_fqbns_to_build",
    "arduino_fqbns_to_ignore",
    "pio_envs_to_build",
    "pio_envs_to_ignore",
    "log_grouping_fields",
    "job_grouping_fields",
]  # for values with a default of "all" or "", these are considered unset
unset_positive = ["all", "", ["all"], [""], []]
# for values with a default of None or "", these are considered unset
unset_negative = ["", None, [""], [None], []]

# %%
# verbose printing
use_verbose = (
    False  # set to True to print debug messages (updated by read_env_config())
)


def set_verbose_mode(verbose: bool) -> None:
    """Set the verbose mode for print_verbose output

    This should be called by any script that imports print_verbose after parsing
    its own command line arguments to ensure print_verbose respects the --verbose flag.

    Args:
        verbose: True to enable debug output, False to disable
    """
    global use_verbose
    use_verbose = verbose


def print_verbose(msg: str) -> None:
    """Print debug message if verbose mode is enabled

    Uses the global use_verbose flag which can be set via:
    - read_env_config() in this script
    - set_verbose_mode() in any importing script
    """
    if use_verbose:
        print(f"::debug::{msg}")


# %%
# Arg parsing and config file reading


class JsonConfigFileParser(configargparse.ConfigFileParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def dict_to_namespace(self, d):
        """Convert a dictionary to a Namespace, removing '-' from keys"""
        return configargparse.Namespace(**self.clean_dict(d))

    def convert(self, obj):
        if isinstance(obj, bool):
            return str(obj).lower()
        if isinstance(obj, (list, tuple)):
            return [self.convert(item) for item in obj]
        if isinstance(obj, dict):
            return {
                self.convert(key): self.convert(value) for key, value in obj.items()
            }
        return obj

    def clean_dict(self, d, convert=False):
        """Clean dictionary keys by replacing '-' with '_'"""
        new_d = {}
        for k, v in d.items():
            new_k = k.replace("-", "_")
            if convert:
                new_d[new_k] = self.convert(v)
            else:
                new_d[new_k] = v
        return new_d

    def parse_file(self, filename, namespace=None):
        d = {}
        with open(filename, "r") as f:
            d = self.clean_dict(json.load(f), True)
        if namespace is None:
            return self.dict_to_namespace(d)
        else:
            for k, v in d.items():
                if not hasattr(namespace, k):
                    setattr(namespace, k, v)
                elif getattr(namespace, k) != v and k not in ["verbose", "cleanup"]:
                    if k not in ["examples_to_build"]:
                        # ^^ we expect these to be changed by the parsing
                        print(
                            f"::warning::Config file value for '{k}' ({v}) overrides existing value ({getattr(namespace, k)})"
                        )
                    setattr(namespace, k, v)
            return namespace

    def parse(self, stream):
        return self.clean_dict(json.load(stream), True)

    def serialize(self, items):
        items = dict(items)
        return json.dumps(self.clean_dict(items), indent=2)

    def write_file(self, items, filename):
        items = dict(items)
        with open(filename, "w") as f:
            json.dump(self.clean_dict(items), f, indent=2)


def get_env_parser():
    parser = configargparse.ArgParser(
        add_env_var_help=True,
        auto_env_var_prefix="",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true",
        env_var="RUNNER_DEBUG",
    )
    parser.add_argument("--cleanup", help="perform cleanup", action="store_true")

    parser.add_argument(
        "--workspace-path",
        help="workspace path as an absolute path",
        type=str,
        env_var="GITHUB_WORKSPACE",
        default=os.getcwd(),
    )
    # This is an alias for workspace-path, to support local environment variable overrides
    parser.add_argument(
        "--working-path",
        help="working path as an absolute path",
        type=str,
        dest="workspace_path",
        default=os.getcwd(),
    )
    parser.add_argument(
        "--ci-path",
        help="continuous integration path, relative to the workspace path",
        type=str,
        default="continuous_integration",
    )
    parser.add_argument(
        "--artifact-path",
        help="path to store artifacts, relative to the workspace path",
        type=str,
        default="continuous_integration_artifacts",
    )
    parser.add_argument(
        "--examples-path",
        help="path to examples, relative to the workspace path",
        type=str,
        default="examples",
    )
    parser.add_argument(
        "--extras-path",
        help="path to extras, relative to the workspace path",
        type=str,
        default="extras",
    )
    parser.add_argument(
        "--config-file-name",
        help="filename for the configuration file (not the full path)",
        type=str,
        default="matrix_config.json",
    )

    parser.add_argument(
        "--compiler-list",
        help="comma-separated list of compilers to use",
        type=str,
        default="arduino-cli,platformio",
        choices=[
            "arduino-cli",
            "platformio",
            "arduino-cli,platformio",
            "platformio,arduino-cli",
        ],
    )

    ex_group = parser.add_mutually_exclusive_group()
    ex_group.add_argument(
        "--examples-to-build",
        help='comma-separated list of examples to build (or "all" for all)'
        "\nThis should be a list of example folder names relative to the workspace path, "
        "not the .ino file names.",
        type=str,
        default="all",
    )
    ex_group.add_argument(
        "--examples-to-ignore",
        help="comma-separated list of examples to ignore",
        type=str,
    )

    common_boards_group = parser.add_argument_group(
        "Board selections for all compilers"
    )
    common_boards_group.add_argument(
        "--boards-to-build",
        help='comma-separated list of board names to build with all compilers (or "all" for all)',
        type=str,
        default="all",
    )
    common_boards_group.add_argument(
        "--boards-to-ignore",
        help="comma-separated list of board names to skip when building with any compilers",
        type=str,
    )

    cli_group = parser.add_argument_group(
        "Arduino CLI specific board selections"
        "\nThese will be added to the common boards-to-build list and the common boards-to-ignore list."
    )
    cli_group.add_argument(
        "--arduino-fqbns-to-build",
        help='comma-separated list of FQBNs or board names to build with the Arduino CLI (or "all" for all)',
        type=str,
        default="all",
    )
    cli_group.add_argument(
        "--arduino-fqbns-to-ignore",
        help="comma-separated list of FQBNs or board names to skip when building with the Arduino CLI",
        type=str,
    )

    pio_group = parser.add_argument_group(
        "PlatformIO specific environment selections"
        "\nThese will be added to the common boards-to-build list and the common boards-to-ignore list."
    )
    pio_group.add_argument(
        "--pio-envs-to-build",
        help='comma-separated list of environment names or board names to build with PlatformIO (or "all" for all)',
        type=str,
        default="all",
    )
    pio_group.add_argument(
        "--pio-envs-to-ignore",
        help="comma-separated list of environment names or board names to skip when building with PlatformIO",
        type=str,
    )

    parser.add_argument(
        "--inline-defines",
        help="\nsemicolon separated list of comma-separated lists of defined values that will be written to the top of the example code as #define statements"
        "\nTo set a value, use the format: NAME=VALUE. For example: `DEBUG,VERSION=1.0;VERSION=2.0`."
        "\nThese will NOT be passed to the compiler!",
        type=str,
        default="",
        dest="raw_inline_defines",
    )
    parser.add_argument(
        "--compiler-flags",
        help="semicolon separated list of comma-separated lists of compiler flags that will be passed to the compiler."
        "\nFor example: `-Wall,-Wextra,-D DEBUG,-D VERSION=1.0;-Wall,-Wextra,-D VERSION=2.0`",
        type=str,
        default="",
        dest="raw_compiler_flags",
    )
    parser.add_argument(
        "--log-grouping-fields",
        help="comma-separated list of fields to group logs by",
        type=str,
        default="",
    )
    parser.add_argument(
        "--job-grouping-fields",
        help="comma-separated list of fields to group jobs by",
        type=str,
        default="compiler,board",
    )
    return parser


def read_env_config():
    """
    Read the configuration from environment variables and return a namespace of the values.
    """
    parser = get_env_parser()
    args, _unknown = parser.parse_known_args()

    # immediately set the global verbose flag to the value of the args.verbose argument
    global use_verbose
    use_verbose = args.verbose
    print(f"Verbose mode is now {'enabled' if use_verbose else 'disabled'}")

    print_verbose(
        "Configuration read from environment variables and command line arguments:"
    )
    for line in parser.format_values().splitlines():
        print_verbose(line)

    return args


# %%
def validate_input_args(args):
    """
    Validate the input arguments

    WARNING: This function should only be called once after the initial parsing of the
    arguments by configargparse. If it is called after the examples or boards have
    been parsed, it will throw an error because the parsed lists will not be equal
    to the unset values.
    """

    # immediately set the global verbose flag to the value of the args.verbose argument
    global use_verbose
    use_verbose = args.verbose

    # the workspace path must exist
    clean_workspace_path_name(args)
    if not os.path.isdir(args.workspace_path):
        print(f"::error::Workspace path does not exist: {args.workspace_path}")
        exit(1)


def clean_workspace_path_name(args) -> str:
    """
    Removes 'continuous_integration' from the workspace path if it is present, and returns the cleaned path.
    This is useful for ensuring that the workspace path is consistent and does not include the CI directory.

    Returns:
        str: Absolute path to the workspace directory
    """

    workspace_dir = args.workspace_path

    if os.path.basename(os.path.normpath(workspace_dir)) == "continuous_integration":
        print_verbose(
            f"continuous_integration removed from workspace path: {workspace_dir}"
        )
        workspace_dir = os.path.dirname(workspace_dir)

    workspace_path = os.path.abspath(os.path.realpath(workspace_dir))
    args.workspace_path = workspace_path  # Update the args object with the cleaned path
    print(f"Workspace path set to: {workspace_path}")
    return workspace_path


def is_child_path(child, parent):
    child = os.path.realpath(child)
    parent = os.path.realpath(parent)
    return not os.path.relpath(child, parent).startswith("..")


def get_full_directory_paths(args) -> Dict[str, str]:
    """
    Get the full absolute paths for the working directories and create folders if they do not exist.
    Call clean_workspace_path_name() before this function to ensure the workspace path is correct.

    Returns:
        dict: Dictionary with keys:
            - workspace_path: Root workspace directory
            - ci_path: Continuous integration directory
            - artifact_path: Artifacts output directory
            - examples_path: Examples directory
            - extras_path: Extras directory
    """

    workspace_path = args.workspace_path
    dirs = {"workspace_path": workspace_path}
    for arg_name in [
        "ci_path",
        "artifact_path",
        "examples_path",
        "extras_path",
    ]:
        working_dir = getattr(args, arg_name.replace("-", "_"), "")
        # verify that it's not already an absolute path, if not, join it with the workspace path
        if os.path.isabs(working_dir):
            full_path = os.path.abspath(os.path.realpath(working_dir))
        else:
            full_path = os.path.join(workspace_path, working_dir)
            full_path = os.path.abspath(os.path.realpath(full_path))
        if not is_child_path(full_path, workspace_path):
            print(
                f"::error::{arg_name} must be a subdirectory of the workspace path: {workspace_path}"
            )
            exit(1)
        if full_path != working_dir:
            print(f"Full path for {arg_name} ({working_dir}) is: {full_path}\n")

        # Check if the path exists,
        # throw an error if it's required or create it's optional but we need it later
        if not os.path.exists(full_path) and arg_name in existing_path_args:
            print(f"::error::{full_path} does not exist. Please create it.")
            exit(1)
        if not os.path.exists(full_path) and arg_name in create_path_args:
            print(f"Creating the directory: {full_path}")
            os.makedirs(full_path, exist_ok=True)

        dirs[arg_name] = full_path
        setattr(
            args, arg_name.replace("-", "_"), full_path
        )  # Update the args object with the full path

    # Add the config file info to the dirs dictionary and args object
    if os.path.isabs(args.config_file_name):
        config_file_path = args.config_file_name
        config_file_name = os.path.basename(config_file_path)
    else:
        config_file_path = os.path.join(
            args.workspace_path, args.artifact_path, args.config_file_name
        )
        config_file_name = args.config_file_name
    args.config_file_name = config_file_name
    args.config_file_path = config_file_path
    dirs["config_file_path"] = config_file_path

    return dirs


def parse_list_from_args(arg_name: str, args) -> list | None:
    """Parse a comma-separated list from an argument value"""
    if arg_name not in list_args and arg_name.replace("_", "-") not in list_args:
        print(f"::warning::{arg_name} is not a recognized list argument.")
        return
    arg_value = getattr(args, arg_name.replace("-", "_"), None)

    # if the value is empty, return an empty list
    if arg_value is None:
        parsed_list = []
    # if it's already a list, return it as is
    elif isinstance(arg_value, list):
        parsed_list = arg_value
    # if it's not a string, print a warning and return an empty list
    elif not isinstance(arg_value, str):
        print(f"::warning:: {arg_name} is not a string. Using empty list.")
        parsed_list = []
    # if the value is an empty string, return an empty list (not a list with an empty string)
    elif arg_value == "":
        parsed_list = []
    # finally, if we have a non-empty string, split it by commas and strip whitespace
    else:
        parsed_list = [item.strip() for item in arg_value.split(",")]
        print_verbose(
            f"Using {arg_name}: {len(parsed_list)} items ({', '.join(parsed_list)})"
        )

    # update the args object with the parsed list
    setattr(args, arg_name.replace("-", "_"), parsed_list)
    return parsed_list


def get_env_config():
    """Get the configuration from the command line arguments and environment variables OR from the supplied config file"""

    # read the command line and environment variables
    print_verbose(
        "Reading configuration from environment variables and command line arguments..."
    )
    args = read_env_config()

    # validate the parsed arguments
    print_verbose("Validating input arguments...")
    validate_input_args(args)

    # get the full directory paths and create folders if they do not exist
    print_verbose(
        "Getting full directory paths and creating folders if they do not exist..."
    )
    get_full_directory_paths(args)

    # parse all of the list inputs from the args object
    print_verbose("Parsing list arguments from the args object...")
    for list_arg in list_args:
        parse_list_from_args(list_arg, args)

    return args


def write_config_file(args) -> str:
    """Save the current configuration to a JSON file"""
    if args.config_file_path is None:
        raise ValueError("Config file name is not set. Cannot write config file.")
    # Read the config file path from the args object,
    # which should have been set by get_full_directory_paths()
    config_file = args.config_file_path
    # create a new ConfigFileParser to write the config file with the correct class
    # NOTE: We use the JsonConfigFileParser class to ensure that the keys are cleaned
    # (i.e., '-' replaced with '_') when writing the config file.
    file_parser = JsonConfigFileParser()
    print_verbose(f"Writing configuration to: {config_file}")
    file_parser.write_file(args.__dict__, config_file)
    return config_file


def get_extended_config():
    """
    Get the configuration from the command line arguments and environment variables,
    and extend it with additional derived values saved in the config files.
    """

    print_verbose("Getting environment and command line config...")
    env_args = get_env_config()
    print_verbose("Finished getting environment and command line config.")

    # verify the config file path is set, otherwise we cannot get the extended config
    if env_args.config_file_path is None:
        print("Config file name is not set; returning environment args.")
        return env_args
    # verify that the config file exists, otherwise there's nothing to read
    if not os.path.exists(env_args.config_file_path):
        print_verbose(
            f"Config file does not exist: {env_args.config_file_path}; returning environment args"
        )
        return env_args

    # create a new ConfigFileParser to write the config file with the correct class
    # NOTE: We use the JsonConfigFileParser class to ensure that the keys are cleaned
    # (i.e., '-' replaced with '_') when reading the config file.
    # NOTE: We *don't* use the configargparse parser with the JsonConfigFileParser
    # class because it can't handle anything but strings and lists as inputs.
    file_parser = JsonConfigFileParser()
    print_verbose(f"Reading extended config from: {env_args.config_file_path}")
    ext_args = file_parser.parse_file(env_args.config_file_path, namespace=env_args)

    return ext_args


# %%
if __name__ == "__main__":
    print("=" * 60)
    print("CI Build Pipeline: Shared Configuration Reader")
    print("=" * 60)

    args = get_env_config()

    # Dump the parsed inputs to a JSON file in the artifact path for use in later steps of the CI pipeline
    config_file = write_config_file(args)

    print(f"\n✓ Parsed inputs saved to: {config_file}")
    print("✓ Workflow inputs parsed successfully")

# %%
# cSpell:ignore
