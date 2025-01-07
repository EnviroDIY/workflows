import os
import sys
import subprocess

from SCons.Script import BUILD_TARGETS  # pylint: disable=import-error
from SCons.Script import COMMAND_LINE_TARGETS  # pylint: disable=import-error
from SCons.Script import DEFAULT_TARGETS  # pylint: disable=import-error

Import("env")

print(
    "Running generate_compile_commands.py on environment (PIOENV) {}".format(
        env["PIOENV"]
    )
)
# print(f"Current build targets: {[str(tgt) for tgt in BUILD_TARGETS]}")
# print(f"Current command line targets: {COMMAND_LINE_TARGETS}")

if set(["_idedata", "idedata"]) & set(COMMAND_LINE_TARGETS):
    print("This is an IDE data build, exiting.")
    os._exit(os.EX_OK)

if env.IsCleanTarget() or env.GetOption("clean"):
    print("This is cleaning, exiting.")
    os._exit(os.EX_OK)

# include toolchain paths
env.Replace(COMPILATIONDB_INCLUDE_TOOLCHAIN=True)
dump_dir = f"{env['PROJECT_WORKSPACE_DIR']}\\config\\{env['PIOENV']}"

if not os.path.exists(dump_dir):
    os.makedirs(dump_dir)

if "compiledb" not in COMMAND_LINE_TARGETS:  # avoids infinite recursion
    subprocess.run(["pio", "run", "-e", env["PIOENV"], "-t", "compiledb"])
else:
    env_dump_file = os.path.join(dump_dir, "pio_env_dump.log")
    print(f"Dumping environment to {env_dump_file}")
    output_file = open(env_dump_file, "w")

    output_file.write("Enviroment Dump:\n")
    output_file.write(env.Dump())
    output_file.close()
