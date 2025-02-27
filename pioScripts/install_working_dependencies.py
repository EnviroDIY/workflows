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
import semantic_version
import datetime
import logging
from pathlib import Path

from platformio.project.config import ProjectConfig
from platformio.package.meta import PackageCompatibility, PackageSpec
from platformio.package.manager.library import LibraryPackageManager
from platformio.platform.factory import PlatformFactory
from platformio.package.exception import UnknownPackageError
from platformio.platform.exception import UnknownPlatform

try:
    from SCons.Script import BUILD_TARGETS  # pylint: disable=import-error
    from SCons.Script import COMMAND_LINE_TARGETS  # pylint: disable=import-error
    from SCons.Script import DEFAULT_TARGETS  # pylint: disable=import-error

except:
    pass

# %%
print("Running install_working_dependencies.py")

options = {"update": True, "silent": False, "skip_dependencies": False, "force": False}

# Some working directories
try:
    # Import the current working construction
    # environment to the `env` variable.
    # alias of `env = DefaultEnvironment()`
    Import("env")

    # print(f"Current build targets: {[str(tgt) for tgt in BUILD_TARGETS]}")
    # print(f"Current command line targets: {COMMAND_LINE_TARGETS}")

    if not (set(["_idedata", "idedata"]) & set(COMMAND_LINE_TARGETS)):
        print(
            "This is an IDE data build, will also install dependencies for the default environment."
        )
    else:
        os._exit(os.EX_OK)

    print("Working on environment (PIOENV) {}".format(env["PIOENV"]))
    # print("Enviroment and project settings:")
    # for project_directory in [
    #     "PROJECT_DIR",
    #     "PROJECT_CORE_DIR",
    #     "PROJECT_PACKAGES_DIR",
    #     "PROJECT_WORKSPACE_DIR",
    #     "PROJECT_INCLUDE_DIR",
    #     "PROJECT_SRC_DIR",
    #     "PROJECT_TEST_DIR",
    #     "PROJECT_DATA_DIR",
    #     "PROJECT_BUILD_DIR",
    #     "PROJECT_LIBDEPS_DIR",
    #     "LIBSOURCE_DIRS",
    #     "LIBPATH",
    #     "PIOENV",
    #     "BUILD_DIR",
    #     "BUILD_TYPE",
    #     "BUILD_CACHE_DIR",
    #     "LINKFLAGS",
    # ]:
    #     print(f"{project_directory}: {env[project_directory]}")

    project_dir = env["PROJECT_DIR"]
    shared_lib_dir = env["LIBSOURCE_DIRS"][0]
    shared_lib_abbr = "lib"
    project_ini_file = f"{env['PROJECT_DIR']}\\platformio.ini"
    libdeps_ini_file = f"{env['PROJECT_DIR']}\\pio_common_libdeps.ini"
    library_json_file = f"{env['PROJECT_DIR']}\\library.json"
    examples_deps_file = f"{env['PROJECT_DIR']}\\examples\\example_dependencies.json"
    project_config = env.GetProjectConfig()
    active_env_name = env["PIOENV"]
    default_env_name = project_config.get_default_env()

    print(f"Active environment: {active_env_name}")
    print(f"Default environment: {active_env_name}")
    if active_env_name == default_env_name:
        print("This is a build of the default environment, will install dependencies.")
    else:
        os._exit(os.EX_OK)

except:
    cwd = os.getcwd()
    if (
        cwd.lower()
        == "c:\\users\\sdamiano\\documents\\github\\envirodiy\\workflows\\pioscripts"
    ):
        cwd = "C:\\Users\\sdamiano\\Documents\\GitHub\\EnviroDIY\\ModularSensors"
        # cwd = "C:\\Users\\sdamiano\\Documents\\PlatformIO\\Projects\\NGWOS_TTN"
        # cwd = "C:\\Users\\sdamiano\\Documents\\GitHub\\EnviroDIY\\GeoluxCamera"
    project_dir = cwd
    shared_lib_dir = f"{cwd}\\lib"
    shared_lib_abbr = "lib"
    project_ini_file = f"{cwd}\\platformio.ini"
    libdeps_ini_file = f"{cwd}\\pio_common_libdeps.ini"
    library_json_file = f"{cwd}\\library.json"
    examples_deps_file = f"{cwd}\\examples\\example_dependencies.json"
    project_config = ProjectConfig.get_instance(path=project_ini_file)
    active_env_name = project_config.envs()[0]
    default_env_name = project_config.get_default_env()

