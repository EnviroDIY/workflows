#!/usr/bin/env python
# %%
from collections import OrderedDict
import copy
import os
import sys
from typing import Union
import subprocess
from os import makedirs
from os.path import isdir
import re
import json

from platformio.project.config import ProjectConfig
from platformio.package.meta import PackageSpec


# %%
# Some working directories
try:
    # Import the current working construction
    # environment to the `env` variable.
    # alias of `env = DefaultEnvironment()`
    Import("env")

    print("Working on environment (PIOENV) {}".format(env["PIOENV"]))
    print("Enviroment and project settings:")
    for project_directory in [
        "PROJECT_DIR",
        "PROJECT_CORE_DIR",
        "PROJECT_PACKAGES_DIR",
        "PROJECT_WORKSPACE_DIR",
        "PROJECT_INCLUDE_DIR",
        "PROJECT_SRC_DIR",
        "PROJECT_TEST_DIR",
        "PROJECT_DATA_DIR",
        "PROJECT_BUILD_DIR",
        "PROJECT_LIBDEPS_DIR",
        "LIBSOURCE_DIRS",
        "LIBPATH",
        "PIOENV",
        "BUILD_DIR",
        "BUILD_TYPE",
        "BUILD_CACHE_DIR",
        "LINKFLAGS",
    ]:
        print(f"{project_directory}: {env[project_directory]}")

    shared_lib_dir = env["LIBSOURCE_DIRS"][0]
    shared_lib_abbr = "lib"
    project_ini_file = f"{env['PROJECT_DIR']}\\platformio.ini"
    libdeps_ini_file = f"{env['PROJECT_DIR']}\\pio_common_libdeps.ini"
    library_json_file = f"{env['PROJECT_DIR']}\\library.json"
    examples_deps_file = f"{env['PROJECT_DIR']}\\examples\\example_dependencies.json"
    proj_config = env.GetProjectConfig()
    active_env_name = env["PIOENV"]
except:
    cwd = os.getcwd()
    shared_lib_dir = f"{cwd}\\lib"
    shared_lib_abbr = "lib"
    project_ini_file = f"{cwd}\\platformio.ini"
    libdeps_ini_file = f"{cwd}\\pio_common_libdeps.ini"
    library_json_file = f"{cwd}\\library.json"
    examples_deps_file = f"{cwd}\\examples\\example_dependencies.json"
    proj_config = ProjectConfig.get_instance(path=project_ini_file)
    default_env_name = proj_config.get_default_env()

envs = proj_config.envs()
common_env_name = "env"


# %%
# functions to find dependencies in the platformio.ini file
def get_shared_lib_deps(env="env"):
    # Get dependencies listed in the standard lib_deps section for the specified environment
    raw_lib_deps_std = proj_config.get(
        section=f"env:{env}", option="lib_deps", default=""
    )
    lib_deps_std = proj_config.parse_multi_values(raw_lib_deps_std)
    # Remove any libraries that are symlinks from the list!
    # The symlinks are created by this program, so if we don't ignore them, everything is duplicated
    lib_deps_std_nolinks = [
        lib_dep for lib_dep in lib_deps_std if "symlink" not in lib_dep
    ]
    print(f'Dependencies (lib_deps) for environment "{env}"')
    print(lib_deps_std_nolinks)

    # Get dependencies listed in the custom_shared_lib_deps section for the specified environment
    raw_lib_deps_custom = proj_config.get(
        section=f"env:{env}", option="custom_shared_lib_deps", default=""
    )
    lib_deps_custom = proj_config.parse_multi_values(raw_lib_deps_custom)
    print(f'Custom dependencies (custom_shared_lib_deps) for environment "{env}"')
    print(lib_deps_custom)

    # convert each custom lib_dep to a PlatformIO PackageSpec
    lib_deps_specs = []
    for lib_deps in lib_deps_custom + lib_deps_std_nolinks:
        spec = PackageSpec(lib_deps)
        lib_deps_specs.append(copy.deepcopy(spec))
    return lib_deps_specs


