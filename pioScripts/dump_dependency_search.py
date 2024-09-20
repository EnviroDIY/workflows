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

print("Working on environment (PIOENV) {}".format(env["PIOENV"]))

print("\n\nEnviroment Dump:")
print(env.Dump())
print("\n\n")

shared_lib_dir = env["LIBSOURCE_DIRS"][0]
shared_lib_abbr = "lib"
project_ini_file = f"{env['PROJECT_DIR']}\\platformio.ini"
libdeps_ini_file = f"{env['PROJECT_DIR']}\\pio_common_libdeps.ini"
library_json_file = f"{env['PROJECT_DIR']}\\library.json"
examples_deps_file = f"{env['PROJECT_DIR']}\\examples\\example_dependencies.json"
proj_config = env.GetProjectConfig()
lsds = env.GetLibSourceDirs()
print("\nlsds")
print(lsds)
print("\nproject ")
project = ProjectAsLibBuilder(env, "$PROJECT_DIR")
print(project)
print("LDF Mode:", project.lib_ldf_mode)
print("SRC DIR:", project.src_dir)
print("\nSRC Filter:", json.dumps(project.src_filter, indent=2))
print("\nDependencies:", project.dependencies)
print("\nInitial dependency builders:")
print(project.depbuilders)

lib_builders = env.GetLibBuilders()
print("\n\nFound %d compatible libraries" % len(lib_builders))
print(lib_builders)
print()

print("\n\nProcessing dependencies")
project.process_dependencies()
print("\nDependency builders after processing dependencies:")
print(project.depbuilders)

print("\n\nSearching Dependencies Recursively")
project.search_deps_recursive()
print("\nDependency builders after searching dependencies recursively:")
print(project.depbuilders)

if project.lib_ldf_mode.startswith("deep"):
    search_files = project.get_search_files()
print("\n\nFound %d files to search" % len(search_files))
print(json.dumps(search_files, indent=2))
print()

lib_inc_map = {}
for inc in project.get_implicit_includes(search_files):
    inc_path = inc.get_abspath()
    print("implicit include:")
    print(inc_path)
    for lb in project.env.GetLibBuilders():
        if inc_path in lb:
            if lb not in lib_inc_map:
                lib_inc_map[lb] = []
            lib_inc_map[lb].append(inc_path)
            break

print("lib_inc_map:")
print(json.dumps(lib_inc_map, indent=2))


sys.exit()