envs = project_config.envs()
common_env_name = "env"


# %%
# functions to find dependencies in the platformio.ini file
def get_shared_lib_deps(env="env"):
    # Get dependencies listed in the standard lib_deps section for the specified environment
    raw_lib_deps_std = project_config.get(
        section=f"env:{env}", option="lib_deps", default=""
    )
    lib_deps_std = project_config.parse_multi_values(raw_lib_deps_std)
    # Remove any libraries that are symlinks from the list!
    # The symlinks are created by this program, so if we don't ignore them, everything is duplicated
    lib_deps_std_nolinks = [
        lib_dep for lib_dep in lib_deps_std if "symlink" not in lib_dep
    ]
    # print(f'Dependencies (lib_deps) for environment "{env}"')
    # print(lib_deps_std_nolinks)

    # Get dependencies listed in the custom_shared_lib_deps section for the specified environment
    raw_lib_deps_custom = project_config.get(
        section=f"env:{env}", option="custom_shared_lib_deps", default=""
    )
    lib_deps_custom = project_config.parse_multi_values(raw_lib_deps_custom)
    # print(f'Custom dependencies (custom_shared_lib_deps) for environment "{env}"')
    # print(lib_deps_custom)

    # convert each custom lib_dep to a PlatformIO PackageSpec
    lib_deps_specs = []
    for lib_deps in lib_deps_custom + lib_deps_std_nolinks:
        spec = PackageSpec(lib_deps)
        lib_deps_specs.append(copy.deepcopy(spec))
    return lib_deps_specs


def get_ignored_lib_deps(env):
    return project_config.parse_multi_values(
        project_config.get(section=f"env:{env}", option="lib_ignore", default=[])
    )


