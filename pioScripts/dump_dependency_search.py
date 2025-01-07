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
from platformio.builder.tools.piolib import ProjectAsLibBuilder

import click
from SCons.Script import ARGUMENTS  # pylint: disable=import-error
from SCons.Script import BUILD_TARGETS  # pylint: disable=import-error
from SCons.Script import COMMAND_LINE_TARGETS  # pylint: disable=import-error
from SCons.Script import DEFAULT_TARGETS  # pylint: disable=import-error
from SCons.Script import AllowSubstExceptions  # pylint: disable=import-error
from SCons.Script import AlwaysBuild  # pylint: disable=import-error
from SCons.Script import Default  # pylint: disable=import-error
from SCons.Script import DefaultEnvironment  # pylint: disable=import-error
from SCons.Script import Import  # pylint: disable=import-error
from SCons.Script import Variables  # pylint: disable=import-error

from platformio import app, fs
from platformio.platform.base import PlatformBase
from platformio.proc import get_pythonexe_path
from platformio.project.helpers import get_project_dir


# %%
# Some working directories
# try:
# Import the current working construction
# environment to the `env` variable.
# alias of `env = DefaultEnvironment()`
Import("env")
env.Append(CXXFLAGS=["/DEBUG"])

print(
    "Running dump_dependency_search.py on environment (PIOENV) {}".format(env["PIOENV"])
)
# print(f"Current build targets: {[str(tgt) for tgt in BUILD_TARGETS]}")
# print(f"Current command line targets: {COMMAND_LINE_TARGETS}")

if set(["_idedata", "idedata"]) & set(COMMAND_LINE_TARGETS):
    print("This is an IDE data build, exiting.")
    os._exit(os.EX_OK)

if env.IsCleanTarget() or env.GetOption("clean"):
    print("This is cleaning, exiting.")
    os._exit(os.EX_OK)

output_file_name = f"{env['PROJECT_DIR']}\\output_pio_dependency_dump.log"
output_file = open(output_file_name, "w")
print("Dumping environment:")
output_file.write("Enviroment Dump:\n")
output_file.write(env.Dump())
output_file.write("\n\n")

print("Dumping dependency search info:")
shared_lib_dir = env["LIBSOURCE_DIRS"][0]
shared_lib_abbr = "lib"
project_ini_file = f"{env['PROJECT_DIR']}\\platformio.ini"
libdeps_ini_file = f"{env['PROJECT_DIR']}\\pio_common_libdeps.ini"
library_json_file = f"{env['PROJECT_DIR']}\\library.json"
examples_deps_file = f"{env['PROJECT_DIR']}\\examples\\example_dependencies.json"
proj_config = env.GetProjectConfig()
lsds = env.GetLibSourceDirs()
output_file.write("lsds\n")
output_file.write(json.dumps(lsds))
output_file.write("\nproject ")
project = ProjectAsLibBuilder(env, "$PROJECT_DIR")
output_file.write(str(project))
output_file.write("\nLDF Mode:")
output_file.write(project.lib_ldf_mode)
output_file.write("\nSRC DIR:")
output_file.write(project.src_dir)
output_file.write("\nSRC Filter:")
output_file.write(json.dumps(project.src_filter, indent=2))
output_file.write("\nDependencies:\n")
output_file.write(json.dumps(project.dependencies))
output_file.write("\nInitial dependency builders:\n")
output_file.write(str(project.depbuilders))

lib_builders = env.GetLibBuilders()
output_file.write("\n\nFound %d compatible libraries\n" % len(lib_builders))
output_file.write(str(lib_builders))

output_file.write("\n\nProcessing dependencies\n")
project.process_dependencies()
output_file.write("\nDependency builders after processing dependencies:\n")
output_file.write(str(project.depbuilders))

output_file.write("\n\nSearching Dependencies Recursively")
project.search_deps_recursive()
output_file.write("\nDependency builders after searching dependencies recursively:\n")
output_file.write(str(project.depbuilders))

if project.lib_ldf_mode.startswith("deep"):
    search_files = project.get_search_files()
output_file.write("\n\nFound %d files to search\n" % len(search_files))
output_file.write(json.dumps(search_files, indent=2))
output_file.write("")

lib_inc_map = {}
for inc in project.get_implicit_includes(search_files):
    inc_path = inc.get_abspath()
    output_file.write("implicit include:")
    output_file.write(inc_path)
    for lb in project.env.GetLibBuilders():
        if inc_path in lb:
            if lb not in lib_inc_map:
                lib_inc_map[lb] = []
            lib_inc_map[lb].append(inc_path)
            break

output_file.write("lib_inc_map:")
output_file.write(json.dumps(lib_inc_map, indent=2))

output_file.close()

# os._exit(os.EX_OK)