def get_ignored_lib_deps(env):
    return proj_config.parse_multi_values(
        proj_config.get(section=f"env:{env}", option="lib_ignore", default=[])
    )

# %%
# functions for parsing libraries
def get_package_spec(dependency: dict):
    spec = PackageSpec(
        id=dependency.get("id"),
        owner=dependency.get("owner"),
        name=dependency.get("name"),
        requirements=dependency.get("version"),
    )
    return spec


def convert_dep_dict_to_str(dependency: dict, include_version: bool = True) -> str:
    install_str = ""
    if "owner" in dependency.keys() and "github" in dependency["version"]:
        if "name" in dependency.keys():
            install_str += f"{dependency['name']}="
        install_str += dependency["version"]
    elif (
        "owner" in dependency.keys()
        and "name" in dependency.keys()
        and "version" in dependency.keys()
    ):
        lib_dep = f"{dependency['owner']}/{dependency['name']}"
        if include_version:
            lib_dep += f"@{dependency['version']}"
        install_str += lib_dep
    elif "name" in dependency.keys() and "version" in dependency.keys():
        lib_dep = f"{dependency['name']}"
        if include_version:
            lib_dep += f"@{dependency['version']}"
        install_str += lib_dep
    else:
        install_str += dependency["name"]

    return install_str


# %%
# find dependencies based on the library specification
if os.path.isfile(library_json_file):
    with open(library_json_file) as f:
        library_specs = json.load(f)
else:
    library_specs = {"dependencies": []}
# find dependencies based on the examples dependency specs
if os.path.isfile(examples_deps_file):
    with open(examples_deps_file) as f:
        example_specs = json.load(f)
else:
    example_specs = {"dependencies": []}

# %%
# find dependencies of the various environments
dependencies = get_shared_lib_deps(common_env_name)
# make sure the "dependencies" key exists, add if not
if "dependencies" not in library_specs.keys():
    library_specs["dependencies"] = []
if "dependencies" not in example_specs.keys():
    example_specs["dependencies"] = []

# %% Combine dependencies
dependencies.extend(
    [get_package_spec(dependency) for dependency in library_specs["dependencies"]]
)
dependencies.extend(
    [get_package_spec(dependency) for dependency in example_specs["dependencies"]]
)

humanized_deps = [dep.as_dependency() for dep in dependencies]
print("Humanized dependencies:")
print(humanized_deps)

# %%
# quit if there are no dependencies
if len(dependencies) == 0:
    print("No dependencies to install!")
    sys.exit()