def get_extra_lib_dirs(env):
    return project_config.parse_multi_values(
        project_config.get(section=f"env:{env}", option="lib_extra_dirs", default=[])
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
# print("Humanized dependencies:")
# print(humanized_deps)

# %%
# quit if there are no dependencies
if len(dependencies) == 0:
    print("No dependencies to install!")
    os._exit(os.EX_OK)


# %%

# create a lib manager set at the directory we want to use to install shared dependencies
compatibility_qualifiers = {}
if project_config.get(f"env:{common_env_name}", "platform", None):
    try:
        p = PlatformFactory.new(
            project_config.get(f"env:{common_env_name}", "platform")
        )
        compatibility_qualifiers["platforms"] = [p.name]
    except UnknownPlatform:
        pass
    if project_config.get(f"env:{common_env_name}", "framework"):
        compatibility_qualifiers["frameworks"] = project_config.get(
            f"env:{common_env_name}", "framework"
        )
private_lm = LibraryPackageManager(
    shared_lib_dir,
    compatibility=(
        PackageCompatibility(**compatibility_qualifiers)
        if compatibility_qualifiers
        else None
    ),
)
private_lm.set_log_level(logging.DEBUG)


# %%
# check for changes to dependencies
def get_changed_dependencies():
    lib_deps = humanized_deps
    if not lib_deps:
        return
    integrity_dat = Path(shared_lib_dir) / "integrity.dat"
    have_deps_changed = True
    unused_dependencies = []
    new_dependencies = []
    if integrity_dat.is_file():
        prev_lib_deps = set(
            integrity_dat.read_text(encoding="utf-8").strip().split("\n")
        )
        unused_dependencies = set(prev_lib_deps) - set(lib_deps)
        new_dependencies = set(lib_deps) - set(prev_lib_deps)
        if len(unused_dependencies) == 0 and len(new_dependencies) == 0:
            print("No change in dependencies.")
            have_deps_changed = False
    return have_deps_changed, new_dependencies, unused_dependencies


have_deps_changed, new_dependencies, unused_dependencies = get_changed_dependencies()

# %%
# quit if there are no changes to the dependencies
if not have_deps_changed:
    print("No changes to the dependencies")
    os._exit(os.EX_OK)


# %%
# Uninstall unused libs, install new ones
# https://github.com/platformio/platformio-core/blob/b537004a75f4985630b5aec19699e48d4d186746/platformio/package/commands/install.py#L265
def uninstall_project_unused_libdeps(options):
    if options.get("silent"):
        private_lm.set_log_level(logging.WARN)
        print("Removing unused dependencies...")
    else:
        private_lm.set_log_level(logging.DEBUG)
    if len(unused_dependencies) == 0:
        print("No unused dependencies to remove.")
    for spec in unused_dependencies:
        # print(private_lm.log)
        try:
            private_lm.uninstall(spec)
        except UnknownPackageError:
            pass


# https://github.com/platformio/platformio-core/blob/b537004a75f4985630b5aec19699e48d4d186746/platformio/package/commands/install.py#L206
def install_project_env_libraries(options):
    uninstall_project_unused_libdeps(options)
    if options.get("silent"):
        private_lm.set_log_level(logging.WARN)
    else:
        private_lm.set_log_level(logging.DEBUG)

    lib_deps = humanized_deps
    for library in lib_deps:
        spec = PackageSpec(library)
        # skip built-in dependencies
        if not spec.external and not spec.owner:
            print(f"Skipping {library}")
            continue
        # print(private_lm.log)
        already_installed = private_lm.get_package(spec) is not None
        sub_dependencies = private_lm.get_pkg_dependencies(private_lm.get_package(spec))
        if (
            options.get("skip_dependencies") == False
            and sub_dependencies is not None
            and len(sub_dependencies) > 0
        ):
            for sub_dependency in sub_dependencies:
                dep_spec = private_lm.dependency_to_spec(sub_dependency)
                already_installed &= private_lm.get_package(dep_spec) is not None
        was_updated = False
        if not already_installed:
            print(
                "Installing",
                spec.name,
                spec.requirements if spec.requirements else spec.uri,
            )
            if options.get("silent"):
                private_lm.set_log_level(logging.WARN)
            else:
                private_lm.set_log_level(logging.DEBUG)
            # print(private_lm.log)
            private_lm.install(
                spec,
                skip_dependencies=options.get("skip_dependencies"),
                force=options.get("force"),
            )
            was_updated = True
        elif options.get("update"):
            print(
                "Updating",
                spec.name,
                spec.requirements if spec.requirements else spec.uri,
            )
            if options.get("silent"):
                private_lm.set_log_level(logging.WARN)
            else:
                private_lm.set_log_level(logging.DEBUG)
            # check if the library should be updated
            # print(private_lm.log)
            new_pkg = private_lm.update(
                spec, skip_dependencies=options.get("skip_dependencies")
            )
            org_pkg = private_lm.get_package(spec)
            was_updated = new_pkg == org_pkg
        if not was_updated:
            pass
    return private_lm.get_installed()


install_project_env_libraries(options)

# write a new 'integrity' file if needed
if not Path(shared_lib_dir).is_dir():
    Path(shared_lib_dir).mkdir(parents=True)
    integrity_dat = Path(shared_lib_dir) / "integrity.dat"
    integrity_dat.write_text("\n".join(humanized_deps), encoding="utf-8")


# %%
# check what's already installed and sort by dependencies
def sort_lib_deps(verbose=False):
    private_lm.set_log_level(logging.DEBUG)
    installed_libs = private_lm.get_installed()
    lib_order = {}
    for lib_num, installed_lib in enumerate(installed_libs):
        lib_order[installed_lib.metadata.name] = {}
        lib_order[installed_lib.metadata.name]["main_lib_order_num"] = lib_num
        lib_order[installed_lib.metadata.name]["dep_order_num"] = []
    unsorted_deps = copy.deepcopy(installed_libs)
    sorted_deps = []
    while len(unsorted_deps) > 0:
        current_lib = unsorted_deps.pop(0)
        pkg_deps = private_lm.get_pkg_dependencies(current_lib) or []
        if verbose:
            print(f"{current_lib.metadata.name} has {len(pkg_deps)} dependencies")
        num_sorted_deps = 0
        for dep_num, dependency in enumerate(pkg_deps):
            dep_spec = private_lm.dependency_to_spec(dependency)
            if verbose:
                print(f"{current_lib.metadata.name} is dependent on {dep_spec.name}")
            matched_dep = list(
                filter(lambda d: d.metadata.name == dep_spec.name, sorted_deps)
            )
            if dependency["name"] in ["SD"]:
                matched_dep.extend(dependency["name"])
            if len(matched_dep) == 0 or dep_spec.external:
                num_sorted_deps += 1
            else:
                if verbose:
                    print(f"{dep_spec.name} is already on the ordered list")
        if num_sorted_deps == 0:
            if verbose:
                print(f"{current_lib.metadata.name} has no remaining dependencies")
            sorted_deps.append(current_lib)
        else:
            if verbose:
                print(
                    f"{current_lib.metadata.name} still is dependent on {num_sorted_deps} other packages"
                )
            unsorted_deps.append(current_lib)

    # return not already_up_to_date
    return list(sorted_deps)


installed_libs = sort_lib_deps()


# %%
# check for not required libs
not_required_libs = []
for installed_lib in installed_libs:
    matched_by_name = list(
        filter(
            lambda d: d.name.lower() == installed_lib.metadata.name.lower(),
            dependencies,
        )
    )
    if len(matched_by_name) == 0:
        not_required_libs.append(installed_lib)
        continue
    elif len(matched_by_name) == 1:
        the_match = matched_by_name[0]
        if (
            installed_lib.metadata.spec.owner is not None
            and the_match.owner is not None
        ):
            if installed_lib.metadata.spec.owner.lower() != the_match.owner.lower():
                not_required_libs.append(installed_lib)
                continue
            if (
                installed_lib.metadata.version is not None
                and the_match.requirements is not None
                and installed_lib.metadata.version not in the_match.requirements
            ):
                not_required_libs.append(installed_lib)
                continue
        elif installed_lib.metadata.spec.uri is not None and the_match.uri is not None:
            if installed_lib.metadata.spec.uri.lower() != the_match.uri.lower():
                not_required_libs.append(installed_lib)
                continue
            else:
                continue
        else:
            print(f"WARNING! DON'T KNOW HOW TO MATCH {installed_lib.metadata.name}")
    else:
        print(f"WARNING! MORE THAN ONE LIBRARY MATCHED {installed_lib.metadata.name}")

# %%
all_symlinks = [
    f"{installed_lib.metadata.name}=symlink://{installed_lib.path}"
    for installed_lib in installed_libs
]

ignored_folders = [shared_lib_abbr]
using_main_dir = "." in get_extra_lib_dirs(common_env_name)
if using_main_dir:
    sub_dirs = next(os.walk(project_dir))[1]
    ignored_folders = [
        i_dir for i_dir in sub_dirs if i_dir not in ["lib", "src"] + [shared_lib_abbr]
    ]


out_file_str = ""
out_file_str += (
    "; File Automatically Generated by pioScripts/install_working_dependencies.py\n"
)

out_file_str += f"; File last updated at {datetime.datetime.now()}\n"
out_file_str += "; DO NOT MODIFY\n\n"
out_file_str += "; Global data for all [env:***]\n"
out_file_str += "[env]\n"

out_file_str += "lib_deps =\n"
for item in all_symlinks:
    out_file_str += "    "
    out_file_str += item
    out_file_str += "\n"

out_file_str += "lib_ignore =\n"
for folder in ignored_folders:
    out_file_str += "    "
    out_file_str += folder
    out_file_str += "\n"
for lib in not_required_libs:
    out_file_str += "    "
    out_file_str += lib.metadata.name
    out_file_str += "\n"
# for lib_name in ["Adafruit TinyUSB Library"]:
for lib_name in []:
    out_file_str += "    "
    out_file_str += lib_name
    out_file_str += "\n"

if os.path.isfile(libdeps_ini_file):
    with open(libdeps_ini_file, "r") as out_file:
        prev_content = out_file.read()
else:
    prev_content = ""


# %%
# check if dependencies have changed, we don't want to update the file if not
# if we update the platformio file, the ide will try to rebuild, causing a loop
have_deps_changed = len(prev_content.splitlines()) == 0 or len(
    prev_content.splitlines()
) != len(out_file_str.splitlines())
for line_num, line in enumerate(prev_content.splitlines()):
    if line.startswith("; File last updated at"):
        continue
    if len(out_file_str.splitlines()) <= line_num:
        have_deps_changed = True
    elif line != out_file_str.splitlines()[line_num]:
        have_deps_changed = True

# %%
if have_deps_changed:
    with open(libdeps_ini_file, "w+") as out_file:
        out_file.write(out_file_str)
else:
    print("No changes to dependency output file")
# %%