# %%
# check what's already installed
def parse_global_installs(verbose: bool = False):
    # Build dependency list command
    list_cmd = ["pio", "pkg", "list", "-g", "--only-libraries", "-v"]

    # set the storage directory for the libraries
    list_cmd.extend(["--storage-dir", shared_lib_dir])

    # Run list command
    if int(verbose) >= 1:
        print("Global library list command")
        print(" ".join(list_cmd))
    try:
        list_result = subprocess.run(
            list_cmd, capture_output=True, text=True, check=True
        )
        # print(list_result.stdout)
        # print(list_result.stderr)
    except:
        return []

    lib_list_presort = []

    for line in list_result.stdout.split("\n"):
        if int(verbose) >= 1:
            print(line)
        # print(line.split())
        match = re.search(
            r".*? (?P<lib_name>[\w\s-]*?) @ (?P<lib_version>[\w\s\.\+-]*?) \(required: (?:git\+)?(?P<lib_req>.*?)(?: @ .*?)?, (?P<lib_dir>.*?)\)",
            line,
        )
        if match:
            if int(verbose) >= 1:
                print("Library name: {}".format(match.group("lib_name")))
                print("Library Version: {}".format(match.group("lib_version")))
                print("Library Storage Dir: {}".format(match.group("lib_dir")))
                print("Library Req: {}".format(match.group("lib_req")))
            req_entry_by_owner = list(
                filter(
                    lambda x: match.group("lib_req").lower() in x.lower(),
                    humanized_deps,
                )
            )
            if int(verbose) >= 1:
                print("Library Req Entry by Owner: {}".format(req_entry_by_owner))
            eq_entry_by_name = list(
                filter(
                    lambda x: match.group("lib_name").lower() in x.lower(),
                    humanized_deps,
                )
            )
            if int(verbose) >= 1:
                print("Library Req Entry by Name: {}".format(eq_entry_by_name))

            req_entry = list(
                OrderedDict.fromkeys(req_entry_by_owner + eq_entry_by_name)
            )
            if int(verbose) >= 1:
                print("Req Entry: {}".format(req_entry))
            is_in_reqs = len(req_entry) > 0
            if is_in_reqs:
                req_position = humanized_deps.index(req_entry[0])
            else:
                req_position = -1
            if match.group("lib_name") == "Adafruit BusIO":
                req_position = -2
            match_groups = match.groupdict()
            match_groups["req_entry"] = req_entry
            match_groups["is_in_reqs"] = is_in_reqs
            match_groups["req_position"] = req_position
            lib_list_presort.append(match_groups)
        else:
            if int(verbose) >= 1:
                print("XXXXXXXXXXXXXXXXXXXXXXX NO MATCH XXXXXXXXXXXXXXXXXXXXXXX")
        if int(verbose) >= 1:
            print("##########")

    lib_list = sorted(lib_list_presort, key=lambda d: d["req_position"])
    if int(verbose) >= 1:
        print("Listing libraries")
        print(json.dumps(lib_list))
    return lib_list


lib_list = parse_global_installs(False)
print("Listing libraries")
print(json.dumps(lib_list))

# decide what to install and what to update
libs_to_install = []
libs_to_update = []
for dep_spec in dependencies:
    if f"{dep_spec.owner}/{dep_spec.name}".lower() in [
        lib["lib_req"].lower() for lib in lib_list
    ] or (
        dep_spec.owner is None
        and f"{dep_spec.name}".lower() in [lib["lib_name"].lower() for lib in lib_list]
    ):
        libs_to_update.append(dep_spec)
    else:
        libs_to_install.append(dep_spec)

print("Libraries to install")
print([dep.as_dependency() for dep in libs_to_install])
print("\nLibraries to update")
print([dep.as_dependency() for dep in libs_to_update])


# %%
# Create shared_lib_dir if it does not exist
if not isdir(shared_lib_dir):
    makedirs(shared_lib_dir)


def create_pio_ci_command(
    library: Union[str | dict | PackageSpec],
    update: bool = True,
    include_version: bool = True,
) -> list:
    pio_command_args = [
        "pio",
        "pkg",
        "update" if update else "install",
        # "--skip-dependencies",
        "-g",
        "--storage-dir",
        shared_lib_dir,
        "--library",
    ]
    if isinstance(library, PackageSpec):
        pio_command_args.append(library.as_dependency())
        # pio_command_args.append(f'"{library.as_dependency()}"')
        return pio_command_args
    elif isinstance(library, dict):
        pio_command_args.append(convert_dep_dict_to_str(library))
        # pio_command_args.append(f'"{convert_dep_dict_to_str(library)}"')
        return pio_command_args
    elif isinstance(library, str):
        pio_command_args.append(library)
        # pio_command_args.append(f'"{library}"')
        return pio_command_args


# %%
print(f"\nInstalling new common libraries in {shared_lib_dir}")

def install_shared_dependencies(verbose):
    if int(verbose) >= 1:
        print("\nInstalling libraries")

    for lib in libs_to_install:
        lib_install_cmd = create_pio_ci_command(
            library=lib, update=False, include_version=True
        )

        if int(verbose) >= 1:
            print(f"Installing {lib}")
            print(" ".join(lib_install_cmd))
        # Run command
        install_result = subprocess.run(
            lib_install_cmd, capture_output=True, text=True, check=False
        )
        print(install_result.stdout)
        print(install_result.stderr)
        install_result.check_returncode()


install_shared_dependencies(True)


# %%
print(f"\nUpdating existing common libraries in {shared_lib_dir}")

def update_shared_dependencies(verbose):
    if int(verbose) >= 1:
        print("\nUpdating libraries")

    for lib in libs_to_update:
        lib_update_cmd = create_pio_ci_command(
            library=lib, update=True, include_version=False
        )

        if int(verbose) >= 1:
            print(f"Updating {lib}")
            print(" ".join(lib_update_cmd))
        # Run update command
        # update_result = subprocess.run(
        #     lib_update_cmd, capture_output=True, text=True, check=True
        # )
        update_result = subprocess.run(
            lib_update_cmd, capture_output=True, text=True, check=False
        )
        print(update_result.stdout)
        print(update_result.stderr)
        update_result.check_returncode()


update_shared_dependencies(True)


# %%
# check what's now installed
lib_list = parse_global_installs(False)
print(lib_list)


# %%
def create_symlink_list(environment: str, verbose: bool = False):
    all_symlinks = []
    req_symlinks = []
    ign_symlinks = []
    other_symlinks = []
    print("Creating symlink list")
    for lib in lib_list:
        symlink = (
            f"{lib['lib_name']}=symlink://{lib['lib_dir']}".replace(
                shared_lib_dir, shared_lib_abbr
            )
            .replace("\\\\", "/")
            .replace("\\", "/")
        )
        all_symlinks.append(symlink)
        is_req = lib["is_in_reqs"]
        is_ignored = lib["lib_name"] in get_ignored_lib_deps(environment)
        if is_req:
            req_symlinks.append(symlink)
        elif is_ignored:
            ign_symlinks.append(symlink)
        else:
            other_symlinks.append(symlink)
    if int(verbose) >= 1:
        print(other_symlinks)

    return {
        "all_symlinks": all_symlinks,
        "req_symlinks": req_symlinks,
        "ign_symlinks": ign_symlinks,
        "other_symlinks": other_symlinks,
    }


common_lib_symlinks = create_symlink_list("env", False)
print("<<<<<<<<<<<<Required Symlinks>>>>>>>>>>>>")
for item in common_lib_symlinks["req_symlinks"]:
    print("   ", item)
print("<<<<<<<<<<<<Ignored Symlinks>>>>>>>>>>>>")
for item in common_lib_symlinks["ign_symlinks"]:
    print("   ", item)
print("<<<<<<<<<<<<Other Symlinks>>>>>>>>>>>>")
for item in common_lib_symlinks["other_symlinks"]:
    print("   ", item)
# for env in envs:
#     env_symlinks = create_symlink_list(env, False)


# %%
with open(libdeps_ini_file, "w+") as out_file:
    out_file.write(
        "; File Automatically Generated by pioScripts/install_working_dependencies.py\n"
    )
    out_file.write("; DO NOT MODIFY\n\n")
    out_file.write("; Global data for all [env:***]\n")
    out_file.write("[env]\n")

    out_file.write("lib_deps =\n")
    for item in common_lib_symlinks["all_symlinks"]:
        out_file.write("    ")
        out_file.write(item)
        out_file.write("\n")

    out_file.write("lib_ignore =\n")
    ignored_folders = [
        ".git",
        ".github",
        ".pio",
        ".vscode",
        ".history",
        "boards",
        "continuous_integration",
        "continuous_integration_artifacts",
        "docs",
        "doc",
        "examples",
        "extras",
        "sensor_tests",
        "ex_one_offs",
    ]
    for folder in ignored_folders:
        out_file.write("   ")
        out_file.write(folder)
        out_file.write("\n")
    for lib in lib_list:
        is_req = lib["is_in_reqs"]
        if not is_req:
            out_file.write("    ")
            out_file.write(lib["lib_name"])
            out_file.write("\n")

# %%
